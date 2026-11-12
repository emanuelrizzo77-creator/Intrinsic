"""Intrinsic 27 — integrated, economically consistent FCFF driver model.

One model, not per-metric selection. Each driver = (start from latest data,
long-run anchor, convergence speed), every value labelled with its SOURCE:

  data        computed from the company's SEC history
  calibrated  estimated on a cross-company panel (calibration_27.json)
  assumption  economic default, editable, NOT estimated from data
  user        explicit user override

Mechanics (horizon H, default 10 years, then a value-driver terminal value):
  growth_t   = g_T + (g0 - g_T) * phi^t                 -> converges to terminal g
  margin_t   = m* + (m0 - m*) * psi^t
  tax_t      = linear from effective to marginal rate by year H
  NetPPE_t   = k_t * Revenue_t, k_t = k* + (k0 - k*) * psi_k^t   (capital intensity)
  Dep_t      = delta * NetPPE_{t-1}                     (PP&E roll-forward)
  CapEx_t    = NetPPE_t - NetPPE_{t-1} + Dep_t          (=> CapEx and D&A consistent)
  NWC_t      = n_t * Revenue_t  (negative allowed)
  FCFF_t     = NOPAT_t + Dep_t + Amort_t - CapEx_t - dNWC_t
  Terminal   : FCFF_{H+1} = NOPAT_{H+1} * (1 - g / RONIC)
"""
from __future__ import annotations

import json
import os
from statistics import median

from sec_annual_27 import consecutive, is_number

CALIBRATION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calibration_27.json')

# Provisional defaults used ONLY when no calibration file exists. They are
# explicit economic assumptions, not estimates, and are reported as such.
PROVISIONAL = {
    'growth_fade': 0.60,       # share of excess growth persisting each year
    'margin_fade': 0.70,       # share of margin gap persisting each year
    'intensity_fade': 0.70,    # share of capital-intensity gap persisting each year
    'scenario_growth_shift': 0.05,
    'scenario_margin_shift': 0.02,
}
MARGINAL_TAX = 0.25            # 21% federal + ~4% state; editable assumption
AMORT_RUNOFF_YEARS = 5         # organic forecast: existing acquired intangibles run off
SIZE_BUCKETS = ((1e9, '<1B'), (1e10, '1-10B'), (1e11, '10-100B'), (float('inf'), '>100B'))


def size_bucket(revenue):
    for limit, name in SIZE_BUCKETS:
        if revenue < limit:
            return name
    return '>100B'


def load_calibration(path=CALIBRATION_FILE):
    if path and os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return None


def _drv(value, source, note=''):
    return {'value': value, 'source': source, 'note': note}


def _med(values):
    vals = [v for v in values if is_number(v)]
    return median(vals) if vals else None


# ------------------------------------------------------------------
# 1. History
# ------------------------------------------------------------------

def merge_history(rows_23c, capital_rows):
    """Join 23C income/cash-flow rows with operating-capital rows by fiscal end."""
    cap = {r['Fiscal year end']: r for r in capital_rows}
    out = []
    for r in sorted(rows_23c, key=lambda x: x['Fiscal year end']):
        merged = dict(r)
        c = cap.get(r['Fiscal year end'], {})
        for key in ('Net PP&E', 'Operating NWC', 'Operating invested capital', 'Depreciation',
                    'Amortization', 'Goodwill', 'Intangibles', 'Short-term investments',
                    'Current debt', 'Cash'):
            merged[key] = c.get(key)
        merged['capital_flags'] = list(c.get('flags', []))
        merged['capital_tags'] = dict(c.get('tags', {}))
        out.append(merged)
    return out


