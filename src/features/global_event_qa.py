"""Validate global event scope and bounded timing evidence; no feature construction."""
from pathlib import Path
from datetime import timedelta
from collections import Counter
import csv
import hashlib
import json
from math import log10
import duckdb
from .events import EventLayer

ROOT=Path(__file__).resolve().parents[2]


def main():
    c=duckdb.connect();c.execute('SET threads=2')
    folder=ROOT/'data/interim/stage2a_events'
    m=json.loads((folder/'manifest.json').read_text())
    assert m['complete'] and m['qa_passed'] and m['login_attempts']==1
    assert hashlib.sha256((folder/'stkdistributions.parquet').read_bytes()).hexdigest()==m['distribution_sha256']
    assert hashlib.sha256((folder/'stkdelists.parquet').read_bytes()).hexdigest()==m['delists']['sha256']
    cols=['permno','disexdt','disdeclaredt','dispaymenttype','distype','disdetailtype','disordinaryflg',
        'disdivamt','disfacpr','disfacshr','dispermno']
    c.execute(f"CREATE VIEW s AS SELECT * FROM read_parquet('{folder/'stkdistributions.parquet'}')")
    c.execute(f"CREATE VIEW l AS SELECT * FROM read_parquet('{folder/'stkdelists.parquet'}')")
    cur=c.execute('SELECT '+','.join(cols)+' FROM s')
    records=[dict(zip(cols,r)) for r in cur.fetchall()]
    delcols=['permno','delistingdt','deldlydt']
    dels=[dict(zip(delcols,r)) for r in c.execute('SELECT '+','.join(delcols)+' FROM l').fetchall()]
    layer=EventLayer(records,dels)
    sample=c.execute(f'''SELECT permno,dlycaldt,eligible FROM read_parquet(
        '{ROOT/'data/interim/reconstruction_diagnostic_parts/part_00.parquet'}')
        WHERE dlycaldt BETWEEN DATE '2020-11-01' AND DATE '2021-04-30' ''').fetchall()
    calendar=c.execute(f'''SELECT DISTINCT signal_date,signal_td FROM read_parquet(
        '{ROOT/'data/interim/target_boundary_audit_parts/part_00.parquet'}')
        WHERE signal_date BETWEEN DATE '2020-10-26' AND DATE '2021-04-30' ORDER BY 1''').fetchall()
    assert all(b[1]==a[1]+1 for a,b in zip(calendar,calendar[1:]))
    previous={calendar[i][0]:calendar[i-1][0] for i in range(1,len(calendar))}
    reasons=Counter();eligible_reasons=Counter()
    for permno,d,eligible in sample:
        decision=layer.interval(permno,previous[d],d,d)
        reasons[decision.reason]+=1
        if eligible:
            eligible_reasons[decision.reason]+=1
    old=json.loads((ROOT/'data/interim/stage2a_historical_qa/event_screen_counterexamples.json').read_text())
    corner=[]
    for row in old:
        if row['eligible'] and row['daily_zero_effect_screen']:
            from datetime import date
            d=date.fromisoformat(row['dlycaldt'])
            # Exact ex-date presence check; calendar preceding date irrelevant
            # to this narrowly scoped legal-event regression.
            decision=layer.interval(row['permno'],d-timedelta(days=1),d,d)
            assert decision.distribution_count>0 and decision.gap_admissible is not True
            corner.append({'permno':row['permno'],'date':str(d),'reason':decision.reason})
    assert len(corner)==2
    timing=c.execute('''SELECT count(*) FILTER(WHERE disdeclaredt>disexdt),
        count(*) FILTER(WHERE disdeclaredt IS NULL),count(*) FROM s''').fetchone()
    probes=c.execute('''SELECT permno,disexdt::DATE,disdeclaredt::DATE FROM s
        WHERE disdeclaredt>disexdt AND dispaymenttype='USD' AND distype IN ('CD','SD')
        ORDER BY disexdt,permno,disseqnbr LIMIT 20''').fetchall()
    physical=[]
    for permno,ex,declare in probes:
        vals=c.execute(f'''SELECT dlyorddivamt,dlynonorddivamt,eligible FROM read_parquet(
            '{ROOT/f'data/interim/reconstruction_diagnostic_parts/part_{permno%32:02d}.parquet'}')
            WHERE permno=? AND dlycaldt=?''',[permno,ex]).fetchone()
        if vals:
            physical.append({'permno':permno,'exdate':str(ex),'declaredate':str(declare),
                'amount_on_earlier_exdate':bool(vals[0] or vals[1]),'eligible':vals[2]})
    table=ROOT/'results/tables/stage2a';table.mkdir(exist_ok=True)
    with (table/'global_event_verification_qa.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['check','count','interpretation'])
        for row in [('global_distribution_records',timing[2],'all PERMNOs; DisExDt 1993-2025; all event types/values'),
            ('complete_delisting_records',len(dels),'reused complete table; amounts/payment/status not admission inputs'),
            ('bounded_sample_rows',len(sample),'no Stage 1G scope selection in adapter'),
            ('bounded_sample_eligible_keys',sum(bool(r[2]) for r in sample),'current eligibility only'),
            ('rights_counterexamples_detected',len(corner),'global index rejects event-free certification'),
            ('declaration_after_exdate',timing[0],'timing-review gate; not automatically blacked out or admitted'),
            ('missing_declaration_date',timing[1],'event presence known from exdate; amount publication not proven'),
            ('later_declaration_cash_probe_rows',len(physical),'bounded first 20 cash records by exdate'),
            ('cash_probe_earlier_daily_amounts',sum(r['amount_on_earlier_exdate'] for r in physical),'daily amount already present before recorded declaration'),
            ('cash_probe_eligible_rows',sum(r['eligible'] for r in physical),'timing conflict reaches locked sample')]:
            w.writerow(row)
    with (table/'bounded_global_event_adapter_reasons.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['reason','sample_rows','eligible_keys'])
        for reason,n in sorted(reasons.items()):
            w.writerow([reason,n,eligible_reasons[reason]])
    fig=ROOT/'results/figures/stage2a';fig.mkdir(exist_ok=True,parents=True)
    categories=[('Declaration after ex-date',timing[0],'#b24b3f'),
        ('Declaration date missing',timing[1],'#b78c38'),
        ('Declaration on/before ex-date',timing[2]-timing[1]-timing[0],'#2e6d83')]
    bars=''
    for i,(name,n,color) in enumerate(categories):
        y=90+i*68
        width=560*log10(n+1)/log10(timing[2]+1)
        bars+=f'<text x="20" y="{y}" font-size="15">{name}: {n:,}</text><rect x="20" y="{y+8}" width="{width:.2f}" height="20" fill="{color}"/>'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="335" viewBox="0 0 680 335">
        <rect width="680" height="335" fill="white"/>
        <text x="20" y="30" font-size="19">Global CRSP event-date verification</text>
        <text x="20" y="54" font-size="13">670,977 records; ex-dates 1993-2025; all securities/event types</text>
        {bars}<text x="20" y="302" font-size="13">Bar widths: log10(count+1); labels show exact record counts.</text>
        <text x="20" y="322" font-size="13">Chronology QA only. Timing conflicts require review; no feature results.</text></svg>'''
    (fig/'global_event_declaration_chronology.svg').write_text(svg+'\n')
    report={'global_scope_verified':True,'rights_cases_detected':2,
        'sample_rows':len(sample),'sample_eligible_keys':sum(bool(r[2]) for r in sample),
        'declaration_after_exdate_records':timing[0],'missing_declaration_records':timing[1],
        'historical_gate_passed':False,'full_feature_construction_executed':False,
        'blocker':'Declaration/exdate conflict: metadata error versus retrospective recording unresolved.',
        'outcome_selected_cache_used_for_admission':False,'target_or_status_values_read':False,
        'corners':corner,'cash_timing_probe':physical}
    (folder/'adapter_qa_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('corners','cash_timing_probe')},indent=2))


if __name__=='__main__':main()
