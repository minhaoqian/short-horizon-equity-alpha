from datetime import date
import pytest
from src.data.stage1g_targets import event_ledger, wealth_target, EXPECTED, ROOT, OUT


def test_open_to_open_without_events():
    assert wealth_target(100, 105, 0) == pytest.approx(0.05)


def test_entry_excluded_exit_included_and_no_reinvestment():
    a, b = date(2020, 1, 2), date(2020, 1, 9)
    q, cash = event_ledger(a, b, [
        {'date':a, 'cash':100, 'share_multiplier':2},
        {'date':date(2020, 1, 6), 'cash':2},
        {'date':b, 'cash':3},
        {'date':date(2020, 1, 10), 'cash':500},
    ])
    assert (q, cash) == (1, 5)
    assert wealth_target(100, q*90, cash) == pytest.approx(-0.05)


def test_split_cash_previous_share_basis_and_exit_split():
    a, b = date(2020, 1, 2), date(2020, 1, 9)
    split_day = date(2020, 1, 6)
    events = [{'date':split_day,'share_multiplier':2}, {'date':split_day,'cash':3},
              {'date':b,'cash':4,'share_multiplier':1.5}]
    # Same-day cash is per pre-event share, independent of row ordering.
    assert event_ledger(a,b,events) == (3,11)
    assert event_ledger(a,b,list(reversed(events))) == (3,11)
    assert wealth_target(100,3*30,11) == pytest.approx(0.01)


def test_cash_delisting_retains_cash_to_planned_exit_without_double_return():
    # Settlement replaces the parent; subsequent cash accrues no interest.
    assert wealth_target(100,0,110+2) == pytest.approx(0.12)
    with pytest.raises(ValueError):
        wealth_target(0,110,0)


def test_local_dataset_integrity_and_accounting():
    p = OUT/'targets_5d.parquet'
    if not p.exists():
        pytest.skip('Licensed local output unavailable')
    import duckdb
    c=duckdb.connect()
    c.execute(f"CREATE VIEW t AS SELECT * FROM read_parquet('{p}')")
    assert dict(c.execute('SELECT label_status,count(*) FROM t GROUP BY 1').fetchall()) == EXPECTED
    assert c.execute('SELECT count(*),count(DISTINCT(permno,signal_date)),count(target_5d) FROM t').fetchone() == (6699101,6699101,6676750)
    assert c.execute("SELECT count(*) FROM t WHERE label_reason IS NULL OR label_reason='' OR metadata_role<>'outcome_metadata_not_predictors'").fetchone()[0] == 0
    assert c.execute("SELECT count(*) FROM t WHERE (target_5d IS NOT NULL) IS DISTINCT FROM (label_status IN ('measurable_ordinary_event_adjusted','measurable_cash_only_delisting'))").fetchone()[0] == 0
    assert c.execute('SELECT max(abs((target_5d+1)*entry_open-security_value-cash_claims)) FROM t').fetchone()[0] < 1e-8
    # Plain price paths provide an independently specified special-case identity.
    assert c.execute('''SELECT max(abs(target_5d-(exit_open/entry_open-1))) FROM t
        WHERE label_status='measurable_ordinary_event_adjusted' AND NOT period_factor_event
        AND NOT cumulative_factor_event AND NOT interior_ordinary AND NOT exit_ordinary
        AND NOT interior_nonordinary AND NOT exit_nonordinary''').fetchone()[0] < 1e-12
    assert c.execute('''SELECT count(*) FROM t WHERE label_status='measurable_cash_only_delisting'
        AND (security_value<>0 OR terminal_parent_quantity<>0 OR cash_claims<=0)''').fetchone()[0] == 0
    assert c.execute(f'''SELECT count(*) FROM t FULL OUTER JOIN read_parquet(
        '{ROOT/'data/interim/target_boundary_audit_parts'}/*.parquet') a USING(permno,signal_date)
        WHERE t.permno IS NULL OR a.permno IS NULL OR t.entry_date IS DISTINCT FROM a.entry_date
          OR t.exit_date IS DISTINCT FROM a.exit_date''').fetchone()[0] == 0
    c.close()
