"""Synthetic QA only; no historical data readers or performance metrics."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.features.qa import write_fixture_table
if __name__ == '__main__':
    p=Path(__file__).resolve().parents[1]/'results/tables/stage2a/synthetic_feature_qa.csv'
    rows=write_fixture_table(p)
    print(f'Wrote {len(rows)} synthetic feature/scenario rows to {p}')
