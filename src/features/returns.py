"""Conservative fixture admission. Verification evidence is supplied, not inferred.

Live CRSP status/event adapters have not yet been approved or implemented.
"""
from math import isfinite


def positive(x):
    return isinstance(x, (int,float)) and isfinite(x) and x > 0


def actual_price(row):
    return bool(row and row.get('dlyprcflg') == 'TR' and positive(row.get('dlyprc')))


def event_free(row, date):
    return bool(row and row.get('dlyfacprc') == 1 and row.get('dlyorddivamt') == 0
        and row.get('dlynonorddivamt') == 0 and row.get('dlydelflg') == 'N'
        and row.get('event_verified') is True and row.get('event_type') == 'none'
        and row.get('event_known_date') is not None and row['event_known_date'] <= date)


def admitted_return(row, previous, date, previous_date):
    if not actual_price(row) or not actual_price(previous):
        return None, 'missing_or_unverified_close'
    if row.get('source_prev_date') != previous_date or not positive(row.get('dlyprevprc')):
        return None, 'previous_price_anchor_not_adjacent'
    if abs(row['dlyprevprc']-previous['dlyprc']) > 1e-6:
        return None, 'previous_price_mismatch'
    if row.get('dlyretdurflg') not in ('D1','D2','D3','D4','DU'):
        return None, 'multiperiod_or_unknown_return'
    if row.get('dlydelflg') != 'N':
        return None, 'delisting_or_unknown_storage_flag'
    known = row.get('event_known_date')
    if row.get('event_verified') is not True or known is None or known > date:
        return None, 'event_not_verified_by_close'
    if row.get('event_type') not in ('none','ordinary_cash','pure_split','ordinary_cash_and_split'):
        return None, 'unresolved_nonordinary_or_received_asset'
    r, f, o, n = (row.get(k) for k in ('dlyret','dlyfacprc','dlyorddivamt','dlynonorddivamt'))
    if not all(isinstance(v,(int,float)) and isfinite(v) for v in (r,f,o,n)) or f <= 0 or r < -1:
        return None, 'invalid_return_fields'
    if n != 0:
        return None, 'nonordinary_amount_not_admitted_in_fixture'
    rebuilt = (row['dlyprc']*f+o+n)/row['dlyprevprc']-1
    if abs(rebuilt-r) > 1e-6:
        return None, 'return_reconstruction_mismatch'
    return r, 'observed'
