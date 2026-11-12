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
import math
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
POOLING_K = 200               # pseudo-observations of the all-company estimate (hyperparameter)
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
                    'Current debt', 'Cash', 'R&D', 'Research asset', 'R&D amortization', 'R&D history',
                    'Finance-lease ROU additions', 'Finance lease liabilities'):
            merged[key] = c.get(key)
        # Operating margin BEFORE amortisation of acquired intangibles (EBITA): the
        # forecast fades this margin and charges the (running-off) amortisation
        # separately, so EBIT rises as acquired intangibles are amortised away.
        am, ebit, rev = merged.get('Amortization'), merged.get('EBIT'), merged.get('Revenue')
        if is_number(ebit) and is_number(rev) and rev > 0:
            merged['EBITA margin'] = (ebit + (am if is_number(am) else 0.0)) / rev
        else:
            merged['EBITA margin'] = None
        merged['capital_flags'] = list(c.get('flags', []))
        merged['capital_tags'] = dict(c.get('tags', {}))
        out.append(merged)
    return out


def _depreciation_series(h):
    """Return (recurring depreciation per row, ACQUIRED-intangible amortization per row, methods).

    Only the AmortizationOfIntangibleAssets tag is treated as run-off amortization.
    Any other residual of total D&A (finance-lease, content, software amortization)
    is recurring and stays inside the depreciation base.
    """
    deps, amorts, methods = [], [], set()
    for r in h:
        da, dep, am = r.get('D&A verified'), r.get('Depreciation'), r.get('Amortization')
        if is_number(da) and is_number(am) and da >= am:
            deps.append(da - am)
            amorts.append(am)
            methods.add('total D&A minus acquired-intangible amortization')
        elif is_number(da):
            deps.append(da)
            amorts.append(0.0)
            methods.add('total D&A (no acquired-amortization tag; nothing runs off)')
        elif is_number(dep):
            deps.append(dep)
            amorts.append(am if is_number(am) else 0.0)
            methods.add('depreciation tag + acquired-intangible amortization tag')
        else:
            deps.append(None)
            amorts.append(None)
    return deps, amorts, methods


def historical_diagnostics(history):
    """Ratios and reconciliation checks that inform (not dictate) assumptions."""
    h = sorted(history, key=lambda r: r['Fiscal year end'])
    deps, amorts, methods = _depreciation_series(h)
    dep_rates, capex_recon, roic, leakage = [], [], [], []
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
            if ppe0 > 0:
                # Cash + lease-financed investment not explained by depreciation and the
                # change in Net PP&E: disposals, impairments, FX translation, refranchising (>0)
                # or assets arriving without cash/lease (acquisitions, accrued capex) (<0).
                fin = c.get('Finance-lease ROU additions')
                leakage.append((c['CapEx'] + (fin if is_number(fin) else 0.0) - deps[i] - (ppe1 - ppe0)) / ppe0)
        ic0, tax = p.get('Operating invested capital'), c.get('Effective tax rate')
        if is_number(ic0) and ic0 > 0 and is_number(c.get('EBIT')) and is_number(tax):
            roic.append(c['EBIT'] * (1 - tax) / ic0)

    def rev(r):
        return r['Revenue'] if is_number(r.get('Revenue')) and r['Revenue'] > 0 else None

    def ratio(key):
        return [r[key] / rev(r) for r in h if rev(r) and is_number(r.get(key))]

    return {
        'dep_rates': dep_rates, 'dep_method': sorted(methods),
        'capex_reconciliation': capex_recon, 'ppe_leakage': leakage,
        'ppe_intensity': ratio('Net PP&E'), 'nwc_ratio': ratio('Operating NWC'),
        'margins': [r.get('EBITA margin', r.get('EBIT margin')) for r in h
                    if is_number(r.get('EBITA margin', r.get('EBIT margin')))],
        'tax_rates': [r['Effective tax rate'] for r in h if is_number(r.get('Effective tax rate'))],
        'roic_ex_goodwill': roic,
        'latest_amortization': amorts[-1] if amorts else None,
        'latest_depreciation': deps[-1] if deps else None,
    }


