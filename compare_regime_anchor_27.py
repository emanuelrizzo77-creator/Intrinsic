"""Intrinsic 27 — does a CONDITIONAL "regime shift" margin anchor beat prior9 out of sample?

Unconditional alternatives (prior5, prior3, industry, blend) were already tested in
compare_anchors_27.py and none beat prior9. This tests anchors that move ONLY when the
recent margins have clearly left the historical level.

PRE-REGISTERED (written before looking at results, 2026-11-12):

  prior9  median of up to 9 years BEFORE the origin (production default)
  recent3 = median of the 3 most recent margins, origin year included (t-2, t-1, t)
  trigger = those 3 margins are ALL above prior9, or ALL below (symmetric: the rule can
            lower the anchor as easily as raise it)

  shift    triggered -> anchor = recent3                     ; else prior9
  shiftmix triggered -> anchor = 0.5 * prior9 + 0.5 * recent3 ; else prior9
  shiftbig triggered AND |recent3 - prior9| > stdev(prior margins) -> recent3 ; else prior9

  psi is re-estimated on TRAIN companies for each rule (same as compare_anchors_27).
  Errors on locked TEST companies (CIK % 5 == 0), h = 1, 3, 5, company-block bootstrap.

  ADOPT a rule only if, on TEST origins where it triggers:
    A1  MAE better than prior9 at h = 3 AND h = 5 (95% CI upper < 0)
    A2  not worse at h = 1 (CI lower <= 0)
    A3  |bias| at h = 5 not larger than prior9's by more than 1 pp
  Three rules are tested, so a single marginal "win" is treated as weak evidence.

RESULT (run 2026-11-12, 927 train / 244 test runs): NO RULE ADOPTED.
  Triggered origins, MAE vs prior9 (pp):  shift    h3 8.46 vs 8.22, h5 9.54 vs 9.22
                                          shiftmix h3 8.25 vs 8.22, h5 9.27 vs 9.22
                                          shiftbig h3 9.37 vs 8.87, h5 10.97 vs 10.13
  All CIs include zero; point estimates favour prior9 at h = 3 and 5. A1 fails for every rule.
  Margin shifts that persisted 3 years still partly reverted within 5 years in this panel.
  Caveat: h <= 5 only; the anchor's effect on years 6-10 and the terminal value is untested.
"""
from __future__ import annotations

from statistics import mean, median, pstdev

import calibrate_fade_27 as cal
from compare_anchors_27 import load_panel

RULES = ('prior9', 'shift', 'shiftmix', 'shiftbig')
WATCH = {1045810: 'NVIDIA', 2488: 'AMD', 1730168: 'Broadcom', 59478: 'Eli Lilly',
         789019: 'Microsoft', 320193: 'Apple', 104169: 'Walmart', 909832: 'Costco'}


def anchor(run, i, rule):
    """(anchor, triggered) using only information available at origin i."""
    prior = [z['m'] for z in run[:i] if z['m'] is not None]
    if len(prior) < 3:
        return None, False
    p9 = median(prior[-9:])
    recent = [z['m'] for z in run[max(0, i - 2):i + 1]]
    if rule == 'prior9' or len(recent) < 3 or any(m is None for m in recent):
        return p9, False
    trig = all(m > p9 for m in recent) or all(m < p9 for m in recent)
    r3 = median(recent)
    if rule == 'shiftbig':
        trig = trig and abs(r3 - p9) > pstdev(prior[-9:])
    if not trig:
        return p9, False
    return (0.5 * p9 + 0.5 * r3 if rule == 'shiftmix' else r3), True


def pairs(runs, rule):
    out = {h: [] for h in cal.HORIZONS}
    for cid, run in runs:
        for i, r in enumerate(run):
            if r['m'] is None or r['rev'] < cal.MIN_REVENUE:
                continue
            a, trig = anchor(run, i, rule)
            if a is None:
                continue
            for h in cal.HORIZONS:
                if i + h < len(run) and run[i + h]['m'] is not None:
                    out[h].append((r['m'] - a, run[i + h]['m'] - a, cid, trig, a))
    return out


def summary(e):
    v = [x for _, x in e]
    return len(v), mean(abs(x) for x in v), median(abs(x) for x in v), mean(v)


def main():
    train, test = load_panel()
    print(f'train runs {len(train)} · test runs {len(test)}')
    psi, errs = {}, {}
    for rule in RULES:
        psi[rule] = cal.fit({h: [(x, y, 'all') for x, y, *_ in rows]
                             for h, rows in pairs(train, rule).items()})['all']['phi']
        for h, rows in pairs(test, rule).items():
            if h in (1, 3, 5):
                errs[(rule, h)] = [(cid, (psi[rule] ** h * x - y) * 100, trig) for x, y, cid, trig, _ in rows]

    trig_share = {r: mean(t for *_, t in errs[(r, 1)]) for r in RULES[1:]}
    print('psi by rule:', {r: round(p, 2) for r, p in psi.items()})
    print('trigger share (test, h=1 origins):', {r: f'{s:.0%}' for r, s in trig_share.items()})

    for scope in ('ALL test origins', 'TRIGGERED origins only'):
        print(f'\n{scope}: margin error (pp). CI = MAE(rule) - MAE(prior9), company bootstrap')
        print(f"{'rule':<10}{'h':>3}{'n':>7}{'MAE':>8}{'MdAE':>8}{'bias':>8}   prior9 MAE/bias   CI vs prior9")
        for rule in RULES[1:]:
            for h in (1, 3, 5):
                e, b = errs[(rule, h)], errs[('prior9', h)]
                assert len(e) == len(b)   # identical (company, origin) set: anchors differ, sample doesn't
                keep = [k for k, (_, _, t) in enumerate(e) if t] if scope.startswith('TRIG') else range(len(e))
                ee = [(e[k][0], e[k][1]) for k in keep]
                bb = [(b[k][0], b[k][1]) for k in keep]
                if len(ee) < 20:
                    print(f'{rule:<10}{h:>3}{len(ee):>7}   too few')
                    continue
                n, mae, mdae, bias = summary(ee)
                _, bmae, _, bbias = summary(bb)
                lo, hi = cal.bootstrap_diff(ee, bb)
                verdict = 'better' if hi < 0 else 'worse' if lo > 0 else 'n.s.'
                print(f'{rule:<10}{h:>3}{n:>7}{mae:>8.2f}{mdae:>8.2f}{bias:>+8.2f}   {bmae:>6.2f} {bbias:>+6.2f}'
                      f'     [{lo:+.2f}, {hi:+.2f}] {verdict}')

    # Illustration only (not evidence): what each rule implies today for watched companies.
    print('\nLatest-origin anchors for watched companies (cached panel, as originally reported):')
    for cid, run in train + test:
        if cid in WATCH and run is max((r for c, r in train + test if c == cid), key=lambda r: r[-1]['end']):
            i = len(run) - 1
            if run[i]['m'] is None:
                continue
            cells = '  '.join(f'{rule}={anchor(run, i, rule)[0] * 100:5.1f}%' for rule in RULES
                              if anchor(run, i, rule)[0] is not None)
            print(f"  {WATCH[cid]:<11} FY{run[i]['end'][:4]} margin {run[i]['m'] * 100:5.1f}%  {cells}")


if __name__ == '__main__':
    main()
