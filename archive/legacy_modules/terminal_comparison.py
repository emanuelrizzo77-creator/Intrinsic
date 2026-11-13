
from copy import deepcopy

from assumptions_engine import SCENARIOS, proyectar_escenario
from scenario_dcf import calcular_dcf
from terminal_normalization import calcular_fcff_terminal_normalizado


REVENUE_2026 = 331_839_000_000
WACC = 0.0917
G = 0.025
NET_DEBT = -36_549_000_000
SHARES = 7_426_194_552

# Supuestos ilustrativos, todavía no calibrados.
TERMINAL = {
    "ebit_margin": 0.45,
    "tax_rate": 0.21,
    "da_ratio": 0.11,
    "capex_ratio": 0.23,
    "nwc_ratio": 0.03,
}


def comparar():
    base = deepcopy(SCENARIOS["base"])
    elevado = deepcopy(base)
    elevado["capex_ratio"] = [
        0.35, 0.33, 0.30, 0.28, 0.26
    ]

    resultados = {}

    for nombre, hipotesis in {
        "BASE": base,
        "HIGH CAPEX": elevado,
    }.items():

        forecast = proyectar_escenario(
            REVENUE_2026, 2026, hipotesis
        )

        dcf_actual = calcular_dcf(
            forecast, WACC, G, NET_DEBT, SHARES
        )

        terminal = calcular_fcff_terminal_normalizado(
            revenue_final=forecast[-1]["revenue"],
            terminal_growth=G,
            **TERMINAL,
        )

        fcff_2032 = terminal["fcff_terminal"]

        tv_normalizado = fcff_2032 / (WACC - G)

        pv_terminal_normalizado = (
            tv_normalizado / (1 + WACC) ** len(forecast)
        )

        ev_normalizado = (
            dcf_actual["pv_fcff"]
            + pv_terminal_normalizado
        )

        equity_normalizado = ev_normalizado - NET_DEBT
        precio_normalizado = equity_normalizado / SHARES

        resultados[nombre] = {
            "actual": dcf_actual["intrinsic_price"],
            "normalizado": precio_normalizado,
            "pv_fcff": dcf_actual["pv_fcff"],
            "pv_terminal_normalizado": pv_terminal_normalizado,
        }

    print("\nINTRINSIC — TERMINAL VALUE COMPARISON")
    print("=" * 70)

    for nombre, resultado in resultados.items():
        print(f"\n{nombre}")
        print(f"Current DCF: ${resultado['actual']:,.2f}")
        print(
            f"Normalized DCF: "
            f"${resultado['normalizado']:,.2f}"
        )

    print("\nCAPEX SENSITIVITY")
    print("-" * 70)

    diferencia_actual = (
        resultados["BASE"]["actual"]
        - resultados["HIGH CAPEX"]["actual"]
    )

    diferencia_normalizada = (
        resultados["BASE"]["normalizado"]
        - resultados["HIGH CAPEX"]["normalizado"]
    )

    print(
        f"Current Price Difference: "
        f"${diferencia_actual:,.2f}"
    )

    print(
        f"Normalized Price Difference: "
        f"${diferencia_normalizada:,.2f}"
    )

    print(
        f"Reduction in Sensitivity: "
        f"{(1 - diferencia_normalizada / diferencia_actual) * 100:,.2f}%"
    )


if __name__ == "__main__":
    comparar()
