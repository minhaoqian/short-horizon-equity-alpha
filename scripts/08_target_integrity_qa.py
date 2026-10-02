"""Stage 1D: freeze signal-date eligibility and audit the 5-day next-open target.

Usage:
    python3 scripts/08_target_integrity_qa.py \
        data/raw/crsp_daily_1993_2025.csv.gz \
        data/raw/crsp_names_history.csv

Outputs:
    results/tables/stage1d/target_integrity_yearly.csv
    results/tables/stage1d/target_integrity_overall.csv
    results/tables/stage1d/endpoint_failure_examples.csv
    results/tables/stage1d/final_eligibility_yearly.csv

This script does not train a model and does not evaluate return performance.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import duckdb


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("daily", type=Path)
    p.add_argument("names", type=Path)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/tables/stage1d"),
    )
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

    print("[1/6] Loading locked historical security classification...", flush=True)
    names_rel = f"read_csv_auto('{names}', header=true, sample_size=200000)"
    con.execute(f"""
        CREATE TEMP TABLE names_locked AS
        SELECT
            CAST(permno AS BIGINT) AS permno,
            CAST(secinfostartdt AS DATE) AS startdt,
            CAST(secinfoenddt AS DATE) AS enddt
        FROM {names_rel}
        WHERE securitytype = 'EQTY'
          AND securitysubtype = 'COM'
          AND sharetype = 'NS'
          AND usincflg = 'Y'
          AND issuertype IN ('ACOR','CORP')
          AND primaryexch IN ('N','A','Q')
          AND tradingstatusflg = 'A'
    """)

    print("[2/6] Materialising deduplicated daily fields...", flush=True)
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
            dlydelflg
        FROM {daily_rel}
    """)

    print("[3/6] Building CRSP trading calendar and t+1 / t+6 mappings...", flush=True)
    con.execute("""
        CREATE TEMP TABLE calendar AS
        SELECT
            dlycaldt,
            ROW_NUMBER() OVER (ORDER BY dlycaldt) AS td
        FROM (SELECT DISTINCT dlycaldt FROM daily)
    """)

    con.execute("""
        CREATE TEMP TABLE dated AS
        SELECT d.*, c.td
        FROM daily d
        JOIN calendar c USING (dlycaldt)
    """)

    print("[4/6] Computing lag-safe ADV20 and locked signal-date eligibility...", flush=True)
    con.execute("""
        CREATE TEMP TABLE with_adv AS
        SELECT
            *,
            AVG(ABS(dlyprc) * dlyvol) OVER (
                PARTITION BY permno
                ORDER BY td
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS adv20,
            COUNT(ABS(dlyprc) * dlyvol) OVER (
                PARTITION BY permno
                ORDER BY td
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS adv20_obs
        FROM dated
    """)

    con.execute("""
        CREATE TEMP TABLE eligible AS
        SELECT
            a.permno,
            a.dlycaldt AS signal_date,
            a.td AS signal_td,
            ABS(a.dlyprc) AS signal_price,
            a.dlycap AS signal_cap_kusd,
            a.adv20
        FROM with_adv a
        JOIN names_locked n
          ON a.permno = n.permno
         AND a.dlycaldt BETWEEN n.startdt AND n.enddt
        WHERE ABS(a.dlyprc) > 5
          AND a.dlycap > 1000000
          AND a.adv20 > 20000000
          AND a.adv20_obs >= 15
    """)

    yearly = con.execute("""
        SELECT
            EXTRACT(year FROM signal_date)::INTEGER AS year,
            COUNT(*) AS eligible_observations,
            COUNT(DISTINCT permno) AS eligible_permnos
        FROM eligible
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    yearly.to_csv(args.output_dir / "final_eligibility_yearly.csv", index=False)

    print("[5/6] Auditing next-open entry and 5-day endpoint availability...", flush=True)

    con.execute("""
        CREATE TEMP TABLE target_audit AS
        SELECT
            e.*,
            c1.dlycaldt AS entry_date,
            c6.dlycaldt AS exit_date,
            d1.dlyopen AS entry_open,
            d6.dlyopen AS exit_open,
            CASE WHEN d1.permno IS NOT NULL THEN 1 ELSE 0 END AS has_entry_row,
            CASE WHEN d6.permno IS NOT NULL THEN 1 ELSE 0 END AS has_exit_row,
            CASE WHEN d1.dlyopen IS NOT NULL THEN 1 ELSE 0 END AS has_entry_open,
            CASE WHEN d6.dlyopen IS NOT NULL THEN 1 ELSE 0 END AS has_exit_open,
            CASE WHEN EXISTS (
                SELECT 1
                FROM dated dx
                WHERE dx.permno = e.permno
                  AND dx.td BETWEEN e.signal_td + 1 AND e.signal_td + 6
                  AND dx.dlydelflg IS NOT NULL
                  AND TRIM(CAST(dx.dlydelflg AS VARCHAR)) NOT IN ('','0','N')
            ) THEN 1 ELSE 0 END AS delist_flag_within_horizon
        FROM eligible e
        LEFT JOIN calendar c1 ON c1.td = e.signal_td + 1
        LEFT JOIN calendar c6 ON c6.td = e.signal_td + 6
        LEFT JOIN dated d1
          ON d1.permno = e.permno AND d1.td = e.signal_td + 1
        LEFT JOIN dated d6
          ON d6.permno = e.permno AND d6.td = e.signal_td + 6
    """)

    integrity = con.execute("""
        SELECT
            EXTRACT(year FROM signal_date)::INTEGER AS year,
            COUNT(*) AS eligible_observations,
            AVG(has_entry_row) AS entry_row_rate,
            AVG(has_entry_open) AS entry_open_rate,
            AVG(has_exit_row) AS exit_row_rate,
            AVG(has_exit_open) AS exit_open_rate,
            AVG(CASE WHEN has_entry_open=1 AND has_exit_open=1 THEN 1 ELSE 0 END)
                AS complete_open_target_rate,
            SUM(CASE WHEN has_entry_open=0 THEN 1 ELSE 0 END) AS missing_entry_open,
            SUM(CASE WHEN has_entry_open=1 AND has_exit_open=0 THEN 1 ELSE 0 END)
                AS missing_exit_open_after_valid_entry,
            SUM(delist_flag_within_horizon) AS delist_flag_windows
        FROM target_audit
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    integrity.to_csv(args.output_dir / "target_integrity_yearly.csv", index=False)

    overall = con.execute("""
        SELECT
            COUNT(*) AS eligible_observations,
            AVG(has_entry_open) AS entry_open_rate,
            AVG(has_exit_open) AS exit_open_rate,
            AVG(CASE WHEN has_entry_open=1 AND has_exit_open=1 THEN 1 ELSE 0 END)
                AS complete_open_target_rate,
            SUM(CASE WHEN has_entry_open=0 THEN 1 ELSE 0 END) AS missing_entry_open,
            SUM(CASE WHEN has_entry_open=1 AND has_exit_open=0 THEN 1 ELSE 0 END)
                AS missing_exit_open_after_valid_entry,
            SUM(delist_flag_within_horizon) AS delist_flag_windows
        FROM target_audit
    """).fetchdf()
    overall.to_csv(args.output_dir / "target_integrity_overall.csv", index=False)

    print("[6/6] Exporting representative endpoint failures...", flush=True)
    failures = con.execute("""
        SELECT *
        FROM target_audit
        WHERE has_entry_open=0
           OR has_exit_open=0
           OR delist_flag_within_horizon=1
        ORDER BY signal_date DESC, permno
        LIMIT 500
    """).fetchdf()
    failures.to_csv(args.output_dir / "endpoint_failure_examples.csv", index=False)

    print("")
    print("Stage 1D target-integrity QA complete.", flush=True)
    print(overall.to_string(index=False), flush=True)
    print(f"Outputs: {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
