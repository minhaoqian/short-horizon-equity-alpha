"""Evidence-supported entitlement arithmetic, separate from executable inventory."""
from decimal import Decimal


def merger_entitlement(parent_quantity, ordinary_ratio, ordinary_per_ads):
    """Signed ADS-equivalent claim; never certify an election, fill or settlement.

    Ratios must come from independent legal terms, not market prices/factors.
    Fractions are deliberately retained as claims, not rounded into inventory.
    """
    q, r, a = map(lambda x: Decimal(str(x)),
                  (parent_quantity, ordinary_ratio, ordinary_per_ads))
    if not all(x.is_finite() for x in (q, r, a)) or r <= 0 or a <= 0:
        raise ValueError('Finite quantity and positive documented ratios required')
    return {'ordinary_share_entitlement': q*r,
            'ads_equivalent_entitlement': q*r/a,
            'ads_ratio': r/a,
            'tradable_successor_quantity': None,
            'inventory_verified': False,
            'reason': 'election_delivery_fractional_claim_and_short_terms_unverified'}
