"""Intrinsic 27 — operating invested capital from SEC CompanyFacts.

Builds, per fiscal year end:
  * Net PP&E
  * Full operating NWC = (current assets - cash - short-term investments)
                       - (current liabilities - interest-bearing current debt)
    Negative values are legitimate (e.g. retailers, platforms) and are kept.
  * Depreciation (PP&E only) and amortization of intangibles, when tagged
  * Goodwill and other intangibles (reported, not forecast)

Every value carries tag provenance. Missing components are flagged, never
silently replaced, except where a tag's absence plausibly means "none"
(short-term investments, current debt) — those are flagged as ASSUMED_ZERO.
"""
from __future__ import annotations

from sec_annual_27 import annual_flows, annual_points, is_number

PPE_TAGS = (
    'PropertyPlantAndEquipmentNet',
    'PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization',
)
CURRENT_ASSETS = ('AssetsCurrent',)
CURRENT_LIABILITIES = ('LiabilitiesCurrent',)
CASH = ('CashAndCashEquivalentsAtCarryingValue',
        'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents', 'Cash')
SHORT_TERM_INVESTMENTS = ('ShortTermInvestments', 'MarketableSecuritiesCurrent',
                          'AvailableForSaleSecuritiesDebtSecuritiesCurrent')
DEBT_CURRENT_TOTAL = ('DebtCurrent',)
LTD_CURRENT = ('LongTermDebtCurrent', 'LongTermDebtAndCapitalLeaseObligationsCurrent')
SHORT_BORROWINGS = ('ShortTermBorrowings', 'CommercialPaper')
GOODWILL = ('Goodwill',)
INTANGIBLES = ('IntangibleAssetsNetExcludingGoodwill', 'FiniteLivedIntangibleAssetsNet')
DEPRECIATION = ('Depreciation',)
AMORTIZATION = ('AmortizationOfIntangibleAssets',)


def build_capital_history(payload, fiscal_ends, *, vintage='latest', as_of=None):
    kw = {'vintage': vintage, 'as_of': as_of}
    pts = {name: annual_points(payload, tags, **kw) for name, tags in {
        'ppe': PPE_TAGS, 'ca': CURRENT_ASSETS, 'cl': CURRENT_LIABILITIES, 'cash': CASH,
        'sti': SHORT_TERM_INVESTMENTS, 'debt_total': DEBT_CURRENT_TOTAL, 'ltd': LTD_CURRENT,
        'stb': SHORT_BORROWINGS, 'gw': GOODWILL, 'intang': INTANGIBLES}.items()}
    flows = {'dep': annual_flows(payload, DEPRECIATION, **kw),
             'amort': annual_flows(payload, AMORTIZATION, **kw)}
    rows = []
    for end in fiscal_ends:
        row = {'Fiscal year end': end, 'tags': {}, 'flags': []}

        def val(store, name, label):
            fact = store[name].get(end)
            if fact:
                row['tags'][label] = fact['tag']
                return fact['value']
            return None

        ppe = val(pts, 'ppe', 'Net PP&E')
        ca, cl = val(pts, 'ca', 'Current assets'), val(pts, 'cl', 'Current liabilities')
        cash = val(pts, 'cash', 'Cash')
        sti = val(pts, 'sti', 'Short-term investments')
        debt_total = val(pts, 'debt_total', 'Current debt')
        ltd, stb = val(pts, 'ltd', 'Current LTD'), val(pts, 'stb', 'Short-term borrowings')
        row['Goodwill'] = val(pts, 'gw', 'Goodwill')
        row['Intangibles'] = val(pts, 'intang', 'Intangibles')
        row['Depreciation'] = val(flows, 'dep', 'Depreciation')
        row['Amortization'] = val(flows, 'amort', 'Amortization')
        row['Net PP&E'] = ppe
        if ppe is None:
            row['flags'].append('MISSING: Net PP&E')

        if sti is None:
            sti = 0.0
            row['flags'].append('ASSUMED_ZERO: short-term investments tag absent')
        if debt_total is not None:
            current_debt = debt_total
        elif ltd is not None or stb is not None:
            # LTD current and short-term borrowings are distinct balance-sheet lines.
            current_debt = (ltd or 0.0) + (stb or 0.0)
            row['tags']['Current debt'] = 'derived:current_LTD+short_term_borrowings'
        else:
            current_debt = 0.0
            row['flags'].append('ASSUMED_ZERO: no current debt tags')
        row['Short-term investments'] = sti
        row['Current debt'] = current_debt
        row['Cash'] = cash

        if all(is_number(x) for x in (ca, cl, cash)):
            row['Operating NWC'] = (ca - cash - sti) - (cl - current_debt)
            if row['tags'].get('Cash', '').endswith('RestrictedCashEquivalents'):
                row['flags'].append('Cash includes restricted cash; operating NWC slightly understated')
        else:
            row['Operating NWC'] = None
            row['flags'].append('MISSING: current assets/liabilities or cash; operating NWC unavailable')
        if is_number(ppe) and is_number(row['Operating NWC']):
            row['Operating invested capital'] = ppe + row['Operating NWC']
        else:
            row['Operating invested capital'] = None
        rows.append(row)
    return rows
