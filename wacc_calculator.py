"""INTRINSIC — Dynamic WACC calculator, Milestone 19B.

Pure arithmetic. Market debt is approximated by reported SEC book debt upstream.
All rates are decimals, capital amounts share units/currency.
"""

import math


def _finite_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number.")
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise ValueError(f"{name} must be a finite number.") from None
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number.")
    return number


def calculate_cost_of_equity(risk_free_rate, beta, equity_risk_premium):
    """CAPM: Ke = Rf + beta * ERP."""
    rf = _finite_number("risk_free_rate", risk_free_rate)
    b = _finite_number("beta", beta)
    erp = _finite_number("equity_risk_premium", equity_risk_premium)
    if rf < 0 or b < 0 or erp < 0:
        raise ValueError("Risk-free rate, beta and equity risk premium cannot be negative.")
    ke = rf + b * erp
    if not math.isfinite(ke):
        raise ValueError("Calculated cost of equity is not finite.")
    return ke


def calculate_wacc(risk_free_rate, beta, equity_risk_premium,
                   cost_of_debt, tax_rate, market_equity, total_debt):
    """WACC with equity at market value and debt at upstream supplied value."""
    kd = _finite_number("cost_of_debt", cost_of_debt)
    tax = _finite_number("tax_rate", tax_rate)
    equity = _finite_number("market_equity", market_equity)
    debt = _finite_number("total_debt", total_debt)
    if kd < 0:
        raise ValueError("Cost of debt cannot be negative.")
    if not 0 <= tax <= 1:
        raise ValueError("Tax rate must be between 0 and 1.")
    if equity <= 0:
        raise ValueError("Market equity must be positive.")
    if debt < 0:
        raise ValueError("Total debt cannot be negative.")
    ke = calculate_cost_of_equity(risk_free_rate, beta, equity_risk_premium)
    capital = equity + debt
    if not math.isfinite(capital):
        raise ValueError("Total capital is not finite.")
    ew, dw = equity / capital, debt / capital
    after_tax_kd = kd * (1 - tax)
    wacc = ew * ke + dw * after_tax_kd
    if not all(math.isfinite(v) for v in (after_tax_kd, wacc)):
        raise ValueError("Calculated WACC is not finite.")
    return {
        "wacc": wacc,
        "cost_of_equity": ke,
        "after_tax_cost_of_debt": after_tax_kd,
        "equity_weight": ew,
        "debt_weight": dw,
    }


if __name__ == "__main__":
    result = calculate_wacc(
        risk_free_rate=0.04, beta=1.04, equity_risk_premium=0.05,
        cost_of_debt=0.05, tax_rate=0.21,
        market_equity=3_852_635_209_728, total_debt=40_294_000_000,
    )
    print("\nINTRINSIC — DYNAMIC WACC")
    print("-" * 45)
    for key, value in result.items():
        print(f"{key}: {value:.2%}")
