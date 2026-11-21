"""Final verdict: Buy / Hold / Sell shares from the model's own valuation range. Pure arithmetic.

The three scenarios define a distribution of intrinsic value per share by construction: base is the MEDIAN, and
conservative / optimistic are placed at the 20th / 80th percentiles (they come from the 20th / 80th percentiles of the
model's measured out-of-sample revenue and margin forecast errors). The fit is a SPLIT distribution, so it passes
exactly through all three points even when they are asymmetric around the base:

  * split lognormal when all values are positive: median = base,
        sigma_below = ln(base / conservative) / z80,  sigma_above = ln(optimistic / base) / z80
  * split normal otherwise (a value at or below zero cannot be logged), same rule in levels
  * one-sided when a scenario is missing: the available side sets both halves (assumed symmetric)

Half of the probability lies on each side of the base, so the CDF is continuous and integrates to one; the density
has a step at the median when the two sides differ. (Until November 2026 a single sigma was fitted from
ln(optimistic / conservative), which placed the scenarios at other percentiles when they were asymmetric, e.g. the
15th and 75th for Microsoft.)

With a margin of safety m around the market price P (classification thresholds on VALUE, not recommended prices):

  Buy  = Prob(value > P x (1 + m))     the model value exceeds the price by more than the margin
  Sell = Prob(value < P x (1 - m))     the model value falls short of the price by more than the margin
  Hold = the rest

The verdict is Buy or Sell only when that side holds a MAJORITY (> 50%) of the outcomes; otherwise Hold.

What these numbers are: probabilities CONDITIONAL on the model's assumptions. They are not calibrated against
realised returns and are not the probability that the share price rises or falls. Limitations: the scenario bands
shift revenue and margin together and the conservative case also sets terminal RONIC = WACC, so the percentile
placement is a modelling assumption; uncertainty in the discount rate and terminal growth is not included.
"""
from __future__ import annotations

import math

Z80 = 0.8416212335729143      # standard-normal 80th percentile
ACTIONS = ('sell', 'hold', 'buy')


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def value_distribution(conservative, base, optimistic):
    """{'kind', 'center', 'spread_lo', 'spread_hi', 'spread'} or None when the range cannot define one."""
    if not _num(base):
        return None
    lo, hi = (conservative if _num(conservative) else None), (optimistic if _num(optimistic) else None)
    if lo is None and hi is None:
        return None
    log = base > 0 and all(x is None or x > 0 for x in (lo, hi))
    tr = math.log if log else (lambda x: x)
    c = tr(base)
    s_lo = (c - tr(lo)) / Z80 if lo is not None else None
    s_hi = (tr(hi) - c) / Z80 if hi is not None else None
    s_lo, s_hi = (s_lo if s_lo is not None else s_hi), (s_hi if s_hi is not None else s_lo)
    if not (s_lo > 0 and s_hi > 0):
        return None              # scenarios not ordered conservative < base < optimistic
    return {'kind': 'lognormal' if log else 'normal', 'center': c, 'spread_lo': s_lo, 'spread_hi': s_hi,
            'spread': (s_lo + s_hi) / 2}


def _z(dist, x):
    """Standardised distance from the median, using the sigma of x's side. None for x <= 0 under a lognormal."""
    if dist['kind'] == 'lognormal':
        if x <= 0:
            return None
        u = math.log(x) - dist['center']
    else:
        u = x - dist['center']
    return u / (dist['spread_lo'] if u < 0 else dist['spread_hi'])


def cdf(dist, x):
    """Prob(value <= x)."""
    z = _z(dist, x)
    return 0.0 if z is None else _phi(z)


def pdf(dist, x):
    z = _z(dist, x)
    if z is None:
        return 0.0
    sigma = dist['spread_lo'] if z < 0 else dist['spread_hi']
    dens = math.exp(-0.5 * z * z) / (sigma * math.sqrt(2 * math.pi))
    return dens / x if dist['kind'] == 'lognormal' else dens


def quantile(dist, p):
    """Inverse CDF by bisection (enough for chart limits)."""
    s = max(dist['spread_lo'], dist['spread_hi'])
    lo, hi = (1e-9, math.exp(dist['center'] + 10 * s)) if dist['kind'] == 'lognormal' else (
        dist['center'] - 10 * s, dist['center'] + 10 * s)
    for _ in range(200):
        mid = (lo + hi) / 2
        if cdf(dist, mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def verdict(prices, market_price, margin=0.15):
    """prices: {'conservative', 'base', 'optimistic'} per share. Returns None when no distribution exists."""
    if not _num(market_price) or market_price <= 0 or not 0 <= margin < 1:
        return None
    dist = value_distribution(prices.get('conservative'), prices.get('base'), prices.get('optimistic'))
    if dist is None:
        return None
    buy_at, sell_at = market_price * (1 + margin), market_price * (1 - margin)
    p_buy = 1 - cdf(dist, buy_at)
    p_sell = cdf(dist, sell_at)
    p_hold = max(0.0, 1 - p_buy - p_sell)
    probs = {'sell': p_sell, 'hold': p_hold, 'buy': p_buy}
    action = 'buy' if p_buy > 0.5 else ('sell' if p_sell > 0.5 else 'hold')
    return {'action': action, 'probabilities': probs, 'distribution': dist, 'margin': margin,
            'buy_above': buy_at, 'sell_below': sell_at, 'market_price': market_price,
            'prob_above_market': 1 - cdf(dist, market_price),
            # B: the most one could pay and keep the margin of safety on the BASE value (not a classification threshold)
            'price_with_margin': prices['base'] * (1 - margin) if prices['base'] > 0 else None,
            'one_sided': not all(_num(prices.get(k)) for k in ('conservative', 'optimistic'))}
