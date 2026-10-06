from datetime import date
import numpy as np
import pytest
from src.portfolio.construction import plan, SLEEVE
from src.portfolio.reservation import Reservations, paired_plan, interval_measurable

D = date(2003,3,31)


def test_asymmetric_reserve_shrinks_both_sides_without_netting():
    b = Reservations(); b.quarantine('long',0,'long',40000,D,'unknown')
    rem,paired,idle = b.budgets()
    np.testing.assert_allclose(rem[0],[1960000,2000000])
    assert paired[0] == 1960000 and idle[0,1] == 40000
    b.quarantine('short',0,'short',40000,D,'unknown')
    assert b.amounts.sum() == 80000 and b.budgets()[1][0] == 1960000


def test_cohorts_and_phases_do_not_net_or_borrow():
    b = Reservations()
    b.quarantine('one',0,'long',SLEEVE,D,'unknown')
    b.quarantine('two',1,'short',SLEEVE,D,'unknown')
    np.testing.assert_allclose(b.budgets()[1],[0,0,SLEEVE,SLEEVE,SLEEVE])
    assert b.amounts.sum() == 2*SLEEVE


def test_fixed_executed_entry_basis_and_no_duplicate_reserve():
    b = Reservations(); r=b.quarantine('a',2,'short',12345,D,'unknown')
    assert r['reserve'] == r['original_entry_notional'] == 12345
    assert 'asset_value' not in r and 'NAV' not in r
    with pytest.raises(ValueError):b.quarantine('a',2,'short',1,D,'unknown')


def test_known_overdue_commitments_and_exhaustion_are_budget_states():
    b=Reservations(); k=np.zeros((5,2));k[0]=[SLEEVE+10,100]
    assert b.budgets(k)[1][0] == 0
    assert b.opening_overcommitment(k)[0,0] == 10
    assert b.budgets(k)[1][1] == SLEEVE
    assert not hasattr(b,'solvent')


def test_existing_queued_entry_is_not_retroactively_canceled():
    b=Reservations(); queued=np.zeros((5,2));queued[0]=SLEEVE
    b.quarantine('new_event',0,'long',50000,D,'unknown')
    assert b.opening_overcommitment(queued)[0,0] == 50000
    assert queued[0,0] == SLEEVE
    assert b.budgets(queued)[1][0] == 0


@pytest.mark.parametrize('evidence',[{'delisting_date':D},{'later_price':100},
                                   {'security_cash_payment_date':D},{}])
def test_security_event_or_quote_cannot_release_an_account(evidence):
    b=Reservations();b.quarantine('a',0,'long',10,D,'unknown')
    with pytest.raises(ValueError):b.release('a',evidence,D)
    assert b.amounts.sum()==10


def test_release_requires_through_date_all_obligations_and_only_own_cohort():
    b=Reservations();b.quarantine('a',0,'short',10,D,'unknown')
    b.quarantine('b',0,'long',20,D,'unknown')
    proof=dict(account_obligation_terminated=True,all_remaining_claims_terminated=True,
               independent_account_source='synthetic audited delivery/claim receipt',
               effective_date=D,known_date=date(2003,4,2))
    with pytest.raises(ValueError):b.release('a',proof,D)
    b.release('a',proof,date(2003,4,2))
    assert b.amounts.sum()==20 and b.records['b']['reserve']==20
    with pytest.raises(ValueError):b.release('a',proof,date(2003,4,2))


def args():
    return [np.arange(300.),np.full(300,100.),np.full(300,21e6),np.zeros(300)]


def test_unreserved_plan_is_identical_to_frozen_plan():
    a=args();old=plan(*a);new=paired_plan(*a,SLEEVE,np.zeros(300,bool))
    for x,y in zip(old,new):np.testing.assert_array_equal(x,y)


def test_blocking_changes_capacity_not_ranks_and_preserves_all_keys():
    a=args();block=np.zeros(300,bool);block[[0,299]]=True
    side,dollars,reasons=paired_plan(*a,1e6,block)
    np.testing.assert_array_equal(side,plan(*a)[0])
    assert not dollars[block].any() and len(reasons)==300
    assert abs(dollars.sum())<1e-7 and dollars[dollars>0].sum()==pytest.approx(1e6)


def test_zero_allowance_no_new_orders_no_bankruptcy_interpretation():
    _,d,r=paired_plan(*args(),0,np.zeros(300,bool))
    assert not d.any() and 'no_new_paired_capital_available' in r


def test_missing_wealth_or_expenses_never_becomes_zero_return():
    assert interval_measurable(True,False,True,True,True)==(False,True,False)
    assert interval_measurable(True,True,True,True,False)==(True,False,False)
    assert interval_measurable(True,True,False,False,True)==(False,True,False)


@pytest.mark.parametrize('sign',['long','short'])
def test_quarantine_holds_original_signed_borrow_obligation_separate(sign):
    b=Reservations();q=-5 if sign=='short' else 5
    b.quarantine((1,D),0,sign,abs(q)*10,D,'unverified_successor')
    assert b.records[(1,D)]['side']==sign and b.amounts.sum()==50