# ------------------------------------------------------------------
# 2. Assumptions
# ------------------------------------------------------------------

def derive_assumptions(history, *, wacc, terminal_growth, scenario='base',
                       calibration=None, overrides=None, rd_life=None, rd_life_note=''):
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
    blockers, degraded, notes, d = [], [], [], {}

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

    def _n(entry):
        n = entry.get('n_by_horizon', {})
        return n.get(1, n.get('1', 0))

    def calibrated(key):
        # Partial pooling (empirical-Bayes style): a size bucket's estimate is
        # shrunk toward the all-company estimate with weight n / (n + POOLING_K).
        table = cal.get(key, {})
        overall, own = table.get('all'), table.get(bucket)
        if isinstance(own, dict) and isinstance(overall, dict):
            w = _n(own) / (_n(own) + POOLING_K)
            phi = w * own['phi'] + (1 - w) * overall['phi']
            return phi, f"bucket {bucket} (n={_n(own)}, weight {w:.0%}) pooled with all ({overall['phi']:.2f})"
        if isinstance(overall, dict):
            return overall['phi'], f"all (no estimate for bucket {bucket})"
        return None, None

    high = cal.get('growth_fade_high')
    for name, key in (('growth_fade', 'growth_fade'), ('margin_fade', 'margin_fade'),
                      ('intensity_fade', 'intensity_fade')):
        phi, used = calibrated(key)
        if name == 'growth_fade' and isinstance(high, dict) and is_number(g0) and g0 > high.get('threshold', 0.25):
            phi, used = high['phi'], (f"high-growth panel (start growth > {high.get('threshold', 0.25):.0%}, "
                                       f"n={_n(high)})")
        if phi is not None:
            d[name] = _drv(round(phi, 3), 'calibrated', f'panel estimate: {used}')
        else:
            d[name] = _drv(PROVISIONAL[name], 'assumption', 'PROVISIONAL: run calibrate_fade_27.py to estimate')
    if not cal:
        degraded.append('No calibration_27.json: fade speeds are provisional assumptions')

    m0 = last.get('EBITA margin', last.get('EBIT margin'))
    if last.get('EBIT source') == 'derived':
        degraded.append('No OperatingIncomeLoss tag: EBIT derived as pretax income + interest expense '
                        '− interest income (includes other non-operating items)')
    if not is_number(m0):
        blockers.append('Latest EBIT margin unavailable')
    elif m0 <= 0:
        degraded.append('Negative latest EBIT margin: path to profitability relies on margin target')
    # Anchor = median of years BEFORE the latest one, the same definition used to
    # calibrate the fade weight (calibrate_fade_27.py); falls back to all years.
    prior = lambda xs: xs[:-1] if len(xs) >= 4 else xs
    m_star = _med(prior(diag['margins']))
    d['margin_start'] = _drv(m0, 'data', 'latest fiscal year, operating margin before acquired-intangible amortisation')
    d['margin_target'] = _drv(m_star, 'data',
                              f"company median of {len(prior(diag['margins']))} prior years; no industry shrinkage yet")

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
    d['intensity_target'] = _drv(_med(prior(diag['ppe_intensity'])), 'data',
                                 'company median Net PP&E / revenue (prior years); override for investment cycles')

    delta = _med(diag['dep_rates'])
    if delta is None:
        blockers.append('No depreciation / prior Net PP&E observation: D&A cannot be modelled '
                        '(enter a dep_rate override)')
    d['dep_rate'] = _drv(delta, 'data', 'median depreciation / prior-year Net PP&E; method: '
                         + (', '.join(diag['dep_method']) or 'n/a'))
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

    # R&D capitalisation: reclassifies R&D from expense to investment. It changes
    # NOPAT, invested capital, ROIC and the terminal reinvestment base, NOT the
    # explicit-year cash flows (the identity is asserted in consistency_checks).
    hist_rd = last.get('R&D history')
    if rd_life and is_number(last.get('Research asset')) and hist_rd and rev0:
        rd_ratios = [r['R&D'] / r['Revenue'] for r in h
                     if is_number(r.get('R&D')) and is_number(r.get('Revenue')) and r['Revenue'] > 0]
        d['rd_life'] = _drv(rd_life, 'assumption', f'R&D amortisable life (years), {rd_life_note}')
        d['rd_history'] = _drv(list(hist_rd), 'data', f'last {rd_life} years of R&D, oldest first')
        d['research_asset0'] = _drv(last['Research asset'], 'data', 'unamortised capitalised R&D, latest')
        d['rd_ratio_start'] = _drv(last['R&D'] / rev0, 'data', 'R&D / revenue, latest')
        d['rd_ratio_target'] = _drv(_med(prior(rd_ratios)), 'data', 'median R&D / revenue, prior years')
    elif rd_life and is_number(last.get('R&D')):
        degraded.append(f'R&D reported but fewer than {rd_life + 1} consecutive years: not capitalised')
    elif rd_life:
        notes.append('No R&D tag (or R&D reported under another caption): R&D not capitalised; '
                     'ROIC may be overstated if growth investment is expensed')

    leak = _med(diag['ppe_leakage'][-9:])
    if leak is None:
        d['ppe_leakage'] = _drv(0.0, 'assumption', 'no CapEx/PP&E history to reconcile')
    elif leak > 0:
        d['ppe_leakage'] = _drv(leak, 'data', 'median share of Net PP&E leaving without depreciation each year '
                                '(FX, impairments, disposals, refranchising); added to projected CapEx')
        if leak > 0.15:
            degraded.append(f'Large unexplained PP&E outflows ({leak:.0%} of Net PP&E per year): verify in 10-K')
    else:
        d['ppe_leakage'] = _drv(0.0, 'data', f'historical PP&E arrived without cash/lease CapEx ({leak:.1%} of PP&E/yr: '
                                'acquisitions or accrued capex); economic CapEx (ΔPP&E + depreciation) used')

    d['ronic'] = _drv('wacc' if scenario == 'conservative' else 'steady_state', 'assumption',
                      'terminal reinvestment: steady_state = growth at g with final-year capital intensity '
                      'and NWC ratio (consistent with explicit years); wacc = excess returns vanish')
    d['wacc'] = _drv(wacc, 'user')

    bands = cal.get('scenario_bands') or {}
    if scenario != 'base' and bands:
        # Horizon-specific p20/p80 bands of the calibrated forecast error (validated
        # out of sample: revenue coverage 54-62% for a 60% band). Revenue level and
        # margin are shifted together, so the combined scenario is more extreme than p20/p80.
        high_t = (cal.get('growth_fade_high') or {}).get('threshold', 0.25)
        group = 'high_growth' if (is_number(g0) and g0 > high_t and 'high_growth' in bands) else 'all'
        k = 0 if scenario == 'conservative' else 1
        tbl = bands[group]
        d['revenue_band'] = _drv([tbl[str(h)]['revenue_log'][k] for h in range(1, 6)], 'calibrated',
                                 f'{scenario}: p{20 if k == 0 else 80} log-revenue error by horizon ({group}); held after year 5')
        d['margin_band'] = _drv([tbl[str(h)]['margin'][k] for h in range(1, 6)], 'calibrated',
                                f'{scenario}: p{20 if k == 0 else 80} margin error by horizon ({group}); held after year 5')
    elif scenario != 'base':
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
    return {'drivers': d, 'status': status, 'blockers': blockers, 'degradations': degraded, 'notes': notes,
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
    cap_rd = 'research_asset0' in v
    if cap_rd:
        life, rd_hist, ra_prev = int(v['rd_life']), list(v['rd_history']), v['research_asset0']
    base_rev = rev_prev
    for t in range(1, horizon + 1):
        g = gT + (g0 - gT) * phi ** t
        base_rev = base_rev * (1 + g)
        rev = base_rev
        margin = mT + (m0 - mT) * psi ** t
        if 'revenue_band' in v:                     # scenario = base path shifted by horizon band
            hb = min(t, 5) - 1
            rev = base_rev * math.exp(v['revenue_band'][hb])
            margin += v['margin_band'][hb]
            g = rev / rev_prev - 1
        ebita = rev * margin
        tax = v['tax_start'] + (v['tax_terminal'] - v['tax_start']) * t / horizon
        k = kT + (k0 - kT) * psik ** t
        dep = v['dep_rate'] * ppe_prev
        ppe = k * rev
        capex = ppe - ppe_prev + dep
        if capex < 0:
            flags.append(f'Year {t}: implied CapEx negative; floored at zero '
                         '(capital intensity falling faster than depreciation)')
            capex, ppe = 0.0, ppe_prev - dep
        leak = v.get('ppe_leakage', 0.0) * ppe_prev
        capex += leak                               # cash spent to replace PP&E that leaves without depreciation
        amort = v['amortization0'] * max(0.0, 1 - t / AMORT_RUNOFF_YEARS)
        ebit = ebita - amort
        nopat = ebit * (1 - tax) if ebit > 0 else ebit   # no tax credit assumed on losses
        nwc_ratio = nT + (n0 - nT) * psi ** t
        nwc = nwc_ratio * rev
        dnwc = nwc - nwc_prev
        fcff = nopat + dep + amort - capex - dnwc
        ic_prev = ppe_prev + nwc_prev
        net_reinv = capex - dep + dnwc
        rd = rd_amort = ra = None
        if cap_rd:
            rd_ratio = v['rd_ratio_target'] + (v['rd_ratio_start'] - v['rd_ratio_target']) * psi ** t
            rd = rd_ratio * rev
            rd_amort = sum(rd_hist[-life:]) / life          # straight-line on the previous L years
            ra = ra_prev + rd - rd_amort
            nopat += rd - rd_amort                           # R&D added back, amortisation charged
            net_reinv += rd - rd_amort                       # ... and treated as investment
            ic_prev += ra_prev
            rd_hist.append(rd)
            ra_prev = ra
        rows.append({
            'year': v['year0'] + t, 't': t, 'revenue': rev, 'growth': g, 'ebit': ebit,
            'ebit_margin': ebit / rev, 'ebita_margin': margin, 'tax_rate': tax, 'nopat': nopat, 'depreciation': dep,
            'amortization': amort, 'da': dep + amort, 'capex': capex, 'net_ppe': ppe,
            'ppe_intensity': ppe / rev, 'nwc': nwc, 'nwc_ratio': nwc_ratio, 'delta_nwc': dnwc,
            'net_reinvestment': net_reinv,
            'reinvestment_rate': net_reinv / nopat if nopat > 0 else None,
            'invested_capital': ppe + nwc + (ra or 0.0), 'rd': rd, 'rd_amortization': rd_amort,
            'research_asset': ra, 'ppe_leakage': leak,
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
    g, wacc, mode = v['terminal_growth'], v['wacc'], v['ronic']
    rev = last['revenue'] * (1 + g)
    nopat = rev * last['ebita_margin'] * (1 - v['tax_terminal'])
    if last.get('research_asset') is not None:
        # steady state: R&D - amortisation = growth of the research asset = g * asset
        nopat += g * last['research_asset']
    if nopat <= 0:
        raise ValueError('Terminal NOPAT is not positive: no going-concern terminal value')
    notes = []
    if mode == 'steady_state':
        # Net investment needed to grow revenue at g while holding final-year
        # Net PP&E / revenue and operating NWC / revenue constant.
        reinvest = g * last['revenue'] * (last['ppe_intensity'] + last['nwc_ratio'])
        if last.get('research_asset') is not None:
            reinvest += g * last['research_asset']           # research asset must grow at g too
        rr = reinvest / nopat
        if rr < 0:
            notes.append('Steady-state reinvestment negative (NWC release exceeds PP&E needs); floored at 0.')
            rr = 0.0
        if rr >= 1:
            raise ValueError('Steady-state reinvestment exceeds NOPAT: growth destroys value at this margin')
        ronic = g / rr if rr > 0 else None
    else:
        ronic = wacc if mode == 'wacc' else mode
        if not is_number(ronic) or ronic <= max(g, 0):
            raise ValueError('RONIC must exceed terminal growth')
        rr = g / ronic if g > 0 else 0.0
    if ronic is not None and ronic > 3 * wacc:
        notes.append(f'Terminal assumes new capital earns {ronic:.0%} on operating capital forever '
                     '(moat persists); compare with the conservative scenario (RONIC = WACC).')
    leak_cost = v.get('ppe_leakage', 0.0) * last['net_ppe'] * (1 + g)
    fcff = nopat * (1 - rr) - leak_cost
    return {'revenue': rev, 'nopat': nopat, 'ronic': ronic, 'reinvestment_rate': rr, 'mode': mode,
            'ppe_leakage_cost': leak_cost,
            'notes': notes, 'fcff': fcff, 'terminal_value': fcff / (wacc - g)}


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
    for r in rows:   # identity: capitalising R&D must not change cash flow
        if r['rd'] is not None:
            reported_nopat = r['nopat'] - (r['rd'] - r['rd_amortization'])
            cash = reported_nopat + r['da'] - r['capex'] - r['delta_nwc']
            if abs(cash - r['fcff']) > 1e-6 * max(1.0, abs(r['fcff'])):
                raise AssertionError('R&D capitalisation changed FCFF')
    for r in rows:   # identity: PP&E roll-forward must hold exactly
        prev = rows[r['t'] - 2]['net_ppe'] if r['t'] > 1 else v['net_ppe0']
        if abs(prev + r['capex'] - r['depreciation'] - r['ppe_leakage'] - r['net_ppe']) > 1e-6 * max(1.0, abs(prev)):
            raise AssertionError('PP&E roll-forward identity violated')
    if abs(last['growth'] - v['terminal_growth']) > 0.005:
        issues.append(f"Not at steady state: year-{last['t']} growth {last['growth']:.1%} vs terminal "
                      f"{v['terminal_growth']:.1%}. Extend horizon or revisit growth fade.")
    if abs(last['ebita_margin'] - v['margin_target']) > 0.01:
        issues.append('Margin still converging in final year; terminal margin is not the long-run target.')
    if valuation:
        rr_term, rr_last = valuation['terminal']['reinvestment_rate'], last['reinvestment_rate']
        if valuation['terminal'].get('mode') == 'wacc':
            if rr_last is not None and rr_term - rr_last > 0.15:
                issues.append(f'Conservative terminal: excess returns vanish after year {last["t"]} '
                              f'(reinvestment {rr_last:.0%} -> {rr_term:.0%}). Intentional stress case.')
        elif rr_last is not None and abs(rr_last - rr_term) > 0.15:
            issues.append(f'Final-year reinvestment rate {rr_last:.0%} vs terminal {rr_term:.0%}: explicit '
                          'capital intensity and terminal RONIC imply different economics.')
        issues.extend(valuation['terminal'].get('notes', []))
        share = valuation['terminal_share_of_ev']
        if share is not None and share > 0.85:
            issues.append(f'Terminal value is {share:.0%} of EV: valuation dominated by perpetuity assumptions.')
    for r in rows:
        if r['roic'] is not None and not 0 <= r['roic'] <= 1.0:
            issues.append(f"Year {r['t']}: ROIC on operating capital {r['roic']:.0%} (ex-goodwill); check plausibility.")
            break
    return issues


def run(history, *, wacc, terminal_growth, net_debt, shares, scenario='base',
        horizon=10, overrides=None, calibration='auto', mid_year=False, rd_life=None, rd_life_note=''):
    """Full pipeline. Returns a dict even when BLOCKED (then without valuation)."""
    cal = load_calibration() if calibration == 'auto' else calibration
    a = derive_assumptions(history, wacc=wacc, terminal_growth=terminal_growth,
                           scenario=scenario, calibration=cal, overrides=overrides,
                           rd_life=rd_life, rd_life_note=rd_life_note)
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
