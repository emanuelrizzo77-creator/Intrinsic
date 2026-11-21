"""Insurer inputs from SEC CompanyFacts for the equity engine (the bank engine's models, insurance-specific inputs).

Insurers, like banks, are valued on equity: policyholder reserves are operating liabilities, not financing. Two
adjustments make an insurer's reported net income and book value usable for an excess-return model:

  Equity gains out of ROE       Since 2018 gains on equity securities, realised or not, run through net income
                                (ASU 2016-01), so reported ROE swings with the stock market (Berkshire 2019-2025: -5% to +23%).
                                Operating earnings = net income to common - equity-security gains x (1 - tax rate).
                                Other realised gains (bonds, derivatives) stay: for life insurers they are mostly
                                hedges offsetting liability changes that are also in net income.
  Equity portfolio at market    When the portfolio of equity securities at fair value is large (>= 10% of common
                                equity, cost basis tagged), it is taken out of the operating book and added back at
                                market value net of the deferred tax on its unrealised gain. A marked-to-market
                                portfolio is expected to earn its required return, so its excess return is zero and
                                its value is its after-tax market value; the excess-return model then values only the
                                operating businesses (underwriting, float income, and for Berkshire the railroad,
                                utilities and other companies). The portfolio's dividends are removed from operating
                                earnings too (tagged dividend income, or an assumed yield when it is not tagged).
  Book value without AOCI       Unrealised gains and losses on bonds held in other comprehensive income move book
                                value with interest rates, not with the business; operating book excludes AOCI.

Tags are tried in priority order and never added across tags; required inputs missing block the valuation.
"""
from __future__ import annotations

from statistics import mean

from intrinsic.bank_inputs import add_ratios, build_history, latest_shares
from intrinsic.inputs import DataUnavailable, lookup_cik
from intrinsic.sec_data import annual_flows, annual_points, companyfacts_cached, is_number, submissions_cached
from intrinsic.sector_routing import classify_sic

TAX_RATE = 0.21                 # US federal statutory rate on gains and dividends (assumption)
DIVIDEND_YIELD = 0.02           # equity portfolio dividend yield when dividend income is not tagged (assumption)
SEPARATE_SHARE = 0.10           # separate the equity portfolio when it is at least this share of common equity
ASU_2016_01 = '2018-12-15'      # equity-security gains run through net income for fiscal years ending after this
FLOWS = {
    # Only gains on equity securities at fair value: the ASU 2016-01 swing. Realised gains on bonds and derivatives stay
    # in earnings: for life insurers most of them are hedges that offset liability remeasurements elsewhere in net
    # income, so removing them alone would distort operating earnings (Prudential 2025: -$4.1B).
    'Investment gains': ('EquitySecuritiesFvNiGainLoss',),
    'Dividend income': ('InvestmentIncomeDividend',),
    'Premiums earned': ('PremiumsEarnedNet',),
    'Net investment income': ('NetInvestmentIncome',),
}
POINTS = {
    'Equity securities (fair value)': ('EquitySecuritiesFvNi',),
    'Equity securities (cost)': ('EquitySecuritiesFvNiCost',),
    'AOCI': ('AccumulatedOtherComprehensiveIncomeLossNetOfTax',),
}


def _v(series, end):
    x = series.get(end)
    return x['value'] if x else None


def portfolio_after_tax(fair_value, cost, tax=TAX_RATE):
    """Market value of an equity portfolio net of the deferred tax on its unrealised gain (no tax credit on a loss)."""
    return fair_value - tax * max(0.0, fair_value - cost)


def operating_history(rows, extra, separate, tax=TAX_RATE, dividend_yield=DIVIDEND_YIELD):
    """Rewrite 'Net income to common' and 'Common equity' as operating figures (see the module notes), keeping the
    reported ones as 'Reported net income to common' and 'Reported common equity'. Returns (rows, notes)."""
    notes = []
    out = []
    for i, r in enumerate(rows):
        end = r['Fiscal year end']
        x = {k: _v(s, end) for k, s in extra.items()}
        r = {**r, **x, 'Reported net income to common': r['Net income to common'],
             'Reported common equity': r['Common equity']}
        gains = x['Investment gains'] if is_number(x['Investment gains']) else 0.0
        ni = r['Net income to common']
        r['After-tax investment gains'] = gains * (1 - tax)
        aoci = x['AOCI'] if is_number(x['AOCI']) else 0.0
        book = r['Common equity'] - aoci if is_number(r['Common equity']) else None
        r['Equity portfolio (after tax)'] = None
        r['Portfolio dividends (after tax)'] = None
        if separate:
            fv, cost = x['Equity securities (fair value)'], x['Equity securities (cost)']
            pat = portfolio_after_tax(fv, cost, tax)
            r['Equity portfolio (after tax)'] = pat
            book = book - pat if book is not None else None
            prev_fv = rows[i - 1] and extra['Equity securities (fair value)'].get(rows[i - 1]['Fiscal year end']) if i else None
            avg_fv = mean([fv, prev_fv['value']]) if prev_fv else fv
            div = x['Dividend income'] if is_number(x['Dividend income']) else dividend_yield * avg_fv
            r['Portfolio dividends (after tax)'] = div * (1 - tax)
        if is_number(ni):
            r['Net income to common'] = ni - r['After-tax investment gains'] - (r['Portfolio dividends (after tax)'] or 0.0)
        r['Common equity'] = book
        intang = (r.get('Goodwill') or 0.0) + (r.get('Intangibles') or 0.0)
        r['Tangible common equity'] = book - intang if book is not None else None
        for k in ('ROE', 'ROTCE', 'Book value growth'):
            r.pop(k, None)
        out.append(r)
    add_ratios(out)
    notes.append(f'Operating earnings = net income to common − gains on equity securities × (1 − {tax:.0%})'
                 + (' − equity-portfolio dividends × (1 − tax)' if separate else '') + '.')
    notes.append('Operating book value = common equity − AOCI'
                 + (' − equity portfolio at market net of deferred tax on its unrealised gain.' if separate else '.'))
    if separate and not any(is_number(_v(extra['Dividend income'], r['Fiscal year end'])) for r in rows):
        notes.append(f'Dividend income on the equity portfolio is not tagged: assumed {dividend_yield:.0%} of its '
                     'average fair value.')
    return out, notes


