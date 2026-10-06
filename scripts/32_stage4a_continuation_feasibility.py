"""Audit strict continuation feasibility only; never a portfolio backtest."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.portfolio.continuation import run
from src.portfolio.continuation_report import run as report
if __name__=='__main__':
    run()
    report()
