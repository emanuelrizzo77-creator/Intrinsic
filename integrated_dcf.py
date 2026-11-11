
# INTRINSIC — INTEGRATED DCF
# Milestone 07B

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
    MARKET_RETURN,
    COST_OF_DEBT,
    TAX_RATE
)

from dcf_engine import (
    calcular_dcf,
    TERMINAL_GROWTH
)

from data_validator import (
    validar_mercado,
    validar_balance,
    calcular_deuda_neta
)

from market_data import (
    obtener_mercado,
    obtener_balance_sec
)


def ejecutar_valoracion():
    # 1. Datos históricos
    datos = descargar_datos()
    tabla = construir_tabla(datos)

    # 2. Datos de mercado y balance
    mercado = obtener_mercado("MSFT")
    balance = obtener_balance_sec(datos)

    validar_mercado(mercado)
    fecha_balance = validar_balance(balance)

    deuda = calcular_deuda_neta(balance)

    # 3. Proyecciones
    proyecciones = proyectar(
        tabla,
        CRECIMIENTO,
        MARGEN_EBIT
    )

    ultimo_anio = max(tabla["Revenue"])

    flujos = calcular_fcff(
        proyecciones,
        tabla["Revenue"][ultimo_anio]
    )

    # 4. WACC
    # Beta y pesos de capital observados.
    # Las tasas siguen siendo hipótesis.
    beta = mercado["beta"]

    if beta is None:
        raise ValueError(
            "Beta no disponible. "
            "Se requiere una hipótesis explícita."
        )

    wacc_resultado = calcular_wacc(
        RISK_FREE_RATE,
        beta,
        MARKET_RETURN,
        COST_OF_DEBT,
        TAX_RATE,
        mercado["market_cap"],
        deuda["debt"]
    )

    wacc = wacc_resultado["wacc"]

    # 5. DCF
    # Puente EV-Equity preliminar.
    resultados = calcular_dcf(
        flujos,
        wacc,
        TERMINAL_GROWTH,
        deuda["debt"],
        deuda["cash_and_investments"],
        mercado["shares"]
    )

    # 6. Comparación con mercado
    precio = resultados["intrinsic_price"]
    precio_mercado = mercado["price"]

    upside = precio / precio_mercado - 1

    print("\nINTRINSIC — INTEGRATED DCF")
    print("-" * 60)
    print("Empresa:", mercado["company"])
    print("Ticker:", mercado["ticker"])
    print("Balance:", fecha_balance)
    print("Consulta mercado:", mercado["retrieved_at"])

    print(f"\nBeta: {beta:.2f}")
    print(f"WACC: {wacc:.2%}")
    print(f"Terminal Growth: {TERMINAL_GROWTH:.2%}")

    print("\nVALUATION")
    print("-" * 60)

    print(
        f"Enterprise Value: "
        f"${resultados['enterprise_value'] / 1e9:,.2f} B"
    )

    print(
        f"Equity Value: "
        f"${resultados['equity_value'] / 1e9:,.2f} B"
    )

    print(
        f"Intrinsic Price: ${precio:,.2f}"
    )

    print(
        f"Market Price: ${precio_mercado:,.2f}"
    )

    print(
        f"Upside / Downside: {upside:+.2%}"
    )

    print("-" * 60)
    print("PROTOTIPO — VALORACIÓN NO VALIDADA")
    print(
        "FCFF, WACC y puente EV-Equity "
        "requieren revisión financiera."
    )

    return resultados


if __name__ == "__main__":
    ejecutar_valoracion()
