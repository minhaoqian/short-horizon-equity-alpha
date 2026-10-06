"""Generalized conditional reservation audit; performance is not implemented."""
import argparse
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.portfolio.reservation_audit import run
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--end',type=date.fromisoformat,default=date(2019,12,31))
    args=parser.parse_args()
    if not date(2003,1,2)<=args.end<=date(2019,12,31):parser.error('Development end date only')
    run(args.end)
    from src.portfolio.reservation_report import report, bounded_checks
    if args.end==date(2019,12,31):report()
    elif args.end==date(2003,4,30):bounded_checks()
