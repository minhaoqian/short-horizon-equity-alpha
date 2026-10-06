"""Prespecified first-open/capped fallback primitives; no return calculations."""
from math import isfinite


def positive_open(value):
    return value is not None and isfinite(value) and value>0


def first_exit(calendar, scheduled, opens, maximum_delay=5):
    """Date-by-date first admissible open, never a best-price selection.

    Missing future calendar yields administrative pending, not cap failure.
    Caller must separately verify owned asset identity/quantity and events.
    """
    if maximum_delay != 5:
        raise ValueError('Approved maximum delay is five global dates')
    if len(set(calendar))!=len(calendar) or list(calendar)!=sorted(calendar):
        raise ValueError('Unique ordered global calendar required')
    index=calendar.index(scheduled)
    for delay in range(6):
        if index+delay>=len(calendar):
            return {'status':'administrative_pending','actual_date':None,'delay':None}
        date=calendar[index+delay]
        if positive_open(opens.get(date)):
            return {'status':'assumed_exit','actual_date':date,'delay':delay}
    return {'status':'unresolved_execution','actual_date':None,'delay':5,
            'known_date':calendar[index+5]}


def entry_assumption(open_value):
    return 'assumed_entry' if positive_open(open_value) else 'canceled_missing_open'


def verified_split_multiplier(event):
    """Pure-parent split only; a received asset is never a zero-share split."""
    if not (event.get('dispaymenttype')=='SS' and event.get('distype')=='FRS'
            and event.get('disdetailtype') in ('STKSPL','STKDIV')):
        return None
    linked=event.get('dispermno')
    if linked is not None and isfinite(linked) and linked!=0:return None
    f=event.get('disfacshr');p=event.get('disfacpr')
    if f is None or p is None or not isfinite(f) or not isfinite(p) or f<=-1 or abs(f-p)>1e-6:
        return None
    return 1+f


def admissible_liquidation(price,quantity):
    return positive_open(price) and quantity is not None and isfinite(quantity) and quantity!=0
