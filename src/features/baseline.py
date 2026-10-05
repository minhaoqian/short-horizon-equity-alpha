"""Calendar-indexed baseline functions for synthetic/local-fixture QA only."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, log1p, prod
from statistics import mean, stdev
from .returns import admitted_return, actual_price, event_free


@dataclass(frozen=True)
class Feature:
    raw: float | None
    reason: str
    n_valid: int
    positions: tuple

    @property
    def missing(self):
        return self.raw is None


def finite(x):
    return isinstance(x, (int, float)) and isfinite(x)


def compute_features(calendar, rows, t):
    """rows: {global_date: allowlisted daily fields}. Never consult labels/eligibility.

    Positions retain absent rows, and only positions <= t are read. Calendar must
    be explicitly supplied by caller, not inferred from this security's rows.
    """
    if len(set(calendar)) != len(calendar) or list(calendar) != sorted(calendar):
        raise ValueError('Global calendar must be unique and sorted')
    if t not in calendar:
        raise ValueError('Signal date absent from global calendar')
    idx = calendar.index(t)

    def window(start, stop, extract, minimum, operation):
        positions = tuple(calendar[max(0, start):stop+1])
        if start < 0:
            return Feature(None, 'insufficient_calendar_history', 0, positions)
        values = [extract(i) for i in range(start, stop+1)]
        valid = [v for v in values if finite(v)]
        if len(valid) < minimum:
            return Feature(None, 'insufficient_valid_observations', len(valid), positions)
        result = operation(valid)
        if not finite(result):
            return Feature(None, 'nonfinite_result', len(valid), positions)
        return Feature(result, 'observed', len(valid), positions)

    def ret(i):
        if i == 0:
            return None
        value, _ = admitted_return(rows.get(calendar[i]), rows.get(calendar[i-1]), calendar[i], calendar[i-1])
        return value

    def dollar(i):
        row = rows.get(calendar[i])
        if not row or not actual_price(row) or row.get('volume_verified') is not True:
            return None
        volume = row.get('dlyvol')
        return row['dlyprc']*volume if finite(volume) and volume >= 0 else None

    def turnover(i):
        dv = dollar(i)
        row = rows.get(calendar[i], {})
        cap = row.get('dlycap')
        if dv is None or not finite(cap) or cap <= 0 or row.get('cap_verified') is not True:
            return None
        return dv/(1000*cap)

    output = {
        'reversal_5': window(idx-4, idx, ret, 5, lambda x: -(prod(1+r for r in x)-1)),
        'momentum_60_skip5': window(idx-59, idx-5, ret, 55, lambda x: prod(1+r for r in x)-1),
        'volatility_20': window(idx-19, idx, ret, 20, stdev),
        'turnover_20': window(idx-19, idx, turnover, 15, lambda x: log1p(mean(x))),
        'dollar_liquidity_20': window(idx-19, idx, dollar, 15, lambda x: log1p(mean(x))),
    }
    prior = window(idx-20, idx-1, dollar, 15, mean)
    current = dollar(idx)
    shock_reason = prior.reason if prior.missing else ('current_dollar_volume_unavailable' if current is None else 'observed')
    output['volume_shock_20'] = Feature(
        None if prior.missing or current is None else log1p(current)-log1p(prior.raw),
        shock_reason, prior.n_valid, prior.positions+(t,))
    row = rows.get(t)
    previous = rows.get(calendar[idx-1]) if idx > 0 else None
    prices_ok = row and actual_price(row) and finite(row.get('dlyopen')) and row['dlyopen'] > 0
    output['intraday_1'] = Feature(row['dlyprc']/row['dlyopen']-1 if prices_ok else None,
        'observed' if prices_ok else 'invalid_or_missing_current_price', int(bool(prices_ok)), (t,))
    if not prices_ok or not actual_price(previous):
        reason = 'invalid_or_missing_open_or_previous_calendar_close'
    elif row.get('source_prev_date') != calendar[idx-1]:
        reason = 'previous_price_anchor_not_adjacent'
    elif not event_free(row, t):
        reason = 'eventful_or_unverified_interval'
    else:
        reason = 'observed'
    output['gap_1'] = Feature(row['dlyopen']/previous['dlyprc']-1 if reason == 'observed' else None,
        reason, int(reason == 'observed'), tuple(calendar[max(0,idx-1):idx+1]))
    return output
