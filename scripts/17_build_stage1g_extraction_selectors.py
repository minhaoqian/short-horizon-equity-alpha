"""Build local selectors only; does not connect to WRDS."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data.stage1g_extraction_selectors import main
if __name__=='__main__':
    main()
