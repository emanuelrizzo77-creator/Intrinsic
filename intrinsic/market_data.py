"""Intrinsic market data — Milestone 18F.

Only explicitly classified SEC balance-sheet tags are used for short/long
investments. Maturity disclosures and aggregate available-for-sale balances
are NOT substituted for current/noncurrent investments.
"""
from datetime import datetime, timezone
import yfinance as yf
from intrinsic.sec_client import descargar_datos

TICKER = "MSFT"

# First valid tag wins, but selection is restricted to the same balance date.
BALANCE_TAGS = {
    "Cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "Short Term Investments": [
        "ShortTermInvestments", "MarketableSecuritiesCurrent",
        "ShortTermInvestmentsAndMarketableSecurities",
        "AvailableForSaleSecuritiesCurrent",
    ],
    "Long Term Investments": [
        "LongTermInvestments", "MarketableSecuritiesNoncurrent",
        "AvailableForSaleSecuritiesNoncurrent", "OtherLongTermInvestments",
    ],
    "Long Term Debt": [
    "LongTermDebtNoncurrent",
    "LongTermDebt",
    "LongTermDebtAndCapitalLeaseObligations",
],
"Current Debt": [
    "LongTermDebtCurrent",
    "DebtCurrent",
    "LongTermDebtAndCapitalLeaseObligationsCurrent",
    "ShortTermBorrowings",
],
    "Equity": ["StockholdersEquity"],
    "Finance Leases": ["FinanceLeaseLiability"],
    "Operating Leases": ["OperatingLeaseLiability"],
}

def _info(tk):
    """Yahoo quote summary; {} when Yahoo rate-limits or blocks the request (common from shared cloud hosts)."""
    try:
        return tk.info or {}
    except Exception:
        return {}


def _fast(tk, attr):
    try:
        v = getattr(tk.fast_info, attr)
        return v if v is not None and v == v else None      # drop NaN
    except Exception:
        return None


def obtener_mercado(ticker):
    print(f"Consultando datos de mercado: {ticker}")
    tk = yf.Ticker(ticker)
    info = _info(tk)
    precio = info.get("currentPrice") or info.get("regularMarketPrice") or _fast(tk, "last_price")
    acciones = info.get("sharesOutstanding") or _fast(tk, "shares")
    capitalizacion = info.get("marketCap") or _fast(tk, "market_cap")
    if capitalizacion is None and precio is not None and acciones is not None:
        capitalizacion = precio * acciones
    # Every company here is an SEC filer whose ordinary shares or ADSs trade in the US, so when Yahoo omits the
    # currency the quote is in USD. A currency Yahoo DOES report is kept, so a non-USD listing is still refused.
    moneda = info.get("currency") or _fast(tk, "currency") or "USD"
    return {
        "ticker": ticker, "company": info.get("longName"),
        "price": precio, "shares": acciones, "market_cap": capitalizacion,
        "beta": info.get("beta"), "currency": moneda,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance via yfinance" + ("" if info else " (fast quote; full quote unavailable)"),
    }

def _candidatos(conceptos, etiqueta, fecha=None):
    registros = conceptos.get(etiqueta, {}).get("units", {}).get("USD", [])
    return [
        {"value": r["val"], "date": r["end"], "filed": r["filed"], "tag": etiqueta}
        for r in registros
        if r.get("form") == "10-K"
        and "start" not in r
        and r.get("end")
        and (fecha is None or r["end"] == fecha)
        and r.get("filed")
        and isinstance(r.get("val"), (int, float))
        and not isinstance(r.get("val"), bool)
        and r["val"] >= 0
    ]

def _buscar(conceptos, etiquetas, fecha):
    for etiqueta in etiquetas:
        candidatos = _candidatos(conceptos, etiqueta, fecha)
        if candidatos:
            return max(candidatos, key=lambda r: r["filed"])
    return None

def _fecha_balance(conceptos):
    # Anchor to the most recent cash balance, not a potentially stale tag.
    cash = _candidatos(conceptos, BALANCE_TAGS["Cash"][0])
    if not cash:
        return None
    return max(cash, key=lambda r: (r["date"], r["filed"]))["date"]

def obtener_balance_sec(datos):
    conceptos = datos.get("facts", {}).get("us-gaap", {})
    fecha = _fecha_balance(conceptos)
    balance = {
        nombre: _buscar(conceptos, etiquetas, fecha) if fecha else None
        for nombre, etiquetas in BALANCE_TAGS.items()
        if nombre not in ("Equity", "Finance Leases", "Operating Leases")
    }
    return balance

def obtener_deuda_en_fecha(datos, fecha_balance):
    """Extract reported financial debt at a specific SEC balance date."""
    conceptos = datos.get("facts", {}).get("us-gaap", {})

    largo = _buscar(
        conceptos,
        BALANCE_TAGS["Long Term Debt"],
        fecha_balance,
    )

    corto = _buscar(
        conceptos,
        BALANCE_TAGS["Current Debt"],
        fecha_balance,
    )

    if largo is None or corto is None:
        return None

    return {
        "date": fecha_balance,
        "long_term_debt": float(largo["value"]),
        "current_debt": float(corto["value"]),
        "total_debt": float(largo["value"] + corto["value"]),
        "long_term_tag": largo["tag"],
        "current_tag": corto["tag"],
    }

def obtener_balance_historico_sec(datos, fecha_balance):
    """Strict historical balance: no assumed zeros or mismatched dates."""
    conceptos = datos.get("facts", {}).get("us-gaap", {})
    resultados = {}
    for nombre in (
        "Cash", "Short Term Investments", "Long Term Debt", "Current Debt",
        "Equity", "Finance Leases", "Operating Leases", "Long Term Investments"
    ):
        registro = _buscar(conceptos, BALANCE_TAGS[nombre], fecha_balance)
        if registro is None:
            raise ValueError(f"SEC historical data missing: {nombre} ({fecha_balance})")
        resultados[nombre] = registro
    return resultados

def mostrar_resultados(mercado, balance):
    print("\nINTRINSIC — MARKET DATA\n" + "-" * 55)
    for nombre, clave in (
        ("Ticker", "ticker"), ("Empresa", "company"),
        ("Moneda", "currency"), ("Fuente", "source"),
        ("Consulta UTC", "retrieved_at")
    ):
        print(f"{nombre}: {mercado.get(clave)}")
    print("\nMARKET INFORMATION\n" + "-" * 55)
    for nombre, clave in (
        ("Market Price", "price"), ("Shares Outstanding", "shares"),
        ("Market Capitalization", "market_cap"), ("Beta", "beta")
    ):
        valor = mercado.get(clave)
        if valor is None:
            salida = "N/A"
        elif clave == "price":
            salida = f"${valor:,.2f}"
        elif clave == "beta":
            salida = f"{valor:.2f}"
        else:
            salida = f"{valor:,.0f}"
        print(f"{nombre:<25}{salida}")
    print("\nSEC BALANCE SHEET\n" + "-" * 55)
    for nombre, registro in balance.items():
        if registro is None:
            print(f"{nombre:<25}N/A")
        else:
            print(f"{nombre:<25}${registro['value']/1_000_000:,.0f} M "
                  f"({registro['date']}; {registro['tag']})")

if __name__ == "__main__":
    datos = descargar_datos(TICKER)
    mostrar_resultados(obtener_mercado(TICKER), obtener_balance_sec(datos))
