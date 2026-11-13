"""Intrinsic 27 — do the conservative/optimistic scenarios cover reality?

Bands are estimated on development companies with data <= 2018 and evaluated on
the FRESH holdout companies (origins after 2018). Target coverage of a p20–p80
band = 60%.

  current  : shift start growth by residual quantile / phi (year-1 calibrated),
             shift margin target by h=5 residual quantile
  horizon  : cumulative-error quantiles estimated separately for each horizon h
             (revenue: log-level error; margin: pp error)
"""
from __future__ import annotations

import json
import math
import os
from statistics import median

import sys as _sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in _sys.path:          # allow `python validation/<script>.py` as well as -m
    _sys.path.insert(0, _ROOT)
from validation import calibrate_fade as cal
from validation import final_validation as fv
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # project root


def fade_paths(run, i, est):
    r = run[i]
    c = est['center']
    gphi = est['growth_high']['phi'] if (r['g'] > cal.HIGH_GROWTH and est['growth_high']) else fv.pooled(est['growth'], r['rev'])
    mphi = fv.pooled(est['margin'], r['rev'])
    past_m = [z['m'] for z in run[:i] if z['m'] is not None][-9:]
    anchor = median(past_m) if len(past_m) >= 3 and r['m'] is not None else None
    return c, gphi, mphi, anchor


def observations(runs, est, after=None, until=None):
    """Yield (h, rev_err_log, margin_err_pp, start state) for the fade forecast."""
    for cid, run in runs:
        for i, r in enumerate(run):
            if r['g'] is None or r['rev'] < cal.MIN_REVENUE:
                continue
            if after and r['end'] <= after:
                continue
            c, gphi, mphi, anchor = fade_paths(run, i, est)
            for h in (1, 2, 3, 4, 5):
                if i + h >= len(run) or (until and run[i + h]['end'] > until):
                    continue
                tgt = run[i + h]
                lvl = r['rev'] * math.prod(1 + c + (r['g'] - c) * gphi ** s for s in range(1, h + 1))
                merr = None
                if anchor is not None and tgt['m'] is not None:
                    merr = tgt['m'] - (anchor + (r['m'] - anchor) * mphi ** h)
                yield h, cid, math.log(tgt['rev'] / lvl), merr, (r, c, gphi, mphi, anchor)


def main():
    with open(os.path.join(HERE, 'validation/results/frozen_design.json')) as fh:
        seen = set(json.load(fh)['seen_ciks'])
    cached = {int(f[:-5]) for f in os.listdir(cal.SERIES_DIR)}
    fresh = sorted(cached - seen)
    dev = fv.runs_for(sorted(seen), until=fv.CUTOFF)
    est = fv.estimate(dev)
    # Horizon-specific bands from development data (<= cutoff)
    rev_e, mar_e = {}, {}
    for h, _, re_, me, _ in observations(dev, est):
        rev_e.setdefault(h, []).append(re_)
        if me is not None:
            mar_e.setdefault(h, []).append(me)
    band = {h: {'rev': (cal._q(rev_e[h], .2), cal._q(rev_e[h], .8)),
                'mar': (cal._q(mar_e[h], .2), cal._q(mar_e[h], .8))} for h in rev_e}
    # "current" method parameters (year-1 growth residual, h=5 margin residual)
    g1 = [re_ for h, _, re_, _, _ in observations(dev, est) if h == 1]
    gq = (cal._q(g1, .2), cal._q(g1, .8))
    mq = band[5]['mar']
    test = fv.runs_for(fresh)
    cover = {}
    for h, cid, re_, me, (r, c, gphi, mphi, anchor) in observations(test, est, after=fv.CUTOFF):
        # current method: start growth shifted by gq/phi -> cumulative effect on level
        base = sum(math.log(1 + c + (r['g'] - c) * gphi ** s) for s in range(1, h + 1))
        lo = sum(math.log(max(1e-6, 1 + c + (r['g'] + gq[0] / max(gphi, .05) - c) * gphi ** s)) for s in range(1, h + 1)) - base
        hi = sum(math.log(1 + c + (r['g'] + gq[1] / max(gphi, .05) - c) * gphi ** s) for s in range(1, h + 1)) - base
        k = cover.setdefault(h, {'cur_rev': [], 'hor_rev': [], 'cur_mar': [], 'hor_mar': []})
        k['cur_rev'].append(lo <= re_ <= hi)
        k['hor_rev'].append(band[h]['rev'][0] <= re_ <= band[h]['rev'][1])
        if me is not None:
            shift = 1 - mphi ** h      # target shift reaches the path gradually
            k['cur_mar'].append(mq[0] * shift <= me <= mq[1] * shift)
            k['hor_mar'].append(band[h]['mar'][0] <= me <= band[h]['mar'][1])
    print(f'Fresh holdout companies: {len(fresh)} · target coverage of p20–p80 band = 60%\n')
    print(f"{'h':>2}{'n':>6}  {'revenue: current':>17}{'horizon':>9}   {'margin: current':>16}{'horizon':>9}   band revenue (log)      band margin (pp)")
    for h in sorted(cover):
        k = cover[h]
        pct = lambda xs: f'{100 * sum(xs) / len(xs):.0f}%' if xs else 'n/a'
        b = band[h]
        print(f"{h:>2}{len(k['hor_rev']):>6}  {pct(k['cur_rev']):>17}{pct(k['hor_rev']):>9}   {pct(k['cur_mar']):>16}{pct(k['hor_mar']):>9}"
              f"   [{b['rev'][0]:+.3f}, {b['rev'][1]:+.3f}]      [{b['mar'][0] * 100:+.1f}, {b['mar'][1] * 100:+.1f}]")


if __name__ == '__main__':
    main()
