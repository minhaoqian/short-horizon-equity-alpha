"""Run Stage 1A CRSP coverage diagnostics.

Usage:
    python scripts/01_crsp_data_qa.py data/raw/crsp_daily.parquet

The script does not download licensed CRSP data. Exported WRDS/CRSP data should
be placed locally under data/raw/, which is excluded from Git.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.data.qa import (
    CRSPColumns,
    duplicate_security_dates,
    open_coverage_by_liquidity_bucket,
    yearly_coverage,
)


def load_panel(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in {".csv", ".gz"}:
        return pd.read_csv(path)
    raise ValueError("Expected a .parquet, .csv, or .gz file.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/tables/data_qa"),
    )
    args = parser.parse_args()

    df = load_panel(args.input)
    cols = CRSPColumns()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    duplicates = duplicate_security_dates(df, cols)
    coverage = yearly_coverage(df, cols)
    open_by_adv = open_coverage_by_liquidity_bucket(df, cols)

    coverage.to_csv(args.output_dir / "yearly_coverage.csv", index=False)
    open_by_adv.to_csv(
        args.output_dir / "open_coverage_by_adv_bucket.csv",
        index=False,
    )
    duplicates.to_csv(args.output_dir / "duplicate_security_dates.csv", index=False)

    print(f"Rows: {len(df):,}")
    print(f"Duplicate PERMNO-date rows: {len(duplicates):,}")
    print(f"Wrote diagnostics to {args.output_dir}")


if __name__ == "__main__":
    main()
