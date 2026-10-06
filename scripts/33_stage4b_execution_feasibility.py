"""Audit prespecified fallback execution only; no portfolio performance."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.portfolio.fallback_audit import run
from src.portfolio.fallback_report import run as report
if __name__=='__main__':
    run()
    report()
