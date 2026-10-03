"""Stage 1G coverage and discrepancy attribution; no target or model construction.

Reuses cumulative factors and the saved top-500 errors. Caches selected daily
fields locally. Missingness predicates overlap; primary_reason uses the stated
CASE order to produce a partition, not a causal hierarchy. Eligibility is at the
observation date, not at an earlier signal date or over a holding window.
"""
from pathlib import Path
import csv
import json
import duckdb

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/tables/stage1g'
CACHE = ROOT / 'data/interim/reconstruction_diagnostic_daily.parquet'


def main():
    # Bump the version when cached row construction or eligibility changes.
    inputs = ['data/raw/crsp_daily_1993_2025.csv.gz',
              'data/interim/crsp_cumfac_1993_2025.parquet',
              'data/raw/crsp_names_history.csv']
    fingerprint = {'cache_schema_version': 1, 'inputs': {
        name: {'size': (ROOT / name).stat().st_size,
               'mtime_ns': (ROOT / name).stat().st_mtime_ns} for name in inputs}}
    manifest = ROOT / 'data/interim/reconstruction_diagnostic_manifest.json'
    if manifest.exists():
        if json.loads(manifest.read_text()) != fingerprint:
            raise RuntimeError('Diagnostic inputs changed; rebuild caches in a fresh location.')
    elif CACHE.exists():
        raise RuntimeError('Existing cache has no provenance manifest; rebuild in a fresh location.')
    else:
        manifest.write_text(json.dumps(fingerprint, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ROOT / 'data/interim/reconstruction_diagnostic.duckdb'))
    con.execute("SET memory_limit='6GB'")
    con.execute("SET threads=1")
    con.execute(f"SET temp_directory='{ROOT / '.duckdb_tmp'}'")
    con.execute('SET preserve_insertion_order=false')
    if not CACHE.exists():
        print('Scanning selected daily fields into local cache', flush=True)
        nums = ['dlyprc','dlycap','dlyvol','dlyprevprc','dlyret','dlyretx','dlyfacprc','dlyorddivamt','dlynonorddivamt','dlyopen']
        flags = ['dlydelflg','dlyprcflg','dlyprevprcflg','dlyretdurflg']
        fields = ','.join([f'TRY_CAST({x} AS DOUBLE) AS {x}' for x in nums] + [f'CAST({x} AS VARCHAR) AS {x}' for x in flags])
        con.execute(f"COPY (SELECT DISTINCT CAST(permno AS BIGINT) permno, CAST(dlycaldt AS DATE) dlycaldt,{fields} FROM read_csv_auto('{ROOT / 'data/raw/crsp_daily_1993_2025.csv.gz'}',sample_size=200000)) TO '{CACHE}' (FORMAT PARQUET)")
    print('Computing coverage predicates and point-in-time eligibility', flush=True)
    chunks = ROOT / 'data/interim/reconstruction_diagnostic_parts'
    chunks.mkdir(exist_ok=True)
    for bucket in range(32):
        target = chunks / f'part_{bucket:02d}.parquet'
        if target.exists():
            continue
        print(f'Processing security partition {bucket + 1}/32', flush=True)
        con.execute(f"""CREATE TEMP TABLE x_chunk AS
    WITH j AS (
      SELECT d.*, f.dlycumfacpr, ABS(d.dlyprc)/NULLIF(f.dlycumfacpr,0) adj_prc
      FROM (SELECT * FROM read_parquet('{CACHE}') WHERE permno % 32 = {bucket}) d LEFT JOIN read_parquet('{ROOT / 'data/interim/crsp_cumfac_1993_2025.parquet'}') f USING(permno,dlycaldt)
    ), w AS (
      SELECT *, LAG(adj_prc) OVER win prev_adj_prc,
      LAG(dlyprc) OVER win lag_prc, LAG(dlycumfacpr) OVER win lag_fac,
      LAG(dlycaldt) OVER win lag_date,
      AVG(ABS(dlyprc)*dlyvol) OVER adv adv20,
      COUNT(ABS(dlyprc)*dlyvol) OVER adv adv20_obs
      FROM j WINDOW win AS(PARTITION BY permno ORDER BY dlycaldt),
      adv AS(PARTITION BY permno ORDER BY dlycaldt ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
    )
    SELECT *, CASE WHEN prev_adj_prc IS NOT NULL AND prev_adj_prc<>0 AND dlyret IS NOT NULL AND dlyretx IS NOT NULL AND ABS(1+dlyretx)>1e-14
    THEN adj_prc/prev_adj_prc*((1+dlyret)/(1+dlyretx)) END reconstructed,
    (ABS(dlyprc)>5 AND dlycap>1000000 AND adv20>20000000 AND adv20_obs>=15 AND EXISTS(
      SELECT 1 FROM read_csv_auto('{ROOT / 'data/raw/crsp_names_history.csv'}',sample_size=200000) n
      WHERE CAST(n.permno AS BIGINT)=w.permno AND w.dlycaldt BETWEEN CAST(n.secinfostartdt AS DATE) AND CAST(n.secinfoenddt AS DATE)
      AND securitytype='EQTY' AND securitysubtype='COM' AND sharetype='NS' AND usincflg='Y'
      AND issuertype IN('ACOR','CORP') AND primaryexch IN('N','A','Q') AND tradingstatusflg='A'
    )) eligible FROM w""")
        con.execute(f"COPY x_chunk TO '{target}' (FORMAT PARQUET)")
        con.execute('DROP TABLE x_chunk')
    con.execute(f"CREATE TEMP VIEW x AS SELECT * FROM read_parquet('{chunks}/*.parquet')")
    def export(name, sql):
        con.execute(f"COPY ({sql}) TO '{OUT / name}' (HEADER, FORMAT CSV)")
    checks=con.execute('SELECT COUNT(*), COUNT(reconstructed), COUNT(*) FILTER(WHERE eligible), COUNT(*)-COUNT(DISTINCT (permno,dlycaldt)) FROM x').fetchone()
    with (OUT/'diagnostic_integrity.csv').open('w') as f:
        wr=csv.writer(f);wr.writerow(['rows','comparable_rows','eligible_rows','duplicate_keys']);wr.writerow(checks)
    assert checks == (64959561,64056350,6699101,0), checks
    predicates={
      'missing_current_factor':'dlycumfacpr IS NULL',
      'missing_current_price':'dlyprc IS NULL',
      'missing_previous_comparable_price':'prev_adj_prc IS NULL',
      'zero_current_factor':'dlycumfacpr=0',
      'zero_previous_comparable_price':'prev_adj_prc=0',
      'missing_total_return':'dlyret IS NULL',
      'missing_ex_distribution_return':'dlyretx IS NULL',
      'near_zero_return_denominator':'ABS(1+dlyretx)<=1e-14',
    }
    export('noncomparable_overlapping_reasons.csv',' UNION ALL '.join(f"SELECT '{k}' reason, COUNT(*) observation_rows, COUNT(*) FILTER(WHERE eligible) eligible_rows FROM x WHERE reconstructed IS NULL AND ({v})" for k,v in predicates.items()))
    case='CASE '+ ' '.join(f"WHEN {v} THEN '{k}'" for k,v in predicates.items())+" ELSE 'other' END"
    export('noncomparable_primary_reasons.csv',f'SELECT {case} reason, COUNT(*) observation_rows, COUNT(*) FILTER(WHERE eligible) eligible_rows FROM x WHERE reconstructed IS NULL GROUP BY 1 ORDER BY observation_rows DESC')
    export('nonfinite_consistency.csv',"SELECT COUNT(*) FILTER(WHERE reconstructed IS NOT NULL AND NOT isfinite(reconstructed)) nonfinite_reconstruction, COUNT(*) FILTER(WHERE dlyret IS NOT NULL AND NOT isfinite(dlyret)) nonfinite_ret, COUNT(*) FILTER(WHERE dlyretx IS NOT NULL AND NOT isfinite(dlyretx)) nonfinite_retx FROM x")
    con.execute(f"""CREATE TEMP TABLE examples AS SELECT x.*, e.abs_total_factor_error,
      adj_prc/prev_adj_prc price_ratio,
      ABS(dlyprc)/NULLIF(ABS(dlyprevprc),0)*dlyfacprc source_previous_price_factor,
      ABS(ABS(dlyprc)/NULLIF(ABS(dlyprevprc),0)*dlyfacprc-(1+dlyretx)) source_previous_error,
      dlydelflg IS NOT NULL AND TRIM(dlydelflg) NOT IN('','0','N') delist_flag,
      lag_fac IS DISTINCT FROM dlycumfacpr factor_change,
      ABS(dlyfacprc-1)>1e-12 period_factor_event,
      ABS(dlyprevprc) IS DISTINCT FROM ABS(lag_prc) source_previous_price_differs,
      dlyprc=lag_prc unchanged_price_proxy,
      ABS(dlyret)>1 OR ABS(dlyretx)>1 extreme_return_proxy,
      DATE_DIFF('day',lag_date,dlycaldt)>4 calendar_gap_proxy
      FROM x JOIN (SELECT permno,dlycaldt,abs_total_factor_error FROM read_csv_auto('{OUT / 'return_reconstruction_examples.csv'}')) e USING(permno,dlycaldt)""")
    export('reconstruction_error_attribution.csv','SELECT * FROM examples ORDER BY abs_total_factor_error DESC')
    export('reconstruction_error_attribution_summary.csv',"""SELECT COUNT(*) examples, COUNT(*) FILTER(WHERE eligible) eligible_examples,
    COUNT(*) FILTER(WHERE delist_flag) delist_flag_rows,
    COUNT(*) FILTER(WHERE factor_change) factor_change_rows,
    COUNT(*) FILTER(WHERE period_factor_event) period_factor_rows,
    COUNT(*) FILTER(WHERE source_previous_price_differs) source_previous_price_differs_rows,
    COUNT(*) FILTER(WHERE source_previous_error<=1e-6) source_previous_matches_rows,
    COUNT(*) FILTER(WHERE unchanged_price_proxy) unchanged_price_rows,
    COUNT(*) FILTER(WHERE extreme_return_proxy) extreme_return_rows,
    COUNT(*) FILTER(WHERE calendar_gap_proxy) calendar_gap_rows,
    COUNT(*) FILTER(WHERE dlyprc IS NULL OR dlyprevprc IS NULL) missing_price_rows
    FROM examples""")
    export('error_flag_frequencies.csv',"SELECT dlydelflg,dlyprcflg,dlyprevprcflg,dlyretdurflg,COUNT(*) observation_rows,COUNT(*) FILTER(WHERE eligible) eligible_rows FROM examples GROUP BY ALL ORDER BY observation_rows DESC")
    # Diagnostic accounting check only: not a replacement target specification.
    export('distribution_accounting_examples.csv', """SELECT permno,dlycaldt,eligible,
      dlynonorddivamt, factor_change, dlyfacprc,
      abs_total_factor_error,
      (ABS(dlyprc)*dlyfacprc+COALESCE(dlynonorddivamt,0))/NULLIF(ABS(dlyprevprc),0) distribution_inclusive_price_factor,
      ABS((ABS(dlyprc)*dlyfacprc+COALESCE(dlynonorddivamt,0))/NULLIF(ABS(dlyprevprc),0)-(1+dlyretx)) distribution_inclusive_error
      FROM examples ORDER BY abs_total_factor_error DESC""")
    export('eligible_reconstruction_errors.csv', """SELECT
      COALESCE(dlynonorddivamt,0)<>0 nonordinary_distribution,
      COUNT(*) comparable_rows,
      AVG(ABS(reconstructed-(1+dlyret))) mean_abs_error,
      MEDIAN(ABS(reconstructed-(1+dlyret))) median_abs_error,
      MAX(ABS(reconstructed-(1+dlyret))) max_abs_error,
      COUNT(*) FILTER(WHERE ABS(reconstructed-(1+dlyret))>1e-6) error_gt_1e6,
      COUNT(*) FILTER(WHERE ABS(reconstructed-(1+dlyret))>0.001) error_gt_0_001
      FROM x WHERE eligible AND reconstructed IS NOT NULL GROUP BY 1""")
    export('eligible_distribution_examples.csv', 'SELECT * FROM x WHERE eligible AND COALESCE(dlynonorddivamt,0)<>0 ORDER BY permno,dlycaldt')
    export('eligible_noncomparable_examples.csv',
      'SELECT * FROM x WHERE eligible AND reconstructed IS NULL ORDER BY permno,dlycaldt')
    export('previous_price_missing_detail.csv', """SELECT
      CASE WHEN lag_date IS NULL THEN 'first_observation_in_extract'
      WHEN lag_prc IS NULL THEN 'previous_raw_price_missing'
      WHEN lag_fac IS NULL THEN 'previous_factor_missing'
      WHEN lag_fac=0 THEN 'previous_factor_zero'
      ELSE 'other' END reason,
      COUNT(*) observation_rows, COUNT(*) FILTER(WHERE eligible) eligible_rows
      FROM x WHERE reconstructed IS NULL AND prev_adj_prc IS NULL GROUP BY 1""")
    print('Diagnostics complete', checks, flush=True)

if __name__=='__main__':
    main()
