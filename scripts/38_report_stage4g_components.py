"""Reconcile local primitive journal and create coverage-qualified aggregates."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.portfolio.measured_report import report
if __name__=='__main__':
    report()
