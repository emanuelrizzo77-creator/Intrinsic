
import requests

# Identificador oficial de Microsoft en la SEC
CIK = "0000789019"

URL = (
    "https://data.sec.gov/api/xbrl/"
    f"companyfacts/CIK{CIK}.json"
)

# Reemplaza el correo por uno de contacto real.
HEADERS = {
    "User-Agent": "Intrinsic Research your@email.com",
    "Accept-Encoding": "gzip, deflate",
}

def obtener_datos():
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


def obtener_ingresos_anuales(datos):
    conceptos = datos["facts"]["us-gaap"]

    posibles_etiquetas = [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ]

    registros = {}

    for etiqueta in posibles_etiquetas:
        if etiqueta not in conceptos:
            continue

        hechos = conceptos[etiqueta]["units"]["USD"]

        for hecho in hechos:
            if hecho.get("form") != "10-K":
                continue

            if hecho.get("fp") != "FY":
                continue

            if "start" not in hecho:
                continue

            from datetime import date

            duracion = (
                date.fromisoformat(hecho["end"])
                - date.fromisoformat(hecho["start"])
            ).days

            # Evitar datos trimestrales y parciales.
            if not 340 <= duracion <= 400:
                continue

            anio = int(hecho["end"][:4])

            # Priorizar la primera etiqueta disponible
            # y la presentación más reciente de cada año.
            actual = registros.get(anio)

            if actual is None or (
                actual["etiqueta"] == etiqueta
                and hecho["filed"] > actual["filed"]
            ):
                registros[anio] = {
                    "valor": hecho["val"],
                    "filed": hecho["filed"],
                    "etiqueta": etiqueta,
                }

    return registros


if __name__ == "__main__":
    datos = obtener_datos()
    ingresos = obtener_ingresos_anuales(datos)

    print("\nINGRESOS ANUALES (USD MILLONES)")
    print("--------------------------------")

    for anio in sorted(ingresos)[-5:]:
        millones = ingresos[anio]["valor"] / 1_000_000
        print(f"FY {anio}: ${millones:,.0f} M")
