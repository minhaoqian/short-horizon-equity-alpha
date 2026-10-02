"""Stage 1C: liquidity-threshold sensitivity without using return performance.

Usage:
    python3 scripts/07_liquidity_threshold_sensitivity.py \
        data/raw/crsp_daily_1993_2025.csv.gz \
        data/raw/crsp_names_history.csv

Outputs:
    results/tables/stage1c/threshold_grid_yearly.csv
    results/tables/stage1c/threshold_grid_overall.csv
    results/tables/stage1c/baseline_daily_counts.csv

The script deliberately does NOT compute IC, returns, Sharpe, or PnL.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import duckdb


PRICE_FLOORS = [3.0, 5.0, 10.0]
CAP_FLOORS_KUSD = [500_000.0, 1_000_000.0, 2_000_000.0]
ADV_FLOORS_USD = [10_000_000.0, 20_000_000.0, 50_000_000.0]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("daily", type=Path)
    p.add_argument("names", type=Path)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/tables/stage1c"),
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

    print("[1/5] Loading locked point-in-time common-equity metadata...", flush=True)
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

    print("[2/5] Building deduplicated daily panel and true ADV20...", flush=True)
    daily_rel = f"read_csv_auto('{daily}', header=true, sample_size=200000)"
    con.execute(f"""
        CREATE TEMP TABLE base AS
        SELECT DISTINCT
            CAST(permno AS BIGINT) AS permno,
            CAST(dlycaldt AS DATE) AS dlycaldt,
            ABS(TRY_CAST(dlyprc AS DOUBLE)) AS price,
            TRY_CAST(dlyopen AS DOUBLE) AS dlyopen,
            TRY_CAST(dlycap AS DOUBLE) AS cap_kusd,
            TRY_CAST(dlyvol AS DOUBLE) AS volume,
            TRY_CAST(dlyprc AS DOUBLE) AS prc
        FROM {daily_rel}
    """)

    con.execute("""
        CREATE TEMP TABLE adv AS
        SELECT
            *,
            AVG(ABS(prc) * volume) OVER (
                PARTITION BY permno
                ORDER BY dlycaldt
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS adv20,
            COUNT(ABS(prc) * volume) OVER (
                PARTITION BY permno
                ORDER BY dlycaldt
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS adv20_obs
        FROM base
    """)

    print("[3/5] Applying locked security classification point-in-time...", flush=True)
    con.execute("""
        CREATE TEMP TABLE eligible_base AS
        SELECT
            a.dlycaldt,
            a.permno,
            a.price,
            a.dlyopen,
            a.cap_kusd,
            a.adv20,
            a.adv20_obs
        FROM adv a
        JOIN names_locked n
          ON a.permno = n.permno
         AND a.dlycaldt BETWEEN n.startdt AND n.enddt
        WHERE a.adv20_obs >= 15
    """)

    print("[4/5] Evaluating pre-specified threshold grid...", flush=True)
    rows = []
    for pf in PRICE_FLOORS:
        for cf in CAP_FLOORS_KUSD:
            for af in ADV_FLOORS_USD:
                yearly = con.execute(f"""
                    SELECT
                        {pf} AS price_floor,
                        {cf} AS cap_floor_kusd,
                        {af} AS adv20_floor_usd,
                        EXTRACT(year FROM dlycaldt)::INTEGER AS year,
                        COUNT(*) AS observations,
                        COUNT(DISTINCT permno) AS securities,
                        AVG(CASE WHEN dlyopen IS NOT NULL THEN 1 ELSE 0 END) AS open_coverage
                    FROM eligible_base
                    WHERE price > {pf}
                      AND cap_kusd > {cf}
                      AND adv20 > {af}
                    GROUP BY 4
                    ORDER BY 4
                """).fetchdf()
                rows.append(yearly)

    import pandas as pd
    grid = pd.concat(rows, ignore_index=True)
    grid.to_csv(args.output_dir / "threshold_grid_yearly.csv", index=False)

    overall = (
        grid.groupby(["price_floor","cap_floor_kusd","adv20_floor_usd"])
        .agg(
            years=("year","nunique"),
            mean_annual_observations=("observations","mean"),
            min_annual_observations=("observations","min"),
            mean_annual_securities=("securities","mean"),
            min_annual_securities=("securities","min"),
            max_annual_securities=("securities","max"),
            mean_open_coverage=("open_coverage","mean"),
            min_open_coverage=("open_coverage","min"),
        )
        .reset_index()
    )
    overall.to_csv(args.output_dir / "threshold_grid_overall.csv", index=False)

    print("[5/5] Exporting baseline daily breadth series...", flush=True)
    baseline = con.execute("""
        SELECT
            dlycaldt,
            COUNT(*) AS eligible_securities,
            AVG(CASE WHEN dlyopen IS NOT NULL THEN 1 ELSE 0 END) AS open_coverage
        FROM eligible_base
        WHERE price > 5
          AND cap_kusd > 1000000
          AND adv20 > 20000000
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    baseline.to_csv(args.output_dir / "baseline_daily_counts.csv", index=False)

    print("")
    print("Stage 1C threshold sensitivity complete.", flush=True)
    print("No return-performance statistics were used.", flush=True)
    print(f"Outputs: {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
