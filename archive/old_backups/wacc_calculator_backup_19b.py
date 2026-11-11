
# INTRINSIC — DYNAMIC WACC CALCULATOR
# Milestone 12

def calculate_cost_of_equity(
    risk_free_rate,
    beta,
    equity_risk_premium
):
    """
    CAPM:
    Ke = Rf + Beta * ERP

    Rates must be expressed as decimals.
    Example: 4% = 0.04
    """

    if risk_free_rate < 0:
        raise ValueError("Risk-free rate cannot be negative.")

    if beta < 0:
        raise ValueError("Beta cannot be negative.")

    if equity_risk_premium < 0:
        raise ValueError(
            "Equity risk premium cannot be negative."
        )

    return risk_free_rate + beta * equity_risk_premium


def calculate_wacc(
    risk_free_rate,
    beta,
    equity_risk_premium,
    cost_of_debt,
    tax_rate,
    market_equity,
    total_debt
):
    """
    Calculates WACC using market-value weights.

    All rates are decimals.
    Equity and debt must use the same currency and units.
    """

    if cost_of_debt < 0:
        raise ValueError("Cost of debt cannot be negative.")

    if not 0 <= tax_rate <= 1:
        raise ValueError("Tax rate must be between 0 and 1.")

    if market_equity <= 0:
        raise ValueError("Market equity must be positive.")

    if total_debt < 0:
        raise ValueError("Total debt cannot be negative.")

    cost_of_equity = calculate_cost_of_equity(
        risk_free_rate,
        beta,
        equity_risk_premium
    )

    total_capital = market_equity + total_debt

    equity_weight = market_equity / total_capital
    debt_weight = total_debt / total_capital

    after_tax_cost_of_debt = (
        cost_of_debt * (1 - tax_rate)
    )

    wacc = (
        equity_weight * cost_of_equity
        + debt_weight * after_tax_cost_of_debt
    )

    return {
        "wacc": wacc,
        "cost_of_equity": cost_of_equity,
        "after_tax_cost_of_debt": after_tax_cost_of_debt,
        "equity_weight": equity_weight,
        "debt_weight": debt_weight,
    }


if __name__ == "__main__":

    result = calculate_wacc(
        risk_free_rate=0.04,
        beta=1.04,
        equity_risk_premium=0.05,
        cost_of_debt=0.05,
        tax_rate=0.21,
        market_equity=3_852_635_209_728,
        total_debt=40_294_000_000
    )

    print("\nINTRINSIC — DYNAMIC WACC")
    print("-" * 45)

    for key, value in result.items():
        print(f"{key}: {value:.2%}")
