from datetime import date
import pytest
from src.portfolio.fallback import first_exit,entry_assumption

CAL=[date(2003,1,x) for x in (10,13,14,15,16,17,21)]


def test_scheduled_and_first_open_not_best_price():
    r=first_exit(CAL,CAL[0],{CAL[0]:10.,CAL[1]:100.})
    assert r['delay']==0
    r=first_exit(CAL,CAL[0],{CAL[1]:5.,CAL[2]:100.})
    assert r['delay']==1 and r['actual_date']==CAL[1]


@pytest.mark.parametrize('delay',[1,2,3,4,5])
def test_all_five_exact_global_delay_positions(delay):
    r=first_exit(CAL,CAL[0],{CAL[delay]:2.})
    assert r['delay']==delay and r['actual_date']==CAL[delay]


def test_after_cap_price_ignored_and_halt_known_at_cap_close():
    r=first_exit(CAL,CAL[0],{CAL[6]:10.})
    assert r['status']=='unresolved_execution' and r['known_date']==CAL[5]


def test_missing_entry_canceled_without_chasing():
    for x in (None,0.,-1.,float('nan')):assert entry_assumption(x)=='canceled_missing_open'
    assert entry_assumption(1.)=='assumed_entry'


def test_incomplete_calendar_is_pending_not_extended_or_imputed():
    assert first_exit(CAL[:2],CAL[0],{})['status']=='administrative_pending'
    with pytest.raises(ValueError):first_exit(CAL,CAL[0],{},10)


def test_verified_pure_split_and_received_asset_not_zero_multiplier():
    from src.portfolio.fallback import verified_split_multiplier
    pure={'dispaymenttype':'SS','distype':'FRS','disdetailtype':'STKSPL',
          'disfacshr':1.,'disfacpr':1.,'dispermno':0}
    assert verified_split_multiplier(pure)==2.
    received={'dispaymenttype':'OS','distype':'SP','disdetailtype':'SECMRG',
              'disfacshr':-1.,'disfacpr':0.,'dispermno':87033}
    assert verified_split_multiplier(received) is None


def test_successor_positive_open_does_not_establish_unknown_quantity():
    from src.portfolio.fallback import admissible_liquidation
    assert not admissible_liquidation(10.,None)
    assert not admissible_liquidation(10.,0.)
    assert admissible_liquidation(10.,-5.)
