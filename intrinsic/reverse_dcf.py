"""Reverse DCF: which growth, margin or discount rate makes the DCF value equal today's market price.

The traditional DCF answers "what is the company worth on our assumptions?". The reverse DCF answers "what would
the company have to deliver for today's price to be fair?". It does NOT re-model anything: it takes the scenario's
own assumptions (as built by intrinsic.forecast.derive_assumptions, user overrides included), changes ONE driver,
and prices it with the same audited functions (forecast.project -> forecast.value), so the bridge from enterprise
value to equity (net debt incl. finance leases, cash, diluted shares, failure weighting for loss-makers) and the
terminal value are exactly those of the traditional DCF. With the driver at its original value the two engines
return the same price (asserted in tests).

Three modes, each solved on its own with everything else held constant:

  growth  a growth PREMIUM, in percentage points of revenue growth per year, added to the calibrated growth path:
          full in years 1..H/2, tapering linearly to zero by year H, so terminal growth and the steady state are
          untouched. The calibration (fade speed, centre) is not modified.
  margin  the long-run operating margin (before acquired-intangible amortisation) the margin path converges to;
          revenue, reinvestment rules, tax, WACC unchanged. Loss-makers keep their path length.
  wacc    the discount rate; cash flows unchanged. Must exceed terminal growth. A diagnostic, not a cost of capital.

Solver: f(x) = DCF price(x) - market price. The bounded interval is first scanned on a grid (finite values only;
points where the model has no value, e.g. a negative terminal NOPAT, are gaps that are never bracketed across).
  * no sign change            -> 'no_solution' (the price is outside what the bounds can produce; never widened)
  * one sign change           -> scipy.optimize.brentq inside that bracket -> 'solved' if the residual is within
                                 tolerance, else 'not_converged'
  * several sign changes      -> 'multiple': every root is reported and none is picked
Non-monotone scans are flagged even when one root exists.
"""
from __future__ import annotations

import math

from scipy.optimize import brentq

from intrinsic import forecast as dm

MODES = ('growth', 'margin', 'wacc')

# Economic bounds (documented, not widened to force a solution).
GROWTH_PREMIUM_BOUNDS = (-0.15, 0.30)   # pp/yr; +30 pp for five years is beyond what almost any large company sustains
MARGIN_BOUNDS = (0.0, 0.75)             # below 0: no going concern; above 75%: beyond any large non-financial company
WACC_MAX = 0.25
WACC_MIN_GAP = 0.005                    # WACC must exceed terminal growth by at least this (Gordon model stability)

GRID_POINTS = 61
PRICE_RTOL = 1e-4                       # residual tolerance: 0.01% of the market price
X_TOL = 1e-8
MAX_ITER = 200

# Diagnostic thresholds for warnings (not limits).
LARGE_PREMIUM = 0.10
WACC_NEAR_GROWTH = 0.01


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _with_driver(assumptions, key, value, note):
    """Shallow copy of the assumptions with one driver replaced; the scenario's own dict is never mutated."""
    drivers = dict(assumptions['drivers'])
    drivers[key] = {'value': value, 'source': 'user', 'note': note}
    return {**assumptions, 'drivers': drivers}


def reprice(assumptions, mode, x, *, net_debt, shares, horizon=10, mid_year=False):
    """(price, projection, valuation) with driver `mode` set to x, using forecast.project and forecast.value.

    Raises ValueError where the model has no value (same rules as the traditional DCF)."""
    if mode == 'growth':
        a = _with_driver(assumptions, 'growth_premium', x, 'reverse DCF growth premium')
    elif mode == 'margin':
        a = _with_driver(assumptions, 'margin_target', x, 'reverse DCF implied long-run margin')
    elif mode == 'wacc':
        g = assumptions['drivers']['terminal_growth']['value']
        if not x > g:
            raise ValueError('WACC must exceed terminal growth')
        a = _with_driver(assumptions, 'wacc', x, 'reverse DCF implied WACC')
    else:
        raise ValueError(f'unknown mode {mode}')
    proj = dm.project(a, horizon)
    val = dm.value(proj, a, net_debt=net_debt, shares=shares, mid_year=mid_year)
    return val['intrinsic_price'], proj, val


