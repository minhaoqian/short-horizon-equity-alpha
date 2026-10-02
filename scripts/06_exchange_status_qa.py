"""Stage 1B final exchange/status diagnostic for the candidate liquid common-equity universe.

Usage:
    python3 scripts/06_exchange_status_qa.py \
        data/raw/crsp_daily_1993_2025.csv.gz \
        data/raw/crsp_names_history.csv

Outputs small cross-tabs used to lock the final universe definition.
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
        default=Path("results/tables/security_metadata"),
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

    print("[1/4] Reading historical metadata...", flush=True)
    names_rel = f"read_csv_auto('{names}', header=true, sample_size=200000)"
    con.execute(f"""
        CREATE TEMP TABLE names AS
        SELECT
            CAST(permno AS BIGINT) AS permno,
            CAST(secinfostartdt AS DATE) AS startdt,
            CAST(secinfoenddt AS DATE) AS enddt,
            primaryexch,
            tradingstatusflg
        FROM {names_rel}
        WHERE securitytype = 'EQTY'
          AND securitysubtype = 'COM'
          AND sharetype = 'NS'
          AND usincflg = 'Y'
          AND issuertype IN ('ACOR','CORP')
    """)

    print("[2/4] Building candidate liquid panel with ADV20...", flush=True)
    daily_rel = f"read_csv_auto('{daily}', header=true, sample_size=200000)"
    con.execute(f"""
        CREATE TEMP TABLE candidate AS
        WITH base AS (
            SELECT DISTINCT
                CAST(permno AS BIGINT) AS permno,
                CAST(dlycaldt AS DATE) AS dlycaldt,
                ABS(TRY_CAST(dlyprc AS DOUBLE)) AS price,
                TRY_CAST(dlycap AS DOUBLE) AS cap_kusd,
                TRY_CAST(dlyvol AS DOUBLE) AS volume,
                TRY_CAST(dlyprc AS DOUBLE) AS prc
            FROM {daily_rel}
        ),
        x AS (
            SELECT *,
                AVG(ABS(prc) * volume) OVER (
                    PARTITION BY permno ORDER BY dlycaldt
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS adv20,
                COUNT(ABS(prc) * volume) OVER (
                    PARTITION BY permno ORDER BY dlycaldt
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS adv20_obs
            FROM base
        )
        SELECT *
        FROM x
        WHERE price > 5
          AND cap_kusd > 1000000
          AND adv20 > 20000000
          AND adv20_obs >= 15
    """)

    print("[3/4] Joining and producing exchange/status cross-tabs...", flush=True)
    con.execute("""
        CREATE TEMP TABLE joined AS
        SELECT
            d.dlycaldt,
            d.permno,
            n.primaryexch,
            n.tradingstatusflg
        FROM candidate d
        JOIN names n
          ON d.permno = n.permno
         AND d.dlycaldt BETWEEN n.startdt AND n.enddt
    """)

    exch = con.execute("""
        SELECT
            primaryexch,
            tradingstatusflg,
            COUNT(*) AS observations,
            COUNT(DISTINCT permno) AS permnos
        FROM joined
        GROUP BY 1,2
        ORDER BY observations DESC
    """).fetchdf()
    exch.to_csv(args.output_dir / "common_equity_exchange_status.csv", index=False)

    yearly = con.execute("""
        SELECT
            EXTRACT(year FROM dlycaldt)::INTEGER AS year,
            COUNT(*) AS all_common_obs,
            SUM(CASE WHEN primaryexch IN ('N','A','Q') THEN 1 ELSE 0 END) AS naq_obs,
            SUM(CASE WHEN primaryexch IN ('N','A','Q') AND tradingstatusflg='A'
                     THEN 1 ELSE 0 END) AS naq_active_obs,
            COUNT(DISTINCT permno) AS all_common_permnos,
            COUNT(DISTINCT CASE WHEN primaryexch IN ('N','A','Q') THEN permno END) AS naq_permnos,
            COUNT(DISTINCT CASE WHEN primaryexch IN ('N','A','Q') AND tradingstatusflg='A'
                                THEN permno END) AS naq_active_permnos
        FROM joined
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    yearly.to_csv(args.output_dir / "exchange_filter_impact_yearly.csv", index=False)

    print("[4/4] Done.", flush=True)
    print(exch.to_string(index=False), flush=True)
    print(f"Outputs: {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
