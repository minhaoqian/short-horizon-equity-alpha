"""Approved execution-feasibility audit. Never computes returns or PnL."""
from datetime import date
import hashlib
import json
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from .construction import plan

ROOT = Path(__file__).resolve().parents[2]
END = pd.Timestamp('2019-12-31')


def halt_mask(calendar, unresolved_dates, verified_termination_dates=None):
    """Decision-close state; same-open pre-submitted orders are unaffected.

    Only independently verified account/obligation termination can lift a halt.
    Security event dates and later prices are not such certificates.
    """
    cal = pd.DatetimeIndex(calendar)
    if cal.has_duplicates or not cal.is_monotonic_increasing:
        raise ValueError('Unique ordered market calendar required')
    ends = verified_termination_dates or {}
    active = np.zeros(len(cal), bool)
    for key, start in unresolved_dates.items():
        start = pd.Timestamp(start)
        stop = ends.get(key)
        if stop is not None and pd.Timestamp(stop) < start:
            raise ValueError('Termination precedes unresolved execution')
        active |= (cal >= start) & (True if stop is None else cal < pd.Timestamp(stop))
    return ~active


def run():
    cache = ROOT/'data/interim/stage4a_continuation'; cache.mkdir(parents=True,exist_ok=True)
    out = ROOT/'results/tables/stage4a'; out.mkdir(parents=True,exist_ok=True)
    forecasts = ROOT/'data/interim/stage3a/predictions'
    prior = json.loads((ROOT/'data/interim/stage3a/manifest.json').read_text())
    frozen = json.loads((ROOT/'data/interim/stage3a/source_manifest.json').read_text())
    for item in frozen['input_fingerprints']:
        st=(ROOT/item['path']).stat()
        assert (st.st_size,st.st_mtime_ns)==(item['size'],item['mtime_ns']), 'Changed frozen input'

    for k in range(1,69):
        assert hashlib.sha256((forecasts/f'fold_{k:02d}.parquet').read_bytes()).hexdigest()==prior['folds'][str(k)]['hashes']['predictions']
    c=duckdb.connect(); c.execute('SET threads=2')
    # No target returns, other forecast models or 2020 signals are projected.
    c.execute(f"""CREATE TABLE signals AS SELECT permno,signal_date::DATE signal_date,
        entry_date::DATE entry_date,exit_date::DATE exit_date,ridge,uni_reversal_5
        FROM read_parquet('{forecasts}/*.parquet')
        WHERE signal_date BETWEEN DATE '2003-01-02' AND DATE '2019-12-31'""")
    n,k=c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)) FROM signals').fetchone()
    assert (n,k)==(3829908,3829908)
    cal=pd.DatetimeIndex(c.execute('SELECT DISTINCT signal_date FROM signals ORDER BY 1').fetchnumpy()['signal_date'])
    assert len(cal)==4279
    # Full-development rank-screen inventory is expressly counterfactual;
    # it is not a portfolio and is not used to count primary submitted orders.
    c.execute('''CREATE TABLE rank_screen AS WITH u AS (
        SELECT permno,signal_date,entry_date,exit_date,
        unnest(['ridge','uni_reversal_5']) candidate,unnest([ridge,uni_reversal_5]) score
        FROM signals WHERE isfinite(ridge) AND isfinite(uni_reversal_5)),
        r AS (SELECT *,count(*) OVER(PARTITION BY candidate,signal_date) n,
        (rank() OVER(PARTITION BY candidate,signal_date ORDER BY score)
         +(count(*) OVER(PARTITION BY candidate,signal_date,score)-1)/2.0-.5)
         /count(*) OVER(PARTITION BY candidate,signal_date) u FROM u)
        SELECT *,CASE WHEN u>=.8 THEN 'long' ELSE 'short' END side
        FROM r WHERE n>=100 AND (u>=.8 OR u<=.2)''')
    c.execute(f"""CREATE VIEW endpoints AS SELECT permno,signal_date,entry_open,exit_open,
        label_status,label_reason FROM read_parquet('{ROOT}/data/interim/stage1g_targets/targets_5d.parquet')
        WHERE signal_date BETWEEN DATE '2003-01-02' AND DATE '2019-12-31'""")
    screen=c.execute('''SELECT candidate,label_status,side,count(*) observations,
        count(DISTINCT r.permno) distinct_permnos,min(r.exit_date) first_exit,
        max(r.exit_date) last_exit FROM rank_screen r JOIN endpoints t USING(permno,signal_date)
        GROUP BY ALL ORDER BY ALL''').fetchdf()
    screen['scope']='counterfactual_rank_screen_not_orders_or_live_book'
    screen.to_csv(out/'continuation_virtual_rank_screen.csv',index=False)
    # Determine the chronological witness before submitting any post-halt orders.
    first=c.execute('''SELECT candidate,min(exit_date) first_exit FROM rank_screen r
        JOIN endpoints t USING(permno,signal_date) WHERE entry_open>0
          AND label_status IN ('valid_entry_unresolved_exit_wealth','other_unresolved_corporate_action')
        GROUP BY candidate ORDER BY candidate''').fetchall()
    assert all(pd.Timestamp(t)==pd.Timestamp('2003-01-13') for _,t in first)
    # The primary audit needs only seven decision dates, ending close Jan10.
    # It cannot create new primary trades after the Jan13 decision-close halt.
    last_pre_halt=pd.Timestamp('2003-01-10')
    c.execute(f"""CREATE TABLE sizing AS SELECT permno,dlycaldt signal_date,dlyprc,adv20,
        dlyprcflg FROM read_parquet('{ROOT}/data/interim/reconstruction_diagnostic_parts/part_*.parquet')
        WHERE dlycaldt BETWEEN DATE '2003-01-02' AND DATE '2003-01-10'""")
    assert c.execute('SELECT count(*)-count(DISTINCT(permno,signal_date)) FROM sizing').fetchone()[0]==0
    d=c.execute('''SELECT s.*,p.dlyprc,p.adv20,p.dlyprcflg FROM signals s LEFT JOIN sizing p
        USING(permno,signal_date) WHERE s.signal_date<=DATE '2003-01-10'
        ORDER BY s.signal_date,s.permno''').fetchdf()
    c.execute(f"""CREATE TABLE early_events AS SELECT permno,disexdt::DATE disexdt,
        dispaymenttype,distype,disdetailtype,disfacshr,dispermno
        FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdistributions.parquet')
        WHERE disexdt BETWEEN DATE '2003-01-02' AND DATE '2003-01-10'""")
    events=c.execute('SELECT * FROM early_events').fetchdf()
    orders=[]; capacity_checks=[]
    for model in ('uni_reversal_5','ridge'):
        previous=[]
        for signal,g in d.groupby('signal_date',sort=True):
            g=g.reset_index(drop=True)
            due=[]
            tomorrow=c.execute('SELECT min(entry_date) FROM signals WHERE signal_date=?',[signal]).fetchone()[0]
            for old in previous:
                if pd.Timestamp(old['exit_date'])!=pd.Timestamp(tomorrow): continue
                # Close-t known parent share transformations only. Terminal
                # cash events need no parent trade at the opening; conservatively
                # reserving their pre-event flow cannot improve entry capacity.
                e=events[(events.permno==old['permno']) & (events.disexdt>old['signal_date'])
                         & (events.disexdt<=signal)]
                assert e.empty or (e.dispaymenttype.eq('USD') | (
                    e.dispaymenttype.eq('SS') & e.distype.eq('FRS') &
                    e.disdetailtype.isin(['STKSPL','STKDIV']) & e.dispermno.fillna(0).eq(0))).all(), 'Unsupported pre-halt quantity transformation'
                splits=e[(e.dispaymenttype=='SS') & (e.distype=='FRS') & e.disdetailtype.isin(['STKSPL','STKDIV']) & (e.dispermno.fillna(0)==0)]
                multiplier=float(np.prod(1+splits.disfacshr.to_numpy(float)))
                assert np.isfinite(multiplier) and multiplier>0
                due.append((old['permno'],abs(old['signed_order_shares'])*multiplier))
            gross={}
            for permno,q in due:gross[permno]=gross.get(permno,0)+q
            exit_q=np.array([gross.get(int(p),0) for p in g.permno])
            side,dollars,reasons=plan(g[model],g.dlyprc,g.adv20,exit_q)
            # Verify this witness's sizing is independent of conservative cash
            # exit reservation: no selected capacity is binding before the halt.
            zero_flow=plan(g[model],g.dlyprc,g.adv20,np.zeros(len(g)))[1]
            np.testing.assert_allclose(dollars,zero_flow,atol=1e-8)
            capacity_checks.append({'candidate':model,'signal_date':signal,
                                    'nonbinding_conservative_due_flow':True})
            z=g[['permno','signal_date','entry_date','exit_date']].copy()
            z['candidate']=model;z['planned_dollars']=dollars
            z['signed_order_shares']=dollars/g.dlyprc
            z['decision_reason']=reasons;z['side']=np.where(dollars>0,'long',np.where(dollars<0,'short','unallocated'))
            previous+=z[z.planned_dollars!=0].to_dict('records');orders.append(z)
    orders=pd.concat(orders,ignore_index=True)
    assert not orders.duplicated(['candidate','permno','signal_date']).any()
    assert len(orders)==2*len(d)
    orders.to_parquet(cache/'primary_pre_halt_decisions.parquet',index=False)
    c.register('orders',orders)
    c.execute('CREATE TABLE measured AS SELECT o.*,t.entry_open,t.exit_open,t.label_status,t.label_reason FROM orders o JOIN endpoints t USING(permno,signal_date)')
    c.execute(f"COPY measured TO '{cache}/primary_submitted_measurement.parquet' (FORMAT PARQUET)")
    rows=c.execute('''SELECT * FROM measured WHERE planned_dollars<>0 AND entry_open>0
        AND label_status IN ('valid_entry_unresolved_exit_wealth','other_unresolved_corporate_action')
        ORDER BY candidate,exit_date''').fetchdf()
    assert len(rows)==2 and rows.permno.nunique()==1
    uncertain_entries=c.execute('''SELECT * FROM measured WHERE planned_dollars<>0
        AND label_status='missing_entry_measurement' ORDER BY candidate,entry_date''').fetchdf()
    assert len(uncertain_entries)==1 and uncertain_entries.iloc[0].candidate=='ridge'
    # This already-submitted short is NOT retrospectively canceled or netted
    # against the unknown long. It is a distinct unmeasured entry/quantity case.
    uncertain_entries.to_parquet(cache/'pre_submitted_unknown_entry.parquet',index=False)

    # Full development history of the actual primary witness only; no holdout
    # events, prices or account-termination inference from later trading.
    c.register('witness_keys',rows[['candidate','permno','exit_date']])
    c.execute(f"""CREATE TABLE later_delists AS SELECT k.candidate,l.* FROM witness_keys k
        JOIN read_parquet('{ROOT}/data/interim/stage2a_events/stkdelists.parquet') l USING(permno)
        WHERE (l.delistingdt BETWEEN k.exit_date AND DATE '2019-12-31'
            OR l.deldlydt BETWEEN k.exit_date AND DATE '2019-12-31'
            OR l.delamtdt BETWEEN k.exit_date AND DATE '2019-12-31')""")
    c.execute(f"""CREATE TABLE later_distributions AS SELECT k.candidate,e.* FROM witness_keys k
        JOIN read_parquet('{ROOT}/data/interim/stage2a_events/stkdistributions.parquet') e USING(permno)
        WHERE e.disexdt BETWEEN k.exit_date AND DATE '2019-12-31'""")
    for name in ('later_delists','later_distributions'):
        c.execute(f"COPY {name} TO '{cache}/{name}.parquet' (FORMAT PARQUET)")
    summaries=[];durations=[]; states=[];event_summaries=[]
    for model in ('uni_reversal_5','ridge'):
        r=rows[rows.candidate==model].iloc[0]
        start=pd.Timestamp(r.exit_date)
        # No account-level termination certificate exists in these CRSP
        # security-level histories. Do not equate FPAY to a specific account fill.
        tradable=halt_mask(cal,{'first_unresolved_order':start},{})
        days=int((END-start).days); market_days=int((cal>=start).sum())
        ld=c.execute('SELECT delistingdt,delpaymenttype,delstatustype FROM later_delists WHERE candidate=? ORDER BY delistingdt',[model]).fetchall()
        e=c.execute('SELECT count(*) FROM later_distributions WHERE candidate=?',[model]).fetchone()[0]
        summary={'candidate':model,'development_decision_dates':len(cal),
            'first_unresolved_scheduled_exit':str(start.date()),'halt_decision_close':str(start.date()),
            'first_blocked_new_entry_open':'2003-01-14','first_unresolved_side':r.side,
            'first_entry_notional':float(abs(r.signed_order_shares)*r.entry_open),
            'primary_unresolved_valid_entry_exit_cases':int((rows.candidate==model).sum()),
            'primary_unresolved_distinct_permnos':1,
            'pre_submitted_unknown_entry_quantity_cases':int((uncertain_entries.candidate==model).sum()),
            'primary_unresolved_scheduled_exit_or_quantity_cases':int((rows.candidate==model).sum()+(uncertain_entries.candidate==model).sum()),

            'tradable_decision_dates':int(tradable.sum()),'tradable_fraction':float(tradable.mean()),
            'earliest_persistent_halt_through_development_end':str(start.date()),
            'independently_proven_resume_date':'','unresolved_calendar_days':days,
            'unresolved_development_decision_dates':market_days,
            'later_security_delisting_events':len(ld),'later_distribution_records':e,
            'termination_evidence_status':'no_account_or_obligation_termination_certificate',
            'headline_performance_identifiable':False}
        summaries.append(summary)
        durations.append({'candidate':model,'scope':'actual_primary_valid_entry_order',
            'start':str(start.date()),'planned_exit':str(pd.Timestamp(r.exit_date).date()),'end_censor':str(END.date()),'calendar_elapsed_days':days,
            'affected_decision_dates_inclusive':market_days,'right_censored':True,
            'observed_termination_date':'','scope_beyond_2019':'not_assessed'})
        for d0,yes in zip(cal,tradable):states.append({'candidate':model,'decision_date':d0,
            'new_primary_orders_permitted':bool(yes),'reason':'no_known_unresolved_exit' if yes else 'persistent_unresolved_execution'})
        for dt,payment,status in ld:
            event_summaries.append({'candidate':model,'event_date':dt,'payment_type':payment,
                'completion_status':status,'proves_parent_security_event':True,
                'proves_account_exit_or_all_obligations_terminated':False})
    for r in uncertain_entries.to_dict('records'):
        start=pd.Timestamp(r['entry_date'])
        durations.append({'candidate':r['candidate'],'scope':'already_submitted_unknown_entry_quantity',
            'start':str(start.date()),'planned_exit':str(pd.Timestamp(r['exit_date']).date()),'end_censor':str(END.date()),
            'calendar_elapsed_days':int((END-start).days),
            'affected_decision_dates_inclusive':int((cal>=start).sum()),'right_censored':True,
            'observed_termination_date':'','scope_beyond_2019':'not_assessed'})
    pd.DataFrame(summaries).to_csv(out/'continuation_feasibility_summary.csv',index=False)
    pd.DataFrame(durations).to_csv(out/'continuation_unresolved_durations.csv',index=False)
    pd.DataFrame(states).to_csv(out/'continuation_decision_states.csv',index=False)
    pd.DataFrame(event_summaries).to_csv(out/'continuation_later_event_evidence.csv',index=False)
    pd.DataFrame(capacity_checks).to_csv(out/'continuation_pre_halt_capacity_qa.csv',index=False)
    submitted=c.execute('''SELECT candidate,label_status,side,count(*) orders
        FROM measured WHERE planned_dollars<>0 GROUP BY ALL ORDER BY ALL''').fetchdf()
    submitted['scope']='actual_pre_halt_submitted_orders';submitted.to_csv(out/'continuation_submitted_order_inventory.csv',index=False)
    manifest={'qa_passed':True,'forecast_checksums_verified':68,'original_development_keys':n,
        'development_dates':len(cal),'primary_halt_policy':'approved RL-063',
        'permanent_halt_statement':'persistent through 2019-12-31; beyond-period termination not assessed',
        'independent_account_termination_certificates':0,'performance_computed':False,
        'return_or_target_values_projected':False,'holdout_records_accessed':0,
        'wrds_queries':0,'raw_scanned':False,'summaries':summaries}
    (cache/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    c.close();print(json.dumps(manifest,indent=2))
