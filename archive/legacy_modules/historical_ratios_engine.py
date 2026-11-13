"""Intrinsic Milestone 18C — historical ratios with freshness and SEC-tag diagnostics.

Historical statistics are descriptive, NOT company-specific forecasts.
No absent financial metric is silently replaced by zero.
Compatible with financial_engine and financial_reconciliation APIs.
"""
from __future__ import annotations

import argparse
import math
from statistics import median

from financial_engine import descargar_datos, construir_tabla, extraer_metrica
from financial_reconciliation import WORKING_CAPITAL_TAGS, extraer_saldos, calcular_onwc

SUPPORTED_TICKERS = ("MSFT", "AAPL", "NVDA", "GOOGL")
METRICS = ("growth", "ebit_margin", "da_ratio", "capex_ratio", "nwc_ratio")
# These tags are for diagnostics only; do not automatically combine them.
TAG_HINTS = {
    "Depreciation / Amortization": (
        "Depreciation", "DepreciationDepletionAndAmortization",
        "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
        "DepreciationAmortizationAndAccretionNet", "AmortizationOfIntangibleAssets",
    ),
    "CapEx": (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForProceedsFromOtherInvestingActivities",
        "PaymentsToAcquireProductiveAssets",
    ),
    "Operating working capital": (
        "AccountsReceivableNetCurrent", "InventoryNet", "AccountsPayableCurrent",
        "AccountsNotesAndOtherReceivablesNetCurrent",
    ),
}


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _ratio(numerator, denominator):
    n, d = _number(numerator), _number(denominator)
    return n / d if n is not None and d is not None and d > 0 else None


def calcular_ratios_historicos(tabla, onwc=None, min_revenue_change_pct=0.02):
    """One row per year; NWC/revenue change unavailable when revenue change is tiny.

    A tiny denominator can yield economically misleading NWC ratios.
    The 2% threshold is a diagnostic rule, not an accounting convention.
    """
    if not 0 <= min_revenue_change_pct < 1:
        raise ValueError("min_revenue_change_pct debe estar entre 0 y 1")
    onwc = {} if onwc is None else onwc
    ingresos = tabla.get("Revenue", {})
    filas = []
    for year in sorted(ingresos):
        revenue = _number(ingresos[year])
        if revenue is None or revenue <= 0:
            continue
        previous = _number(ingresos.get(year - 1))
        growth = revenue / previous - 1 if previous is not None and previous > 0 else None
        ebit = _number(tabla.get("EBIT", {}).get(year))
        dep = _number(tabla.get("Depreciation", {}).get(year))
        amort = _number(tabla.get("Amortization", {}).get(year))
        da = dep + amort if dep is not None and amort is not None else None
        capex = _number(tabla.get("CapEx", {}).get(year))
        nwc = _number(onwc.get(year))
        prev_nwc = _number(onwc.get(year - 1))
        delta_nwc = nwc - prev_nwc if nwc is not None and prev_nwc is not None else None
        delta_revenue = revenue - previous if previous is not None else None
        nwc_ratio = None
        nwc_flag = None
        if delta_nwc is not None and delta_revenue is not None and previous is not None:
            if abs(delta_revenue) >= min_revenue_change_pct * previous and delta_revenue != 0:
                nwc_ratio = delta_nwc / delta_revenue
            else:
                nwc_flag = "Small revenue change; ΔNWC/ΔRevenue suppressed"
        filas.append({
            "year": year, "revenue": revenue, "growth": growth,
            "ebit": ebit, "ebit_margin": _ratio(ebit, revenue),
            "depreciation": dep, "amortization": amort, "da": da,
            "da_ratio": _ratio(da, revenue), "capex": capex,
            "capex_ratio": _ratio(capex, revenue), "onwc": nwc,
            "delta_nwc": delta_nwc, "nwc_ratio": nwc_ratio,
            "nwc_flag": nwc_flag,
        })
    return filas


