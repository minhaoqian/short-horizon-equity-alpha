"""Inventory Stage 1G exception extraction requirements from cached audit."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.target_exception_inventory import main
if __name__ == '__main__':
    main()