def _depreciation_series(h):
    """Return (pure depreciation per row, amortization per row, method notes)."""
    deps, amorts, methods = [], [], set()
    for r in h:
        da, dep, am = r.get('D&A verified'), r.get('Depreciation'), r.get('Amortization')
        if is_number(dep):
            deps.append(dep)
            amorts.append(da - dep if is_number(da) and da >= dep else (am if is_number(am) else 0.0))
            methods.add('depreciation tag')
        elif is_number(da) and is_number(am) and da >= am:
            deps.append(da - am)
            amorts.append(am)
            methods.add('D&A minus amortization')
        elif is_number(da):
            deps.append(da)
            amorts.append(0.0)
            methods.add('D&A combined (amortization inside delta)')
        else:
            deps.append(None)
            amorts.append(None)
    return deps, amorts, methods


def historical_diagnostics(history):
    """Ratios and reconciliation checks that inform (not dictate) assumptions."""
    h = sorted(history, key=lambda r: r['Fiscal year end'])
    deps, amorts, methods = _depreciation_series(h)
    dep_rates, capex_recon, roic = [], [], []
    for i in range(1, len(h)):
        p, c = h[i - 1], h[i]
        if not consecutive(p['Fiscal year end'], c['Fiscal year end']):
            continue
        ppe0, ppe1 = p.get('Net PP&E'), c.get('Net PP&E')
        if is_number(ppe0) and ppe0 > 0 and is_number(deps[i]):
            dep_rates.append(deps[i] / ppe0)
        if (is_number(ppe0) and is_number(ppe1) and is_number(deps[i])
                and is_number(c.get('CapEx')) and c['CapEx'] > 0):
            capex_recon.append((ppe1 - ppe0 + deps[i]) / c['CapEx'])
        ic0, tax = p.get('Operating invested capital'), c.get('Effective tax rate')
        if is_number(ic0) and ic0 > 0 and is_number(c.get('EBIT')) and is_number(tax):
            roic.append(c['EBIT'] * (1 - tax) / ic0)

    def rev(r):
        return r['Revenue'] if is_number(r.get('Revenue')) and r['Revenue'] > 0 else None

    def ratio(key):
        return [r[key] / rev(r) for r in h if rev(r) and is_number(r.get(key))]

    return {
        'dep_rates': dep_rates, 'dep_method': sorted(methods),
        'capex_reconciliation': capex_recon,
        'ppe_intensity': ratio('Net PP&E'), 'nwc_ratio': ratio('Operating NWC'),
        'margins': [r['EBIT margin'] for r in h if is_number(r.get('EBIT margin'))],
        'tax_rates': [r['Effective tax rate'] for r in h if is_number(r.get('Effective tax rate'))],
        'roic_ex_goodwill': roic,
        'latest_amortization': amorts[-1] if amorts else None,
        'latest_depreciation': deps[-1] if deps else None,
    }


# ------------------------------------------------------------------
# 2. Assumptions
# ------------------------------------------------------------------

