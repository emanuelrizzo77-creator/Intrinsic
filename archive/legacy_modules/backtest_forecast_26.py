"""Milestone 26: preliminary historical forecast backtest.

Retrospective holdout test. Not a point-in-time backtest:
SEC companyfacts may include subsequently restated historical values.
"""
from math import isfinite
from automatic_forecast_engine import generar_forecast_automatico

METRICS = {
    "Revenue growth": "growth",
    "EBIT margin": "ebit_margin",
    "D&A / Revenue": "da_ratio",
    "CapEx / Revenue": "capex_ratio",
}

def backtest_forecast(historical, min_train=4):
    rows = sorted(
        historical["rows"],
        key=lambda row: row["Fiscal year end"]
    )

    results = []
    for split in range(min_train, len(rows)):
        train = {"rows": rows[:split]}
        actual = rows[split]

        try:
            forecast = generar_forecast_automatico(train)
        except ValueError:
            continue

        predicted = forecast["scenarios"]["base"]
        record = {"year": actual["Fiscal year end"][:4]}

        for source, target in METRICS.items():
            observed = actual.get(source)
            if (
                isinstance(observed, (int, float))
                and isfinite(observed)
            ):
                estimate = predicted[target][0]
                record[target + "_actual"] = observed
                record[target + "_predicted"] = estimate
                record[target + "_error_pp"] = (
                    estimate - observed
                ) * 100

        results.append(record)

    return results
