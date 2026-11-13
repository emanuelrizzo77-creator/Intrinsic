"""Intrinsic — how much of the SEC universe can the dashboard actually value?

Draws a fixed random sample of NYSE/Nasdaq companies outside the Top 25 and runs the same
steps the dashboard runs: sector routing, SEC history and bridge (validation.top25_check.check),
then the market/WACC data step (intrinsic.wacc_data). Every company ends in exactly one bucket:

  VALUED        base-case intrinsic value produced (OK or DEGRADED data)
  OUT_OF_SCOPE  bank / insurer / REIT / holding company: refused by design
  BLOCKED       required SEC data missing or not verifiable: refused with a reason
  MARKET_DATA   SEC side fine, market data (price, beta, shares) unavailable
  ERROR         unexpected exception = a bug to fix

  python -m validation.universe_coverage --target 60
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import traceback
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from validation.top25_check import TOP_25, check  # noqa: E402

RESULTS = os.path.join(_ROOT, 'validation', 'results')


def bucket(row):
    r = row['result']
    if r == 'NOT_FCFF':
        return 'OUT_OF_SCOPE'
    if r in ('OK', 'DEGRADED', 'NEEDS_MARKET_SHARES'):
        return 'VALUED' if row.get('wacc_ok', True) else 'MARKET_DATA'
    if r == 'BLOCKED':
        return 'BLOCKED'
    if r == 'ERROR_DATA' and (row.get('detail') or '').startswith(('DataUnavailable', 'LookupError')):
        return 'BLOCKED'
    return 'ERROR'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', type=int, default=60, help='non-financial companies to evaluate')
    ap.add_argument('--max', type=int, default=120, help='hard cap on companies drawn')
    ap.add_argument('--seed', type=int, default=2026)
    args = ap.parse_args()
    from intrinsic.wacc_data import obtener_datos_wacc

    # One listing per company: the SEC list repeats a CIK for warrants, units and rights; the first
    # (shortest) ticker of each CIK is the common stock.
    first = {}
    with open(os.path.join(_ROOT, 'data', 'sec_companies.csv')) as fh:
        for r in csv.DictReader(fh):
            if r.get('exchange') in ('NYSE', 'Nasdaq') and r['ticker'] not in TOP_25:
                cur = first.get(r['cik'])
                if cur is None or (len(r['ticker']), r['ticker']) < (len(cur), cur):
                    first[r['cik']] = r['ticker']
    pool = sorted(first.values())
    random.Random(args.seed).shuffle(pool)
    rows, eligible = [], 0
    for ticker in pool[:args.max]:
        if eligible >= args.target:
            break
        row = check(ticker, 0.09, 0.025)
        if row['result'] in ('OK', 'DEGRADED', 'NEEDS_MARKET_SHARES'):
            try:
                w = obtener_datos_wacc(ticker)
                row.update(wacc_ok=True, beta_industry=(w.get('beta_bottom_up') or {}).get('industry'))
            except Exception as exc:
                row.update(wacc_ok=False, wacc_error=f'{type(exc).__name__}: {exc}'[:300],
                           wacc_trace=traceback.format_exc(limit=4))
        row['bucket'] = bucket(row)
        eligible += row['bucket'] != 'OUT_OF_SCOPE'
        rows.append(row)
        detail = row.get('wacc_error') or row.get('detail') or row.get('valuation_error') or ''
        print(f"{ticker:<7}{row['bucket']:<13}{str(row.get('company', ''))[:28]:<29}{detail}"[:200], flush=True)

    counts = Counter(r['bucket'] for r in rows)
    in_scope = [r for r in rows if r['bucket'] != 'OUT_OF_SCOPE']
    summary = {'drawn': len(rows), 'non_financial': len(in_scope), 'counts': dict(counts),
               'valued_share_of_non_financial': round(counts['VALUED'] / max(1, len(in_scope)), 3),
               'seed': args.seed}
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, 'universe_coverage.json'), 'w') as fh:
        json.dump({'summary': summary, 'rows': rows}, fh, indent=1, default=str)
    print('\nSummary:', json.dumps(summary))


if __name__ == '__main__':
    main()
