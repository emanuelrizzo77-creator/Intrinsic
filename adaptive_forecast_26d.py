"""Milestone 26D: per-metric walk-forward model selection.

Research-only, retrospective SEC companyfacts may contain later restatements.
Never uses the target year's value to select the model for that year.
Does not modify underlying engines or validate a DCF.
"""
from __future__ import annotations
from math import isfinite
from statistics import mean
from automatic_forecast_engine import generar_forecast_automatico
from hybrid_forecast_26c import generar_forecast_hibrido

METRICS = {
    "Revenue growth": "growth",
    "EBIT margin": "ebit_margin",
    "D&A / Revenue": "da_ratio",
    "CapEx / Revenue": "capex_ratio",
}
ENGINES = {"Normalized v2": generar_forecast_automatico,
           "Hybrid 26C": generar_forecast_hibrido}
DEFAULT = "Normalized v2"


def _valid(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x)


def _year(row):
    return int(str(row["Fiscal year end"])[:4])


def _rows(historical):
    if not isinstance(historical, dict) or not isinstance(historical.get("rows"), list):
        raise ValueError("Expected historical={'rows': [...]} ")
    rows = sorted(historical["rows"], key=lambda r: r["Fiscal year end"])
    years = [_year(r) for r in rows]
    if len(years) != len(set(years)):
        raise ValueError("Duplicate fiscal years")
    return rows


def _recent_contiguous_values(rows, metric, end_index):
    """Use consecutive annual values ending at the last training year only."""
    subset = []
    previous = None
    for row in reversed(rows[:end_index]):
        year = _year(row)
        if previous is not None and previous - year != 1:
            break
        if not _valid(row.get(metric)):
            break
        subset.append(row)
        previous = year
    return list(reversed(subset))


def _forecast(engine, rows):
    return engine({"rows": rows})["scenarios"]["base"]


def select_methods(historical, min_train=4, min_pairs=3):
    """Select on past one-year holdouts, using paired observations per metric.

    Falls back to Normalized v2 if evidence is insufficient or tied.
    Note: the complete forecast still requires both underlying engines to run.
    """
    rows = _rows(historical)
    if min_train < 3 or min_pairs < 1:
        raise ValueError("Invalid min_train or min_pairs")
    errors = {key: {name: [] for name in ENGINES} for key in METRICS.values()}
    periods = {key: [] for key in METRICS.values()}
    for split in range(min_train, len(rows)):
        actual = rows[split]
        # Training ends in the immediately preceding fiscal year.
        if _year(actual) - _year(rows[split - 1]) != 1:
            continue
        # Paired evaluation: both engines must succeed on the same training rows.
        try:
            forecasts = {name: _forecast(engine, rows[:split])
                         for name, engine in ENGINES.items()}
        except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError):
            continue
        for source, target in METRICS.items():
            if not _valid(actual.get(source)):
                continue
            # Reject gaps in the metric's recent training window.
            recent = _recent_contiguous_values(rows, source, split)
            if len(recent) < 3:
                continue
            preds = {}
            for name, forecast in forecasts.items():
                values = forecast.get(target)
                if not isinstance(values, (list, tuple)) or not values or not _valid(values[0]):
                    break
                preds[name] = values[0]
            if len(preds) != len(ENGINES):
                continue
            for name, predicted in preds.items():
                errors[target][name].append(abs(predicted - actual[source]) * 100)
            periods[target].append(_year(actual))
    selections = {}
    diagnostics = {}
    for target, by_model in errors.items():
        n = len(periods[target])
        maes = {name: mean(values) if values else None for name, values in by_model.items()}
        # Strictly better required; ties favor the documented default.
        best = DEFAULT
        if n >= min_pairs and maes["Hybrid 26C"] < maes[DEFAULT]:
            best = "Hybrid 26C"
        selections[target] = best
        diagnostics[target] = {
            "selected": best,
            "paired_n": n,
            "evaluation_years": periods[target],
            "mae_pp": maes,
            "selection_supported": n >= min_pairs,
            "reason": "lower past paired MAE" if n >= min_pairs else "insufficient paired history; fallback",
        }
    return {"selected": selections, "diagnostics": diagnostics,
            "selection_validated": False}


def generar_forecast_adaptativo(historical, min_train=4, min_pairs=3):
    """Return five-year scenarios assembled per metric from selected engines.

    Both engines must support the complete current history. Missing core data
    are never replaced with zeros or silently extrapolated.
    """
    rows = _rows(historical)
    selection = select_methods(historical, min_train=min_train, min_pairs=min_pairs)
    outputs = {name: engine({"rows": rows}) for name, engine in ENGINES.items()}
    scenarios = {}
    for scenario in ("base", "conservative", "optimistic"):
        combined = {}
        for target in METRICS.values():
            model = selection["selected"][target]
            values = outputs[model]["scenarios"][scenario][target]
            if len(values) != 5 or not all(_valid(v) for v in values):
                raise ValueError(f"Invalid five-year {target} from {model}")
            combined[target] = list(values)
        # No verified complete operating-NWC estimate: preserve provisional zero.
        combined["nwc_ratio"] = 0.0
        scenarios[scenario] = combined
    return {"scenarios": scenarios, "selection": selection,
            "validated": False,
            "warnings": [
                "RESEARCH ONLY: historical model selection is not point-in-time validated.",
                "Small paired samples can overfit; selection is not proof of forecast accuracy.",
                "Five-year DCF, NWC, CapEx/D&A consistency and terminal value are not validated.",
                "NWC ratio remains provisional zero, not an audited estimate.",
            ]}


def evaluate_selector_walk_forward(historical, min_train=4, min_pairs=3):
    """Outer chronological evaluation: select on prior years, test next year.

    Returns only paired eligible outer folds. No peeking at outer test actual
    in the selection step. Still subject to historical SEC restatements.
    """
    rows = _rows(historical)
    result = {key: [] for key in METRICS.values()}
    for split in range(min_train + min_pairs, len(rows)):
        if _year(rows[split]) - _year(rows[split - 1]) != 1:
            continue
        train = {"rows": rows[:split]}
        try:
            selected = select_methods(train, min_train, min_pairs)
            outputs = {name: _forecast(engine, rows[:split])
                       for name, engine in ENGINES.items()}
        except (ValueError, KeyError, TypeError, IndexError, ZeroDivisionError):
            continue
        for source, target in METRICS.items():
            if not _valid(rows[split].get(source)):
                continue
            if len(_recent_contiguous_values(rows, source, split)) < 3:
                continue
            if not selected["diagnostics"][target]["selection_supported"]:
                continue
            if any(not _valid(outputs[name][target][0]) for name in ENGINES):
                continue
            name = selected["selected"][target]
            result[target].append({
                "year": _year(rows[split]), "selected": name,
                "adaptive_error_pp": abs(outputs[name][target][0] - rows[split][source]) * 100,
                "v2_error_pp": abs(outputs[DEFAULT][target][0] - rows[split][source]) * 100,
                "hybrid_error_pp": abs(outputs["Hybrid 26C"][target][0] - rows[split][source]) * 100,
            })
    return result
