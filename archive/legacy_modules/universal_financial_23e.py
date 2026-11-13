"""Intrinsic 23E: transparent FCFF discounted cash-flow valuation.

No market inputs are invented. A result with provisional working capital is
explicitly scenario-only, never a validated price target.
"""
from __future__ import annotations
import math
from wacc_calculator import calculate_wacc


def number(name, value, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be finite and numeric')
    value = float(value)
    if positive and value <= 0 or nonnegative and value < 0:
        raise ValueError(f'{name} outside permitted range')
    return value


def value_fcff_23e(forecast, *, wacc, terminal_growth, net_debt,
                   shares_outstanding, balance_date=None, shares_date=None,
                   market_price=None, working_capital_validated=False):
    """Discount forecast FCFF, perpetuity TV, subtract net debt, divide by shares.

    All money in USD, shares as count, rates as decimals. WACC must exceed g.
    net_debt must be a reviewed enterprise-to-equity bridge, including any
    necessary non-operating adjustments. Pass a negative value for net cash.
    """
    rate = number('wacc', wacc, positive=True)
    g = number('terminal_growth', terminal_growth)
    if not -0.1 <= g <= 0.15 or rate <= g:
        raise ValueError('Terminal growth must be within [-10%, 15%] and below WACC')
    debt = number('net_debt', net_debt)
    shares = number('shares_outstanding', shares_outstanding, positive=True)
    rows = forecast.get('rows') or []
    if not rows or len(rows) > 15:
        raise ValueError('Expected 1–15 annual FCFF forecast rows')
    if market_price is not None:
        market_price = number('market_price', market_price, positive=True)
    pv_flows = []
    for t, row in enumerate(rows, 1):
        fcff = number(f'FCFF year {t}', row.get('FCFF'))
        pv_flows.append({'year': row.get('Year', str(t)), 'fcff': fcff,
                         'discount_factor': (1 + rate) ** t,
                         'present_value': fcff / ((1 + rate) ** t)})
    final_fcff = pv_flows[-1]['fcff']
    terminal_fcff = final_fcff * (1 + g)
    terminal_value = terminal_fcff / (rate - g)
    pv_terminal = terminal_value / (1 + rate) ** len(rows)
    pv_explicit = sum(x['present_value'] for x in pv_flows)
    ev = pv_explicit + pv_terminal
    equity = ev - debt
    per_share = equity / shares
    warnings = list(forecast.get('warnings', []))
    if not working_capital_validated:
        warnings.append('PROVISIONAL: operating NWC is not fully validated; valuation is a scenario, not a defensible price target.')
    if balance_date and shares_date and balance_date != shares_date:
        warnings.append(f'Balance sheet ({balance_date}) and shares ({shares_date}) use different measurement dates.')
    warnings.append('Confirm lease treatment, non-operating assets, diluted shares, WACC inputs and normalized terminal FCFF before investment use.')
    result = {'company': forecast.get('company'), 'wacc': rate, 'terminal_growth': g,
              'pv_fcff': pv_explicit, 'terminal_fcff': terminal_fcff,
              'terminal_value': terminal_value, 'pv_terminal_value': pv_terminal,
              'enterprise_value': ev, 'net_debt': debt, 'equity_value': equity,
              'shares_outstanding': shares, 'intrinsic_value_per_share': per_share,
              'terminal_value_share_of_ev': pv_terminal / ev if ev else None,
              'discounted_flows': pv_flows, 'balance_date': balance_date,
              'shares_date': shares_date, 'working_capital_validated': bool(working_capital_validated),
              'status': 'SCENARIO_ONLY' if not working_capital_validated else 'REQUIRES_FURTHER_VALIDATION',
              'warnings': warnings}
    if market_price is not None:
        result['market_price'] = market_price
        result['upside'] = per_share / market_price - 1
    return result


def calculate_wacc_23e(*, risk_free_rate, beta, equity_risk_premium,
                       cost_of_debt, tax_rate, market_equity, total_debt):
    """Reuse Intrinsic's existing WACC calculator, no hardcoded assumptions."""
    return calculate_wacc(risk_free_rate=risk_free_rate, beta=beta,
                          equity_risk_premium=equity_risk_premium,
                          cost_of_debt=cost_of_debt, tax_rate=tax_rate,
                          market_equity=market_equity, total_debt=total_debt)


def sensitivity_23e(forecast, *, wacc_values, growth_values, net_debt,
                    shares_outstanding):
    """Return per-share scenario matrix; invalid WACC <= g cells are None."""
    table = []
    for rate in wacc_values:
        line = []
        for growth in growth_values:
            if number('wacc', rate) <= number('growth', growth):
                line.append(None)
            else:
                line.append(value_fcff_23e(forecast, wacc=rate,
                    terminal_growth=growth, net_debt=net_debt,
                    shares_outstanding=shares_outstanding)['intrinsic_value_per_share'])
        table.append(line)
    return table
