import unittest
from unittest.mock import patch
from adaptive_forecast_26d import (select_methods, generar_forecast_adaptativo,
                                   evaluate_selector_walk_forward)


def history(n=12, missing_da=False):
    rows = []
    for i in range(n):
        rows.append({"Fiscal year end": f"{2010+i}-12-31",
                     "Revenue growth": .08 + .002*i,
                     "EBIT margin": .15 + .003*i,
                     "D&A / Revenue": None if missing_da and i >= 7 else .04,
                     "CapEx / Revenue": .06})
    return {"rows": rows}


def fake_engine(offset):
    def run(h):
        if len(h["rows"]) < 3 or any(r.get("D&A / Revenue") is None for r in h["rows"][-3:]):
            raise ValueError("Incomplete D&A")
        last = h["rows"][-1]
        b = {"growth": [last["Revenue growth"]+offset]*5,
             "ebit_margin": [last["EBIT margin"]+offset]*5,
             "da_ratio": [.04+offset]*5,
             "capex_ratio": [.06+offset]*5, "nwc_ratio": 0.0}
        return {"scenarios": {s: b for s in ("base", "conservative", "optimistic")}}
    return run


class Tests(unittest.TestCase):
    def setUp(self):
        self.p = patch.dict("adaptive_forecast_26d.ENGINES",
                            {"Normalized v2": fake_engine(0),
                             "Hybrid 26C": fake_engine(.002)}, clear=True)
        self.p.start()
        self.addCleanup(self.p.stop)

    def test_selection_deterministic(self):
        a = select_methods(history())
        self.assertEqual(a, select_methods(history()))
        self.assertTrue(a["diagnostics"]["growth"]["selection_supported"])

    def test_fallback_small_sample(self):
        a = select_methods(history(5), min_pairs=3)
        self.assertFalse(a["diagnostics"]["growth"]["selection_supported"])
        self.assertEqual(a["selected"]["growth"], "Normalized v2")

    def test_five_year_output(self):
        a = generar_forecast_adaptativo(history())
        self.assertEqual(len(a["scenarios"]["base"]["growth"]), 5)
        self.assertFalse(a["validated"])

    def test_missing_core_data_blocks(self):
        with self.assertRaises(ValueError):
            generar_forecast_adaptativo(history(missing_da=True))

    def test_outer_fold_excludes_test_year(self):
        h = history()
        a = evaluate_selector_walk_forward(h)
        h["rows"][-1]["Revenue growth"] = .99
        b = evaluate_selector_walk_forward(h)
        self.assertEqual(a["growth"][-1]["selected"], b["growth"][-1]["selected"])

    def test_duplicate_years_rejected(self):
        h = history()
        h["rows"][-1]["Fiscal year end"] = h["rows"][-2]["Fiscal year end"]
        with self.assertRaises(ValueError):
            select_methods(h)


if __name__ == "__main__":
    unittest.main()
