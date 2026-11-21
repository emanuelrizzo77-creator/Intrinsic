"""Joint revenue / margin forecast errors for the Monte Carlo verdict, with an out-of-sample check.

  python validation/joint_errors.py      # reads the cached panel (.intrinsic_cache/series27), no downloads

For every company-year origin in the calibration panel it rebuilds the production forecast (same fade speeds and
growth centre as data/calibration.json) and records the errors at horizons 1..5 as ONE vector:

    [log revenue error h1..h5, margin error h1..h5]

stored both RAW (log points and margin points) and SCALED (divided by the company's own growth / margin volatility at
the origin, as the scenario bands are). Vectors are grouped by revenue size at the origin. Which form a size group
uses was decided OUT OF SAMPLE (train CIK % 5 != 0, test CIK % 5 == 0; table in the validation report): scaled errors
cover better below $10B, raw errors at $10B and above, where scaling by a volatility that reflects a structural trend
(e.g. Microsoft's rising margin) produced implausible tails (a 1st-percentile margin error of -83 points vs -33 raw).
High-growth origins (start growth > 25%) form their own group at any size, with scaled errors (90% band coverage
0.88 revenue / 0.94 margin vs 0.82 / 0.84 raw): large companies rarely grow that fast, so the size pool understates
how wrong a hypergrowth forecast can be.

Keeping the ten numbers together preserves the correlation between revenue and margin errors and across horizons,
which the separate p20/p80 bands of the scenarios ignore. The Monte Carlo verdict resamples these vectors.

Validation (locked split, as in calibrate_fade.py): vectors from companies with CIK % 5 != 0 are the TRAIN sample;
companies with CIK % 5 == 0 are TEST. The check asks whether TEST errors fall inside TRAIN quantiles at the nominal
rate, for each horizon and for the joint "both adverse" event. Writes data/joint_errors.json (all vectors, for
production) and validation/results/joint_errors_validation.json.

Limitation: only origins with five later years are used, so companies that stopped filing within five years
(failures, acquisitions) are under-represented and the error spread is, if anything, too narrow.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from statistics import median, pstdev

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from validation.calibrate_fade import (EXCHANGES, HIGH_GROWTH, HORIZONS, MIN_REVENUE, SERIES_DIR,  # noqa: E402
                                       SIGMA_FLOOR_GROWTH, SIGMA_FLOOR_MARGIN, _pooled, chains, company_series, enrich)

OUT = os.path.join(_ROOT, 'data', 'joint_errors.json')
GROUPS = (('<1B', 0.0, 1e9), ('1-10B', 1e9, 1e10), ('>=10B', 1e10, float('inf')))
KIND = {'<1B': 'z', '1-10B': 'z', '>=10B': 'raw', 'high_growth': 'z'}   # chosen by the out-of-sample table below


def size_group(revenue, high=False):
    """High-growth origins (start growth > 25%) form their own group at any size; the rest group by revenue."""
    if high:
        return 'high_growth'
    return next(name for name, lo, hi in GROUPS if lo <= revenue < hi)
REPORT = os.path.join(_ROOT, 'validation', 'results', 'joint_errors_validation.json')


def _q(xs, p):
    s = sorted(xs)
    k = (len(s) - 1) * p
    f = math.floor(k)
    return s[f] + (s[min(f + 1, len(s) - 1)] - s[f]) * (k - f)


def vectors(cal):
    with open(os.path.join(_ROOT, 'data', 'sec_companies.csv')) as fh:
        listed = {int(r['cik']) for r in csv.DictReader(fh) if r.get('exchange') in EXCHANGES}
    ciks = sorted({int(f[:-5]) for f in os.listdir(SERIES_DIR)} & listed)
    center = cal['growth_center']
    out = []
    for cik in ciks:
        for run in (enrich(r) for r in chains(company_series(cik)['rows'])):
            for i, r in enumerate(run):
                if r['g'] is None or r['m'] is None or r['rev'] < MIN_REVENUE or i + 5 >= len(run):
                    continue
                past_m = [z['m'] for z in run[:i] if z['m'] is not None][-9:]
                pg = [z['g'] for z in run[max(1, i - 8):i + 1] if z['g'] is not None]
                if len(past_m) < 3 or len(pg) < 3 or any(run[i + h]['m'] is None for h in HORIZONS):
                    continue
                high = r['g'] > HIGH_GROWTH
                gphi = cal['growth_fade_high']['phi'] if high else _pooled(cal['growth_fade'], r['rev'])
                mphi = _pooled(cal['margin_fade'], r['rev'])
                sg = max(SIGMA_FLOOR_GROWTH, pstdev(pg))
                sm = max(SIGMA_FLOOR_MARGIN, pstdev(past_m + [r['m']]))
                a = median(past_m)
                rev_e, mar_e = [], []
                for h in HORIZONS:
                    t = run[i + h]
                    lvl = r['rev'] * math.prod(1 + center + (r['g'] - center) * gphi ** s for s in range(1, h + 1))
                    rev_e.append(math.log(t['rev'] / lvl))
                    mar_e.append(t['m'] - (a + (r['m'] - a) * mphi ** h))
                out.append({'cik': cik, 'high': high, 'rev': r['rev'], 'group': size_group(r['rev'], high),
                            'raw': rev_e + mar_e, 'z': [x / sg for x in rev_e] + [x / sm for x in mar_e]})
    return out


def _coverage(train, test, j, lo_p, hi_p):
    lo, hi = _q([z[j] for z in train], lo_p), _q([z[j] for z in train], hi_p)
    return sum(lo <= z[j] <= hi for z in test) / len(test)


def validate(vecs):
    names = [f'revenue_h{h}' for h in HORIZONS] + [f'margin_h{h}' for h in HORIZONS]
    rep = {'by_group': {}}
    for g in [x[0] for x in GROUPS] + ['high_growth', 'all']:
        sel = [v for v in vecs if g == 'all' or v['group'] == g]
        tr, te = [v for v in sel if v['cik'] % 5], [v for v in sel if not v['cik'] % 5]
        rep['by_group'][g] = {'n_train': len(tr), 'n_test': len(te)}
        for kind in ('raw', 'z'):
            a, b = [v[kind] for v in tr], [v[kind] for v in te]
            rep['by_group'][g][kind] = {
                'central_60': {n: round(_coverage(a, b, j, .2, .8), 3) for j, n in enumerate(names)},
                'central_90_h5': {'revenue': round(_coverage(a, b, 4, .05, .95), 3),
                                  'margin': round(_coverage(a, b, 9, .05, .95), 3)},
                'margin_h5_p1_p99': [round(_q([z[9] for z in a], .01), 3), round(_q([z[9] for z in a], .99), 3)]}
    # joint event with the production choice: both revenue and margin below their train p20 at h5
    tr = [v[KIND[v['group']]] for v in vecs if v['cik'] % 5]
    te = [v[KIND[v['group']]] for v in vecs if not v['cik'] % 5]
    r20, m20 = _q([z[4] for z in tr], .2), _q([z[9] for z in tr], .2)
    both = lambda zs: sum(z[4] < r20 and z[9] < m20 for z in zs) / len(zs)
    rep['joint_both_below_p20_h5'] = {'train': round(both(tr), 4), 'test': round(both(te), 4), 'if_independent': 0.04}
    return rep


def main():
    with open(os.path.join(_ROOT, 'data', 'calibration.json')) as fh:
        cal = json.load(fh)
    vecs = vectors(cal)
    rep = validate(vecs)
    rep['created_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with open(REPORT, 'w') as fh:
        json.dump(rep, fh, indent=1)
    data = {'created_utc': rep['created_utc'], 'source': 'validation/joint_errors.py on the calibration panel',
            'calibration_created_utc': cal['created_utc'], 'horizons': list(HORIZONS),
            'layout': '[log revenue error h1..h5, margin error h1..h5]; kind z = divided by the company volatility '
                      '(growth sigma, margin sigma), kind raw = log points and margin points',
            'n': len(vecs), 'n_companies': len({v['cik'] for v in vecs}),
            'groups': {g: {'kind': 'scaled' if KIND[g] == 'z' else 'raw', 'min_revenue': lo, 'max_revenue': hi,
                           'vectors': [[round(x, 4) for x in v[KIND[g]]] for v in vecs if v['group'] == g]}
                       for g, lo, hi in GROUPS + (('high_growth', None, None),)}}
    with open(OUT, 'w') as fh:
        json.dump(data, fh, separators=(',', ':'), default=lambda x: None)
    print(f"{len(vecs)} vectors from {data['n_companies']} companies: "
          + ', '.join(f"{g} {len(d['vectors'])} ({d['kind']})" for g, d in data['groups'].items()))
    for g, r in rep['by_group'].items():
        for kind in ('raw', 'z'):
            c = r[kind]
            print(f"  {g:6} {kind:3} test 60%: rev h1/h3/h5 {c['central_60']['revenue_h1']}/{c['central_60']['revenue_h3']}/"
                  f"{c['central_60']['revenue_h5']} margin {c['central_60']['margin_h1']}/{c['central_60']['margin_h3']}/"
                  f"{c['central_60']['margin_h5']} | 90% h5 {c['central_90_h5']} | margin h5 p1/p99 {c['margin_h5_p1_p99']}")
    print('  joint both below p20 at h5 (production choice):', rep['joint_both_below_p20_h5'])


if __name__ == '__main__':
    main()
