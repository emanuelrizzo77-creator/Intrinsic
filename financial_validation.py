
import math


def validar_numero(valor, nombre):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"{nombre} debe ser numérico")

    if not math.isfinite(valor):
        raise ValueError(f"{nombre} debe ser finito")

    return float(valor)


def validar_fcff(ebit, tax_rate, da, capex, delta_nwc, fcff):
    valores = [
        validar_numero(v, nombre)
        for nombre, v in [
            ("EBIT", ebit),
            ("Tax Rate", tax_rate),
            ("D&A", da),
            ("CapEx", capex),
            ("Delta NWC", delta_nwc),
            ("FCFF", fcff),
        ]
    ]

    ebit, tax_rate, da, capex, delta_nwc, fcff = valores

    if not 0 <= tax_rate <= 1:
        raise ValueError("Tax Rate debe estar entre 0 y 1")

    calculado = ebit * (1 - tax_rate) + da - capex - delta_nwc

    return math.isclose(calculado, fcff, rel_tol=1e-9, abs_tol=0.01)


def validar_enterprise_value(pv_fcff, pv_terminal, enterprise_value):
    calculado = validar_numero(pv_fcff, "PV FCFF") + validar_numero(
        pv_terminal, "PV Terminal"
    )
    return math.isclose(
        calculado,
        validar_numero(enterprise_value, "Enterprise Value"),
        rel_tol=1e-9,
        abs_tol=0.01,
    )


def validar_equity_value(enterprise_value, net_debt, equity_value):
    calculado = (
        validar_numero(enterprise_value, "Enterprise Value")
        - validar_numero(net_debt, "Net Debt")
    )

    return math.isclose(
        calculado,
        validar_numero(equity_value, "Equity Value"),
        rel_tol=1e-9,
        abs_tol=0.01,
    )


def validar_precio(equity_value, shares, intrinsic_price):
    equity_value = validar_numero(equity_value, "Equity Value")
    shares = validar_numero(shares, "Shares")

    if shares <= 0:
        raise ValueError("Shares debe ser positivo")

    calculado = equity_value / shares

    return math.isclose(
        calculado,
        validar_numero(intrinsic_price, "Intrinsic Price"),
        rel_tol=1e-9,
        abs_tol=0.01,
    )


def validar_terminal_growth(wacc, growth):
    wacc = validar_numero(wacc, "WACC")
    growth = validar_numero(growth, "Terminal Growth")

    if wacc <= growth:
        raise ValueError("Terminal Growth debe ser inferior al WACC")

    return True
