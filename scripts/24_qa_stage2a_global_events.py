"""Bounded global event layer QA; no feature, model or portfolio computation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.features.global_event_qa import main
if __name__=='__main__':main()
