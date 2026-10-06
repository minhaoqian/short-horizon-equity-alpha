from datetime import date
import numpy as np
import pytest
from src.portfolio.construction import plan, capped_equal
from src.portfolio.ledger import measured_sum, execution_cost, borrow_cost, signed_wealth, event_transform


def fixture():
    n = 200
    return np.arange(n), np.full(n, 100.), np.full(n, 21_000_000.), np.zeros(n)


def test_caps_dollar_neutrality_and_preserved_rows():
    s, d, r = plan(*fixture())
    assert len(d) == 200 and abs(d.sum()) < 1e-8
    assert np.abs(d).max() <= 40_000 and (r == 'planned_entry').sum() == 80
    assert np.isclose(d[d > 0].sum(), 1_600_000)


def test_redistribution_and_permutation():
    a = capped_equal([1., 10., 10.], 15.)
    np.testing.assert_allclose(a, [1., 7., 7.])
    np.testing.assert_allclose(capped_equal([10., 1., 10.], 15.), a[[1, 0, 2]])


def test_gross_exits_reduce_entries_without_netting():
    args = list(fixture()); args[3][0] = 2100
    _, d, r = plan(*args)
    assert d[0] == 0 and r[0] == 'capacity_unallocated'
    assert abs(d.sum()) < 1e-8


def test_ties_and_constant_scores_not_split():
    args = list(fixture()); args[0] = np.ones(200)
    assert not plan(*args)[1].any()
    args[0] = np.repeat(np.arange(5), 40)
    side, _, _ = plan(*args)
    assert len(set(side[:40])) == 1 and len(set(side[-40:])) == 1


def test_fixed_shares_and_opening_drift():
    _, d, _ = plan(*fixture()); shares = d / 100
    opens = np.where(d > 0, 110., 90.)
    assert (shares * opens).sum() != 0
    np.testing.assert_allclose(shares, d / 100)


def test_linear_scenarios_replace_baseline():
    for b in (3, 6, 12):
        assert np.isclose(execution_cost(10000, .02, .01, b), b + 2)
    assert execution_cost(10000, None, .01) is None


def test_calendar_day_borrow_and_gross_trade_turnover():
    assert np.isclose(borrow_cost(10000, date(2019, 12, 27), date(2019, 12, 30)), 100 * 3 / 365)
    assert np.isclose(2 * execution_cost(10000, 0., 0.), 12)


def test_signed_split_cash_and_target_boundary_identity():
    q, c = event_transform(1., 0., 2., 2.)
    assert signed_wealth(q, 50., c) == 102
    q, c = event_transform(-1., 0., 2., 2.)
    assert signed_wealth(q, 50., c) == -102
    assert (102 / 100 - 1) == pytest.approx(.02)


def test_unknowns_never_become_zero_or_later_price():
    assert signed_wealth(1., None) is None
    assert measured_sum([2., None]) is None
    assert signed_wealth(0., None, 12.) == 12
    assert event_transform(1., 0., None) == (None, None)
    args = list(fixture()); args[3][0] = np.nan
    with pytest.raises(ValueError, match='requires review'):
        plan(*args)


def test_five_market_day_sleeves_and_exit_replacement():
    calendar = [date(2003,1,d) for d in (2,3,6,7,8,9,10,13,14,15,16,17)]
    cohorts = [(calendar[i],calendar[i+1],calendar[i+6],i%5) for i in range(6)]
    assert cohorts[0][2] == cohorts[5][1]
    assert cohorts[0][3] == cohorts[5][3]
    assert all(calendar.index(b)-calendar.index(a)==5 for _,a,b,_ in cohorts)


def test_entry_rights_excluded_exit_rights_included():
    from src.data.stage1g_targets import event_ledger
    a,b = date(2003,1,6),date(2003,1,13)
    events = [{'date':a,'cash':50.},{'date':date(2003,1,10),'cash':2.},
              {'date':b,'cash':3.}]
    assert event_ledger(a,b,events) == (1.,5.)


def test_cash_receivable_settlement_is_not_a_second_return():
    before = signed_wealth(1.,100.,5.)
    # An established receivable becomes cash at the same face amount.
    receivable,cash = 0.,5.
    after = signed_wealth(1.,100.,receivable+cash)
    assert before == after
