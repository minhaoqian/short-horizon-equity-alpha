"""Stage 1E: audit corporate actions inside the candidate 5-day holding window.

Usage:
    python3 scripts/09_corporate_action_audit.py \
        data/raw/crsp_daily_1993_2025.csv.gz \
        data/raw/crsp_names_history.csv

This is a methodology audit only. It does not compute model or portfolio performance.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import duckdb


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("daily", type=Path)
    p.add_argument("names", type=Path)
    p.add_argument("--output-dir", type=Path, default=Path("results/tables/stage1e"))
    args = p.parse_args()

    if not args.daily.exists():
        raise FileNotFoundError(args.daily)
    if not args.names.exists():
        raise FileNotFoundError(args.names)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    Path(".duckdb_tmp").mkdir(exist_ok=True)

    daily = str(args.daily.resolve()).replace("'", "''")
    names = str(args.names.resolve()).replace("'", "''")

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET temp_directory='.duckdb_tmp'")

    print("[1/6] Loading locked security metadata...", flush=True)
    names_rel = f"read_csv_auto('{names}', header=true, sample_size=200000)"
    con.execute(f"""
        CREATE TEMP TABLE names_locked AS
        SELECT
            CAST(permno AS BIGINT) AS permno,
            CAST(secinfostartdt AS DATE) AS startdt,
            CAST(secinfoenddt AS DATE) AS enddt
        FROM {names_rel}
        WHERE securitytype='EQTY'
          AND securitysubtype='COM'
          AND sharetype='NS'
          AND usincflg='Y'
          AND issuertype IN ('ACOR','CORP')
          AND primaryexch IN ('N','A','Q')
          AND tradingstatusflg='A'
    """)

    print("[2/6] Loading daily fields and trading calendar...", flush=True)
    daily_rel = f"read_csv_auto('{daily}', header=true, sample_size=200000)"
    con.execute(f"""
        CREATE TEMP TABLE daily AS
        SELECT DISTINCT
            CAST(permno AS BIGINT) AS permno,
            CAST(dlycaldt AS DATE) AS dlycaldt,
            TRY_CAST(dlyprc AS DOUBLE) AS dlyprc,
            TRY_CAST(dlyopen AS DOUBLE) AS dlyopen,
            TRY_CAST(dlyvol AS DOUBLE) AS dlyvol,
            TRY_CAST(dlycap AS DOUBLE) AS dlycap,
            TRY_CAST(dlyret AS DOUBLE) AS dlyret,
            TRY_CAST(dlyfacprc AS DOUBLE) AS dlyfacprc,
            TRY_CAST(dlyorddivamt AS DOUBLE) AS dlyorddivamt,
            TRY_CAST(dlynonorddivamt AS DOUBLE) AS dlynonorddivamt,
            dlydelflg
        FROM {daily_rel}
    """)

    con.execute("""
        CREATE TEMP TABLE calendar AS
        SELECT dlycaldt, ROW_NUMBER() OVER (ORDER BY dlycaldt) AS td
        FROM (SELECT DISTINCT dlycaldt FROM daily)
    """)

    con.execute("""
        CREATE TEMP TABLE dated AS
        SELECT d.*, c.td
        FROM daily d
        JOIN calendar c USING (dlycaldt)
    """)

    print("[3/6] Rebuilding locked signal-date eligibility...", flush=True)
    con.execute("""
        CREATE TEMP TABLE adv AS
        SELECT *,
            AVG(ABS(dlyprc)*dlyvol) OVER (
                PARTITION BY permno ORDER BY td
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS adv20,
            COUNT(ABS(dlyprc)*dlyvol) OVER (
                PARTITION BY permno ORDER BY td
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS adv20_obs
        FROM dated
    """)

    con.execute("""
        CREATE TEMP TABLE eligible AS
        SELECT
            a.permno,
            a.dlycaldt AS signal_date,
            a.td AS signal_td
        FROM adv a
        JOIN names_locked n
          ON a.permno=n.permno
         AND a.dlycaldt BETWEEN n.startdt AND n.enddt
        WHERE ABS(a.dlyprc)>5
          AND a.dlycap>1000000
          AND a.adv20>20000000
          AND a.adv20_obs>=15
    """)

    max_td = con.execute("SELECT MAX(td) FROM calendar").fetchone()[0]

    print("[4/6] Auditing 5-day windows...", flush=True)
    con.execute(f"""
        CREATE TEMP TABLE audit AS
        SELECT
            e.permno,
            e.signal_date,
            e.signal_td,
            CASE WHEN e.signal_td + 6 <= {max_td} THEN 0 ELSE 1 END AS right_censored,
            COUNT(CASE WHEN d.td=e.signal_td+1 AND d.dlyopen IS NOT NULL THEN 1 END) AS has_entry_open,
            COUNT(CASE WHEN d.td=e.signal_td+6 AND d.dlyopen IS NOT NULL THEN 1 END) AS has_exit_open,
            MAX(CASE WHEN d.td BETWEEN e.signal_td+1 AND e.signal_td+6
                       AND COALESCE(d.dlyorddivamt,0)<>0 THEN 1 ELSE 0 END) AS ordinary_dividend_window,
            MAX(CASE WHEN d.td BETWEEN e.signal_td+1 AND e.signal_td+6
                       AND COALESCE(d.dlynonorddivamt,0)<>0 THEN 1 ELSE 0 END) AS nonordinary_dividend_window,
            MAX(CASE WHEN d.td BETWEEN e.signal_td+1 AND e.signal_td+6
                       AND d.dlyfacprc IS NOT NULL
                       AND ABS(d.dlyfacprc) > 1e-12 THEN 1 ELSE 0 END) AS nonzero_factor_window,
            MAX(CASE WHEN d.td BETWEEN e.signal_td+1 AND e.signal_td+6
                       AND d.dlydelflg IS NOT NULL
                       AND TRIM(CAST(d.dlydelflg AS VARCHAR)) NOT IN ('','0','N')
                     THEN 1 ELSE 0 END) AS delist_window
        FROM eligible e
        LEFT JOIN dated d
          ON d.permno=e.permno
         AND d.td BETWEEN e.signal_td+1 AND e.signal_td+6
        GROUP BY e.permno,e.signal_date,e.signal_td
    """)

    yearly = con.execute("""
        SELECT
            EXTRACT(year FROM signal_date)::INTEGER AS year,
            COUNT(*) AS eligible_windows,
            SUM(right_censored) AS right_censored,
            SUM(CASE WHEN right_censored=0 AND has_entry_open=0 THEN 1 ELSE 0 END) AS genuine_missing_entry_open,
            SUM(CASE WHEN right_censored=0 AND has_entry_open>0 AND has_exit_open=0 THEN 1 ELSE 0 END) AS genuine_missing_exit_open,
            SUM(ordinary_dividend_window) AS ordinary_dividend_windows,
            SUM(nonordinary_dividend_window) AS nonordinary_dividend_windows,
            SUM(nonzero_factor_window) AS nonzero_factor_windows,
            SUM(delist_window) AS delist_windows
        FROM audit
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    yearly.to_csv(args.output_dir / "corporate_action_audit_yearly.csv", index=False)

    overall = con.execute("""
        SELECT
            COUNT(*) AS eligible_windows,
            SUM(right_censored) AS right_censored,
            SUM(CASE WHEN right_censored=0 AND has_entry_open=0 THEN 1 ELSE 0 END) AS genuine_missing_entry_open,
            SUM(CASE WHEN right_censored=0 AND has_entry_open>0 AND has_exit_open=0 THEN 1 ELSE 0 END) AS genuine_missing_exit_open,
            SUM(ordinary_dividend_window) AS ordinary_dividend_windows,
            SUM(nonordinary_dividend_window) AS nonordinary_dividend_windows,
            SUM(nonzero_factor_window) AS nonzero_factor_windows,
            SUM(delist_window) AS delist_windows
        FROM audit
    """).fetchdf()
    overall.to_csv(args.output_dir / "corporate_action_audit_overall.csv", index=False)

    print("[5/6] Sampling genuine failures and corporate-action windows...", flush=True)
    sample = con.execute("""
        SELECT *
        FROM audit
        WHERE right_censored=0
          AND (
               has_entry_open=0
            OR has_exit_open=0
            OR ordinary_dividend_window=1
            OR nonordinary_dividend_window=1
            OR nonzero_factor_window=1
            OR delist_window=1
          )
        USING SAMPLE 1000 ROWS
    """).fetchdf()
    sample.to_csv(args.output_dir / "corporate_action_examples.csv", index=False)

    print("[6/6] Auditing DlyFacPrc observed values...", flush=True)
    fac = con.execute("""
        SELECT
            dlyfacprc,
            COUNT(*) AS rows
        FROM daily
        WHERE dlyfacprc IS NOT NULL
        GROUP BY 1
        ORDER BY rows DESC
        LIMIT 100
    """).fetchdf()
    fac.to_csv(args.output_dir / "dlyfacprc_frequency.csv", index=False)

    print("")
    print("Stage 1E corporate-action audit complete.", flush=True)
    print(overall.to_string(index=False), flush=True)
    print(f"Outputs: {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