def derive_assumptions(history, *, wacc, terminal_growth, scenario='base',
                       calibration=None, overrides=None):
    """Return {'drivers', 'status', 'blockers', 'degradations', 'diagnostics'}."""
    if scenario not in ('base', 'conservative', 'optimistic'):
        raise ValueError('scenario must be base, conservative or optimistic')
    if not is_number(wacc) or not is_number(terminal_growth) or wacc <= terminal_growth:
        raise ValueError('WACC must be numeric and exceed terminal growth')
    h = sorted(history, key=lambda r: r['Fiscal year end'])
    if not h:
        raise ValueError('Empty history')
    last = h[-1]
    diag = historical_diagnostics(h)
    blockers, degraded, d = [], [], {}

    rev0 = last.get('Revenue')
    if not is_number(rev0) or rev0 <= 0:
        blockers.append('Latest revenue missing or non-positive')
        rev0 = None
    d['revenue0'] = _drv(rev0, 'data', f"FY ending {last['Fiscal year end']}")
    d['year0'] = _drv(int(str(last['Fiscal year end'])[:4]), 'data')

    g0 = last.get('Revenue growth')
    if not is_number(g0):
        blockers.append('Latest revenue growth unavailable (non-consecutive or missing prior year)')
    d['growth_start'] = _drv(g0, 'data', 'latest fiscal-year growth (recent results, not historical median)')
    d['terminal_growth'] = _drv(terminal_growth, 'assumption',
                                'long-run nominal growth; should not exceed long-run risk-free rate / nominal GDP')

    cal = calibration or {}
    bucket = size_bucket(rev0) if rev0 else 'all'

    def calibrated(key):
        table = cal.get(key, {})
        entry = table.get(bucket) or table.get('all')
        return entry.get('phi') if isinstance(entry, dict) else None

    for name, key in (('growth_fade', 'growth_fade'), ('margin_fade', 'margin_fade'),
                      ('intensity_fade', 'intensity_fade')):
        phi = calibrated(key)
        if phi is not None:
            d[name] = _drv(phi, 'calibrated', f'panel estimate, size bucket {bucket}')
        else:
            d[name] = _drv(PROVISIONAL[name], 'assumption', 'PROVISIONAL: run calibrate_fade_27.py to estimate')
    if not cal:
        degraded.append('No calibration_27.json: fade speeds are provisional assumptions')

    m0 = last.get('EBIT margin')
    if not is_number(m0):
        blockers.append('Latest EBIT margin unavailable')
    elif m0 <= 0:
        degraded.append('Negative latest EBIT margin: path to profitability relies on margin target')
    m_star = _med(diag['margins'])
    d['margin_start'] = _drv(m0, 'data', 'latest fiscal year')
    d['margin_target'] = _drv(m_star, 'data',
                              f"company median of {len(diag['margins'])} years; no industry shrinkage yet")

    tax0 = last.get('Effective tax rate')
    if is_number(tax0):
        d['tax_start'] = _drv(tax0, 'data', 'latest effective rate')
    elif _med(diag['tax_rates']) is not None:
        d['tax_start'] = _drv(_med(diag['tax_rates']), 'data', 'median effective rate (latest unreliable)')
    else:
        degraded.append('No reliable effective tax rate: marginal rate used from year 1')
        d['tax_start'] = _drv(MARGINAL_TAX, 'assumption', 'no reliable effective tax history')
    d['tax_terminal'] = _drv(MARGINAL_TAX, 'assumption', 'US marginal: 21% federal + ~4% state')

    ppe0 = last.get('Net PP&E')
    if not is_number(ppe0) or ppe0 < 0:
        blockers.append('Latest Net PP&E missing: capital roll-forward impossible')
        ppe0 = None
    d['net_ppe0'] = _drv(ppe0, 'data')
    d['intensity_start'] = _drv(ppe0 / rev0 if ppe0 is not None and rev0 else None, 'data',
                                'Net PP&E / revenue, latest')
    d['intensity_target'] = _drv(_med(diag['ppe_intensity']), 'data',
                                 'company median Net PP&E / revenue; override for investment cycles')

    delta = _med(diag['dep_rates'])
    if delta is None:
        blockers.append('No depreciation / prior Net PP&E observation: D&A cannot be modelled '
                        '(enter a dep_rate override)')
    d['dep_rate'] = _drv(delta, 'data', 'median depreciation / prior-year Net PP&E; method: '
                         + (', '.join(diag['dep_method']) or 'n/a'))
    if any('combined' in m for m in diag['dep_method']):
        degraded.append('Depreciation rate includes amortization (no separate tag): D&A may be overstated')
    am0 = diag['latest_amortization']
    d['amortization0'] = _drv(am0 if is_number(am0) else 0.0, 'data' if is_number(am0) else 'assumption',
                              f'acquired-intangible amortization; runs off over {AMORT_RUNOFF_YEARS} years '
                              '(organic forecast, no new M&A)')

    nwc0 = last.get('Operating NWC')
    if is_number(nwc0) and rev0:
        d['nwc0'] = _drv(nwc0, 'data')
        d['nwc_ratio_start'] = _drv(nwc0 / rev0, 'data', 'operating NWC / revenue, latest (negative allowed)')
        d['nwc_ratio_target'] = _drv(_med(diag['nwc_ratio']), 'data', 'company median operating NWC / revenue')
    else:
        degraded.append('Operating NWC unavailable: NWC held at ZERO (explicit, unvalidated)')
        for key in ('nwc0', 'nwc_ratio_start', 'nwc_ratio_target'):
            d[key] = _drv(0.0, 'assumption', 'NWC data missing')

    recon = _med(diag['capex_reconciliation'])
    if recon is not None and not 0.7 <= recon <= 1.3:
        degraded.append(f'PP&E roll-forward does not reconcile to reported CapEx (median implied/reported '
                        f'= {recon:.2f}): leases, acquisitions, impairments or FX. Projected CapEx includes these.')

    d['ronic'] = _drv('wacc' if scenario != 'optimistic' else 'last_roic', 'assumption',
                      'return on NEW capital in perpetuity: wacc = no excess returns; last_roic = moat persists')
    d['wacc'] = _drv(wacc, 'user')

    if scenario != 'base':
        sign = -1 if scenario == 'conservative' else 1
        q = cal.get('scenario_quantiles', {})
        gq, mq = q.get('growth_p20_p80_h1'), q.get('margin_p20_p80_h5')
        if is_number(g0):
            if gq:
                shift, src = (gq[0] if sign < 0 else gq[1]) / max(d['growth_fade']['value'], 0.05), 'calibrated'
            else:
                shift, src = sign * PROVISIONAL['scenario_growth_shift'], 'assumption'
            d['growth_start'] = _drv(g0 + shift, src, f'{scenario}: start growth shifted {shift:+.1%}')
        if is_number(m_star):
            mshift = (mq[0] if sign < 0 else mq[1]) if mq else sign * PROVISIONAL['scenario_margin_shift']
            d['margin_target'] = _drv(m_star + mshift, 'calibrated' if mq else 'assumption',
                                      f'{scenario}: margin target shifted {mshift:+.1%}')

    for key, val in (overrides or {}).items():
        if key not in d:
            raise ValueError(f'Unknown driver override: {key}')
        d[key] = _drv(val, 'user', 'user override')
        if key == 'dep_rate':
            blockers[:] = [b for b in blockers if 'depreciation' not in b.lower()]
        if key == 'net_ppe0':
            blockers[:] = [b for b in blockers if 'Net PP&E' not in b]
            if d['revenue0']['value']:
                d['intensity_start'] = _drv(val / d['revenue0']['value'], 'user', 'derived from override')
    if any(x['source'] == 'user' for k, x in d.items() if k != 'wacc'):
        degraded.append('User overrides in use (see driver table)')

    for key in ('margin_target', 'intensity_target'):
        if d[key]['value'] is None:
            blockers.append(f'{key} unavailable')
    status = 'BLOCKED' if blockers else ('DEGRADED' if degraded else 'DATA_COMPLETE')
    return {'drivers': d, 'status': status, 'blockers': blockers, 'degradations': degraded,
            'diagnostics': diag, 'scenario': scenario}


