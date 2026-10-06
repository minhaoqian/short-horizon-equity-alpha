"""Approved conditional component journal; no full-book NAV or selection."""
import argparse
import sys
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.portfolio.measured_replay import run

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--end',type=date.fromisoformat,default=date(2019,12,31))
    a=p.parse_args()
    if not date(2003,1,3)<=a.end<=date(2019,12,31):p.error('Development reporting dates only')
    run(a.end)
