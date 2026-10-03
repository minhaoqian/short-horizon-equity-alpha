"""CRSP CIZ definition-grounded return reconstruction, not target construction."""
from math import isfinite


def reconstruct_returns(price, previous_price, period_factor, nonordinary, ordinary):
    """Return (price return, total return) for the SOURCE return interval.

    The previous price may precede the prior trading day. No missing value is
    filled. Nonordinary and ordinary amounts are on the source previous-price
    basis; cumulative price factors cannot replace the period factor.
    """
    fields = (price, previous_price, period_factor, nonordinary, ordinary)
    if any(x is None or not isfinite(x) for x in fields):
        return None, None
    if price < 0 or previous_price <= 0 or period_factor < 0:
        return None, None
    price_return = (price * period_factor + nonordinary) / previous_price - 1
    total_return = (price * period_factor + nonordinary + ordinary) / previous_price - 1
    return price_return, total_return


def rounding_bound(price, previous_price, period_factor, reconstructed, amounts):
    """Conservative six-decimal input rounding propagation, including prices.

    This checks consistency with export precision, not precision of the original
    CRSP values. It does not identify individual true unrounded inputs.
    """
    delta = 0.5e-6
    if previous_price <= delta:
        return None
    numerator_bound = abs(price) * delta + abs(period_factor) * delta + delta**2 + amounts * delta
    return delta + (numerator_bound + abs(1 + reconstructed) * delta) / (previous_price - delta)


def reconstruct_adjusted_returns(price, previous_price, period_factor, nonordinary,
                                 ordinary, current_cumulative, previous_cumulative):
    """Same accounting on a common cumulative-price basis with factor transport.

    previous_cumulative must refer to the source previous price's date, not a
    missing immediately preceding row. This expression is an algebraic basis
    check, not independent economic evidence or an open-to-open target.
    """
    fields = (price, previous_price, period_factor, nonordinary, ordinary,
              current_cumulative, previous_cumulative)
    if any(x is None or not isfinite(x) for x in fields):
        return None, None
    if price < 0 or previous_price <= 0 or period_factor < 0 or min(current_cumulative, previous_cumulative) <= 0:
        return None, None
    adjusted = price / current_cumulative
    previous_adjusted = previous_price / previous_cumulative
    transport = period_factor * current_cumulative / previous_cumulative
    return ((adjusted * transport + nonordinary / previous_cumulative) / previous_adjusted - 1,
            (adjusted * transport + (nonordinary + ordinary) / previous_cumulative) / previous_adjusted - 1)


def return_span_trading_days(flag):
    """Official CRSP RD duration, not a calendar-day inference."""
    if flag in ('D1', 'D2', 'D3', 'D4', 'DU'):
        return 1
    if flag in tuple(f'P{i}' for i in range(1, 10)):
        return int(flag[1]) + 1
    return None
