
from financial_engine import (
    descargar_datos,
    construir_tabla
)

from forecast_engine import (
    proyectar,
    CRECIMIENTO,
    MARGEN_EBIT
)


# HIPÓTESIS EDITABLES
TASA_IMPUESTOS = 0.21
DA_SOBRE_INGRESOS = 0.10
CAPEX_SOBRE_INGRESOS = 0.20
NWC_SOBRE_INCREMENTO_INGRESOS = 0.05


def calcular_fcff(proyecciones, ingresos_iniciales):
    resultados = []
    ingresos_anteriores = ingresos_iniciales

    for fila in proyecciones:
        anio = fila["year"]
        ingresos = fila["revenue"]
        ebit = fila["ebit"]

        # Beneficio operativo después de impuestos
        nopat = ebit * (1 - TASA_IMPUESTOS)

        # Depreciación y amortización proyectadas
        da = ingresos * DA_SOBRE_INGRESOS

        # Inversión en activos fijos
        capex = ingresos * CAPEX_SOBRE_INGRESOS

        # Inversión incremental en capital de trabajo
        incremento_ingresos = ingresos - ingresos_anteriores

        delta_nwc = (
            incremento_ingresos
            * NWC_SOBRE_INCREMENTO_INGRESOS
        )

        # Free Cash Flow to the Firm
        fcff = nopat + da - capex - delta_nwc

        resultados.append({
            "year": anio,
            "revenue": ingresos,
            "ebit": ebit,
            "nopat": nopat,
            "da": da,
            "capex": capex,
            "delta_nwc": delta_nwc,
            "fcff": fcff,
        })

        ingresos_anteriores = ingresos

    return resultados


def mostrar_resultados(resultados):
    print("\nFREE CASH FLOW FORECAST")
    print("USD MILLONES")
    print("-" * 92)

    encabezado = f"{'Métrica':<20}"

    for fila in resultados:
        encabezado += f"{fila['year']:>14}"

    print(encabezado)
    print("-" * 92)

    metricas = {
        "Revenue": "revenue",
        "EBIT": "ebit",
        "NOPAT": "nopat",
        "D&A": "da",
        "CapEx": "capex",
        "Delta NWC": "delta_nwc",
        "FCFF": "fcff",
    }

    for nombre, clave in metricas.items():
        linea = f"{nombre:<20}"

        for fila in resultados:
            valor = fila[clave] / 1_000_000
            linea += f"{valor:>14,.0f}"

        print(linea)

    print("-" * 92)


if __name__ == "__main__":
    datos = descargar_datos()
    tabla = construir_tabla(datos)

    proyecciones = proyectar(
        tabla,
        CRECIMIENTO,
        MARGEN_EBIT
    )

    ultimo_anio = max(tabla["Revenue"])
    ingresos_iniciales = tabla["Revenue"][ultimo_anio]

    flujos = calcular_fcff(
        proyecciones,
        ingresos_iniciales
    )

    mostrar_resultados(flujos)
