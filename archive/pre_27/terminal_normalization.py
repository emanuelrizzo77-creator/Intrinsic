
def calcular_fcff_terminal_normalizado(
    revenue_final,
    terminal_growth,
    ebit_margin,
    tax_rate,
    da_ratio,
    capex_ratio,
    nwc_ratio,
):
    if revenue_final <= 0:
        raise ValueError("Revenue debe ser positivo")

    if not 0 <= terminal_growth < 1:
        raise ValueError("Terminal growth inválido")

    if not 0 <= tax_rate < 1:
        raise ValueError("Tax rate inválido")

    if not 0 <= ebit_margin <= 1:
        raise ValueError("EBIT margin inválido")

    if not 0 <= da_ratio <= 1:
        raise ValueError("D&A ratio inválido")

    if not 0 <= capex_ratio <= 1:
        raise ValueError("CapEx ratio inválido")

    if not 0 <= nwc_ratio <= 1:
        raise ValueError("NWC ratio inválido")

    revenue_terminal = revenue_final * (
        1 + terminal_growth
    )

    ebit_terminal = (
        revenue_terminal * ebit_margin
    )

    nopat_terminal = (
        ebit_terminal * (1 - tax_rate)
    )

    da_terminal = (
        revenue_terminal * da_ratio
    )

    capex_terminal = (
        revenue_terminal * capex_ratio
    )

    delta_revenue = (
        revenue_terminal - revenue_final
    )

    delta_nwc_terminal = (
        delta_revenue * nwc_ratio
    )

    fcff_terminal = (
        nopat_terminal
        + da_terminal
        - capex_terminal
        - delta_nwc_terminal
    )

    return {
        "revenue_terminal": revenue_terminal,
        "nopat_terminal": nopat_terminal,
        "da_terminal": da_terminal,
        "capex_terminal": capex_terminal,
        "delta_nwc_terminal": delta_nwc_terminal,
        "fcff_terminal": fcff_terminal,
    }
