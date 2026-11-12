"""Intrinsic 27 — which long-run MARGIN anchor forecasts best out of sample?

Uses the cached panel from calibrate_fade_27.py (no downloads). For each anchor
definition, the fade weight psi is re-estimated on TRAIN companies, then errors
are measured on TEST companies at h = 1, 3, 5. Same company split as calibration.

Anchors (all point-in-time: only information available at the origin year):
  prior9   median of up to 9 prior years      (current production default)
  prior5   median of up to 5 prior years
  prior3   median of up to 3 prior years
  industry median margin of TRAIN companies in the same 2-digit SIC that year
  blend    50% prior9 + 50% industry
"""
from __future__ import annotations

import glob
import json
import os
from statistics import mean, median

import calibrate_fade_27 as cal

ANCHORS = ('prior9', 'prior5', 'prior3', 'industry', 'blend')


def load_panel():
    train, test = [], []
    for path in glob.glob(os.path.join(cal.SERIES_DIR, '*.json')):
        with open(path) as fh:
            s = json.load(fh)
        sic2 = str(s.get('sic') or '')[:2]
        for run in cal.chains(s.get('rows', [])):
            run = cal.enrich(run)
            for r in run:
                r['sic2'] = sic2
            (test if s['cik'] % 5 == 0 else train).append((s['cik'], run))
    return train, test


def industry_table(train):
    cells = {}
    for _, run in train:
        for r in run:
            if r['m'] is not None and r['rev'] >= cal.MIN_REVENUE:
                cells.setdefault((r['sic2'], r['end'][:4]), []).append(r['m'])
                cells.setdefault(('*', r['end'][:4]), []).append(r['m'])
    return {k: median(v) for k, v in cells.items() if len(v) >= 5}


def anchor(run, i, kind, ind):
    prior = [z['m'] for z in run[:i] if z['m'] is not None]
    if len(prior) < 3:
        return None
    own = {'prior9': median(prior[-9:]), 'prior5': median(prior[-5:]), 'prior3': median(prior[-3:])}
    year = run[i]['end'][:4]
    industry = ind.get((run[i]['sic2'], year), ind.get(('*', year)))
    if kind in own:
        return own[kind]
    if industry is None:
        return None
    return industry if kind == 'industry' else 0.5 * own['prior9'] + 0.5 * industry


def pairs(runs, kind, ind):
    out = {h: [] for h in cal.HORIZONS}
    for cid, run in runs:
        for i, r in enumerate(run):
            if r['m'] is None or r['rev'] < cal.MIN_REVENUE:
                continue
            a = anchor(run, i, kind, ind)
            if a is None:
                continue
            for h in cal.HORIZONS:
                if i + h < len(run) and run[i + h]['m'] is not None:
                    out[h].append((r['m'] - a, run[i + h]['m'] - a, cid))
    return out


def main():
    train, test = load_panel()
    ind = industry_table(train)
    print(f'train runs {len(train)} · test runs {len(test)} · industry cells {len(ind)}')
    errors, psis = {}, {}
    for kind in ANCHORS:
        fit = cal.fit({h: [(x, y, 'all') for x, y, _ in rows] for h, rows in pairs(train, kind, ind).items()})
        psi = fit['all']['phi']
        psis[kind] = psi
        for h, rows in pairs(test, kind, ind).items():
            if h in (1, 3, 5):
                # forecast = anchor + psi^h (m_t - anchor); error vs actual, in pp
                errors[(kind, h)] = [(cid, (psi ** h * x - y) * 100) for x, y, cid in rows]
    print('\nOUT-OF-SAMPLE margin error by anchor (pp). CI = MAE(anchor) - MAE(prior9), company bootstrap')
    print(f"{'anchor':<10}{'psi':>6}{'h':>3}{'n':>7}{'MAE':>8}{'MdAE':>8}{'bias':>8}   CI vs prior9")
    for kind in ANCHORS:
        for h in (1, 3, 5):
            e = errors[(kind, h)]
            vals = [x for _, x in e]
            ci = ''
            if kind != 'prior9':
                # pair on identical (company, origin) observations only
                base = errors[('prior9', h)]
                if len(base) == len(e):
                    lo, hi = cal.bootstrap_diff(e, base)
                    ci = f'[{lo:+.2f}, {hi:+.2f}]' + ('  better' if hi < 0 else '  worse' if lo > 0 else '  n.s.')
                else:
                    ci = '(different sample: industry cell missing for some origins)'
            print(f"{kind:<10}{psis[kind]:>6.2f}{h:>3}{len(vals):>7}{mean(abs(v) for v in vals):>8.2f}"
                  f"{median(abs(v) for v in vals):>8.2f}{mean(vals):>+8.2f}   {ci}")


if __name__ == '__main__':
    main()
