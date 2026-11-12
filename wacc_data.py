
# INTRINSIC — WACC DATA CONNECTOR
# Milestone 12.2

from market_data import (
    obtener_mercado,
    obtener_balance_sec,
    obtener_deuda_en_fecha,
)

from financial_engine import descargar_datos


def calcular_kd_historico(datos_sec, deuda_inicio, deuda_final, fecha_final):
    """Estimate historical cost of debt from matching fiscal-year data."""
    from financial_engine import _registros_anuales

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

def obtener_datos_wacc(ticker="MSFT"):

    mercado = obtener_mercado(ticker)
    datos_sec = descargar_datos(ticker)
    balance = obtener_balance_sec(datos_sec)

    if mercado.get("currency") != "USD":
        raise ValueError(
            "This version only supports USD market data."
        )

    beta = mercado.get("beta")
    market_cap = mercado.get("market_cap")

    if beta is None or market_cap is None:
        raise ValueError(
            "Missing beta or market capitalization."
        )

    deuda_largo = balance.get("Long Term Debt")
    deuda_corto = balance.get("Current Debt")

    if deuda_largo is None or deuda_corto is None:
        # Intrinsic 27 fallback: the model's audited bridge has broader debt-tag
        # coverage (short-term borrowings, carrying amounts, finance leases).
        from run_driver_27 import load_inputs
        br = load_inputs(ticker)["bridge"]
        if br.get("total_debt") is None:
            raise ValueError("Missing SEC debt data. Automatic WACC cannot be calculated.")
        return {
            "ticker": ticker, "beta": float(beta), "beta_adjusted": 0.67 * float(beta) + 0.33,
            "market_equity": float(market_cap), "total_debt": float(br["total_debt"]),
            "market_price": mercado.get("price"), "shares": mercado.get("shares"),
            "market_date": mercado.get("retrieved_at"), "debt_date": br["balance_date"],
            "debt_source": "Model 27 bridge: " + str(br.get("debt_source")),
            "currency": mercado["currency"], "historical_kd": None,
        }

    if deuda_largo["date"] != deuda_corto["date"]:
        raise ValueError(
            "Debt balances have different reporting dates."
        )

    total_debt = (
        deuda_largo["value"]
        + deuda_corto["value"]
    )


    
    # Estimate historical cost of debt using the latest annual balance.
    from datetime import date

    fecha_final = deuda_largo["date"]

    try:
        fecha = date.fromisoformat(fecha_final)
        fecha_anterior = fecha.replace(year=fecha.year - 1)
    except ValueError:
        fecha_anterior = None

    kd_historico = None

    if fecha_anterior is not None:
        deuda_anterior = obtener_deuda_en_fecha(
            datos_sec,
            fecha_anterior.isoformat(),
        )

        deuda_actual = obtener_deuda_en_fecha(
            datos_sec,
            fecha_final,
        )

        if deuda_anterior is not None and deuda_actual is not None:
            etiquetas_consistentes = (
                deuda_anterior["long_term_tag"] == deuda_actual["long_term_tag"]
                and deuda_anterior["current_tag"] == deuda_actual["current_tag"]
            )

            if etiquetas_consistentes:
                kd_historico = calcular_kd_historico(
                    datos_sec,
                    deuda_anterior["total_debt"],
                    deuda_actual["total_debt"],
                    fecha_final,
                )


    return {
        "ticker": ticker,
        "beta": float(beta),
        "beta_adjusted": 0.67 * float(beta) + 0.33,
        "market_equity": float(market_cap),
        "total_debt": float(total_debt),
        "market_price": mercado.get("price"),
        "shares": mercado.get("shares"),
        "market_date": mercado.get("retrieved_at"),
        "debt_date": deuda_largo["date"],
        "currency": mercado["currency"],
        "historical_kd": kd_historico,
    }


if __name__ == "__main__":

    datos = obtener_datos_wacc()

    print("\nINTRINSIC — AUTOMATIC WACC DATA")
    print("-" * 50)

    for clave, valor in datos.items():
        print(f"{clave}: {valor}")
