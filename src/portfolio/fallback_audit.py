"""Separate Stage4B execution-assumption audit. No PnL or target returns."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb
from .construction import plan
from .fallback import positive_open,entry_assumption,verified_split_multiplier,admissible_liquidation

ROOT=Path(__file__).resolve().parents[2]


def run():
    protected=[ROOT/'docs/stage4a_continuation_feasibility.md',
        ROOT/'results/tables/stage4a/continuation_feasibility_summary.csv',
        ROOT/'results/figures/stage4a/continuation_feasibility.png',
        ROOT/'data/interim/stage4a_continuation/manifest.json']
    strict_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    out=ROOT/'results/tables/stage4b';cache=ROOT/'data/interim/stage4b'
    out.mkdir(parents=True,exist_ok=True);cache.mkdir(parents=True,exist_ok=True)
    m=json.loads((ROOT/'data/interim/stage3a/manifest.json').read_text())
    paths=ROOT/'data/interim/stage3a/predictions'
    for i in range(1,69):assert hashlib.sha256((paths/f'fold_{i:02d}.parquet').read_bytes()).hexdigest()==m['folds'][str(i)]['hashes']['predictions']
    frozen=json.loads((ROOT/'data/interim/stage3a/source_manifest.json').read_text())
    for x in frozen['input_fingerprints']:
        st=(ROOT/x['path']).stat();assert (st.st_size,st.st_mtime_ns)==(x['size'],x['mtime_ns'])
    c=duckdb.connect();c.execute('SET threads=2')
    counts=c.execute(f"SELECT count(*),count(DISTINCT(permno,signal_date)),count(DISTINCT signal_date) FROM read_parquet('{paths}/*.parquet') WHERE signal_date BETWEEN DATE '2003-01-02' AND DATE '2019-12-31'").fetchone()
    assert counts==(3829908,3829908,4279)
    fullcal=c.execute(f"SELECT signal_date::DATE FROM read_parquet('{ROOT}/data/interim/stage3a/calendar.parquet') WHERE signal_date BETWEEN DATE '2003-01-02' AND DATE '2019-12-31' ORDER BY 1").fetchnumpy()['CAST(signal_date AS DATE)']
    fullcal=[pd.Timestamp(d).date() for d in fullcal];td={d:i for i,d in enumerate(fullcal)}
    signal=c.execute(f"""SELECT permno,signal_date::DATE signal_date,entry_date::DATE entry_date,
        exit_date::DATE exit_date,ridge,uni_reversal_5 FROM read_parquet('{paths}/fold_01.parquet')
        WHERE signal_date BETWEEN DATE '2003-01-02' AND DATE '2003-03-31' ORDER BY signal_date,permno""").fetchdf()
    for col in ('signal_date','entry_date','exit_date'):signal[col]=pd.to_datetime(signal[col]).dt.date
    c.register('signal',signal)
    # Cached first-quarter source records only; no 2020 signals/source access.
    daily=c.execute(f"""SELECT permno,dlycaldt,dlyprc,dlyopen,adv20,dlyorddivamt,dlynonorddivamt FROM read_parquet(
        '{ROOT}/data/interim/reconstruction_diagnostic_parts/part_*.parquet')
        WHERE dlycaldt BETWEEN DATE '2003-01-02' AND DATE '2003-04-11'
        AND permno IN (SELECT DISTINCT permno FROM signal)""").fetchdf()
    assert not daily.duplicated(['permno','dlycaldt']).any()
    records={(int(r.permno),pd.Timestamp(r.dlycaldt).date()):r for r in daily.itertuples()}
    def row(p,d):return records.get((int(p),d))
    def opening(p,d):
        r=row(p,d);return None if r is None else r.dlyopen
    ev=c.execute(f"""SELECT * FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdistributions.parquet')
        WHERE disexdt BETWEEN DATE '2003-01-02' AND DATE '2003-04-11'
        AND permno IN (SELECT DISTINCT permno FROM signal) ORDER BY disexdt,permno,disseqnbr""").fetchdf()
    dl=c.execute(f"""SELECT * FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdelists.parquet')
        WHERE (delistingdt BETWEEN DATE '2003-01-02' AND DATE '2003-04-11'
        OR deldlydt BETWEEN DATE '2003-01-02' AND DATE '2003-04-11'
        OR delamtdt BETWEEN DATE '2003-01-02' AND DATE '2003-04-11')
        AND permno IN (SELECT DISTINCT permno FROM signal)""").fetchdf()
    groups={pd.Timestamp(d).date():g.to_dict('records') for d,g in ev.groupby('disexdt')}
    signals={d:g.reset_index(drop=True) for d,g in signal.groupby('signal_date')}
    allorders=[];decisions=[];states=[];issues=[];summaries=[];accounting_events=[]
    for model in ('uni_reversal_5','ridge'):
        book=[];orders=[];submitted=[];halt=None;capital_unknown=False
        for date in [d for d in fullcal if d<=pd.Timestamp('2003-04-11').date()]:
            terms=groups.get(date,[])
            # Opening-effective actions on already owned shares precede trades;
            # events on entry day do not grant rights to the new position.
            for pos in book:
                if pos['state']!='outstanding':continue
                same=[e for e in terms if e['permno']==pos['permno']]
                if not same:continue
                ordinary_or_split=True
                quantity_before=pos['current_shares']
                for e in same:
                    accounting_events.append({'candidate':model,'permno':pos['permno'],
                        'signal_date':pos['signal_date'],'effective_date':date,
                        'owned_prior_share_quantity':quantity_before,
                        'distribution_sequence':e['disseqnbr'],'payment_type':e['dispaymenttype'],
                        'event_type':e['distype'],'cash_amount_per_prior_share':e['disdivamt'] if e['dispaymenttype']=='USD' else None,
                        'share_factor':e['disfacshr'],'received_permno':e['dispermno'],
                        'payment_date':e['dispaydt'],'terms_source':'global_crsp_history',
                        'economic_wealth_or_return_computed':False})
                    multiplier=verified_split_multiplier(e)
                    split=multiplier is not None
                    fixed=(e['dispaymenttype']=='USD' and e['distype'] in ('CD','SD','ROC','CG')
                           and e['disfacshr']==0 and e['disfacpr']==0)
                    cash_terminal=(e['dispaymenttype']=='USD' and e['distype']=='CP'
                        and ((dl.permno==pos['permno']) & (dl.delpaymenttype=='CASH')
                             & (dl.delstatustype=='FPAY') & dl.deldistype.isin(['D1','D2'])
                             & (dl.delretmisstype=='NA') & (dl.deldlydt.dt.date==date)
                             & (dl.delamtdt.dt.date<=date)).any())
                    if split:
                        if pos['current_shares'] is not None:pos['current_shares']*=multiplier
                        pos['split_events']+=1
                    elif fixed:pos['cash_claim_events']+=1
                    elif cash_terminal:
                        cash_terms=[x for x in same if x['dispaymenttype']=='USD']
                        assert e['disdetailtype'] in ('CPM','CPRCSH')
                        assert all(pd.notna(x['disdivamt']) and np.isfinite(x['disdivamt']) and x['disdivamt']>=0 for x in cash_terms)
                        amount=sum(x['disdivamt'] for x in cash_terms)
                        contemporary=row(pos['permno'],date)
                        assert contemporary is not None
                        assert abs(amount-contemporary.dlyorddivamt-contemporary.dlynonorddivamt)<1e-5
                        matched=dl[(dl.permno==pos['permno']) & (dl.deldlydt.dt.date==date)]
                        assert len(matched)==1 and abs(amount-matched.iloc[0].deldivamt)<1e-5
                        pos['state']='measurable_cash_termination';pos['actual_assumed_exit_date']=date
                        pos['actual_delay']=None;pos['fallback_reason']='independent_cash_replacement_not_market_trade'
                    else:
                        ordinary_or_split=False;pos['state']='unresolved_execution'
                        pos['unresolved_known_date']=date;pos['fallback_reason']='received_asset_quantity_or_terms_unverified'
                        pos['received_permno']=e['dispermno'];pos['received_quantity']=None
                        pos['last_verified_parent_shares']=pos['current_shares'];pos['current_shares']=None
                        issues.append({'candidate':model,'permno':pos['permno'],'signal_date':pos['signal_date'],
                            'event_date':date,'event_type':e['distype'],'payment_type':e['dispaymenttype'],
                            'received_permno':e['dispermno'],'disfacshr':e['disfacshr'],
                            'quantity_verified':False})
                if not ordinary_or_split:capital_unknown=True;halt=halt or date
            # Orders submitted at a previous close remain even if a halt is
            # discovered at this opening. Missing entry is NOW assumed no-fill.
            for order in submitted:
                if order['scheduled_entry_date']!=date:continue
                p=opening(order['permno'],date)
                order['entry_status']=entry_assumption(p)
                if order['entry_status']=='canceled_missing_open':
                    order['state']='canceled_entry';order['fallback_reason']='scheduled_entry_open_not_positive_assume_no_fill'
                    continue
                q=order['order_shares']
                for e in terms:
                    if e['permno']==order['permno'] and verified_split_multiplier(e) is not None:
                        q*=verified_split_multiplier(e)
                order['current_shares']=q;order['actual_assumed_entry_date']=date
                order['entry_notional']=abs(q)*p;order['state']='outstanding';book.append(order)
            for pos in book:
                if pos['state']!='outstanding' or date<pos['scheduled_exit_date']:continue
                delay=td[date]-td[pos['scheduled_exit_date']]
                assert delay<=5
                p=opening(pos['permno'],date)
                if admissible_liquidation(p,pos['current_shares']):
                    pos['state']='assumed_exited';pos['actual_assumed_exit_date']=date;pos['actual_delay']=delay
                    pos['fallback_reason']='scheduled_open' if delay==0 else 'first_positive_open_within_five'
                elif delay==5:
                    pos['state']='unresolved_execution';pos['unresolved_known_date']=date
                    pos['actual_delay']=None;pos['fallback_reason']='no_admissible_open_in_five_subsequent_global_dates'
                    halt=halt or date;capital_unknown=True
            operational=halt is None
            states.append({'candidate':model,'decision_date':date,'operational':operational,
                'reason':'approved_fallback_assumption' if operational else 'unresolved_execution_or_asset_quantity'})
            if date not in signals or not operational:continue
            g=signals[date];price=np.array([row(p,date).dlyprc if row(p,date) else np.nan for p in g.permno])
            adv=np.array([row(p,date).adv20 if row(p,date) else np.nan for p in g.permno])
            tomorrow=fullcal[td[date]+1]
            gross={}
            for pos in book:
                if pos['state']=='outstanding' and pos['scheduled_exit_date']<=tomorrow:
                    gross[pos['permno']]=gross.get(pos['permno'],0)+abs(pos['current_shares'])
            exits=np.array([gross.get(int(p),0) for p in g.permno])
            sides,dollars,reasons=plan(g[model],price,adv,exits)
            for i,r in enumerate(g.itertuples()):
                decisions.append({'candidate':model,'permno':r.permno,'signal_date':date,
                                  'decision_reason':reasons[i],'planned_dollars':dollars[i]})
                if dollars[i]==0:continue
                order={'candidate':model,'permno':r.permno,'signal_date':date,
                    'scheduled_entry_date':r.entry_date,'scheduled_exit_date':r.exit_date,
                    'side':'long' if dollars[i]>0 else 'short','planned_entry_notional':abs(dollars[i]),
                    'order_shares':dollars[i]/price[i],'current_shares':None,
                    'state':'submitted','entry_status':'pending','entry_notional':None,
                    'actual_assumed_entry_date':None,'actual_assumed_exit_date':None,'actual_delay':None,
                    'split_events':0,'cash_claim_events':0,'received_permno':None,'received_quantity':None,
                    'unresolved_known_date':None,'fallback_reason':None}
                orders.append(order);submitted.append(order)
        # If first-quarter gate passed, do NOT promote a bounded run to a
        # full-development pass; a longer run would be required.
        assert halt is not None,'Bounded gate passed: extend feasibility audit before any performance'
        for date in fullcal:
            if date>pd.Timestamp('2003-04-11').date():states.append({'candidate':model,'decision_date':date,
                'operational':False,'reason':'persistent_unverified_asset_quantity_no_termination_certificate'})
        for pos in orders:
            if pos['actual_assumed_entry_date'] and pos['actual_assumed_exit_date']:
                pos['realized_holding_global_days']=td[pos['actual_assumed_exit_date']]-td[pos['actual_assumed_entry_date']]
            else:pos['realized_holding_global_days']=None
            pos['scheduled_exit_open_missing']=pos['entry_status']=='assumed_entry' and not positive_open(opening(pos['permno'],pos['scheduled_exit_date']))
            if pos['state']=='unresolved_execution':
                deadline=fullcal[td[pos['scheduled_exit_date']]+5]
                pos['five_day_deadline']=deadline
                pos['parent_open_unavailable_at_all_six_attempt_dates']=not any(positive_open(opening(pos['permno'],fullcal[j]))
                    for j in range(td[pos['scheduled_exit_date']],td[deadline]+1))
        allorders+=orders
        frame=pd.DataFrame(orders);canceled=frame[frame.state=='canceled_entry']
        unresolved=frame[frame.state=='unresolved_execution']
        calendar_states=[x for x in states if x['candidate']==model]
        summaries.append({'candidate':model,'original_development_keys':counts[0],
            'development_decision_dates':counts[2],'submitted_name_orders':len(frame),
            'affected_exception_parent_permnos':int(frame[(frame.state=='canceled_entry') | frame.scheduled_exit_open_missing | (frame.state=='unresolved_execution')].permno.nunique()),
            'missing_scheduled_entries':len(canceled),'canceled_entry_decision_notional':float(canceled.planned_entry_notional.sum()),
            'missing_scheduled_exits':int(frame.scheduled_exit_open_missing.sum()),
            'missing_exit_open_with_measurable_cash_replacement':int(((frame.state=='measurable_cash_termination') & frame.scheduled_exit_open_missing).sum()),
            'resolved_at_scheduled_open':int((frame.actual_delay==0).sum()),
            **{f'exits_resolved_delay_{k}':int((frame.actual_delay==k).sum()) for k in range(1,6)},
            'unresolved_execution_or_quantity_positions':len(unresolved),
            'unresolved_quantity_and_no_parent_open_by_five_date_cap':int(sum(v is True or v==True for v in unresolved.parent_open_unavailable_at_all_six_attempt_dates)),
            'unresolved_distinct_permnos':int(unresolved.permno.nunique()),
            'first_halt_decision_close':str(halt),'operational_decision_dates':sum(x['operational'] for x in calendar_states),
            'operational_fraction':sum(x['operational'] for x in calendar_states)/counts[2],
            'independently_proven_resume_date':'','permanent_halt_through_development_end':True,
            'feasibility_gate_passed':False})
    orders=pd.DataFrame(allorders);decisions=pd.DataFrame(decisions)
    assert set(orders.state)<=set(['canceled_entry','assumed_exited','measurable_cash_termination','unresolved_execution'])
    market=orders[orders.state=='assumed_exited']
    for r in market.itertuples():
        assert positive_open(opening(r.permno,r.actual_assumed_exit_date))
        assert all(not positive_open(opening(r.permno,fullcal[j]))
                   for j in range(td[r.scheduled_exit_date],td[r.actual_assumed_exit_date]))

    assert market.actual_delay.between(0,5).all()
    assert (market.realized_holding_global_days==5+market.actual_delay).all()
    assert (market.actual_assumed_entry_date==market.scheduled_entry_date).all()
    assert not orders[orders.state=='canceled_entry'].actual_assumed_entry_date.notna().any()
    assert all(sum(x['candidate']==model for x in states)==4279 for model in ('uni_reversal_5','ridge'))

    assert not orders.duplicated(['candidate','permno','signal_date']).any()
    assert not decisions.duplicated(['candidate','permno','signal_date']).any()
    orders.to_parquet(cache/'assumed_orders_and_execution_states.parquet',index=False)
    ev.to_parquet(cache/'bounded_distribution_history.parquet',index=False)
    dl.to_parquet(cache/'bounded_delisting_history.parquet',index=False)
    unknown_keys=orders[orders.state=='unresolved_execution'][['permno','received_permno']].drop_duplicates()
    c.register('unknown_keys',unknown_keys)
    later=c.execute(f"""SELECT * FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdistributions.parquet')
        WHERE permno IN (SELECT permno FROM unknown_keys UNION SELECT received_permno FROM unknown_keys)
        AND disexdt BETWEEN DATE '2003-03-31' AND DATE '2019-12-31'""").fetchdf()
    later.to_parquet(cache/'unresolved_parent_successor_event_history.parquet',index=False)
    # These security-level events supply no verified initial received inventory
    # or account termination certificate; no later prices/ratios repair it.

    decisions.to_parquet(cache/'all_pre_halt_signal_decisions.parquet',index=False)
    pd.DataFrame(issues).to_parquet(cache/'unverified_asset_events.parquet',index=False)
    pd.DataFrame(accounting_events).to_parquet(cache/'owned_event_terms_and_entitlements.parquet',index=False)
    affected=orders[(orders.state=='canceled_entry') | orders.scheduled_exit_open_missing | (orders.state=='unresolved_execution')]
    affected.groupby(['candidate','side','state'],dropna=False).agg(observations=('permno','size'),distinct_permnos=('permno','nunique')).reset_index().to_csv(out/'affected_execution_states_by_side.csv',index=False)
    unresolved=orders[orders.state=='unresolved_execution']
    unresolved.groupby(['candidate','scheduled_exit_date','five_day_deadline','side','fallback_reason'],dropna=False).agg(observations=('permno','size'),distinct_permnos=('permno','nunique')).reset_index().to_csv(out/'unresolved_execution_deadlines.csv',index=False)

    pd.DataFrame(summaries).to_csv(out/'execution_feasibility_summary.csv',index=False)
    pd.DataFrame(states).sort_values(['candidate','decision_date']).to_csv(out/'operational_decision_states.csv',index=False)
    orders.groupby(['candidate','side','state'],dropna=False).agg(observations=('permno','size'),distinct_permnos=('permno','nunique')).reset_index().to_csv(out/'execution_states_by_side.csv',index=False)
    orders.groupby(['candidate','side','state','realized_holding_global_days'],dropna=False).size().rename('observations').reset_index().to_csv(out/'realized_holding_durations.csv',index=False)
    orders.groupby(['candidate','side','state','actual_delay'],dropna=False).size().rename('observations').reset_index().to_csv(out/'exit_delays_by_side.csv',index=False)
    pd.DataFrame(issues).groupby(['candidate','event_date','event_type','payment_type','quantity_verified']).agg(observations=('permno','size'),distinct_permnos=('permno','nunique')).reset_index().to_csv(out/'unresolved_asset_event_summary.csv',index=False)
    assert strict_hashes=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    (cache/'manifest.json').write_text(json.dumps({'execution_assumption_only':True,'qa_passed':True,
        'full_period_execution_feasibility_passed':False,'forecast_hashes_verified':68,
        'original_development_keys':counts[0],'global_development_decision_dates':counts[2],
        'raw_file_scanned':False,'wrds_queries':0,'holdout_records_accessed':0,
        'performance_computed':False,'frozen_target_changed':False,
        'strict_stage4a_artifacts_modified':False,'protected_stage4a_hashes':strict_hashes,'summaries':summaries},indent=2)+'\n')
    c.close();print(json.dumps(summaries,indent=2))
