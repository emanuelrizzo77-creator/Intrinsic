
# INTRINSIC — WACC DATA CONNECTOR
# Milestone 12.2

from intrinsic.market_data import (
    obtener_mercado,
    obtener_balance_sec,
    obtener_deuda_en_fecha,
)

from intrinsic.sec_client import descargar_datos, resolver_cik
from intrinsic.industry_beta import bottom_up_beta


INTEREST_TAGS = ["InterestExpense", "InterestExpenseNonoperating", "InterestAndDebtExpense", "InterestExpenseDebt"]


def interest_coverage(datos_sec):
    """Latest fiscal year EBIT / interest expense from 10-K facts, or None.

    Returns {'coverage', 'ebit', 'interest', 'fiscal_end', 'interest_tag'}; coverage is inf when
    the company reports operating income but zero interest expense."""
    from intrinsic.sec_client import _registros_anuales

    def latest(tags):
        best = {}
        for prio, tag, reg, fin, filed in _registros_anuales(datos_sec, tags):
            if reg.get("fp") not in (None, "FY"):
                continue
            key = fin.isoformat()
            cand = (prio, -filed.toordinal())
            if key not in best or cand < best[key][0]:
                best[key] = (cand, float(reg["val"]), tag)
        return {k: (v[1], v[2]) for k, v in best.items()}

    ebit, interest = latest(["OperatingIncomeLoss"]), latest(INTEREST_TAGS)
    common = sorted(set(ebit) & set(interest))
    if not common:
        return None
    end = common[-1]
    from datetime import date
    if date.today().year - int(end[:4]) > 2:
        return None                      # tags stopped being reported: too old to describe today's debt
    e, (i, tag) = ebit[end][0], interest[end]
    if i < 0:
        return None
    return {"coverage": float("inf") if i == 0 else e / i, "ebit": e, "interest": i,
            "fiscal_end": end, "interest_tag": tag}


def _with_bottom_up_beta(result, datos_sec=None):
    """Add the industry (bottom-up) beta and interest coverage; the regression beta stays as a fallback."""
    try:
        result["interest_coverage"] = interest_coverage(datos_sec) if datos_sec else None
    except Exception:
        result["interest_coverage"] = None
    try:
        from intrinsic.sec_data import submissions_cached
        sic = submissions_cached(int(resolver_cik(result["ticker"]))).get("sic")
        bu = bottom_up_beta(sic, market_equity=result["market_equity"], total_debt=result["total_debt"])
    except Exception as exc:  # SEC profile unavailable: keep regression beta
        bu = {"beta": None, "reason": f"SIC lookup failed: {exc}"}
    result["beta_bottom_up"] = bu
    if bu.get("beta") is not None:
        result["beta_default"], result["beta_default_source"] = bu["beta"], "bottom_up"
    elif result["beta_adjusted"] is not None:
        result["beta_default"], result["beta_default_source"] = result["beta_adjusted"], "regression_blume"
    else:
        raise ValueError("No beta available: Yahoo Finance has no regression beta and the SEC industry "
                         f"could not be matched ({bu.get('reason')}). Use Manual Override.")
    return result


def calcular_kd_historico(datos_sec, deuda_inicio, deuda_final, fecha_final):
    """Estimate historical cost of debt from matching fiscal-year data."""
    from intrinsic.sec_client import _registros_anuales

    etiquetas = [
        "InterestExpenseNonoperating",
        "InterestExpense",
        "InterestAndDebtExpense",
    ]

    candidatos = [
        (prioridad, registro, fin, filed, etiqueta)
        for prioridad, etiqueta, registro, fin, filed
        in _registros_anuales(datos_sec, etiquetas)
        if fin.isoformat() == fecha_final
        and registro.get("fp") in (None, "FY")
    ]

    if not candidatos:
        return None

    prioridad, registro, fin, filed, etiqueta = min(
        candidatos,
        key=lambda x: (x[0], -x[3].toordinal()),
    )

    if deuda_inicio <= 0 or deuda_final < 0:
        return None

    deuda_promedio = (deuda_inicio + deuda_final) / 2

    if deuda_promedio <= 0 or registro["val"] < 0:
        return None

    return {
        "cost_of_debt": registro["val"] / deuda_promedio,
        "interest_expense": registro["val"],
        "average_debt": deuda_promedio,
        "interest_tag": etiqueta,
        "fiscal_end": fecha_final,
    }

