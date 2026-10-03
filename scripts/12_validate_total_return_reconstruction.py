"""Stage 1G: validate CRSP-consistent total-return reconstruction.

The objective is to verify, on CRSP close-to-close returns, the same
price/income decomposition that will later be used for the open-to-open target.

Usage:
    python3 scripts/12_validate_total_return_reconstruction.py \
        data/raw/crsp_daily_1993_2025.csv.gz \
        data/interim/crsp_cumfac_1993_2025.parquet

Outputs:
    results/tables/stage1g/return_reconstruction_summary.csv
    results/tables/stage1g/return_reconstruction_yearly.csv
    results/tables/stage1g/return_reconstruction_examples.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import duckdb


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("daily", type=Path)
    p.add_argument("cumfac", type=Path)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/tables/stage1g"),
    )
    args = p.parse_args()

    if not args.daily.exists():
        raise FileNotFoundError(args.daily)
    if not args.cumfac.exists():
        raise FileNotFoundError(args.cumfac)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    daily = str(args.daily.resolve()).replace("'", "''")
    fac = str(args.cumfac.resolve()).replace("'", "''")

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")

    print("[1/4] Joining daily CRSP returns to cumulative factors...", flush=True)

    con.execute(f"""
        CREATE TEMP TABLE x AS
        WITH d AS (
            SELECT DISTINCT
                CAST(permno AS BIGINT) AS permno,
                CAST(dlycaldt AS DATE) AS dlycaldt,
                TRY_CAST(dlyprc AS DOUBLE) AS dlyprc,
                TRY_CAST(dlyret AS DOUBLE) AS dlyret,
                TRY_CAST(dlyretx AS DOUBLE) AS dlyretx
            FROM read_csv_auto('{daily}', header=true, sample_size=200000)
        ),
        f AS (
            SELECT
                CAST(permno AS BIGINT) AS permno,
                CAST(dlycaldt AS DATE) AS dlycaldt,
                TRY_CAST(dlycumfacpr AS DOUBLE) AS dlycumfacpr
            FROM read_parquet('{fac}')
        ),
        j AS (
            SELECT
                d.*,
                f.dlycumfacpr,
                ABS(d.dlyprc) / NULLIF(f.dlycumfacpr, 0) AS adj_prc
            FROM d
            LEFT JOIN f USING (permno, dlycaldt)
        )
        SELECT
            *,
            LAG(adj_prc) OVER (
                PARTITION BY permno ORDER BY dlycaldt
            ) AS prev_adj_prc
        FROM j
    """)

    print("[2/4] Reconstructing ex-distribution and total daily returns...", flush=True)

    con.execute("""
        CREATE TEMP TABLE recon AS
        SELECT
            *,
            CASE
                WHEN prev_adj_prc IS NOT NULL AND prev_adj_prc <> 0
                THEN adj_prc / prev_adj_prc
            END AS price_factor_reconstructed,

            CASE
                WHEN dlyret IS NOT NULL
                 AND dlyretx IS NOT NULL
                 AND ABS(1 + dlyretx) > 1e-14
                THEN (1 + dlyret) / (1 + dlyretx)
            END AS income_multiplier,

            CASE
                WHEN prev_adj_prc IS NOT NULL
                 AND prev_adj_prc <> 0
                 AND dlyret IS NOT NULL
                 AND dlyretx IS NOT NULL
                 AND ABS(1 + dlyretx) > 1e-14
                THEN
                    (adj_prc / prev_adj_prc)
                    * ((1 + dlyret) / (1 + dlyretx))
            END AS total_factor_reconstructed
        FROM x
    """)

    print("[3/4] Measuring reconstruction errors...", flush=True)

    summary = con.execute("""
        SELECT
            COUNT(*) AS rows,
            SUM(CASE
                WHEN price_factor_reconstructed IS NOT NULL
                 AND dlyretx IS NOT NULL
                THEN 1 ELSE 0 END) AS comparable_price_rows,
            SUM(CASE
                WHEN total_factor_reconstructed IS NOT NULL
                 AND dlyret IS NOT NULL
                THEN 1 ELSE 0 END) AS comparable_total_rows,

            AVG(ABS(price_factor_reconstructed - (1 + dlyretx)))
                FILTER (
                    WHERE price_factor_reconstructed IS NOT NULL
                      AND dlyretx IS NOT NULL
                ) AS mean_abs_price_factor_error,

            MEDIAN(ABS(price_factor_reconstructed - (1 + dlyretx)))
                FILTER (
                    WHERE price_factor_reconstructed IS NOT NULL
                      AND dlyretx IS NOT NULL
                ) AS median_abs_price_factor_error,

            QUANTILE_CONT(
                ABS(price_factor_reconstructed - (1 + dlyretx)), 0.99
            ) FILTER (
                WHERE price_factor_reconstructed IS NOT NULL
                  AND dlyretx IS NOT NULL
            ) AS p99_abs_price_factor_error,

            AVG(ABS(total_factor_reconstructed - (1 + dlyret)))
                FILTER (
                    WHERE total_factor_reconstructed IS NOT NULL
                      AND dlyret IS NOT NULL
                ) AS mean_abs_total_factor_error,

            MEDIAN(ABS(total_factor_reconstructed - (1 + dlyret)))
                FILTER (
                    WHERE total_factor_reconstructed IS NOT NULL
                      AND dlyret IS NOT NULL
                ) AS median_abs_total_factor_error,

            QUANTILE_CONT(
                ABS(total_factor_reconstructed - (1 + dlyret)), 0.99
            ) FILTER (
                WHERE total_factor_reconstructed IS NOT NULL
                  AND dlyret IS NOT NULL
            ) AS p99_abs_total_factor_error
        FROM recon
    """).fetchdf()
    summary.to_csv(args.output_dir / "return_reconstruction_summary.csv", index=False)

    yearly = con.execute("""
        SELECT
            EXTRACT(year FROM dlycaldt)::INTEGER AS year,
            COUNT(*) FILTER (
                WHERE total_factor_reconstructed IS NOT NULL
                  AND dlyret IS NOT NULL
            ) AS comparable_rows,
            AVG(ABS(total_factor_reconstructed - (1 + dlyret)))
                FILTER (
                    WHERE total_factor_reconstructed IS NOT NULL
                      AND dlyret IS NOT NULL
                ) AS mean_abs_total_factor_error,
            MEDIAN(ABS(total_factor_reconstructed - (1 + dlyret)))
                FILTER (
                    WHERE total_factor_reconstructed IS NOT NULL
                      AND dlyret IS NOT NULL
                ) AS median_abs_total_factor_error,
            QUANTILE_CONT(
                ABS(total_factor_reconstructed - (1 + dlyret)), 0.99
            ) FILTER (
                WHERE total_factor_reconstructed IS NOT NULL
                  AND dlyret IS NOT NULL
            ) AS p99_abs_total_factor_error
        FROM recon
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    yearly.to_csv(args.output_dir / "return_reconstruction_yearly.csv", index=False)

    print("[4/4] Exporting largest discrepancies for inspection...", flush=True)

    examples = con.execute("""
        SELECT
            permno,
            dlycaldt,
            dlyprc,
            dlycumfacpr,
            prev_adj_prc,
            adj_prc,
            dlyretx,
            dlyret,
            price_factor_reconstructed,
            income_multiplier,
            total_factor_reconstructed,
            ABS(price_factor_reconstructed - (1 + dlyretx))
                AS abs_price_factor_error,
            ABS(total_factor_reconstructed - (1 + dlyret))
                AS abs_total_factor_error
        FROM recon
        WHERE total_factor_reconstructed IS NOT NULL
          AND dlyret IS NOT NULL
        ORDER BY abs_total_factor_error DESC NULLS LAST
        LIMIT 500
    """).fetchdf()
    examples.to_csv(args.output_dir / "return_reconstruction_examples.csv", index=False)

    print("")
    print("Stage 1G return reconstruction audit complete.", flush=True)
    print(summary.to_string(index=False), flush=True)
    print(f"Outputs: {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
