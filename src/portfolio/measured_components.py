"""Identified signed subtotals, never full-account wealth or return substitution."""
from dataclasses import dataclass, field
import math
import numpy as np

COMPLETE = 'complete_within_declared_component_scope'
PARTIAL = 'partial_identified_subtotal'
UNKNOWN = 'no_identified_active_component'
SD_LABEL = 'annualized SD of conditional measured-component daily contribution'
HAC_LABEL = 'nominal inference for the conditional measured-component mean'


def finite(x):
    return x is not None and np.isfinite(x)


def asset_increment(q, previous_open, opening, multiplier=1.):
    if not all(finite(x) for x in (q, previous_open, opening, multiplier)):
        return None
    if previous_open <= 0 or opening <= 0 or multiplier <= 0:
        return None
    return q * (multiplier * opening - previous_open)


def terminal_asset_increment(q, previous_open):
    """The prior parent component; only valid inside verified cash replacement."""
    return -q * previous_open if finite(q) and finite(previous_open) and previous_open > 0 else None


def execution_primitives(notional, sigma, participation):
    if not finite(notional) or notional < 0:
        return None, None
    fixed = -notional * .0006
    impact = (-notional * .10 * math.sqrt(participation) * sigma
              if finite(sigma) and sigma >= 0 and finite(participation) and participation >= 0 else None)
    return fixed, impact


def borrow_primitive(basis, days):
    if not finite(basis) or basis < 0 or days < 0:
        return None
    return -basis * .01 * days / 365


@dataclass
class Subtotal:
    identified: int = 0
    unknown: int = 0
    amount: float = 0.

    def add(self, value):
        if finite(value):
            self.identified += 1
            self.amount += float(value)
        else:
            self.unknown += 1

    def result(self):
        status = PARTIAL if self.unknown and self.identified else UNKNOWN if self.unknown else COMPLETE
        # A genuinely empty scope has a structural zero; an active unknown scope does not.
        amount = self.amount if self.identified or not self.unknown else None
        return amount, status


@dataclass
class DailyJournal:
    """Keep known primitive expenses even when asset increments are unknown."""
    scopes: dict = field(default_factory=lambda: {k: Subtotal() for k in ('gross', 'fixed', 'impact', 'borrow')})
    net: Subtotal = field(default_factory=Subtotal)

    def add(self, kind, value):
        self.scopes[kind].add(value)
        self.net.add(value)

    def result(self):
        out = {}
        for k, scope in {**self.scopes, 'net': self.net}.items():
            out[k], out[k + '_status'] = scope.result()
            out[k + '_identified_count'] = scope.identified
            out[k + '_unknown_count'] = scope.unknown
        return out


def nominal_hac(values, lag):
    """Bartlett sandwich on the original grid; missing scores are not returns."""
    x = np.asarray(values, dtype=float)
    mask = np.isfinite(x)
    n = int(mask.sum())
    mean = float(x[mask].mean()) if n else None
    result = dict(label=HAC_LABEL, lag=lag, calendar_dates=len(x), numeric_dates=n,
                  mean=mean, se=None, nominal_t=None, ci_low=None, ci_high=None,
                  status='insufficient_or_constant')
    if n <= lag + 1:
        return result
    s = np.zeros(len(x))
    s[mask] = x[mask] - mean
    variance = (s @ s + 2 * sum((1 - l / (lag + 1)) * (s[l:] @ s[:-l])
                               for l in range(1, min(lag, len(x)-1) + 1))) / n**2
    if not finite(variance) or variance <= 0:
        return result
    se = math.sqrt(variance)
    result.update(se=se, nominal_t=mean/se, ci_low=mean-1.96*se,
                  ci_high=mean+1.96*se, status='nominal_conditional_only')
    return result


def qualified_hac(values, lag, coverage):
    """Attach coverage only when original-grid/numeric denominators agree."""
    h = nominal_hac(values, lag)
    if any(h[key] != coverage[key] for key in ('calendar_dates', 'numeric_dates')):
        raise ValueError('HAC and coverage calendar/measurement denominators disagree')
    return {**coverage, **h}
