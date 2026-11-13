"""Intrinsic Milestone 25 — provisional automatic normalized FCFF assumptions.

Consumes the audited output of analyze_historical_23c(). No SEC fetching,
no valuation, and no assertion that the forecast is investment-grade.
"""
from __future__ import annotations

from math import isfinite
from statistics import median, pstdev

METRICS = {
    "Revenue growth": "growth",
    "EBIT margin": "ebit_margin",
    "D&A / Revenue": "da_ratio",
    "CapEx / Revenue": "capex_ratio",
}


def _valid(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _clip(value, low, high):
    return min(high, max(low, value))


def _blend(start, target):
    return [float(start + (target - start) * (i + 1) / 5) for i in range(5)]


def generar_forecast_automatico(historical):
    """Return scenarios, diagnostics, and warnings from audited SEC history.

    Raises ValueError rather than inventing missing core inputs.
    Ratios are decimals; five forecast periods are returned.
    """
    if not isinstance(historical, dict):
        raise ValueError("Historical audit must be a dictionary")
    rows = historical.get("rows")
    if not isinstance(rows, list) or len(rows) < 3:
        raise ValueError("At least three audited annual periods are required")
    if len({r.get("Fiscal year end") for r in rows}) != len(rows):
        raise ValueError("Duplicate fiscal year ends")
    rows = sorted(rows, key=lambda r: r["Fiscal year end"])

    series = {}
    for source in METRICS:
        observations = [float(r[source]) for r in rows if _valid(r.get(source))]
        if len(observations) < 3:
            raise ValueError(f"Insufficient annual observations: {source}")
        series[source] = observations

    # Use recent performance but shrink toward the multi-year median.
    # These fixed weights are provisional modeling choices, not empirical forecasts.
    starts = {}
    targets = {}
    diagnostics = {}
    limits = {
        "Revenue growth": (-0.50, 1.00),
        "EBIT margin": (0.0, 1.0),
        "D&A / Revenue": (0.0, 1.0),
        "CapEx / Revenue": (0.0, 1.0),
    }
    for source, observations in series.items():
        historical_median = median(observations)
        recent = median(observations[-2:])
        lo, hi = limits[source]
        # Avoid assuming a recent spike persists forever.
        initial = _clip(0.5 * historical_median + 0.5 * recent, lo, hi)
        terminal = _clip(0.7 * historical_median + 0.3 * recent, lo, hi)
        starts[source] = initial
        targets[source] = terminal
        diagnostics[source] = {
            "observations": len(observations),
            "historical_median": historical_median,
            "recent_two_median": recent,
            "first_forecast_anchor": initial,
            "year_five_target": terminal,
        }

    base = {
        metric: _blend(starts[source], targets[source])
        for source, metric in METRICS.items()
    }
    # High, volatile historical growth must not be extrapolated as a steady state.
    # Volatility-driven exponential decay is an explicitly provisional heuristic.
    growth_history = series["Revenue growth"]
    volatility = pstdev(growth_history)
    growth_anchor = starts["Revenue growth"]
    if growth_anchor > 0.30 and volatility > 0.20:
        from math import exp
        # A larger volatility increases the annual decay rate. No industry
        # benchmark or externally validated terminal growth is implied.
        decay_rate = min(0.75, volatility)
        base["growth"] = [
            float(_clip(growth_anchor * exp(-decay_rate * (i + 1)), -0.50, 1.00))
            for i in range(5)
        ]
        diagnostics["Revenue growth"]["normalization_method"] = "volatility_decay_provisional"
        diagnostics["Revenue growth"]["annual_decay_rate"] = decay_rate
    else:
        diagnostics["Revenue growth"]["normalization_method"] = "median_recent_blend"
    base["nwc_ratio"] = 0.0

    conservative = {k: list(v) if isinstance(v, list) else v for k, v in base.items()}
    optimistic = {k: list(v) if isinstance(v, list) else v for k, v in base.items()}
    for i in range(5):
        conservative["growth"][i] = _clip(base["growth"][i] - 0.03, -0.50, 1.00)
        conservative["ebit_margin"][i] = _clip(base["ebit_margin"][i] - 0.02, 0.0, 1.0)
        optimistic["growth"][i] = _clip(base["growth"][i] + 0.03, -0.50, 1.00)
        optimistic["ebit_margin"][i] = _clip(base["ebit_margin"][i] + 0.02, 0.0, 1.0)

    return {
        "scenarios": {"base": base, "conservative": conservative, "optimistic": optimistic},
        "diagnostics": diagnostics,
        "warnings": [
            "PROVISIONAL automatic forecast: heuristic weighting and volatility decay, not calibrated or validated.",
            "NWC ratio set to zero because audited NWC is partial and the projection engine disallows negative ratios.",
            "D&A and CapEx are forecast independently; economic consistency and terminal reinvestment require review.",
        ],
        "validated": False,
    }
