"""Historical backtest of the Final verdict: did past signals predict the returns that followed?

  python validation/verdict_backtest.py run        # build point-in-time valuations (downloads, cached; ~1 h first time)
  python validation/verdict_backtest.py analyse    # tables from validation/results/verdict_backtest_rows.csv

For every held-out company (CIK % 5 == 0, the companies the calibration's test split never estimated on) and every
original 10-K for a fiscal year ending mid-2012 to 2020, the app's valuation is rebuilt AS OF THE FILING DATE:

  statements     SEC CompanyFacts keeping only facts filed on or before that date (sec_data.payload_as_of)
  price          Yahoo close two trading days after filing, multiplied back by every later stock split so it is
                 the price per share that existed then (the SEC share count is the one of that date)
  risk-free      10-year Treasury (^TNX) on the price date
  ERP            Damodaran implied ERP published at the start of that year (data/damodaran_implied_erp_history.json)
  beta, spreads  today's Damodaran industry betas and rating spreads (look-ahead, documented)
  WACC           same construction as the dashboard default (industry beta, synthetic rating, 25% tax, market weights)
  verdict        base / conservative / optimistic DCF and the Monte Carlo verdict (200 draws), the revenue/margin
                 error pool re-estimated on TRAIN companies only

Outcomes: total return (dividends reinvested, Yahoo adjusted close) over 1, 3 and 5 years minus SPY's over the same
dates. The analysis ranks signals against those excess returns, with confidence intervals from resampling companies.

Known biases (reported in the output, not corrected):
  * survivorship: data/sec_companies.csv lists companies that trade today, and Yahoo has no prices for delisted
    tickers, so companies that failed or were acquired are missing; the panel is tilted toward survivors;
  * look-ahead: industry betas, rating spreads, industry margins and the 25% long-run tax rate are 2026 values; the
    fade speeds use the full panel (test companies included, about 20% of observations);
  * terminal growth is the app's 2.5% even when the risk-free rate was lower (2012-2020), as the app would have done.
"""
from __future__ import annotations

import csv
import json
import math
import os
import random
import sys
import time
import warnings
from datetime import date, timedelta

warnings.filterwarnings('ignore')
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

RESULTS = os.path.join(_ROOT, 'validation', 'results')
ROWS_CSV = os.path.join(RESULTS, 'verdict_backtest_rows.csv')
SUMMARY = os.path.join(RESULTS, 'verdict_backtest.json')
PRICE_CACHE = os.path.join(_ROOT, '.intrinsic_cache', 'prices')
ERP_FILE = os.path.join(_ROOT, 'data', 'damodaran_implied_erp_history.json')
FIRST_END, LAST_END = date(2012, 6, 30), date(2020, 12, 31)
HORIZONS_Y = (1, 3, 5)
G = 0.025
N_DRAWS = 200
INTEREST_TAGS = ('InterestExpense', 'InterestExpenseNonoperating', 'InterestExpenseDebt')
FIELDS = ['cik', 'ticker', 'fy_end', 'filed', 'price_date', 'status', 'detail', 'price', 'shares', 'market_equity',
          'rf', 'erp', 'beta', 'wacc', 'value_cons', 'value_base', 'value_opt', 'value_to_price', 'p_above',
          'p_buy', 'p_hold', 'p_sell', 'verdict', 'verdict_scenarios', 'distress_share', 'data_status',
          'ret_1y', 'ret_3y', 'ret_5y', 'spy_1y', 'spy_3y', 'spy_5y', 'xs_1y', 'xs_3y', 'xs_5y']


# ------------------------------------------------------------------ pure helpers (unit-tested)

def split_factor_after(splits, day):
    """Product of stock-split ratios strictly after `day`: multiplies a split-adjusted price back to that date's."""
    f = 1.0
    for d, ratio in splits:
        if d > day and ratio and ratio > 0:
            f *= ratio
    return f


def on_or_after(series, day):
    """(date, value) of the first observation on or after `day` in a date-sorted [(date, value)], or None."""
    lo, hi = 0, len(series)
    while lo < hi:
        mid = (lo + hi) // 2
        if series[mid][0] < day:
            lo = mid + 1
        else:
            hi = mid
    return series[lo] if lo < len(series) else None


