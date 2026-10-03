"""Stage 1F edge-case QA for cumulative price adjustment factors.

Usage:
    python3 scripts/11_cumfac_edge_case_qa.py \
        data/interim/crsp_cumfac_1993_2025.parquet \
        data/raw/crsp_daily_1993_2025.csv.gz \
        data/raw/crsp_names_history.csv

Outputs:
    results/tables/stage1f/cumfac_edge_case_overall.csv
    results/tables/stage1f/cumfac_edge_case_eligible.csv
"""

from __future__ import annotations
import argparse
from pathlib import Path
import duckdb


def main():
    p=argparse.ArgumentParser()
    p.add_argument("cumfac", type=Path)
    p.add_argument("daily", type=Path)
    p.add_argument("names", type=Path)
    p.add_argument("--output-dir", type=Path, default=Path("results/tables/stage1f"))
    args=p.parse_args()

    for x in [args.cumfac,args.daily,args.names]:
        if not x.exists():
            raise FileNotFoundError(x)
    args.output_dir.mkdir(parents=True,exist_ok=True)

    fac=str(args.cumfac.resolve()).replace("'","''")
    daily=str(args.daily.resolve()).replace("'","''")
    names=str(args.names.resolve()).replace("'","''")

    con=duckdb.connect()
    con.execute("SET preserve_insertion_order=false")

    overall=con.execute(f"""
        SELECT
            COUNT(*) AS rows,
            SUM(CASE WHEN dlycumfacpr = 0 THEN 1 ELSE 0 END) AS zero_factor_rows,
            SUM(CASE WHEN dlycumfacpr < 0 THEN 1 ELSE 0 END) AS negative_factor_rows,
            SUM(CASE WHEN dlycumfacpr > 0 AND dlycumfacpr < 1e-12 THEN 1 ELSE 0 END) AS positive_lt_1e12,
            SUM(CASE WHEN dlycumfacpr >= 1e-12 AND dlycumfacpr < 1e-9 THEN 1 ELSE 0 END) AS factor_1e12_to_1e9,
            SUM(CASE WHEN dlycumfacpr >= 1e-9 AND dlycumfacpr < 1e-6 THEN 1 ELSE 0 END) AS factor_1e9_to_1e6,
            MIN(dlycumfacpr) AS min_factor
        FROM read_parquet('{fac}')
    """).fetchdf()
    overall.to_csv(args.output_dir/"cumfac_edge_case_overall.csv",index=False)

    con.execute(f"""
        CREATE TEMP TABLE names_locked AS
        SELECT CAST(permno AS BIGINT) permno,
               CAST(secinfostartdt AS DATE) startdt,
               CAST(secinfoenddt AS DATE) enddt
        FROM read_csv_auto('{names}',header=true,sample_size=200000)
        WHERE securitytype='EQTY'
          AND securitysubtype='COM'
          AND sharetype='NS'
          AND usincflg='Y'
          AND issuertype IN ('ACOR','CORP')
          AND primaryexch IN ('N','A','Q')
          AND tradingstatusflg='A'
    """)

    con.execute(f"""
        CREATE TEMP TABLE d AS
        SELECT DISTINCT
            CAST(permno AS BIGINT) permno,
            CAST(dlycaldt AS DATE) dlycaldt,
            TRY_CAST(dlyprc AS DOUBLE) dlyprc,
            TRY_CAST(dlyvol AS DOUBLE) dlyvol,
            TRY_CAST(dlycap AS DOUBLE) dlycap
        FROM read_csv_auto('{daily}',header=true,sample_size=200000)
    """)

    con.execute("""
        CREATE TEMP TABLE a AS
        SELECT *,
            AVG(ABS(dlyprc)*dlyvol) OVER (
                PARTITION BY permno ORDER BY dlycaldt
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) adv20,
            COUNT(ABS(dlyprc)*dlyvol) OVER (
                PARTITION BY permno ORDER BY dlycaldt
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ) adv20_obs
        FROM d
    """)

    eligible=con.execute(f"""
        WITH e AS (
            SELECT a.permno,a.dlycaldt
            FROM a
            JOIN names_locked n
              ON a.permno=n.permno
             AND a.dlycaldt BETWEEN n.startdt AND n.enddt
            WHERE ABS(a.dlyprc)>5
              AND a.dlycap>1000000
              AND a.adv20>20000000
              AND a.adv20_obs>=15
        ),
        x AS (
            SELECT e.*,f.dlycumfacpr
            FROM e
            LEFT JOIN read_parquet('{fac}') f
              USING (permno,dlycaldt)
        )
        SELECT
            COUNT(*) AS eligible_rows,
            SUM(CASE WHEN dlycumfacpr IS NULL THEN 1 ELSE 0 END) AS missing_factor,
            SUM(CASE WHEN dlycumfacpr = 0 THEN 1 ELSE 0 END) AS zero_factor,
            SUM(CASE WHEN dlycumfacpr < 0 THEN 1 ELSE 0 END) AS negative_factor,
            SUM(CASE WHEN dlycumfacpr > 0 AND dlycumfacpr < 1e-12 THEN 1 ELSE 0 END) AS positive_lt_1e12,
            SUM(CASE WHEN dlycumfacpr >= 1e-12 AND dlycumfacpr < 1e-9 THEN 1 ELSE 0 END) AS factor_1e12_to_1e9,
            SUM(CASE WHEN dlycumfacpr >= 1e-9 AND dlycumfacpr < 1e-6 THEN 1 ELSE 0 END) AS factor_1e9_to_1e6,
            MIN(dlycumfacpr) AS min_factor
        FROM x
    """).fetchdf()
    eligible.to_csv(args.output_dir/"cumfac_edge_case_eligible.csv",index=False)

    print("Overall:")
    print(overall.to_string(index=False))
    print("\nLocked eligible universe:")
    print(eligible.to_string(index=False))


if __name__=="__main__":
    main()
