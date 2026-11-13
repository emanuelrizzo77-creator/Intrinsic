"""Intrinsic Milestone 26C — experimental hybrid forecast engine.

Research prototype: recent-history anchor plus long-run convergence.
Not a point-in-time calibrated model or investment-grade forecast.
Input: audited dictionary returned by analyze_historical_23c().
Output: same scenarios structure as automatic_forecast_engine v2.
"""
from __future__ import annotations

from math import isfinite
from statistics import median, mean

METRICS = {
    'Revenue growth': 'growth',
    'EBIT margin': 'ebit_margin',
    'D&A / Revenue': 'da_ratio',
    'CapEx / Revenue': 'capex_ratio',
}
BOUNDS = {
    'growth': (-0.50, 1.00),
    'ebit_margin': (0.0, 1.0),
    'da_ratio': (0.0, 1.0),
    'capex_ratio': (0.0, 1.0),
}

def _valid(v):
    return isinstance(v, (float, int)) and not isinstance(v, bool) and isfinite(v)

def _clip(v, lo, hi):
    return float(max(lo, min(hi, v)))

def generar_forecast_hibrido(historical):
    """Return five-year scenarios, diagnostics, warnings and validated=False.

    Never silently fills missing audited observations. The DCF's working
    capital assumption remains zero pending a verified NWC model.
    """
    if not isinstance(historical, dict) or not isinstance(historical.get('rows'), list):
        raise ValueError('Expected audited historical dictionary with rows')
    rows = historical['rows']
    if len(rows) < 4:
        raise ValueError('At least four audited annual rows required')
    if any(not isinstance(r, dict) or not r.get('Fiscal year end') for r in rows):
        raise ValueError('Missing fiscal year end or invalid row')
    if len(set(r['Fiscal year end'] for r in rows)) != len(rows):
        raise ValueError('Duplicate fiscal year ends')
    rows = sorted(rows, key=lambda r: r['Fiscal year end'])
    # Require recent periods to be complete: otherwise a stale value could
    # masquerade as a recent observation.
    for metric in METRICS:
        if any(not _valid(r.get(metric)) for r in rows[-2:]):
            raise ValueError(f'Missing recent audited observation: {metric}')

    base = {}
    diagnostics = {}
    for source, key in METRICS.items():
        vals = [float(r[source]) for r in rows if _valid(r.get(source))]
        if len(vals) < 4:
            raise ValueError(f'Insufficient annual observations: {source}')
        historical_anchor = median(vals)
        recent_anchor = mean([float(r[source]) for r in rows[-2:]])
        lo, hi = BOUNDS[key]
        recent_anchor = _clip(recent_anchor, lo, hi)
        historical_anchor = _clip(historical_anchor, lo, hi)
        # Growth normalization is more aggressive when recent growth is
        # unusually elevated relative to the historical median. This is a
        # heuristic, not an industry or market-size forecast.
        if key == 'growth' and recent_anchor > max(0.30, historical_anchor + 0.20):
            # An exceptional growth regime converges toward a conservative
            # fraction of its historical median by year five.
            terminal = _clip(min(historical_anchor, recent_anchor * 0.35), lo, hi)
            speed = 0.40
        else:
            terminal = historical_anchor
            speed = 0.22 if key == 'growth' else 0.28
        series = []
        for year in range(1, 6):
            # Year 1 is the recent anchor; years 2–5 converge smoothly.
            factor = (1.0 - speed) ** (year - 1)
            series.append(_clip(terminal + (recent_anchor - terminal) * factor, lo, hi))
        base[key] = series
        diagnostics[key] = {
            'observations': len(vals),
            'recent_anchor': recent_anchor,
            'historical_anchor': historical_anchor,
            'year_five_value': series[-1],
            'long_run_target': terminal,
            'convergence_rate': speed,
        }

    base['nwc_ratio'] = 0.0
    conservative = {k: list(v) if isinstance(v, list) else v for k, v in base.items()}
    optimistic = {k: list(v) if isinstance(v, list) else v for k, v in base.items()}
    for year in range(5):
        conservative['growth'][year] = _clip(base['growth'][year] - 0.03, *BOUNDS['growth'])
        conservative['ebit_margin'][year] = _clip(base['ebit_margin'][year] - 0.02, *BOUNDS['ebit_margin'])
        optimistic['growth'][year] = _clip(base['growth'][year] + 0.03, *BOUNDS['growth'])
        optimistic['ebit_margin'][year] = _clip(base['ebit_margin'][year] + 0.02, *BOUNDS['ebit_margin'])
    return {
        'scenarios': {'base': base, 'conservative': conservative, 'optimistic': optimistic},
        'diagnostics': diagnostics,
        'warnings': [
            'EXPERIMENTAL hybrid forecast; convergence rates and exceptional-growth threshold are heuristic, not calibrated.',
            'NWC ratio is zero pending a verified operating working-capital model.',
            'CapEx and D&A projected independently; reinvestment consistency is not validated.',
            'Five-year projection accuracy is not established by one-year historical tests.',
        ],
        'validated': False,
    }