def solve(price_fn, market_price, lo, hi, grid_points=GRID_POINTS):
    """Find x in [lo, hi] with price_fn(x) = market_price. price_fn returns a price or None (no value).

    Returns {'status', 'root', 'roots', 'residual', 'iterations', 'monotone', 'scan', 'reason'}."""
    if not _num(market_price) or market_price <= 0:
        return {'status': 'invalid', 'reason': 'market price missing or not positive', 'root': None, 'roots': []}
    if not (_num(lo) and _num(hi) and lo < hi):
        return {'status': 'invalid', 'reason': 'invalid bounds', 'root': None, 'roots': []}

    def f(x):
        try:
            p = price_fn(x)
        except (ValueError, ZeroDivisionError, OverflowError):
            return None
        return p - market_price if _num(p) else None

    xs = [lo + (hi - lo) * i / (grid_points - 1) for i in range(grid_points)]
    fs = [f(x) for x in xs]
    finite = [(x, y) for x, y in zip(xs, fs) if y is not None]
    scan = {'x': xs, 'price': [None if y is None else y + market_price for y in fs]}
    base = {'root': None, 'roots': [], 'residual': None, 'iterations': None, 'scan': scan}
    if not finite:
        return {**base, 'status': 'no_value', 'monotone': None,
                'reason': 'the model produces no value anywhere in the interval'}
    diffs = [b[1] - a[1] for a, b in zip(finite, finite[1:])]
    signs = {d > 0 for d in diffs if abs(d) > 1e-12 * max(1.0, market_price)}
    monotone = len(signs) <= 1

    brackets = []
    for i in range(len(xs) - 1):
        a, b = fs[i], fs[i + 1]
        if a is None or b is None:
            continue                                   # never bracket across a gap
        if a == 0:
            brackets.append((xs[i], xs[i]))
        elif a * b < 0:
            brackets.append((xs[i], xs[i + 1]))
    if fs[-1] == 0:
        brackets.append((xs[-1], xs[-1]))
    if not brackets:
        above = all(y < 0 for _, y in finite)
        return {**base, 'status': 'no_solution', 'monotone': monotone,
                'reason': ('the market price is above every value the model produces within the bounds' if above else
                           'the market price is below every value the model produces within the bounds'),
                'price_range': (min(y for _, y in finite) + market_price, max(y for _, y in finite) + market_price)}

    roots, iters, converged = [], 0, True
    for a, b in brackets:
        if a == b:
            roots.append(a)
            continue
        def g(x):
            y = f(x)
            if y is None:
                raise ValueError('no model value inside the bracket')
            return y
        try:
            r, info = brentq(g, a, b, xtol=X_TOL, rtol=4 * 2.220446049250313e-16, maxiter=MAX_ITER,
                             full_output=True, disp=False)
        except (ValueError, RuntimeError):
            return {**base, 'status': 'not_converged', 'monotone': monotone, 'iterations': iters,
                    'reason': 'the model has no value inside the bracket, so the solver could not finish'}
        roots.append(r)
        iters += info.iterations
        converged = converged and info.converged
    if len(roots) > 1:
        return {**base, 'status': 'multiple', 'roots': roots, 'monotone': False, 'iterations': iters,
                'reason': f'{len(roots)} values of the driver reproduce the price; none is selected'}
    root = roots[0]
    res = f(root)
    ok = converged and res is not None and abs(res) <= PRICE_RTOL * market_price
    return {**base, 'status': 'solved' if ok else 'not_converged', 'root': root, 'roots': roots,
            'residual': res, 'iterations': iters, 'monotone': monotone,
            'reason': None if ok else 'the solver did not reach the price tolerance'}


def bounds(mode, assumptions):
    if mode == 'growth':
        return GROWTH_PREMIUM_BOUNDS
    if mode == 'margin':
        return MARGIN_BOUNDS
    g = assumptions['drivers']['terminal_growth']['value']
    return (g + WACC_MIN_GAP, WACC_MAX)


