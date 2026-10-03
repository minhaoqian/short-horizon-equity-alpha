"""Preserve all locked signal keys; classify observable next-open exceptions."""
from pathlib import Path
import json
import duckdb
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/tables/stage1g'


def main():
    manifest=json.loads((ROOT/'data/interim/reconstruction_diagnostic_manifest.json').read_text())
    for p,s in manifest['inputs'].items():
        v=(ROOT/p).stat();assert s=={'size':v.st_size,'mtime_ns':v.st_mtime_ns}
    c=duckdb.connect();c.execute("SET memory_limit='4GB'");c.execute('SET threads=1')
    c.execute(f"SET temp_directory='{ROOT/'.duckdb_tmp'}'")
    c.execute(f"CREATE VIEW all_daily AS SELECT * FROM read_parquet('{ROOT/'data/interim/reconstruction_diagnostic_parts/*.parquet'}')")
    c.execute('CREATE TABLE cal AS SELECT dlycaldt, ROW_NUMBER() OVER(ORDER BY dlycaldt) td FROM (SELECT DISTINCT dlycaldt FROM all_daily)')
    max_td=c.execute('SELECT MAX(td) FROM cal').fetchone()[0]
    folder=ROOT/'data/interim/target_boundary_audit_parts';folder.mkdir(exist_ok=True)
    for i in range(32):
        print('Auditing partition',i+1,flush=True)
        part=ROOT/f'data/interim/reconstruction_diagnostic_parts/part_{i:02d}.parquet'
        c.execute(f"CREATE TEMP VIEW d AS SELECT p.*,cc.td FROM read_parquet('{part}') p JOIN cal cc USING(dlycaldt)")
        c.execute(f'''CREATE TEMP TABLE a AS
        WITH grid AS (
          SELECT e.permno,e.dlycaldt signal_date,e.td signal_td,e.td+6>{max_td} right_censored,
            k.step,cc.dlycaldt expected_date,v.* EXCLUDE(permno,dlycaldt),v.permno observed_permno,
            v.dlycaldt observed_date
          FROM d e CROSS JOIN range(1,7) k(step)
          LEFT JOIN cal cc ON cc.td=e.td+k.step
          LEFT JOIN d v ON v.permno=e.permno AND v.dlycaldt=cc.dlycaldt
          WHERE e.eligible
        )
        SELECT permno,signal_date,signal_td,right_censored,
          MAX(expected_date) FILTER(WHERE step=1) entry_date,
          MAX(expected_date) FILTER(WHERE step=6) exit_date,
          MAX(dlyopen) FILTER(WHERE step=1) entry_open,
          MAX(dlyopen) FILTER(WHERE step=6) exit_open,
          COUNT(observed_permno) FILTER(WHERE step=1)>0 entry_row,
          COUNT(observed_permno) FILTER(WHERE step=6)>0 exit_row,
          MAX(dlyprcflg) FILTER(WHERE step=1) entry_price_flag,
          MAX(dlyprcflg) FILTER(WHERE step=6) exit_price_flag,
          MAX(dlyvol) FILTER(WHERE step=1) entry_volume,
          MAX(dlyvol) FILTER(WHERE step=6) exit_volume,
          COUNT(*) FILTER(WHERE dlydelflg='Y')>0 daily_delist_flag,
          COUNT(*) FILTER(WHERE step=1 AND dlydelflg='Y')>0 entry_delist_flag,
          COUNT(*) FILTER(WHERE step=6 AND dlydelflg='Y')>0 exit_delist_flag,
          COUNT(*) FILTER(WHERE step BETWEEN 2 AND 5 AND dlydelflg='Y')>0 interior_delist_flag,
          COUNT(*) FILTER(WHERE step=1 AND dlyorddivamt<>0)>0 entry_ordinary,
          COUNT(*) FILTER(WHERE step=6 AND dlyorddivamt<>0)>0 exit_ordinary,
          COUNT(*) FILTER(WHERE step BETWEEN 2 AND 5 AND dlyorddivamt<>0)>0 interior_ordinary,
          COUNT(*) FILTER(WHERE step=1 AND dlynonorddivamt<>0)>0 entry_nonordinary,
          COUNT(*) FILTER(WHERE step=6 AND dlynonorddivamt<>0)>0 exit_nonordinary,
          COUNT(*) FILTER(WHERE step BETWEEN 2 AND 5 AND dlynonorddivamt<>0)>0 interior_nonordinary,
          COUNT(*) FILTER(WHERE dlyfacprc<>1)>0 period_factor_event,
          COUNT(*) FILTER(WHERE dlycumfacpr IS DISTINCT FROM lag_fac AND lag_fac IS NOT NULL)>0 cumulative_factor_event,
          COUNT(*) FILTER(WHERE step BETWEEN 2 AND 6 AND dlyretdurflg LIKE 'P%'
              AND (dlyorddivamt<>0 OR dlynonorddivamt<>0 OR dlyfacprc<>1))>0 aggregated_event_interval,
          COUNT(*) FILTER(WHERE step BETWEEN 2 AND 5 AND (observed_permno IS NULL OR dlyprc IS NULL))>0 interior_missing_price,
          COUNT(*) FILTER(WHERE step BETWEEN 2 AND 6 AND (dlyorddivamt IS NULL OR dlynonorddivamt IS NULL OR dlyfacprc IS NULL))>0 missing_event_fields,
          COUNT(*) FILTER(WHERE dlyprcflg='DA')>0 delist_price_flag,
          COUNT(*) FILTER(WHERE dlycumfacpr IS NULL OR dlycumfacpr<=0)>0 invalid_factor
        FROM grid GROUP BY permno,signal_date,signal_td,right_censored''')
        c.execute(f"COPY a TO '{folder/f'part_{i:02d}.parquet'}' (FORMAT PARQUET)")
        c.execute('DROP TABLE a');c.execute('DROP VIEW d')
    c.execute(f"CREATE VIEW a AS SELECT *,COALESCE(entry_open>0 AND isfinite(entry_open),false) valid_entry,COALESCE(exit_open>0 AND isfinite(exit_open),false) valid_exit FROM read_parquet('{folder}/*.parquet')")
    def export(name,q):c.execute(f"COPY ({q}) TO '{OUT/name}' (HEADER,FORMAT CSV)")
    n,keys=c.execute('SELECT COUNT(*),COUNT(DISTINCT (permno,signal_date)) FROM a').fetchone()
    assert (n,keys)==(6699101,6699101)
    predicates={
      'right_censored':'right_censored',
      'missing_entry_non_censored':'NOT right_censored AND NOT valid_entry',
      'missing_exit_given_entry':'NOT right_censored AND valid_entry AND NOT valid_exit',
      'missing_exit_all_non_censored':'NOT right_censored AND NOT valid_exit',
      'both_missing_non_censored':'NOT right_censored AND NOT valid_entry AND NOT valid_exit',
      'daily_delist_flag_1_6':'daily_delist_flag',
      'entry_delist_flag':'entry_delist_flag','interior_delist_flag':'interior_delist_flag','exit_delist_flag':'exit_delist_flag',
      'ordinary_any_1_6':'entry_ordinary OR interior_ordinary OR exit_ordinary',
      'ordinary_entitlement_2_6_proxy':'interior_ordinary OR exit_ordinary',
      'ordinary_entry':'entry_ordinary','ordinary_exit':'exit_ordinary','ordinary_interior':'interior_ordinary',
      'nonordinary_any_1_6':'entry_nonordinary OR interior_nonordinary OR exit_nonordinary',
      'nonordinary_entitlement_2_6_proxy':'interior_nonordinary OR exit_nonordinary',
      'nonordinary_entry':'entry_nonordinary','nonordinary_exit':'exit_nonordinary','nonordinary_interior':'interior_nonordinary',
      'period_factor_event':'period_factor_event','cumulative_factor_event':'cumulative_factor_event',
      'aggregated_event_interval':'aggregated_event_interval','interior_missing_price':'interior_missing_price',
      'missing_event_fields':'missing_event_fields','invalid_factor':'invalid_factor',
    }
    export('target_boundary_counts.csv',' UNION ALL '.join(f"SELECT '{k}' category,COUNT(*) observations,100.0*COUNT(*)/{n} percentage FROM a WHERE {v}" for k,v in predicates.items()))
    event='(entry_nonordinary OR interior_nonordinary OR exit_nonordinary OR period_factor_event OR cumulative_factor_event)'
    reason=f"""CASE WHEN right_censored THEN 'right_censored' WHEN NOT valid_entry THEN 'missing_entry'
      WHEN daily_delist_flag OR delist_price_flag THEN 'delisting_review'
      WHEN NOT valid_exit THEN 'missing_exit'
      WHEN {event} THEN 'nonordinary_or_factor_review'
      WHEN aggregated_event_interval OR missing_event_fields THEN 'event_timing_or_fields_review'
      WHEN interior_ordinary OR exit_ordinary THEN 'ordinary_cash_candidate'
      ELSE 'price_only_candidate' END"""
    export('target_boundary_primary_paths.csv',f'SELECT {reason} path,COUNT(*) observations,100.0*COUNT(*)/{n} percentage FROM a GROUP BY 1 ORDER BY observations DESC')
    export('target_endpoint_causes.csv',f'''SELECT side,has_row,price_flag,zero_volume,delist_flag,
      COUNT(*) observations,100.0*COUNT(*)/{n} percentage FROM (
        SELECT 'entry' side,entry_row has_row,entry_price_flag price_flag,COALESCE(entry_volume,0)=0 zero_volume,daily_delist_flag delist_flag
        FROM a WHERE NOT right_censored AND NOT valid_entry UNION ALL
        SELECT 'exit',exit_row,exit_price_flag,COALESCE(exit_volume,0)=0,daily_delist_flag
        FROM a WHERE NOT right_censored AND valid_entry AND NOT valid_exit
      ) GROUP BY ALL ORDER BY side,observations DESC''')
    export('target_boundary_unresolved_examples.csv',f"SELECT * FROM a WHERE NOT right_censored AND (NOT valid_entry OR NOT valid_exit OR daily_delist_flag OR {event} OR aggregated_event_interval OR missing_event_fields) ORDER BY signal_date,permno LIMIT 1000")
    export_additional_checks(c, n)
    print('Boundary audit complete',n,flush=True)


