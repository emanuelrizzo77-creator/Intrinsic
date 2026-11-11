
# INTRINSIC — ASSUMPTIONS ENGINE
# Milestone 09

from financial_engine import (
    descargar_datos,
    construir_tabla
)

from financial_reconciliation import (
    WORKING_CAPITAL_TAGS,
    extraer_saldos,
    calcular_onwc
)


# ==========================================
# 1. ESCENARIOS
# ==========================================

# Hipótesis ilustrativas, no estimaciones
# verificadas de Microsoft.
# Los porcentajes se expresan como decimales.

SCENARIOS = {
    "conservative": {
        "growth": [0.08, 0.07, 0.06, 0.05, 0.04],
        "ebit_margin": [0.44, 0.44, 0.43, 0.43, 0.42],
        "da_ratio": [0.12, 0.13, 0.13, 0.12, 0.12],
        "capex_ratio": [0.35, 0.33, 0.30, 0.28, 0.26],
        "nwc_ratio": 0.05
    },

    "base": {
        "growth": [0.12, 0.10, 0.09, 0.08, 0.07],
        "ebit_margin": [0.47, 0.47, 0.46, 0.46, 0.45],
        "da_ratio": [0.12, 0.12, 0.12, 0.11, 0.11],
        "capex_ratio": [0.28, 0.26, 0.24, 0.22, 0.20],
        "nwc_ratio": 0.03
    },

    "optimistic": {
        "growth": [0.16, 0.14, 0.12, 0.10, 0.09],
        "ebit_margin": [0.49, 0.49, 0.49, 0.48, 0.48],
        "da_ratio": [0.11, 0.11, 0.11, 0.10, 0.10],
        "capex_ratio": [0.22, 0.21, 0.20, 0.19, 0.18],
        "nwc_ratio": 0.02
    }
}

TAX_RATE = 0.21


# ==========================================
# 2. VALIDAR HIPÓTESIS
# ==========================================

def validar_hipotesis(hipotesis):
    campos = [
        "growth",
        "ebit_margin",
        "da_ratio",
        "capex_ratio"
    ]

    for campo in campos:
        valores = hipotesis[campo]

        if len(valores) != 5:
            raise ValueError(
                f"{campo} debe contener cinco años."
            )

        for valor in valores:
            if not isinstance(valor, (int, float)):
                raise ValueError(
                    f"{campo} contiene un valor inválido."
                )

            if not -1 < valor < 2:
                raise ValueError(
                    f"{campo} fuera del rango permitido."
                )

            if campo in ("da_ratio", "capex_ratio"):
                if valor < 0:
                    raise ValueError(
                        f"{campo} no puede ser negativo."
                    )

    if not 0 <= hipotesis["nwc_ratio"] < 1:
        raise ValueError(
            "nwc_ratio debe estar entre 0 y 1."
        )

    return True


# ==========================================
# 3. PROYECTAR FCFF
# ==========================================

def proyectar_escenario(
    revenue_inicial,
    anio_inicial,
    hipotesis,
    tax_rate=TAX_RATE
):
    validar_hipotesis(hipotesis)

    if revenue_inicial <= 0:
        raise ValueError(
            "Revenue inicial debe ser positivo."
        )

    if not 0 <= tax_rate < 1:
        raise ValueError(
            "La tasa impositiva es inválida."
        )

    resultados = []
    revenue_anterior = revenue_inicial

    for i in range(5):
        anio = anio_inicial + i + 1

        growth = hipotesis["growth"][i]
        margin = hipotesis["ebit_margin"][i]
        da_ratio = hipotesis["da_ratio"][i]
        capex_ratio = hipotesis["capex_ratio"][i]
        nwc_ratio = hipotesis["nwc_ratio"]

        revenue = revenue_anterior * (1 + growth)
        ebit = revenue * margin
        nopat = ebit * (1 - tax_rate)

        da = revenue * da_ratio
        capex = revenue * capex_ratio

        delta_revenue = revenue - revenue_anterior
        delta_nwc = delta_revenue * nwc_ratio

        fcff = nopat + da - capex - delta_nwc

        resultados.append({
            "year": anio,
            "revenue": revenue,
            "growth": growth,
            "ebit": ebit,
            "ebit_margin": margin,
            "nopat": nopat,
            "da": da,
            "capex": capex,
            "delta_nwc": delta_nwc,
            "fcff": fcff
        })

        revenue_anterior = revenue

    return resultados


# ==========================================
# 4. DATOS HISTÓRICOS
# ==========================================

def obtener_base_historica(ticker="MSFT"):
    datos = descargar_datos(ticker)
    tabla = construir_tabla(datos)

    revenue_historico = tabla["Revenue"]

    ultimo_anio = max(revenue_historico)
    ultimo_revenue = revenue_historico[ultimo_anio]

    saldos = extraer_saldos(
        datos,
        WORKING_CAPITAL_TAGS
    )

    onwc = calcular_onwc(saldos)

    print("\nINTRINSIC — HISTORICAL BASE")
    print("-" * 60)
    print(f"Last Fiscal Year: {ultimo_anio}")
    print(f"Revenue: ${ultimo_revenue / 1e6:,.0f} M")

    if ultimo_anio in onwc:
        print(
            f"Operating NWC: "
            f"${onwc[ultimo_anio] / 1e6:,.0f} M"
        )

    return ultimo_revenue, ultimo_anio


# ==========================================
# 5. MOSTRAR PROYECCIONES
# ==========================================

def mostrar_escenario(nombre, resultados):
    print(f"\nSCENARIO: {nombre.upper()}")
    print("USD MILLONES")
    print("-" * 95)

    print(
        f"{'FY':<8}"
        f"{'Revenue':>15}"
        f"{'EBIT':>15}"
        f"{'CapEx':>15}"
        f"{'D&A':>15}"
        f"{'FCFF':>15}"
    )

    print("-" * 95)

    for fila in resultados:
        print(
            f"{fila['year']:<8}"
            f"{fila['revenue'] / 1e6:>15,.0f}"
            f"{fila['ebit'] / 1e6:>15,.0f}"
            f"{fila['capex'] / 1e6:>15,.0f}"
            f"{fila['da'] / 1e6:>15,.0f}"
            f"{fila['fcff'] / 1e6:>15,.0f}"
        )


# ==========================================
# 6. EJECUCIÓN
# ==========================================

if __name__ == "__main__":
    revenue, ultimo_anio = obtener_base_historica()

    for nombre, hipotesis in SCENARIOS.items():
        proyeccion = proyectar_escenario(
            revenue,
            ultimo_anio,
            hipotesis
        )

        mostrar_escenario(nombre, proyeccion)

    print("\n" + "=" * 95)
    print("INTRINSIC — SCENARIO FORECAST COMPLETED")
    print("Assumptions are illustrative and editable.")
