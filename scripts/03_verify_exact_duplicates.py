"""Verify whether every duplicated PERMNO-date group consists only of exact duplicate rows.

Usage:
    python3 scripts/03_verify_exact_duplicates.py data/raw/crsp_daily_1993_2025.csv.gz

Output:
    results/tables/data_qa/duplicate_integrity_summary.csv

If conflicting_groups == 0, duplicate PERMNO-date records are exact row duplicates
and may be deterministically collapsed to one row per key.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import duckdb


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("raw", type=Path)
    p.add_argument(
        "--output",
        type=Path,
        default=Path("results/tables/data_qa/duplicate_integrity_summary.csv"),
    )
    args = p.parse_args()

    if not args.raw.exists():
        raise FileNotFoundError(args.raw)

    raw = str(args.raw.resolve()).replace("'", "''")
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET temp_directory='.duckdb_tmp'")

    print("Detecting schema...", flush=True)
    rel = f"read_csv_auto('{raw}', header=true, sample_size=200000)"
    schema = con.execute(f"DESCRIBE SELECT * FROM {rel}").fetchdf()
    cols = schema["column_name"].tolist()

    lower = {c.lower(): c for c in cols}
    if "permno" not in lower or "dlycaldt" not in lower:
        raise RuntimeError("PERMNO or DlyCalDt not found")

    permno = '"' + lower["permno"] + '"'
    date = '"' + lower["dlycaldt"] + '"'
    quoted = [f'"{c}"' for c in cols]
    hash_expr = "hash(" + ", ".join(quoted) + ")"

    print("Scanning all duplicate PERMNO-date groups...", flush=True)

    q = f"""
    WITH x AS (
        SELECT
            {permno} AS permno,
            CAST({date} AS DATE) AS dlycaldt,
            {hash_expr} AS row_hash
        FROM {rel}
    ),
    g AS (
        SELECT
            permno,
            dlycaldt,
            COUNT(*) AS row_count,
            COUNT(DISTINCT row_hash) AS distinct_row_versions
        FROM x
        GROUP BY 1,2
        HAVING COUNT(*) > 1
    )
    SELECT
        COUNT(*) AS duplicate_groups,
        SUM(row_count - 1) AS excess_rows,
        SUM(CASE WHEN distinct_row_versions = 1 THEN 1 ELSE 0 END) AS exact_duplicate_groups,
        SUM(CASE WHEN distinct_row_versions > 1 THEN 1 ELSE 0 END) AS conflicting_groups,
        MAX(row_count) AS max_multiplicity,
        MAX(distinct_row_versions) AS max_distinct_versions
    FROM g
    """

    out = con.execute(q).fetchdf()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)

    print(out.to_string(index=False), flush=True)
    print(f"Wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
