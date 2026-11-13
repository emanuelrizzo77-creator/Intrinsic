
# INTRINSIC — WACC ENGINE
# Milestone 05
# Modelo inicial con hipótesis editables


# ==========================================
# 1. HIPÓTESIS FINANCIERAS
# ==========================================

# Risk-free rate: rendimiento de un bono del Tesoro
RISK_FREE_RATE = 0.04

# Beta: sensibilidad de la acción al mercado
BETA = 1.10

# Rentabilidad esperada del mercado
MARKET_RETURN = 0.09

# Coste de la deuda antes de impuestos
COST_OF_DEBT = 0.05

# Tasa impositiva marginal
TAX_RATE = 0.21

# Valores de mercado hipotéticos (USD millones)
EQUITY_VALUE = 3_000_000
DEBT_VALUE = 100_000


# ==========================================
# 2. COST OF EQUITY — CAPM
# ==========================================

def calcular_cost_of_equity(rf, beta, rm):
    return rf + beta * (rm - rf)


# ==========================================
# 3. COST OF DEBT AFTER TAX
# ==========================================

def calcular_cost_of_debt_after_tax(kd, tax):
    return kd * (1 - tax)


# ==========================================
# 4. CAPITAL STRUCTURE
# ==========================================

def calcular_pesos(equity, debt):
    if equity < 0 or debt < 0:
        raise ValueError(
            "Equity y deuda no pueden ser negativos."
        )

    total = equity + debt

    if total <= 0:
        raise ValueError(
            "El capital total debe ser positivo."
        )

    peso_equity = equity / total
    peso_deuda = debt / total

    return peso_equity, peso_deuda


# ==========================================
# 5. WACC
# ==========================================

def calcular_wacc(
    rf,
    beta,
    rm,
    kd,
    tax,
    equity,
    debt
):
    if not 0 <= tax <= 1:
        raise ValueError(
            "La tasa impositiva debe estar entre 0 y 1."
        )

    if rf < 0 or rm < 0 or kd < 0:
        raise ValueError(
            "Las tasas no pueden ser negativas "
            "en este modelo inicial."
        )

    if beta < 0:
        raise ValueError(
            "Beta debe ser no negativa "
            "en este modelo inicial."
        )

    ke = calcular_cost_of_equity(rf, beta, rm)

    kd_after_tax = calcular_cost_of_debt_after_tax(
        kd, tax
    )

    peso_e, peso_d = calcular_pesos(
        equity, debt
    )

    wacc = (
        peso_e * ke
        + peso_d * kd_after_tax
    )

    return {
        "cost_of_equity": ke,
        "cost_of_debt_after_tax": kd_after_tax,
        "equity_weight": peso_e,
        "debt_weight": peso_d,
        "wacc": wacc
    }


# ==========================================
# 6. MOSTRAR RESULTADOS
# ==========================================

def mostrar_resultados(resultados):
    print("\nINTRINSIC — WACC ANALYSIS")
    print("-" * 45)

    print(
        f"Risk-Free Rate:       {RISK_FREE_RATE:.2%}"
    )
    print(
        f"Beta:                 {BETA:.2f}"
    )
    print(
        f"Market Return:        {MARKET_RETURN:.2%}"
    )

    print("-" * 45)

    print(
        f"Cost of Equity:       "
        f"{resultados['cost_of_equity']:.2%}"
    )
    print(
        f"After-Tax Debt Cost:  "
        f"{resultados['cost_of_debt_after_tax']:.2%}"
    )
    print(
        f"Equity Weight:        "
        f"{resultados['equity_weight']:.2%}"
    )
    print(
        f"Debt Weight:          "
        f"{resultados['debt_weight']:.2%}"
    )

    print("-" * 45)

    print(
        f"WACC:                 "
        f"{resultados['wacc']:.2%}"
    )

    print("-" * 45)


# ==========================================
# 7. EJECUTAR
# ==========================================

if __name__ == "__main__":

    resultados = calcular_wacc(
        RISK_FREE_RATE,
        BETA,
        MARKET_RETURN,
        COST_OF_DEBT,
        TAX_RATE,
        EQUITY_VALUE,
        DEBT_VALUE
    )

    mostrar_resultados(resultados)
