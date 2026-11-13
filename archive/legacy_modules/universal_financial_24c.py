"""Intrinsic 24C: generic, auditable XBRL resolver and coverage classification.

Does not silently turn missing data into zero or assert that a partial NWC
proxy is a complete operating working-capital calculation.
"""
from __future__ import annotations
from datetime import date
from statistics import median
from universal_financial_24b import balance_24b, history_24b, annual, point, valid


def _positive_annual(facts, tags, end):
    value, source = annual(facts, tags, end)
    return (value, source) if valid(value) and value >= 0 else (None, None)


def resolve_history(payload, last_n=5):
    result = history_24b(payload, last_n=last_n)
    facts = payload.get('facts', {})
    for row in result['rows']:
        end = row['Fiscal year end']
        sources = row.setdefault('source_tags', {})
        notes = row.setdefault('warnings', [])
        # Some issuers separately report cash-flow depreciation and amortization.
        # Sum only explicitly non-overlapping components, never a combined D&A tag.
        if row.get('D&A verified') is None:
            depreciation, dep_tag = _positive_annual(facts, (
                'Depreciation', 'DepreciationDepletionAndAmortizationPropertyPlantAndEquipment',
            ), end)
            amortization, amort_tag = _positive_annual(facts, (
                'AmortizationOfIntangibleAssets',
            ), end)
            if depreciation is not None and amortization is not None:
                row['D&A verified'] = depreciation + amortization
                sources['D&A verified'] = f'derived:{dep_tag}+{amort_tag}'
                notes.append('D&A reconstructed from separately reported depreciation and intangible amortization; check cash-flow classification.')
        # OperatingIncomeLoss is preferred; do not derive EBIT from pretax
        # income plus interest without verifying nonoperating gains/losses.
        # Annual net tax expense / positive pretax income is only a descriptive rate.
        if row.get('Effective tax rate') is None:
            tax, tax_tag = annual(facts, ('IncomeTaxExpenseBenefit',), end)
            pretax, pretax_tag = annual(facts, (
                'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments',
                'IncomeLossFromContinuingOperationsBeforeIncomeTaxes',
            ), end)
            if valid(tax) and valid(pretax) and pretax > 0 and 0 <= tax / pretax <= .6:
                row['Effective tax rate'] = tax / pretax
                sources['Effective tax rate'] = f'derived:{tax_tag}/{pretax_tag}'
        revenue = row.get('Revenue')
        for ratio, numerator in [('EBIT margin', 'EBIT'), ('D&A / Revenue', 'D&A verified'), ('CapEx / Revenue', 'CapEx')]:
            row[ratio] = row[numerator] / revenue if valid(revenue) and revenue > 0 and valid(row.get(numerator)) else None
    for metric in ('EBIT margin','D&A / Revenue','CapEx / Revenue','Effective tax rate'):
        vals = [r[metric] for r in result['rows'] if valid(r.get(metric))]
        result['historical_medians'][metric] = median(vals) if vals else None
        result['sample_counts'][metric] = len(vals)
    return result


def resolve_balance(payload, ends):
    rows = balance_24b(payload, ends)
    facts = payload.get('facts', {})
    for row in rows:
        end = row['Fiscal year end']
        # Reconstruct total debt ONLY from explicitly matching noncurrent and
        # current debt components; never add total debt to its current portion.
        if row.get('Total debt') is None:
            for noncurrent_tags, current_tags in [
                (('LongTermDebtNoncurrent',), ('LongTermDebtCurrent',)),
                (('LongTermDebtAndCapitalLeaseObligations',), ('LongTermDebtAndCapitalLeaseObligationsCurrent',)),
            ]:
                noncurrent, ns = point(facts, noncurrent_tags, end)
                current, cs = point(facts, current_tags, end)
                if all(valid(v) and v >= 0 for v in (noncurrent, current)):
                    row['Total debt'] = noncurrent + current
                    row['Long-term debt'], row['Current debt'] = noncurrent, current
                    row['tags']['Total debt'] = f'derived:{ns}+{cs}'
                    row['warnings'].append('Debt reconstructed from compatible current and noncurrent components.')
                    break
            cash = row.get('Cash')
            if row.get('Total debt') is not None and valid(cash) and row.get('tags',{}).get('Cash') == 'us-gaap:CashAndCashEquivalentsAtCarryingValue':
                row['Net debt (cash-only)'] = row['Total debt'] - cash
        row['quality'] = {
            'net_debt': 'REPORTED_OR_RECONSTRUCTED' if row.get('Net debt (cash-only)') is not None else 'MISSING',
            'shares': 'DATED_DEI_SNAPSHOT' if row.get('Shares outstanding') is not None else 'MISSING',
            'working_capital': 'PARTIAL_PROXY' if row.get('Partial operating NWC') is not None else 'MISSING',
        }
    return rows


def assess_company(payload, sector_model='fcff', last_n=5):
    history = resolve_history(payload, last_n)
    rows = history.get('rows', [])
    if not rows:
        return {'status':'MISSING_DATA','latest_year':None,'missing':['Annual financial history'], 'warnings':[], 'history':history, 'balance':None}
    latest = rows[-1]
    balance = resolve_balance(payload, [latest['Fiscal year end']])[0]
    required = ('Revenue','EBIT','D&A verified','CapEx','Effective tax rate')
    missing = [k for k in required if latest.get(k) is None]
    missing += [k for k in ('Net debt (cash-only)','Shares outstanding') if balance.get(k) is None]
    if len(rows) < 3:
        missing.append('3+ fiscal periods')
    # ΔNWC is an assumption issue, not a hard blocker to an explicitly provisional scenario.
    provisional = ['Full operating NWC unverified; a scenario requires an explicit ΔNWC policy.',
                   'WACC, terminal assumptions, lease treatment and equity bridge require validation.']
    if latest.get('Delta partial NWC') is None:
        provisional.append('Even partial ΔNWC is unavailable; do not treat missing as zero without an explicit assumption.')
    if sector_model != 'fcff':
        status = 'UNSUPPORTED_SECTOR'
    elif missing:
        status = 'MISSING_DATA'
    else:
        status = 'PROVISIONAL_SCENARIO_ONLY'
    return {'status':status, 'latest_year':latest['Fiscal year end'], 'missing':missing,
            'warnings':provisional, 'history':history, 'balance':balance}
