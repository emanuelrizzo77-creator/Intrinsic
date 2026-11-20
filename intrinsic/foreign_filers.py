"""Foreign private issuers (Form 20-F / 40-F): adapt their SEC facts to what the engine reads.

The valuation engine reads US GAAP facts in USD from Form 10-K. A foreign filer differs in up to three
ways, and this adapter removes each one at load time, so every downstream module stays unchanged:

1. Form      20-F / 40-F (and amendments) are the annual reports: relabelled 10-K / 10-K/A, original kept.
2. Standard  IFRS filers tag `ifrs-full` concepts: each concept the engine needs is copied to its US GAAP
             name (IFRS_TO_US_GAAP). Under IFRS 16 every lease is on the balance sheet and operating profit
             is before lease interest, so lease liabilities are mapped to finance-lease debt (consistent).
3. Currency  Amounts in the reporting currency are converted to USD with Yahoo Finance daily rates:
             flows (income statement, cash flow) at the AVERAGE rate of their fiscal period, balances at the
             CLOSING rate of their date. Values that cannot be converted are dropped, never left unconverted.
             Convenience translations already tagged in USD are discarded so currencies are never mixed.

Hyperinflationary currencies (IAS 29 restates history to current purchasing power) are refused: translating
restated figures with market exchange rates would not give a meaningful history.

US filers (any Form 10-K) are returned untouched.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache

ANNUAL_FOREIGN = {'20-F': '10-K', '20-F/A': '10-K/A', '40-F': '10-K', '40-F/A': '10-K/A'}
DOMESTIC_ANNUAL = {'10-K', '10-K/A', '10-KT'}
HYPERINFLATIONARY = {'ARS', 'VES', 'VEF', 'TRY', 'LBP', 'ZWL', 'ZWG', 'SSP', 'SDG', 'IRR', 'SYP', 'HTG', 'ETB'}
FX_HISTORY_START = '2008-01-01'

# US GAAP tag the engine reads  <-  IFRS concepts, in priority order.
IFRS_TO_US_GAAP = {
    'Revenues': ('Revenue', 'RevenueFromContractsWithCustomers'),
    'OperatingIncomeLoss': ('ProfitLossFromOperatingActivities',),
    'IncomeLossFromContinuingOperationsBeforeIncomeTaxes': ('ProfitLossBeforeTax',),
    'IncomeTaxExpenseBenefit': ('IncomeTaxExpenseContinuingOperations',),
    'NetIncomeLoss': ('ProfitLossAttributableToOwnersOfParent', 'ProfitLoss'),
    'Depreciation': ('DepreciationPropertyPlantAndEquipment',),
    'AmortizationOfIntangibleAssets': ('AmortisationIntangibleAssetsOtherThanGoodwill',),
    'DepreciationDepletionAndAmortization': ('DepreciationAndAmortisationExpense',),
    'PaymentsToAcquirePropertyPlantAndEquipment': ('PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',
                                                   'PurchaseOfPropertyPlantAndEquipment'),
    'NetCashProvidedByUsedInOperatingActivities': ('CashFlowsFromUsedInOperatingActivities',),
    'ResearchAndDevelopmentExpense': ('ResearchAndDevelopmentExpense',),
    'InterestExpense': ('InterestExpense', 'FinanceCosts'),
    'InvestmentIncomeInterest': ('InterestRevenueCalculatedUsingEffectiveInterestMethod',),
    'PropertyPlantAndEquipmentNet': ('PropertyPlantAndEquipment',),
    'AssetsCurrent': ('CurrentAssets',),
    'LiabilitiesCurrent': ('CurrentLiabilities',),
    'CashAndCashEquivalentsAtCarryingValue': ('CashAndCashEquivalents',),
    'ShortTermInvestments': ('CurrentInvestments', 'ShorttermInvestments'),
    'AccountsReceivableNetCurrent': ('CurrentTradeReceivables', 'TradeAndOtherCurrentReceivables'),
    'InventoryNet': ('Inventories',),
    'AccountsPayableCurrent': ('CurrentTradePayables', 'TradeAndOtherCurrentPayablesToTradeSuppliers'),
    'AccountsPayableAndAccruedLiabilitiesCurrent': ('TradeAndOtherCurrentPayables',),
    'Goodwill': ('Goodwill',),
    'IntangibleAssetsNetExcludingGoodwill': ('IntangibleAssetsOtherThanGoodwill',),
    'EquityMethodInvestments': ('InvestmentsAccountedForUsingEquityMethod',),
    'LongTermDebtNoncurrent': ('NoncurrentPortionOfNoncurrentBorrowings', 'LongtermBorrowings'),
    'DebtCurrent': ('CurrentBorrowingsAndCurrentPortionOfNoncurrentBorrowings', 'ShorttermBorrowings'),
    'LongTermDebt': ('Borrowings',),
    'FinanceLeaseLiability': ('LeaseLiabilities',),
    'FinanceLeaseLiabilityCurrent': ('CurrentLeaseLiabilities',),
    'FinanceLeaseLiabilityNoncurrent': ('NoncurrentLeaseLiabilities',),
    'WeightedAverageNumberOfDilutedSharesOutstanding': ('AdjustedWeightedAverageShares',),
    'StockholdersEquity': ('EquityAttributableToOwnersOfParent',),
}

_CURRENCY = re.compile(r'^[A-Z]{3}$')
_PER_SHARE = re.compile(r'^([A-Z]{3})/shares$')


class ForeignFilerUnsupported(ValueError):
    """A foreign filer the adapter cannot translate faithfully (refusal by design)."""


def _forms(facts):
    return {r.get('form') for ns in facts.values() for f in ns.values()
            for recs in f.get('units', {}).values() for r in recs}


def is_foreign_filer(payload):
    forms = _forms((payload or {}).get('facts', {}))
    return bool(forms & set(ANNUAL_FOREIGN)) and not forms & DOMESTIC_ANNUAL


def reporting_standard(facts):
    def count(ns):
        return sum(1 for f in facts.get(ns, {}).values() for recs in f.get('units', {}).values() for r in recs
                   if r.get('form') in ANNUAL_FOREIGN)
    return 'ifrs-full' if count('ifrs-full') > count('us-gaap') else 'us-gaap'


def reporting_currency(facts, standard):
    """Most frequent ISO currency unit among annual-report facts of the reporting standard."""
    counts = {}
    for f in facts.get(standard, {}).values():
        for unit, recs in f.get('units', {}).items():
            if _CURRENCY.match(unit):
                n = sum(1 for r in recs if r.get('form') in ANNUAL_FOREIGN)
                counts[unit] = counts.get(unit, 0) + n
    return max(counts, key=counts.get) if counts else 'USD'


@lru_cache(maxsize=32)
def _fx_series(currency):
    """Daily USD per unit of `currency` (pandas Series indexed by date) from Yahoo Finance."""
    import yfinance as yf
    hist = yf.Ticker(f'{currency}USD=X').history(start=FX_HISTORY_START, interval='1d')['Close'].dropna()
    if hist.empty:
        raise ForeignFilerUnsupported(f'No {currency}/USD exchange-rate history available to convert to USD.')
    hist.index = hist.index.tz_localize(None).normalize()
    return hist


class FxConverter:
    """USD per unit of a currency: average over a period (flows) or the close on a date (balances)."""

    def __init__(self, currency, series=None):
        self.currency = currency
        self.series = series if series is not None else _fx_series(currency)

    def average(self, start, end):
        window = self.series.loc[str(start):str(end)]
        return float(window.mean()) if len(window) >= 20 else None

    def at(self, day):
        window = self.series.loc[:str(day)]
        if not len(window):
            return None
        last = window.index[-1]
        import pandas as pd
        return float(window.iloc[-1]) if (pd.Timestamp(day) - last).days <= 7 else None


def _convert(recs, fx):
    out = []
    for r in recs:
        val = r.get('val')
        if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val):
            continue
        rate = fx.average(r['start'], r['end']) if r.get('start') else fx.at(r['end'])
        if rate is None:
            continue
        out.append({**r, 'val': val * rate})
    return out


def _relabel(recs):
    return [{**r, 'form': ANNUAL_FOREIGN.get(r.get('form'), r.get('form')), 'original_form': r.get('form')}
            for r in recs]


def normalize_payload(payload, fx=None):
    """(payload, meta). Foreign filers come back as US GAAP / USD / 10-K facts; US filers unchanged (meta None)."""
    if not is_foreign_filer(payload):
        return payload, None
    facts = payload.get('facts', {})
    standard = reporting_standard(facts)
    currency = reporting_currency(facts, standard)
    if currency in HYPERINFLATIONARY:
        raise ForeignFilerUnsupported(
            f"{payload.get('entityName', 'This company')} reports in {currency}, a hyperinflationary currency: its "
            'history is restated to current purchasing power (IAS 29), so it cannot be translated into a meaningful '
            'USD history.')
    if currency != 'USD' and fx is None:
        fx = FxConverter(currency)
    source = facts.get(standard, {})
    if standard == 'ifrs-full':
        concepts = {}
        for us_tag, ifrs_tags in IFRS_TO_US_GAAP.items():
            # Filers switch concepts over the years (e.g. Revenue -> RevenueFromContractsWithCustomers): a lower-
            # priority concept only fills periods the higher-priority ones do not cover, so definitions never mix.
            units, covered = {}, set()
            for ifrs_tag in ifrs_tags:
                for unit, recs in source.get(ifrs_tag, {}).get('units', {}).items():
                    new = [r for r in recs if (unit, r.get('start'), r.get('end')) not in covered]
                    units.setdefault(unit, []).extend(new)
                covered |= {(u, r.get('start'), r.get('end')) for u, rs in units.items() for r in rs}
            if any(units.values()):
                concepts[us_tag] = {'units': units}
    else:
        concepts = source
    mapped = {}
    for tag, fact in concepts.items():
        units = {}
        for unit, recs in fact.get('units', {}).items():
            per_share = _PER_SHARE.match(unit)
            if unit == currency or (per_share and per_share.group(1) == currency):
                target = 'USD' if unit == currency else 'USD/shares'
                recs = recs if currency == 'USD' else _convert(recs, fx)
                units[target] = _relabel(recs)
            elif _CURRENCY.match(unit) or per_share:
                continue                    # convenience translations / other currencies: never mixed in
            else:
                units[unit] = _relabel(recs)    # shares, pure ratios
        if units:
            mapped[tag] = {**{k: v for k, v in fact.items() if k != 'units'}, 'units': units}
    dei = {tag: {**f, 'units': {u: _relabel(r) for u, r in f.get('units', {}).items()}}
           for tag, f in facts.get('dei', {}).items()}
    forms = sorted(_forms(facts) & set(ANNUAL_FOREIGN))
    meta = {'standard': 'IFRS' if standard == 'ifrs-full' else 'US GAAP', 'currency': currency, 'forms': forms,
            'note': (f"Foreign private issuer ({', '.join(forms)}), {'IFRS' if standard == 'ifrs-full' else 'US GAAP'}"
                     + (f', reported in {currency}: converted to USD at Yahoo Finance rates (flows at the fiscal-year '
                        'average, balances at the closing rate)' if currency != 'USD' else ', reported in USD')
                     + ('; IFRS concepts mapped to their US GAAP equivalents, lease liabilities (IFRS 16) treated as '
                        'debt' if standard == 'ifrs-full' else '') + '.')}
    return {**payload, 'facts': {'us-gaap': mapped, 'dei': dei}}, meta


def annual_payload(cik):
    """Cached CompanyFacts for `cik`, normalized for foreign filers. Returns (payload, meta)."""
    from intrinsic.sec_data import companyfacts_cached
    return normalize_payload(companyfacts_cached(cik))


def ads_ratio(sec_shares, market_shares, tolerance=0.05):
    """Ordinary shares per traded ADS, inferred from the two share counts; None when they do not reconcile.

    The SEC reports ordinary shares; Yahoo Finance quotes the price per ADS and counts ADS-equivalents. A ratio
    within `tolerance` of a whole number n (or of 1/n) is taken as the ADS ratio; anything else is left to the caller.
    """
    if not (isinstance(sec_shares, (int, float)) and isinstance(market_shares, (int, float))
            and sec_shares > 0 and market_shares > 0):
        return None
    r = sec_shares / market_shares
    for n in range(1, 101):
        for cand in ((n,) if n == 1 else (n, 1 / n)):
            if abs(r / cand - 1) <= tolerance:
                return cand
    return None