def original_value(mode, assumptions):
    d = assumptions['drivers']
    return {'growth': 0.0, 'margin': d['margin_target']['value'], 'wacc': d['wacc']['value']}[mode]


def implied(result, mode, market_price, *, net_debt, shares, risk_free_rate=None):
    """Solve one mode for a forecast.run result (one scenario). Returns a dict for display and tests."""
    if 'projection' not in result or 'valuation' not in result:
        return {'mode': mode, 'status': 'not_valued', 'reason': 'the scenario has no DCF value', 'warnings': []}
    a = result['assumptions']
    horizon = result['projection']['horizon']
    lo, hi = bounds(mode, a)

    def price(x):
        return reprice(a, mode, x, net_debt=net_debt, shares=shares, horizon=horizon)[0]

    out = {'mode': mode, 'bounds': (lo, hi), 'original': original_value(mode, a), 'warnings': [],
           **solve(price, market_price, lo, hi)}
    if out['status'] == 'solved':
        _, proj, val = reprice(a, mode, out['root'], net_debt=net_debt, shares=shares, horizon=horizon)
        out['projection'], out['valuation'] = proj, val
    out['warnings'] += _warnings(mode, out, a, risk_free_rate)
    return out


WARNING_TEXT = {
    'non_monotone': 'The value does not move in one direction across the range; check the solution.',
    'large_premium': 'Requires {pp:.1f} extra points of revenue growth a year for five years: far above the '
                     'persistence observed for companies of this size.',
    'margin_above_latest': 'Requires a long-run margin of {x:.1%}, more than 5 points above the latest {m0:.1%}.',
    'wacc_below_rf': 'Implied WACC {x:.2%} is below the risk-free rate ({rf:.2%}): no investor would accept a risky '
                     'stock at that return, so the price embeds growth or margins above the forecast.',
    'wacc_near_growth': 'Implied WACC is within 1 point of terminal growth: the value is extremely sensitive here.',
}


def _warnings(mode, out, a, rf):
    """[(code, params)]; English text via WARNING_TEXT[code].format(**params)."""
    w = []
    if out.get('monotone') is False and out['status'] == 'solved':
        w.append(('non_monotone', {}))
    if out['status'] != 'solved':
        return w
    x, d = out['root'], a['drivers']
    if mode == 'growth' and x > LARGE_PREMIUM:
        w.append(('large_premium', {'pp': x * 100}))
    if mode == 'margin':
        m0 = d['margin_start']['value']
        if _num(m0) and x > m0 + 0.05:
            w.append(('margin_above_latest', {'x': x, 'm0': m0}))
    if mode == 'wacc':
        g = d['terminal_growth']['value']
        if _num(rf) and x < rf:
            w.append(('wacc_below_rf', {'x': x, 'rf': rf}))
        if x - g < WACC_NEAR_GROWTH:
            w.append(('wacc_near_growth', {}))
    return w


def warning_text(code, params):
    return WARNING_TEXT[code].format(**params)


def growth_paths(result, solved):
    """Per-year growth and revenue for Intrinsic and for the market-implied path (if solved)."""
    rows = result['projection']['rows']
    out = {'year': [r['year'] for r in rows], 'growth': [r['growth'] for r in rows],
           'revenue': [r['revenue'] for r in rows]}
    if solved and solved.get('status') == 'solved' and solved.get('projection'):
        irows = solved['projection']['rows']
        out['implied_growth'] = [r['growth'] for r in irows]
        out['implied_revenue'] = [r['revenue'] for r in irows]
    return out


def cagr(start, end, years):
    if not (_num(start) and _num(end)) or start <= 0 or end <= 0 or years <= 0:
        return None
    return (end / start) ** (1 / years) - 1


def run_all(result, market_price, *, net_debt, shares, risk_free_rate=None):
    return {m: implied(result, m, market_price, net_debt=net_debt, shares=shares, risk_free_rate=risk_free_rate)
            for m in MODES}