def total_return(adj, start, years, max_gap_days=10):
    """Adjusted-close return from the first close on/after `start` to the first on/after start + years.
    None when either end is missing or the series stops (delisting) before the end date."""
    a = on_or_after(adj, start)
    target = start + timedelta(days=round(365.25 * years))
    b = on_or_after(adj, target)
    if not a or not b or (b[0] - target).days > max_gap_days or (a[0] - start).days > max_gap_days:
        return None
    return b[1] / a[1] - 1


def spearman(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None

    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks([p[0] for p in pairs]), ranks([p[1] for p in pairs])
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def bootstrap_by_company(rows, stat, reps=1000, seed=7):
    """(low, high) 95% interval of stat(rows) resampling COMPANIES with replacement (rows of one company stay
    together, since a company's yearly observations are not independent)."""
    by = {}
    for r in rows:
        by.setdefault(r['cik'], []).append(r)
    keys = list(by)
    if len(keys) < 5:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        sample = [r for k in (rng.choice(keys) for _ in keys) for r in by[k]]
        v = stat(sample)
        if v is not None:
            vals.append(v)
    if len(vals) < reps * 0.5:
        return None
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]


def quantile_buckets(rows, key, n=5):
    """Split rows with a numeric `key` into n equal-count buckets, lowest first."""
    s = sorted((r for r in rows if r.get(key) is not None), key=lambda r: r[key])
    return [s[len(s) * i // n:len(s) * (i + 1) // n] for i in range(n)]


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def median_(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


# ------------------------------------------------------------------ data

def erp_for(day, table):
    """ERP published at the start of day's year: the row for the previous year."""
    row = table['by_year'].get(str(day.year - 1))
    return row['implied_erp'] if row else None


def yahoo_history(ticker):
    """{'adj': [(date, adj close)], 'close': [(date, split-adjusted close)], 'splits': [(date, ratio)]}, cached."""
    os.makedirs(PRICE_CACHE, exist_ok=True)
    path = os.path.join(PRICE_CACHE, f'{ticker}.json')
    if os.path.exists(path):
        with open(path) as fh:
            raw = json.load(fh)
    else:
        import yfinance as yf
        raw = {'adj': [], 'close': [], 'splits': []}
        try:
            df = yf.Ticker(ticker).history(period='max', auto_adjust=False, actions=True)
            for ts, row in df.iterrows():
                d = ts.date().isoformat()
                if row.get('Adj Close') == row.get('Adj Close') and row.get('Close') == row.get('Close'):
                    raw['adj'].append([d, float(row['Adj Close'])])
                    raw['close'].append([d, float(row['Close'])])
                if row.get('Stock Splits'):
                    raw['splits'].append([d, float(row['Stock Splits'])])
        except Exception as exc:                        # delisted / unknown ticker: recorded as missing
            raw['error'] = str(exc)[:200]
        with open(path, 'w') as fh:
            json.dump(raw, fh)
        time.sleep(0.3)
    conv = lambda xs: [(date.fromisoformat(d), v) for d, v in xs]
    return {'adj': conv(raw['adj']), 'close': conv(raw['close']), 'splits': conv(raw['splits'])}


def original_10k_filings(payload):
    """{fiscal year end: first 10-K filing date}, read from every one-year USD fact in the filer's 10-Ks.

    A fact counts for year E only if its 10-K was filed within 200 days of E (the original report, not the
    prior-year comparative repeated in a later 10-K)."""
    out = {}
    for concept in payload.get('facts', {}).get('us-gaap', {}).values():
        for r in concept.get('units', {}).get('USD', []):
            if r.get('form') != '10-K' or r.get('fp') != 'FY' or not r.get('start') or not r.get('filed'):
                continue
            s, e = date.fromisoformat(r['start']), date.fromisoformat(r['end'])
            if not 330 <= (e - s).days <= 400:
                continue
            f = date.fromisoformat(r['filed'])
            if f < e or (f - e).days > 200:
                continue
            out[e] = min(out.get(e, f), f)
    return out


def quality_issue(row):
    """Reason an otherwise valued origin is excluded from the statistics as a likely data error, or None.

    Penny prices and value/price beyond 10x almost always come from a share count reported in thousands, a
    reused ticker or an unadjusted reverse split, not from the model."""
    if row.get('price') is not None and row['price'] < 1.0:
        return 'price below $1'
    vp = row.get('value_to_price')
    if vp is not None and abs(vp) > 10:
        return '|value / price| above 10'
    return None


def log_excess(r, m):
    """ln((1 + stock) / (1 + SPY)): additive over time and far less skewed than the arithmetic difference."""
    if r is None or m is None or r <= -1 or m <= -1:
        return None
    return math.log((1 + r) / (1 + m))


def train_error_pool():
    """Joint error groups as in data/joint_errors.json, but only from TRAIN companies (CIK % 5 != 0)."""
    from validation import joint_errors as je
    with open(os.path.join(_ROOT, 'data', 'calibration.json')) as fh:
        cal = json.load(fh)
    vecs = [v for v in je.vectors(cal) if v['cik'] % 5]
    groups = {}
    for g, lo, hi in je.GROUPS + (('high_growth', None, None),):
        groups[g] = {'kind': 'scaled' if je.KIND[g] == 'z' else 'raw', 'min_revenue': lo, 'max_revenue': hi,
                     'vectors': [v[je.KIND[g]] for v in vecs if v['group'] == g]}
    return {'groups': groups}


def universe():
    from validation.calibrate_fade import EXCHANGES, SERIES_DIR, company_series
    from intrinsic.sector_routing import classify_sic
    with open(os.path.join(_ROOT, 'data', 'sec_companies.csv')) as fh:
        listed = {int(r['cik']): r['ticker'] for r in csv.DictReader(fh) if r.get('exchange') in EXCHANGES}
    ciks = sorted({int(f[:-5]) for f in os.listdir(SERIES_DIR)} & set(listed))
    out = []
    for cik in ciks:
        if cik % 5:
            continue
        s = company_series(cik)
        if classify_sic(s.get('sic')).model == 'fcff':
            out.append((cik, listed[cik].replace('.', '-'), s.get('sic')))
    return out


# ------------------------------------------------------------------ one origin

def value_origin(cik, ticker, sic, payload, fy_end, filed, prices, tnx, erp_table, spy, errors, cal):
    from intrinsic import forecast as dm, value_simulation as vs, verdict as vd
    from intrinsic.industry_beta import bottom_up_beta
    from intrinsic.inputs import DataUnavailable, inputs_from_payload
    from intrinsic.sec_data import annual_flows, payload_as_of
    from intrinsic.wacc_calculator import calculate_wacc
    from intrinsic.wacc_inputs import MARGINAL_TAX, cost_of_debt
    from intrinsic.wacc_data import wacc_debt
    row = {'cik': cik, 'ticker': ticker, 'fy_end': fy_end.isoformat(), 'filed': filed.isoformat()}
    start = filed + timedelta(days=2)
    px = on_or_after(prices['close'], start)
    if not px or (px[0] - start).days > 10:
        return {**row, 'status': 'NO_PRICE', 'detail': 'no Yahoo price near the filing date'}
    pdate = px[0]
    row['price_date'] = pdate.isoformat()
    price = px[1] * split_factor_after(prices['splits'], pdate)
    pit = payload_as_of(payload, filed)
    try:
        data = inputs_from_payload(pit, cik=cik, name=ticker, sic=sic)
    except (DataUnavailable, ValueError, KeyError, ZeroDivisionError) as exc:
        return {**row, 'status': 'NO_DATA', 'detail': str(exc)[:160]}
    if not data['history'] or data['history'][-1]['Fiscal year end'] != fy_end.isoformat():
        return {**row, 'status': 'NO_DATA', 'detail': 'latest year in the point-in-time history is not this FY'}
    br = data['bridge']
    if br.get('net_debt') is None or not br.get('shares'):
        return {**row, 'status': 'NO_BRIDGE', 'detail': 'debt, cash or shares missing at that date'}
    shares, me = br['shares'], price * br['shares']
    t = on_or_after(tnx, pdate)
    rf = t[1] / 100 if t and (t[0] - pdate).days <= 10 else None
    erp = erp_for(pdate, erp_table)
    if rf is None or erp is None:
        return {**row, 'status': 'NO_RATES', 'detail': 'risk-free or ERP missing'}
    debt = wacc_debt(br)[0]
    bu = bottom_up_beta(sic, market_equity=me, total_debt=debt)
    if bu.get('beta') is None:
        return {**row, 'status': 'NO_BETA', 'detail': 'no industry beta for this SIC'}
    ebit = data['history'][-1].get('EBIT')
    intr = annual_flows(pit, INTEREST_TAGS).get(fy_end.isoformat(), {}).get('value')
    cov = (float('inf') if intr == 0 else ebit / intr) if (ebit is not None and intr is not None and intr >= 0) else None
    kd = (cost_of_debt(rf, cov)[0] if cov is not None else None) or rf + 0.0111
    w = calculate_wacc(risk_free_rate=rf, beta=bu['beta'], equity_risk_premium=erp, cost_of_debt=kd,
                       tax_rate=MARGINAL_TAX, market_equity=me, total_debt=debt)
    row.update(price=price, shares=shares, market_equity=me, rf=rf, erp=erp, beta=bu['beta'], wacc=w['wacc'])
    if not w['wacc'] > G + 0.005:
        return {**row, 'status': 'NO_WACC', 'detail': 'WACC not above terminal growth'}
    res = {}
    for s in ('conservative', 'base', 'optimistic'):
        res[s] = dm.run(data['history'], wacc=w['wacc'], terminal_growth=G, net_debt=br['net_debt'], shares=shares,
                        scenario=s, calibration=cal, rd_life=data['rd_life'], rd_life_note=data['rd_note'],
                        industry_margin=data.get('industry_margin'))
    vals = {s: res[s]['valuation']['intrinsic_price'] if 'valuation' in res[s] else None for s in res}
    if vals['base'] is None:
        return {**row, 'status': 'BLOCKED', 'detail': '; '.join(res['base']['assumptions'].get('blockers', []))[:160]
                or str(res['base'].get('valuation_error', ''))[:160]}
    capm = {'risk_free_rate': rf, 'beta': bu['beta'], 'equity_risk_premium': erp, 'equity_weight': w['equity_weight'],
            'debt_weight': w['debt_weight'], 'after_tax_cost_of_debt': w['after_tax_cost_of_debt']}
    sim = vs.simulate(res['base'], data['history'], net_debt=br['net_debt'], shares=shares, capm=capm, n=N_DRAWS,
                      calibration=cal, errors=errors)
    v = vd.verdict_from_samples(sim['values'], price, 0.15, base=vals['base']) if sim else None
    vs_ = vd.verdict(vals, price, 0.15)
    row.update(status='OK', value_cons=vals['conservative'], value_base=vals['base'], value_opt=vals['optimistic'],
               value_to_price=vals['base'] / price, data_status=res['base']['status'],
               verdict_scenarios=vs_['action'] if vs_ else None)
    if v:
        row.update(p_above=v['prob_above_market'], p_buy=v['probabilities']['buy'], p_hold=v['probabilities']['hold'],
                   p_sell=v['probabilities']['sell'], verdict=v['action'], distress_share=sim['distress_share'])
    for y in HORIZONS_Y:
        r, m = total_return(prices['adj'], pdate, y), total_return(spy, pdate, y)
        row[f'ret_{y}y'], row[f'spy_{y}y'] = r, m
        row[f'xs_{y}y'] = r - m if r is not None and m is not None else None
    return row


def run(limit=None):
    from intrinsic import forecast as dm
    from intrinsic.sec_data import companyfacts_cached
    if '@' not in os.environ.get('INTRINSIC_SEC_USER_AGENT', ''):
        raise SystemExit('Set INTRINSIC_SEC_USER_AGENT (a generic contact is fine for local runs)')
    with open(ERP_FILE) as fh:
        erp_table = json.load(fh)
    cal = dm.load_calibration()
    errors = train_error_pool()
    spy = yahoo_history('SPY')['adj']
    tnx = yahoo_history('^TNX')['close']
    uni = universe()[:limit] if limit else universe()
    done = set()
    if os.path.exists(ROWS_CSV):
        with open(ROWS_CSV) as fh:
            done = {(int(r['cik']), r['fy_end']) for r in csv.DictReader(fh)}
    new_file = not os.path.exists(ROWS_CSV)
    with open(ROWS_CSV, 'a', newline='') as fh:
        wr = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction='ignore')
        if new_file:
            wr.writeheader()
        for i, (cik, ticker, sic) in enumerate(uni, 1):
            try:
                payload = companyfacts_cached(cik, max_age_days=3650)
            except Exception as exc:
                wr.writerow({'cik': cik, 'ticker': ticker, 'status': 'NO_SEC', 'detail': str(exc)[:160]})
                continue
            filings = {e: f for e, f in original_10k_filings(payload).items() if FIRST_END <= e <= LAST_END}
            todo = [(e, f) for e, f in sorted(filings.items()) if (cik, e.isoformat()) not in done]
            if not todo:
                continue
            prices = yahoo_history(ticker)
            for e, f in todo:
                if not prices['close']:
                    wr.writerow({'cik': cik, 'ticker': ticker, 'fy_end': e.isoformat(), 'filed': f.isoformat(),
                                 'status': 'NO_TICKER_PRICES', 'detail': 'Yahoo has no history for this ticker'})
                    continue
                try:
                    row = value_origin(cik, ticker, sic, payload, e, f, prices, tnx, erp_table, spy, errors, cal)
                except Exception as exc:                 # never hide: record and continue
                    row = {'cik': cik, 'ticker': ticker, 'fy_end': e.isoformat(), 'filed': f.isoformat(),
                           'status': 'ERROR', 'detail': f'{type(exc).__name__}: {exc}'[:160]}
                wr.writerow(row)
            fh.flush()
            print(f'[{i}/{len(uni)}] {ticker:6} {len(todo)} origins', flush=True)


# ------------------------------------------------------------------ analysis

def load_rows():
    with open(ROWS_CSV) as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r['cik'] = int(r['cik'])
        for k in FIELDS:
            if k in ('cik', 'ticker', 'fy_end', 'filed', 'price_date', 'status', 'detail', 'verdict',
                     'verdict_scenarios', 'data_status'):
                continue
            r[k] = float(r[k]) if r.get(k) not in (None, '') else None
    return rows


def analyse():
    rows = load_rows()
    status = {}
    for r in rows:
        status[r['status']] = status.get(r['status'], 0) + 1
    valued = [r for r in rows if r['status'] == 'OK' and r.get('p_above') is not None]
    issues = {}
    for r in valued:
        q = quality_issue(r)
        if q:
            issues[q] = issues.get(q, 0) + 1
    ok = [r for r in valued if not quality_issue(r)]
    for r in ok:
        for y in HORIZONS_Y:
            r[f'lx_{y}y'] = log_excess(r[f'ret_{y}y'], r[f'spy_{y}y'])
    out = {'origins': len(rows), 'companies': len({r['cik'] for r in rows}), 'status_counts': status,
           'valued_before_quality_filter': len(valued), 'excluded_data_quality': issues,
           'valued': len(ok), 'valued_companies': len({r['cik'] for r in ok}), 'by_horizon': {}}
    out['verdict_mix'] = {a: sum(r['verdict'] == a for r in ok) for a in ('buy', 'hold', 'sell')}
    out['median_value_to_price'] = median_([r['value_to_price'] for r in ok])
    for y in HORIZONS_Y:
        k, lk = f'xs_{y}y', f'lx_{y}y'
        sub = [r for r in ok if r[k] is not None and r[lk] is not None]
        if len(sub) < 30:
            continue
        h = {'n': len(sub), 'companies': len({r['cik'] for r in sub}),
             'lost_no_future_price': sum(1 for r in ok if r[k] is None),
             'mean_excess_all': mean([r[k] for r in sub]), 'median_excess_all': median_([r[k] for r in sub]),
             'mean_log_excess_all': mean([r[lk] for r in sub]),
             'share_beating_spy_all': sum(r[k] > 0 for r in sub) / len(sub)}
        for sig in ('p_above', 'value_to_price'):
            rho = spearman([r[sig] for r in sub], [r[k] for r in sub])
            ci = bootstrap_by_company(sub, lambda s: spearman([r[sig] for r in s], [r[k] for r in s]))
            h[f'spearman_{sig}'] = {'rho': rho, 'ci95': ci}
            buckets = []
            for b in quantile_buckets(sub, sig, 5):
                buckets.append({'range': [b[0][sig], b[-1][sig]], 'n': len(b),
                                'mean_excess': mean([r[k] for r in b]), 'median_excess': median_([r[k] for r in b]),
                                'mean_log_excess': mean([r[lk] for r in b]),
                                'share_beating_spy': sum(r[k] > 0 for r in b) / len(b),
                                'ci95_mean_log': bootstrap_by_company(b, lambda s: mean([r[lk] for r in s]), reps=500)})
            h[f'quintiles_{sig}'] = buckets
            top, bottom = quantile_buckets(sub, sig, 5)[-1], quantile_buckets(sub, sig, 5)[0]
            spread = lambda s: (mean([r[lk] for r in s if r[sig] >= top[0][sig]]) or 0) - \
                (mean([r[lk] for r in s if r[sig] <= bottom[-1][sig]]) or 0)
            h[f'top_minus_bottom_{sig}'] = {'value': spread(sub), 'ci95': bootstrap_by_company(sub, spread, reps=500)}
        h['by_verdict'] = {}
        for a in ('buy', 'hold', 'sell'):
            g = [r for r in sub if r['verdict'] == a]
            if g:
                h['by_verdict'][a] = {'n': len(g), 'companies': len({r['cik'] for r in g}),
                                      'mean_excess': mean([r[k] for r in g]), 'median_excess': median_([r[k] for r in g]),
                                      'mean_log_excess': mean([r[lk] for r in g]),
                                      'share_beating_spy': sum(r[k] > 0 for r in g) / len(g),
                                      'ci95_mean_log': bootstrap_by_company(g, lambda s: mean([r[lk] for r in s]),
                                                                            reps=500)}
        out['by_horizon'][f'{y}y'] = h
    with open(SUMMARY, 'w') as fh:
        json.dump(out, fh, indent=1, default=str)
    return out


def _fmt(x, pct=True):
    return '   n/a' if x is None else (f'{x:+.1%}' if pct else f'{x:+.2f}')


def print_summary(out):
    print(f"origins {out['origins']} from {out['companies']} companies · status {out['status_counts']}")
    print(f"valued {out['valued_before_quality_filter']}, excluded as data errors {out['excluded_data_quality']} -> "
          f"analysed {out['valued']} ({out['valued_companies']} companies)")
    print(f"verdict mix {out['verdict_mix']} · median base value / price {out['median_value_to_price']:.2f}")
    for hz, h in out['by_horizon'].items():
        print(f"\n== {hz}: n {h['n']} ({h['companies']} companies), lost for missing later prices "
              f"{h['lost_no_future_price']} · excess vs SPY: median {_fmt(h['median_excess_all'])}, mean log "
              f"{_fmt(h['mean_log_excess_all'])}, beat SPY {h['share_beating_spy_all']:.0%}")
        for sig in ('p_above', 'value_to_price'):
            s = h[f'spearman_{sig}']
            ci = s['ci95']
            print(f"  rank correlation {sig} vs excess return: {_fmt(s['rho'], False)} "
                  f"[{_fmt(ci[0], False) if ci else ''},{_fmt(ci[1], False) if ci else ''}]")
            for i, b in enumerate(h[f'quintiles_{sig}'], 1):
                ci = b['ci95_mean_log']
                print(f"    Q{i} [{b['range'][0]:.2f}..{b['range'][1]:.2f}] n {b['n']:4} median {_fmt(b['median_excess'])} "
                      f"mean log {_fmt(b['mean_log_excess'])} [{_fmt(ci[0]) if ci else ''},{_fmt(ci[1]) if ci else ''}] "
                      f"beat SPY {b['share_beating_spy']:.0%}")
            t = h[f'top_minus_bottom_{sig}']
            ci = t['ci95']
            print(f"    top − bottom quintile, mean log excess: {_fmt(t['value'])} "
                  f"[{_fmt(ci[0]) if ci else ''},{_fmt(ci[1]) if ci else ''}]")
        for a, g in h['by_verdict'].items():
            ci = g['ci95_mean_log']
            print(f"  {a:4} n {g['n']:4} ({g['companies']} cos) median {_fmt(g['median_excess'])} mean log "
                  f"{_fmt(g['mean_log_excess'])} [{_fmt(ci[0]) if ci else ''},{_fmt(ci[1]) if ci else ''}] "
                  f"beat SPY {g['share_beating_spy']:.0%}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'analyse'
    if cmd == 'run':
        run(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    print_summary(analyse())
