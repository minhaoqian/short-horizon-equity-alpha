"""Stage 1F: verify CRSP CIZ daily cumulative adjustment factors.

Usage:
    python3 scripts/10_verify_cumulative_factors.py \
        data/raw/crsp_daily_1993_2025.csv.gz \
        data/raw/crsp_cumfac_1993_2025.zip

Outputs:
    data/interim/crsp_cumfac_1993_2025.parquet
    results/tables/stage1f/cumfac_yearly_summary.csv
    results/tables/stage1f/cumfac_join_coverage_yearly.csv
    results/tables/stage1f/factor_change_summary.csv
    results/tables/stage1f/factor_change_examples.csv

This is a data/methodology verification step only.
"""

from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


EXPECTED_YEARS = list(range(1993, 2026))
EXPECTED_COLS = ["permno", "dlycaldt", "dlycumfacpr", "dlycumfacshr"]


def build_parquet(zip_path: Path, parquet_path: Path) -> pd.DataFrame:
    yearly = []
    writer = None

    with zipfile.ZipFile(zip_path) as z:
        members = sorted(
            n for n in z.namelist()
            if n.startswith("crsp_cumfac_") and n.endswith(".csv")
        )

        found_years = []
        for member in members:
            year = int(Path(member).stem.split("_")[-1])
            found_years.append(year)

        if found_years != EXPECTED_YEARS:
            raise RuntimeError(
                f"Expected annual files 1993-2025; found years: {found_years}"
            )

        parquet_path.parent.mkdir(parents=True, exist_ok=True)

        for member in members:
            year = int(Path(member).stem.split("_")[-1])
            print(f"Reading {member}...", flush=True)

            with z.open(member) as fh:
                df = pd.read_csv(
                    fh,
                    dtype={
                        "permno": "int64",
                        "dlycumfacpr": "float64",
                        "dlycumfacshr": "float64",
                    },
                    parse_dates=["dlycaldt"],
                )

            if list(df.columns) != EXPECTED_COLS:
                raise RuntimeError(
                    f"{member}: expected columns {EXPECTED_COLS}; got {list(df.columns)}"
                )

            if not df["dlycaldt"].dt.year.eq(year).all():
                raise RuntimeError(f"{member}: contains dates outside calendar year {year}")

            yearly.append({
                "year": year,
                "rows": len(df),
                "unique_permnos": df["permno"].nunique(),
                "min_date": df["dlycaldt"].min(),
                "max_date": df["dlycaldt"].max(),
                "missing_price_factor": int(df["dlycumfacpr"].isna().sum()),
                "missing_share_factor": int(df["dlycumfacshr"].isna().sum()),
                "duplicate_permno_date_rows": int(
                    df.duplicated(["permno", "dlycaldt"], keep=False).sum()
                ),
            })

            table = pa.Table.from_pandas(df, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(
                    parquet_path,
                    table.schema,
                    compression="zstd",
                )
            writer.write_table(table)

    if writer is not None:
        writer.close()

    return pd.DataFrame(yearly)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("daily", type=Path)
    p.add_argument("cumfac_zip", type=Path)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/tables/stage1f"),
    )
    p.add_argument(
        "--parquet",
        type=Path,
        default=Path("data/interim/crsp_cumfac_1993_2025.parquet"),
    )
    args = p.parse_args()

    if not args.daily.exists():
        raise FileNotFoundError(args.daily)
    if not args.cumfac_zip.exists():
        raise FileNotFoundError(args.cumfac_zip)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("[1/5] Building compressed cumulative-factor parquet...", flush=True)
    yearly = build_parquet(args.cumfac_zip, args.parquet)
    yearly.to_csv(args.output_dir / "cumfac_yearly_summary.csv", index=False)

    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")

    daily = str(args.daily.resolve()).replace("'", "''")
    fac = str(args.parquet.resolve()).replace("'", "''")

    print("[2/5] Checking cumulative-factor key uniqueness...", flush=True)
    dup = con.execute(f"""
        SELECT COUNT(*) AS duplicate_groups
        FROM (
            SELECT permno, dlycaldt, COUNT(*) AS n
            FROM read_parquet('{fac}')
            GROUP BY 1,2
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    if dup:
        raise RuntimeError(f"Cumulative-factor file has {dup:,} duplicate PERMNO-date groups.")

    print("[3/5] Measuring join coverage against daily panel...", flush=True)
    coverage = con.execute(f"""
        WITH d AS (
            SELECT DISTINCT
                CAST(permno AS BIGINT) AS permno,
                CAST(dlycaldt AS DATE) AS dlycaldt
            FROM read_csv_auto('{daily}', header=true, sample_size=200000)
        ),
        f AS (
            SELECT
                CAST(permno AS BIGINT) AS permno,
                CAST(dlycaldt AS DATE) AS dlycaldt,
                dlycumfacpr,
                dlycumfacshr
            FROM read_parquet('{fac}')
        )
        SELECT
            EXTRACT(year FROM d.dlycaldt)::INTEGER AS year,
            COUNT(*) AS daily_rows,
            SUM(CASE WHEN f.permno IS NOT NULL THEN 1 ELSE 0 END) AS matched_rows,
            AVG(CASE WHEN f.permno IS NOT NULL THEN 1.0 ELSE 0.0 END) AS match_rate,
            AVG(CASE WHEN f.dlycumfacpr IS NOT NULL THEN 1.0 ELSE 0.0 END)
                AS price_factor_coverage,
            AVG(CASE WHEN f.dlycumfacshr IS NOT NULL THEN 1.0 ELSE 0.0 END)
                AS share_factor_coverage
        FROM d
        LEFT JOIN f USING (permno, dlycaldt)
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    coverage.to_csv(args.output_dir / "cumfac_join_coverage_yearly.csv", index=False)

    print("[4/5] Identifying genuine cumulative-price-factor changes...", flush=True)
    changes = con.execute(f"""
        WITH f AS (
            SELECT
                permno,
                dlycaldt,
                dlycumfacpr,
                LAG(dlycumfacpr) OVER (
                    PARTITION BY permno ORDER BY dlycaldt
                ) AS prev_cumfacpr,
                LAG(dlycaldt) OVER (
                    PARTITION BY permno ORDER BY dlycaldt
                ) AS prev_date
            FROM read_parquet('{fac}')
        )
        SELECT *
        FROM f
        WHERE dlycumfacpr IS NOT NULL
          AND prev_cumfacpr IS NOT NULL
          AND ABS(dlycumfacpr - prev_cumfacpr) > 1e-12
    """).fetchdf()

    pd.DataFrame({
        "factor_change_events": [len(changes)],
        "unique_permnos": [changes["permno"].nunique()],
        "min_event_date": [changes["dlycaldt"].min() if len(changes) else None],
        "max_event_date": [changes["dlycaldt"].max() if len(changes) else None],
    }).to_csv(args.output_dir / "factor_change_summary.csv", index=False)

    print("[5/5] Verifying raw vs adjusted-open continuity around factor changes...", flush=True)
    examples = con.execute(f"""
        WITH d AS (
            SELECT DISTINCT
                CAST(permno AS BIGINT) AS permno,
                CAST(dlycaldt AS DATE) AS dlycaldt,
                TRY_CAST(dlyopen AS DOUBLE) AS dlyopen
            FROM read_csv_auto('{daily}', header=true, sample_size=200000)
        ),
        f AS (
            SELECT
                permno,
                dlycaldt,
                dlycumfacpr,
                LAG(dlycumfacpr) OVER (
                    PARTITION BY permno ORDER BY dlycaldt
                ) AS prev_cumfacpr,
                LAG(dlycaldt) OVER (
                    PARTITION BY permno ORDER BY dlycaldt
                ) AS prev_date
            FROM read_parquet('{fac}')
        ),
        ev AS (
            SELECT *
            FROM f
            WHERE dlycumfacpr IS NOT NULL
              AND prev_cumfacpr IS NOT NULL
              AND ABS(dlycumfacpr - prev_cumfacpr) > 1e-12
        )
        SELECT
            ev.permno,
            ev.prev_date,
            ev.dlycaldt AS event_date,
            ev.prev_cumfacpr,
            ev.dlycumfacpr,
            dp.dlyopen AS prev_raw_open,
            de.dlyopen AS event_raw_open,
            CASE WHEN ev.prev_cumfacpr <> 0
                 THEN dp.dlyopen / ev.prev_cumfacpr END AS prev_adjusted_open,
            CASE WHEN ev.dlycumfacpr <> 0
                 THEN de.dlyopen / ev.dlycumfacpr END AS event_adjusted_open,
            CASE WHEN dp.dlyopen IS NOT NULL AND dp.dlyopen <> 0
                 THEN ABS(de.dlyopen / dp.dlyopen - 1) END AS abs_raw_open_jump,
            CASE WHEN dp.dlyopen IS NOT NULL
                      AND de.dlyopen IS NOT NULL
                      AND ev.prev_cumfacpr <> 0
                      AND ev.dlycumfacpr <> 0
                      AND (dp.dlyopen / ev.prev_cumfacpr) <> 0
                 THEN ABS(
                     (de.dlyopen / ev.dlycumfacpr)
                     / (dp.dlyopen / ev.prev_cumfacpr) - 1
                 ) END AS abs_adjusted_open_jump
        FROM ev
        LEFT JOIN d dp
          ON dp.permno=ev.permno AND dp.dlycaldt=ev.prev_date
        LEFT JOIN d de
          ON de.permno=ev.permno AND de.dlycaldt=ev.dlycaldt
        WHERE dp.dlyopen IS NOT NULL
          AND de.dlyopen IS NOT NULL
        ORDER BY abs_raw_open_jump DESC NULLS LAST
        LIMIT 500
    """).fetchdf()
    examples.to_csv(args.output_dir / "factor_change_examples.csv", index=False)

    print("")
    print("Stage 1F cumulative-factor verification complete.", flush=True)
    print(yearly.to_string(index=False), flush=True)
    print("")
    print(coverage.to_string(index=False), flush=True)
    print("")
    print(f"Factor-change events: {len(changes):,}", flush=True)
    print(f"Outputs: {args.output_dir}", flush=True)
    print(f"Parquet: {args.parquet}", flush=True)


if __name__ == "__main__":
    main()
