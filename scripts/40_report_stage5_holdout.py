"""Audit the saved holdout forecasts and report prespecified diagnostics."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.evaluation.stage5_report import report
if __name__=='__main__':report()