def wacc_debt(bridge):
    """(total_debt, balance_date, source) for the WACC weights: the SAME audited debt the equity bridge deducts.

    The bridge includes finance-lease liabilities (and wider debt-tag coverage). Using a narrower figure for
    the WACC weights while deducting the wider one from enterprise value would value the debt two ways.
    """
    debt = (bridge or {}).get("total_debt")
    if debt is None:
        raise ValueError("Missing SEC debt data. Automatic WACC cannot be calculated.")
    return float(debt), bridge.get("balance_date"), "Equity bridge: " + str(bridge.get("debt_source"))


def _historical_kd(datos_sec, balance):
    """Interest expense / average debt from the plain debt tags (reference only; the default Kd is synthetic)."""
    from datetime import date

    deuda_largo, deuda_corto = balance.get("Long Term Debt"), balance.get("Current Debt")
    if deuda_largo is None or deuda_corto is None or deuda_largo["date"] != deuda_corto["date"]:
        return None
    fecha_final = deuda_largo["date"]
    try:
        fecha = date.fromisoformat(fecha_final)
        fecha_anterior = fecha.replace(year=fecha.year - 1)
    except ValueError:
        return None
    deuda_anterior = obtener_deuda_en_fecha(datos_sec, fecha_anterior.isoformat())
    deuda_actual = obtener_deuda_en_fecha(datos_sec, fecha_final)
    if deuda_anterior is None or deuda_actual is None:
        return None
    if (deuda_anterior["long_term_tag"] != deuda_actual["long_term_tag"]
            or deuda_anterior["current_tag"] != deuda_actual["current_tag"]):
        return None
    return calcular_kd_historico(datos_sec, deuda_anterior["total_debt"], deuda_actual["total_debt"], fecha_final)


def obtener_datos_wacc(ticker="MSFT"):
    from intrinsic.inputs import load_inputs

    mercado = obtener_mercado(ticker)
    datos_sec = descargar_datos(ticker)

    if mercado.get("currency") != "USD":
        raise ValueError(
            "This version only supports USD market data."
        )

    beta = mercado.get("beta")
    market_cap = mercado.get("market_cap")

    if market_cap is None:
        raise ValueError("Market capitalization unavailable from Yahoo Finance.")
    # The regression beta is optional: the default is the industry beta (see _with_bottom_up_beta).
    beta_raw = float(beta) if beta is not None else None
    beta_blume = 0.67 * beta_raw + 0.33 if beta_raw is not None else None

    total_debt, debt_date, debt_source = wacc_debt(load_inputs(ticker)["bridge"])

    return _with_bottom_up_beta({
        "ticker": ticker,
        "beta": beta_raw,
        "beta_adjusted": beta_blume,
        "market_equity": float(market_cap),
        "total_debt": total_debt,
        "market_price": mercado.get("price"),
        "shares": mercado.get("shares"),
        "market_date": mercado.get("retrieved_at"),
        "debt_date": debt_date,
        "debt_source": debt_source,
        "currency": mercado["currency"],
        "historical_kd": _historical_kd(datos_sec, obtener_balance_sec(datos_sec)),
    }, datos_sec)


if __name__ == "__main__":

    datos = obtener_datos_wacc()

    print("\nINTRINSIC — AUTOMATIC WACC DATA")
    print("-" * 50)

    for clave, valor in datos.items():
        print(f"{clave}: {valor}")
