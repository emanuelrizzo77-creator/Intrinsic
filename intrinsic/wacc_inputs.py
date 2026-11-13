"""Intrinsic 27 — sourced market inputs for the discount rate.

Every value returns (value, source text) so the dashboard can show where it came from.

  risk-free rate   live US 10-year Treasury yield (Yahoo Finance ^TNX); falls back to the
                   dated year-end 2025 value in data/damodaran_market_inputs.json
  equity premium   Damodaran implied ERP for the S&P 500 at 1 January 2026 (dated snapshot)
  cost of debt     risk-free rate + default spread of the SYNTHETIC rating implied by
                   interest coverage (EBIT / interest expense), Damodaran's table for large
                   non-financial firms. This is the marginal cost of NEW borrowing today;
                   historical interest / average debt reflects old coupons and is shown only
                   for comparison.
  tax rate         MARGINAL_TAX from driver_forecast_27 (same rate the forecast converges to)

All of these are economic assumptions with a source, and remain editable.
"""
from __future__ import annotations

import json
import math
import os

from intrinsic.forecast import MARGINAL_TAX

from intrinsic.paths import ROOT

HERE = ROOT   # project root (intrinsic.paths)
INPUTS_FILE = os.path.join(HERE, 'data', 'damodaran_market_inputs.json')


def _snapshot():
    with open(INPUTS_FILE) as fh:
        return json.load(fh)


def risk_free_rate():
    """(rate, source). Live 10-year Treasury if available, else dated fallback."""
    try:
        import yfinance as yf
        hist = yf.Ticker('^TNX').history(period='10d')['Close'].dropna()
        if len(hist):
            rate = float(hist.iloc[-1]) / 100
            if 0 < rate < 0.2:
                return rate, f"US 10-year Treasury yield, Yahoo Finance ^TNX close {hist.index[-1].date()}"
    except Exception:
        pass
    fb = _snapshot()['treasury_10y_fallback']
    return fb['value'], f"Fallback: {fb['note']} (live yield unavailable)"


def equity_risk_premium():
    erp = _snapshot()['implied_erp']
    return erp['value'], f"Damodaran implied ERP, S&P 500, {erp['as_of']}"


def marginal_tax_rate():
    return MARGINAL_TAX, 'US marginal rate: 21% federal + ~4% state (same as the forecast model)'


def synthetic_rating(coverage):
    """(rating, spread) for an interest coverage ratio, or (None, None)."""
    if coverage is None or (isinstance(coverage, float) and math.isnan(coverage)):
        return None, None
    for row in _snapshot()['synthetic_rating_large_nonfinancial']:
        if row['coverage_above'] <= coverage <= row['coverage_up_to'] or (
                row['coverage_above'] < coverage < row['coverage_up_to'] + 1e-6):
            return row['rating'], row['spread']
    table = _snapshot()['synthetic_rating_large_nonfinancial']
    return (table[-1]['rating'], table[-1]['spread']) if coverage > 0 else (table[0]['rating'], table[0]['spread'])


def cost_of_debt(rf, coverage, coverage_note=''):
    """(pre-tax cost of debt or None, source)."""
    rating, spread = synthetic_rating(coverage)
    if rating is None:
        return None, 'Interest coverage unavailable'
    shown = 'no interest expense' if math.isinf(coverage) else f'{coverage:.1f}×'
    return rf + spread, (f"Risk-free + {spread:.2%} default spread for synthetic rating {rating} "
                         f"(interest coverage {shown}{coverage_note}; Damodaran, Jan 2026)")