def test_overdue_quantity_remains_committed_at_replacement():
    from src.portfolio.reservation_audit import retained_at_replacement
    tomorrow=date(2003,4,2)
    rows=[dict(phase=0,side='long',entry_notional=12,scheduled_exit_date=tomorrow),
          dict(phase=0,side='short',entry_notional=15,scheduled_exit_date=D)]
    k=retained_at_replacement(rows,{},D,tomorrow)
    np.testing.assert_array_equal(k[0],[0,15])


def test_signed_cash_claims_preserve_owned_basis_without_reserve_release():
    from src.portfolio.reservation_audit import add_claims
    p=dict(key='cohort',permno=1,signal_date=D,measured_claims_count=0)
    claims=[];journal=[]
    add_claims(p,[dict(disdivamt=2.,dispaydt=date(2003,4,2))],-5,D,claims,journal)
    assert claims[0]['signed_amount']==-10
    assert claims[0]['prior_owned_share_basis']==-5
    assert claims[0]['cash_state']=='established_measurable_receivable'


def test_later_declaration_never_certifies_opening_event_terms():
    from src.portfolio.reservation_audit import event_batch
    e=dict(disdeclaredt=date(2003,4,2))
    r=event_batch([e],None,[],D)
    assert r['unknown'] and r['multiplier'] is None and not r['terminal']


def test_quarantine_cannot_invent_successor_or_forget_signed_parent():
    from src.portfolio.reservation_audit import reserve_position
    p=dict(key='short',phase=2,side='short',entry_notional=500,state='outstanding',current_shares=-10)
    b=Reservations();reserve_position(p,b,D,'unknown',[dict(distype='SECMRG',dispermno=2)])
    assert p['last_verified_signed_quantity']==-10
    assert p['current_shares'] is None and p['unknown_successor_quantity'] is None
    assert p['linked_identifiers']==[2] and b.amounts[2,1]==500


def test_entry_nonpure_share_factor_stops_before_inventing_executed_notional():
    from src.portfolio.reservation import verified_entry_multiplier, EntryBasisUnidentified
    e=dict(distype='SP',dispaymenttype='OS',disdetailtype='SECDO',disfacshr=-.07,disfacpr=0.,dispermno=2)
    with pytest.raises(EntryBasisUnidentified):verified_entry_multiplier([e])


def test_entry_pure_split_retains_frozen_quantity_adjustment():
    from src.portfolio.reservation import verified_entry_multiplier
    e=dict(distype='FRS',dispaymenttype='SS',disdetailtype='STKSPL',disfacshr=1.,disfacpr=1.,dispermno=0)
    assert verified_entry_multiplier([e])==2


def test_entry_day_received_rights_without_parent_basis_change_not_owned():
    from src.portfolio.reservation import verified_entry_multiplier
    e=dict(distype='SP',dispaymenttype='OS',disdetailtype='SECSO',disfacshr=0.,disfacpr=0.,dispermno=2)
    assert verified_entry_multiplier([e])==1


def test_planned_proxy_never_acquires_an_executed_notional():
    b=Reservations();r=b.queued_proxy('queue',0,'long',123,D,'entry_basis')
    assert r['original_entry_notional'] is None
    assert r['planned_notional_reserve_proxy']==123
    assert b.executed_amounts.sum()==0 and b.planned_amounts.sum()==123
    assert b.budgets()[1][0]==SLEEVE-123


@pytest.mark.parametrize('side',['long','short'])
def test_unknown_queued_state_preserves_order_and_signed_obligations_without_inference(side):
    from src.portfolio.reservation_audit import reserve_queued_execution
    q=-10 if side=='short' else 10
    p=dict(key='queue',phase=2,side=side,planned_entry_notional=1000,
           order_shares=q,entry_notional=None,current_shares=None)
    b=Reservations();reserve_queued_execution(p,b,D,[dict(distype='SP',dispermno=2)])
    assert p['state']=='queued_execution_quantity_unresolved' and p['order_shares']==q
    for field in ('current_shares','entry_notional','actual_entry_date','executed_entry_notional','borrow_basis','unknown_wealth'):
        assert p[field] is None
    assert p['planned_notional_reserve_proxy']==1000
    assert b.amounts[2,0 if side=='long' else 1]==1000


def test_mixed_reserves_reconcile_and_do_not_net_sides_or_basis():
    b=Reservations();b.quarantine('fill',0,'long',300,D,'event')
    b.queued_proxy('queue',0,'short',200,D,'entry_basis')
    np.testing.assert_array_equal(b.amounts,b.executed_amounts+b.planned_amounts)
    assert b.amounts.sum()==500 and b.budgets()[1][0]==SLEEVE-300
    with pytest.raises(ValueError):b.queued_proxy('queue',0,'short',200,D,'duplicate')


def test_planned_proxy_release_requires_same_independent_account_evidence():
    b=Reservations();b.queued_proxy('queue',1,'short',100,D,'entry_basis')
    with pytest.raises(ValueError):b.release('queue',{'positive_open':50},D)
    proof=dict(account_obligation_terminated=True,all_remaining_claims_terminated=True,
               independent_account_source='synthetic complete canceled/settled order receipt',effective_date=D,known_date=D)
    b.release('queue',proof,D)
    assert b.amounts.sum()==b.planned_amounts.sum()==b.executed_amounts.sum()==0
