"""Equity valuation engine for banks: excess-return model and dividend discount model, side by side.

Why not FCFF: a bank's debt (deposits, borrowings) is raw material, not financing, so free cash flow
to the firm and WACC are not meaningful. Both models here discount cash or returns to COMMON equity
at the cost of equity (CAPM).

Excess-return (residual income) model
    Value = BV_0 + Σ (ROE_t − Ke) · BV_{t−1} / (1+Ke)^t + TV / (1+Ke)^H
    TV    = (ROE_{H+1} − Ke) · BV_H / (Ke − g)
    ROE_t = ROE* + (ROE_0 − ROE*) · ψ^t     (fades from today's level to the long-run level)
    BV_t  = BV_{t−1} · (1 + b_t),  b_t = g + (b_0 − g) · ψ^t   (book growth fades to terminal growth)

Dividend discount model (two-stage, total payout = dividends + buybacks)
    E_t   = E_{t−1} · (1 + γ_t),  γ_t fades linearly from sustainable growth ROE_0 · (1 − p_0) to g
    D_t   = p_t · E_t, p_t moves linearly from the company's own payout p_0 to the stable payout 1 − g / ROE*
    Value = Σ D_t / (1+Ke)^t + D_{H+1} / (Ke − g) / (1+Ke)^H

Under perfectly consistent assumptions both models give the same value (clean-surplus accounting).
Here they are built from different evidence — book value and ROE for one, the bank's actual payout
policy for the other — so the gap between them shows how far today's payout and growth are from what
the ROE path implies. Use the pair as a range, not as two independent opinions.

Every parameter is labelled with its source. The fade speed ψ is an economic assumption (no panel
calibration for banks yet); scenarios move the starting and long-run ROE, not arbitrary ±%.
"""
from __future__ import annotations

import math
from statistics import mean, median

HORIZON = 10
FADE = 0.75            # ψ: share of the ROE gap left after each year (≈5% after 10 years)
SCENARIOS = ('conservative', 'base', 'optimistic')


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _pct(values, q):
    """Linear-interpolation percentile (q in 0..1) of a non-empty list."""
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def derive_assumptions(history, ke, terminal_growth, scenario='base', overrides=None):
    """Drivers for one scenario, each with value, source and note."""
    if scenario not in SCENARIOS:
        raise ValueError(f'scenario must be one of {SCENARIOS}')
    overrides = overrides or {}
    roes = [r['ROE'] for r in history if _num(r.get('ROE'))]
    recent = roes[-3:]
    growths = [r['Book value growth'] for r in history if _num(r.get('Book value growth'))][-5:]
    payouts = [r['Payout ratio'] for r in history if _num(r.get('Payout ratio'))][-3:]
    nis = [r['Net income to common'] for r in history if _num(r.get('Net income to common'))][-3:]
    latest = history[-1]
    g = terminal_growth

    roe_base_now = mean(recent)
    roe_hist_median = median(roes)
    if scenario == 'conservative':
        roe_now, roe_now_note = min(roe_base_now, _pct(roes, 0.25)), '25th percentile of the company\'s own ROE history (or the 3-year mean if lower)'
        roe_long, roe_long_note = ke, 'Long-run ROE = cost of equity: excess returns are competed away'
    elif scenario == 'optimistic':
        roe_now, roe_now_note = max(roe_base_now, roes[-1]), 'Latest-year ROE (or the 3-year mean if higher)'
        roe_long, roe_long_note = _pct(roes, 0.75), '75th percentile of the company\'s own ROE history'
    else:
        roe_now, roe_now_note = roe_base_now, 'Mean ROE of the last 3 years (smooths the credit or underwriting cycle)'
        roe_long, roe_long_note = roe_hist_median, f'Median ROE of the last {len(roes)} years'
    src_now = src_long = 'data'
    if scenario == 'conservative':
        src_long = 'assumption'
    if 'roe_start' in overrides:
        roe_now, roe_now_note, src_now = overrides['roe_start'], 'Your input', 'user'
    if 'roe_long' in overrides:
        roe_long, roe_long_note, src_long = overrides['roe_long'], 'Your input', 'user'

    b0 = _clip(median(growths), 0.0, 0.08) if growths else g
    p0 = _clip(median(payouts), 0.0, 1.5) if payouts else max(0.0, 1 - g / roe_now) if roe_now > 0 else 0.0
    if 'payout_start' in overrides:
        p0 = overrides['payout_start']
    sustainable = _clip(roe_now * (1 - min(p0, 1.0)), 0.0, 0.12)
    stable_payout = 1 - g / roe_long if roe_long > 0 else None
    e0 = mean(nis) if nis else latest['Net income to common']
    # Earnings base moves with the scenario's starting ROE, so the DDM and the excess-return model start alike.
    if _num(e0) and roe_base_now > 0:
        e0 *= roe_now / roe_base_now

    drivers = {
        'cost_of_equity': {'value': ke, 'source': 'assumption', 'note': 'CAPM: risk-free rate + beta × equity risk premium'},
        'terminal_growth': {'value': g, 'source': 'assumption', 'note': 'Perpetual growth after year 10'},
        'roe_start': {'value': roe_now, 'source': src_now, 'note': roe_now_note},
        'roe_long': {'value': roe_long, 'source': src_long, 'note': roe_long_note},
        'fade_speed': {'value': FADE, 'source': 'assumption',
                       'note': 'Share of the ROE gap left each year (≈5% after 10 years); not panel-calibrated for banks or insurers'},
        'book_growth_start': {'value': b0, 'source': 'data',
                              'note': f'Median common-equity growth, last {len(growths)} years (clipped 0–8%)'},
        'payout_start': {'value': p0, 'source': 'user' if 'payout_start' in overrides else 'data',
                         'note': f'Median (dividends + buybacks) / net income to common, last {len(payouts)} years'},
        'sustainable_growth': {'value': sustainable, 'source': 'data',
                               'note': 'ROE today × (1 − payout today), clipped 0–12%'},
        'stable_payout': {'value': stable_payout, 'source': 'assumption', 'note': '1 − g / long-run ROE'},
        'normalized_earnings': {'value': e0, 'source': 'data',
                                'note': f'Mean {latest.get("Earnings basis", "net income to common")}, last {len(nis)} '
                                        'years, scaled by starting ROE / 3-year mean ROE'},
        'book_value': {'value': latest['Common equity'], 'source': 'data',
                       'note': f'{latest.get("Book basis", "Common equity")} at {latest["Fiscal year end"]}'
                               + ('' if 'Book basis' in latest else ' (total equity − preferred)')},
    }
    blockers = []
    if ke <= g:
        blockers.append('Cost of equity must be above terminal growth.')
    if roe_long <= g:
        blockers.append('Long-run ROE must be above terminal growth (otherwise growth destroys value without limit).')
    if not _num(e0) or e0 <= 0:
        blockers.append('Normalized earnings are not positive.')
    return {'drivers': drivers, 'blockers': blockers, 'year0': int(str(latest['Fiscal year end'])[:4])}


