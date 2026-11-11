"""Intrinsic 24B: generic, provenance-first SEC XBRL coverage resolver.

This is a conservative extension of 23B/23C, not a certified FCFF engine.
No ticker-specific rules; never converts absent data to zero.
"""
from __future__ import annotations
from datetime import date
from math import isfinite
from statistics import median
from universal_financial_23b import normalize_balance_23b
from universal_financial_23c import analyze_historical_23c

# Ordered *semantically compatible* candidates; do not combine overlapping facts.
ANNUAL_TAGS = {
    'Revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax', 'RevenueFromContractWithCustomerIncludingAssessedTax', 'Revenues', 'SalesRevenueNet', 'SalesRevenueGoodsNet', 'SalesRevenueServicesNet'),
    'EBIT': ('OperatingIncomeLoss',),
    'CapEx': ('PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets', 'PaymentsForProceedsFromOtherInvestingActivities'),
    'D&A verified': ('DepreciationDepletionAndAmortization', 'DepreciationDepletionAndAmortizationPropertyPlantAndEquipment'),
    'Income tax expense': ('IncomeTaxExpenseBenefit',),
    'Pretax income': ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments', 'IncomeLossFromContinuingOperationsBeforeIncomeTaxes'),
}
# Some candidate tags have broader definitions. Keep them explicitly separate from strict data.
STRICT_TAGS = {
    'Revenue': ANNUAL_TAGS['Revenue'][:4],
    'EBIT': ANNUAL_TAGS['EBIT'],
    'CapEx': ANNUAL_TAGS['CapEx'][:2],
    'D&A verified': ANNUAL_TAGS['D&A verified'][:1],
    'Income tax expense': ANNUAL_TAGS['Income tax expense'],
    'Pretax income': ANNUAL_TAGS['Pretax income'],
}

def valid(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x)

def point(facts, tags, end, unit='USD'):
    """Use a 10-K instant observation, without assuming a missing balance is zero."""
    for tag in tags:
        records = facts.get('us-gaap', {}).get(tag, {}).get('units', {}).get(unit, [])
        options = [r for r in records if r.get('form') in ('10-K', '10-K/A') and
                   r.get('end') == end and 'start' not in r and valid(r.get('val')) and r.get('filed')]
        if options:
            r = max(options, key=lambda x: (x['filed'], x.get('accn', '')))
            return r['val'], f'us-gaap:{tag}'
    return None, None

def annual(facts, tags, end):
    """Annual flows must cover ~12 months, not a quarter or comparative YTD."""
    for tag in tags:
        records = facts.get('us-gaap', {}).get(tag, {}).get('units', {}).get('USD', [])
        options = []
        for r in records:
            if r.get('form') not in ('10-K', '10-K/A') or r.get('end') != end or not valid(r.get('val')) or not r.get('filed'):
                continue
            try:
                days = (date.fromisoformat(end) - date.fromisoformat(r['start'])).days
            except (KeyError, TypeError, ValueError):
                continue
            if 340 <= days <= 400:
                options.append(r)
        if options:
            r = max(options, key=lambda x: (x['filed'], x.get('accn', '')))
            return r['val'], f'us-gaap:{tag}'
    return None, None

def balance_24b(payload, ends):
    rows = normalize_balance_23b(payload, ends)
    facts = payload.get('facts', {})
    for row in rows:
        end = row['Fiscal year end']
        # Only reconstruct from compatible noncurrent + current debt; do not treat a
        # gross debt tag as a noncurrent tag or count leases twice.
        if row['Total debt'] is None:
            current, ct = point(facts, ('LongTermDebtCurrent', 'LongTermDebtAndCapitalLeaseObligationsCurrent'), end)
            noncurrent, nt = point(facts, ('LongTermDebtNoncurrent',), end)
            if current is not None and noncurrent is not None and current >= 0 and noncurrent >= 0:
                row['Current debt'], row['Long-term debt'] = current, noncurrent
                row['Total debt'] = current + noncurrent
                row['tags'].update({'Current debt':ct, 'Long-term debt':nt, 'Total debt':'derived:current_plus_noncurrent'})
                row['Net debt (cash-only)'] = row['Total debt'] - row['Cash'] if row['Cash'] is not None and row['tags'].get('Cash') == 'us-gaap:CashAndCashEquivalentsAtCarryingValue' else None
        # Explicitly prefer trade payables for the partial proxy, never combined accrued liabilities.
        row['NWC quality'] = 'PARTIAL_PROXY' if row.get('Partial operating NWC') is not None else 'MISSING'
    return rows

