import unittest
from automatic_forecast_engine import generar_forecast_automatico
from assumptions_engine import validar_hipotesis


def sample():
    rows = []
    for i in range(5):
        rows.append({
            "Fiscal year end": f"{2021+i}-12-31",
            "Revenue growth": [None, .10, .12, .11, .13][i],
            "EBIT margin": [.05, .03, .07, .10, .12][i],
            "D&A / Revenue": [.07, .08, .09, .08, .09][i],
            "CapEx / Revenue": [.12, .11, .10, .15, .18][i],
        })
    return {"rows": rows}


class TestAutoForecast(unittest.TestCase):
    def test_scenarios_validate(self):
        result = generar_forecast_automatico(sample())
        for assumptions in result["scenarios"].values():
            self.assertTrue(validar_hipotesis(assumptions))
            self.assertEqual(len(assumptions["growth"]), 5)

    def test_deterministic(self):
        self.assertEqual(generar_forecast_automatico(sample()), generar_forecast_automatico(sample()))

    def test_missing_data_fails(self):
        data = sample()
        for row in data["rows"]:
            row["CapEx / Revenue"] = None
        with self.assertRaises(ValueError):
            generar_forecast_automatico(data)

    def test_volatile_hypergrowth_decays(self):
        data = sample()
        for row, g in zip(data["rows"], [None, .61, .002, 1.26, 1.14]):
            row["Revenue growth"] = g
        data["rows"].append({
            "Fiscal year end": "2026-12-31", "Revenue growth": .65,
            "EBIT margin": .60, "D&A / Revenue": .02, "CapEx / Revenue": .03,
        })
        result = generar_forecast_automatico(data)
        growth = result["scenarios"]["base"]["growth"]
        self.assertEqual(result["diagnostics"]["Revenue growth"]["normalization_method"], "volatility_decay_provisional")
        self.assertGreater(growth[0], growth[-1])
        self.assertLess(growth[-1], .30)

    def test_scenario_direction(self):
        scenarios = generar_forecast_automatico(sample())["scenarios"]
        for i in range(5):
            self.assertLessEqual(scenarios["conservative"]["growth"][i], scenarios["base"]["growth"][i])
            self.assertGreaterEqual(scenarios["optimistic"]["ebit_margin"][i], scenarios["base"]["ebit_margin"][i])


if __name__ == "__main__":
    unittest.main()
