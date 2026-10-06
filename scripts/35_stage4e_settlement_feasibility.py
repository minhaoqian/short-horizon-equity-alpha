"""Approved conditional settlement feasibility; never portfolio performance."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.portfolio.settlement_audit import run
from src.portfolio.settlement_report import run as report
if __name__ == '__main__':
    run()
    report()
