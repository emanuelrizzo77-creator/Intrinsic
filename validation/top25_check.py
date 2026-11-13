"""Intrinsic 27 — run the model on the Top 25 dashboard universe and report readiness.

  python validation/top25_check.py              # downloads/caches SEC data, writes validation/results/top25_status.csv/json

WACC is a uniform placeholder (default 9%) because this script checks DATA and MODEL
behaviour; company-specific WACC is computed in the dashboard.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import traceback

import sys as _sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in _sys.path:          # allow `python validation/<script>.py` as well as -m
    _sys.path.insert(0, _ROOT)
from intrinsic import forecast as dm
from intrinsic.inputs import load_inputs

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # project root
TOP_25 = ['MSFT', 'AAPL', 'NVDA', 'GOOGL', 'AMZN', 'META', 'AVGO', 'TSLA', 'BRK-B', 'WMT', 'LLY', 'JPM', 'V', 'MA',
          'XOM', 'JNJ', 'ORCL', 'COST', 'HD', 'PG', 'ABBV', 'BAC', 'NFLX', 'KO', 'AMD']


def check(ticker, wacc, g):
    row = {'ticker': ticker}
    try:
        data = load_inputs(ticker)
    except Exception as exc:
        row.update(result='ERROR_DATA', detail=f'{type(exc).__name__}: {exc}')
        return row
    dec = data['decision']
    row.update(company=data['name'], sic=data['sic'], sector_model=dec.model)
    if dec.model != 'fcff':
        row.update(result='NOT_FCFF', detail=f'{dec.category}: {dec.reason}')
        return row
    br = data['bridge']
    row.update(net_debt_b=round(br['net_debt'] / 1e9, 2) if br['net_debt'] is not None else None,
               shares_source=br.get('shares_source'), debt_source=br.get('debt_source'),
               fiscal_year_end=data['history'][-1]['Fiscal year end'] if data['history'] else None,
               years_of_history=len(data['history']), capital_flags=' | '.join(data['capital_flags']))
    if br['net_debt'] is not None and not br['shares']:
        row.update(result='NEEDS_MARKET_SHARES', detail='SEC reports shares only by class; the dashboard uses the '
                   'market share count (flagged)')
        return row
    if br['net_debt'] is None:
        row.update(result='BLOCKED', detail='incomplete EV-to-equity bridge (debt, cash or short-term investments)')
        return row
    try:
        prices = {}
        for s in ('conservative', 'base', 'optimistic'):
            out = dm.run(data['history'], wacc=wacc, terminal_growth=g, net_debt=br['net_debt'], shares=br['shares'],
                         scenario=s, rd_life=data['rd_life'], rd_life_note=data['rd_note'])
            if s == 'base':
                a = out['assumptions']
                row.update(status=out['status'], blockers=' | '.join(a['blockers']),
                           degradations=' | '.join(a['degradations']), notes=' | '.join(a.get('notes', [])),
                           checks=' | '.join(out.get('checks', [])), valuation_error=out.get('valuation_error'))
                if 'projection' in out:
                    d = {k: x['value'] for k, x in a['drivers'].items()}
                    row.update(growth_y1=round(out['projection']['rows'][0]['growth'], 4),
                               margin_start=round(d['margin_start'], 4) if d.get('margin_start') is not None else None,
                               margin_target=round(d['margin_target'], 4) if d.get('margin_target') is not None else None,
                               ppe_leakage=d.get('ppe_leakage'), rd_capitalised='research_asset0' in d)
            prices[s] = round(out['valuation']['intrinsic_price'], 2) if 'valuation' in out else None
        row.update(price_conservative=prices['conservative'], price_base=prices['base'],
                   price_optimistic=prices['optimistic'],
                   result='OK' if prices['base'] is not None and row['status'] == 'DATA_COMPLETE'
                   else ('DEGRADED' if prices['base'] is not None else 'BLOCKED'))
    except Exception as exc:
        row.update(result='ERROR_MODEL', detail=f'{type(exc).__name__}: {exc}', trace=traceback.format_exc(limit=3))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wacc', type=float, default=0.09)
    ap.add_argument('--g', type=float, default=0.025)
    ap.add_argument('tickers', nargs='*')
    args = ap.parse_args()
    rows = []
    for t in args.tickers or TOP_25:
        r = check(t, args.wacc, args.g)
        rows.append(r)
        price = f"${r['price_base']:,.2f}" if r.get('price_base') is not None else '—'
        print(f"{t:<7}{r['result']:<12}{price:>11}   {r.get('detail') or r.get('blockers') or r.get('degradations') or ''}"[:220], flush=True)
    keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in ('ticker', 'result', 'company'), k))
    with open(os.path.join(HERE, 'validation/results/top25_status.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(HERE, 'validation/results/top25_status.json'), 'w') as fh:
        json.dump(rows, fh, indent=1, default=str)
    from collections import Counter
    print('\nSummary:', dict(Counter(r['result'] for r in rows)))
    print('Saved validation/results/top25_status.csv and validation/results/top25_status.json')


if __name__ == '__main__':
    main()
