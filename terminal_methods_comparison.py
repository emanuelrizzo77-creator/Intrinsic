
from assumptions_engine import (
    SCENARIOS,
    proyectar_escenario,
)

from scenario_dcf import calcular_dcf

from terminal_normalization import (
    calcular_fcff_terminal_normalizado,
)

from terminal_roic_model import (
    calcular_terminal_roic,
)


REVENUE_2026 = 331_839_000_000
NET_DEBT = -36_549_000_000
SHARES = 7_426_194_552

WACC = 0.0917
G = 0.025

TERMINAL = {
    "ebit_margin": 0.45,
    "tax_rate": 0.21,
    "da_ratio": 0.11,
    "capex_ratio": 0.23,
    "nwc_ratio": 0.03,
}


def comparar_metodos():

    forecast = proyectar_escenario(
        REVENUE_2026,
        2026,
        SCENARIOS["base"],
    )

    dcf_actual = calcular_dcf(
        forecast,
        WACC,
        G,
        NET_DEBT,
        SHARES,
    )

    pv_fcff = dcf_actual["pv_fcff"]
    n = len(forecast)

    # Método 1: Gordon Growth tradicional
    precio_tradicional = dcf_actual["intrinsic_price"]

    # Método 2: FCFF terminal normalizado
    normalizado = calcular_fcff_terminal_normalizado(
        revenue_final=forecast[-1]["revenue"],
        terminal_growth=G,
        **TERMINAL,
    )

    pv_terminal_normalizado = (
        normalizado["fcff_terminal"]
        / (WACC - G)
        / (1 + WACC) ** n
    )

    precio_normalizado = (
        pv_fcff
        + pv_terminal_normalizado
        - NET_DEBT
    ) / SHARES

    # Método 3: Terminal basado en ROIC
    nopat_terminal = normalizado["nopat_terminal"]

    resultados_roic = {}

    for roic in [0.10, 0.15, 0.20, 0.25]:

        resultado = calcular_terminal_roic(
            nopat_terminal=nopat_terminal,
            terminal_growth=G,
            roic=roic,
            wacc=WACC,
            forecast_years=n,
        )

        precio = (
            pv_fcff
            + resultado["pv_terminal"]
            - NET_DEBT
        ) / SHARES

        resultados_roic[roic] = {
            "precio": precio,
            "reinvestment_rate": resultado[
                "reinvestment_rate"
            ],
        }

    print("\nINTRINSIC — TERMINAL METHODS")
    print("=" * 65)

    print(
        f"Gordon Growth: "
        f"${precio_tradicional:,.2f}"
    )

    print(
        f"Normalized FCFF: "
        f"${precio_normalizado:,.2f}"
    )

    print("\nROIC-BASED TERMINAL")
    print("-" * 65)

    for roic, resultado in resultados_roic.items():
        print(
            f"ROIC {roic * 100:.0f}% | "
            f"Reinvestment "
            f"{resultado['reinvestment_rate'] * 100:.2f}% | "
            f"Price ${resultado['precio']:,.2f}"
        )

    return {
        "traditional": precio_tradicional,
        "normalized": precio_normalizado,
        "roic": resultados_roic,
    }


if __name__ == "__main__":
    comparar_metodos()
