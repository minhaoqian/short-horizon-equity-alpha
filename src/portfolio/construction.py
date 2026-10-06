"""Approved fixed-capital sleeve construction; no outcomes accepted as inputs."""
import numpy as np
from scipy.stats import rankdata

CAPITAL = 10_000_000.
SLEEVE = CAPITAL / 5


def capped_equal(capacities, amount):
    """Deterministic water filling, invariant to input ordering."""
    caps = np.asarray(capacities, float)
    if (not np.isfinite(caps).all() or (caps < 0).any()
            or not np.isfinite(amount) or amount < 0
            or amount > caps.sum() + 1e-8):
        raise ValueError('Invalid capacities or infeasible allocation')
    out = np.zeros(len(caps))
    active = np.ones(len(caps), bool)
    remaining = amount
    while active.any() and remaining > 1e-8:
        level = remaining / active.sum()
        limited = active & (caps <= level)
        if not limited.any():
            out[active] = level
            break
        out[limited] = caps[limited]
        remaining -= caps[limited].sum()
        active[limited] = False
    assert abs(out.sum() - amount) < 1e-7
    assert (out <= caps + 1e-8).all()
    return out


def plan(score, close, adv, scheduled_exit_shares):
    """Per-date universe already frozen; retain all input rows and reasons.

    scheduled_exit_shares are gross known quantities on the close-t share basis.
    An unknown exit commitment fails explicitly instead of assuming zero.
    """
    score, close, adv, exits = [np.asarray(v, float) for v in
                               (score, close, adv, scheduled_exit_shares)]
    if len({len(v) for v in (score, close, adv, exits)}) != 1:
        raise ValueError('Unmatched keys')
    if not np.isfinite(exits).all() or (exits < 0).any():
        raise ValueError('Unknown scheduled exit capacity requires review')
    valid = np.isfinite(score)
    side = np.zeros(len(score), int)
    dollars = np.zeros(len(score))
    reason = np.full(len(score), 'missing_forecast', dtype=object)
    reason[valid] = 'middle_rank'
    if valid.sum() < 100 or np.ptp(score[valid]) == 0:
        reason[valid] = 'insufficient_or_constant_pool'
        return side, dollars, reason
    u = (rankdata(score[valid], method='average') - .5) / valid.sum()
    side[valid] = np.where(u >= .8, 1, np.where(u <= .2, -1, 0))
    if min((side == 1).sum(), (side == -1).sum()) < 25:
        reason[valid] = 'insufficient_side_breadth'
        side[:] = 0
        return side, dollars, reason
    usable = np.isfinite(close) & (close > 0) & np.isfinite(adv) & (adv > 0)
    capacity = np.zeros(len(score))
    capacity[usable] = np.minimum(.02 * SLEEVE,
        np.maximum(0, .01 * adv[usable] - exits[usable] * close[usable]))
    amount = min(SLEEVE, capacity[side == 1].sum(), capacity[side == -1].sum())
    for s in (-1, 1):
        ix = side == s
        dollars[ix] = s * capped_equal(capacity[ix], amount)
        reason[ix] = np.where(np.abs(dollars[ix]) > 0, 'planned_entry',
                              np.where(usable[ix], 'capacity_unallocated', 'missing_sizing_input'))
    assert abs(dollars.sum()) < 1e-7
    assert (np.abs(dollars) <= .02 * SLEEVE + 1e-8).all()
    return side, dollars, reason
