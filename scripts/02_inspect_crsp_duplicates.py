"""Extract full rows for representative duplicate PERMNO-date keys.

Usage:
    python3 scripts/02_inspect_crsp_duplicates.py \
        data/raw/crsp_daily_1993_2025.csv.gz \
        results/tables/data_qa/duplicate_security_dates.csv

Produces a small CSV suitable for manual inspection.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import duckdb
import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("raw", type=Path)
    p.add_argument("duplicates", type=Path)
    p.add_argument(
        "--output",
        type=Path,
        default=Path("results/tables/data_qa/duplicate_examples_full_rows.csv"),
    )
    p.add_argument("--n", type=int, default=25)
    args = p.parse_args()

    dups = pd.read_csv(args.duplicates)
    sample = dups.sort_values(["n", "permno"], ascending=[False, True]).head(args.n)
    keys = ",".join(
        f"({int(r.permno)}, DATE '{r.dlycaldt}')" for r in sample.itertuples()
    )

    raw = str(args.raw.resolve()).replace("'", "''")
    con = duckdb.connect()
    relation = f"read_csv_auto('{raw}', header=true, sample_size=200000)"

    query = f"""
        SELECT *
        FROM {relation}
        WHERE (PERMNO, CAST(DlyCalDt AS DATE)) IN ({keys})
        ORDER BY PERMNO, CAST(DlyCalDt AS DATE)
    """
    out = con.execute(query).fetchdf()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    print(f"Wrote {len(out):,} rows to {args.output}", flush=True)


if __name__ == "__main__":
    main()
