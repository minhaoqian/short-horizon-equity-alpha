"""Extract full rows for representative duplicate PERMNO-date keys.

Simple usage:
    python3 scripts/02_inspect_crsp_duplicates.py data/raw/crsp_daily_1993_2025.csv.gz

By default the script reads:
    results/tables/data_qa/duplicate_security_dates.csv

and writes:
    results/tables/data_qa/duplicate_examples_full_rows.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("raw", type=Path)
    p.add_argument(
        "--duplicates",
        type=Path,
        default=Path("results/tables/data_qa/duplicate_security_dates.csv"),
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("results/tables/data_qa/duplicate_examples_full_rows.csv"),
    )
    p.add_argument("--n", type=int, default=25)
    args = p.parse_args()

    if not args.raw.exists():
        raise FileNotFoundError(f"Raw CRSP file not found: {args.raw}")
    if not args.duplicates.exists():
        raise FileNotFoundError(
            f"Duplicate-key file not found: {args.duplicates}. "
            "Run Stage 1A QA first."
        )

    print(f"Reading duplicate keys from {args.duplicates}...", flush=True)
    dups = pd.read_csv(args.duplicates)
    sample = (
        dups.sort_values(["n", "permno"], ascending=[False, True])
        .head(args.n)
        .copy()
    )

    keys = ",".join(
        f"({int(r.permno)}, DATE '{r.dlycaldt}')" for r in sample.itertuples()
    )

    raw = str(args.raw.resolve()).replace("'", "''")
    con = duckdb.connect()
    relation = (
        f"read_csv_auto('{raw}', header=true, sample_size=200000, "
        f"all_varchar=false)"
    )

    print(
        f"Scanning raw CRSP file for {len(sample)} representative duplicate keys...",
        flush=True,
    )

    query = f"""
        SELECT *
        FROM {relation}
        WHERE (permno, CAST(dlycaldt AS DATE)) IN ({keys})
        ORDER BY permno, CAST(dlycaldt AS DATE)
    """
    out = con.execute(query).fetchdf()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)

    print(f"Wrote {len(out):,} rows to {args.output}", flush=True)


if __name__ == "__main__":
    main()
