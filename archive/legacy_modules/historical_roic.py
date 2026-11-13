
# INTRINSIC — HISTORICAL ROIC ENGINE
# Milestone 12 — Invested Capital Reconciliation
from financial_engine import (
    descargar_datos,
    extraer_metrica,
    METRICAS,
)
from market_data import obtener_balance_historico_sec

TAX_RATE = 0.21

# Valores históricos auditados contra el 10-K.
# USD billions.
BALANCES = {
    2025: {
        "equity": 343.479,
        "long_term_debt": 40.152,
        "current_debt": 2.999,
        "cash": 30.242,
        "short_term_investments": 64.323,
        "finance_leases": 46.172,
        "operating_leases": 22.861,
    },
    2026: {
        "equity": 442.387,
        "long_term_debt": 31.067,
        "current_debt": 9.227,
        "cash": 20.935,
        "short_term_investments": 55.908,
        "finance_leases": 66.594,
        "operating_leases": 21.925,
    },
}

EBIT_2026 = 155.237


def calcular_capital_invertido(balance):
    deuda = (
        balance["long_term_debt"]
        + balance["current_debt"]
    )

    liquidez = (
        balance["cash"]
        + balance["short_term_investments"]
    )

    convencional = (
        balance["equity"]
        + deuda
        - liquidez
    )

    con_finance_leases = (
        convencional
        + balance["finance_leases"]
    )

    con_todos_leases = (
        con_finance_leases
        + balance["operating_leases"]
    )

    return {
        "conventional": convencional,
        "finance_leases": con_finance_leases,
        "all_leases": con_todos_leases,
    }

def calcular_capital_operativo_ajustado(
    capital_invertido,
    inversiones_no_operativas,
):
    """
    Calcula capital invertido ajustado.

    Supuesto:
    Se excluye la totalidad de LongTermInvestments.

    Ambas cantidades deben expresarse en USD B.
    """

    if inversiones_no_operativas < 0:
        raise ValueError(
            "Non-operating investments cannot be negative"
        )

    capital_ajustado = (
        capital_invertido
        - inversiones_no_operativas
    )

    if capital_ajustado <= 0:
        raise ValueError(
            "Adjusted invested capital must be positive"
        )

    return capital_ajustado



def calcular_roic(nopat, capital_promedio):
    if capital_promedio <= 0:
        raise ValueError(
            "Average invested capital must be positive."
        )

    return nopat / capital_promedio

def obtener_balances_automaticos():
    """
    Descarga los balances FY2025 y FY2026 desde SEC.

    Convierte USD a miles de millones de USD
    para mantener las unidades del motor ROIC.
    """

    datos = descargar_datos()

    fechas = {
        2025: "2025-06-30",
        2026: "2026-06-30",
    }

    equivalencias = {
        "equity": "Equity",
        "long_term_debt": "Long Term Debt",
        "current_debt": "Current Debt",
        "cash": "Cash",
        "short_term_investments": "Short Term Investments",
        "finance_leases": "Finance Leases",
        "operating_leases": "Operating Leases",
        "long_term_investments": "Long Term Investments",
    }

    balances = {}

    for anio, fecha in fechas.items():
        registros = obtener_balance_historico_sec(
            datos,
            fecha,
        )

        balances[anio] = {
            clave: registros[etiqueta]["value"] / 1e9
            for clave, etiqueta in equivalencias.items()
        }

        ebit_historico = extraer_metrica(
        datos,
        METRICAS["EBIT"],
    )

    if 2026 not in ebit_historico:
        raise ValueError(
            "SEC EBIT FY2026 not available"
        )

    return {
        "balances": balances,
        "ebit_2026": ebit_historico[2026] / 1e9,
    }

    


def ejecutar_analisis():
    datos_sec = obtener_balances_automaticos()

    balances = datos_sec["balances"]
    ebit_2026 = datos_sec["ebit_2026"]

    capital_2025 = calcular_capital_invertido(
        balances[2025]
    )

    capital_2026 = calcular_capital_invertido(
        balances[2026]
    )

    nopat = ebit_2026 * (1 - TAX_RATE)

    print("\nINTRINSIC — HISTORICAL ROIC")
    print("=" * 72)
    print(f"EBIT FY2026: ${ebit_2026:.3f} B")
    print(f"Tax Rate: {TAX_RATE:.2%}")
    print(f"NOPAT FY2026: ${nopat:.3f} B")

    print("\nINVESTED CAPITAL COMPARISON")
    print("-" * 72)

    nombres = {
        "conventional": "Conventional",
        "finance_leases": "Including Finance Leases",
        "all_leases": "Including All Leases",
    }

    resultados = {}

    for clave, nombre in nombres.items():
        ic_2025 = capital_2025[clave]
        ic_2026 = capital_2026[clave]

        promedio = (ic_2025 + ic_2026) / 2
        roic = calcular_roic(nopat, promedio)

        resultados[clave] = {
            "ic_2025": ic_2025,
            "ic_2026": ic_2026,
            "average_ic": promedio,
            "roic": roic,
        }

        print(f"\n{nombre}")
        print(f"IC FY2025: ${ic_2025:.3f} B")
        print(f"IC FY2026: ${ic_2026:.3f} B")
        print(f"Average IC: ${promedio:.3f} B")
        print(f"ROIC FY2026: {roic:.2%}")

    # ==========================================
    # ADJUSTED OPERATING CAPITAL
    # ==========================================
    # Supuesto ilustrativo:
    # Se excluye el 100% de LongTermInvestments.
    # No representa aún el ROIC definitivo.

    ic_ajustado_2025 = calcular_capital_operativo_ajustado(
        capital_2025["finance_leases"],
        balances[2025]["long_term_investments"],
    )

    ic_ajustado_2026 = calcular_capital_operativo_ajustado(
        capital_2026["finance_leases"],
        balances[2026]["long_term_investments"],
    )

    ic_promedio_ajustado = (
        ic_ajustado_2025
        + ic_ajustado_2026
    ) / 2

    roic_ajustado = calcular_roic(
        nopat,
        ic_promedio_ajustado,
    )

    resultados["adjusted_operating_capital"] = {
        "ic_2025": ic_ajustado_2025,
        "ic_2026": ic_ajustado_2026,
        "average_ic": ic_promedio_ajustado,
        "roic": roic_ajustado,
    }

    print("\nADJUSTED OPERATING CAPITAL — ILLUSTRATIVE")
    print("-" * 72)
    print(f"IC FY2025: ${ic_ajustado_2025:.3f} B")
    print(f"IC FY2026: ${ic_ajustado_2026:.3f} B")
    print(f"Average IC: ${ic_promedio_ajustado:.3f} B")
    print(f"Adjusted ROIC: {roic_ajustado:.2%}")

    return resultados


if __name__ == "__main__":
    ejecutar_analisis()
