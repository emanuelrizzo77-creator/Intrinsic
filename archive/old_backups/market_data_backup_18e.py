
# INTRINSIC — MARKET DATA ENGINE
# Milestone 07

from datetime import datetime, timezone

import yfinance as yf

from financial_engine import (
    descargar_datos,
    construir_tabla
)


TICKER = "MSFT"


def obtener_mercado(ticker):
    print(f"Consultando datos de mercado: {ticker}")

    accion = yf.Ticker(ticker)
    info = accion.info

    precio = info.get("currentPrice")
    if precio is None:
        precio = info.get("regularMarketPrice")

    acciones = info.get("sharesOutstanding")
    capitalizacion = info.get("marketCap")

    if capitalizacion is None:
        if precio is not None and acciones is not None:
            capitalizacion = precio * acciones

    return {
        "ticker": ticker,
        "company": info.get("longName"),
        "price": precio,
        "shares": acciones,
        "market_cap": capitalizacion,
        "beta": info.get("beta"),
        "currency": info.get("currency"),
        "retrieved_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": "Yahoo Finance via yfinance"
    }


def obtener_balance_sec(datos):
    conceptos = datos["facts"].get("us-gaap", {})

    
    etiquetas = {
        "Cash": [
            "CashAndCashEquivalentsAtCarryingValue"
        ],
        "Short Term Investments": [
            "ShortTermInvestments"
        ],
        "Long Term Investments": [
            "LongTermInvestments"
        ],
        "Long Term Debt": [
            "LongTermDebtNoncurrent"
        ],
        "Current Debt": [
            "LongTermDebtCurrent",
            "ShortTermBorrowings"
        ],
}


    resultados = {}

    for nombre, opciones in etiquetas.items():
        candidatos = []

        for etiqueta in opciones:
            concepto = conceptos.get(etiqueta, {})

            registros = concepto.get(
                "units", {}
            ).get("USD", [])

            for registro in registros:
                if registro.get("form") != "10-K":
                    continue

                # Los saldos de balance son instantáneos:
                # no deben contener fecha de inicio.
                if "start" in registro:
                    continue

                if not all(
                    clave in registro
                    for clave in ("end", "filed", "val")
                ):
                    continue

                candidatos.append({
                    "value": registro["val"],
                    "date": registro["end"],
                    "filed": registro["filed"],
                    "tag": etiqueta,
                })

            # Priorizar la primera etiqueta disponible
            if candidatos:
                break

        if candidatos:
            ultimo = max(
                candidatos,
                key=lambda r: (r["date"], r["filed"])
            )
            resultados[nombre] = ultimo
        else:
            resultados[nombre] = None

    return resultados

def obtener_balance_historico_sec(datos, fecha_balance):
    """
    Extrae balances históricos de SEC EDGAR.

    Todos los valores se expresan en USD.
    Exige registros instantáneos de un 10-K
    correspondientes a la fecha solicitada.
    """

    conceptos = datos["facts"].get("us-gaap", {})

    etiquetas = {
        "Cash": [
            "CashAndCashEquivalentsAtCarryingValue"
        ],
        "Short Term Investments": [
            "ShortTermInvestments"
        ],
        "Long Term Debt": [
            "LongTermDebtNoncurrent"
        ],
        "Current Debt": [
            "LongTermDebtCurrent",
            "ShortTermBorrowings"
        ],
        "Equity": [
            "StockholdersEquity"
        ],
        "Finance Leases": [
            "FinanceLeaseLiability"
        ],
        "Operating Leases": [
            "OperatingLeaseLiability"
        ],
        "Long Term Investments": [
    "LongTermInvestments"
    ],
    }

    resultados = {}

    for nombre, opciones in etiquetas.items():
        candidatos = []

        for etiqueta in opciones:
            registros = (
                conceptos.get(etiqueta, {})
                .get("units", {})
                .get("USD", [])
            )

            validos = [
                registro
                for registro in registros
                if registro.get("form") == "10-K"
                and registro.get("end") == fecha_balance
                and "start" not in registro
                and isinstance(
                    registro.get("val"), (int, float)
                )
                and not isinstance(
                    registro.get("val"), bool
                )
                and registro["val"] >= 0
                and registro.get("filed")
            ]

            if validos:
                candidatos = [
                    {
                        "value": registro["val"],
                        "date": registro["end"],
                        "filed": registro["filed"],
                        "tag": etiqueta,
                    }
                    for registro in validos
                ]
                break

        if not candidatos:
            raise ValueError(
                f"SEC historical data missing: "
                f"{nombre} ({fecha_balance})"
            )

        # Selecciona el registro más reciente
        # presentado para esa fecha de balance.
        resultados[nombre] = max(
            candidatos,
            key=lambda r: r["filed"]
        )

    return resultados



def mostrar_resultados(mercado, balance):
    print("\nINTRINSIC — MARKET DATA")
    print("-" * 55)

    print("Ticker:", mercado["ticker"])
    print("Empresa:", mercado["company"])
    print("Moneda:", mercado["currency"])
    print("Fuente:", mercado["source"])
    print("Consulta UTC:", mercado["retrieved_at"])

    print("\nMARKET INFORMATION")
    print("-" * 55)

    for nombre, clave in [
        ("Market Price", "price"),
        ("Shares Outstanding", "shares"),
        ("Market Capitalization", "market_cap"),
        ("Beta", "beta"),
    ]:
        valor = mercado[clave]

        if valor is None:
            print(f"{nombre:<25}N/A")
        elif clave == "price":
            print(f"{nombre:<25}${valor:,.2f}")
        elif clave == "beta":
            print(f"{nombre:<25}{valor:.2f}")
        else:
            print(f"{nombre:<25}{valor:,.0f}")

    print("\nSEC BALANCE SHEET")
    print("-" * 55)

    for nombre, registro in balance.items():
        if registro is None:
            print(f"{nombre:<25}N/A")
        else:
            millones = registro["value"] / 1_000_000

            print(
                f"{nombre:<25}"
                f"${millones:,.0f} M "
                f"({registro['date']})"
            )

    print("-" * 55)


if __name__ == "__main__":
    datos = descargar_datos()

    mercado = obtener_mercado(TICKER)
    balance = obtener_balance_sec(datos)

    mostrar_resultados(mercado, balance)
