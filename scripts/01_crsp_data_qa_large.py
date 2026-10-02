"""Large-file Stage 1A CRSP QA using DuckDB.

Designed for multi-GB WRDS CSV / CSV.GZ extracts without loading the full
dataset into pandas memory.

Usage:
    python3 scripts/01_crsp_data_qa_large.py data/raw/crsp_daily_1993_2025.csv.gz
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

import duckdb


def log(msg: str) -> None:
    print(msg, flush=True)


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

    if not args.input.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    Path(".duckdb_tmp").mkdir(exist_ok=True)

    input_path = str(args.input.resolve()).replace("'", "''")
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET temp_directory='.duckdb_tmp'")

    log(f"Input: {args.input}")
    log(f"Size: {args.input.stat().st_size / (1024**3):.2f} GB")
    log("[1/6] Detecting CSV schema from a sample...")

    relation = (
        f"read_csv_auto('{input_path}', header=true, "
        f"sample_size=200000, all_varchar=false)"
    )

    schema = con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchdf()
    schema.to_csv(args.output_dir / "schema.csv", index=False)

    cols = {c.lower(): c for c in schema["column_name"].tolist()}
    required = ["permno", "dlycaldt", "dlyprc", "dlyopen", "dlyret", "dlyvol", "dlycap"]
    missing = [c for c in required if c not in cols]
    if missing:
        raise RuntimeError(f"Missing required columns: {missing}")

    p = {k: qident(cols[k]) for k in required}

    log("[2/6] Materialising the required columns once with DuckDB.")
    log("      For a 2.4 GB gzip file this can take several minutes.")
    log("      DuckDB may use .duckdb_tmp/ on disk if RAM is insufficient.")

    t0 = time.time()
    con.execute(f"""
        CREATE TEMP TABLE crsp_qa AS
        SELECT
            {p['permno']} AS permno,
            CAST({p['dlycaldt']} AS DATE) AS dlycaldt,
            TRY_CAST({p['dlyprc']} AS DOUBLE) AS dlyprc,
            TRY_CAST({p['dlyopen']} AS DOUBLE) AS dlyopen,
            TRY_CAST({p['dlyret']} AS DOUBLE) AS dlyret,
            TRY_CAST({p['dlyvol']} AS DOUBLE) AS dlyvol,
            TRY_CAST({p['dlycap']} AS DOUBLE) AS dlycap
        FROM {relation}
    """)
    log(f"      Loaded once in {(time.time()-t0)/60:.1f} minutes.")

    log("[3/6] Computing row counts and duplicate PERMNO-date checks...")
    basic = con.execute("""
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT permno) AS unique_permnos,
            MIN(dlycaldt) AS min_date,
            MAX(dlycaldt) AS max_date
        FROM crsp_qa
    """).fetchdf()
    basic.to_csv(args.output_dir / "basic_summary.csv", index=False)

    dups = con.execute("""
        SELECT
            permno,
            dlycaldt,
            COUNT(*) AS n
        FROM crsp_qa
        GROUP BY 1, 2
        HAVING COUNT(*) > 1
        ORDER BY n DESC, permno, dlycaldt
    """).fetchdf()
    dups.to_csv(args.output_dir / "duplicate_security_dates.csv", index=False)

    log("[4/6] Computing yearly field coverage...")
    coverage = con.execute("""
        SELECT
            EXTRACT(year FROM dlycaldt)::INTEGER AS year,
            COUNT(*) AS observations,
            COUNT(DISTINCT permno) AS securities,
            AVG(CASE WHEN dlyprc IS NOT NULL THEN 1 ELSE 0 END) AS dlyprc_coverage,
            AVG(CASE WHEN dlyopen IS NOT NULL THEN 1 ELSE 0 END) AS dlyopen_coverage,
            AVG(CASE WHEN dlyret IS NOT NULL THEN 1 ELSE 0 END) AS dlyret_coverage,
            AVG(CASE WHEN dlyvol IS NOT NULL THEN 1 ELSE 0 END) AS dlyvol_coverage,
            AVG(CASE WHEN dlycap IS NOT NULL THEN 1 ELSE 0 END) AS dlycap_coverage
        FROM crsp_qa
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    coverage.to_csv(args.output_dir / "yearly_coverage.csv", index=False)

    log("[5/6] Computing annual price / size / dollar-volume distributions...")
    distributions = con.execute("""
        WITH x AS (
            SELECT
                EXTRACT(year FROM dlycaldt)::INTEGER AS year,
                ABS(dlyprc) AS price,
                dlycap AS dlycap_thousand_usd,
                ABS(dlyprc) * dlyvol AS dollar_volume
            FROM crsp_qa
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

    log("[6/6] Computing opening-price coverage in a candidate liquid sample...")
    liquid_open = con.execute("""
        WITH x AS (
            SELECT
                EXTRACT(year FROM dlycaldt)::INTEGER AS year,
                ABS(dlyprc) AS price,
                dlycap AS cap_kusd,
                ABS(dlyprc) * dlyvol AS dollar_volume,
                dlyopen
            FROM crsp_qa
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
    liquid_open.to_csv(
        args.output_dir / "open_coverage_candidate_liquid.csv",
        index=False,
    )

    log("")
    log("Stage 1A QA complete.")
    log(basic.to_string(index=False))
    log(f"Duplicate PERMNO-date groups: {len(dups):,}")
    log(f"Outputs: {args.output_dir.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.", file=sys.stderr)
        sys.exit(130)
