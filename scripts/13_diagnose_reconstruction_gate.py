"""Run Stage 1G coverage and largest-error diagnostics from local caches."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data.reconstruction_diagnostics import main

if __name__ == '__main__':
    main()
