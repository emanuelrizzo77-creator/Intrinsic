
# INTRINSIC — DCF VALUATION ENGINE
# Milestone 06

from financial_engine import (
    descargar_datos,
    construir_tabla
)

from forecast_engine import (
    proyectar,
    CRECIMIENTO,
    MARGEN_EBIT
)

from cashflow_engine import calcular_fcff

from wacc_engine import (
    calcular_wacc,
    RISK_FREE_RATE,
    BETA,
    MARKET_RETURN,
    COST_OF_DEBT,
    TAX_RATE,
    EQUITY_VALUE,
    DEBT_VALUE
)


# ==========================================
# 1. HIPÓTESIS EDITABLES
# ==========================================

# Crecimiento perpetuo del FCFF
TERMINAL_GROWTH = 0.025

# Datos hipotéticos, expresados en USD millones
CASH = 80_000
SHARES_OUTSTANDING = 7_400

# Precio de mercado hipotético, USD por acción
MARKET_PRICE = 450.00


# ==========================================
# 2. DCF VALUATION
# ==========================================

def calcular_dcf(
    flujos,
    wacc,
    terminal_growth,
    debt,
    cash,
    shares
):
    if not flujos:
        raise ValueError(
            "Se necesita al menos un flujo de caja."
        )

    if wacc <= terminal_growth:
        raise ValueError(
            "WACC debe ser mayor que el "
            "crecimiento perpetuo."
        )

    if wacc <= -1:
        raise ValueError("WACC inválido.")

    if terminal_growth <= -1:
        raise ValueError(
            "Crecimiento perpetuo inválido."
        )

    if shares <= 0:
        raise ValueError(
            "Las acciones en circulación deben "
            "ser mayores que cero."
        )

    if debt < 0 or cash < 0:
        raise ValueError(
            "Deuda y efectivo no pueden "
            "ser negativos."
        )

    # Descontar los FCFF anuales
    valores_presentes = []

    for periodo, flujo in enumerate(flujos, start=1):
        fcff = flujo["fcff"]

        pv = fcff / ((1 + wacc) ** periodo)

        valores_presentes.append({
            "year": flujo["year"],
            "fcff": fcff,
            "present_value": pv
        })

    pv_flujos = sum(
        fila["present_value"]
        for fila in valores_presentes
    )

    # Valor terminal — Gordon Growth
    ultimo_fcff = flujos[-1]["fcff"]

    terminal_value = (
        ultimo_fcff * (1 + terminal_growth)
        / (wacc - terminal_growth)
    )

    pv_terminal = (
        terminal_value / ((1 + wacc) ** len(flujos))
    )

    # Enterprise Value
    enterprise_value = pv_flujos + pv_terminal

    # Equity Value
    equity_value = enterprise_value - debt + cash

    # Precio intrínseco por acción
    intrinsic_price = equity_value / shares

    return {
        "present_values": valores_presentes,
        "pv_fcf": pv_flujos,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "intrinsic_price": intrinsic_price
    }


# ==========================================
# 3. MOSTRAR RESULTADOS
# ==========================================

def mostrar_resultados(resultados, wacc):
    print("\nINTRINSIC — DCF VALUATION")
    print("MICROSOFT CORPORATION")
    print("USD MILLONES, EXCEPTO PRECIO POR ACCIÓN")
    print("-" * 65)

    print(f"WACC:                  {wacc:.2%}")
    print(f"Terminal Growth:       {TERMINAL_GROWTH:.2%}")

    print("\nDISCOUNTED FREE CASH FLOWS")
    print("-" * 65)

    for fila in resultados["present_values"]:
        print(
            f"FY {fila['year']}: "
            f"FCFF ${fila['fcff'] / 1e6:,.0f} M "
            f"| PV ${fila['present_value'] / 1e6:,.0f} M"
        )

    print("\nVALUATION SUMMARY")
    print("-" * 65)

    metricas = {
        "PV of FCFF": resultados["pv_fcf"],
        "Terminal Value": resultados["terminal_value"],
        "PV of Terminal Value": resultados["pv_terminal"],
        "Enterprise Value": resultados["enterprise_value"],
        "Equity Value": resultados["equity_value"],
    }

    for nombre, valor in metricas.items():
        print(f"{nombre:<25}${valor / 1e6:>15,.0f} M")

    print("-" * 65)

    precio = resultados["intrinsic_price"]
    upside = precio / MARKET_PRICE - 1

    print(f"Intrinsic Price:       ${precio:,.2f}")
    print(f"Market Price (Demo):   ${MARKET_PRICE:,.2f}")
    print(f"Upside / Downside:     {upside:+.2%}")

    print("-" * 65)
    print("SIMULACIÓN — HIPÓTESIS NO VALIDADAS")


# ==========================================
# 4. EJECUCIÓN PRINCIPAL
# ==========================================

if __name__ == "__main__":

    # Obtener estados financieros
    datos = descargar_datos()
    tabla = construir_tabla(datos)

    # Proyectar ingresos y EBIT
    proyecciones = proyectar(
        tabla,
        CRECIMIENTO,
        MARGEN_EBIT
    )

    # Calcular flujos de caja
    ultimo_anio = max(tabla["Revenue"])
    ingresos_iniciales = tabla["Revenue"][ultimo_anio]

    flujos = calcular_fcff(
        proyecciones,
        ingresos_iniciales
    )

    # Calcular WACC
    resultado_wacc = calcular_wacc(
        RISK_FREE_RATE,
        BETA,
        MARKET_RETURN,
        COST_OF_DEBT,
        TAX_RATE,
        EQUITY_VALUE,
        DEBT_VALUE
    )

    wacc = resultado_wacc["wacc"]

    # IMPORTANTE:
    # Los flujos están expresados en USD.
    # Convertimos los datos hipotéticos de
    # deuda y efectivo de millones a USD.
    deuda_usd = DEBT_VALUE * 1_000_000
    efectivo_usd = CASH * 1_000_000

    # Las acciones están expresadas en millones.
    acciones = SHARES_OUTSTANDING * 1_000_000

    resultados = calcular_dcf(
        flujos,
        wacc,
        TERMINAL_GROWTH,
        deuda_usd,
        efectivo_usd,
        acciones
    )

    mostrar_resultados(resultados, wacc)
