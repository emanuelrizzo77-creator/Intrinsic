"""Intrinsic 21D: auditable SEC balance-sheet normalization and illustrative FCFF engine.

Not a universal certified valuation. Only nonfinancial operating companies with
sufficient, aligned SEC US-GAAP annual facts are eligible for a preview.
"""
from __future__ import annotations
from datetime import date
from math import isfinite

BALANCE_TAGS = {
    'Cash': ('CashAndCashEquivalentsAtCarryingValue',),
    'Short-term investments': ('ShortTermInvestments', 'MarketableSecuritiesCurrent'),
    'Receivables': ('AccountsNotesAndOtherReceivablesNetCurrent', 'AccountsReceivableNetCurrent'),
    'Inventory': ('InventoryNet',),
    'Payables': ('AccountsPayableCurrent',),
    'Current debt': ('LongTermDebtCurrent', 'LongTermDebtAndCapitalLeaseObligationsCurrent', 'ShortTermBorrowings'),
    'Long-term debt': ('LongTermDebtNoncurrent', 'LongTermDebtAndCapitalLeaseObligations'),
    'Shares outstanding': ('CommonStockSharesOutstanding',),
}

def _valid(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v)

def _point(fact, end, unit):
    eligible = []
    for x in fact.get('units', {}).get(unit, []):
        if x.get('form') not in ('10-K', '10-K/A') or x.get('end') != end or 'start' in x:
            continue
        if not _valid(x.get('val')) or not x.get('filed'):
            continue
        eligible.append(x)
    if not eligible:
        return None
    return max(eligible, key=lambda x: x['filed'])['val']

def normalize_balance(payload, fiscal_ends):
    facts = payload.get('facts', {}).get('us-gaap', {})
    results = []
    for end in fiscal_ends:
        record = {'Fiscal year end': end, 'tags': {}}
        for label, tags in BALANCE_TAGS.items():
            unit = 'shares' if label == 'Shares outstanding' else 'USD'
            found = None
            for tag in tags:
                found = _point(facts.get(tag, {}), end, unit)
                if found is not None:
                    record['tags'][label] = tag
                    break
            record[label] = found
        # Missing investments cannot be assumed zero. Use cash-only net debt
        # and disclose excluded nonoperating investments when computing preview.
        ar, inv, ap = (record[k] for k in ('Receivables', 'Inventory', 'Payables'))
        record['Partial operating NWC'] = ar + inv - ap if all(_valid(v) for v in (ar, inv, ap)) else None
        debt = (record['Current debt'], record['Long-term debt'])
        record['Net debt (cash-only)'] = sum(debt) - record['Cash'] if all(_valid(v) for v in (*debt, record['Cash'])) else None
        results.append(record)
    return results

def readiness(audit_rows, balance_rows, model):
    issues = []
    if model != 'fcff':
        issues.append('This company requires a sector-specific valuation model, not FCFF.')
    if len(audit_rows) < 3:
        issues.append('At least three historical annual income-statement periods are required.')
    if len(balance_rows) < 2:
        issues.append('At least two aligned annual balance-sheet periods are required.')
    if audit_rows and balance_rows and audit_rows[-1]['Fiscal year end'] != balance_rows[-1]['Fiscal year end']:
        issues.append('Income statement and balance sheet latest fiscal dates differ.')
    if audit_rows:
        latest = audit_rows[-1]
        for k in ('Revenue', 'EBIT', 'D&A verified', 'CapEx'):
            if not _valid(latest.get(k)):
                issues.append('Missing or invalid latest ' + k)
        if not _valid(latest.get('Revenue')) or latest['Revenue'] <= 0:
            issues.append('Latest revenue must be positive.')
    if balance_rows:
        latest = balance_rows[-1]
        for k in ('Net debt (cash-only)', 'Shares outstanding'):
            if not _valid(latest.get(k)):
                issues.append('Missing ' + k)
        if _valid(latest.get('Shares outstanding')) and latest['Shares outstanding'] <= 0:
            issues.append('Shares outstanding must be positive.')
    if len(balance_rows) >= 2 and not all(_valid(r.get('Partial operating NWC')) for r in balance_rows[-2:]):
        issues.append('Missing comparable receivables, inventory or payables for NWC changes.')
    return issues

def forecast_fcff(audit_rows, balance_rows, *, growth, margin, da_ratio, capex_ratio, nwc_ratio, tax_rate, wacc, terminal_growth, years=5):
    """Illustrative scenario only; explicit inputs required. Returns projected FCFF and EV.

    nwc_ratio models incremental operating NWC / incremental revenue, not full ONWC.
    """
    inputs = (growth, margin, da_ratio, capex_ratio, nwc_ratio, tax_rate, wacc, terminal_growth)
    if not all(_valid(v) for v in inputs):
        raise ValueError('All scenario inputs must be finite numbers.')
    if not (-0.5 <= growth <= 0.5 and -1 <= margin <= 1 and 0 <= da_ratio <= 1 and 0 <= capex_ratio <= 1 and -1 <= nwc_ratio <= 1 and 0 <= tax_rate <= 0.6 and 0 < wacc < 1 and -0.05 <= terminal_growth < wacc):
        raise ValueError('Scenario parameters outside safe ranges or WACC <= terminal growth.')
    if not isinstance(years, int) or not 1 <= years <= 15:
        raise ValueError('Invalid projection horizon.')
    if not audit_rows or not _valid(audit_rows[-1].get('Revenue')) or audit_rows[-1]['Revenue'] <= 0:
        raise ValueError('Valid revenue is required.')
    if not balance_rows or not _valid(balance_rows[-1].get('Net debt (cash-only)')) or not _valid(balance_rows[-1].get('Shares outstanding')) or balance_rows[-1]['Shares outstanding'] <= 0:
        raise ValueError('Valid net debt and shares are required.')
    rev = audit_rows[-1]['Revenue']
    projections = []
    pv = 0.0
    for year in range(1, years+1):
        next_rev = rev * (1+growth)
        ebit = next_rev * margin
        nopat = ebit * (1-tax_rate)
        da = next_rev * da_ratio
        capex = next_rev * capex_ratio
        delta_nwc = (next_rev-rev)*nwc_ratio
        fcff = nopat + da - capex - delta_nwc
        pv += fcff/(1+wacc)**year
        projections.append({'Year':year, 'Revenue':next_rev, 'EBIT':ebit, 'NOPAT':nopat, 'D&A':da, 'CapEx':capex, 'Delta NWC proxy':delta_nwc, 'FCFF':fcff})
        rev = next_rev
    tv = projections[-1]['FCFF']*(1+terminal_growth)/(wacc-terminal_growth)
    ev = pv + tv/(1+wacc)**years
    net_debt = balance_rows[-1]['Net debt (cash-only)']
    equity = ev - net_debt
    return {'projections':projections, 'pv_explicit_fcff':pv, 'terminal_value':tv, 'enterprise_value':ev, 'net_debt_cash_only':net_debt, 'equity_value':equity, 'intrinsic_value_per_share':equity/balance_rows[-1]['Shares outstanding'], 'status':'ILLUSTRATIVE_NOT_VALIDATED'}
