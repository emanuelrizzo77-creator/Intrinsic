"""Frozen Top 25 baseline: a regression guard for the universal engine.

  python -m validation.top25_baseline freeze     # snapshot SEC inputs + current outputs (needs SEC access)
  python -m validation.top25_baseline check      # recompute from the frozen inputs and compare (offline)

`freeze` stores, for every FCFF company of the Top 25, the inputs the dashboard feeds the engine (SEC history,
net-debt bridge, R&D life, industry margin) in tests/fixtures/top25_inputs.json and the engine's outputs in
tests/fixtures/top25_baseline.json: status, blockers, the three scenario prices and Monte Carlo quantiles, all at a
uniform 9% WACC and 2.5% terminal growth. Because the inputs are frozen, new SEC filings do not move the baseline:
only a change to the engine, the calibration or the error pool does. tests/test_top25_baseline.py runs `compare`.

A deliberate model change that moves these values must be followed by a new `freeze`, with the reason in the commit.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from intrinsic import forecast as dm  # noqa: E402
from intrinsic import value_simulation as vs  # noqa: E402

FIXTURES = os.path.join(_ROOT, 'tests', 'fixtures')
INPUTS = os.path.join(FIXTURES, 'top25_inputs.json')
BASELINE = os.path.join(FIXTURES, 'top25_baseline.json')
WACC, G = 0.09, 0.025
MC_DRAWS = 200
REL_TOL = 1e-6


def compute(inp):
    """Engine outputs for one frozen company input."""
    br = inp['bridge']
    shares = br['shares'] or 1.0
    out = {'scenarios': {}}
    base = None
    for s in ('conservative', 'base', 'optimistic'):
        r = dm.run(inp['history'], wacc=WACC, terminal_growth=G, net_debt=br['net_debt'], shares=shares, scenario=s,
                   rd_life=inp['rd_life'], rd_life_note=inp['rd_note'], industry_margin=inp['industry_margin'])
        out['scenarios'][s] = r['valuation']['intrinsic_price'] if 'valuation' in r else None
        if s == 'base':
            base = r
            out['status'] = r['status']
            out['blockers'] = list(r['assumptions']['blockers'])
            out['degradations'] = list(r['assumptions']['degradations'])
    sim = vs.simulate(base, inp['history'], net_debt=br['net_debt'], shares=shares, n=MC_DRAWS) \
        if 'valuation' in base else None
    if sim:
        v = sorted(sim['values'])
        out['mc'] = {f'p{q}': v[int(q / 100 * (len(v) - 1))] for q in (10, 50, 90)}
        out['mc']['distress_share'] = sim['distress_share']
    else:
        out['mc'] = None
    return out


def _close(a, b):
    if a is None or b is None:
        return a is b
    return abs(a - b) <= REL_TOL * max(1.0, abs(b))


def compare(inputs=None, baseline=None):
    """List of human-readable differences between the current engine and the frozen baseline (empty = identical)."""
    with open(inputs or INPUTS) as fh:
        inputs = json.load(fh)
    with open(baseline or BASELINE) as fh:
        baseline = json.load(fh)['companies']
    diffs = []
    for t, want in baseline.items():
        got = compute(inputs[t])
        for k in ('status', 'blockers', 'degradations'):
            if got[k] != want[k]:
                diffs.append(f'{t} {k}: {want[k]!r} -> {got[k]!r}')
        for s, w in want['scenarios'].items():
            if not _close(got['scenarios'][s], w):
                diffs.append(f'{t} {s}: {w} -> {got["scenarios"][s]}')
        if (want['mc'] is None) != (got['mc'] is None):
            diffs.append(f'{t} monte carlo: {want["mc"]} -> {got["mc"]}')
        elif want['mc']:
            for q, w in want['mc'].items():
                if not _close(got['mc'][q], w):
                    diffs.append(f'{t} mc {q}: {w} -> {got["mc"][q]}')
    return diffs


def freeze():
    from intrinsic.inputs import load_inputs
    from validation.top25_check import TOP_25
    inputs, baseline = {}, {}
    for t in TOP_25:
        d = load_inputs(t)
        if d['decision'].model != 'fcff' or d['bridge']['net_debt'] is None:
            print(f'{t:6} skipped ({d["decision"].model})')
            continue
        inp = json.loads(json.dumps({k: d[k] for k in ('cik', 'name', 'sic', 'history', 'rd_life', 'rd_note',
                                                       'industry_margin', 'bridge')}, default=str))
        inputs[t] = inp
        baseline[t] = compute(inp)
        print(f'{t:6} {baseline[t]["status"]:14} base {baseline[t]["scenarios"]["base"]}')
    os.makedirs(FIXTURES, exist_ok=True)
    with open(INPUTS, 'w') as fh:
        json.dump(inputs, fh, separators=(',', ':'))
    with open(BASELINE, 'w') as fh:
        json.dump({'created_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'wacc': WACC,
                   'terminal_growth': G, 'mc_draws': MC_DRAWS, 'companies': baseline}, fh, indent=1)
    print(f'Froze {len(inputs)} companies -> {os.path.relpath(INPUTS, _ROOT)}, {os.path.relpath(BASELINE, _ROOT)}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'freeze':
        freeze()
    else:
        d = compare()
        print('\n'.join(d) if d else 'Top 25 baseline: identical')
        sys.exit(1 if d else 0)
