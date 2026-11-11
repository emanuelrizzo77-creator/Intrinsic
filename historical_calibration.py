
# INTRINSIC — HISTORICAL CALIBRATION
# Milestone 11: Financial Model Validation

import math
from statistics import mean, median

from financial_engine import (
    descargar_datos,
    construir_tabla,
)

from financial_reconciliation import (
    WORKING_CAPITAL_TAGS,
    extraer_saldos,
    calcular_onwc,
    calcular_ratios,
)


def calcular_calibracion(tabla, onwc):
    ratios = calcular_ratios(tabla, onwc)
    revenue_historico = tabla["Revenue"]

    resultados = []

    for fila in ratios:
        anio = fila["year"]
        revenue = fila["revenue"]

        revenue_anterior = revenue_historico.get(anio - 1)

        delta_revenue = None
        nwc_incremental_ratio = None

        if revenue_anterior is not None:
            delta_revenue = revenue - revenue_anterior

            if (
                fila["delta_nwc"] is not None
                and abs(delta_revenue) > 1
            ):
                nwc_incremental_ratio = (
                    fila["delta_nwc"] / delta_revenue
                )

        onwc_ratio = None

        if fila["onwc"] is not None:
            onwc_ratio = fila["onwc"] / revenue

        resultados.append({
            "year": anio,
            "revenue": revenue,
            "da_ratio": fila["da_ratio"],
            "capex_ratio": fila["capex_ratio"],
            "onwc_ratio": onwc_ratio,
            "delta_nwc": fila["delta_nwc"],
            "delta_revenue": delta_revenue,
            "nwc_incremental_ratio": nwc_incremental_ratio,
        })

    return resultados


def resumir_ratio(filas, clave, ultimos=3):
    valores = [
        fila[clave]
        for fila in filas
        if fila[clave] is not None
        and math.isfinite(fila[clave])
    ]

    valores = valores[-ultimos:]

    if not valores:
        return {
            "count": 0,
            "mean": None,
            "median": None,
        }

    return {
        "count": len(valores),
        "mean": mean(valores),
        "median": median(valores),
    }


def mostrar_calibracion(filas):
    print("\nINTRINSIC — HISTORICAL CALIBRATION")
    print("=" * 90)

    print(
        f"{'FY':<8}"
        f"{'D&A/Rev':>14}"
        f"{'CapEx/Rev':>14}"
        f"{'ONWC/Rev':>14}"
        f"{'ΔNWC/ΔRev':>16}"
    )

    print("-" * 90)

    def porcentaje(valor):
        if valor is None:
            return "N/A"
        return f"{valor:.2%}"

    for fila in filas:
        print(
            f"{fila['year']:<8}"
            f"{porcentaje(fila['da_ratio']):>14}"
            f"{porcentaje(fila['capex_ratio']):>14}"
            f"{porcentaje(fila['onwc_ratio']):>14}"
            f"{porcentaje(fila['nwc_incremental_ratio']):>16}"
        )

    print("\nLAST 3 AVAILABLE OBSERVATIONS")
    print("-" * 90)

    metricas = {
        "D&A / Revenue": "da_ratio",
        "CapEx / Revenue": "capex_ratio",
        "ONWC / Revenue": "onwc_ratio",
        "Delta NWC / Delta Revenue": "nwc_incremental_ratio",
    }

    for nombre, clave in metricas.items():
        resumen = resumir_ratio(filas, clave)

        if resumen["count"] == 0:
            print(f"{nombre}: N/A")
            continue

        print(
            f"{nombre}: "
            f"Mean={resumen['mean']:.2%} | "
            f"Median={resumen['median']:.2%} | "
            f"N={resumen['count']}"
        )

        if resumen["count"] < 3:
            print(
                "  WARNING: Fewer than 3 observations."
            )

    print("\nNOTES")
    print("- Ratios are historical, not forecasts.")
    print("- ONWC = AR + Inventory - AP.")
    print("- D&A SEC tags require overlap validation.")
    print("- CapEx classification requires verification.")
    print("- ΔNWC/ΔRevenue can be unstable.")
    print("- No DCF assumptions were changed.")


def ejecutar_calibracion():
    datos = descargar_datos()
    tabla = construir_tabla(datos)

    saldos = extraer_saldos(
        datos,
        WORKING_CAPITAL_TAGS,
    )

    onwc = calcular_onwc(saldos)

    filas = calcular_calibracion(tabla, onwc)

    mostrar_calibracion(filas)

    return filas


if __name__ == "__main__":
    ejecutar_calibracion()
