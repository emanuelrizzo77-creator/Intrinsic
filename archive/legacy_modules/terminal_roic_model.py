
import math


def calcular_terminal_roic(
    nopat_terminal,
    terminal_growth,
    roic,
    wacc,
    forecast_years,
):
    valores = {
        "NOPAT": nopat_terminal,
        "Growth": terminal_growth,
        "ROIC": roic,
        "WACC": wacc,
    }

    if any(
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or not math.isfinite(v)
        for v in valores.values()
    ):
        raise ValueError("Invalid financial inputs")

    if nopat_terminal <= 0:
        raise ValueError("NOPAT must be positive")

    if not 0 <= terminal_growth < wacc:
        raise ValueError(
            "Growth must be nonnegative and below WACC"
        )

    if not 0 < roic <= 1:
        raise ValueError("ROIC must be between 0 and 1")

    if not isinstance(forecast_years, int) or isinstance(
        forecast_years, bool
    ) or forecast_years <= 0:
        raise ValueError("Invalid forecast period")

    reinvestment_rate = terminal_growth / roic

    if reinvestment_rate > 1:
        raise ValueError(
            "Growth requires reinvestment above NOPAT"
        )

    net_reinvestment = (
        nopat_terminal * reinvestment_rate
    )

    fcff_terminal = (
        nopat_terminal - net_reinvestment
    )

    terminal_value = (
        fcff_terminal / (wacc - terminal_growth)
    )

    pv_terminal = (
        terminal_value / (1 + wacc) ** forecast_years
    )

    return {
        "reinvestment_rate": reinvestment_rate,
        "net_reinvestment": net_reinvestment,
        "fcff_terminal": fcff_terminal,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
    }
