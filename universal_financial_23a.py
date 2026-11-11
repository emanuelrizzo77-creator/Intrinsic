"""Intrinsic 23A: audited SEC annual balance extraction (no fabricated zeros).

This module does not certify a DCF. It improves 21D extraction, including DEI
shares and alternative payables tags. It deliberately rejects ambiguous debt.
"""
from __future__ import annotations
from datetime import date
from math import isfinite

TAGS = {
    'Cash': ('us-gaap', ('CashAndCashEquivalentsAtCarryingValue', 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents')),
    'Short-term investments': ('us-gaap', ('ShortTermInvestments', 'MarketableSecuritiesCurrent')),
    'Receivables': ('us-gaap', ('AccountsNotesAndOtherReceivablesNetCurrent', 'AccountsReceivableNetCurrent', 'AccountsReceivableNet')),
    'Inventory': ('us-gaap', ('InventoryNet',)),
    'Payables': ('us-gaap', ('AccountsPayableCurrent', 'AccountsPayableAndAccruedLiabilitiesCurrent')),
    'Current debt': ('us-gaap', ('LongTermDebtCurrent', 'LongTermDebtAndCapitalLeaseObligationsCurrent', 'ShortTermBorrowings')),
    'Long-term debt': ('us-gaap', ('LongTermDebtNoncurrent', 'LongTermDebtAndCapitalLeaseObligationsNoncurrent')),
    'Shares outstanding': ('dei', ('EntityCommonStockSharesOutstanding',)),
}

def valid(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v)

def _point(fact, end, unit):
    matches = []
    for item in fact.get('units', {}).get(unit, []):
        if item.get('form') not in ('10-K', '10-K/A') or item.get('end') != end or 'start' in item or not valid(item.get('val')):
            continue
        try:
            filed = date.fromisoformat(item['filed'])
        except (KeyError, ValueError, TypeError):
            continue
        matches.append((filed, item['val']))
    return max(matches, key=lambda x: x[0])[1] if matches else None

def normalize_balance_23a(payload, fiscal_ends):
    facts = payload.get('facts', {})
    output = []
    for end in fiscal_ends:
        row = {'Fiscal year end': end, 'tags': {}, 'warnings': []}
        for label, (namespace, tags) in TAGS.items():
            unit = 'shares' if label == 'Shares outstanding' else 'USD'
            value = None
            for tag in tags:
                value = _point(facts.get(namespace, {}).get(tag, {}), end, unit)
                if value is not None:
                    row['tags'][label] = f'{namespace}:{tag}'
                    break
            # Fallback: common shares are sometimes tagged in us-gaap.
            if label == 'Shares outstanding' and value is None:
                for tag in ('CommonStockSharesOutstanding', 'CommonStockSharesIssued'):
                    value = _point(facts.get('us-gaap', {}).get(tag, {}), end, 'shares')
                    if value is not None:
                        row['tags'][label] = f'us-gaap:{tag}'
                        if tag.endswith('Issued'):
                            row['warnings'].append('Shares issued are NOT equivalent to shares outstanding; manual verification required.')
                            value = None
                        break
            row[label] = value
        ar, inv, ap = (row[k] for k in ('Receivables', 'Inventory', 'Payables'))
        row['Partial operating NWC'] = ar + inv - ap if all(valid(v) for v in (ar, inv, ap)) else None
        current, longterm, cash = (row[k] for k in ('Current debt', 'Long-term debt', 'Cash'))
        row['Net debt (cash-only)'] = current + longterm - cash if all(valid(v) for v in (current, longterm, cash)) else None
        if row['tags'].get('Payables', '').endswith('AccountsPayableAndAccruedLiabilitiesCurrent'):
            row['warnings'].append('Payables include accrued liabilities: partial NWC is not comparable to accounts-payable-only periods.')
        if row['tags'].get('Cash', '').endswith('CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'):
            row['warnings'].append('Cash includes restricted cash; cash-only net debt needs reconciliation.')
        if row['Short-term investments'] is None:
            row['warnings'].append('Short-term investments unavailable; do not assume zero.')
        if row['Shares outstanding'] is None:
            row['warnings'].append('Shares outstanding unavailable for this fiscal year end; DEI may report a different measurement date.')
        output.append(row)
    return output
