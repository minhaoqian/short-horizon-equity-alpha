"""Verify opening-price coverage using true trailing 20-day ADV.

Usage:
    python3 scripts/04_verify_adv20_open_coverage.py data/raw/crsp_daily_1993_2025.csv.gz

Outputs:
    results/tables/data_qa/open_coverage_adv20.csv
    results/tables/data_qa/universe_counts_adv20.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import duckdb


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("raw", type=Path)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/tables/data_qa"),
    )
    args = p.parse_args()

    if not args.raw.exists():
        raise FileNotFoundError(args.raw)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = str(args.raw.resolve()).replace("'", "''")

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET temp_directory='.duckdb_tmp'")

    print("Reading required columns and removing exact duplicate rows...", flush=True)

    rel = f"read_csv_auto('{raw}', header=true, sample_size=200000)"

    con.execute(f"""
        CREATE TEMP TABLE base AS
        SELECT DISTINCT
            permno,
            CAST(dlycaldt AS DATE) AS dlycaldt,
            TRY_CAST(dlyprc AS DOUBLE) AS dlyprc,
            TRY_CAST(dlyopen AS DOUBLE) AS dlyopen,
            TRY_CAST(dlyvol AS DOUBLE) AS dlyvol,
            TRY_CAST(dlycap AS DOUBLE) AS dlycap
        FROM {rel}
    """)

    print("Computing trailing 20-day ADV by PERMNO...", flush=True)

    con.execute("""
        CREATE TEMP TABLE adv AS
        SELECT
            *,
            AVG(ABS(dlyprc) * dlyvol) OVER (
                PARTITION BY permno
                ORDER BY dlycaldt
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS adv20,
            COUNT(ABS(dlyprc) * dlyvol) OVER (
                PARTITION BY permno
                ORDER BY dlycaldt
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) AS adv20_obs
        FROM base
    """)

    print("Computing yearly open coverage under candidate liquid-universe rules...", flush=True)

    coverage = con.execute("""
        SELECT
            EXTRACT(year FROM dlycaldt)::INTEGER AS year,
            COUNT(*) AS observations,
            COUNT(DISTINCT permno) AS securities,
            AVG(CASE WHEN dlyopen IS NOT NULL THEN 1 ELSE 0 END) AS open_coverage
        FROM adv
        WHERE ABS(dlyprc) > 5
          AND dlycap > 1000000
          AND adv20 > 20000000
          AND adv20_obs >= 15
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()

    coverage.to_csv(
        args.output_dir / "open_coverage_adv20.csv",
        index=False,
    )

    counts = con.execute("""
        SELECT
            dlycaldt,
            COUNT(*) AS eligible_securities
        FROM adv
        WHERE ABS(dlyprc) > 5
          AND dlycap > 1000000
          AND adv20 > 20000000
          AND adv20_obs >= 15
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()

    counts.to_csv(
        args.output_dir / "universe_counts_adv20.csv",
        index=False,
    )

    print("")
    print(coverage.to_string(index=False), flush=True)
    print("")
    print("ADV20 opening-price verification complete.", flush=True)


if __name__ == "__main__":
    main()