# ------------------------------------------------------------------
# 3. Projection
# ------------------------------------------------------------------

def project(assumptions, horizon=10):
    if assumptions['status'] == 'BLOCKED':
        raise ValueError('Forecast blocked: ' + '; '.join(assumptions['blockers']))
    if not isinstance(horizon, int) or isinstance(horizon, bool) or not 5 <= horizon <= 15:
        raise ValueError('horizon must be an integer between 5 and 15')
    v = {k: x['value'] for k, x in assumptions['drivers'].items()}
    gT, g0, phi = v['terminal_growth'], v['growth_start'], v['growth_fade']
    m0, mT, psi = v['margin_start'], v['margin_target'], v['margin_fade']
    k0, kT, psik = v['intensity_start'], v['intensity_target'], v['intensity_fade']
    n0, nT = v['nwc_ratio_start'], v['nwc_ratio_target']
    for name, x in (('growth_fade', phi), ('margin_fade', psi), ('intensity_fade', psik)):
        if not is_number(x) or not 0 <= x < 1:
            raise ValueError(f'{name} must be in [0, 1)')
    if not is_number(v['dep_rate']) or not 0 < v['dep_rate'] < 1:
        raise ValueError('dep_rate must be in (0, 1)')

    rows, flags = [], []
    rev_prev, ppe_prev, nwc_prev = v['revenue0'], v['net_ppe0'], v['nwc0']
    for t in range(1, horizon + 1):
        g = gT + (g0 - gT) * phi ** t
        rev = rev_prev * (1 + g)
        margin = mT + (m0 - mT) * psi ** t
        ebit = rev * margin
        tax = v['tax_start'] + (v['tax_terminal'] - v['tax_start']) * t / horizon
        nopat = ebit * (1 - tax) if ebit > 0 else ebit   # no tax credit assumed on losses
        k = kT + (k0 - kT) * psik ** t
        dep = v['dep_rate'] * ppe_prev
        ppe = k * rev
        capex = ppe - ppe_prev + dep
        if capex < 0:
            flags.append(f'Year {t}: implied CapEx negative; floored at zero '
                         '(capital intensity falling faster than depreciation)')
            capex, ppe = 0.0, ppe_prev - dep
        amort = v['amortization0'] * max(0.0, 1 - t / AMORT_RUNOFF_YEARS)
        nwc_ratio = nT + (n0 - nT) * psi ** t
        nwc = nwc_ratio * rev
        dnwc = nwc - nwc_prev
        fcff = nopat + dep + amort - capex - dnwc
        ic_prev = ppe_prev + nwc_prev
        net_reinv = capex - dep + dnwc
        rows.append({
            'year': v['year0'] + t, 't': t, 'revenue': rev, 'growth': g, 'ebit': ebit,
            'ebit_margin': margin, 'tax_rate': tax, 'nopat': nopat, 'depreciation': dep,
            'amortization': amort, 'da': dep + amort, 'capex': capex, 'net_ppe': ppe,
            'ppe_intensity': ppe / rev, 'nwc': nwc, 'nwc_ratio': nwc_ratio, 'delta_nwc': dnwc,
            'net_reinvestment': net_reinv,
            'reinvestment_rate': net_reinv / nopat if nopat > 0 else None,
            'invested_capital': ppe + nwc,
            'roic': nopat / ic_prev if ic_prev > 0 else None, 'fcff': fcff,
            # compatibility with the existing 5-year engine / dashboard tables
            'da_ratio': (dep + amort) / rev, 'capex_ratio': capex / rev,
        })
        rev_prev, ppe_prev, nwc_prev = rev, ppe, nwc
    return {'rows': rows, 'flags': flags, 'horizon': horizon}


