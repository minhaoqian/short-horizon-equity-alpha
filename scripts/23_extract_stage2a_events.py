"""Global Stage 2A event extraction, explicit --execute and single login only."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data.stage2a_event_extraction import main
if __name__=='__main__':main()
