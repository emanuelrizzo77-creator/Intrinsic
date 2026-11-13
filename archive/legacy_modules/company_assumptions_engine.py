"""INTRINSIC — Milestone 18D: company-specific, illustrative DCF assumptions.

Consumes audited historical ratios (18C). Does NOT modify the dashboard or
assumptions_engine. Scenarios are transparent heuristics, not predictions.
Alphabet is blocked until complete D&A and comparable NWC inputs are available.
"""
from __future__ import annotations

import argparse
import math
from copy import deepcopy

from historical_ratios_engine import obtener_ratios_empresa
from googl_alternative_18h import obtener_ratios_alternativos_googl
from assumptions_engine import validar_hipotesis, proyectar_escenario

HORIZON = 5
# Research assumptions, not sourced SEC observations. Change explicitly if needed.
POLICY = {
    "MSFT": {"terminal_growth_anchor": 0.045, "growth_ceiling": 0.22},
    "AAPL": {"terminal_growth_anchor": 0.035, "growth_ceiling": 0.16},
    "NVDA": {"terminal_growth_anchor": 0.06, "growth_ceiling": 0.35},
    "GOOGL": {"terminal_growth_anchor": 0.035, "growth_ceiling": 0.22},  # illustrative policy, not SEC data
}
MIN_OBSERVATIONS = 2


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _clamp(x, low, high):
    return max(low, min(high, x))


def _blend(start, end, step, horizon=HORIZON):
    """Linear convergence, with year 5 equal to end."""
    return start + (end - start) * (step / horizon)


def _required_summary(result):
    summary = result.get("summary", {})
    missing = []
    values = {}
    for metric in ("growth", "ebit_margin", "da_ratio", "capex_ratio", "nwc_ratio"):
        item = summary.get(metric, {})
        value = item.get("median")
        if not _finite(value) or item.get("observations", 0) < MIN_OBSERVATIONS:
            missing.append(metric)
        else:
            values[metric] = float(value)
    return values, missing


def generar_escenarios_empresa(ticker, datos_historicos=None):
    """Build five-year conservative/base/optimistic assumptions.

    `datos_historicos` can be injected for offline tests. Missing data blocks
    generation; no implicit zero, no substitute AR-AP for complete NWC.
    """
    ticker = ticker.strip().upper()
    if ticker not in POLICY:
        raise ValueError(f"Ticker no configurado para escenarios: {ticker}")
    if datos_historicos is not None:
        result = datos_historicos
        if ticker == "GOOGL" and result.get("methodology") != "GOOGL_DEPRECIATION_ONLY_AR_MINUS_AP_PROXY":
            raise ValueError("GOOGL requiere ratios alternativos etiquetados explícitamente")
    elif ticker == "GOOGL":
        result = obtener_ratios_alternativos_googl()
    else:
        result = obtener_ratios_empresa(ticker)
    if result.get("ticker") != ticker:
        raise ValueError("El ticker de los datos históricos no coincide con el solicitado")
    values, missing = _required_summary(result)
    if missing:
        raise ValueError(f"{ticker}: faltan métricas recientes verificables: {', '.join(missing)}")

    # Projector's validator currently requires 0 <= nwc_ratio < 1.
    # Do not silently force negative historical working-capital ratios to zero.
    if not 0 <= values["nwc_ratio"] < 1:
        raise ValueError(f"{ticker}: nwc_ratio={values['nwc_ratio']:.2%} incompatible con el validador actual; revisión manual requerida")
    if values["da_ratio"] < 0 or values["capex_ratio"] < 0:
        raise ValueError("D&A y CapEx históricos deben ser no negativos")

    policy = POLICY[ticker]
    historical_growth = values["growth"]
    # Cap extraordinary growth instead of extrapolating NVIDIA's 114% median.
    initial_growth = _clamp(historical_growth, -0.10, policy["growth_ceiling"])
    anchor = policy["terminal_growth_anchor"]
    base_growth = [_blend(initial_growth, anchor, i) for i in range(1, HORIZON + 1)]
    historical_margin = _clamp(values["ebit_margin"], 0.01, 0.90)
    historical_da = values["da_ratio"]
    historical_capex = values["capex_ratio"]
    historical_nwc = values["nwc_ratio"]

    # Explicit policy adjustments relative to the base case. They are NOT
    # statistical confidence intervals or externally validated forecasts.
    scenario_adjustments = {
        "conservative": {"growth": -0.04, "margin": -0.035, "capex": 0.025, "nwc": 0.02},
        "base": {"growth": 0.0, "margin": 0.0, "capex": 0.0, "nwc": 0.0},
        "optimistic": {"growth": 0.04, "margin": 0.025, "capex": -0.015, "nwc": -0.01},
    }
    scenarios = {}
    for name, adj in scenario_adjustments.items():
        # For a conservative scenario, margins fade; for optimistic, rise.
        margin_target = _clamp(historical_margin + adj["margin"], 0.01, 0.90)
        scenario = {
            "growth": [_clamp(g + adj["growth"], -0.30, 1.0) for g in base_growth],
            "ebit_margin": [_blend(historical_margin, margin_target, i) for i in range(1, HORIZON + 1)],
            "da_ratio": [historical_da] * HORIZON,
            "capex_ratio": [_clamp(historical_capex + adj["capex"], 0.0, 1.0)] * HORIZON,
            "nwc_ratio": _clamp(historical_nwc + adj["nwc"], 0.0, 0.99),
        }
        validar_hipotesis(scenario)
        scenarios[name] = scenario

    return {
        "ticker": ticker,
        "company": result.get("company", ticker),
        "scenarios": scenarios,
        "historical_medians": values,
        "historical_years": {key: result["summary"][key]["years"] for key in values},
        "policy": deepcopy(policy),
        "warnings": list(result.get("warnings", [])) + [
            "Escenarios ilustrativos basados en reglas explícitas; NO son predicciones ni recomendaciones de inversión.",
            "NVIDIA CapEx usa la definición más amplia de activos productivos cuando falta PP&E.",
            "Tax rate, WACC, terminal value y deuda neta se calculan fuera de este módulo.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Genera escenarios DCF ilustrativos por empresa")
    parser.add_argument("ticker", choices=("MSFT", "AAPL", "NVDA", "GOOGL"))
    parser.add_argument("--preview-fcff", action="store_true", help="Proyectar FCFF con tasa fiscal ilustrativa del 21%")
    args = parser.parse_args()
    try:
        result = generar_escenarios_empresa(args.ticker)
    except ValueError as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"\nINTRINSIC — COMPANY ASSUMPTIONS | {result['company']} ({result['ticker']})")
    print("Historical medians:")
    for metric, value in result["historical_medians"].items():
        print(f"  {metric:<14} {value:>8.2%}  FY {result['historical_years'][metric]}")
    for name, scenario in result["scenarios"].items():
        print(f"\n{name.upper()}")
        for metric in ("growth", "ebit_margin", "da_ratio", "capex_ratio"):
            print(f"  {metric:<14} " + "  ".join(f"{v:6.2%}" for v in scenario[metric]))
        print(f"  nwc_ratio      {scenario['nwc_ratio']:.2%}")
    if args.preview_fcff:
        history = obtener_ratios_empresa(args.ticker)
        last = history["ratios"][-1]
        for name, scenario in result["scenarios"].items():
            projected = proyectar_escenario(last["revenue"], last["year"], scenario)
            print(f"\n{name.upper()} projected FCFF (USD M): " + ", ".join(f"{r['fcff']/1e6:,.0f}" for r in projected))
    for warning in result["warnings"]:
        print("WARNING:", warning)


if __name__ == "__main__":
    main()