# ------------------------------------------------------------------
# 4. Terminal value, valuation and consistency checks
# ------------------------------------------------------------------

def terminal_value(projection, assumptions):
    v = {k: x['value'] for k, x in assumptions['drivers'].items()}
    last = projection['rows'][-1]
    g, wacc, ronic = v['terminal_growth'], v['wacc'], v['ronic']
    if ronic == 'wacc':
        ronic = wacc
    elif ronic == 'last_roic':
        ronic = last['roic'] if last['roic'] and last['roic'] > wacc else wacc
    if not is_number(ronic) or ronic <= max(g, 0):
        raise ValueError('RONIC must exceed terminal growth')
    rev = last['revenue'] * (1 + g)
    nopat = rev * last['ebit_margin'] * (1 - v['tax_terminal'])
    if nopat <= 0:
        raise ValueError('Terminal NOPAT is not positive: no going-concern terminal value')
    rr = g / ronic if g > 0 else 0.0
    fcff = nopat * (1 - rr)
    return {'revenue': rev, 'nopat': nopat, 'ronic': ronic, 'reinvestment_rate': rr,
            'fcff': fcff, 'terminal_value': fcff / (wacc - g)}


def value(projection, assumptions, *, net_debt, shares, mid_year=False):
    if not is_number(shares) or shares <= 0:
        raise ValueError('shares must be positive')
    if not is_number(net_debt):
        raise ValueError('net_debt must be numeric')
    wacc = assumptions['drivers']['wacc']['value']
    offset = 0.5 if mid_year else 0.0
    pv = [r['fcff'] / (1 + wacc) ** (r['t'] - offset) for r in projection['rows']]
    term = terminal_value(projection, assumptions)
    pv_tv = term['terminal_value'] / (1 + wacc) ** (projection['horizon'] - offset)
    ev = sum(pv) + pv_tv
    equity = ev - net_debt
    return {'pv_fcff': sum(pv), 'pv_fcff_by_year': pv, 'terminal': term,
            'pv_terminal': pv_tv, 'enterprise_value': ev, 'equity_value': equity,
            'intrinsic_price': equity / shares,
            'terminal_share_of_ev': pv_tv / ev if ev > 0 else None}


