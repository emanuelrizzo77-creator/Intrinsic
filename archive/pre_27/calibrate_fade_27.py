"""Intrinsic 27 — panel calibration of fade speeds + out-of-sample validation.

1. Samples non-financial US filers from intrinsic_sec_companies.csv.
2. Extracts AS-ORIGINALLY-REPORTED (vintage='first') annual revenue, EBIT, Net PP&E.
3. Splits companies: CIK % 5 == 0 -> locked TEST set, never used to estimate.
4. Estimates, on TRAIN companies only, by revenue size bucket:
     growth fade  : (g_{t+h} - c)       = phi^h (g_t - c)
     margin fade  : (m_{t+h} - anchor_t) = psi^h (m_t - anchor_t), anchor_t = median margin up to t
     intensity    : same as margin for Net PP&E / revenue
5. Evaluates on TEST companies at h = 1, 3, 5 vs baselines (random walk,
   historical median), with company-block bootstrap CIs.
Writes calibration_27.json (read automatically by driver_forecast_27).

Usage:
  export INTRINSIC_SEC_USER_AGENT="Intrinsic your@email.com"
  python calibrate_fade_27.py --n 500        # ~15-25 min first time; cached afterwards
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import time
from datetime import datetime, timezone
from statistics import mean, median
from urllib.request import Request, urlopen

from driver_forecast_27 import size_bucket
from financial_audit_21b import TAGS as TAGS_21B
from operating_capital_27 import PPE_TAGS
from sec_annual_27 import CACHE_DIR, annual_flows, annual_points, consecutive
from universal_valuation_21c import classify_sic

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES_DIR = os.path.join(CACHE_DIR, 'series27')
REVENUE_TAGS = tuple(TAGS_21B['Revenue']) + ('RevenueFromContractWithCustomerIncludingAssessedTax',)
HORIZONS = (1, 2, 3, 4, 5)


def _get(url):
    agent = os.environ.get('INTRINSIC_SEC_USER_AGENT', '')
    if '@' not in agent:
        raise SystemExit('Set INTRINSIC_SEC_USER_AGENT="Intrinsic your@email.com"')
    req = Request(url, headers={'User-Agent': agent, 'Accept-Encoding': 'identity'})
    with urlopen(req, timeout=60) as r:
        data = json.load(r)
    time.sleep(0.12)
    return data


def company_series(cik):
    """Compact cached series: [{end, rev, ebit, ppe}], plus SIC. No full payload stored."""
    path = os.path.join(SERIES_DIR, f'{cik}.json')
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    out = {'cik': cik, 'sic': None, 'rows': []}
    try:
        out['sic'] = _get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json').get('sic')
        if classify_sic(out['sic']).model == 'fcff':
            p = _get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json')
            rev = annual_flows(p, REVENUE_TAGS, vintage='first')
            ebit = annual_flows(p, ('OperatingIncomeLoss',), vintage='first')
            ppe = annual_points(p, PPE_TAGS, vintage='first')
            out['rows'] = [{'end': e, 'rev': rev[e]['value'], 'ebit': ebit.get(e, {}).get('value'),
                            'ppe': ppe.get(e, {}).get('value')} for e in sorted(rev)]
    except Exception as exc:   # network / missing filer: record and skip
        out['error'] = str(exc)[:200]
    os.makedirs(SERIES_DIR, exist_ok=True)
    with open(path, 'w') as fh:
        json.dump(out, fh)
    return out


def chains(rows):
    """Split into runs of consecutive fiscal years with positive revenue."""
    runs, cur = [], []
    for r in rows:
        if not r['rev'] or r['rev'] <= 0:
            cur = []
            continue
        if cur and not consecutive(cur[-1]['end'], r['end']):
            runs.append(cur)
            cur = []
        cur.append(r)
    if cur:
        runs.append(cur)
    return [c for c in runs if len(c) >= 4]


def enrich(run):
    for i, r in enumerate(run):
        r['g'] = min(1.5, max(-0.5, r['rev'] / run[i - 1]['rev'] - 1)) if i else None
        r['m'] = r['ebit'] / r['rev'] if r['ebit'] is not None else None
        r['k'] = r['ppe'] / r['rev'] if r['ppe'] is not None else None
    return run


def _q(vals, p):
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, int(p * (len(s) - 1))))]


def winsor(pairs):
    if len(pairs) < 50:
        return pairs
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    lo_x, hi_x, lo_y, hi_y = _q(xs, .01), _q(xs, .99), _q(ys, .01), _q(ys, .99)
    return [(min(hi_x, max(lo_x, x)), min(hi_y, max(lo_y, y))) for x, y in pairs]


def samples(runs, key, center=None):
    """{h: [(x, y, bucket)]} deviations from center (growth) or point-in-time anchor."""
    out = {h: [] for h in HORIZONS}
    for run in runs:
        for i, r in enumerate(run):
            if r[key] is None:
                continue
            if center is None:
                hist = [z[key] for z in run[:i + 1] if z[key] is not None]
                if len(hist) < 3:
                    continue
                anchor = median(hist)
            else:
                anchor = center
            for h in HORIZONS:
                if i + h < len(run) and run[i + h][key] is not None:
                    out[h].append((r[key] - anchor, run[i + h][key] - anchor, size_bucket(r['rev'])))
    return out


def fit(samp, min_n=30):
    """Per bucket: phi_h by OLS through origin, then geometric phi by grid search."""
    result = {}
    for bucket in ('all', '<1B', '1-10B', '10-100B', '>100B'):
        phis, ns = {}, {}
        for h, rows in samp.items():
            pairs = winsor([(x, y) for x, y, b in rows if bucket == 'all' or b == bucket])
            sxx = sum(x * x for x, _ in pairs)
            if len(pairs) >= min_n and sxx > 0:
                phis[h], ns[h] = sum(x * y for x, y in pairs) / sxx, len(pairs)
        if 1 not in phis:
            continue
        best = min((sum(ns[h] * (phis[h] - (p / 100) ** h) ** 2 for h in phis), p / 100) for p in range(0, 100))[1]
        result[bucket] = {'phi': best, 'phi_by_horizon': phis, 'n_by_horizon': ns}
    return result


def evaluate(test_runs, cal, center):
    """Out-of-sample errors on TEST companies. Revenue: log level error at h. Margin: pp."""
    gphi = lambda rev: (cal['growth_fade'].get(size_bucket(rev)) or cal['growth_fade']['all'])['phi']
    mphi = lambda rev: (cal['margin_fade'].get(size_bucket(rev)) or cal['margin_fade']['all'])['phi']
    errs = {}   # (metric, model, h) -> list of (company, error)
    for cid, run in test_runs:
        for i, r in enumerate(run):
            if r['g'] is None:
                continue
            past_g = [z['g'] for z in run[max(1, i - 4):i + 1] if z['g'] is not None]
            past_m = [z['m'] for z in run[:i + 1] if z['m'] is not None]
            for h in (1, 3, 5):
                if i + h >= len(run):
                    continue
                actual = run[i + h]['rev']
                paths = {
                    'random_walk': [r['g']] * h,
                    'hist_median': [median(past_g)] * h,
                    'fade_27': [center + (r['g'] - center) * gphi(r['rev']) ** s for s in range(1, h + 1)],
                }
                for model, path in paths.items():
                    level = r['rev'] * math.prod(1 + x for x in path)
                    errs.setdefault(('revenue_log_level', model, h), []).append((cid, math.log(level / actual)))
                if r['m'] is not None and len(past_m) >= 3 and run[i + h]['m'] is not None:
                    anchor, am = median(past_m), run[i + h]['m']
                    preds = {'random_walk': r['m'], 'hist_median': anchor,
                             'fade_27': anchor + (r['m'] - anchor) * mphi(r['rev']) ** h}
                    for model, pred in preds.items():
                        errs.setdefault(('ebit_margin_pp', model, h), []).append((cid, (pred - am) * 100))
    return errs


def bootstrap_diff(a, b, reps=500, seed=7):
    """95% CI of MAE(a) - MAE(b), resampling companies (errors are clustered)."""
    by = {}
    for (c, ea), (_, eb) in zip(a, b):
        by.setdefault(c, []).append((abs(ea), abs(eb)))
    ids, rng, diffs = list(by), random.Random(seed), []
    for _ in range(reps):
        pick = [p for c in (rng.choice(ids) for _ in ids) for p in by[c]]
        diffs.append(mean(x for x, _ in pick) - mean(y for _, y in pick))
    return _q(diffs, .025), _q(diffs, .975)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=500, help='companies to sample')
    ap.add_argument('--seed', type=int, default=27)
    args = ap.parse_args()
    with open(os.path.join(HERE, 'intrinsic_sec_companies.csv')) as fh:
        universe = sorted({int(r['cik']) for r in csv.DictReader(fh)})
    random.Random(args.seed).shuffle(universe)
    train, test = [], []
    for i, cik in enumerate(universe[:args.n], 1):
        s = company_series(cik)
        runs = [enrich(r) for r in chains(s['rows'])]
        (test if cik % 5 == 0 else train).extend((cik, r) for r in runs)
        if i % 25 == 0:
            print(f'  {i}/{args.n} companies · train runs {len(train)} · test runs {len(test)}', flush=True)

    train_runs = [r for _, r in train]
    center = median([z['g'] for r in train_runs for z in r if z['g'] is not None])
    cal = {
        'created_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'universe_sampled': args.n, 'train_companies': len({c for c, _ in train}),
        'test_companies': len({c for c, _ in test}), 'growth_center': center,
        'vintage': 'first (as originally reported)',
        'growth_fade': fit(samples(train_runs, 'g', center=center)),
        'margin_fade': fit(samples(train_runs, 'm')),
        'intensity_fade': fit(samples(train_runs, 'k')),
        'caveats': [
            'Revenue growth uses first-reported values from consecutive 10-Ks; real-time growth would use the restated prior year.',
            'Survivorship: universe is the current SEC ticker list; delisted companies are under-represented.',
            'Company-level fade speeds are pooled by size bucket only; no sector conditioning yet.',
        ],
    }
    if 'all' not in cal['growth_fade'] or 'all' not in cal['margin_fade']:
        raise SystemExit('Not enough data to calibrate; increase --n')
    g_phi, m_phi = cal['growth_fade']['all']['phi'], cal['margin_fade']['all']['phi']
    g_res = [y - g_phi * x for x, y, _ in samples(train_runs, 'g', center=center)[1]]
    m_res = [y - m_phi ** 5 * x for x, y, _ in samples(train_runs, 'm')[5]]
    cal['scenario_quantiles'] = {'growth_p20_p80_h1': [_q(g_res, .2), _q(g_res, .8)],
                                 'margin_p20_p80_h5': [_q(m_res, .2), _q(m_res, .8)]}

    errs = evaluate(test, cal, center)
    report = {}
    print('\nOUT-OF-SAMPLE (TEST companies only)')
    print(f"{'metric':<18}{'h':>3}{'model':>13}{'n':>7}{'MAE':>9}{'MdAE':>9}{'bias':>9}   CI[MAE fade − MAE RW]")
    for (metric, model, h), e in sorted(errs.items()):
        vals = [x for _, x in e]
        scale = 100 if metric.startswith('revenue') else 1
        row = {'n': len(vals), 'mae': mean(abs(x) for x in vals) * scale,
               'mdae': median(abs(x) for x in vals) * scale, 'bias': mean(vals) * scale}
        ci = ''
        if model == 'fade_27':
            lo, hi = bootstrap_diff(e, errs[(metric, 'random_walk', h)])
            row['ci_vs_random_walk'] = [lo * scale, hi * scale]
            ci = f'[{lo * scale:+.2f}, {hi * scale:+.2f}]' + ('  better' if hi < 0 else '  worse' if lo > 0 else '  n.s.')
        report[f'{metric}|{model}|h{h}'] = row
        print(f"{metric:<18}{h:>3}{model:>13}{row['n']:>7}{row['mae']:>9.2f}{row['mdae']:>9.2f}{row['bias']:>+9.2f}   {ci}")
    print('Units: revenue = % log-level error at horizon h; margin = percentage points. bias>0 = optimistic.')
    cal['out_of_sample'] = report
    with open(os.path.join(HERE, 'calibration_27.json'), 'w') as fh:
        json.dump(cal, fh, indent=2)
    print(f"\nSaved calibration_27.json · growth phi(all)={g_phi:.2f} · margin psi(all)={m_phi:.2f} · "
          f"intensity={cal['intensity_fade'].get('all', {}).get('phi')}")


if __name__ == '__main__':
    main()
