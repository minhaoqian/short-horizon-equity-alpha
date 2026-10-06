"""Run only the approved Stage3A fixed development protocol."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.models.stage3a_pipeline import run
from src.models.stage3a_audit import run as audit
if __name__=='__main__':
    run()
    audit()