def history_24b(payload, last_n=5):
    """Return 23C-compatible historical output with conservative missing-tag recovery.

    Only uses strict equivalent tags for automatic baseline. Broader candidates
    are reported as suggestions, not silently inserted into the valuation.
    """
    history = analyze_historical_23c(payload, last_n=last_n)
    facts = payload.get('facts', {})
    for row in history['rows']:
        end = row['Fiscal year end']
        row.setdefault('source_tags', {})
        row.setdefault('warnings', [])
        row['candidate_alternatives'] = {}
        for field, tags in STRICT_TAGS.items():
            target = 'D&A verified' if field == 'D&A verified' else field
            if row.get(target) is None:
                value, tag = annual(facts, tags, end)
                if value is not None and (target not in ('CapEx', 'D&A verified') or value >= 0):
                    row[target] = value
                    row['source_tags'][target] = tag
            if row.get(target) is None:
                broad = tuple(t for t in ANNUAL_TAGS[field] if t not in tags)
                v, t = annual(facts, broad, end)
                if v is not None:
                    row['candidate_alternatives'][target] = {'value':v,'tag':t,'note':'broader definition; manual review required'}
        rev = row.get('Revenue')
        for label, numerator in [('EBIT margin','EBIT'), ('D&A / Revenue','D&A verified'), ('CapEx / Revenue','CapEx')]:
            row[label] = row[numerator] / rev if valid(rev) and rev > 0 and valid(row.get(numerator)) else None
        tax, pretax = row.get('Income tax expense'), row.get('Pretax income')
        if row.get('Effective tax rate') is None and valid(tax) and valid(pretax) and pretax > 0:
            rate = tax / pretax
            row['Effective tax rate'] = rate if 0 <= rate <= .6 else None
    # Recompute latest-year blockers, keeping partial-NWC limitation explicit.
    required = ('Revenue','EBIT','D&A verified','CapEx','Effective tax rate')
    latest = history['rows'][-1] if history['rows'] else {}
    blockers = [f'Missing latest {k}' for k in required if latest.get(k) is None]
    if len(history['rows']) < 3: blockers.append('Fewer than three annual income statement periods.')
    if latest.get('Delta partial NWC') is None: blockers.append('No comparable latest-year partial NWC change.')
    history['latest_data_blockers'] = blockers
    for metric in ('EBIT margin','D&A / Revenue','CapEx / Revenue','Effective tax rate'):
        vals = [r[metric] for r in history['rows'] if valid(r.get(metric))]
        history['historical_medians'][metric] = median(vals) if vals else None
        history['sample_counts'][metric] = len(vals)
    history['warnings'].append('24B resolver adds only conservative tag alternatives; full NWC and enterprise bridge remain unvalidated.')
    history['ready_for_automatic_dcf'] = False
    return history

def coverage_24b(payload):
    history = history_24b(payload)
    rows = history['rows']
    if not rows:
        return {'company':history['company'], 'status':'MISSING_DATA', 'missing':['No annual SEC financial records'], 'latest_year':None}
    latest = rows[-1]
    balance = balance_24b(payload, [latest['Fiscal year end']])[0]
    missing = [k for k in ('Revenue','EBIT','D&A verified','CapEx','Effective tax rate') if latest.get(k) is None]
    for k in ('Net debt (cash-only)','Shares outstanding'):
        if balance.get(k) is None: missing.append(k)
    if latest.get('Delta partial NWC') is None: missing.append('Delta partial NWC')
    return {'company':history['company'], 'latest_year':latest['Fiscal year end'],
            'status':'MISSING_DATA' if missing else 'PROVISIONAL_SCENARIO_ONLY',
            'missing':missing, 'balance':balance, 'history':history}