def resumir_ratios(filas, ultimos=3, ventana_anios=4):
    """Median of up to `ultimos` observations from recent `ventana_anios` years.

    Never substitutes older values when recent observations are missing.
    """
    if ultimos < 1 or ventana_anios < 1:
        raise ValueError("ultimos y ventana_anios deben ser positivos")
    if not filas:
        return {m: {"median": None, "years": [], "observations": 0, "status": "NO_DATA"} for m in METRICS}
    ultimo_anio = max(r["year"] for r in filas)
    limite = ultimo_anio - ventana_anios + 1
    resumen = {}
    for metrica in METRICS:
        validos = [(r["year"], _number(r.get(metrica))) for r in filas if r["year"] >= limite]
        validos = sorted(((y, v) for y, v in validos if v is not None), key=lambda x: x[0])
        seleccion = validos[-ultimos:]
        resumen[metrica] = {
            "median": median(v for _, v in seleccion) if seleccion else None,
            "years": [y for y, _ in seleccion],
            "observations": len(seleccion),
            "status": "AVAILABLE" if len(seleccion) >= 2 else ("LIMITED" if seleccion else "MISSING_RECENT"),
        }
    return resumen


def diagnosticar_etiquetas(datos):
    """List whether candidate us-gaap tags have any annual 10-K records.

    This is NOT a declaration that similarly named tags are interchangeable.
    """
    facts = datos.get("facts", {}).get("us-gaap", {})
    diagnostico = {}
    for grupo, tags in TAG_HINTS.items():
        encontrados = []
        for tag in tags:
            records = facts.get(tag, {}).get("units", {}).get("USD", [])
            years = sorted({r.get("end", "")[:4] for r in records if r.get("form") == "10-K" and r.get("end")})
            if years:
                encontrados.append({"tag": tag, "last_year": years[-1]})
        diagnostico[grupo] = encontrados
    return diagnostico


def obtener_ratios_empresa(ticker="MSFT", ultimos=3, ventana_anios=4):
    ticker = ticker.strip().upper()
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(f"Ticker no habilitado: {ticker}")
    datos = descargar_datos(ticker)
    tabla = construir_tabla(datos)
    warnings = []
    sources = {"capex": "PaymentsToAcquirePropertyPlantAndEquipment"}
    if ticker == "NVDA":
        # NVIDIA reports purchases of productive assets (includes software/intangibles).
        # Never sum these tags: they may overlap.
        alternative = extraer_metrica(datos, ["PaymentsToAcquireProductiveAssets"])
        primary = tabla.get("CapEx", {})
        tabla["CapEx"] = {**alternative, **primary}
        sources["capex"] = "PP&E tag when available; otherwise PaymentsToAcquireProductiveAssets (broader definition)"
        warnings.append("NVDA CapEx fallback includes productive assets, software and intangibles; compare definitions before cross-company benchmarking")
    if ticker == "GOOGL":
        warnings.append("GOOGL: complete D&A and original AR+Inventory-AP NWC unavailable; do not infer zero")
    try:
        saldos = extraer_saldos(datos, WORKING_CAPITAL_TAGS)
        onwc = calcular_onwc(saldos)
    except (KeyError, ValueError, TypeError) as exc:
        onwc = {}
        warnings.append(f"ONWC unavailable: {exc}")
    filas = calcular_ratios_historicos(tabla, onwc)
    # Optional, explicitly different measure: receivables minus payables.
    # Does not overwrite operating NWC, because inventory is missing.
    if ticker == "GOOGL":
        facts = datos.get("facts", {}).get("us-gaap", {})
        def instant(tag):
            candidates = {}
            for r in facts.get(tag, {}).get("units", {}).get("USD", []):
                if r.get("form") != "10-K" or "start" in r or not all(k in r for k in ("end", "filed", "val")):
                    continue
                year = int(r["end"][:4])
                key = (r["end"], r["filed"])
                if year not in candidates or key > candidates[year][0]:
                    candidates[year] = (key, r["val"])
            return {year: value for year, (_, value) in candidates.items()}
        ar = instant("AccountsReceivableNetCurrent")
        ap = instant("AccountsPayableCurrent")
        ar_ap = {y: ar[y] - ap[y] for y in ar.keys() & ap.keys()}
        for row in filas:
            y = row["year"]
            row["ar_minus_ap"] = ar_ap.get(y)
            previous = ar_ap.get(y - 1)
            prev_revenue = tabla.get("Revenue", {}).get(y - 1)
            delta_revenue = row["revenue"] - prev_revenue if prev_revenue else None
            row["ar_ap_delta_ratio"] = (
                (ar_ap[y] - previous) / delta_revenue
                if y in ar_ap and previous is not None and delta_revenue is not None
                and abs(delta_revenue) >= 0.02 * prev_revenue and delta_revenue != 0 else None
            )
    if not filas:
        raise ValueError(f"No hay ingresos anuales válidos para {ticker}")
    resumen = resumir_ratios(filas, ultimos, ventana_anios)
    for metrica, stat in resumen.items():
        if stat["status"] != "AVAILABLE":
            warnings.append(f"{metrica}: {stat['status']} ({stat['observations']} recent observation(s))")
    for row in filas[-6:]:
        if row["nwc_flag"]:
            warnings.append(f"FY{row['year']} NWC: {row['nwc_flag']}")
    return {
        "ticker": ticker, "company": datos.get("entityName", ticker),
        "ratios": filas, "summary": resumen,
        "tag_diagnostics": diagnosticar_etiquetas(datos), "sources": sources,
        "warnings": warnings,
        "note": "Historical SEC ratios only; NOT validated forecast assumptions.",
    }


