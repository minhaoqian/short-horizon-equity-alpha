"""Stage 1B: historical security metadata QA and point-in-time universe construction.

Usage:
    python3 scripts/05_security_metadata_qa.py \
        data/raw/crsp_daily_1993_2025.csv.gz \
        data/raw/crsp_names_history.csv

Outputs:
    results/tables/security_metadata/
"""

from __future__ import annotations

import argparse
from pathlib import Path
import duckdb


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("daily", type=Path)
    p.add_argument("names", type=Path)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/tables/security_metadata"),
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

    print("[1/7] Reading metadata and checking schema...", flush=True)

    names_rel = f"read_csv_auto('{names}', header=true, sample_size=200000)"
    schema = con.execute(f"DESCRIBE SELECT * FROM {names_rel}").fetchdf()
    schema.to_csv(args.output_dir / "metadata_schema.csv", index=False)

    required = {
        "permno","permco","secinfostartdt","secinfoenddt",
        "securitytype","securitysubtype","sharetype","issuertype",
        "usincflg","primaryexch","ticker","cusip","siccd","tradingstatusflg"
    }
    actual = {c.lower() for c in schema["column_name"].tolist()}
    missing = sorted(required - actual)
    if missing:
        raise RuntimeError(f"Missing expected metadata columns: {missing}")

    print("[2/7] Materialising metadata...", flush=True)

    con.execute(f"""
        CREATE TEMP TABLE names AS
        SELECT
            CAST(permno AS BIGINT) AS permno,
            CAST(permco AS BIGINT) AS permco,
            CAST(secinfostartdt AS DATE) AS secinfostartdt,
            CAST(secinfoenddt AS DATE) AS secinfoenddt,
            securitytype,
            securitysubtype,
            sharetype,
            issuertype,
            usincflg,
            primaryexch,
            ticker,
            cusip,
            siccd,
            tradingstatusflg
        FROM {names_rel}
    """)

    summary = con.execute("""
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT permno) AS unique_permnos,
            MIN(secinfostartdt) AS min_start,
            MAX(secinfoenddt) AS max_end,
            SUM(CASE WHEN secinfostartdt IS NULL THEN 1 ELSE 0 END) AS missing_start,
            SUM(CASE WHEN secinfoenddt IS NULL THEN 1 ELSE 0 END) AS missing_end
        FROM names
    """).fetchdf()
    summary.to_csv(args.output_dir / "metadata_summary.csv", index=False)

    print("[3/7] Exporting classification code frequencies...", flush=True)

    fields = [
        "securitytype","securitysubtype","sharetype","issuertype",
        "usincflg","primaryexch","tradingstatusflg"
    ]
    for field in fields:
        out = con.execute(f"""
            SELECT {field} AS value, COUNT(*) AS rows, COUNT(DISTINCT permno) AS permnos
            FROM names
            GROUP BY 1
            ORDER BY rows DESC
        """).fetchdf()
        out.to_csv(args.output_dir / f"{field}_frequency.csv", index=False)

    print("[4/7] Checking invalid and overlapping metadata intervals...", flush=True)

    invalid = con.execute("""
        SELECT *
        FROM names
        WHERE secinfostartdt IS NULL
           OR secinfoenddt IS NULL
           OR secinfostartdt > secinfoenddt
        ORDER BY permno, secinfostartdt
    """).fetchdf()
    invalid.to_csv(args.output_dir / "invalid_metadata_intervals.csv", index=False)

    overlap = con.execute("""
        WITH x AS (
            SELECT
                *,
                LAG(secinfoenddt) OVER (
                    PARTITION BY permno
                    ORDER BY secinfostartdt, secinfoenddt
                ) AS prev_end
            FROM names
        )
        SELECT *
        FROM x
        WHERE prev_end IS NOT NULL
          AND secinfostartdt <= prev_end
        ORDER BY permno, secinfostartdt
    """).fetchdf()
    overlap.to_csv(args.output_dir / "overlapping_metadata_intervals.csv", index=False)

    print("[5/7] Measuring historical ordinary-US-common-equity coverage...", flush=True)

    common = con.execute("""
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT permno) AS permnos
        FROM names
        WHERE securitytype = 'EQTY'
          AND securitysubtype = 'COM'
          AND sharetype = 'NS'
          AND usincflg = 'Y'
          AND issuertype IN ('ACOR','CORP')
    """).fetchdf()
    common.to_csv(args.output_dir / "common_equity_metadata_summary.csv", index=False)

    print("[6/7] Joining candidate liquid daily panel to point-in-time metadata...", flush=True)

    daily_rel = f"read_csv_auto('{daily}', header=true, sample_size=200000)"

    # Exact duplicates were previously proven to be mechanically identical.
    con.execute(f"""
        CREATE TEMP TABLE daily_candidate AS
        WITH base AS (
            SELECT DISTINCT
                CAST(permno AS BIGINT) AS permno,
                CAST(dlycaldt AS DATE) AS dlycaldt,
                ABS(TRY_CAST(dlyprc AS DOUBLE)) AS price,
                TRY_CAST(dlycap AS DOUBLE) AS cap_kusd,
                TRY_CAST(dlyvol AS DOUBLE) AS dlyvol,
                TRY_CAST(dlyprc AS DOUBLE) AS dlyprc
            FROM {daily_rel}
        ),
        adv AS (
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
        )
        SELECT *
        FROM adv
        WHERE price > 5
          AND cap_kusd > 1000000
          AND adv20 > 20000000
          AND adv20_obs >= 15
    """)

    joined = con.execute("""
        WITH j AS (
            SELECT
                d.dlycaldt,
                d.permno,
                n.permco,
                n.securitytype,
                n.securitysubtype,
                n.sharetype,
                n.issuertype,
                n.usincflg,
                n.primaryexch,
                n.tradingstatusflg,
                CASE WHEN n.permno IS NOT NULL THEN 1 ELSE 0 END AS metadata_match,
                CASE WHEN
                    n.securitytype = 'EQTY'
                    AND n.securitysubtype = 'COM'
                    AND n.sharetype = 'NS'
                    AND n.usincflg = 'Y'
                    AND n.issuertype IN ('ACOR','CORP')
                THEN 1 ELSE 0 END AS ordinary_us_common
            FROM daily_candidate d
            LEFT JOIN names n
              ON d.permno = n.permno
             AND d.dlycaldt BETWEEN n.secinfostartdt AND n.secinfoenddt
        )
        SELECT
            EXTRACT(year FROM dlycaldt)::INTEGER AS year,
            COUNT(*) AS candidate_rows,
            COUNT(DISTINCT permno) AS candidate_permnos,
            AVG(metadata_match) AS metadata_match_rate,
            AVG(ordinary_us_common) AS ordinary_us_common_share,
            SUM(ordinary_us_common) AS ordinary_us_common_rows
        FROM j
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    joined.to_csv(args.output_dir / "point_in_time_join_coverage.csv", index=False)

    print("[7/7] Computing final candidate universe breadth by year...", flush=True)

    universe = con.execute("""
        WITH j AS (
            SELECT
                d.dlycaldt,
                d.permno,
                n.primaryexch,
                n.tradingstatusflg
            FROM daily_candidate d
            JOIN names n
              ON d.permno = n.permno
             AND d.dlycaldt BETWEEN n.secinfostartdt AND n.secinfoenddt
            WHERE n.securitytype = 'EQTY'
              AND n.securitysubtype = 'COM'
              AND n.sharetype = 'NS'
              AND n.usincflg = 'Y'
              AND n.issuertype IN ('ACOR','CORP')
        )
        SELECT
            EXTRACT(year FROM dlycaldt)::INTEGER AS year,
            COUNT(*) AS observations,
            COUNT(DISTINCT permno) AS securities,
            COUNT(DISTINCT primaryexch) AS exchanges
        FROM j
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    universe.to_csv(args.output_dir / "ordinary_common_universe_yearly.csv", index=False)

    print("")
    print("Metadata QA complete.", flush=True)
    print(summary.to_string(index=False), flush=True)
    print("")
    print(f"Invalid metadata intervals: {len(invalid):,}", flush=True)
    print(f"Overlapping metadata intervals: {len(overlap):,}", flush=True)
    print(f"Outputs: {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
