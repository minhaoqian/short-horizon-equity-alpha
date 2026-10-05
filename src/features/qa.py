"""Small synthetic fixtures and descriptive output. No CRSP file access."""
from datetime import date, timedelta
from pathlib import Path
import csv
from .baseline import compute_features


def synthetic_fixture(n=85):
    calendar = []
    day = date(2020,1,1)
    while len(calendar) < n:
        if day.weekday() < 5:
            calendar.append(day)
        day += timedelta(days=1)
    rows, previous = {}, 100.0
    for i,d in enumerate(calendar):
        r = (i%7-3)/1000
        close = previous*(1+r)
        rows[d] = dict(dlyprc=close,dlyprevprc=previous,dlyopen=previous*1.001,
            dlyret=r,dlyfacprc=1.0,dlyorddivamt=0.0,dlynonorddivamt=0.0,
            dlyvol=1000.0,dlycap=1000.0,dlyprcflg='TR',dlydelflg='N',
            dlyretdurflg='D1',source_prev_date=calendar[i-1] if i else None,
            event_type='none',event_verified=True,event_known_date=d,
            volume_verified=True,cap_verified=True)
        previous = close
    return calendar, rows


def write_fixture_table(path):
    calendar, rows = synthetic_fixture()
    t = calendar[75]
    missing = dict(rows)
    missing.pop(calendar[73])
    records = []
    for scenario, data in [('complete',rows),('missing_security_row',missing)]:
        for name,f in compute_features(calendar,data,t).items():
            records.append(dict(scenario=scenario,feature=name,signal_date=t,raw=f.raw,
                missing=f.missing,reason=f.reason,n_valid=f.n_valid,
                window_start=f.positions[0],window_end=f.positions[-1],calendar_positions=len(f.positions)))
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as file:
        writer = csv.DictWriter(file,fieldnames=list(records[0]))
        writer.writeheader();writer.writerows(records)
    return records
