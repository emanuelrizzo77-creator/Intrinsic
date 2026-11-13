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

from intrinsic.sec_data import annual_flows, annual_points, is_number

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
FIN_LEASE_ROU_ADDITIONS = ('RightOfUseAssetObtainedInExchangeForFinanceLeaseLiability',)
FIN_LEASE_LIABILITY = ('FinanceLeaseLiability',)
FIN_LEASE_PARTS = (('FinanceLeaseLiabilityCurrent',), ('FinanceLeaseLiabilityNoncurrent',))
AMORTIZATION = ('AmortizationOfIntangibleAssets',)


def build_capital_history(payload, fiscal_ends, *, vintage='latest', as_of=None, rd_life=None):
    kw = {'vintage': vintage, 'as_of': as_of}
    rd_all = rd_series(payload, **kw) if rd_life else []
    rd_by_end = dict(rd_all)
    pts = {name: annual_points(payload, tags, **kw) for name, tags in {
        'ppe': PPE_TAGS, 'ca': CURRENT_ASSETS, 'cl': CURRENT_LIABILITIES, 'cash': CASH,
        'sti': SHORT_TERM_INVESTMENTS, 'cash_sti': CASH_AND_STI_TOTAL, 'mkt_cur': MARKETABLE_CURRENT,
        'eqm': NONOPERATING_LONG_TERM['Equity-method investments'],
        'ltm': NONOPERATING_LONG_TERM['Long-term marketable securities'],
        **{f'mt{i}': (tot, ) for i, (tot, _) in enumerate(MARKETABLE_TOTAL)},
        **{f'mn{i}': (nc, ) for i, (_, nc) in enumerate(MARKETABLE_TOTAL)},
        'debt_total': DEBT_CURRENT_TOTAL, 'fll': FIN_LEASE_LIABILITY,
        'fllc': FIN_LEASE_PARTS[0], 'flln': FIN_LEASE_PARTS[1], 'ltd': LTD_CURRENT,
        'stb': SHORT_BORROWINGS, 'gw': GOODWILL, 'intang': INTANGIBLES}.items()}
    flows = {'dep': annual_flows(payload, DEPRECIATION, **kw),
             'amort': annual_flows(payload, AMORTIZATION, **kw),
             'finrou': annual_flows(payload, FIN_LEASE_ROU_ADDITIONS, **kw)}
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
        row['Finance-lease ROU additions'] = val(flows, 'finrou', 'Finance-lease ROU additions')
        fll = val(pts, 'fll', 'Finance lease liabilities')
        if fll is None:
            c_, n_ = val(pts, 'fllc', 'Finance lease (current)'), val(pts, 'flln', 'Finance lease (noncurrent)')
            fll = (c_ or 0.0) + (n_ or 0.0) if (c_ is not None or n_ is not None) else None
        row['Finance lease liabilities'] = fll
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
        row['R&D'] = rd_by_end.get(end)
        ra = research_asset(rd_all, end, rd_life) if rd_life else None
        row['Research asset'] = ra['research_asset'] if ra else None
        row['R&D amortization'] = ra['rd_amortization'] if ra else None
        row['R&D history'] = ra['rd_history'] if ra else None
        if is_number(ppe) and is_number(row['Operating NWC']):
            row['Operating invested capital'] = ppe + row['Operating NWC']
        else:
            row['Operating invested capital'] = None
        rows.append(row)
    return rows


# ------------------------------------------------------------------
# R&D capitalisation (Damodaran): R&D is an investment, amortised straight-line
# ------------------------------------------------------------------
RD_TAGS = ('ResearchAndDevelopmentExpense', 'ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost')


def rd_life_for_sic(sic):
    """Amortisable life of R&D by industry (assumption, editable via override)."""
    try:
        n = int(sic)
    except (TypeError, ValueError):
        return 5, 'default'
    if 2833 <= n <= 2836:
        return 10, 'pharma/biotech'
    if 7370 <= n <= 7379:
        return 3, 'software/services'
    if 3570 <= n <= 3579 or 3660 <= n <= 3679:
        return 5, 'computers/semiconductors/electronics'
    return 5, 'default'


def rd_series(payload, *, vintage='latest', as_of=None):
    """[(fiscal_end, R&D)] sorted, ~12-month annual values."""
    flows = annual_flows(payload, RD_TAGS, vintage=vintage, as_of=as_of)
    return [(end, flows[end]['value']) for end in sorted(flows)]


def research_asset(series, end, life):
    """Unamortised research asset and current-year amortisation at fiscal end.

    asset_t = sum_{j=0}^{L-1} RD_{t-j} * (1 - j/L);  amort_t = sum_{j=1}^{L} RD_{t-j} / L
    Requires L+1 consecutive annual observations ending at `end`, else None.
    """
    from intrinsic.sec_data import consecutive
    ends = [e for e, _ in series]
    if end not in ends:
        return None
    i = ends.index(end)
    if i < life:
        return None
    window = series[i - life:i + 1]
    if any(not consecutive(a[0], b[0]) for a, b in zip(window, window[1:])):
        return None
    rd = [v for _, v in reversed(window)]          # rd[0] = current year
    return {'research_asset': sum(rd[j] * (1 - j / life) for j in range(life)),
            'rd_amortization': sum(rd[j] / life for j in range(1, life + 1)),
            'rd_history': list(reversed(rd[:life])), 'rd': rd[0]}   # oldest -> newest, last L years
