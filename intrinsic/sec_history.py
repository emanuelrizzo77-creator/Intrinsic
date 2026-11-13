"""Intrinsic 23C — SEC historical assumption audit (no DCF, no dashboard changes).

Combines 21B income/cash-flow audit and 23B balance normalization. All amounts
USD; ratios decimals. Partial NWC is a proxy, not full operating working capital.
"""
from __future__ import annotations
from datetime import date
from math import isfinite
from statistics import median
from intrinsic.sec_tags import audit_companyfacts
from intrinsic.balance_sheet import normalize_balance_23b

TAX_TAGS = ('IncomeTaxExpenseBenefit',)
PRETAX_TAGS = ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
               'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments',
               'IncomeLossFromContinuingOperationsBeforeIncomeTaxes')

def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x)

def _annual_fact(payload, tags, end):
    facts = payload.get('facts', {}).get('us-gaap', {})
    for tag in tags:
        records = facts.get(tag, {}).get('units', {}).get('USD', [])
        candidates = []
        for r in records:
            if r.get('form') not in ('10-K', '10-K/A') or r.get('end') != end or not _number(r.get('val')):
                continue
            try:
                days = (date.fromisoformat(r['end']) - date.fromisoformat(r['start'])).days
            except (KeyError, TypeError, ValueError):
                continue
            if 340 <= days <= 400 and r.get('filed'):
                candidates.append(r)
        if candidates:
            r = max(candidates, key=lambda x: (x['filed'], x.get('accn', '')))
            return r['val'], f'us-gaap:{tag}', r['filed']
    return None, None, None

def _ratio(numerator, denominator):
    if _number(numerator) and _number(denominator) and denominator > 0:
        return numerator / denominator
    return None

def _consecutive(a, b):
    return 340 <= (date.fromisoformat(b) - date.fromisoformat(a)).days <= 400

def analyze_historical_23c(payload, last_n=5):
    """Return auditable rows, descriptive medians, warnings, and readiness flags.

    Not a forecast, investment recommendation, or automatically validated DCF.
    """
    if not isinstance(last_n, int) or not 2 <= last_n <= 15:
        raise ValueError('last_n must be between 2 and 15')
    audit = audit_companyfacts(payload, last_n=last_n)
    income = audit['rows']
    balances = normalize_balance_23b(payload, [r['Fiscal year end'] for r in income])
    result = []
    for i, (src, balance) in enumerate(zip(income, balances)):
        end = src['Fiscal year end']
        row = {k: src.get(k) for k in ('Fiscal year end', 'Revenue', 'EBIT', 'D&A verified', 'CapEx', 'Operating Cash Flow')}
        row['source_tags'] = dict(src.get('SEC tag provenance', {}))
        row['warnings'] = list(balance.get('warnings', []))
        row['Revenue growth'] = src.get('Revenue growth')
        row['EBIT margin'] = _ratio(row['EBIT'], row['Revenue'])
        row['D&A / Revenue'] = _ratio(row['D&A verified'], row['Revenue'])
        row['CapEx / Revenue'] = _ratio(row['CapEx'], row['Revenue'])
        tax, tag, _ = _annual_fact(payload, TAX_TAGS, end)
        pretax, pretax_tag, _ = _annual_fact(payload, PRETAX_TAGS, end)
        row['Income tax expense'] = tax
        row['Pretax income'] = pretax
        if tag: row['source_tags']['Income tax expense'] = tag
        if pretax_tag: row['source_tags']['Pretax income'] = pretax_tag
        rate = _ratio(tax, pretax)
        # Negative expense (benefit) and rates outside 0–60% are not a stable forecast input.
        row['Effective tax rate'] = rate if rate is not None and 0 <= rate <= 0.6 else None
        if rate is not None and row['Effective tax rate'] is None:
            row['warnings'].append('Effective tax rate outside 0–60%; excluded from historical baseline.')
        if row['Effective tax rate'] is None:
            row['warnings'].append('No reliable annual effective tax rate for this fiscal year.')
        row['Partial operating NWC'] = balance.get('Partial operating NWC')
        row['Delta partial NWC'] = None
        row['Delta partial NWC / Delta Revenue'] = None
        row['Historical FCFF (partial NWC proxy)'] = None
        if i:
            prev = result[-1]
            if _consecutive(prev['Fiscal year end'], end):
                p, c = prev['Partial operating NWC'], row['Partial operating NWC']
                if _number(p) and _number(c):
                    row['Delta partial NWC'] = c - p
                    dr = row['Revenue'] - prev['Revenue'] if _number(row['Revenue']) and _number(prev['Revenue']) else None
                    if _number(dr) and abs(dr) > 1:
                        row['Delta partial NWC / Delta Revenue'] = (c - p) / dr
                    if (all(_number(row.get(k)) for k in ('EBIT', 'D&A verified', 'CapEx'))
                        and row['Effective tax rate'] is not None):
                        row['Historical FCFF (partial NWC proxy)'] = (
                            row['EBIT'] * (1 - row['Effective tax rate']) + row['D&A verified']
                            - row['CapEx'] - row['Delta partial NWC'])
            else:
                row['warnings'].append('Nonconsecutive fiscal years: NWC change not computed.')
        if row['Historical FCFF (partial NWC proxy)'] is not None:
            row['warnings'].append('Historical FCFF uses PARTIAL NWC only; not a validated full FCFF.')
        result.append(row)
    metrics = ('Revenue growth', 'EBIT margin', 'D&A / Revenue', 'CapEx / Revenue',
               'Effective tax rate', 'Delta partial NWC / Delta Revenue')
    medians = {}
    samples = {}
    for key in metrics:
        vals = [r[key] for r in result if _number(r.get(key))]
        medians[key] = median(vals) if vals else None
        samples[key] = len(vals)
    required = ('Revenue', 'EBIT', 'D&A verified', 'CapEx', 'Effective tax rate')
    latest = result[-1] if result else {}
    blockers = [f'Missing latest {k}' for k in required if latest.get(k) is None]
    if len(result) < 3: blockers.append('Fewer than three annual income statement periods.')
    if not result or result[-1]['Delta partial NWC'] is None:
        blockers.append('No comparable latest-year partial NWC change.')
    # Full working capital, WACC, sector eligibility, EV bridge require separate checks.
    warnings = ['Partial NWC excludes other operating current assets and liabilities.',
                'Historical medians are descriptive, not automatically approved forecast assumptions.',
                'Debt and shares are audited in 23B; this module does not certify valuation readiness.']
    return {'company': payload.get('entityName', 'Unknown'), 'rows': result,
            'historical_medians': medians, 'sample_counts': samples,
            'latest_data_blockers': blockers, 'warnings': warnings,
            'ready_for_automatic_dcf': False}
