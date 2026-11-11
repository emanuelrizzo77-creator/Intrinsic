
# INTRINSIC — SCENARIO DCF ENGINE
# Milestone 10

from assumptions_engine import (
    SCENARIOS,
    proyectar_escenario,
    obtener_base_historica
)

from copy import deepcopy


# ==========================================
# 1. VALUATION ASSUMPTIONS
# ==========================================

# Valores ilustrativos.
# Sustituiremos estos parámetros por datos
# validados del WACC y del mercado.

WACC = 0.0917
TERMINAL_GROWTH = 0.025

SHARES_OUTSTANDING = 7_426_194_552

# USD, no millones.
NET_DEBT = -36_649_000_000

MARKET_PRICE = 518.78


# ==========================================
# 2. DCF CALCULATION
# ==========================================

def calcular_dcf(
    proyeccion,
    wacc,
    terminal_growth,
    net_debt,
    shares
):
    if not proyeccion:
        raise ValueError("La proyección está vacía.")

    if wacc <= terminal_growth:
        raise ValueError(
            "WACC debe superar el crecimiento terminal."
        )

    if shares <= 0:
        raise ValueError(
            "Las acciones deben ser positivas."
        )

    pv_flows = []

    for i, fila in enumerate(proyeccion, start=1):
        fcff = fila["fcff"]
        pv = fcff / ((1 + wacc) ** i)
        pv_flows.append(pv)

    pv_fcff = sum(pv_flows)

    final_fcff = proyeccion[-1]["fcff"]

    terminal_value = (
        final_fcff * (1 + terminal_growth)
        / (wacc - terminal_growth)
    )

    pv_terminal = terminal_value / (
        (1 + wacc) ** len(proyeccion)
    )

    enterprise_value = pv_fcff + pv_terminal

    equity_value = enterprise_value - net_debt

    intrinsic_price = equity_value / shares

    return {
        "pv_fcff": pv_fcff,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "intrinsic_price": intrinsic_price
    }


# ==========================================
# 3. RUN ALL SCENARIOS
# ==========================================

def ejecutar_escenarios():
    revenue, ultimo_anio = obtener_base_historica()

    resultados = {}

    for nombre, hipotesis in SCENARIOS.items():

        forecast = proyectar_escenario(
            revenue,
            ultimo_anio,
            hipotesis
        )

        dcf = calcular_dcf(
            forecast,
            WACC,
            TERMINAL_GROWTH,
            NET_DEBT,
            SHARES_OUTSTANDING
        )

        resultados[nombre] = dcf

    return resultados


# ==========================================
# 4. SENSITIVITY ANALYSIS
# ==========================================

def matriz_sensibilidad(
    proyeccion,
    wacc_central,
    growth_central
):
    wacc_values = [
        wacc_central - 0.02,
        wacc_central - 0.01,
        wacc_central,
        wacc_central + 0.01,
        wacc_central + 0.02
    ]

    growth_values = [
        growth_central - 0.01,
        growth_central - 0.005,
        growth_central,
        growth_central + 0.005,
        growth_central + 0.01
    ]

    print("\nSENSITIVITY MATRIX — PRICE PER SHARE")
    print("Rows: WACC | Columns: Terminal Growth")
    print("-" * 78)

    print(
        f"{'WACC':<12}"
        + "".join(
            f"{g * 100:>12.2f}%"
            for g in growth_values
        )
    )

    for wacc in wacc_values:
        precios = []

        for growth in growth_values:
            if wacc <= growth:
                precios.append("N/A")
                continue

            resultado = calcular_dcf(
                proyeccion,
                wacc,
                growth,
                NET_DEBT,
                SHARES_OUTSTANDING
            )

            precios.append(
                f"${resultado['intrinsic_price']:,.2f}"
            )

        print(
            f"{wacc * 100:<12.2f}"
            + "".join(f"{p:>13}" for p in precios)
        )


# ==========================================
# 5. MAIN
# ==========================================

if __name__ == "__main__":

    resultados = ejecutar_escenarios()

    print("\nINTRINSIC — SCENARIO DCF")
    print("USD BILLIONS EXCEPT PER SHARE")
    print("=" * 78)

    for nombre, resultado in resultados.items():

        precio = resultado["intrinsic_price"]

        upside = (
            precio / MARKET_PRICE - 1
        ) * 100

        print(f"\nSCENARIO: {nombre.upper()}")

        print(
            f"Enterprise Value: "
            f"${resultado['enterprise_value'] / 1e9:,.2f} B"
        )

        print(
            f"Equity Value: "
            f"${resultado['equity_value'] / 1e9:,.2f} B"
        )

        print(
            f"Intrinsic Price: ${precio:,.2f}"
        )

        print(
            f"Market Price (Demo): ${MARKET_PRICE:,.2f}"
        )

        print(
            f"Upside / Downside: {upside:,.2f}%"
        )

    # Sensibilidad del escenario base
    revenue, ultimo_anio = obtener_base_historica()

    forecast_base = proyectar_escenario(
        revenue,
        ultimo_anio,
        SCENARIOS["base"]
    )

    matriz_sensibilidad(
        forecast_base,
        WACC,
        TERMINAL_GROWTH
    )

    print("\nINTRINSIC — MILESTONE 10 COMPLETED")
    print("PROTOTYPE — VALUATION NOT VALIDATED")
