"""Event-specific approved hypothetical settlement; never historical evidence."""
from datetime import date
from decimal import Decimal, ROUND_DOWN
from .fallback import positive_open

PARENT = 20124
SUCCESSOR = 87033
EVENT_DATE = date(2003, 3, 31)
QUOTE_DATE = date(2003, 3, 28)
REFERENCE = Decimal('51.35')
SCENARIOS = {'D0': date(2003, 3, 31), 'D2': date(2003, 4, 2),
             'D5': date(2003, 4, 7)}


def certify_reference(rows):
    """Certify the approved CRSP reference, NOT equality to a WSJ quotation."""
    if len(rows) != 1:
        raise ValueError('Exactly one reference row required')
    r = rows[0]
    if (r['permno'] != SUCCESSOR or r['dlycaldt'] != QUOTE_DATE
            or r['dlyprcflg'] != 'TR'
            or Decimal(str(r['dlyprc'])) != REFERENCE):
        raise ValueError('Approved same-date CRSP closing trade not certified')
    return REFERENCE


def applies(event):
    """No generic repair of other mergers or received-security events."""
    return (event.get('permno') == PARENT and event.get('disexdt') == EVENT_DATE
            and event.get('dispermno') == SUCCESSOR
            and event.get('dispaymenttype') == 'OS'
            and event.get('distype') == 'SP'
            and event.get('disdetailtype') == 'SECMRG')


def entitlement(quantity, scenario):
    q = Decimal(str(quantity))
    if not q.is_finite() or not q or scenario not in SCENARIOS:
        raise ValueError('Finite nonzero signed quantity and approved scenario required')
    e = q * Decimal('0.535')
    w = e.to_integral_value(rounding=ROUND_DOWN)
    f = e - w
    assert w + f == e and abs(f) < 1
    return {'ads_equivalent': e, 'whole_ads': w, 'fractional_ads': f,
            'fractional_cash': f * REFERENCE, 'credit_date': SCENARIOS[scenario],
            'historical_delivery_identified': False,
            'historical_cash_method_identified': False,
            'reference_is_certified_wsj_quotation': False}


def credit_cash(claim, on_date):
    """Convert a signed receivable/obligation once; independent of asset sale."""
    if claim['credited'] or on_date < claim['credit_date']:
        return Decimal(0)
    claim['credited'] = True
    return claim['amount']


def delivery_gated_exit(calendar, scheduled, delivery, opens):
    """Original scheduled+5 cap; delivery never restarts the clock."""
    if len(set(calendar)) != len(calendar) or list(calendar) != sorted(calendar):
        raise ValueError('Unique sorted global calendar required')
    i = calendar.index(scheduled)
    for lag in range(6):
        if i + lag >= len(calendar):
            return {'state': 'administrative_pending', 'date': None, 'delay': None}
        d = calendar[i + lag]
        if d >= delivery and positive_open(opens.get(d)):
            return {'state': 'assumed_exited', 'date': d, 'delay': lag}
    return {'state': 'unresolved_execution', 'date': None, 'delay': None,
            'known_date': calendar[i + 5]}
