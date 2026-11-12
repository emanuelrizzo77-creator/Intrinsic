"""Run the Intrinsic 27 driver model for one ticker from the command line.

Usage:
  export INTRINSIC_SEC_USER_AGENT="Intrinsic your@email.com"
  python run_driver_27.py NVDA --wacc 0.10 --g 0.025
  python run_driver_27.py TSLA --wacc 0.10 --override dep_rate=0.12
  python run_driver_27.py MSFT --wacc 0.09 --override intensity_target=0.55 --json msft_27.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os

import driver_forecast_27 as dm
from operating_capital_27 import build_capital_history, rd_life_for_sic
from sec_annual_27 import companyfacts_cached, is_number, submissions_cached
from universal_financial_23b import normalize_balance_23b
from universal_financial_23c import analyze_historical_23c
from universal_valuation_21c import classify_sic

HERE = os.path.dirname(os.path.abspath(__file__))


def lookup_cik(ticker):
    ticker = ticker.upper().replace('.', '-')
    path = os.path.join(HERE, 'cik_overrides_27.json')
    if os.path.exists(path):
        with open(path) as fh:
            over = json.load(fh).get(ticker)
        if over:
            return int(over['cik']), ticker + ' (registrant override: ' + over['reason'][:60] + '...)'
    with open(os.path.join(HERE, 'intrinsic_sec_companies.csv')) as fh:
        for row in csv.DictReader(fh):
            if row['ticker'].upper() == ticker.upper():
                return int(row['cik']), row['company']
    raise SystemExit(f'Ticker {ticker} not found in intrinsic_sec_companies.csv')


def load_inputs(ticker, last_n=10):
    cik, name = lookup_cik(ticker)
    payload = companyfacts_cached(cik)
    sic = submissions_cached(cik).get('sic')
    decision = classify_sic(sic)
    from sec_annual_27 import annual_flows, annual_points
    hist = analyze_historical_23c(payload, last_n=last_n)
    if len(hist['rows']) < 3:
        raise ValueError(f"{payload.get('entityName', ticker)} has fewer than 3 annual revenue observations in SEC "
                         'CompanyFacts (new registrant or holding company?). Add a registrant mapping in '
                         'cik_overrides_27.json if the history is filed under another CIK.')
    # EBIT fallback when OperatingIncomeLoss is not reported (common in pharma):
    # pretax income + interest expense - interest income. Flagged as derived.
    pretax = annual_flows(payload, ('IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest',
                                    'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments',
                                    'IncomeLossFromContinuingOperationsBeforeIncomeTaxes'))
    int_exp = annual_flows(payload, ('InterestExpense', 'InterestExpenseNonoperating', 'InterestExpenseDebt'))
    int_inc = annual_flows(payload, ('InvestmentIncomeInterest', 'InvestmentIncomeInterestAndDividend'))
    for r in hist['rows']:
        r['EBIT source'] = 'OperatingIncomeLoss' if is_number(r.get('EBIT')) else None
        end = r['Fiscal year end']
        if not is_number(r.get('EBIT')) and end in pretax and end in int_exp:
            r['EBIT'] = pretax[end]['value'] + int_exp[end]['value'] - int_inc.get(end, {}).get('value', 0.0)
            r['EBIT source'] = 'derived'
            if is_number(r.get('Revenue')) and r['Revenue'] > 0:
                r['EBIT margin'] = r['EBIT'] / r['Revenue']
    ends = [r['Fiscal year end'] for r in hist['rows']]
    rd_life, rd_note = rd_life_for_sic(sic)
    capital = build_capital_history(payload, ends, rd_life=rd_life)
    history = dm.merge_history(hist['rows'], capital)
    bal = normalize_balance_23b(payload, ends[-1:])[-1]
    cap = capital[-1]
    total_debt, debt_source = bal.get('Total debt'), 'SEC 23B'
    if total_debt is None:
        pts = lambda tags: annual_points(payload, tags).get(ends[-1], {}).get('value')
        carrying = pts(('DebtInstrumentCarryingAmount',))
        cur, nonc = pts(('DebtCurrent', 'LongTermDebtCurrent')), pts(('LongTermDebtNoncurrent',))
        stb = pts(('ShortTermBorrowings', 'CommercialPaper'))
        if is_number(nonc) and (is_number(cur) or is_number(stb)):
            total_debt = nonc + (cur if is_number(cur) else 0.0) + (stb if is_number(stb) and not is_number(cur) else 0.0)
            debt_source = 'derived: noncurrent debt + current debt / short-term borrowings'
        elif is_number(carrying):
            total_debt, debt_source = carrying, 'DebtInstrumentCarryingAmount (VERIFY: excludes leases)'
    fll = cap.get('Finance lease liabilities')
    debt_tag = str((bal.get('tags') or {}).get('Total debt', ''))
    if is_number(total_debt) and is_number(fll) and fll > 0 and 'CapitalLease' not in debt_tag:
        total_debt += fll
        debt_source += f' + finance lease liabilities {fll / 1e9:,.2f}B'
    nonop = {k: cap.get(k) for k in ('Equity-method investments', 'Long-term marketable securities')
             if is_number(cap.get(k))}
    bridge = {'total_debt': total_debt, 'debt_source': debt_source, 'cash': cap.get('Cash'),
              'non_operating_assets': nonop,
              'short_term_investments': cap.get('Short-term investments'),
              'shares': bal.get('Shares outstanding'), 'shares_date': bal.get('Shares measurement date'),
              'balance_date': ends[-1]}
    if all(is_number(bridge[k]) for k in ('total_debt', 'cash', 'short_term_investments')):
        # Cash and short-term investments are excluded from operating NWC, so both
        # must be credited to equity here (otherwise they are lost from the valuation).
        bridge['net_debt'] = (bridge['total_debt'] - bridge['cash'] - bridge['short_term_investments']
                              - sum(nonop.values()))
    else:
        bridge['net_debt'] = None
    dil = annual_flows(payload, ('WeightedAverageNumberOfDilutedSharesOutstanding',), unit='shares')
    if ends[-1] in dil:
        bridge['basic_shares_snapshot'] = bridge['shares']
        bridge['shares'] = dil[ends[-1]]['value']
        bridge['shares_source'] = f'diluted weighted average, FY {ends[-1]}'
    else:
        bridge['shares_source'] = 'BASIC cover-page snapshot (no diluted count for latest FY)'
    return {'cik': cik, 'name': name, 'sic': sic, 'decision': decision, 'history': history,
            'rd_life': rd_life, 'rd_note': rd_note,
            'bridge': bridge, 'capital_flags': cap.get('flags', [])}


def _b(x):
    return f'{x / 1e9:9.2f}' if is_number(x) else '      n/a'


def _p(x):
    return f'{x:8.1%}' if is_number(x) else '     n/a'


def print_drivers(a):
    print('\nDRIVERS (value · source · note)')
    for k, x in a['drivers'].items():
        val = x['value']
        shown = f'{val:,.4g}' if is_number(val) else str(val)
        print(f'  {k:<18} {shown:>14}  [{x["source"]:<10}] {x["note"]}')


def print_projection(p):
    cols = ('year', 'revenue', 'growth', 'ebit_margin', 'nopat', 'da', 'capex', 'delta_nwc',
            'fcff', 'reinvestment_rate', 'roic')
    print('\nPROJECTION (USD billions; ratios in %)')
    print('  ' + ''.join(f'{c[:9]:>10}' for c in cols))
    for r in p['rows']:
        cells = []
        for c in cols:
            v = r[c]
            if c == 'year':
                cells.append(f'{v:>10}')
            elif c in ('growth', 'ebit_margin', 'reinvestment_rate', 'roic'):
                cells.append(' ' + _p(v) + ' ')
            else:
                cells.append(' ' + _b(v))
        print('  ' + ''.join(cells))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ticker')
    ap.add_argument('--wacc', type=float, required=True)
    ap.add_argument('--g', type=float, default=0.025, help='terminal growth (decimal)')
    ap.add_argument('--horizon', type=int, default=10)
    ap.add_argument('--scenario', default='all', choices=('all', 'base', 'conservative', 'optimistic'))
    ap.add_argument('--override', action='append', default=[], help='driver=value (decimal)')
    ap.add_argument('--shares', type=float, help='diluted shares (overrides SEC basic snapshot)')
    ap.add_argument('--mid-year', action='store_true')
    ap.add_argument('--no-rd', action='store_true', help='do not capitalise R&D (comparison)')
    ap.add_argument('--json', help='write full results to this file')
    args = ap.parse_args()

    overrides = {}
    for item in args.override:
        key, _, val = item.partition('=')
        overrides[key.strip()] = float(val)

    data = load_inputs(args.ticker)
    print(f"\nINTRINSIC 27 — {data['name']} ({args.ticker.upper()}) · CIK {data['cik']} · SIC {data['sic']}")
    if data['decision'].model != 'fcff':
        print(f"REFUSED: {data['decision'].category} — {data['decision'].reason}")
        return
    br = data['bridge']
    shares = args.shares or br['shares']
    print(f"Balance date {br['balance_date']} · net debt {_b(br['net_debt']).strip()}B "
          f"(debt − cash − ST investments) · shares {shares:,.0f}" if shares else 'Shares unavailable')
    if not args.shares:
        print(f"  Shares: {br['shares_source']}")
    print(f"  Debt source: {br['debt_source']}")
    for k, v in br['non_operating_assets'].items():
        print(f'  + {k} credited at book value: {v / 1e9:,.2f}B (VERIFY that its income is excluded from EBIT)')
    print('  ! Operating-lease liabilities are NOT treated as debt (consistent with EBIT after lease expense).')
    for f in data['capital_flags']:
        print('  ! ' + f)
    if br['net_debt'] is None or not shares:
        print('BLOCKED: incomplete enterprise-to-equity bridge (debt, cash, ST investments or shares).')
        return

    scenarios = ('conservative', 'base', 'optimistic') if args.scenario == 'all' else (args.scenario,)
    results = {}
    for s in scenarios:
        out = dm.run(data['history'], wacc=args.wacc, terminal_growth=args.g, net_debt=br['net_debt'],
                     shares=shares, scenario=s, horizon=args.horizon, overrides=overrides,
                     mid_year=args.mid_year, rd_life=None if args.no_rd else data['rd_life'],
                     rd_life_note=data['rd_note'])
        results[s] = out
        a = out['assumptions']
        print(f"\n=== {s.upper()} · status {out['status']} · validated={out['validated']} ===")
        for b in a['blockers']:
            print('  BLOCKER: ' + b)
        for x in a['degradations']:
            print('  degraded: ' + x)
        for x in a.get('notes', []):
            print('  note: ' + x)
        if s == 'base' or len(scenarios) == 1:
            print_drivers(a)
        if 'projection' in out and (s == 'base' or len(scenarios) == 1):
            print_projection(out['projection'])
        if 'valuation' in out:
            v = out['valuation']
            print(f"\n  EV {_b(v['enterprise_value']).strip()}B · equity {_b(v['equity_value']).strip()}B · "
                  f"intrinsic/share ${v['intrinsic_price']:,.2f} · terminal share of EV "
                  f"{v['terminal_share_of_ev']:.0%} · terminal reinvestment {v['terminal']['reinvestment_rate']:.0%} · "
                  f"RONIC {(format(v['terminal']['ronic'], '.1%') if v['terminal']['ronic'] else 'n/a')} "
                  f"({v['terminal']['mode']})")
        for c in out.get('checks', []):
            print('  check: ' + c)
        if out.get('valuation_error'):
            print('  VALUATION BLOCKED: ' + out['valuation_error'])
    if args.json:
        with open(args.json, 'w') as fh:
            json.dump({'ticker': args.ticker.upper(), 'bridge': br, 'results': results}, fh, indent=2, default=str)
        print(f'\nSaved {args.json}')


if __name__ == '__main__':
    main()