def entitled_at_ex_date(entry_date, exit_date, ex_date):
    """Entry open is ex-rights; exit open occurs after rights detach.

    Use the actual event ex-date, not record/payment date or a daily return row
    containing an aggregated distribution amount.
    """
    return entry_date < ex_date <= exit_date


def planned_dates(calendar, signal_index):
    """Global market calendar only; a missing security row cannot shift exit."""
    entry = calendar[signal_index+1] if signal_index+1 < len(calendar) else None
    exit_ = calendar[signal_index+6] if signal_index+6 < len(calendar) else None
    return entry, exit_


def export_additional_checks(c, n):
    def export(name,q):
        c.execute(f"COPY ({q}) TO '{OUT/name}' (HEADER,FORMAT CSV)")
    export('target_boundary_extra_checks.csv', """SELECT
      COUNT(*) FILTER(WHERE interior_delist_flag OR exit_delist_flag) return_flag_2_6,
      COUNT(*) FILTER(WHERE NOT right_censored AND valid_entry AND (interior_delist_flag OR exit_delist_flag)) flag2_6_with_entry,
      COUNT(*) FILTER(WHERE NOT right_censored AND valid_entry AND NOT valid_exit AND NOT daily_delist_flag) missing_exit_without_flag,
      COUNT(*) FILTER(WHERE NOT right_censored AND valid_entry AND NOT valid_exit AND daily_delist_flag) missing_exit_with_flag,
      COUNT(*) FILTER(WHERE NOT right_censored AND valid_entry AND valid_exit AND NOT daily_delist_flag AND NOT period_factor_event
        AND NOT cumulative_factor_event AND NOT entry_nonordinary AND NOT interior_nonordinary AND NOT exit_nonordinary
        AND (invalid_factor OR missing_event_fields OR aggregated_event_interval)) candidate_integrity_issues FROM a""")
    c.execute(f"CREATE TEMP VIEW names AS SELECT * FROM read_csv_auto('{ROOT/'data/raw/crsp_names_history.csv'}')")
    export('target_endpoint_metadata.csv', """WITH failures AS (
      SELECT permno,entry_date endpoint_date,'entry' side,entry_price_flag price_flag FROM a
        WHERE NOT right_censored AND NOT valid_entry UNION ALL
      SELECT permno,exit_date,'exit',exit_price_flag FROM a WHERE NOT right_censored AND valid_entry AND NOT valid_exit
      ) SELECT side,price_flag,n.tradingstatusflg,COUNT(*) observations FROM failures f
      LEFT JOIN names n ON n.permno=f.permno AND f.endpoint_date BETWEEN n.secinfostartdt AND n.secinfoenddt
      GROUP BY ALL ORDER BY side,observations DESC""")


if __name__=='__main__':
    main()
