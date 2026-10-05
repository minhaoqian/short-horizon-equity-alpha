"""Frozen five-day wealth ledger. Outputs are labels/outcome metadata, never predictors."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
import duckdb

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / 'data/interim/stage1g_extraction'
OUT = ROOT / 'data/interim/stage1g_targets'
EXPECTED = {
    'measurable_ordinary_event_adjusted': 6673134,
    'missing_entry_measurement': 7596,
    'measurable_cash_only_delisting': 3616,
    'valid_entry_unresolved_exit_wealth': 4087,
    'administrative_right_censoring': 8686,
    'other_unresolved_corporate_action': 1982,
}


def wealth_target(entry_open, security_value, cash_claims):
    if entry_open <= 0:
        raise ValueError('No observed positive entry opening')
    return (security_value + cash_claims) / entry_open - 1


def event_ledger(entry, exit_, events):
    """Testable grouped-date ledger; amounts expressed per pre-event owned share."""
    quantity, cash = 1.0, 0.0
    for date in sorted({e['date'] for e in events if entry < e['date'] <= exit_}):
        group = [e for e in events if e['date'] == date]
        cash += quantity * sum(e.get('cash', 0) for e in group)
        for event in group:
            quantity *= event.get('share_multiplier', 1)
    return quantity, cash


def main():
    OUT.mkdir(exist_ok=True)
    manifest = json.loads((EX / 'download_manifest.json').read_text())
    assert manifest['complete'] and manifest['extraction_qa']['passed']
    for info in manifest['outputs'].values():
        assert hashlib.sha256((EX / info['file']).read_bytes()).hexdigest() == info['sha256']
    c = duckdb.connect()
    c.execute('SET threads=2')
    c.execute("SET memory_limit='4GB'")
    c.execute(f"CREATE VIEW e AS SELECT * FROM read_parquet('{EX / 'event_resolution_cases.parquet'}')")
    c.execute(f"CREATE VIEW s AS SELECT * FROM read_parquet('{EX / 'stkdistributions.parquet'}')")
    c.execute(f"CREATE VIEW daily AS SELECT * FROM read_parquet('{ROOT / 'data/interim/reconstruction_diagnostic_daily.parquet'}')")
    # Daily fields use previous-price/share basis; explicit event sums cross-check
    # that basis. Terminal cash is a separate replacement asset, counted once.
    c.execute('''CREATE TABLE ev AS SELECT e.permno,e.signal_date,e.entry_date,e.exit_date,e.deldlydt,
        s.disexdt::DATE event_date,s.disseqnbr,s.disdivamt,s.disfacshr,s.dispaymenttype,
        s.disdetailtype,(s.dispaymenttype='SS' AND s.distype='FRS'
          AND s.disdetailtype IN ('STKSPL','STKDIV')) split,
        (s.disexdt=e.deldlydt AND e.resolution='resolved_cash_claim_by_exit') terminal
        FROM e JOIN s ON e.permno=s.permno AND s.disexdt>e.entry_date AND s.disexdt<=e.exit_date
        WHERE e.resolved AND (e.special_review OR e.resolution='resolved_cash_claim_by_exit')''')
    c.execute('''CREATE TABLE dates AS SELECT permno,signal_date,event_date,
        product(1+disfacshr) FILTER(WHERE split) multiplier,
        sum(disdivamt) FILTER(WHERE dispaymenttype='USD') cash_amount,
        bool_or(terminal) terminal
        FROM ev GROUP BY ALL''')
    c.execute('''CREATE TABLE led AS SELECT *,coalesce(product(coalesce(multiplier,1)) OVER(
        PARTITION BY permno,signal_date ORDER BY event_date ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),1) q_before
        FROM dates''')
    # Stop rather than coercing a schema/accounting contradiction into a label.
    bad = c.execute('''SELECT l.*,d.dlyorddivamt,d.dlynonorddivamt,d.dlyretdurflg FROM led l
        LEFT JOIN daily d ON d.permno=l.permno AND d.dlycaldt=l.event_date
        WHERE cash_amount IS NOT NULL AND NOT terminal AND (
          d.dlyretdurflg NOT IN ('D1','D2','D3','D4','DU') OR d.dlyretdurflg IS NULL
          OR d.dlyorddivamt IS NULL OR d.dlynonorddivamt IS NULL
          OR abs(cash_amount-d.dlyorddivamt-d.dlynonorddivamt)>0.00001)''').fetchall()
    if bad:
        raise RuntimeError(f'Frozen cash-basis contradiction: {len(bad)} observation/event pairs; first={bad[0]}')
    c.execute('''CREATE TABLE totals AS SELECT permno,signal_date,
        product(coalesce(multiplier,1)) quantity,
        sum(q_before*coalesce(cash_amount,0)) cash_claims
        FROM led GROUP BY ALL''')
    uncovered_cash = c.execute('''SELECT count(*) FROM e JOIN daily d
        ON d.permno=e.permno AND d.dlycaldt>e.entry_date AND d.dlycaldt<=e.exit_date
        WHERE e.resolved AND e.special_review AND e.resolution<>'resolved_cash_claim_by_exit'
          AND (d.dlyorddivamt<>0 OR d.dlynonorddivamt<>0)
          AND NOT EXISTS (SELECT 1 FROM led l WHERE l.permno=e.permno
            AND l.signal_date=e.signal_date AND l.event_date=d.dlycaldt AND l.cash_amount IS NOT NULL)''').fetchone()[0]
    assert uncovered_cash == 0, ('unmatched entitled cash dates', uncovered_cash)
    counts = {}
    for i in range(32):
        print(f'Constructing target partition {i+1}/32', flush=True)
        part = ROOT / f'data/interim/target_boundary_audit_parts/part_{i:02d}.parquet'
        c.execute(f"CREATE TEMP VIEW a AS SELECT * FROM read_parquet('{part}')")
        c.execute('''CREATE TEMP TABLE p AS SELECT a.*,e.resolution,e.resolved,
            coalesce(e.special_review,false) special_review,
            e.expected_quantity,e.actual_delist_in_window,e.received_assets,
            CASE WHEN a.right_censored THEN 'administrative_right_censoring'
              WHEN NOT coalesce(a.entry_open>0 AND isfinite(a.entry_open),false) THEN 'missing_entry_measurement'
              WHEN e.resolution='resolved_cash_claim_by_exit' THEN 'measurable_cash_only_delisting'
              WHEN NOT coalesce(a.exit_open>0 AND isfinite(a.exit_open),false) THEN 'valid_entry_unresolved_exit_wealth'
              WHEN e.resolved=false THEN 'other_unresolved_corporate_action'
              ELSE 'measurable_ordinary_event_adjusted' END label_status
            FROM a LEFT JOIN e USING(permno,signal_date)''')
        # Cash-only ordinary paths have no quantity transformation. Their
        # complete single-period daily amount fields identify entitlement dates.
        c.execute('''CREATE TEMP TABLE ordinary_cash AS SELECT p.permno,p.signal_date,
            sum(d.dlyorddivamt) cash_claims,
            count(*) FILTER(WHERE d.dlynonorddivamt<>0 OR d.dlyfacprc<>1
              OR d.dlyretdurflg NOT IN ('D1','D2','D3','D4','DU')) invalid_cash_basis
            FROM p JOIN daily d ON d.permno=p.permno AND d.dlycaldt>p.entry_date AND d.dlycaldt<=p.exit_date
            WHERE p.label_status='measurable_ordinary_event_adjusted' AND NOT p.special_review
              AND d.dlyorddivamt<>0 GROUP BY p.permno,p.signal_date''')
        assert c.execute('SELECT count(*) FROM ordinary_cash WHERE invalid_cash_basis>0').fetchone()[0] == 0
        c.execute('''CREATE TEMP TABLE valued AS SELECT p.*,
            CASE WHEN label_status='measurable_cash_only_delisting' THEN 0.0
              WHEN label_status='measurable_ordinary_event_adjusted' THEN coalesce(t.quantity,1.0)*exit_open END security_value,
            CASE WHEN label_status IN ('measurable_ordinary_event_adjusted','measurable_cash_only_delisting')
              THEN CASE WHEN special_review OR label_status='measurable_cash_only_delisting'
                THEN coalesce(t.cash_claims,0.0) ELSE coalesce(o.cash_claims,0.0) END END cash_claims,
            CASE WHEN label_status='measurable_cash_only_delisting' THEN 0.0
              WHEN label_status='measurable_ordinary_event_adjusted' THEN coalesce(t.quantity,1.0) END terminal_parent_quantity
            FROM p LEFT JOIN totals t USING(permno,signal_date) LEFT JOIN ordinary_cash o USING(permno,signal_date)''')
        assert c.execute('''SELECT count(*) FROM valued WHERE label_status='measurable_cash_only_delisting'
            AND (cash_claims<=0 OR NOT actual_delist_in_window)''').fetchone()[0] == 0
        assert c.execute('''SELECT count(*) FROM valued WHERE special_review AND label_status='measurable_ordinary_event_adjusted'
            AND abs(terminal_parent_quantity-expected_quantity)>1e-10''').fetchone()[0] == 0
        c.execute('''CREATE TEMP TABLE target AS SELECT permno,signal_date,entry_date,exit_date,
            (security_value+cash_claims)/entry_open-1 target_5d,
            label_status,CASE WHEN label_status='administrative_right_censoring' THEN 'planned_exit_beyond_available_calendar'
              WHEN label_status='missing_entry_measurement' THEN 'observed_entry_open_unavailable'
              WHEN label_status='measurable_cash_only_delisting' THEN 'independently_measurable_cash_settlement'
              WHEN label_status='measurable_ordinary_event_adjusted' THEN 'verified_openings_and_distribution_accounting'
              ELSE resolution END label_reason,
            entry_open,exit_open,terminal_parent_quantity,security_value,cash_claims,
            daily_delist_flag,entry_delist_flag,interior_delist_flag,exit_delist_flag,
            entry_ordinary,interior_ordinary,exit_ordinary,entry_nonordinary,interior_nonordinary,exit_nonordinary,
            period_factor_event,cumulative_factor_event,interior_missing_price,aggregated_event_interval,
            missing_event_fields,coalesce(actual_delist_in_window,false) actual_delist_in_window,
            coalesce(received_assets,0)>0 received_asset_claim,
            'outcome_metadata_not_predictors' metadata_role
            FROM valued''')
        for k, n in c.execute('SELECT label_status,count(*) FROM target GROUP BY 1').fetchall():
            counts[k] = counts.get(k, 0) + n
        c.execute(f"COPY target TO '{OUT / f'part_{i:02d}.parquet'}' (FORMAT PARQUET)")
        for table in ['target','valued','ordinary_cash','p']:
            c.execute(f'DROP TABLE {table}')
        c.execute('DROP VIEW a')
    assert counts == EXPECTED, (counts, EXPECTED)
    c.execute(f"CREATE VIEW targets AS SELECT * FROM read_parquet('{OUT}/part_*.parquet')")
    qa = c.execute('''SELECT count(*),count(DISTINCT(permno,signal_date)),count(target_5d),
        count(*) FILTER(WHERE label_reason IS NULL OR label_reason=''),
        count(*) FILTER(WHERE (target_5d IS NOT NULL) IS DISTINCT FROM (label_status IN
          ('measurable_ordinary_event_adjusted','measurable_cash_only_delisting'))),
        count(*) FILTER(WHERE target_5d IS NOT NULL AND NOT isfinite(target_5d)),
        max(abs((target_5d+1)*entry_open-security_value-cash_claims))
        FROM targets''').fetchone()
    assert qa[:6] == (6699101,6699101,6676750,0,0,0), qa
    assert qa[6] < 1e-8, qa
    assert c.execute(f'''SELECT count(*) FROM targets t FULL OUTER JOIN
        read_parquet('{ROOT / 'data/interim/target_boundary_audit_parts'}/*.parquet') a
        USING(permno,signal_date) WHERE t.permno IS NULL OR a.permno IS NULL
        OR t.entry_date IS DISTINCT FROM a.entry_date OR t.exit_date IS DISTINCT FROM a.exit_date''').fetchone()[0] == 0
    c.execute(f"COPY targets TO '{OUT / 'targets_5d.parquet'}' (FORMAT PARQUET)")
    report = {'rows':qa[0],'unique_keys':qa[1],'numeric_labels':qa[2],'counts':counts,
      'numeric_coverage_pct':100*qa[2]/qa[0],'wealth_identity_max_error':qa[6],
      'qa_passed':True,'predictor_columns':[], 'metadata_role':'labels_and_outcomes_only',
      'sources':['target_boundary_audit_parts','event_resolution_cases.parquet','reconstruction_diagnostic_daily.parquet','stkdistributions.parquet'],
      'wrds_queries':0,'raw_daily_scanned':False,
      'constructed_at_utc':datetime.now(timezone.utc).isoformat(),
      'entitlement':'entry_date < DisExDt <= exit_date',
      'cash_convention':'no reinvestment; zero interest; established fixed receivables at face value',
      'unmatched_entitled_cash_dates':uncovered_cash,
      'eligible_keys_and_planned_dates_preserved':True,
      'input_fingerprints':{str(p.relative_to(ROOT)):{'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}
        for p in [EX/'event_resolution_cases.parquet', EX/'stkdistributions.parquet',
          ROOT/'data/interim/reconstruction_diagnostic_daily.parquet',
          *sorted((ROOT/'data/interim/target_boundary_audit_parts').glob('*.parquet'))]}}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__ == '__main__':
    main()
