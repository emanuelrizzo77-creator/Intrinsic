
from financial_engine import (
    descargar_datos,
    construir_tabla
)

# HIPÓTESIS EDITABLES
# Porcentajes expresados como decimales.
CRECIMIENTO = [0.12, 0.10, 0.09, 0.08, 0.07]
MARGEN_EBIT = [0.47, 0.47, 0.46, 0.46, 0.45]


def calcular_historicos(tabla):
    ingresos = tabla["Revenue"]
    ebit = tabla["EBIT"]

    anios = sorted(set(ingresos) & set(ebit))[-5:]

    print("\nHISTORICAL FINANCIAL RATIOS")
    print("-" * 62)
    print(f"{'FY':<8}{'Revenue':>15}{'Growth':>13}{'EBIT Margin':>16}")

    anterior = None

    for anio in anios:
        revenue = ingresos[anio]
        margen = ebit[anio] / revenue

        if anterior is None:
            crecimiento = "N/A"
        else:
            tasa = revenue / anterior - 1
            crecimiento = f"{tasa:.1%}"

        print(
            f"{anio:<8}"
            f"{revenue / 1e6:>15,.0f}"
            f"{crecimiento:>13}"
            f"{margen:>16.1%}"
        )

        anterior = revenue


def proyectar(tabla, crecimiento, margenes):
    if len(crecimiento) != len(margenes):
        raise ValueError(
            "Las listas de crecimiento y márgenes "
            "deben tener la misma longitud."
        )

    ingresos = tabla["Revenue"]
    ultimo_anio = max(ingresos)

    revenue = ingresos[ultimo_anio]
    resultados = []

    for i, (g, margen) in enumerate(
        zip(crecimiento, margenes), start=1
    ):
        anio = ultimo_anio + i

        revenue = revenue * (1 + g)
        ebit = revenue * margen

        resultados.append({
            "year": anio,
            "revenue": revenue,
            "growth": g,
            "ebit_margin": margen,
            "ebit": ebit,
        })

    return resultados


def mostrar_proyecciones(resultados):
    print("\nFINANCIAL FORECAST — USD MILLONES")
    print("-" * 68)

    print(
        f"{'FY':<8}"
        f"{'Revenue':>16}"
        f"{'Growth':>12}"
        f"{'EBIT':>16}"
        f"{'EBIT Margin':>16}"
    )

    for fila in resultados:
        print(
            f"{fila['year']:<8}"
            f"{fila['revenue'] / 1e6:>16,.0f}"
            f"{fila['growth']:>12.1%}"
            f"{fila['ebit'] / 1e6:>16,.0f}"
            f"{fila['ebit_margin']:>16.1%}"
        )


if __name__ == "__main__":
    datos = descargar_datos()
    tabla = construir_tabla(datos)

    calcular_historicos(tabla)

    proyecciones = proyectar(
        tabla,
        CRECIMIENTO,
        MARGEN_EBIT
    )

    mostrar_proyecciones(proyecciones)
