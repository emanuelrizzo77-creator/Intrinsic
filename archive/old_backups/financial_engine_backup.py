
from datetime import date
import requests

# Configuración de Intrinsic
CIK = "0000789019"  # Microsoft
URL = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"

HEADERS = {
    "User-Agent": "Intrinsic Research your@email.com",
    "Accept-Encoding": "gzip, deflate",
}

# Etiquetas contables que buscaremos en SEC EDGAR.
# Están ordenadas por prioridad.
METRICAS = {
    "Revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "EBIT": [
        "OperatingIncomeLoss",
    ],
    "Net Income": [
        "NetIncomeLoss",
    ],
    "Depreciation": [
    "Depreciation",
],
"Amortization": [
    "AmortizationOfIntangibleAssets",
],
    "CapEx": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
    ],
    "CFO": [
        "NetCashProvidedByUsedInOperatingActivities",
    ],
}


def descargar_datos():
    print("Conectando con SEC EDGAR...")

    respuesta = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )
    respuesta.raise_for_status()

    datos = respuesta.json()
    print("Empresa:", datos["entityName"])

    return datos



def extraer_metrica(datos, etiquetas):
    hechos = datos["facts"].get("us-gaap", {})
    candidatos = {}

    for prioridad, etiqueta in enumerate(etiquetas):
        concepto = hechos.get(etiqueta, {})

        registros = concepto.get(
            "units", {}
        ).get("USD", [])

        for registro in registros:
            if registro.get("form") != "10-K":
                continue

            if not all(
                k in registro
                for k in ("start", "end", "val", "filed")
            ):
                continue

            inicio = date.fromisoformat(
                registro["start"]
            )

            fin = date.fromisoformat(
                registro["end"]
            )

            duracion = (fin - inicio).days

            if not 340 <= duracion <= 400:
                continue

            # Microsoft: cierre fiscal 30 de junio
            if fin.month != 6 or fin.day != 30:
                continue

            anio = fin.year

            candidato = {
                "valor": registro["val"],
                "filed": registro["filed"],
                "etiqueta": etiqueta,
                "prioridad": prioridad,
            }

            candidatos.setdefault(
                anio, []
            ).append(candidato)

    resultados = {}

    for anio, registros in candidatos.items():

        seleccionado = sorted(
            registros,
            key=lambda r: (
                r["prioridad"],
                -date.fromisoformat(
                    r["filed"]
                ).toordinal()
            )
        )[0]

        resultados[anio] = seleccionado["valor"]

    return resultados


def construir_tabla(datos):
    tabla = {}

    for nombre, etiquetas in METRICAS.items():
        tabla[nombre] = extraer_metrica(
            datos, etiquetas
        )

    return tabla


def mostrar_tabla(tabla):
    anios = sorted(
        set().union(
            *(valores.keys() for valores in tabla.values())
        )
    )[-5:]

    print("\nFINANCIAL STATEMENTS — USD MILLONES")
    print("-" * 83)

    encabezado = f"{'Métrica':<16}"
    for anio in anios:
        encabezado += f"{anio:>13}"

    print(encabezado)
    print("-" * 83)

    for nombre, valores in tabla.items():
        fila = f"{nombre:<16}"

        for anio in anios:
            valor = valores.get(anio)

            if valor is None:
                fila += f"{'N/A':>13}"
            else:
                millones = valor / 1_000_000
                fila += f"{millones:>13,.0f}"

        print(fila)

    print("-" * 83)

    faltantes = [
        (nombre, anio)
        for nombre, valores in tabla.items()
        for anio in anios
        if anio not in valores
    ]

    if faltantes:
        print("\nATENCIÓN: Datos no encontrados:")
        for nombre, anio in faltantes:
            print(f" - {nombre}, FY {anio}")

    print("\nFuente: SEC EDGAR / Company Facts")


if __name__ == "__main__":
    datos = descargar_datos()
    tabla = construir_tabla(datos)
    mostrar_tabla(tabla)
