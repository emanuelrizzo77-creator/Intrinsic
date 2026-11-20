"""Reverse DCF on real companies with the dashboard's default inputs.

  python validation/reverse_dcf_check.py MSFT AAPL GOOGL AMZN AMD   # writes validation/results/reverse_dcf.json

WACC is rebuilt exactly as the dashboard's default: live 10-year Treasury, Damodaran implied ERP, industry
(bottom-up) beta relevered at market D/E, synthetic-rating cost of debt, 25% marginal tax, market-value weights.
Market price and share count are Yahoo Finance at run time (dated in the output). Nothing is adjusted.
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from datetime import datetime, timezone

warnings.filterwarnings('ignore')
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from intrinsic import forecast as dm  # noqa: E402
from intrinsic import reverse_dcf as rv  # noqa: E402
from intrinsic.industry_beta import bottom_up_beta  # noqa: E402
from intrinsic.inputs import load_inputs  # noqa: E402
from intrinsic.market_reference import obtener_referencia_mercado  # noqa: E402
from intrinsic.wacc_calculator import calculate_wacc  # noqa: E402
from intrinsic.wacc_data import obtener_datos_wacc  # noqa: E402
from intrinsic.wacc_inputs import MARGINAL_TAX, cost_of_debt, equity_risk_premium, risk_free_rate  # noqa: E402

TERMINAL_GROWTH = 0.025


def dashboard_wacc(ticker, sic, rf, erp):
    w = obtener_datos_wacc(ticker)
    bu = bottom_up_beta(sic, market_equity=w['market_equity'], total_debt=w['total_debt'])
    beta = bu['beta'] if bu.get('beta') is not None else w['beta_adjusted']
    cov = w.get('interest_coverage')
    kd = cost_of_debt(rf, cov['coverage'] if cov else None)[0]
    kd = kd if kd is not None else rf + 0.0111
    res = calculate_wacc(risk_free_rate=rf, beta=beta, equity_risk_premium=erp, cost_of_debt=kd,
                         tax_rate=MARGINAL_TAX, market_equity=w['market_equity'], total_debt=w['total_debt'])
    return res['wacc'], beta


def check(ticker, rf, erp):
    data = load_inputs(ticker)
    ref = obtener_referencia_mercado(ticker)
    price, market_shares = ref['market_price'], ref.get('shares_outstanding')
    br = data['bridge']
    shares = br['shares'] or market_shares
    wacc, beta = dashboard_wacc(ticker, data['sic'], rf, erp)
    res = dm.run(data['history'], wacc=wacc, terminal_growth=TERMINAL_GROWTH, net_debt=br['net_debt'], shares=shares,
                 rd_life=data['rd_life'], rd_life_note=data['rd_note'], industry_margin=data.get('industry_margin'))
    d = res['assumptions']['drivers']
    out = rv.run_all(res, price, net_debt=br['net_debt'], shares=shares, risk_free_rate=rf)
    paths = rv.growth_paths(res, out['growth'])
    rows = res['projection']['rows']
    r0 = d['revenue0']['value']

    def summary(m):
        o = out[m]
        row = {k: o.get(k) for k in ('status', 'root', 'roots', 'residual', 'iterations', 'monotone', 'reason', 'bounds')}
        return {**row, 'warnings': [rv.warning_text(c, p) for c, p in o.get('warnings', [])]}
    return {
        'ticker': ticker, 'price': price, 'price_time': ref.get('retrieved_at') or ref.get('price_date'),
        'intrinsic_value': res['valuation']['intrinsic_price'], 'wacc': wacc, 'beta': beta, 'risk_free_rate': rf,
        'terminal_growth': TERMINAL_GROWTH,
        'margin_latest': d['margin_start']['value'], 'margin_target': d['margin_target']['value'],
        'margin_final_year': rows[-1]['ebita_margin'],
        'growth_path': paths['growth'], 'implied_growth_path': paths.get('implied_growth'),
        'revenue_cagr_10y': rv.cagr(r0, paths['revenue'][-1], len(rows)),
        'implied_revenue_cagr_10y': rv.cagr(r0, paths['implied_revenue'][-1], len(rows)) if paths.get('implied_revenue') else None,
        'growth': summary('growth'), 'margin': summary('margin'), 'wacc_mode': summary('wacc'),
    }


def main(tickers):
    rf, erp = risk_free_rate()[0], equity_risk_premium()[0]
    results = []
    for tk in tickers:
        try:
            results.append(check(tk, rf, erp))
        except Exception as exc:                      # report, never hide
            results.append({'ticker': tk, 'error': f'{type(exc).__name__}: {exc}'})
    path = os.path.join(_ROOT, 'validation', 'results', 'reverse_dcf.json')
    with open(path, 'w') as fh:
        json.dump({'run_utc': datetime.now(timezone.utc).isoformat(), 'results': results}, fh, indent=1, default=str)
    for r in results:
        if 'error' in r:
            print(r['ticker'], 'ERROR', r['error'])
            continue
        g, m, w = r['growth'], r['margin'], r['wacc_mode']
        fmt = lambda o, f: f(o['root']) if o['status'] == 'solved' else o['status']
        print(f"{r['ticker']:5} price {r['price']:8.2f}  value {r['intrinsic_value']:8.2f}  WACC {r['wacc']:.2%} -> "
              f"implied {fmt(w, lambda x: f'{x:.2%}')}  | growth premium {fmt(g, lambda x: f'{x * 100:+.1f} pp')} "
              f"(10y CAGR {r['revenue_cagr_10y']:.1%} -> {r['implied_revenue_cagr_10y'] or float('nan'):.1%})  | margin "
              f"latest {r['margin_latest']:.1%} target {r['margin_target']:.1%} -> {fmt(m, lambda x: f'{x:.1%}')}")
        for k in ('growth', 'margin', 'wacc_mode'):
            o = r[k]
            print(f"      {k:9} status={o['status']} residual={o['residual']} iters={o['iterations']} "
                  f"monotone={o['monotone']} reason={o['reason']} warnings={o['warnings']}")
    print(f'\nSaved {path}')


if __name__ == '__main__':
    main(sys.argv[1:] or ['MSFT', 'AAPL', 'GOOGL', 'AMZN', 'AMD'])
