"""Strict measurement primitives for the approved signed-asset ledger."""
from math import isfinite, sqrt


def measured_sum(values):
    values = list(values)
    if any(v is None or not isfinite(v) for v in values):
        return None
    return sum(values)


def execution_cost(notional, sigma, participation, linear_bp=6., impact=.10):
    if any(v is None or not isfinite(v) for v in (notional, sigma, participation)):
        return None
    if min(notional, sigma, participation) < 0:
        raise ValueError('Negative execution input')
    return notional * (linear_bp / 10000 + impact * sigma * sqrt(participation))


def borrow_cost(entry_notional, entry_date, cover_date, annual_bp=100.):
    if entry_notional is None or not isfinite(entry_notional):
        return None
    days = (cover_date - entry_date).days
    if days < 0 or entry_notional < 0:
        raise ValueError('Invalid borrow interval')
    return entry_notional * annual_bp / 10000 * days / 365


def signed_wealth(quantity, price, claims=0.):
    if quantity is None or claims is None or not isfinite(quantity) or not isfinite(claims):
        return None
    if quantity == 0:
        return claims
    if price is None or not isfinite(price) or price <= 0:
        return None
    return quantity * price + claims


def event_transform(quantity, cash, cash_per_prior_share=0., share_multiplier=1.):
    if any(v is None or not isfinite(v) for v in
           (quantity, cash, cash_per_prior_share, share_multiplier)):
        return None, None
    if share_multiplier <= 0:
        raise ValueError('Unverified share multiplier')
    return quantity * share_multiplier, cash + quantity * cash_per_prior_share
