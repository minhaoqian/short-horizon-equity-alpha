"""Bounded source-verification audit. Intentionally does not construct features.

Daily zero-effect fields are tested as a candidate heuristic, not an approved
adapter. Event-history coverage is diagnostic only, never a feature mask.
"""
from pathlib import Path
import csv
import json
import duckdb

ROOT=Path(__file__).resolve().parents[2]


def looks_event_free(row):
    """Necessary daily-field screen; explicitly NOT sufficient verification."""
    return row['dlyfacprc']==1 and row['dlyorddivamt']==0 and row['dlynonorddivamt']==0 and row['dlydelflg']=='N'


def main():
    c=duckdb.connect()
    c.execute('SET threads=2')
    source=ROOT/'data/interim/reconstruction_diagnostic_parts/part_00.parquet'
    events=ROOT/'data/interim/stage1g_extraction/stkdistributions.parquet'
    selected=ROOT/'data/interim/stage1g_extraction/distribution_windows.parquet'
    c.execute(f'''CREATE TABLE sample AS SELECT * FROM read_parquet('{source}')
        WHERE dlycaldt BETWEEN DATE '2020-11-01' AND DATE '2021-04-30' ''')
    assert c.execute('SELECT count(*),count(DISTINCT(permno,dlycaldt)) FROM sample').fetchone()==(32010,32010)
    calendar=c.execute(f'''SELECT DISTINCT signal_date,signal_td FROM read_parquet(
        '{ROOT/'data/interim/target_boundary_audit_parts/part_00.parquet'}')
        WHERE signal_date BETWEEN DATE '2020-11-01' AND DATE '2021-04-30' ORDER BY 1''').fetchall()
    assert len(calendar)==124 and all(b[1]==a[1]+1 for a,b in zip(calendar,calendar[1:]))
    c.execute(f"CREATE VIEW selected AS SELECT DISTINCT permno FROM read_parquet('{selected}')")
    n,k,covered,covered_k,eligible,uncovered_eligible=c.execute('''SELECT count(*),count(DISTINCT sample.permno),
        count(*) FILTER(WHERE selected.permno IS NOT NULL),count(DISTINCT sample.permno) FILTER(WHERE selected.permno IS NOT NULL),
        count(*) FILTER(WHERE eligible),count(*) FILTER(WHERE eligible AND selected.permno IS NULL)
        FROM sample LEFT JOIN selected USING(permno)''').fetchone()
    bad_anchor=c.execute('''SELECT count(*) FROM sample WHERE dlyprcflg='TR' AND dlyprevprcflg='TR'
        AND dlydelflg='N' AND dlyretdurflg IN ('D1','D2','D3','D4','DU')
        AND abs(dlyprevprc-lag_prc)>1e-6''').fetchone()[0]
    # This is a small, prespecified source-definition corner-case census, not a
    # return-based sample or a full-panel feature query. Eight event records.
    c.execute(f'''CREATE TABLE probes AS SELECT * FROM read_parquet('{events}')
        WHERE disexdt BETWEEN DATE '1993-01-01' AND DATE '2025-12-31'
          AND coalesce(disfacpr,0)=0 AND coalesce(disfacshr,0)=0
          AND coalesce(disdivamt,0)=0 ORDER BY disexdt,permno,disseqnbr LIMIT 50''')
    probes=c.execute('SELECT * FROM probes').fetchdf().to_dict('records')
    details=[]
    for event in probes:
        permno=int(event['permno'])
        path=ROOT/f'data/interim/reconstruction_diagnostic_parts/part_{permno%32:02d}.parquet'
        cursor=c.execute(f'''SELECT permno,dlycaldt,dlyprcflg,dlydelflg,dlyfacprc,dlyorddivamt,
            dlynonorddivamt,dlyopen,dlyprc,dlyret,eligible FROM read_parquet('{path}')
            WHERE permno=? AND dlycaldt=?''',[permno,event['disexdt']])
        names=[col[0] for col in cursor.description]
        observed=cursor.fetchone()
        if observed is None:
            continue
        row=dict(zip(names,observed))
        row.update(disdetailtype=event['disdetailtype'],dispaymenttype=event['dispaymenttype'],
            daily_zero_effect_screen=looks_event_free(row))
        details.append(row)
    contradictions=[r for r in details if r['daily_zero_effect_screen'] and r['eligible']
        and r['dlyprcflg']=='TR' and r['dlyopen'] is not None and r['dlyopen']>0 and r['dlyprc']>0]
    report=[
        ('historical_sample_rows',n,k,'bounded partition 00; 2020-11-02 through 2021-04-30'),
        ('sample_rows_with_selected_event_history',covered,covered_k,'coverage diagnostic only; not a feature mask'),
        ('sample_rows_without_selected_event_history',n-covered,k-covered_k,'absence of returned events does not certify event-free'),
        ('sample_eligible_signal_keys',eligible,None,'close-date eligibility only; no target access'),
        ('sample_eligible_keys_without_selected_event_history',uncovered_eligible,None,'do not filter features using outcome-selected extraction coverage'),
        ('single_period_trade_previous_price_mismatches',bad_anchor,None,'numerical anchor check only'),
        ('zero_value_event_corner_case_records',len(details),len({r['permno'] for r in details}),'at most 50 prespecified records; no full daily panel scan'),
        ('eligible_event_days_passing_daily_zero_effect_screen',len(contradictions),len({r['permno'] for r in contradictions}),'event-free certification fails; methodological review required'),
    ]
    out=ROOT/'results/tables/stage2a';out.mkdir(exist_ok=True,parents=True)
    with (out/'historical_source_verification_qa.csv').open('w',newline='') as file:
        writer=csv.writer(file);writer.writerow(['check','observations','distinct_permnos','interpretation']);writer.writerows(report)
    local=ROOT/'data/interim/stage2a_historical_qa';local.mkdir(exist_ok=True)
    (local/'event_screen_counterexamples.json').write_text(json.dumps(details,default=str,indent=2)+'\n')
    manifest={'sample_rows':n,'sample_permnos':k,'calendar_dates':len(calendar),'duplicate_sample_keys':0,
        'sample_eligible_keys':eligible,'uncovered_sample_eligible_keys':uncovered_eligible,
        'zero_value_event_probe_records':len(details),'eligible_event_screen_counterexamples':len(contradictions),
        'historical_feature_gate_passed':False,'full_feature_computation_executed':False,
        'blocker':'Daily zero-effect fields cannot certify event-free; history coverage is outcome-selected.',
        'target_columns_read':False,'performance_metrics_computed':False}
    (local/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Reproducible aggregate SVG; no security identifiers, values or performance.
    fig=ROOT/'results/figures/stage2a';fig.mkdir(exist_ok=True,parents=True)
    bars=''
    for i,(name,value,color) in enumerate([('Existing selected event history',covered,'#276678'),
        ('Outside selected event history',n-covered,'#c98b35')]):
        y=85+i*72
        bars+=f'<text x="20" y="{y}" font-size="15">{name}: {value:,} rows</text><rect x="20" y="{y+10}" width="{600*value/n:.2f}" height="24" fill="{color}"/>'
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="275" viewBox="0 0 680 275">
      <rect width="680" height="275" fill="white"/>
      <text x="20" y="30" font-size="19">Bounded source audit: event-history coverage</text>
      <text x="20" y="54" font-size="13">32,010 cached rows; partition 00; Nov 2020-Apr 2021</text>
      {bars}<text x="20" y="230" font-size="13">Coverage is not a feature-availability rule or a performance result.</text>
      <text x="20" y="250" font-size="13">No full-panel feature computation. Stage 2A review gate remains open.</text></svg>'''
    (fig/'historical_event_history_coverage.svg').write_text(svg+'\n')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
