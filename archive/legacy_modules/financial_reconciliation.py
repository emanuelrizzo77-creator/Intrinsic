
# INTRINSIC — FINANCIAL RECONCILIATION
# Milestone 08B: Data Quality

from collections import defaultdict
from datetime import date

from financial_engine import (
    descargar_datos,
    construir_tabla
)


# ==========================================
# 1. ETIQUETAS CONTABLES
# ==========================================

WORKING_CAPITAL_TAGS = {
    "Accounts Receivable": [
        "AccountsReceivableNetCurrent"
    ],
    "Inventory": [
        "InventoryNet"
    ],
    "Accounts Payable": [
        "AccountsPayableCurrent"
    ]
}


# ==========================================
# 2. EXTRAER SALDOS ANUALES
# ==========================================

def extraer_saldos(datos, etiquetas):
    conceptos = datos["facts"].get("us-gaap", {})
    resultados = {}

    for nombre, opciones in etiquetas.items():
        candidatos = defaultdict(list)

        for prioridad, etiqueta in enumerate(opciones):
            concepto = conceptos.get(etiqueta, {})

            registros = concepto.get(
                "units", {}
            ).get("USD", [])

            for registro in registros:
                if registro.get("form") != "10-K":
                    continue

                # Solo saldos de balance (instantáneos)
                if "start" in registro:
                    continue

                if not all(
                    k in registro
                    for k in ("end", "filed", "val")
                ):
                    continue

                cierre = date.fromisoformat(
                    registro["end"]
                )

                anio = cierre.year

                candidatos[anio].append({
                    "value": registro["val"],
                    "end": registro["end"],
                    "filed": registro["filed"],
                    "tag": etiqueta,
                    "priority": prioridad
                })

        resultados[nombre] = {}

        for anio, registros in candidatos.items():
            # Preferir la etiqueta principal.
            # Dentro de ella, usar el registro
            # presentado más recientemente.
            seleccionado = sorted(
                registros,
                key=lambda r: (
                    r["priority"],
                    -date.fromisoformat(
                        r["filed"]
                    ).toordinal()
                )
            )[0]

            resultados[nombre][anio] = seleccionado

    return resultados


# ==========================================
# 3. CALCULAR OPERATING NWC
# ==========================================

def calcular_onwc(saldos):
    ar = saldos["Accounts Receivable"]
    inventario = saldos["Inventory"]
    ap = saldos["Accounts Payable"]

    anios = sorted(
        set(ar) & set(inventario) & set(ap)
    )

    resultados = {}

    for anio in anios:
        fechas = {
            ar[anio]["end"],
            inventario[anio]["end"],
            ap[anio]["end"]
        }

        if len(fechas) != 1:
            print(
                f"WARNING: Fechas distintas FY{anio}"
            )
            continue

        resultados[anio] = (
            ar[anio]["value"]
            + inventario[anio]["value"]
            - ap[anio]["value"]
        )

    return resultados


# ==========================================
# 4. RATIOS FINANCIEROS
# ==========================================

def calcular_ratios(tabla, onwc):
    ingresos = tabla["Revenue"]
    capex = tabla["CapEx"]
    depreciacion = tabla["Depreciation"]
    amortizacion = tabla["Amortization"]

    resultados = []

    for anio in sorted(ingresos):
        revenue = ingresos.get(anio)

        if revenue is None or revenue <= 0:
            continue

        dep = depreciacion.get(anio)
        amort = amortizacion.get(anio)
        capex_val = capex.get(anio)

        da = None

        if dep is not None and amort is not None:
            da = dep + amort

        delta_nwc = None

        if anio in onwc and (anio - 1) in onwc:
            delta_nwc = (
                onwc[anio] - onwc[anio - 1]
            )

        resultados.append({
            "year": anio,
            "revenue": revenue,
            "da_ratio": (
                da / revenue
                if da is not None else None
            ),
            "capex_ratio": (
                capex_val / revenue
                if capex_val is not None else None
            ),
            "onwc": onwc.get(anio),
            "delta_nwc": delta_nwc
        })

    return resultados


# ==========================================
# 5. MOSTRAR RESULTADOS
# ==========================================

def mostrar_resultados(resultados):
    print("\nINTRINSIC — FINANCIAL RECONCILIATION")
    print("USD MILLONES")
    print("-" * 85)

    print(
        f"{'FY':<8}"
        f"{'D&A / Rev':>14}"
        f"{'CapEx / Rev':>16}"
        f"{'ONWC':>16}"
        f"{'Delta NWC':>16}"
    )

    print("-" * 85)

    for fila in resultados:
        def porcentaje(valor):
            if valor is None:
                return "N/A"
            return f"{valor:.2%}"

        def millones(valor):
            if valor is None:
                return "N/A"
            return f"{valor / 1e6:,.0f}"

        print(
            f"{fila['year']:<8}"
            f"{porcentaje(fila['da_ratio']):>14}"
            f"{porcentaje(fila['capex_ratio']):>16}"
            f"{millones(fila['onwc']):>16}"
            f"{millones(fila['delta_nwc']):>16}"
        )

    print("-" * 85)
    print("ONWC = AR + Inventory - AP")
    print("Fuente: SEC EDGAR / Company Facts")
    print("Pendiente: validación contable detallada")


# ==========================================
# 6. EJECUTAR
# ==========================================

if __name__ == "__main__":
    datos = descargar_datos()
    tabla = construir_tabla(datos)

    saldos = extraer_saldos(
        datos,
        WORKING_CAPITAL_TAGS
    )

    onwc = calcular_onwc(saldos)

    ratios = calcular_ratios(
        tabla,
        onwc
    )

    mostrar_resultados(ratios)
