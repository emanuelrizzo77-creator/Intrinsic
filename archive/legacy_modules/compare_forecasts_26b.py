"""Milestone 26B — comparison of one-year forecast methods.

Retrospective analysis, not point-in-time validation.
"""
from math import isfinite
from statistics import median, mean
from automatic_forecast_engine import generar_forecast_automatico

METRICS = {
    "Revenue growth": "growth",
    "EBIT margin": "ebit_margin",
    "D&A / Revenue": "da_ratio",
    "CapEx / Revenue": "capex_ratio",
}

def valid(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x)

def compare_forecasts(historical, min_train=4):
    rows = sorted(historical["rows"], key=lambda r: r["Fiscal year end"])
    errors = {metric: {m: [] for m in
              ["Historical Median", "Recent Trend", "Normalized v2"]}
              for metric in METRICS}

    for split in range(min_train, len(rows)):
        train = rows[:split]
        actual = rows[split]

        try:
            normalized = generar_forecast_automatico({"rows": train})
        except ValueError:
            continue

        for source, target in METRICS.items():
            values = [r[source] for r in train if valid(r.get(source))]
            observed = actual.get(source)

            if len(values) < 3 or not valid(observed):
                continue

            predictions = {
                "Historical Median": median(values),
                "Recent Trend": mean(values[-2:]),
                "Normalized v2": normalized["scenarios"]["base"][target][0],
            }

            for method, predicted in predictions.items():
                errors[source][method].append(abs(predicted - observed) * 100)

    return {
        metric: {
            method: {
                "MAE_pp": round(mean(values), 2) if values else None,
                "n": len(values),
            }
            for method, values in methods.items()
        }
        for metric, methods in errors.items()
    }
