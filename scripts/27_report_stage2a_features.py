"""Offline descriptive Stage 2A report and final integrity/preprocessing gate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.features.report import main
if __name__=='__main__':main()
