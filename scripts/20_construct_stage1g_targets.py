"""Construct frozen next-open labels from local Stage 1G caches only."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.stage1g_targets import main
if __name__ == '__main__':
    main()
