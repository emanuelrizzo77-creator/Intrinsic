"""Intrinsic 27 — FINAL out-of-sample validation (run once).

Design (pre-registered with --freeze BEFORE any result is seen):
  * Fresh companies: NYSE/Nasdaq filers NEVER used during development (every CIK
    already in the cache at freeze time is excluded).
  * Temporal split: parameters are estimated ONLY with fiscal years ending on or
    before CUTOFF (2018-12-31) from development companies; forecasts are evaluated
    from origins AFTER the cutoff on the fresh companies.
  * Same production logic: size buckets + partial pooling, high-growth fade,
    margin anchor = median of up to 9 prior years, first-reported SEC vintage.
  * Acceptance criteria written to validation/results/frozen_design.json at freeze time.

Usage:
  python validation/final_validation.py --freeze        # once; records design + criteria
  python validation/final_validation.py --n 800         # downloads fresh companies, runs test
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import math
import os
import random
from datetime import datetime, timezone
from statistics import mean, median

import sys as _sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in _sys.path:          # allow `python validation/<script>.py` as well as -m
    _sys.path.insert(0, _ROOT)
from validation import calibrate_fade as cal
from intrinsic.forecast import POOLING_K, size_bucket

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # project root
FROZEN = os.path.join(HERE, 'validation/results/frozen_design.json')
CUTOFF = '2018-12-31'
CRITERIA = [
    'R1: revenue h=3, fade beats random walk (CI upper < 0)',
    'R2: revenue h=5, fade beats random walk (CI upper < 0)',
    'R3: revenue h=5, fade beats historical median (CI upper < 0)',
    'M1: margin, fade not worse than random walk at any h (CI lower <= 0)',
    'B1: |revenue bias| at h=5 below 10% (no strong optimism/pessimism)',
]


# The design was frozen (and the test run) before the repository was reorganised into
# packages; frozen_design.json keeps the original file names. Map them to today's paths.
# The exact frozen code is commit 6dfb260 and earlier.
RENAMED = {'driver_forecast_27.py': 'intrinsic/forecast.py', 'calibrate_fade_27.py': 'validation/calibrate_fade.py',
           'final_validation_27.py': 'validation/final_validation.py', 'sec_annual_27.py': 'intrinsic/sec_data.py'}


def _sha(path):
    path = RENAMED.get(path, path)
    if not os.path.exists(os.path.join(HERE, path)):
        return 'missing'
    with open(os.path.join(HERE, path), 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def freeze(force=False):
    if os.path.exists(FROZEN) and not force:
        raise SystemExit('validation/results/frozen_design.json exists; the design is already frozen.')
    seen = sorted(int(os.path.basename(p)[:-5]) for p in glob.glob(os.path.join(cal.SERIES_DIR, '*.json')))
    design = {
        'frozen_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'cutoff': CUTOFF, 'min_revenue': cal.MIN_REVENUE, 'exchanges': sorted(cal.EXCHANGES),
        'high_growth': cal.HIGH_GROWTH, 'pooling_k': POOLING_K, 'margin_anchor': 'median of up to 9 prior years',
        'vintage': 'first', 'horizons': [1, 3, 5], 'criteria': CRITERIA,
        'code_sha256': {f: _sha(f) for f in ('intrinsic/forecast.py', 'validation/calibrate_fade.py',
                                             'validation/final_validation.py', 'intrinsic/sec_data.py')},
        'seen_ciks': seen,
    }
    with open(FROZEN, 'w') as fh:
        json.dump(design, fh, indent=1)
    print(f'Frozen: {len(seen)} development companies excluded; cutoff {CUTOFF}; {len(CRITERIA)} criteria.')
    for c in CRITERIA:
        print('  ' + c)


def runs_for(ciks, until=None):
    out = []
    for cik in ciks:
        s = cal.company_series(cik)
        rows = [r for r in s.get('rows', []) if until is None or r['end'] <= until]
        out.extend((cik, cal.enrich(r)) for r in cal.chains(rows))
    return out


def estimate(train_runs):
    runs = [r for _, r in train_runs]
    center = median([z['g'] for r in runs for z in r if z['g'] is not None and z['rev'] >= cal.MIN_REVENUE])
    gs = cal.samples(runs, 'g', center=center)
    est = {'center': center, 'growth': cal.fit(gs), 'margin': cal.fit(cal.samples(runs, 'm')),
           'growth_high': cal.fit({h: [s for s in rows if s[0] + center > cal.HIGH_GROWTH]
                                   for h, rows in gs.items()}).get('all')}
    return est


def pooled(table, rev):
    allp, own = table['all'], table.get(size_bucket(rev))
    if not own:
        return allp['phi']
    n = own['n_by_horizon'].get(1, 0)
    w = n / (n + POOLING_K)
    return w * own['phi'] + (1 - w) * allp['phi']


def evaluate(test_runs, est):
    c, errs = est['center'], {}
    for cid, run in test_runs:
        for i, r in enumerate(run):
            if r['g'] is None or r['rev'] < cal.MIN_REVENUE or r['end'] <= CUTOFF:
                continue
            gphi = est['growth_high']['phi'] if (r['g'] > cal.HIGH_GROWTH and est['growth_high']) else pooled(est['growth'], r['rev'])
            mphi = pooled(est['margin'], r['rev'])
            past_g = [z['g'] for z in run[max(1, i - 4):i + 1] if z['g'] is not None]
            past_m = [z['m'] for z in run[:i] if z['m'] is not None][-9:]
            for h in (1, 3, 5):
                if i + h >= len(run):
                    continue
                tgt = run[i + h]
                paths = {'random_walk': [r['g']] * h, 'hist_median': [median(past_g)] * h,
                         'fade_27': [c + (r['g'] - c) * gphi ** s for s in range(1, h + 1)]}
                for model, path in paths.items():
                    lvl = r['rev'] * math.prod(1 + x for x in path)
                    errs.setdefault(('revenue', model, h), []).append((cid, math.log(lvl / tgt['rev']) * 100, r['end'][:4]))
                if r['m'] is not None and len(past_m) >= 3 and tgt['m'] is not None:
                    a = median(past_m)
                    for model, pred in (('random_walk', r['m']), ('hist_median', a),
                                        ('fade_27', a + (r['m'] - a) * mphi ** h)):
                        errs.setdefault(('margin', model, h), []).append((cid, (pred - tgt['m']) * 100, r['end'][:4]))
    return errs


def ci(errs, a, b):
    return cal.bootstrap_diff([(c, e) for c, e, _ in errs[a]], [(c, e) for c, e, _ in errs[b]], reps=1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--freeze', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--n', type=int, default=800)
    ap.add_argument('--seed', type=int, default=2718)
    args = ap.parse_args()
    if args.freeze:
        return freeze(args.force)
    if not os.path.exists(FROZEN):
        raise SystemExit('Run with --freeze first.')
    with open(FROZEN) as fh:
        design = json.load(fh)
    changed = [f for f, h in design['code_sha256'].items() if _sha(f) != h]
    if changed:
        print(f'WARNING: code changed since freeze: {changed}. Results are not a clean pre-registered test.')
    seen = set(design['seen_ciks'])
    with open(os.path.join(HERE, 'data/sec_companies.csv')) as fh:
        universe = sorted({int(r['cik']) for r in csv.DictReader(fh) if r.get('exchange') in cal.EXCHANGES} - seen)
    random.Random(args.seed).shuffle(universe)
    fresh = universe[:args.n]
    print(f'Estimating on {len(seen)} development companies, data <= {CUTOFF} ...', flush=True)
    est = estimate(runs_for(sorted(seen), until=CUTOFF))
    print(f"  growth center {est['center']:.3f} · growth phi(all) {est['growth']['all']['phi']:.2f} · "
          f"high-growth {est['growth_high']['phi'] if est['growth_high'] else 'n/a'} · margin psi(all) {est['margin']['all']['phi']:.2f}")
    print(f'Downloading / loading {len(fresh)} FRESH companies ...', flush=True)
    test = []
    for i, cik in enumerate(fresh, 1):
        test.extend(runs_for([cik]))
        if i % 50 == 0:
            print(f'  {i}/{len(fresh)}', flush=True)
    errs = evaluate(test, est)
    report = {'design': {k: v for k, v in design.items() if k != 'seen_ciks'}, 'estimates': est, 'results': {}}
    print(f"\nFINAL TEST · fresh companies {len({c for c, _ in test})} · origins after {CUTOFF}")
    print(f"{'metric':<9}{'h':>3}{'model':>13}{'n':>7}{'MAE':>8}{'MdAE':>8}{'bias':>8}")
    for key in sorted(errs):
        v = [e for _, e, _ in errs[key]]
        row = {'n': len(v), 'mae': mean(abs(x) for x in v), 'mdae': median(abs(x) for x in v), 'bias': mean(v)}
        report['results']['|'.join(map(str, key))] = row
        print(f"{key[0]:<9}{key[2]:>3}{key[1]:>13}{row['n']:>7}{row['mae']:>8.2f}{row['mdae']:>8.2f}{row['bias']:>+8.2f}")
    verdict = {}
    lo, hi = ci(errs, ('revenue', 'fade_27', 3), ('revenue', 'random_walk', 3)); verdict['R1'] = (hi < 0, [lo, hi])
    lo, hi = ci(errs, ('revenue', 'fade_27', 5), ('revenue', 'random_walk', 5)); verdict['R2'] = (hi < 0, [lo, hi])
    lo, hi = ci(errs, ('revenue', 'fade_27', 5), ('revenue', 'hist_median', 5)); verdict['R3'] = (hi < 0, [lo, hi])
    m_ok, m_ci = True, {}
    for h in (1, 3, 5):
        lo, hi = ci(errs, ('margin', 'fade_27', h), ('margin', 'random_walk', h))
        m_ci[h] = [lo, hi]
        m_ok &= lo <= 0
    verdict['M1'] = (m_ok, m_ci)
    bias5 = report['results']['revenue|fade_27|5']['bias']
    verdict['B1'] = (abs(bias5) < 10, bias5)
    print('\nPRE-REGISTERED CRITERIA')
    for c in CRITERIA:
        k = c.split(':')[0]
        ok, detail = verdict[k]
        print(f"  {'PASS' if ok else 'FAIL'}  {c}  · {detail}")
    print('\nBy origin year (revenue h=1, MAE fade vs random walk):')
    for y in sorted({yr for _, _, yr in errs[('revenue', 'fade_27', 1)]}):
        f = [abs(e) for _, e, yr in errs[('revenue', 'fade_27', 1)] if yr == y]
        r = [abs(e) for _, e, yr in errs[('revenue', 'random_walk', 1)] if yr == y]
        print(f'  {y}: n={len(f):4d}  fade {mean(f):6.2f}  random walk {mean(r):6.2f}')
    report['verdict'] = {k: {'pass': v[0], 'detail': v[1]} for k, v in verdict.items()}
    report['ran_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with open(os.path.join(HERE, 'validation/results/final_validation.json'), 'w') as fh:
        json.dump(report, fh, indent=1, default=str)
    print('\nSaved validation/results/final_validation.json')


if __name__ == '__main__':
    main()
