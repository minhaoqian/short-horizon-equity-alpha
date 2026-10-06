from decimal import Decimal
import pytest
from src.portfolio.successor import merger_entitlement


def test_documented_ratio_is_ads_not_ordinary_stock():
    r=merger_entitlement(200,'2.675',5)
    assert r['ads_ratio']==Decimal('0.535')
    assert r['ordinary_share_entitlement']==535
    assert r['ads_equivalent_entitlement']==107
    assert r['tradable_successor_quantity'] is None


def test_signed_short_obligation_and_fraction_are_not_extinguished():
    a=merger_entitlement(1,'2.675',5)
    b=merger_entitlement(-1,'2.675',5)
    assert b['ads_equivalent_entitlement']==-a['ads_equivalent_entitlement']
    assert b['ads_equivalent_entitlement']==Decimal('-0.535')
    assert not a['inventory_verified'] and not b['inventory_verified']


@pytest.mark.parametrize('q,r,a',[('NaN',2.675,5),(1,-1,5),(1,2.675,0)])
def test_missing_or_sentinel_terms_cannot_certify_ratio(q,r,a):
    with pytest.raises(ValueError):merger_entitlement(q,r,a)
