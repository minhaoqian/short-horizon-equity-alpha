"""Approved reference-budget bookkeeping, never wealth/solvency measurement."""
from math import isfinite
import numpy as np
from scipy.stats import rankdata
from .construction import SLEEVE, capped_equal


class Reservations:
    def __init__(self):
        self.records = {}
        self.amounts = np.zeros((5, 2))  # long, short; never netted

    def quarantine(self, key, phase, side, entry_notional, known_date, reason):
        if key in self.records:
            raise ValueError('A position cannot be reserved twice')
        if phase not in range(5) or side not in ('long', 'short'):
            raise ValueError('Invalid phase/side')
        if not isfinite(entry_notional) or entry_notional <= 0:
            raise ValueError('Positive original EXECUTED entry notional required')
        record = {'phase':phase, 'side':side, 'original_entry_notional':entry_notional,
                  'reserve':entry_notional, 'known_date':known_date, 'reason':reason,
                  'release_date':None, 'release_evidence':None}
        self.records[key] = record
        self.amounts[phase, 0 if side == 'long' else 1] += entry_notional
        return record

    def release(self, key, evidence, as_of):
        """Security prices/delisting dates are not account termination evidence."""
        if not (evidence.get('account_obligation_terminated') is True
                and evidence.get('all_remaining_claims_terminated') is True
                and evidence.get('independent_account_source')
                and evidence.get('effective_date') is not None
                and evidence.get('known_date') is not None
                and max(evidence['effective_date'], evidence['known_date']) <= as_of):
            raise ValueError('Independent through-date COMPLETE termination required')
        r = self.records[key]
        if r['release_date'] is not None:
            raise ValueError('Reserve already released')
        if as_of < r['known_date']:
            raise ValueError('Release precedes quarantine')
        i = 0 if r['side'] == 'long' else 1
        self.amounts[r['phase'], i] -= r['reserve']
        r['reserve'] = 0.
        r['release_date'] = as_of
        r['release_evidence'] = evidence

    def budgets(self, retained=None):
        k = np.zeros((5,2)) if retained is None else np.asarray(retained, float)
        if k.shape != (5,2) or not np.isfinite(k).all() or (k < 0).any():
            raise ValueError('Known nonnegative retained commitments required')
        remaining = np.maximum(0., SLEEVE-self.amounts-k)
        paired = remaining.min(axis=1)
        matched_idle = remaining-paired[:,None]
        assert (matched_idle >= 0).all()
        return remaining, paired, matched_idle

    def opening_overcommitment(self, retained):
        k = np.asarray(retained, float)
        if k.shape != (5,2) or not np.isfinite(k).all() or (k < 0).any():
            raise ValueError('Known nonnegative commitments required')
        return np.maximum(0., self.amounts+k-SLEEVE)


def paired_plan(score, close, adv, exits, limit, blocked):
    """Frozen ranks/caps/ADV; only approved deployment allowance changes."""
    score, close, adv, exits = [np.asarray(x, float) for x in (score,close,adv,exits)]
    blocked = np.asarray(blocked, bool)
    if len({len(x) for x in (score,close,adv,exits,blocked)}) != 1:
        raise ValueError('Unmatched keys')
    if not isfinite(limit) or not 0 <= limit <= SLEEVE:
        raise ValueError('Invalid reference allowance')
    if not np.isfinite(exits).all() or (exits < 0).any():
        raise ValueError('Unknown exit flow must be explicitly blocked')
    valid = np.isfinite(score)
    side = np.zeros(len(score), int); dollars = np.zeros(len(score))
    reasons = np.full(len(score),'missing_forecast',dtype=object)
    reasons[valid] = 'middle_rank'
    if valid.sum() < 100 or np.ptp(score[valid]) == 0:
        reasons[valid] = 'insufficient_or_constant_pool'
        return side,dollars,reasons
    u = (rankdata(score[valid], method='average')-.5)/valid.sum()
    side[valid] = np.where(u >= .8,1,np.where(u <= .2,-1,0))
    if min((side == 1).sum(),(side == -1).sum()) < 25:
        reasons[valid] = 'insufficient_side_breadth'; side[:] = 0
        return side,dollars,reasons
    usable = np.isfinite(close)&(close > 0)&np.isfinite(adv)&(adv > 0)&~blocked
    capacities = np.zeros(len(score))
    capacities[usable] = np.minimum(.02*SLEEVE,
        np.maximum(0.,.01*adv[usable]-exits[usable]*close[usable]))
    amount = min(limit,capacities[side == 1].sum(),capacities[side == -1].sum())
    for sign in (-1,1):
        ix = side == sign
        dollars[ix] = sign*capped_equal(capacities[ix],amount)
        reasons[ix] = np.where(np.abs(dollars[ix]) > 0,'planned_entry',
            np.where(blocked[ix],'unresolved_execution_identity_lock',
            np.where(limit == 0,'no_new_paired_capital_available',
            np.where(usable[ix],'capacity_unallocated','missing_sizing_input'))))
    assert abs(dollars.sum()) < 1e-7
    assert np.abs(dollars).max() <= .02*SLEEVE+1e-8
    assert not dollars[blocked].any()
    return side,dollars,reasons


def interval_measurable(previous_mark, current_mark, quantity_verified,
                        event_terms_verified, expense_inputs_verified):
    """Availability mask only, no wealth differences or performance."""
    wealth = bool(previous_mark and current_mark and quantity_verified and event_terms_verified)
    return wealth, bool(expense_inputs_verified), bool(wealth and expense_inputs_verified)


class EntryBasisUnidentified(ValueError):
    """Queued pre-event shares cannot certify an executed-entry reserve basis."""


def verified_entry_multiplier(events):
    from .fallback import verified_split_multiplier
    multiplier=1.
    for event in events:
        m=verified_split_multiplier(event)
        if m is not None:
            multiplier*=m
        else:
            f=event.get('disfacshr')
            if f is not None and isfinite(f) and f!=0:
                raise EntryBasisUnidentified(
                    'Non-pure entry-day share transformation: fixed pre-event order quantity '
                    'and original executed entry notional are not certified; review required')
    return multiplier
