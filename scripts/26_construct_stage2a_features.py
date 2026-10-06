"""Bounded QA by default; --full builds approved cached panel after QA."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.features.panel import main
if __name__=='__main__':main()
