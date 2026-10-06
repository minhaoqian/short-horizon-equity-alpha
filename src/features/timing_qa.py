"""Effective-date/daily-term reconciliation; declaration chronology is QA only."""
from pathlib import Path
import csv
import json
from math import isfinite, prod
import duckdb

ROOT=Path(__file__).resolve().parents[2]


def close(a,b,tol=1e-6):
    return a is not None and b is not None and isfinite(float(a)) and isfinite(float(b)) and abs(float(a)-float(b))<=tol


def reconcile(events,daily):
    """No declaration/payment/target fields are consulted. Exact ex-date only.

    Compare all same-ex-date events jointly, avoiding double counting daily totals.
    Cash currency/asset mismatches cannot be repaired using later event values.
    """
    if daily is None:
        return False,'absent_contemporaneous_daily_row'
    if any(e['dispaymenttype'] not in ('USD','SS') for e in events):
        return False,'received_asset_property_or_currency_terms_unverified'
    ordinary=0.;nonordinary=0.;factors=[]
    for e in events:
        if e['dispaymenttype']=='USD':
            if e['disdivamt'] is None or e.get('dispermno') not in (None,0):
                return False,'cash_terms_unverified'
            if e.get('disordinaryflg')=='Y':ordinary+=float(e['disdivamt'])
            else:nonordinary+=float(e['disdivamt'])
        elif e['distype']=='FRS' and e['disdetailtype'] in ('STKSPL','STKDIV') and e.get('dispermno') in (None,0):
            if e['disfacpr'] is None or not close(e['disfacpr'],e['disfacshr']):
                return False,'split_terms_unverified'
        else:
            return False,'received_asset_or_rights_terms_unverified'
        if e['disfacpr'] is None:
            return False,'missing_event_factor'
        factors.append(1+float(e['disfacpr']))
    if not close(ordinary,daily['dlyorddivamt']) or not close(nonordinary,daily['dlynonorddivamt']):
        return False,'daily_cash_terms_mismatch'
    if not close(prod(factors),daily['dlyfacprc']):
        return False,'daily_factor_terms_mismatch'
    # A matching amount alone is not enough: source return identity also holds.
    p,p0= daily['dlyprc'],daily['dlyprevprc']
    if p is None or p0 is None or p<=0 or p0<=0:
        return False,'daily_price_anchor_unavailable'
    reconstructed=(p*daily['dlyfacprc']+ordinary+nonordinary)/p0-1
    if not close(reconstructed,daily['dlyret']):
        return False,'daily_return_identity_mismatch'
    return True,'effective_date_terms_and_return_identity_reconciled'


def main():
    c=duckdb.connect();c.execute('SET threads=2')
    source=ROOT/'data/interim/stage2a_events/stkdistributions.parquet'
    c.execute(f"CREATE VIEW events AS SELECT * FROM read_parquet('{source}')")
    names=[r[0] for r in c.execute('DESCRIBE events').fetchall()]
    bad=[dict(zip(names,r)) for r in c.execute('SELECT * FROM events WHERE disdeclaredt>disexdt ORDER BY disexdt,permno,disseqnbr').fetchall()]
    assert len(bad)==109
    cases={};details=[]
    for event in bad:
        ex=event['disexdt']
        ex=ex.date() if hasattr(ex,'date') else ex
        key=event['permno'],ex
        if key not in cases:
            group=[dict(zip(names,r)) for r in c.execute('SELECT * FROM events WHERE permno=? AND disexdt=?',list(key)).fetchall()]
            p=ROOT/f'data/interim/reconstruction_diagnostic_parts/part_{key[0]%32:02d}.parquet'
            cur=c.execute(f'''SELECT dlyprc,dlyprevprc,dlyfacprc,dlyorddivamt,dlynonorddivamt,dlyret,eligible
                FROM read_parquet('{p}') WHERE permno=? AND dlycaldt=?''',list(key))
            cols=[r[0] for r in cur.description];rows=cur.fetchall();assert len(rows)<=1
            daily=dict(zip(cols,rows[0])) if rows else None
            ok,reason=reconcile(group,daily)
            cases[key]=(ok,reason,bool(daily and daily['eligible']),daily is not None)
        ok,reason,eligible,has_daily=cases[key]
        details.append({'permno':key[0],'disexdt':str(key[1]),'disseqnbr':event['disseqnbr'],
            'reconciled':ok,'reason':reason,'eligible_exdate':eligible,'daily_row_exists':has_daily,
            'payment_type':event['dispaymenttype'],'event_type':event['distype']})
    # Additional bounded through-t eligible exposure (up to 60 market days).
    keys=list(cases)
    import pandas as pd
    c.register('case_keys',pd.DataFrame([{'permno':p,'exdate':d,'ambiguous':not cases[(p,d)][0]} for p,d in keys]))
    affected=[]
    for part in sorted({p%32 for p,d in keys}):
        path=ROOT/f'data/interim/reconstruction_diagnostic_parts/part_{part:02d}.parquet'
        # This is a conservative upper bound; exact global-window positions
        # are evaluated below instead of assuming 60 calendar days.
        affected+=c.execute(f'''SELECT DISTINCT d.permno,d.dlycaldt,k.exdate,k.ambiguous
            FROM read_parquet('{path}') d JOIN case_keys k ON d.permno=k.permno
            AND d.dlycaldt BETWEEN k.exdate AND k.exdate+INTERVAL 95 DAY WHERE d.eligible''').fetchall()
    calendar=[r[0] for r in c.execute(f'''SELECT DISTINCT signal_date FROM read_parquet(
        '{ROOT/'data/interim/target_boundary_audit_parts/part_*.parquet'}') ORDER BY 1''').fetchall()]
    index={d:i for i,d in enumerate(calendar)}
    exposure={};ambiguous_keys=set()
    for p,d,ex,amb in affected:
        if ex in index and 0<=index[d]-index[ex]<=59:
            exposure.setdefault((p,ex),set()).add(d)
            if amb:ambiguous_keys.add((p,d))
    out=ROOT/'results/tables/stage2a/timing_conflict_reconciliation.csv'
    with out.open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['status','reason','event_records','distinct_permnos','eligible_exdate_event_records','eligible_60date_signal_keys'])
        for ok,reason in sorted({(r['reconciled'],r['reason']) for r in details}):
            group=[r for r in details if r['reconciled']==ok and r['reason']==reason]
            group_keys={(r['permno'],__import__('datetime').date.fromisoformat(r['disexdt'])) for r in group}
            signals={(p,d) for p,ex in group_keys for d in exposure.get((p,ex),set())}
            w.writerow(['reconciled' if ok else 'timing_ambiguous',reason,len(group),len({r['permno'] for r in group}),sum(r['eligible_exdate'] for r in group),len(signals)])
    folder=ROOT/'data/interim/stage2a_events'
    (folder/'timing_conflict_details.json').write_text(json.dumps(details,indent=2)+'\n')
    report={'events_checked':109,'reconciled_event_records':sum(r['reconciled'] for r in details),
        'ambiguous_event_records':sum(not r['reconciled'] for r in details),
        'ambiguous_eligible_exdate_event_records':sum(not r['reconciled'] and r['eligible_exdate'] for r in details),
        'ambiguous_eligible_60date_signal_keys':len(ambiguous_keys),
        'unique_conflicting_security_dates':len(cases),'declaration_date_used_as_availability_gate':False,
        'target_values_or_status_read':False,'raw_scan_or_network_used':False}
    (folder/'timing_reconciliation_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
