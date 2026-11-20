"""Final verdict: Buy / Hold / Sell probabilities from the model's own valuation range. Pure arithmetic.

The three scenarios are not arbitrary: conservative and optimistic are the 20th and 80th percentiles of the
model's measured out-of-sample forecast errors, and base is the central case. They define a distribution of
intrinsic value per share:

  * lognormal when all values are positive:  median = base, sigma from ln(optimistic / conservative) / (2 z80)
  * normal otherwise (a value at or below zero cannot be logged): mean = base, sd from (optimistic - conservative)
  * one-sided when a scenario is missing: the available side sets the spread, assumed symmetric

With a margin of safety m around the market price P:

  Buy  = Prob(value > P x (1 + m))     the stock looks cheap by more than the margin
  Sell = Prob(value < P x (1 - m))     the stock looks expensive by more than the margin
  Hold = the rest                      keep it if you own it; no reason to buy or sell

The verdict is Buy or Sell only when that side holds a MAJORITY (> 50%) of the outcomes; otherwise Hold, either
because value is close to the price or because the range is too wide for a conviction. Limitation: the bands measure forecast error in revenue and
margin only, not uncertainty in the discount rate or terminal growth, so the spread is a lower bound.
This is what the model's numbers say, not a recommendation for anyone's portfolio.
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
    """{'kind', 'center', 'spread'} or None when the range cannot define one."""
    if not _num(base):
        return None
    lo, hi = (conservative if _num(conservative) else None), (optimistic if _num(optimistic) else None)
    if lo is None and hi is None:
        return None
    if base > 0 and all(x is None or x > 0 for x in (lo, hi)):
        if lo is not None and hi is not None:
            spread = (math.log(hi) - math.log(lo)) / (2 * Z80)
        else:
            spread = abs(math.log(hi if hi is not None else lo) - math.log(base)) / Z80
        kind, center = 'lognormal', math.log(base)
    else:
        if lo is not None and hi is not None:
            spread = (hi - lo) / (2 * Z80)
        else:
            spread = abs((hi if hi is not None else lo) - base) / Z80
        kind, center = 'normal', base
    if not spread > 0:
        return None
    return {'kind': kind, 'center': center, 'spread': spread}


def cdf(dist, x):
    """Prob(value <= x)."""
    if dist['kind'] == 'lognormal':
        return 0.0 if x <= 0 else _phi((math.log(x) - dist['center']) / dist['spread'])
    return _phi((x - dist['center']) / dist['spread'])


def pdf(dist, x):
    if dist['kind'] == 'lognormal':
        if x <= 0:
            return 0.0
        z = (math.log(x) - dist['center']) / dist['spread']
        return math.exp(-0.5 * z * z) / (x * dist['spread'] * math.sqrt(2 * math.pi))
    z = (x - dist['center']) / dist['spread']
    return math.exp(-0.5 * z * z) / (dist['spread'] * math.sqrt(2 * math.pi))


def quantile(dist, p):
    """Inverse CDF by bisection (enough for chart limits)."""
    lo, hi = (1e-9, math.exp(dist['center'] + 10 * dist['spread'])) if dist['kind'] == 'lognormal' else (
        dist['center'] - 10 * dist['spread'], dist['center'] + 10 * dist['spread'])
    for _ in range(100):
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
            'one_sided': not all(_num(prices.get(k)) for k in ('conservative', 'optimistic'))}
