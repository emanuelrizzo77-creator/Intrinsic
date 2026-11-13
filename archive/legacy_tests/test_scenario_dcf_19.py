import math
import unittest
from scenario_dcf import calcular_dcf, calcular_matriz_sensibilidad


class TestDCF19(unittest.TestCase):
    def setUp(self):
        self.forecast = [{"fcff": 100.0}] * 5

    def test_valuation_identities(self):
        result = calcular_dcf(self.forecast, .10, .02, -20, 10)
        self.assertAlmostEqual(result["enterprise_value"], result["pv_fcff"] + result["pv_terminal"])
        self.assertAlmostEqual(result["equity_value"], result["enterprise_value"] + 20)
        self.assertAlmostEqual(result["intrinsic_price"], result["equity_value"] / 10)

    def test_wacc_increase_reduces_price_for_positive_flows(self):
        low = calcular_dcf(self.forecast, .08, .02, 0, 10)["intrinsic_price"]
        high = calcular_dcf(self.forecast, .12, .02, 0, 10)["intrinsic_price"]
        self.assertGreater(low, high)

    def test_growth_increase_raises_price_for_positive_terminal_fcff(self):
        low = calcular_dcf(self.forecast, .10, .01, 0, 10)["intrinsic_price"]
        high = calcular_dcf(self.forecast, .10, .03, 0, 10)["intrinsic_price"]
        self.assertLess(low, high)

    def test_company_specific_sensitivity(self):
        matrix = calcular_matriz_sensibilidad(self.forecast, .10, .02, -20, 10)
        expected = calcular_dcf(self.forecast, .10, .02, -20, 10)["intrinsic_price"]
        self.assertAlmostEqual(matrix["prices"][2][2], expected)

    def test_invalid_inputs(self):
        for kwargs in [
            {"wacc": .02, "terminal_growth": .02},
            {"wacc": -1.1},
            {"shares": 0},
            {"net_debt": float("nan")},
        ]:
            args = dict(wacc=.10, terminal_growth=.02, net_debt=0, shares=10)
            args.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                calcular_dcf(self.forecast, **args)
        with self.assertRaises(ValueError):
            calcular_dcf([{"fcff": float("inf")}], .10, .02, 0, 10)


if __name__ == "__main__":
    unittest.main()
