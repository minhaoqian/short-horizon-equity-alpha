"""Evaluate approved 1993–2019 development signals only, never holdout."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.evaluation.baseline import run
from src.evaluation.audit import run as audit
if __name__=='__main__':
    run()
    audit()
