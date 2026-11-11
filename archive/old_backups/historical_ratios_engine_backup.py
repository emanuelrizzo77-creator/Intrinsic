"""Intrinsic Milestone 18A: audited-input historical ratio extraction.

Uses existing SEC financial_engine and financial_reconciliation APIs.
Missing inputs remain None. No forecasting assumptions are inferred here.
"""
from __future__ import annotations

import argparse
import math
from statistics import median

from financial_engine import descargar_datos, construir_tabla
from financial_reconciliation import WORKING_CAPITAL_TAGS, extraer_saldos, calcular_onwc

SUPPORTED_TICKERS = ("MSFT", "AAPL", "NVDA", "GOOGL")


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def _ratio(numerator, denominator):
    n, d = _number(numerator), _number(denominator)
    return n / d if n is not None and d is not None and d > 0 else None


def _combine_da(dep, amort):
    """Do not treat absent amortization as zero."""
    d, a = _number(dep), _number(amort)
    return d + a if d is not None and a is not None else None


def calcular_ratios_historicos(tabla, onwc=None):
    """Return one row per annual revenue period, with missing ratios as None.

    Year keys are those provided by financial_engine (calendar year of FY end).
    """
    onwc = onwc or {}
    ingresos = tabla.get("Revenue", {})
    filas = []
    for year in sorted(ingresos):
        revenue = _number(ingresos[year])
        if revenue is None or revenue <= 0:
            continue
        prev_revenue = _number(ingresos.get(year - 1))
        growth = revenue / prev_revenue - 1 if prev_revenue is not None and prev_revenue > 0 else None
        ebit = _number(tabla.get("EBIT", {}).get(year))
        dep = _number(tabla.get("Depreciation", {}).get(year))
        amort = _number(tabla.get("Amortization", {}).get(year))
        da = _combine_da(dep, amort)
        capex = _number(tabla.get("CapEx", {}).get(year))
        nwc = _number(onwc.get(year))
        prev_nwc = _number(onwc.get(year - 1))
        delta_nwc = nwc - prev_nwc if nwc is not None and prev_nwc is not None else None
        delta_revenue = revenue - prev_revenue if prev_revenue is not None else None
        nwc_ratio = (delta_nwc / delta_revenue if delta_nwc is not None and delta_revenue is not None and abs(delta_revenue) > 1e-9 else None)
        filas.append({
            "year": year, "revenue": revenue, "growth": growth,
            "ebit": ebit, "ebit_margin": _ratio(ebit, revenue),
            "depreciation": dep, "amortization": amort, "da": da,
            "da_ratio": _ratio(da, revenue), "capex": capex,
            "capex_ratio": _ratio(capex, revenue), "onwc": nwc,
            "delta_nwc": delta_nwc, "nwc_ratio": nwc_ratio,
        })
    return filas


def resumir_ratios(filas, ultimos=3):
    """Historical medians, not forecasts; each metric uses available years."""
    metricas = ("growth", "ebit_margin", "da_ratio", "capex_ratio", "nwc_ratio")
    resumen = {}
    for metrica in metricas:
        validos = [(r["year"], r[metrica]) for r in filas if _number(r.get(metrica)) is not None]
        seleccion = validos[-ultimos:]
        resumen[metrica] = {
            "median": median(v for _, v in seleccion) if seleccion else None,
            "years": [y for y, _ in seleccion],
            "observations": len(seleccion),
        }
    return resumen


def obtener_ratios_empresa(ticker="MSFT", ultimos=3):
    ticker = ticker.strip().upper()
    if ticker not in SUPPORTED_TICKERS:
        raise ValueError(f"Ticker no habilitado: {ticker}")
    datos = descargar_datos(ticker)
    tabla = construir_tabla(datos)
    # ONWC is optional: its absence must not block other ratios.
    try:
        saldos = extraer_saldos(datos, WORKING_CAPITAL_TAGS)
        onwc = calcular_onwc(saldos)
    except (KeyError, ValueError, TypeError) as exc:
        onwc = {}
        onwc_warning = str(exc)
    else:
        onwc_warning = None
    filas = calcular_ratios_historicos(tabla, onwc)
    if not filas:
        raise ValueError(f"No hay ingresos anuales válidos para {ticker}")
    return {
        "ticker": ticker,
        "company": datos.get("entityName", ticker),
        "ratios": filas,
        "summary": resumir_ratios(filas, ultimos),
        "warnings": ([f"ONWC unavailable: {onwc_warning}"] if onwc_warning else []),
        "note": "Ratios históricos SEC, no son supuestos de proyección validados.",
    }


def _fmt(value):
    return "N/A" if value is None else f"{value:.2%}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", nargs="?", default="MSFT", choices=SUPPORTED_TICKERS)
    args = parser.parse_args()
    result = obtener_ratios_empresa(args.ticker)
    print(f"\nINTRINSIC — HISTORICAL RATIOS | {result['company']} ({args.ticker})")
    print(f"{'Year':<8}{'Growth':>12}{'EBIT %':>12}{'D&A %':>12}{'CapEx %':>12}{'ΔNWC/ΔRev':>14}")
    for row in result["ratios"][-6:]:
        print(f"{row['year']:<8}{_fmt(row['growth']):>12}{_fmt(row['ebit_margin']):>12}{_fmt(row['da_ratio']):>12}{_fmt(row['capex_ratio']):>12}{_fmt(row['nwc_ratio']):>14}")
    print("\nMedian of last 3 available observations per metric:")
    for name, stat in result["summary"].items():
        print(f"  {name}: {_fmt(stat['median'])} (years: {stat['years']})")
    for warning in result["warnings"]:
        print("WARNING:", warning)
    print("NOTE: Fiscal years are identified by calendar year of period end.")
    print("NOTE: D&A is unavailable if either depreciation or amortization is missing.")


if __name__ == "__main__":
    main()
