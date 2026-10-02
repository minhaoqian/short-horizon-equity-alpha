"""Large-file Stage 1A CRSP QA using DuckDB.

Designed for multi-GB WRDS CSV / CSV.GZ extracts without loading the full
dataset into pandas memory.

Usage:
    python scripts/01_crsp_data_qa_large.py data/raw/crsp_daily_1993_2025.csv.gz
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/tables/data_qa"),
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    input_path = str(args.input.resolve()).replace("'", "''")
    con = duckdb.connect()

    # Let DuckDB spill to disk rather than relying on RAM.
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET temp_directory='.duckdb_tmp'")

    relation = f"read_csv_auto('{input_path}', header=true, sample_size=-1, all_varchar=false)"

    # Schema snapshot
    schema = con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchdf()
    schema.to_csv(args.output_dir / "schema.csv", index=False)

    cols = {c.lower(): c for c in schema["column_name"].tolist()}
    required = ["permno", "dlycaldt", "dlyprc", "dlyopen", "dlyret", "dlyvol", "dlycap"]
    missing = [c for c in required if c not in cols]
    if missing:
        raise RuntimeError(f"Missing required columns: {missing}")

    p = {k: qident(cols[k]) for k in required}

    # Basic row / identifier diagnostics.
    basic = con.execute(f"""
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT {p['permno']}) AS unique_permnos,
            MIN(CAST({p['dlycaldt']} AS DATE)) AS min_date,
            MAX(CAST({p['dlycaldt']} AS DATE)) AS max_date
        FROM {relation}
    """).fetchdf()
    basic.to_csv(args.output_dir / "basic_summary.csv", index=False)

    # Duplicate security-date rows.
    dups = con.execute(f"""
        SELECT
            {p['permno']} AS permno,
            CAST({p['dlycaldt']} AS DATE) AS dlycaldt,
            COUNT(*) AS n
        FROM {relation}
        GROUP BY 1, 2
        HAVING COUNT(*) > 1
        ORDER BY n DESC, permno, dlycaldt
    """).fetchdf()
    dups.to_csv(args.output_dir / "duplicate_security_dates.csv", index=False)

    # Annual field coverage.
    coverage = con.execute(f"""
        SELECT
            EXTRACT(year FROM CAST({p['dlycaldt']} AS DATE))::INTEGER AS year,
            COUNT(*) AS observations,
            COUNT(DISTINCT {p['permno']}) AS securities,
            AVG(CASE WHEN {p['dlyprc']} IS NOT NULL THEN 1 ELSE 0 END) AS dlyprc_coverage,
            AVG(CASE WHEN {p['dlyopen']} IS NOT NULL THEN 1 ELSE 0 END) AS dlyopen_coverage,
            AVG(CASE WHEN {p['dlyret']} IS NOT NULL THEN 1 ELSE 0 END) AS dlyret_coverage,
            AVG(CASE WHEN {p['dlyvol']} IS NOT NULL THEN 1 ELSE 0 END) AS dlyvol_coverage,
            AVG(CASE WHEN {p['dlycap']} IS NOT NULL THEN 1 ELSE 0 END) AS dlycap_coverage
        FROM {relation}
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    coverage.to_csv(args.output_dir / "yearly_coverage.csv", index=False)

    # Yearly distributions for raw price, CRSP-native market cap (thousand USD),
    # and daily dollar volume.
    distributions = con.execute(f"""
        WITH x AS (
            SELECT
                EXTRACT(year FROM CAST({p['dlycaldt']} AS DATE))::INTEGER AS year,
                ABS(TRY_CAST({p['dlyprc']} AS DOUBLE)) AS price,
                TRY_CAST({p['dlycap']} AS DOUBLE) AS dlycap_thousand_usd,
                ABS(TRY_CAST({p['dlyprc']} AS DOUBLE))
                  * TRY_CAST({p['dlyvol']} AS DOUBLE) AS dollar_volume
            FROM {relation}
        )
        SELECT
            year,
            quantile_cont(price, 0.10) AS price_p10,
            quantile_cont(price, 0.50) AS price_p50,
            quantile_cont(price, 0.90) AS price_p90,
            quantile_cont(dlycap_thousand_usd, 0.10) AS cap_p10,
            quantile_cont(dlycap_thousand_usd, 0.50) AS cap_p50,
            quantile_cont(dlycap_thousand_usd, 0.90) AS cap_p90,
            quantile_cont(dollar_volume, 0.10) AS dollarvol_p10,
            quantile_cont(dollar_volume, 0.50) AS dollarvol_p50,
            quantile_cont(dollar_volume, 0.90) AS dollarvol_p90
        FROM x
        GROUP BY year
        ORDER BY year
    """).fetchdf()
    distributions.to_csv(args.output_dir / "yearly_distributions.csv", index=False)

    # Opening-price coverage in a simple candidate liquid cross-section.
    # dlycap is in thousands of USD, so 1bn USD = 1,000,000.
    liquid_open = con.execute(f"""
        WITH x AS (
            SELECT
                EXTRACT(year FROM CAST({p['dlycaldt']} AS DATE))::INTEGER AS year,
                ABS(TRY_CAST({p['dlyprc']} AS DOUBLE)) AS price,
                TRY_CAST({p['dlycap']} AS DOUBLE) AS cap_kusd,
                ABS(TRY_CAST({p['dlyprc']} AS DOUBLE))
                  * TRY_CAST({p['dlyvol']} AS DOUBLE) AS dollar_volume,
                {p['dlyopen']} AS dlyopen
            FROM {relation}
        )
        SELECT
            year,
            COUNT(*) AS observations,
            AVG(CASE WHEN dlyopen IS NOT NULL THEN 1 ELSE 0 END) AS open_coverage
        FROM x
        WHERE price > 5
          AND cap_kusd > 1000000
          AND dollar_volume > 20000000
        GROUP BY year
        ORDER BY year
    """).fetchdf()
    liquid_open.to_csv(args.output_dir / "open_coverage_candidate_liquid.csv", index=False)

    print("\nStage 1A large-file QA complete.")
    print(basic.to_string(index=False))
    print(f"Duplicate PERMNO-date groups: {len(dups):,}")
    print(f"Outputs: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
