"""Security Market Line (CAPM) for one company. Pure arithmetic, no I/O.

The SML is E[R] = Rf + beta * ERP. Two returns are placed on it:

* required return — the CAPM cost of equity at the company's beta (a point ON the line);
* implied return  — the cost of equity at which the DCF value per share equals today's market price,
  i.e. the return an investor buying at the market price earns if the forecast comes true.

Implied minus required is the CAPM alpha of the model: above the line the stock looks cheap for its
risk, below the line it looks expensive. Capital-structure weights are held at market values, the same
weights the WACC uses, so the implied cost of equity is consistent with the discount rate.
"""
from __future__ import annotations

import math


def required_return(risk_free_rate, beta, equity_risk_premium):
    """CAPM expected return at `beta`."""
    return risk_free_rate + beta * equity_risk_premium


def line(risk_free_rate, equity_risk_premium, beta_max=2.0, n=41):
    """(betas, returns) along the SML from beta 0 to `beta_max`."""
    betas = [beta_max * i / (n - 1) for i in range(n)]
    return betas, [required_return(risk_free_rate, b, equity_risk_premium) for b in betas]


def implied_wacc(value_at, market_price, lo, hi=0.40, tol=1e-6, max_iter=80):
    """Discount rate at which `value_at(wacc)` (intrinsic value per share) equals `market_price`.

    `value_at` must be decreasing in wacc over [lo, hi]; it may return None where no value exists.
    Returns None when the market price is outside the range the model can produce on that interval."""
    if not (isinstance(market_price, (int, float)) and math.isfinite(market_price) and market_price > 0):
        return None

    def f(w):
        v = value_at(w)
        return None if v is None or not math.isfinite(v) else v - market_price

    f_lo, f_hi = f(lo), f(hi)
    if f_lo is None or f_hi is None or f_lo < 0 or f_hi > 0:
        return None
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = f(mid)
        if f_mid is None:
            return None
        if f_mid > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def implied_cost_of_equity(wacc, after_tax_cost_of_debt, equity_weight, debt_weight):
    """Back out Ke from WACC = We * Ke + Wd * Kd(1 - t), holding the weights fixed."""
    if equity_weight <= 0:
        return None
    return (wacc - debt_weight * after_tax_cost_of_debt) / equity_weight


def implied_beta(cost_of_equity, risk_free_rate, equity_risk_premium):
    """Beta at which the SML passes through `cost_of_equity`."""
    if equity_risk_premium <= 0 or cost_of_equity is None:
        return None
    return (cost_of_equity - risk_free_rate) / equity_risk_premium
