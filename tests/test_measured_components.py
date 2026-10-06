from datetime import date
import numpy as np
import pytest
from src.portfolio.measured_components import (
    asset_increment, terminal_asset_increment, execution_primitives,
    borrow_primitive, DailyJournal, Subtotal, nominal_hac, UNKNOWN, PARTIAL)


def test_signed_split_transport_and_prior_basis():
    assert asset_increment(10, 100, 51, 2) == 20
    assert asset_increment(-10, 100, 51, 2) == -20
    assert asset_increment(10, 100, 50, 2) == 0
    # A $2 prior-share entitlement is not doubled by the split.
    assert asset_increment(10, 100, 49, 2) + 10*2 == 0


def test_cash_termination_no_double_count():
    for q in (10, -10):
        j = DailyJournal()
        j.add('gross', terminal_asset_increment(q, 100))
        j.add('gross', q*105)
        assert j.result()['gross'] == q*5
        # Receipt subsequently transfers an established claim: no second income.
        j.add('gross', 0)
        assert j.result()['gross'] == q*5


def test_quarantine_never_writeoff_or_reserve_mark():
    j = DailyJournal(); j.add('gross', None)
    j.add('borrow', borrow_primitive(20_000, 3))
    r = j.result()
    assert r['gross'] is None and r['gross_status'] == UNKNOWN
    assert r['net'] == -20_000*.01*3/365 and r['net_status'] == PARTIAL


def test_all_unknown_not_manufactured_by_idle_zero():
    j = DailyJournal(); j.add('gross', None)
    r = j.result(); assert r['net'] is None
    assert r['fixed'] == 0  # Separate verified absence, not inserted in net.


def test_known_cash_unknown_bundle_disjoint():
    j = DailyJournal(); j.add('gross', None); j.add('gross', -25)
    assert j.result()['gross'] == -25
    assert j.result()['gross_status'] == PARTIAL


def test_partial_cost_fixed_retained():
    f, i = execution_primitives(1000, None, .01)
    assert f == -.6 and i is None
    j = DailyJournal(); j.add('fixed', f); j.add('impact', i)
    assert j.result()['net'] == -.6


def test_unknown_quantity_proxy_not_cost_base():
    assert execution_primitives(None, .03, .01) == (None, None)
    assert borrow_primitive(None, 1) is None


def test_abs_execution_and_frozen_cost():
    assert execution_primitives(10000, .02, .01) == pytest.approx((-6, -2))
    assert borrow_primitive(10000, 3) == pytest.approx(-300/365)


def test_missing_marks_no_gap_bridge():
    assert asset_increment(10, 100, None) is None
    assert asset_increment(10, None, 103) is None
    assert asset_increment(10, 103, 104) == 10


def test_empty_scope_and_identified_flat():
    assert Subtotal().result()[0] == 0
    s = Subtotal(); s.add(0); s.add(None)
    assert s.result() == (0, PARTIAL)


def test_hac_original_grid():
    x = np.array([1., np.nan, 4., 2., 8., -3., 1., 0.])
    r = nominal_hac(x, 2); m = np.nanmean(x)
    s = np.where(np.isfinite(x), x-m, 0)
    v = (sum(s*s)+2*(2/3*(s[1:]@s[:-1])+1/3*(s[2:]@s[:-2])))/7**2
    assert r['se'] == pytest.approx(np.sqrt(v))
    assert r['numeric_dates'] == 7 and r['calendar_dates'] == 8
    assert r['mean'] == m
    assert not np.isclose(r['se'], nominal_hac(x[np.isfinite(x)], 2)['se'])


def test_hac_constant_insufficient():
    assert nominal_hac([1]*30, 20)['se'] is None
    assert nominal_hac([None]*30, 4)['mean'] is None
    assert nominal_hac([1,2,3], 4)['se'] is None


