from datetime import date
from decimal import Decimal
import pytest
from src.portfolio.settlement import (entitlement, credit_cash, applies,
                                     certify_reference, delivery_gated_exit)

CAL = [date(2003, 3, 31)] + [date(2003, 4, x) for x in (1, 2, 3, 4, 7, 8, 9, 10, 11)]


@pytest.mark.parametrize('scenario', ['D0', 'D2', 'D5'])
def test_signed_identity_and_fixed_cash_for_all_scenarios(scenario):
    a, b = entitlement('712.593305', scenario), entitlement('-712.593305', scenario)
    for k in ('ads_equivalent', 'whole_ads', 'fractional_ads', 'fractional_cash'):
        assert b[k] == -a[k]
    assert a['whole_ads'] == 381
    assert a['whole_ads'] + a['fractional_ads'] == a['ads_equivalent']
    assert a['fractional_cash'] == a['fractional_ads'] * Decimal('51.35')
    assert not a['historical_delivery_identified']


def test_no_cohort_netting_or_fractional_trade():
    a, b = entitlement(1, 'D0'), entitlement(-1, 'D0')
    assert a['whole_ads'] == b['whole_ads'] == 0
    assert a['fractional_cash'] > 0 and b['fractional_cash'] < 0


def test_cash_credit_once_and_short_liability_preserved():
    c = {'amount': Decimal('-2.1'), 'credit_date': CAL[2], 'credited': False}
    assert credit_cash(c, CAL[1]) == 0 and not c['credited']
    assert credit_cash(c, CAL[2]) == Decimal('-2.1')
    assert credit_cash(c, CAL[3]) == 0 and c['credited']


def test_first_open_only_and_delivery_gate():
    r = delivery_gated_exit(CAL, CAL[0], CAL[2], {CAL[0]: 500, CAL[2]: 10, CAL[3]: 20})
    assert r['date'] == CAL[2] and r['delay'] == 2


def test_cap_not_restarted_and_exact_day_five_allowed():
    assert delivery_gated_exit(CAL, CAL[0], CAL[5], {CAL[5]: 1})['delay'] == 5
    r = delivery_gated_exit(CAL, CAL[0], CAL[6], {CAL[6]: 1})
    assert r['state'] == 'unresolved_execution' and r['known_date'] == CAL[5]


def test_missing_open_does_not_create_execution_and_incomplete_is_pending():
    assert delivery_gated_exit(CAL, CAL[0], CAL[0], {})['state'] == 'unresolved_execution'
    assert delivery_gated_exit(CAL[:2], CAL[0], CAL[2], {})['state'] == 'administrative_pending'


def test_adapter_cannot_repair_other_events():
    e = dict(permno=20124, disexdt=CAL[0], dispermno=87033,
             dispaymenttype='OS', distype='SP', disdetailtype='SECMRG')
    assert applies(e)
    for field, wrong in [('permno', 1), ('disexdt', CAL[1]), ('dispermno', 1)]:
        assert not applies(dict(e, **{field: wrong}))


@pytest.mark.parametrize('field,wrong', [('dlycaldt', CAL[0]), ('dlyprcflg', 'BA'),
                                      ('dlyprc', 51.36), ('permno', 20124)])
def test_reference_cannot_be_substituted(field, wrong):
    r = dict(permno=87033, dlycaldt=date(2003, 3, 28), dlyprc=51.35, dlyprcflg='TR')
    assert certify_reference([r]) == Decimal('51.35')
    with pytest.raises(ValueError):
        certify_reference([dict(r, **{field: wrong})])


def test_duplicate_reference_rejected():
    with pytest.raises(ValueError):
        certify_reference([{}, {}])


def fixture_position(q):
    return {'permno':20124, 'asset_permno':20124, 'current_shares':q,
            'state':'outstanding', 'cash_claims':[{'source':'prior_parent_claim'}],
            'split_events':0}


@pytest.mark.parametrize('q', [200., -200.])
def test_adapter_preserves_existing_claim_and_signed_inventory(q):
    from types import SimpleNamespace
    from src.portfolio.settlement_audit import apply_actions
    e = dict(permno=20124, disexdt=CAL[0], dispermno=87033,
             dispaymenttype='OS', distype='SP', disdetailtype='SECMRG',
             disfacshr=-1., disfacpr=-1.)
    p = fixture_position(q)
    apply_actions(p, [e], CAL[0], SimpleNamespace(delists=None), 'D5')
    assert p['current_shares'] == q/200*107
    assert p['asset_permno'] == 87033 and p['state'] == 'outstanding'
    assert p['cash_claims'] == [{'source':'prior_parent_claim'}]
    assert not p['scenario_cash_claim']['credited']
    assert p['delivery_date'] == CAL[5]


def test_other_merger_remains_unresolved_no_generic_ratio_or_short_extinction():
    from types import SimpleNamespace
    from src.portfolio.settlement_audit import apply_actions
    p = fixture_position(-7)
    e = dict(permno=20124, disexdt=CAL[1], dispermno=21936,
             dispaymenttype='OS', distype='SP', disdetailtype='SECMRG',
             disfacshr=-1., disfacpr=-1.)
    apply_actions(p, [e], CAL[1], SimpleNamespace(delists=None), 'D0')
    assert p['state'] == 'unresolved_execution'
    assert p['last_verified_quantity'] == -7 and p['current_shares'] is None
    assert p['cash_claims'] == [{'source':'prior_parent_claim'}]


def test_same_date_split_and_cash_use_prior_owned_basis():
    from types import SimpleNamespace
    from src.portfolio.settlement_audit import apply_actions
    p = fixture_position(10)
    split = dict(permno=20124, dispaymenttype='SS', distype='FRS',
                 disdetailtype='STKSPL', dispermno=0, disfacshr=1., disfacpr=1.)
    cash = dict(permno=20124, dispaymenttype='USD', distype='CD',
                disfacshr=0., disfacpr=0., disdivamt=2., dispaydt=None, disseqnbr=1)
    apply_actions(p, [split, cash], CAL[1], SimpleNamespace(delists=None), 'D0')
    assert p['current_shares'] == 20
    assert p['cash_claims'][-1]['signed_amount'] == 20
    assert p['cash_claims'][-1]['prior_share_basis'] == 10
