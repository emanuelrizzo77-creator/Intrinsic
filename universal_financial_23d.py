"""Intrinsic 23D: auditable five-year FCFF forecast; independent of Streamlit.

Partial NWC is never silently used as complete operating NWC. Forecast output
is explicitly provisional until the working-capital policy is validated.
"""
from __future__ import annotations
from math import isfinite

KEYS = ('Revenue growth', 'EBIT margin', 'Effective tax rate', 'D&A / Revenue', 'CapEx / Revenue')
LIMITS = {
    'Revenue growth': (-0.75, 1.5),
    'EBIT margin': (-1.0, 1.0),
    'Effective tax rate': (0.0, 0.6),
    'D&A / Revenue': (0.0, 0.8),
    'CapEx / Revenue': (0.0, 1.5),
}

def _valid(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x)

def forecast_23d(historical, years=5, overrides=None, nwc_policy='zero_change', nwc_ratio=None):
    """Project FCFF using medians and explicit user overrides.

    nwc_policy: 'zero_change' assumes no incremental NWC (not a fact);
                'partial_proxy' uses historical partial-NWC / delta revenue;
                'manual_ratio' uses supplied incremental NWC / delta revenue.
    Ratios are decimals, amounts USD. No discounting or terminal value here.
    """
    if not isinstance(years, int) or isinstance(years, bool) or not 1 <= years <= 15:
        raise ValueError('years must be an integer from 1 to 15')
    rows = historical.get('rows', [])
    if not rows or not _valid(rows[-1].get('Revenue')) or rows[-1]['Revenue'] <= 0:
        raise ValueError('Latest historical revenue is missing or invalid')
    medians = historical.get('historical_medians', {})
    overrides = overrides or {}
    unknown = set(overrides) - set(KEYS)
    if unknown:
        raise ValueError(f'Unknown override(s): {sorted(unknown)}')
    assumptions = {}
    sources = {}
    for key in KEYS:
        val = overrides[key] if key in overrides else medians.get(key)
        if not _valid(val):
            raise ValueError(f'Missing or invalid assumption: {key}')
        low, high = LIMITS[key]
        if not low <= val <= high:
            raise ValueError(f'Assumption out of safety range: {key}')
        assumptions[key] = float(val)
        sources[key] = 'manual override' if key in overrides else 'historical median'
    if nwc_policy not in ('zero_change', 'partial_proxy', 'manual_ratio'):
        raise ValueError('Unknown NWC policy')
    if nwc_policy == 'zero_change':
        nwc_rate = 0.0
        nwc_source = 'scenario assumption: zero incremental working capital'
    elif nwc_policy == 'partial_proxy':
        nwc_rate = medians.get('Delta partial NWC / Delta Revenue')
        nwc_source = 'historical PARTIAL NWC proxy (not full operating NWC)'
    else:
        nwc_rate = nwc_ratio
        nwc_source = 'manual incremental working-capital ratio'
    if not _valid(nwc_rate) or not -2 <= nwc_rate <= 2:
        raise ValueError('NWC ratio unavailable or outside safety range')
    try:
        last_year = int(rows[-1]['Fiscal year end'][:4])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Missing fiscal-year end') from exc
    revenue = float(rows[-1]['Revenue'])
    result = []
    for i in range(1, years + 1):
        previous = revenue
        revenue = previous * (1 + assumptions['Revenue growth'])
        delta_revenue = revenue - previous
        ebit = revenue * assumptions['EBIT margin']
        nopat = ebit * (1 - assumptions['Effective tax rate'])
        da = revenue * assumptions['D&A / Revenue']
        capex = revenue * assumptions['CapEx / Revenue']
        delta_nwc = delta_revenue * nwc_rate
        fcff = nopat + da - capex - delta_nwc
        if not all(_valid(x) for x in (revenue, ebit, nopat, da, capex, delta_nwc, fcff)):
            raise ValueError('Nonfinite forecast result')
        result.append({'Year': f'{last_year + i}E', 'Revenue': revenue,
                       'Revenue growth': assumptions['Revenue growth'], 'EBIT': ebit,
                       'NOPAT': nopat, 'D&A': da, 'CapEx': capex,
                       'Delta NWC': delta_nwc, 'FCFF': fcff})
    return {'company': historical.get('company'), 'assumptions': assumptions,
            'assumption_sources': sources, 'nwc_policy': nwc_policy,
            'nwc_ratio': nwc_rate, 'nwc_source': nwc_source, 'rows': result,
            'valuation_ready': False,
            'warnings': ['Provisional FCFF: full operating working capital has not been independently validated.',
                         'Historical median assumptions are descriptive, not analyst forecasts.',
                         'No WACC, terminal value, enterprise value, or share price calculated.']}
