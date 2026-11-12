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
CASH_AND_STI_TOTAL = ('CashCashEquivalentsAndShortTermInvestments',)
SHORT_TERM_INVESTMENTS = ('ShortTermInvestments', 'OtherShortTermInvestments')
MARKETABLE_CURRENT = ('MarketableSecuritiesCurrent', 'AvailableForSaleSecuritiesDebtSecuritiesCurrent')
# Totals that are current ONLY when the company reports no noncurrent counterpart.
MARKETABLE_TOTAL = (('MarketableSecurities', 'MarketableSecuritiesNoncurrent'),
                    ('AvailableForSaleSecuritiesDebtSecurities', 'AvailableForSaleSecuritiesDebtSecuritiesNoncurrent'))
NONOPERATING_LONG_TERM = {
    'Equity-method investments': ('EquityMethodInvestments',),
    'Long-term marketable securities': ('MarketableSecuritiesNoncurrent',
                                        'AvailableForSaleSecuritiesDebtSecuritiesNoncurrent', 'LongTermInvestments'),
}
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
        'sti': SHORT_TERM_INVESTMENTS, 'cash_sti': CASH_AND_STI_TOTAL, 'mkt_cur': MARKETABLE_CURRENT,
        'eqm': NONOPERATING_LONG_TERM['Equity-method investments'],
        'ltm': NONOPERATING_LONG_TERM['Long-term marketable securities'],
        **{f'mt{i}': (tot, ) for i, (tot, _) in enumerate(MARKETABLE_TOTAL)},
        **{f'mn{i}': (nc, ) for i, (_, nc) in enumerate(MARKETABLE_TOTAL)},
        'debt_total': DEBT_CURRENT_TOTAL, 'ltd': LTD_CURRENT,
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

        # Short-term investments: prefer the balance-sheet subtotal (cash + STI) minus cash.
        cash_sti = val(pts, 'cash_sti', 'Cash + short-term investments')
        separate_marketable = False
        if is_number(cash_sti) and is_number(cash) and cash_sti >= cash:
            sti = cash_sti - cash
            row['tags']['Short-term investments'] = 'derived:CashCashEquivalentsAndShortTermInvestments-cash'
            separate_marketable = True      # the subtotal excludes any separate marketable line
        # Marketable securities are a separate line only when no STI line was found,
        # or when STI came from the cash subtotal (e.g. Coca-Cola). Never both otherwise.
        if sti is None or separate_marketable:
            mkt = val(pts, 'mkt_cur', 'Marketable securities (current)')
            if mkt is None:
                # When STI came from the cash subtotal, AFS debt securities usually ARE
                # those short-term investments: only a distinct 'MarketableSecurities'
                # line may be added. AFS totals are used only when no STI line exists.
                candidates = range(1) if separate_marketable else range(len(MARKETABLE_TOTAL))
                for i in candidates:
                    total = val(pts, f'mt{i}', f'Marketable total {i}')
                    if total is not None and pts[f'mn{i}'].get(end) is None:
                        mkt = total
                        row['flags'].append(f'VERIFY: {MARKETABLE_TOTAL[i][0]} total treated as current '
                                            '(no noncurrent counterpart reported)')
                        break
            if mkt is not None:
                sti = (sti or 0.0) + mkt
        if sti is None:
            sti = 0.0
            row['flags'].append('ASSUMED_ZERO: short-term investments / marketable securities tags absent')
        if is_number(ca) and is_number(cash) and sti > ca - cash:
            row['flags'].append('INCONSISTENT: short-term investments exceed current assets less cash; capped')
            sti = max(0.0, ca - cash)
        eqm, ltm = val(pts, 'eqm', 'Equity-method investments'), val(pts, 'ltm', 'Long-term marketable securities')
        row['Equity-method investments'] = eqm
        row['Long-term marketable securities'] = ltm
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