def consistency_checks(projection, assumptions, valuation=None):
    v = {k: x['value'] for k, x in assumptions['drivers'].items()}
    rows = projection['rows']
    last, issues = rows[-1], list(projection['flags'])
    for r in rows:   # identity: PP&E roll-forward must hold exactly
        prev = rows[r['t'] - 2]['net_ppe'] if r['t'] > 1 else v['net_ppe0']
        if abs(prev + r['capex'] - r['depreciation'] - r['net_ppe']) > 1e-6 * max(1.0, abs(prev)):
            raise AssertionError('PP&E roll-forward identity violated')
    if abs(last['growth'] - v['terminal_growth']) > 0.005:
        issues.append(f"Not at steady state: year-{last['t']} growth {last['growth']:.1%} vs terminal "
                      f"{v['terminal_growth']:.1%}. Extend horizon or revisit growth fade.")
    if abs(last['ebit_margin'] - v['margin_target']) > 0.01:
        issues.append('Margin still converging in final year; terminal margin is not the long-run target.')
    if valuation:
        rr_term, rr_last = valuation['terminal']['reinvestment_rate'], last['reinvestment_rate']
        if rr_last is not None and abs(rr_last - rr_term) > 0.15:
            issues.append(f'Final-year reinvestment rate {rr_last:.0%} vs terminal {rr_term:.0%}: explicit '
                          'capital intensity and terminal RONIC imply different economics.')
        share = valuation['terminal_share_of_ev']
        if share is not None and share > 0.85:
            issues.append(f'Terminal value is {share:.0%} of EV: valuation dominated by perpetuity assumptions.')
    for r in rows:
        if r['roic'] is not None and not 0 <= r['roic'] <= 1.0:
            issues.append(f"Year {r['t']}: ROIC on operating capital {r['roic']:.0%} (ex-goodwill); check plausibility.")
            break
    return issues


def run(history, *, wacc, terminal_growth, net_debt, shares, scenario='base',
        horizon=10, overrides=None, calibration='auto', mid_year=False):
    """Full pipeline. Returns a dict even when BLOCKED (then without valuation)."""
    cal = load_calibration() if calibration == 'auto' else calibration
    a = derive_assumptions(history, wacc=wacc, terminal_growth=terminal_growth,
                           scenario=scenario, calibration=cal, overrides=overrides)
    out = {'assumptions': a, 'status': a['status'], 'validated': False}
    if a['status'] == 'BLOCKED':
        return out
    p = project(a, horizon)
    out['projection'] = p
    try:
        val = value(p, a, net_debt=net_debt, shares=shares, mid_year=mid_year)
    except ValueError as exc:
        out.update(status='BLOCKED', valuation_error=str(exc), checks=consistency_checks(p, a))
        return out
    out.update(valuation=val, checks=consistency_checks(p, a, val))
    return out
