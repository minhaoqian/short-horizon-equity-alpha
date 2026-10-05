"""Local-only event sufficiency diagnostic; no WRDS connection."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data.stage1g_event_resolution import main
if __name__=='__main__':main()
