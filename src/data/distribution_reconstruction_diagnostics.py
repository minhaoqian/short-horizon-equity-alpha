"""Cache-only Stage 1G diagnostics. No forward target, interpolation, or model."""
from pathlib import Path
import csv
import json
import duckdb

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/tables/stage1g'


def main():
    manifest = json.loads((ROOT / 'data/interim/reconstruction_diagnostic_manifest.json').read_text())
    assert manifest['cache_schema_version'] == 1
    for name, expected in manifest['inputs'].items():
        stat = (ROOT / name).stat()
        assert expected == {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}, name
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='4GB'")
    con.execute(f"SET temp_directory='{ROOT / '.duckdb_tmp'}'")
    con.execute(f"CREATE VIEW x AS SELECT * FROM read_parquet('{ROOT / 'data/interim/reconstruction_diagnostic_parts/*.parquet'}')")
    con.execute('''CREATE VIEW r AS WITH v AS (SELECT *,
      (dlyprc*dlyfacprc+dlynonorddivamt)/NULLIF(dlyprevprc,0)-1 source_rx,
      (dlyprc*dlyfacprc+dlynonorddivamt+dlyorddivamt)/NULLIF(dlyprevprc,0)-1 source_rt,
      ((dlyprc/dlycumfacpr)*(dlyfacprc*dlycumfacpr/lag_fac)
        +dlynonorddivamt/lag_fac)/NULLIF(dlyprevprc/lag_fac,0)-1 cumulative_rx,
      ((dlyprc/dlycumfacpr)*(dlyfacprc*dlycumfacpr/lag_fac)
        +(dlynonorddivamt+dlyorddivamt)/lag_fac)/NULLIF(dlyprevprc/lag_fac,0)-1 cumulative_rt
      FROM x)
    SELECT *, ABS(source_rx-dlyretx) source_rx_error, ABS(source_rt-dlyret) source_rt_error,
      CASE WHEN dlyprevprc>0.0000005 THEN 0.0000005+
        (ABS(dlyprc)*0.0000005+ABS(dlyfacprc)*0.0000005+0.0000005*0.0000005
          +0.0000005+ABS(1+source_rx)*0.0000005)/(dlyprevprc-0.0000005) END rx_rounding_bound,
      CASE WHEN dlyprevprc>0.0000005 THEN 0.0000005+
        (ABS(dlyprc)*0.0000005+ABS(dlyfacprc)*0.0000005+0.0000005*0.0000005
          +0.000001+ABS(1+source_rt)*0.0000005)/(dlyprevprc-0.0000005) END rt_rounding_bound
      FROM v''')
    def export(name, query):
        con.execute(f"COPY ({query}) TO '{OUT / name}' (HEADER, FORMAT CSV)")
    assert con.execute('SELECT COUNT(*),COUNT(reconstructed),COUNT(*) FILTER(WHERE eligible) FROM x').fetchone() == (64959561,64056350,6699101)
    scopes = {
      'original_comparable': 'reconstructed IS NOT NULL',
      'eligible_original_comparable': 'eligible AND reconstructed IS NOT NULL',
      'eligible_all': 'eligible',
      'eligible_nonordinary': 'eligible AND dlynonorddivamt<>0',
      'eligible_missing_lag': 'eligible AND reconstructed IS NULL',
    }
    records = []
    for scope, condition in scopes.items():
        print('Checking', scope, flush=True)
        for method in ['source', 'cumulative']:
            for kind, observed in [('rx','dlyretx'),('rt','dlyret')]:
                error = f'ABS({method}_{kind}-{observed})'
                q = f'''SELECT COUNT(*) observation_rows, COUNT({method}_{kind}) reconstructed_rows,
                  MAX({error}) max_abs_error, QUANTILE_CONT({error},0.99) p99_abs_error,
                  MEDIAN({error}) median_abs_error, COUNT(*) FILTER(WHERE {error}>{kind}_rounding_bound+1e-10) outside_rounding_bound,
                  COUNT(*) FILTER(WHERE {method}_{kind} IS NOT NULL AND NOT isfinite({method}_{kind})) nonfinite_rows
                  FROM r WHERE {condition}'''
                cursor = con.execute(q)
                record = dict(zip([d[0] for d in cursor.description],cursor.fetchone()))
                record.update(scope=scope,method=method,return_type=kind)
                records.append(record)
    with (OUT/'distribution_reconstruction_summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    export('distribution_reconstruction_integrity.csv', '''SELECT COUNT(*) original_comparable_rows,
      COUNT(*) FILTER(WHERE dlyprevprc IS DISTINCT FROM lag_prc) source_lag_price_disagreements,
      COUNT(*) FILTER(WHERE dlyprc<0 OR dlyprevprc<=0 OR dlyfacprc<0) invalid_signs,
      COUNT(*) FILTER(WHERE lag_fac<=0 OR dlycumfacpr<=0) invalid_cumulative_factors,
      COUNT(*) FILTER(WHERE ABS(dlyprc-ROUND(dlyprc,6))>1e-9 OR ABS(dlyprevprc-ROUND(dlyprevprc,6))>1e-9
        OR ABS(dlyfacprc-ROUND(dlyfacprc,6))>1e-9 OR ABS(dlynonorddivamt-ROUND(dlynonorddivamt,6))>1e-9
        OR ABS(dlyorddivamt-ROUND(dlyorddivamt,6))>1e-9 OR ABS(dlyret-ROUND(dlyret,6))>1e-9
        OR ABS(dlyretx-ROUND(dlyretx,6))>1e-9) incompatible_six_decimal_precision,
      MAX(ABS(source_rx-cumulative_rx)) max_basis_rx_difference,
      MAX(ABS(source_rt-cumulative_rt)) max_basis_rt_difference
      FROM r WHERE reconstructed IS NOT NULL''')
    export('eligible_nonordinary_reconstruction.csv', '''SELECT permno,dlycaldt,dlyretdurflg,
      dlyprc,dlyprevprc,dlyfacprc,dlycumfacpr,lag_fac,dlynonorddivamt,dlyorddivamt,
      dlyretx,dlyret,source_rx,source_rt,source_rx_error,source_rt_error,
      cumulative_rx,cumulative_rt,rx_rounding_bound,rt_rounding_bound
      FROM r WHERE eligible AND dlynonorddivamt<>0 ORDER BY permno,dlycaldt''')
    export('distribution_reconstruction_rounding_examples.csv', '''SELECT permno,dlycaldt,eligible,
      dlyprc,dlyprevprc,dlyfacprc,dlyretx,dlyret,source_rx_error,source_rt_error,rx_rounding_bound,rt_rounding_bound
      FROM r WHERE reconstructed IS NOT NULL ORDER BY source_rt_error DESC LIMIT 100''')
    # Small subset: current day and three preceding trading dates, no raw scan.
    con.execute("CREATE TEMP TABLE missing AS SELECT * FROM r WHERE eligible AND reconstructed IS NULL")
    con.execute('CREATE TEMP TABLE calendar AS SELECT dlycaldt, ROW_NUMBER() OVER(ORDER BY dlycaldt) td FROM (SELECT DISTINCT dlycaldt FROM x)')
    con.execute(f"CREATE TEMP TABLE names AS SELECT * FROM read_csv_auto('{ROOT / 'data/raw/crsp_names_history.csv'}')")
    con.execute('''CREATE TEMP TABLE context AS SELECT e.permno event_permno,e.dlycaldt event_date,
      e.dlyretdurflg event_duration,e.dlyprevprc event_previous_price, cc.td-cp.td trading_days_before,
      cp.dlycaldt expected_date,d.*, n.tradingstatusflg,n.secinfostartdt,n.secinfoenddt,
      n.securitytype,n.securitysubtype,n.sharetype,n.usincflg,n.issuertype,n.primaryexch
      FROM missing e JOIN calendar cc ON cc.dlycaldt=e.dlycaldt
      JOIN calendar cp ON cp.td BETWEEN cc.td-3 AND cc.td
      LEFT JOIN x d ON d.permno=e.permno AND d.dlycaldt=cp.dlycaldt
      LEFT JOIN names n ON n.permno=e.permno AND cp.dlycaldt BETWEEN n.secinfostartdt AND n.secinfoenddt''')
    export('missing45_full_context.csv','SELECT * FROM context ORDER BY event_permno,event_date,trading_days_before')
    export('missing45_source_anchor.csv', '''SELECT e.permno,e.dlycaldt,e.dlyretdurflg,
      c.expected_date source_price_date,c.dlyprc source_observed_price,e.dlyprevprc,
      c.dlycumfacpr source_cumulative_factor,e.lag_fac lag_row_cumulative_factor,
      c.dlycumfacpr=e.lag_fac source_lag_factor_matches,
      c.dlyprc=e.dlyprevprc source_price_matches,
      e.source_rx_error,e.source_rt_error,
      c.trading_days_before,e.dlyfacprc,e.dlynonorddivamt,e.dlyorddivamt
      FROM missing e JOIN context c ON c.event_permno=e.permno AND c.event_date=e.dlycaldt
      AND c.trading_days_before=CASE e.dlyretdurflg WHEN 'P1' THEN 2 WHEN 'P2' THEN 3 END
      ORDER BY e.permno,e.dlycaldt''')
    export('missing45_causes.csv', '''SELECT event_duration,COUNT(*) observation_rows,
      COUNT(*) FILTER(WHERE permno IS NULL) no_previous_day_row,
      COUNT(*) FILTER(WHERE permno IS NOT NULL AND dlyprc IS NULL AND dlyprcflg='MP') previous_row_missing_price,
      COUNT(*) FILTER(WHERE tradingstatusflg IN ('H','S')) documented_halt_or_suspension,
      COUNT(*) FILTER(WHERE tradingstatusflg='A') active_metadata,
      COUNT(*) FILTER(WHERE dlyfacprc<>1 OR dlyorddivamt<>0 OR dlynonorddivamt<>0) previous_day_corporate_event,
      COUNT(*) FILTER(WHERE dlyopen IS NULL AND COALESCE(dlyvol,0)=0) missing_open_zero_volume,
      COUNT(*) FILTER(WHERE dlydelflg='Y') previous_day_delisting
      FROM context WHERE trading_days_before=1 GROUP BY 1 ORDER BY 1''')
    export('missing45_history_integrity.csv', '''SELECT COUNT(*) observation_rows,
      COUNT(*) FILTER(WHERE x.lag_date<>c.expected_date) lag_not_previous_trading_date,
      COUNT(*) FILTER(WHERE x.dlyfacprc<>1 OR x.dlyorddivamt<>0 OR x.dlynonorddivamt<>0) current_corporate_events,
      COUNT(*) FILTER(WHERE NOT EXISTS(SELECT 1 FROM context z WHERE z.event_permno=x.permno AND z.event_date=x.dlycaldt
        AND z.trading_days_before=CASE x.dlyretdurflg WHEN 'P1' THEN 2 ELSE 3 END AND z.dlyprc=x.dlyprevprc)) unmatched_source_anchor,
      COUNT(*) FILTER(WHERE EXISTS(SELECT 1 FROM context z WHERE z.event_permno=x.permno AND z.event_date=x.dlycaldt
        AND z.trading_days_before>=1 AND z.trading_days_before<CASE x.dlyretdurflg WHEN 'P1' THEN 2 ELSE 3 END
        AND z.dlyprc IS NOT NULL)) intervening_valid_price,
      COUNT(*) FILTER(WHERE NOT EXISTS(SELECT 1 FROM context z WHERE z.event_permno=x.permno AND z.event_date=x.dlycaldt
        AND z.trading_days_before=CASE x.dlyretdurflg WHEN 'P1' THEN 2 ELSE 3 END AND z.permno IS NOT NULL)) no_preexisting_security_row
      FROM missing x JOIN context c ON c.event_permno=x.permno AND c.event_date=x.dlycaldt AND c.trading_days_before=1''')
    assert all(rec['reconstructed_rows']==rec['observation_rows'] for rec in records)
    assert con.execute("SELECT COUNT(*) FROM context c JOIN missing e ON c.event_permno=e.permno AND c.event_date=e.dlycaldt WHERE c.trading_days_before=CASE e.dlyretdurflg WHEN 'P1' THEN 2 ELSE 3 END AND c.dlycumfacpr IS DISTINCT FROM e.lag_fac").fetchone()[0]==0
    assert all(rec['outside_rounding_bound']==0 and rec['nonfinite_rows']==0 for rec in records)
    assert con.execute('SELECT COUNT(*) FROM missing').fetchone()[0]==45
    print('Definition-grounded validation complete', flush=True)

if __name__ == '__main__':
    main()