def load_insurance_inputs(ticker, last_n=10, market=None):
    """Insurer history for the equity engine. `market` (price, market_cap) supplies the share count when the SEC
    cover page has no current total (several share classes, e.g. Berkshire). Raises DataUnavailable."""
    cik, name = lookup_cik(ticker)
    profile = submissions_cached(cik)
    decision = classify_sic(profile.get('sic'))
    if decision.model != 'insurance_equity':
        raise DataUnavailable(f'{ticker} is not classified as an insurer (SIC {profile.get("sic")}).')
    payload = companyfacts_cached(cik)
    rows, provenance = build_history(payload, last_n=last_n + 1)
    extra = {k: annual_flows(payload, tags) for k, tags in FLOWS.items()}
    extra.update({k: annual_points(payload, tags) for k, tags in POINTS.items()})
    for k, s in extra.items():
        if s:
            provenance[k] = s[max(s)]['tag']
    if not rows:
        raise DataUnavailable('No annual periods with net income and equity.')
    latest = rows[-1]
    fv, cost = (_v(extra['Equity securities (fair value)'], latest['Fiscal year end']),
                _v(extra['Equity securities (cost)'], latest['Fiscal year end']))
    separate = (is_number(fv) and is_number(cost) and is_number(latest.get('Common equity'))
                and fv >= SEPARATE_SHARE * latest['Common equity'])
    if separate:      # only years where the portfolio and its cost are known keep a consistent operating book, and
        # only years under ASU 2016-01 (fiscal years ending from December 2018): before it the portfolio's unrealised
        # gain sat in AOCI, so removing AOCI and the portfolio would subtract that gain twice.
        rows = [r for r in rows if r['Fiscal year end'] >= ASU_2016_01
                and is_number(_v(extra['Equity securities (fair value)'], r['Fiscal year end']))
                and is_number(_v(extra['Equity securities (cost)'], r['Fiscal year end']))]
    rows, notes = operating_history(rows, extra, separate)
    rows = rows[-last_n:]
    if rows:
        rows[-1]['Earnings basis'] = 'operating earnings (net income to common excluding equity-security gains)'
        rows[-1]['Book basis'] = ('Operating book value (common equity − AOCI − equity portfolio net of tax)'
                                  if separate else 'Operating book value (common equity − AOCI)')
    blockers = []
    if len(rows) < 4:
        blockers.append(f'Only {len(rows)} annual periods with the inputs the insurer model needs; at least 4.')
    if not is_number(rows[-1].get('Net income to common')):
        blockers.append('Missing latest net income to common.')
    if not is_number(rows[-1].get('Common equity')) or rows[-1]['Common equity'] <= 0:
        blockers.append('Operating book value is not positive.')
    if len([r for r in rows if is_number(r.get('ROE'))]) < 3:
        blockers.append('Fewer than three years of operating return on equity.')
    if not any(is_number(r.get('Investment gains')) for r in rows):
        notes.append('No equity-securities gains tagged: operating earnings equal reported net income.')
    if blockers:
        raise DataUnavailable(' '.join(blockers))
    shares, shares_date, shares_source = latest_shares(payload)
    stale = not shares_date or int(shares_date[:4]) < int(rows[-1]['Fiscal year end'][:4])
    if stale:
        price, cap = (market or {}).get('price'), (market or {}).get('market_cap')
        if is_number(price) and is_number(cap) and price > 0:
            shares, shares_date = cap / price, None
            shares_source = ('market capitalisation ÷ price (Yahoo Finance): all share classes in units of the '
                             'quoted class; the SEC cover page has no current total')
        else:
            shares, shares_date, shares_source = None, None, None
    warnings = list(notes)
    if latest.get('Total payout') is None:
        warnings.append('No common dividends or buybacks tagged for the latest year.')
    last = rows[-1]
    return {'cik': cik, 'name': profile.get('name') or name, 'sic': profile.get('sic'),
            'sic_description': profile.get('sicDescription'), 'decision': vars(decision), 'kind': 'insurer',
            'history': rows, 'provenance': provenance, 'warnings': warnings,
            'portfolio': last['Equity portfolio (after tax)'] or 0.0, 'separate_portfolio': bool(separate),
            'tax_rate': TAX_RATE, 'shares': shares, 'shares_date': shares_date, 'shares_source': shares_source,
            'balance_date': last['Fiscal year end']}
