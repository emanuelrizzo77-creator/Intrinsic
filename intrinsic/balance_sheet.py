"""Intrinsic 23B — auditable annual SEC balance-sheet normalization.

No external dependencies. Does not alter the Streamlit dashboard.
Debt includes leases when the reported source includes leases. Shares from DEI
are post-year-end snapshots, not fiscal-year-end measurements.
"""
from __future__ import annotations
from datetime import date
from math import isfinite

FORMS = {'10-K', '10-K/A'}

def _valid(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v) and v >= 0

def _records(facts, namespace, tag, unit='USD'):
    return facts.get(namespace, {}).get(tag, {}).get('units', {}).get(unit, [])

def _annual_point(facts, end, tags, namespace='us-gaap', unit='USD'):
    for tag in tags:
        options = [r for r in _records(facts, namespace, tag, unit)
                   if r.get('form') in FORMS and r.get('end') == end
                   and 'start' not in r and _valid(r.get('val')) and r.get('filed')]
        if options:
            r = max(options, key=lambda x: (x.get('filed', ''), x.get('accn', '')))
            return r['val'], f'{namespace}:{tag}', r['filed']
    return None, None, None

def _shares_snapshot(facts, end):
    """Use DEI snapshot in annual filing 1–150 days after fiscal year end.

    Do not pretend the snapshot is measured on fiscal year end.
    """
    fiscal = date.fromisoformat(end)
    options = []
    for r in _records(facts, 'dei', 'EntityCommonStockSharesOutstanding', 'shares'):
        if r.get('form') not in FORMS or 'start' in r or not _valid(r.get('val')):
            continue
        try:
            measured, filed = date.fromisoformat(r['end']), date.fromisoformat(r['filed'])
        except (KeyError, ValueError, TypeError):
            continue
        days = (measured - fiscal).days
        if 1 <= days <= 150 and measured <= filed and (filed - fiscal).days <= 180:
            options.append((days, -filed.toordinal(), r))
    if not options:
        return None, None, None
    r = min(options, key=lambda x: (x[0], x[1]))[2]
    return r['val'], r['end'], r['filed']

def normalize_balance_23b(payload, fiscal_ends):
    facts = payload.get('facts', {})
    output = []
    for end in fiscal_ends:
        row = {'Fiscal year end': end, 'tags': {}, 'warnings': [], 'source_filed': {}}
        def take(label, tags):
            v, tag, filed = _annual_point(facts, end, tags)
            row[label] = v
            if tag:
                row['tags'][label] = tag
                row['source_filed'][label] = filed
            return v

        cash = take('Cash', ('CashAndCashEquivalentsAtCarryingValue',))
        if cash is None:
            take('Cash', ('CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',))
            if row['Cash'] is not None:
                row['warnings'].append('Cash includes restricted cash; verify before subtracting from enterprise value.')
        take('Short-term investments', ('ShortTermInvestments', 'MarketableSecuritiesCurrent'))
        ar = take('Receivables', ('AccountsNotesAndOtherReceivablesNetCurrent', 'AccountsReceivableNetCurrent', 'AccountsReceivableNet'))
        inv = take('Inventory', ('InventoryNet',))
        ap = take('Payables', ('AccountsPayableTradeCurrent', 'AccountsPayableCurrent'))
        take('Payables and accrued liabilities', ('AccountsPayableAndAccruedLiabilitiesCurrent',))
        take('Other accrued liabilities', ('OtherAccruedLiabilitiesCurrent',))
        if ap is None:
            row['warnings'].append('Trade payables unavailable: combined payables and accrued liabilities are NOT substituted.')
        row['Partial operating NWC'] = ar + inv - ap if all(_valid(x) for x in (ar, inv, ap)) else None
        row['warnings'].append('Partial operating NWC = receivables + inventory - trade payables; not full operating NWC.')

        # Prefer total debt inclusive of current maturities; subtract cash ONCE.
        total = take('Total debt including current maturities',
                     ('LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities',))
        noncurrent = take('Long-term debt', ('LongTermDebtAndCapitalLeaseObligations',
                                           'LongTermDebtNoncurrent'))
        current = take('Current debt', ('LongTermDebtAndCapitalLeaseObligationsCurrent', 'LongTermDebtCurrent'))
        if total is not None:
            if noncurrent is not None and current is not None:
                if abs(total - noncurrent - current) > max(1, total * 0.001):
                    row['warnings'].append('Reported total debt does not reconcile to current + noncurrent debt.')
            elif noncurrent is not None and total >= noncurrent:
                row['Current debt'] = total - noncurrent
                row['tags']['Current debt'] = 'derived:total_debt_minus_noncurrent_debt'
                current = row['Current debt']
            elif current is not None and total >= current:
                row['Long-term debt'] = total - current
                row['tags']['Long-term debt'] = 'derived:total_debt_minus_current_debt'
                noncurrent = row['Long-term debt']
            row['Total debt'] = total
            row['tags']['Total debt'] = row['tags']['Total debt including current maturities']
            row['warnings'].append('Debt includes capital lease obligations under the selected SEC tag.')
        elif current is not None and noncurrent is not None:
            row['Total debt'] = current + noncurrent
            row['tags']['Total debt'] = 'derived:current_plus_noncurrent'
        else:
            row['Total debt'] = None
            row['warnings'].append('Insufficient debt components; net debt not calculated.')
        row['Net debt (cash-only)'] = (row['Total debt'] - row['Cash']
                                       if _valid(row['Total debt']) and _valid(row['Cash'])
                                       and not row['tags'].get('Cash', '').endswith('CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents')
                                       else None)
        shares, snapshot_date, filed = _shares_snapshot(facts, end)
        row['Shares outstanding'] = shares
        row['Shares measurement date'] = snapshot_date
        if shares is not None:
            row['tags']['Shares outstanding'] = 'dei:EntityCommonStockSharesOutstanding'
            row['source_filed']['Shares outstanding'] = filed
            row['warnings'].append(f'Shares measured {snapshot_date}, after fiscal year end {end}; not year-end shares.')
        else:
            row['warnings'].append('No qualifying DEI shares snapshot for this fiscal year; market-data fallback requires separate verification.')
        if row['Short-term investments'] is None:
            row['warnings'].append('Short-term investments unavailable; not assumed zero.')
        output.append(row)
    return output
