"""Intrinsic 18H: explicit Alphabet-only DCF proxy, NOT complete D&A/ONWC.

D&A proxy = reported depreciation only; working capital proxy = AR - AP.
Neither should be labeled as complete D&A or operating NWC.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date
from statistics import median
import math
from financial_engine import descargar_datos
from historical_ratios_engine import obtener_ratios_empresa


def _instant_series(datos, tag):
    facts = datos.get('facts', {}).get('us-gaap', {})
    records = facts.get(tag, {}).get('units', {}).get('USD', [])
    by_year = {}
    for r in records:
        if r.get('form') != '10-K' or 'start' in r or not all(k in r for k in ('end', 'filed', 'val')):
            continue
        v = r['val']
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            continue
        try:
            end, filed = date.fromisoformat(r['end']), date.fromisoformat(r['filed'])
        except (TypeError, ValueError):
            continue
        year = end.year
        # First most recent balance date, then latest filing of same date.
        if year not in by_year or (end, filed) > by_year[year][:2]:
            by_year[year] = (end, filed, float(v))
    return by_year


def obtener_ratios_alternativos_googl(datos_historicos=None, datos_sec=None):
    """Return existing historical schema with labeled, GOOGL-only proxies.

    Raw source data and original metrics are preserved per row. Missing or
    incompatible observations remain unavailable; no zero substitution.
    """
    original = datos_historicos if datos_historicos is not None else obtener_ratios_empresa('GOOGL')
    if original.get('ticker') != 'GOOGL':
        raise ValueError('El histórico no corresponde a GOOGL')
    datos = datos_sec if datos_sec is not None else descargar_datos('GOOGL')
    ar = _instant_series(datos, 'AccountsReceivableNetCurrent')
    ap = _instant_series(datos, 'AccountsPayableCurrent')
    proxy_balance = {}
    for year in ar.keys() & ap.keys():
        if ar[year][0] == ap[year][0]:
            proxy_balance[year] = ar[year][2] - ap[year][2]
    result = deepcopy(original)
    rows = result['ratios']
    revenue = {r['year']: r['revenue'] for r in rows}
    for r in rows:
        y, rev = r['year'], r['revenue']
        r['original_da_ratio'] = r.get('da_ratio')
        r['original_nwc_ratio'] = r.get('nwc_ratio')
        r['da_ratio'] = (r['depreciation'] / rev if isinstance(r.get('depreciation'), (int, float)) and rev > 0 else None)
        r['nwc_ratio'] = None
        r['ar_ap_proxy'] = proxy_balance.get(y)
        if y in proxy_balance and y - 1 in proxy_balance and y - 1 in revenue:
            delta_revenue = rev - revenue[y - 1]
            if revenue[y - 1] > 0 and abs(delta_revenue) >= 0.02 * revenue[y - 1] and delta_revenue != 0:
                r['nwc_ratio'] = (proxy_balance[y] - proxy_balance[y - 1]) / delta_revenue
    latest = max(r['year'] for r in rows)
    summary = deepcopy(result['summary'])
    for metric in ('da_ratio', 'nwc_ratio'):
        available = [(r['year'], r[metric]) for r in rows if r['year'] >= latest - 3 and isinstance(r[metric], (int, float)) and math.isfinite(r[metric])]
        selected = available[-3:]
        summary[metric] = {'median': median(v for _, v in selected) if selected else None,
                           'years': [y for y, _ in selected], 'observations': len(selected),
                           'status': 'AVAILABLE' if len(selected) >= 2 else ('LIMITED' if selected else 'MISSING_RECENT')}
    result['summary'] = summary
    result['methodology'] = 'GOOGL_DEPRECIATION_ONLY_AR_MINUS_AP_PROXY'
    result['warnings'] = [w for w in result.get('warnings', []) if not (w.startswith('GOOGL: complete D&A') or w.startswith('da_ratio:') or w.startswith('nwc_ratio:'))]
    result['warnings'] += [
        'GOOGL 18H: da_ratio = SEC depreciation/revenue ONLY; excludes any unidentified amortization. This is NOT complete D&A.',
        'GOOGL 18H: nwc_ratio = change in (AR - AP) / change in revenue; excludes inventory and other operating working-capital items. NOT complete ONWC.',
        'GOOGL 18H: proxy DCF is illustrative and may materially misstate FCFF and enterprise value.',
    ]
    return result
