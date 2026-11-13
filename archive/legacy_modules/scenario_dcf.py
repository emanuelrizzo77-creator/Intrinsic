"""INTRINSIC — Milestone 19: validated DCF mathematics.

Backward-compatible with Milestone 10's calcular_dcf and matriz_sensibilidad.
The legacy CLI uses illustrative constants; the multi-company dashboard should
pass its own company-specific WACC, net debt, shares and market price.
"""
from __future__ import annotations

import math
from numbers import Real

from assumptions_engine import SCENARIOS, proyectar_escenario, obtener_base_historica

WACC = 0.0917
TERMINAL_GROWTH = 0.025
SHARES_OUTSTANDING = 7_426_194_552
NET_DEBT = -36_649_000_000
MARKET_PRICE = 518.78


def _number(name, value):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} debe ser un número real finito")
    return float(value)


def calcular_dcf(proyeccion, wacc, terminal_growth, net_debt, shares):
    if not proyeccion:
        raise ValueError("La proyección está vacía")
    wacc = _number("WACC", wacc)
    terminal_growth = _number("terminal_growth", terminal_growth)
    net_debt = _number("net_debt", net_debt)
    shares = _number("shares", shares)
    if wacc <= -1:
        raise ValueError("WACC debe ser mayor que -100%")
    if terminal_growth <= -1:
        raise ValueError("Crecimiento terminal debe ser mayor que -100%")
    if wacc <= terminal_growth:
        raise ValueError("WACC debe superar el crecimiento terminal")
    if shares <= 0:
        raise ValueError("Las acciones deben ser positivas")

    pv_flows = []
    for i, fila in enumerate(proyeccion, start=1):
        if not isinstance(fila, dict) or "fcff" not in fila:
            raise ValueError(f"FCFF ausente en año {i}")
        fcff = _number(f"FCFF año {i}", fila["fcff"])
        pv = fcff / ((1 + wacc) ** i)
        if not math.isfinite(pv):
            raise ValueError(f"PV de FCFF no finito en año {i}")
        pv_flows.append(pv)

    pv_fcff = sum(pv_flows)
    final_fcff = _number("FCFF final", proyeccion[-1]["fcff"])
    terminal_value = final_fcff * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** len(proyeccion))
    enterprise_value = pv_fcff + pv_terminal
    equity_value = enterprise_value - net_debt
    intrinsic_price = equity_value / shares
    if not all(math.isfinite(x) for x in (
        pv_fcff, terminal_value, pv_terminal, enterprise_value,
        equity_value, intrinsic_price
    )):
        raise ValueError("Resultado DCF no finito")
    return {
        "pv_fcff": pv_fcff,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "intrinsic_price": intrinsic_price,
    }


def ejecutar_escenarios():
    """Legacy illustrative scenario runner; dashboard uses company-specific inputs."""
    revenue, ultimo_anio = obtener_base_historica()
    return {
        nombre: calcular_dcf(
            proyectar_escenario(revenue, ultimo_anio, hipotesis),
            WACC, TERMINAL_GROWTH, NET_DEBT, SHARES_OUTSTANDING,
        )
        for nombre, hipotesis in SCENARIOS.items()
    }


def calcular_matriz_sensibilidad(
    proyeccion, wacc_central, growth_central,
    net_debt=NET_DEBT, shares=SHARES_OUTSTANDING,
):
    """Return structured sensitivity values; invalid WACC/growth cells are None.

    Pass company-specific net_debt and shares for any non-demo valuation.
    """
    wacc_central = _number("wacc_central", wacc_central)
    growth_central = _number("growth_central", growth_central)
    wacc_values = [wacc_central + offset for offset in (-.02, -.01, 0, .01, .02)]
    growth_values = [growth_central + offset for offset in (-.01, -.005, 0, .005, .01)]
    values = []
    for wacc in wacc_values:
        row = []
        for growth in growth_values:
            if wacc <= growth or wacc <= -1 or growth <= -1:
                row.append(None)
            else:
                row.append(calcular_dcf(proyeccion, wacc, growth, net_debt, shares)["intrinsic_price"])
        values.append(row)
    return {"wacc_values": wacc_values, "growth_values": growth_values, "prices": values}


def matriz_sensibilidad(proyeccion, wacc_central, growth_central,
                        net_debt=NET_DEBT, shares=SHARES_OUTSTANDING):
    """Print legacy matrix and also return structured results."""
    matrix = calcular_matriz_sensibilidad(
        proyeccion, wacc_central, growth_central, net_debt, shares
    )
    print("\nSENSITIVITY MATRIX — PRICE PER SHARE")
    print("Rows: WACC | Columns: Terminal Growth")
    print(f"{'WACC':<12}" + "".join(f"{g * 100:>12.2f}%" for g in matrix["growth_values"]))
    for wacc, prices in zip(matrix["wacc_values"], matrix["prices"]):
        print(f"{wacc * 100:<12.2f}" + "".join(
            f"{('$' + format(p, ',.2f')) if p is not None else 'N/A':>13}" for p in prices
        ))
    return matrix


if __name__ == "__main__":
    resultados = ejecutar_escenarios()
    print("\nINTRINSIC — SCENARIO DCF (ILLUSTRATIVE LEGACY CLI)")
    for nombre, resultado in resultados.items():
        precio = resultado["intrinsic_price"]
        upside = (precio / MARKET_PRICE - 1) * 100
        print(f"\nSCENARIO: {nombre.upper()}")
        print(f"Enterprise Value: ${resultado['enterprise_value'] / 1e9:,.2f} B")
        print(f"Equity Value: ${resultado['equity_value'] / 1e9:,.2f} B")
        print(f"Intrinsic Price: ${precio:,.2f}")
        print(f"Market Price (Demo): ${MARKET_PRICE:,.2f}")
        print(f"Upside / Downside: {upside:,.2f}%")
    revenue, ultimo_anio = obtener_base_historica()
    forecast_base = proyectar_escenario(revenue, ultimo_anio, SCENARIOS["base"])
    matriz_sensibilidad(forecast_base, WACC, TERMINAL_GROWTH)
    print("\nPROTOTYPE — VALUATION NOT VALIDATED")
