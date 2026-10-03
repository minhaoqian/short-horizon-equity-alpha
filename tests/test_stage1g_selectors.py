from datetime import date
import duckdb
from src.data.stage1g_extraction_selectors import merge_windows


def test_nested_adjacent_disjoint_and_security_isolation():
    c=duckdb.connect()
    c.execute('CREATE TABLE p(permno INTEGER,signal_date DATE,lo DATE,hi DATE,categories VARCHAR[])')
    for permno,lo,hi in [(1,1,10),(1,2,3),(1,11,12),(1,14,15),(2,2,3)]:
        c.execute('INSERT INTO p VALUES (?,?,?,?,?)',[permno,date(2020,1,lo),date(2020,1,lo),date(2020,1,hi),['test']])
    merge_windows(c,'p','m')
    assert c.execute('SELECT permno,day(lo),day(hi),source_observations FROM m ORDER BY permno,lo').fetchall()==[(1,1,12,3),(1,14,15,1),(2,2,3,1)]
    assert c.execute('SELECT sum(len(provenance)) FROM m').fetchone()[0]==5
