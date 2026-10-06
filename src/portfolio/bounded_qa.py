"""Bounded 2003 opening-accounting gate, no performance or holdout access."""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import duckdb
import numpy as np
import pandas as pd
from .construction import plan

ROOT = Path(__file__).resolve().parents[2]


def run():
    c = duckdb.connect(); c.execute('SET threads=2')
    cache = ROOT / 'data/interim/stage4a'
    out = ROOT / 'results/tables/stage4a'
    cache.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    forecast = ROOT / 'data/interim/stage3a/predictions/fold_01.parquet'
    prior = json.loads((ROOT/'data/interim/stage3a/manifest.json').read_text())
    assert hashlib.sha256(forecast.read_bytes()).hexdigest() == prior['folds']['1']['hashes']['predictions']
    sources = json.loads((ROOT/'data/interim/stage3a/source_manifest.json').read_text())
    for item in sources['input_fingerprints']:
        st = (ROOT/item['path']).stat()
        assert (st.st_size,st.st_mtime_ns)==(item['size'],item['mtime_ns']), 'Changed frozen source'

    # Signal projection contains no outcome/label columns.
    c.execute(f"""CREATE TABLE scores AS SELECT permno, signal_date::DATE signal_date,
        entry_date::DATE entry_date,exit_date::DATE exit_date,ridge,uni_reversal_5
        FROM read_parquet('{forecast}') WHERE signal_date BETWEEN DATE '2003-01-02' AND DATE '2003-01-14'""")
    c.execute(f"""CREATE TABLE sizing AS SELECT permno,dlycaldt signal_date,dlyprc,adv20,
        dlyprcflg FROM read_parquet('{ROOT}/data/interim/reconstruction_diagnostic_parts/part_*.parquet')
        WHERE dlycaldt IN (DATE '2003-01-02',DATE '2003-01-03')""")
    assert c.execute('SELECT count(*)-count(DISTINCT(permno,signal_date)) FROM sizing').fetchone()[0] == 0
    d = c.execute('SELECT s.*,p.dlyprc,p.adv20,p.dlyprcflg FROM scores s LEFT JOIN sizing p USING(permno,signal_date) WHERE s.signal_date<=DATE \'2003-01-03\' ORDER BY s.signal_date,s.permno').fetchdf()
    orders = []
    for date, group in d.groupby('signal_date', sort=True):
        group = group.reset_index(drop=True)
        assert (group[group.ridge.notna()].dlyprcflg == 'TR').all()
        for model in ('uni_reversal_5', 'ridge'):
            # Initial two cohorts have no prior five-day sleeve exit commitments.
            _, dollars, reasons = plan(group[model], group.dlyprc, group.adv20, np.zeros(len(group)))
            z = group[['permno','signal_date','entry_date','exit_date']].copy()
            z['candidate'] = model; z['planned_dollars'] = dollars
            z['signed_order_shares'] = dollars / group.dlyprc
            z['decision_reason'] = reasons
            orders.append(z)
    orders = pd.concat(orders, ignore_index=True)
    assert len(d)==923 and len(orders) == 2*len(d)
    assert not orders.duplicated(['candidate','permno','signal_date']).any()
    orders.to_parquet(cache/'bounded_decisions.parquet', index=False)
    c.register('orders', orders)
    # Post-decision endpoint join solely for execution/measurement QA.
    c.execute(f"""CREATE TABLE measured AS SELECT o.*,t.entry_open,t.exit_open,
        t.label_status,t.label_reason,t.actual_delist_in_window,
        t.received_asset_claim FROM orders o
        JOIN (SELECT * FROM read_parquet('{ROOT}/data/interim/stage1g_targets/targets_5d.parquet')
          WHERE signal_date IN (DATE '2003-01-02',DATE '2003-01-03')) t
        USING(permno,signal_date)""")
    c.execute(f"COPY measured TO '{cache}/bounded_measurement.parquet' (FORMAT PARQUET)")
    witnesses = c.execute("SELECT * FROM measured WHERE planned_dollars<>0 AND entry_open>0 AND label_status='valid_entry_unresolved_exit_wealth' AND exit_open IS NULL ORDER BY signal_date,candidate").fetchdf()
    private = []
    for row in witnesses.to_dict('records'):
        permno = int(row['permno'])
        p = ROOT / f'data/interim/reconstruction_diagnostic_parts/part_{permno%32:02d}.parquet'
        actual = c.execute(f"""SELECT dlycaldt,dlyprc,dlyopen,dlyprcflg FROM read_parquet('{p}')
            WHERE permno=? AND dlycaldt BETWEEN ? AND DATE '2003-01-14' ORDER BY 1""",[permno,row['entry_date']]).fetchdf()
        events = c.execute(f"""SELECT count(*) FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdistributions.parquet')
            WHERE permno=? AND disexdt BETWEEN ? AND DATE '2003-01-14'""",[permno,row['signal_date']]).fetchone()[0]
        delists = c.execute(f"""SELECT count(*) FROM read_parquet('{ROOT}/data/interim/stage2a_events/stkdelists.parquet')
            WHERE permno=? AND (delistingdt BETWEEN ? AND DATE '2003-01-14'
                OR deldlydt BETWEEN ? AND DATE '2003-01-14'
                OR delamtdt BETWEEN ? AND DATE '2003-01-14')""",[permno]+[row['signal_date']]*3).fetchone()[0]
        exit_row = actual[pd.to_datetime(actual.dlycaldt) == pd.Timestamp(row['exit_date'])]
        assert len(exit_row)==1 and exit_row.dlyopen.isna().all() and exit_row.dlyprc.isna().all()
        assert events==0 and delists==0, 'Witness requires event share accounting review'
        following = c.execute('SELECT ridge,uni_reversal_5 FROM scores WHERE permno=? AND signal_date=DATE \'2003-01-14\'', [permno]).fetchone()
        private.append(dict(row,following_forecasts_available=following is not None and all(v is not None and np.isfinite(v) for v in following),
                            distribution_events=events,delisting_events=delists))
    (cache/'bounded_unresolved_witnesses.json').write_text(json.dumps(private,default=str,indent=2)+'\n')
    results = []
    for model in ('uni_reversal_5','ridge'):
        m = c.execute('SELECT * FROM measured WHERE candidate=?',[model]).fetchdf()
        w = witnesses[witnesses.candidate==model]
        results.append({'candidate':model,'original_bounded_signal_keys':len(m),
            'planned_entry_orders':int((m.planned_dollars!=0).sum()),
            'valid_entry_unresolved_exit_orders':len(w),
            'unresolved_decision_notional':float(w.planned_dollars.abs().sum()),
            'unresolved_entry_notional':float((w.signed_order_shares.abs()*w.entry_open).sum()),
            'earliest_unresolved_planned_exit':str(w.exit_date.min().date()) if len(w) else '',
            'unknown_residual_inventory_policy_required':len(w)>0,
            'performance_computed':False})
    pd.DataFrame(results).to_csv(out/'bounded_accounting_gate.csv',index=False)
    manifest={'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'signal_dates':['2003-01-02','2003-01-03'],
        'forecast_source':str(forecast.relative_to(ROOT)),
        'bounded_forecast_review_end':'2003-01-14',
        'original_rows_preserved':True,'outcomes_used_for_construction':False,
        'holdout_records_accessed':0,'wrds_queries':0,'raw_scanned':False,
        'performance_computed':False,'accounting_gate_passed':len(witnesses)==0,
        'blocker':'Uncertain residual inventory after unmeasured planned exit needs future capacity/borrow/sleeve replacement policy' if len(witnesses) else None,
        'counts':results}
    (cache/'bounded_qa_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    c.close(); print(json.dumps(manifest,indent=2))