def test_cash_termination_missing_prior_mark_keeps_claim():
    j=DailyJournal();j.add('gross',terminal_asset_increment(-10,None));j.add('gross',-1050)
    assert j.result()['gross']==-1050
    assert j.result()['gross_unknown_count']==1


def test_no_principal_income_at_entry():
    j=DailyJournal()
    fixed,impact=execution_primitives(10_000,.02,.01)
    j.add('fixed',fixed);j.add('impact',impact)
    assert j.result()['gross']==0
    assert j.result()['net']==pytest.approx(-8)


def test_participation_only_previous_close_and_gross_not_net():
    from types import SimpleNamespace
    from src.portfolio.measured_replay import participation
    class Source:
        def row(self,p,d):
            assert d==date(2003,1,2)
            return SimpleNamespace(adv20=1_000_000,dlyprc=50,sigma20=.02)
    sigma,p=participation(Source(),1,date(2003,1,2),{1:200+300})
    assert sigma==.02 and p==.025


def test_missing_previous_cost_inputs_do_not_replace_with_future():
    from src.portfolio.measured_replay import participation
    class Source:
        def row(self,p,d): return None
    assert participation(Source(),1,date(2003,1,2),{1:100})==(None,None)
    assert execution_primitives(1000,*participation(Source(),1,date(2003,1,2),{1:100}))==(-.6,None)


def test_journal_writer_preserves_nulls_and_provenance(tmp_path):
    import pyarrow.parquet as pq
    from src.portfolio.measured_replay import JournalWriter
    path=tmp_path/'journal.parquet';writer=JournalWriter(path)
    writer.add(dict(candidate='fixture',key='1:2003-01-02',permno=1,phase=0,side='short',
                    date=date(2003,1,3),previous_date=date(2003,1,2),kind='gross',amount=None,
                    reason='unresolved_quantity',verified_entry_basis=None))
    writer.close();f=pq.read_table(path).to_pydict()
    assert f['amount']==[None] and f['verified_entry_basis']==[None]
    assert f['reason']==['unresolved_quantity']


def test_signed_subtotal_identity_without_null_substitution():
    j=DailyJournal()
    for kind,value in [('gross',10),('gross',None),('fixed',-2),('impact',None),('borrow',-1)]:j.add(kind,value)
    r=j.result();assert r['net']==7 and r['net_unknown_count']==2
    assert r['impact'] is None and r['net_status']==PARTIAL


def test_holdout_end_guard_before_source_access():
    from src.portfolio.measured_replay import run
    with pytest.raises(ValueError,match='development only'):
        run(date(2020,1,2))


def test_complete_ordinary_lifecycle_telescopes_without_principal():
    # Owned 10 shares; split to20; $2 prior-share cash; exit with20 at$52.
    j=DailyJournal()
    j.add('gross',asset_increment(10,100,49,2));j.add('gross',10*2)
    j.add('gross',asset_increment(20,49,52))
    assert j.result()['gross']==20*52-10*100+10*2
    short=DailyJournal()
    short.add('gross',asset_increment(-10,100,49,2));short.add('gross',-10*2)
    short.add('gross',asset_increment(-20,49,52))
    assert short.result()['gross']==-j.result()['gross']


def test_hac_coverage_keeps_full_calendar_and_partial_composition():
    from src.portfolio.measured_components import qualified_hac
    x=[1,None,2,-1,3,4,None,5]
    r=qualified_hac(x,2,dict(calendar_dates=8,numeric_dates=6,asset_interval_coverage=.5,
                             unresolved_positions_end=4))
    assert r['calendar_dates']==8 and r['numeric_dates']==6
    assert r['asset_interval_coverage']==.5 and r['unresolved_positions_end']==4
    assert r['label']=='nominal inference for the conditional measured-component mean'


def test_hac_coverage_denominator_mismatch_is_not_silently_accepted():
    from src.portfolio.measured_components import qualified_hac
    with pytest.raises(ValueError,match='denominators disagree'):
        qualified_hac([1,None,2,3],1,dict(calendar_dates=3,numeric_dates=3))
