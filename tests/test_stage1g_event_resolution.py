from datetime import date
from pathlib import Path
import duckdb
import pytest
from src.data.stage1g_event_resolution import entitled


def test_exdate_ownership_handles_preentry_market_gap_and_exit():
    entry=date(2012,10,31);exit_=date(2012,11,7)
    assert not entitled(entry,exit_,date(2012,10,29))
    assert not entitled(entry,exit_,entry)
    assert entitled(entry,exit_,exit_)
    assert not entitled(entry,exit_,date(2012,11,8))


def test_cached_resolution_preserves_missing_endpoints_and_cash_timing():
    p=Path(__file__).resolve().parents[1]/'data/interim/stage1g_extraction/event_resolution_cases.parquet'
    if not p.exists():pytest.skip('Licensed diagnostic cache not available')
    c=duckdb.connect();c.execute(f"CREATE VIEW q AS SELECT * FROM read_parquet('{p}')")
    assert c.execute('SELECT count(*) FROM q WHERE missing_entry').fetchone()[0]==7596
    assert c.execute('SELECT count(*) FROM q WHERE exit_flag').fetchone()[0]==6916
    assert c.execute('SELECT count(*) FROM q WHERE exit_no_flag').fetchone()[0]==787
    assert c.execute('SELECT count(*) FROM q WHERE resolved AND (missing_entry OR exit_no_flag)').fetchone()[0]==0
    assert c.execute("SELECT count(*) FROM q WHERE resolution='resolved_cash_claim_by_exit' AND (delamtdt>exit_date OR terminal_cash_count<1 OR NOT actual_delist_in_window)").fetchone()[0]==0
    n,keys=c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)) FROM q').fetchone()
    assert n==keys