def _fmt(value):
    return "N/A" if value is None else f"{value:.2%}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", nargs="?", default="MSFT", choices=SUPPORTED_TICKERS)
    parser.add_argument("--diagnostics", action="store_true", help="Show SEC candidate tags")
    args = parser.parse_args()
    result = obtener_ratios_empresa(args.ticker)
    print(f"\nINTRINSIC — HISTORICAL RATIOS | {result['company']} ({args.ticker})")
    print(f"{'Year':<8}{'Growth':>12}{'EBIT %':>12}{'D&A %':>12}{'CapEx %':>12}{'ΔNWC/ΔRev':>14}")
    for row in result["ratios"][-6:]:
        print(f"{row['year']:<8}{_fmt(row['growth']):>12}{_fmt(row['ebit_margin']):>12}{_fmt(row['da_ratio']):>12}{_fmt(row['capex_ratio']):>12}{_fmt(row['nwc_ratio']):>14}")
    print("\nRecent historical medians (up to 3 observations from last 4 years):")
    for name, stat in result["summary"].items():
        print(f"  {name}: {_fmt(stat['median'])} | {stat['status']} | years: {stat['years']}")
    if args.ticker == "GOOGL":
        print("\nAlphabet alternative AR-AP / ΔRevenue (NOT full operating NWC):")
        for row in result["ratios"][-4:]:
            print(f"  {row['year']}: {_fmt(row.get('ar_ap_delta_ratio'))}")
    for warning in result["warnings"]:
        print("WARNING:", warning)
    if args.diagnostics:
        print("\nSEC candidate tag diagnostics (not automatically substituted):")
        for group, tags in result["tag_diagnostics"].items():
            print(f"  {group}:")
            for item in tags:
                print(f"    {item['tag']} (latest 10-K observation end year: {item['last_year']})")
            if not tags:
                print("    No candidate tags found")
    print("NOTE: Fiscal year keys use the calendar year of period end.")
    print("NOTE: Missing D&A components are not assumed to be zero.")


if __name__ == "__main__":
    main()
