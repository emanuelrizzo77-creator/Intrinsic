"""INTRINSIC — SEC EDGAR financial data engine (multi-company).

Backward compatible: descargar_datos() still defaults to Microsoft.
"""
from datetime import date
from functools import lru_cache
import re
import requests

DEFAULT_TICKER = "MSFT"
BASE_URL = "https://data.sec.gov"
HEADERS = {
    "User-Agent": "Intrinsic Research your@email.com",
    "Accept-Encoding": "gzip, deflate",
}

METRICAS = {
    "Revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "EBIT": ["OperatingIncomeLoss"],
    "Net Income": ["NetIncomeLoss"],
    "Depreciation": ["Depreciation"],
    "Amortization": ["AmortizationOfIntangibleAssets"],
    "CapEx": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "CFO": ["NetCashProvidedByUsedInOperatingActivities"],
}


def _get_json(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


@lru_cache(maxsize=1)
def obtener_directorio_empresas():
    """Return SEC ticker directory. Cache lasts for the Python process."""
    entries = _get_json("https://www.sec.gov/files/company_tickers.json")
    return {
        str(entry["ticker"]).upper(): {
            "cik": str(entry["cik_str"]).zfill(10),
            "name": entry["title"],
        }
        for entry in entries.values()
    }


def resolver_cik(ticker):
    ticker = str(ticker).strip().upper().replace(".", "-")
    if not re.fullmatch(r"[A-Z0-9-]{1,12}", ticker):
        raise ValueError(f"Ticker inválido: {ticker!r}")
    company = obtener_directorio_empresas().get(ticker)
    if company is None:
        raise ValueError(f"Ticker {ticker} no encontrado en el directorio SEC EDGAR.")
    return company["cik"]


def descargar_datos(ticker=DEFAULT_TICKER):
    """Download companyfacts for a US SEC filer by ticker."""
    ticker = str(ticker).strip().upper()
    cik = resolver_cik(ticker)
    print(f"Conectando con SEC EDGAR: {ticker} (CIK {cik})...")
    datos = _get_json(f"{BASE_URL}/api/xbrl/companyfacts/CIK{cik}.json")
    print("Empresa:", datos.get("entityName", ticker))
    return datos


def _registros_anuales(datos, etiquetas):
    facts = datos.get("facts", {}).get("us-gaap", {})
    for prioridad, etiqueta in enumerate(etiquetas):
        for registro in facts.get(etiqueta, {}).get("units", {}).get("USD", []):
            if registro.get("form") != "10-K":
                continue
            if not all(k in registro for k in ("start", "end", "val", "filed")):
                continue
            if not isinstance(registro["val"], (int, float)) or isinstance(registro["val"], bool):
                continue
            try:
                inicio = date.fromisoformat(registro["start"])
                fin = date.fromisoformat(registro["end"])
                fecha_presentacion = date.fromisoformat(registro["filed"])
            except (TypeError, ValueError):
                continue
            if not 340 <= (fin - inicio).days <= 400:
                continue
            yield prioridad, etiqueta, registro, fin, fecha_presentacion


def extraer_metrica(datos, etiquetas):
    """Return annual USD values keyed by fiscal-year label.

    Prioritize tags, then newest filing for the *same fiscal period*.
    Keys use the calendar year of the fiscal period end (not SEC filing fy).
    """
    candidatos = {}
    for prioridad, etiqueta, registro, fin, fecha_presentacion in _registros_anuales(datos, etiquetas):
        # Exclude 10-K comparative observations tagged as interim quarters.
        if registro.get("fp") not in (None, "FY"):
            continue
        # SEC fy refers to the filing, and can mislabel comparative years.
        anio = fin.year
        candidato = {
            "valor": registro["val"],
            "filed": fecha_presentacion,
            "etiqueta": etiqueta,
            "prioridad": prioridad,
            "end": fin,
        }
        candidatos.setdefault(anio, []).append(candidato)

    resultados = {}
    for anio, registros in candidatos.items():
        # Pick the most recent fiscal end date for this FY first, then preferred tag.
        ultimo_fin = max(r["end"] for r in registros)
        mismos_periodos = [r for r in registros if r["end"] == ultimo_fin]
        seleccionado = min(mismos_periodos, key=lambda r: (r["prioridad"], -r["filed"].toordinal()))
        resultados[anio] = seleccionado["valor"]
    return resultados


def construir_tabla(datos):
    return {nombre: extraer_metrica(datos, etiquetas) for nombre, etiquetas in METRICAS.items()}


def mostrar_tabla(tabla):
    anios = sorted(set().union(*(valores.keys() for valores in tabla.values())))[-5:]
    print("\nFINANCIAL STATEMENTS — USD MILLONES")
    print("-" * 83)
    print(f"{'Métrica':<16}" + "".join(f"{anio:>13}" for anio in anios))
    print("-" * 83)
    for nombre, valores in tabla.items():
        fila = f"{nombre:<16}"
        for anio in anios:
            valor = valores.get(anio)
            fila += f"{valor / 1_000_000:>13,.0f}" if valor is not None else f"{'N/A':>13}"
        print(fila)
    print("-" * 83)
    faltantes = [(nombre, anio) for nombre, valores in tabla.items() for anio in anios if anio not in valores]
    if faltantes:
        print("\nATENCIÓN: Datos no encontrados:")
        for nombre, anio in faltantes:
            print(f" - {nombre}, FY {anio}")
    print("\nFuente: SEC EDGAR / Company Facts")


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TICKER
    datos = descargar_datos(ticker)
    tabla = construir_tabla(datos)
    mostrar_tabla(tabla)
