"""Bank inputs from SEC CompanyFacts: audited annual history for the equity-based bank engine.

Banks are valued on equity, not on free cash flow to the firm, so this loader collects what an
equity model needs: net income to common shareholders, common (and tangible common) book value,
common dividends and buybacks, plus a few context lines (assets, deposits, revenue mix).

Rules shared with the FCFF loader: tags are tried in priority order and NEVER added across tags;
missing required inputs block the valuation instead of being filled with zeros.
"""
from __future__ import annotations

from intrinsic.inputs import DataUnavailable, lookup_cik
from intrinsic.sec_data import annual_flows, annual_points, companyfacts_cached, is_number, submissions_cached
from intrinsic.sector_routing import classify_sic

FLOWS = {
    'Net income': ('NetIncomeLoss', 'ProfitLoss'),
    'Net income to common': ('NetIncomeLossAvailableToCommonStockholdersBasic',
                             'NetIncomeLossAvailableToCommonStockholdersDiluted'),
    'Preferred dividends': ('PreferredStockDividendsAndOtherAdjustments', 'DividendsPreferredStock',
                            'DividendsPreferredStockCash', 'PreferredStockDividendsIncomeStatementImpact'),
    'Common dividends': ('DividendsCommonStockCash', 'DividendsCommonStock', 'PaymentsOfDividendsCommonStock'),
    'Buybacks': ('PaymentsForRepurchaseOfCommonStock',),
    'Revenue': ('Revenues', 'RevenuesNetOfInterestExpense'),
    'Net interest income': ('InterestIncomeExpenseNet', 'InterestIncomeExpenseAfterProvisionForLoanLoss'),
    'Noninterest income': ('NoninterestIncome',),
    'Noninterest expense': ('NoninterestExpense',),
    'Credit provisions': ('ProvisionForLoanLeaseAndOtherLosses', 'ProvisionForLoanAndLeaseLosses',
                          'ProvisionForCreditLosses'),
}
POINTS = {
    'Total equity': ('StockholdersEquity',),
    'Preferred equity': ('PreferredStockIncludingAdditionalPaidInCapitalNetOfDiscount',
                         'PreferredStockIncludingAdditionalPaidInCapital', 'PreferredStockValue',
                         'PreferredStockValueOutstanding', 'PreferredStockLiquidationPreferenceValue'),
    'Goodwill': ('Goodwill',),
    'Intangibles': ('IntangibleAssetsNetExcludingGoodwill',),
    'Total assets': ('Assets',),
    'Deposits': ('Deposits',),
}
PER_SHARE = {
    'Diluted EPS': ('EarningsPerShareDiluted',),
    'Dividends per share': ('CommonStockDividendsPerShareDeclared', 'CommonStockDividendsPerShareCashPaid'),
}
REQUIRED = ('Net income to common', 'Common equity')


def _val(series, end):
    x = series.get(end)
    return x['value'] if x else None


