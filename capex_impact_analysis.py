
from copy import deepcopy

from assumptions_engine import (
    SCENARIOS,
    proyectar_escenario,
)

from scenario_dcf import calcular_dcf


REVENUE_2026 = 331_839_000_000
WACC = 0.0917
TERMINAL_GROWTH = 0.025
NET_DEBT = -36_549_000_000
SHARES = 7_426_194_552


def analizar_capex():

    base = deepcopy(SCENARIOS["base"])
    elevado = deepcopy(base)

    elevado["capex_ratio"] = [
        0.35, 0.33, 0.30, 0.28, 0.26
    ]

    escenarios = {
        "BASE": base,
        "HIGH CAPEX": elevado,
    }

    resultados = {}

    for nombre, hipotesis in escenarios.items():

        forecast = proyectar_escenario(
            REVENUE_2026,
            2026,
            hipotesis,
        )

        dcf = calcular_dcf(
            forecast,
            WACC,
            TERMINAL_GROWTH,
            NET_DEBT,
            SHARES,
        )

        resultados[nombre] = {
            "forecast": forecast,
            "dcf": dcf,
        }

    print("\nINTRINSIC — CAPEX IMPACT ANALYSIS")
    print("=" * 65)

    for nombre, resultado in resultados.items():

        dcf = resultado["dcf"]

        print(f"\nSCENARIO: {nombre}")
        print(
            f"Enterprise Value: "
            f"${dcf['enterprise_value']/1e9:,.2f} B"
        )
        print(
            f"Equity Value: "
            f"${dcf['equity_value']/1e9:,.2f} B"
        )
        print(
            f"Intrinsic Price: "
            f"${dcf['intrinsic_price']:,.2f}"
        )

    precio_base = resultados["BASE"]["dcf"][
        "intrinsic_price"
    ]

    precio_elevado = resultados["HIGH CAPEX"]["dcf"][
        "intrinsic_price"
    ]

    diferencia = precio_base - precio_elevado

    base_dcf = resultados["BASE"]["dcf"]
    high_dcf = resultados["HIGH CAPEX"]["dcf"]

    impacto_fcff = (
        base_dcf["pv_fcff"] - high_dcf["pv_fcff"]
    )

    impacto_terminal = (
        base_dcf["pv_terminal"] - high_dcf["pv_terminal"]
    )

    impacto_total = impacto_fcff + impacto_terminal

    print("\nCAPEX IMPACT DECOMPOSITION")
    print("-" * 65)

    print(
        f"Explicit Period Impact: "
        f"${impacto_fcff / 1e9:,.2f} B"
    )

    print(
        f"Terminal Value Impact: "
        f"${impacto_terminal / 1e9:,.2f} B"
    )

    print(
        f"Total Enterprise Value Impact: "
        f"${impacto_total / 1e9:,.2f} B"
    )

    print(
        f"Terminal Contribution: "
        f"{impacto_terminal / impacto_total * 100:,.2f}%"
    )


    print("\n" + "-" * 65)
    print(f"Price Difference: ${diferencia:,.2f}")

    print(
        "Reduction vs Base: "
        f"{diferencia/precio_base*100:,.2f}%"
    )

    return resultados


if __name__ == "__main__":
    analizar_capex()
