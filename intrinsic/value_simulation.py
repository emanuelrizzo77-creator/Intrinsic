"""Monte Carlo distribution of intrinsic value per share for the Final verdict.

Replaces the assumption that the conservative / optimistic scenarios ARE the 20th / 80th percentiles of value. Each
draw re-prices the BASE scenario with the same engine (forecast.project -> forecast.value) after changing:

  revenue and margin paths  one jointly observed error vector (revenue h1..h5 and margin h1..h5 together) from
                            data/joint_errors.json, drawn from companies of the same revenue size (or, for a company growing
                            more than 25%, from high-growth companies of any size). Below $10B the
                            errors are scaled by this company's own growth / margin volatility (as the scenario
                            bands are); at $10B and above they are used in raw points, the form that covered better
                            out of sample for large companies (validation/joint_errors.py). After year 5 the margin shift held
                            is the median of the year 3-5 errors, so a one-year write-off in the panel (impairment,
                            spin-off) does not become a permanent loss of margin
  discount rate             beta ~ N(beta, BETA_SD) and equity risk premium ~ N(ERP, ERP_SD) through CAPM, at the
                            WACC's capital weights; with a manual WACC, WACC ~ N(WACC, WACC_SD)
  terminal growth           triangular(g - G_HALF_RANGE, g, g + G_HALF_RANGE), kept below the risk-free rate and
                            at least WACC_GAP under the drawn WACC
  failure (loss-makers)     with the model's failure probability the draw is the distress value (net cash)

Draws where the business never earns a positive terminal profit are valued at the distress value too.

What is calibrated and what is not: the revenue / margin errors are measured on 610 companies (3,925 five-year
windows) and their central 60% covers 49-64% of held-out companies' errors depending on size and horizon; the discount-rate and terminal-growth spreads are economic assumptions
(documented, editable here), not estimates. The resulting probabilities are still conditional on the model.
"""
from __future__ import annotations

import json
import math
import os
import random
from functools import lru_cache

from intrinsic import forecast as dm
from intrinsic.paths import DATA_DIR

JOINT_FILE = os.path.join(DATA_DIR, 'joint_errors.json')
N_DRAWS = 1000
SEED = 20261120

# Economic assumptions for the discount-rate and terminal-growth spreads (not estimated).
BETA_SD = 0.20          # uncertainty of one company's beta around its industry estimate
ERP_SD = 0.005          # spread of reasonable equity risk premiums (implied vs historical estimates)
WACC_SD = 0.01          # used only when the WACC is entered manually (no CAPM inputs)
G_HALF_RANGE = 0.01     # terminal growth +/- 1 point, triangular
WACC_GAP = 0.01         # the drawn WACC stays at least 1 point above the drawn terminal growth
MIN_ERP, MIN_BETA = 0.02, 0.2


@lru_cache(maxsize=1)
def joint_errors(path=JOINT_FILE):
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def _tri(rng, lo, mode, hi):
    return rng.triangular(lo, hi, mode)


def _with(assumptions, **values):
    drivers = dict(assumptions['drivers'])
    for k, v in values.items():
        drivers[k] = {'value': v, 'source': 'simulation', 'note': 'Monte Carlo draw'}
    return {**assumptions, 'drivers': drivers}


def simulate(base_result, history, *, net_debt, shares, capm=None, n=N_DRAWS, seed=SEED, calibration='auto',
             errors=None):
    """Simulated values per share for the base scenario of a forecast.run result.

    Returns {'values', 'n', 'distress_share', 'inputs'} or None when the base scenario has no valuation or the
    calibration data needed to scale the errors is missing."""
    if 'projection' not in base_result or 'valuation' not in base_result:
        return None
    cal = dm.load_calibration() if calibration == 'auto' else calibration
    vol = dm.company_volatility(history, cal)
    errs = errors if errors is not None else joint_errors()
    if not vol or not errs:
        return None
    sg, sm, high = vol
    rev0 = base_result['assumptions']['drivers']['revenue0']['value']
    groups = errs['groups']
    if high and 'high_growth' in groups:
        group = 'high_growth'                    # hypergrowth: its own pool at any size
    else:
        group = next((g for g, x in groups.items() if x['min_revenue'] is not None
                      and x['min_revenue'] <= rev0 < (x['max_revenue'] if x['max_revenue'] is not None else float('inf'))),
                     None)
    if group is None or len(errs['groups'][group]['vectors']) < 200:
        return None
    pool, kind = errs['groups'][group]['vectors'], errs['groups'][group]['kind']
    scale_g, scale_m = (sg, sm) if kind == 'scaled' else (1.0, 1.0)
    a0 = base_result['assumptions']
    d = a0['drivers']
    wacc0, g0 = d['wacc']['value'], d['terminal_growth']['value']
    horizon = base_result['projection']['horizon']
    p_fail = d.get('failure_prob', {}).get('value') or 0.0
    distress = max(0.0, -net_debt) / shares
    rf = capm.get('risk_free_rate') if capm else None
    rng = random.Random(seed)
    values, distressed = [], 0
    for _ in range(n):
        z = pool[rng.randrange(len(pool))]
        if capm:
            beta = max(MIN_BETA, rng.gauss(capm['beta'], BETA_SD))
            erp = max(MIN_ERP, rng.gauss(capm['equity_risk_premium'], ERP_SD))
            ke = capm['risk_free_rate'] + beta * erp
            wacc = capm['equity_weight'] * ke + capm['debt_weight'] * capm['after_tax_cost_of_debt']
        else:
            wacc = rng.gauss(wacc0, WACC_SD)
        g = _tri(rng, g0 - G_HALF_RANGE, g0, g0 + G_HALF_RANGE)
        g = min(g, wacc - WACC_GAP, rf if rf is not None else g)
        if p_fail and rng.random() < p_fail:
            values.append(distress)
            distressed += 1
            continue
        m = [x * scale_m for x in z[5:10]]
        m[4] = sorted(m[2:5])[1]        # the shift held after year 5: median of years 3-5, so a one-year write-off
        a = _with(a0, revenue_band=[x * scale_g for x in z[:5]], margin_band=m, wacc=wacc,           # is not permanent
                  terminal_growth=g, failure_prob=0.0)
        try:
            val = dm.value(dm.project(a, horizon), a, net_debt=net_debt, shares=shares)
            values.append(val['intrinsic_price'])
        except ValueError:                       # no positive terminal profit: worth its net cash only
            values.append(distress)
            distressed += 1
    return {'values': values, 'n': n, 'distress_share': distressed / n,
            'inputs': {'growth_sigma': sg, 'margin_sigma': sm, 'size_group': group, 'error_kind': kind,
                       'n_vectors': len(pool), 'beta_sd': BETA_SD if capm else None,
                       'erp_sd': ERP_SD if capm else None, 'wacc_sd': None if capm else WACC_SD,
                       'g_half_range': G_HALF_RANGE, 'failure_prob': p_fail, 'seed': seed}}


def percentile_rank(values, x):
    """Share of simulated values at or below x."""
    if not values or x is None or not math.isfinite(x):
        return None
    return sum(v <= x for v in values) / len(values)