def build_history(payload, last_n=10):
    """Annual rows (oldest → newest) keyed on the fiscal year ends that carry total equity."""
    flows = {k: annual_flows(payload, tags) for k, tags in FLOWS.items()}
    points = {k: annual_points(payload, tags) for k, tags in POINTS.items()}
    per_share = {k: annual_flows(payload, tags, unit='USD/shares') for k, tags in PER_SHARE.items()}
    diluted = annual_flows(payload, ['WeightedAverageNumberOfDilutedSharesOutstanding'], unit='shares')
    # Intangibles split into finite + indefinite lives when no single net tag exists (e.g. JPMorgan).
    finite = annual_points(payload, ['FiniteLivedIntangibleAssetsNet'])
    indefinite = annual_points(payload, ['IndefiniteLivedIntangibleAssetsExcludingGoodwill'])

    ends = sorted(e for e in flows['Net income'] if e in points['Total equity'])[-last_n:]
    rows, provenance = [], {}
    for end in ends:
        r = {'Fiscal year end': end}
        for k, s in flows.items():
            r[k] = _val(s, end)
            if s.get(end):
                provenance[k] = s[end]['tag']
        for k, s in points.items():
            r[k] = _val(s, end)
            if s.get(end):
                provenance[k] = s[end]['tag']
        for k, s in per_share.items():
            r[k] = _val(s, end)
        r['Diluted shares'] = _val(diluted, end)
        if r['Intangibles'] is None and (finite.get(end) or indefinite.get(end)):
            r['Intangibles'] = (_val(finite, end) or 0.0) + (_val(indefinite, end) or 0.0)
            provenance['Intangibles'] = 'us-gaap:FiniteLivedIntangibleAssetsNet + IndefiniteLived…ExcludingGoodwill'
        if r['Net income to common'] is None and is_number(r['Net income']):
            pref = r['Preferred dividends'] if is_number(r['Preferred dividends']) else 0.0
            r['Net income to common'] = r['Net income'] - pref
            provenance.setdefault('Net income to common', 'Net income − preferred dividends')
        # Common dividends: declared per share × diluted shares when no cash total is tagged.
        if r['Common dividends'] is None and is_number(r['Dividends per share']) and is_number(r['Diluted shares']):
            r['Common dividends'] = r['Dividends per share'] * r['Diluted shares']
            provenance.setdefault('Common dividends', 'dividends declared per share × diluted shares')
        pref = r['Preferred equity'] if is_number(r['Preferred equity']) else 0.0
        r['Common equity'] = r['Total equity'] - pref if is_number(r['Total equity']) else None
        intang = (r['Goodwill'] or 0.0) + (r['Intangibles'] or 0.0)
        r['Tangible common equity'] = r['Common equity'] - intang if is_number(r['Common equity']) else None
        rows.append(r)
    # Ratios need the previous year's book value (beginning-of-year equity).
    for prev, r in zip(rows, rows[1:]):
        ce0, tce0, ni = prev['Common equity'], prev['Tangible common equity'], r['Net income to common']
        r['ROE'] = ni / ce0 if is_number(ni) and is_number(ce0) and ce0 > 0 else None
        r['ROTCE'] = ni / tce0 if is_number(ni) and is_number(tce0) and tce0 > 0 else None
        ce1 = r['Common equity']
        r['Book value growth'] = ce1 / ce0 - 1 if is_number(ce1) and is_number(ce0) and ce0 > 0 else None
    for r in rows:
        r.setdefault('ROE', None)
        r.setdefault('ROTCE', None)
        r.setdefault('Book value growth', None)
        ni = r['Net income to common']
        paid = (r['Common dividends'] or 0.0) + (r['Buybacks'] or 0.0)
        r['Total payout'] = paid if (r['Common dividends'] is not None or r['Buybacks'] is not None) else None
        r['Payout ratio'] = paid / ni if is_number(ni) and ni > 0 and r['Total payout'] is not None else None
        r['Dividend payout ratio'] = (r['Common dividends'] / ni if is_number(ni) and ni > 0
                                      and is_number(r['Common dividends']) else None)
    return rows, provenance


def latest_shares(payload):
    """(shares, date, source) from the latest 10-K cover page (dei:EntityCommonStockSharesOutstanding)."""
    pts = annual_points(payload, ['EntityCommonStockSharesOutstanding'], namespace='dei', unit='shares')
    if not pts:
        return None, None, None
    end = max(pts)
    return pts[end]['value'], end, 'SEC 10-K cover page (dei:EntityCommonStockSharesOutstanding)'


def load_bank_inputs(ticker, last_n=10):
    """Audited bank history for `ticker`. Raises DataUnavailable when required inputs are missing."""
    cik, name = lookup_cik(ticker)
    profile = submissions_cached(cik)
    decision = classify_sic(profile.get('sic'))
    if decision.model != 'bank_equity':
        raise DataUnavailable(f'{ticker} is not classified as a bank (SIC {profile.get("sic")}).')
    payload = companyfacts_cached(cik)
    rows, provenance = build_history(payload, last_n=last_n)
    blockers = []
    if len(rows) < 4:
        blockers.append(f'Only {len(rows)} annual periods with net income and equity; at least 4 are needed.')
    latest = rows[-1] if rows else {}
    for k in REQUIRED:
        if not is_number(latest.get(k)):
            blockers.append(f'Missing latest {k.lower()}.')
    if is_number(latest.get('Common equity')) and latest['Common equity'] <= 0:
        blockers.append('Common equity is not positive.')
    roes = [r['ROE'] for r in rows if is_number(r.get('ROE'))]
    if len(roes) < 3:
        blockers.append('Fewer than three years of return on equity.')
    if blockers:
        raise DataUnavailable(' '.join(blockers))
    shares, shares_date, shares_source = latest_shares(payload)
    warnings = []
    if not any(is_number(r.get('Preferred equity')) for r in rows[-1:]):
        warnings.append('No preferred stock tag found for the latest year: common equity = total equity.')
    if latest.get('Total payout') is None:
        warnings.append('No common dividends or buybacks tagged for the latest year.')
    return {'cik': cik, 'name': profile.get('name') or name, 'sic': profile.get('sic'),
            'sic_description': profile.get('sicDescription'), 'decision': vars(decision),
            'history': rows, 'provenance': provenance, 'warnings': warnings,
            'shares': shares, 'shares_date': shares_date, 'shares_source': shares_source,
            'balance_date': latest['Fiscal year end']}