def excess_return(a, ke, g):
    d = a['drivers']
    roe0, roeL, b0 = d['roe_start']['value'], d['roe_long']['value'], d['book_growth_start']['value']
    bv = bv0 = d['book_value']['value']
    rows, pv_sum = [], 0.0
    for t in range(1, HORIZON + 1):
        roe = roeL + (roe0 - roeL) * FADE ** t
        b = g + (b0 - g) * FADE ** t
        ni = roe * bv
        bv_end = bv * (1 + b)
        ri = (roe - ke) * bv
        pv = ri / (1 + ke) ** t
        pv_sum += pv
        rows.append({'year': a['year0'] + t, 'roe': roe, 'book_begin': bv, 'net_income': ni,
                     'payout': ni - (bv_end - bv), 'book_growth': b, 'excess_return': ri, 'pv': pv})
        bv = bv_end
    roe_t = roeL + (roe0 - roeL) * FADE ** (HORIZON + 1)
    tv = (roe_t - ke) * bv / (ke - g)
    pv_tv = tv / (1 + ke) ** HORIZON
    return {'rows': rows, 'book_value': bv0, 'pv_excess': pv_sum, 'terminal_roe': roe_t, 'terminal_book': bv,
            'terminal_value': tv, 'pv_terminal': pv_tv, 'equity_value': bv0 + pv_sum + pv_tv}


def dividend_discount(a, ke, g):
    d = a['drivers']
    e, p0 = d['normalized_earnings']['value'], d['payout_start']['value']
    pT, g0 = d['stable_payout']['value'], d['sustainable_growth']['value']
    rows, pv_sum = [], 0.0
    for t in range(1, HORIZON + 1):
        w = t / HORIZON
        growth = g0 + (g - g0) * w
        payout = p0 + (pT - p0) * w
        e *= 1 + growth
        div = payout * e
        pv = div / (1 + ke) ** t
        pv_sum += pv
        rows.append({'year': a['year0'] + t, 'growth': growth, 'earnings': e, 'payout_ratio': payout,
                     'payout': div, 'pv': pv})
    d_next = pT * e * (1 + g)
    tv = d_next / (ke - g)
    pv_tv = tv / (1 + ke) ** HORIZON
    return {'rows': rows, 'pv_payouts': pv_sum, 'terminal_value': tv, 'pv_terminal': pv_tv,
            'equity_value': pv_sum + pv_tv}


def run(history, ke, terminal_growth, shares, scenario='base', overrides=None, portfolio=0.0):
    """Both models for one scenario. Values are total common equity (USD) and per share.

    `portfolio` (insurers): an equity portfolio held at market value net of deferred tax, kept OUT of the history's
    book value and earnings; it earns its required return, so it adds its value to both models unchanged."""
    a = derive_assumptions(history, ke, terminal_growth, scenario, overrides)
    out = {'scenario': scenario, 'assumptions': a, 'status': 'BLOCKED' if a['blockers'] else 'OK'}
    if a['blockers'] or not _num(shares) or shares <= 0:
        if not _num(shares) or shares <= 0:
            a['blockers'].append('Share count unavailable.')
        out['status'] = 'BLOCKED'
        return out
    ri = excess_return(a, ke, terminal_growth)
    ddm = dividend_discount(a, ke, terminal_growth)
    for m in (ri, ddm):
        m['portfolio'] = portfolio
        m['equity_value'] += portfolio
        m['per_share'] = m['equity_value'] / shares
    bv = a['drivers']['book_value']['value'] + portfolio
    out.update({'excess_return': ri, 'ddm': ddm, 'shares': shares,
                'book_value_per_share': bv / shares,
                'justified_pb': ri['equity_value'] / bv if bv > 0 else None,
                'midpoint': (ri['per_share'] + ddm['per_share']) / 2,
                'model_gap': ddm['per_share'] / ri['per_share'] - 1 if ri['per_share'] > 0 else None})
    return out


def run_all(history, ke, terminal_growth, shares, overrides=None, portfolio=0.0):
    return {s: run(history, ke, terminal_growth, shares, s, overrides, portfolio) for s in SCENARIOS}
