
import unittest

from scenario_dcf import calcular_dcf


class TestScenarioDCF(unittest.TestCase):

    def setUp(self):
        self.forecast = [
            {"fcff": 100_000_000},
            {"fcff": 110_000_000},
            {"fcff": 120_000_000}
        ]

    def test_dcf_returns_positive_value(self):
        resultado = calcular_dcf(
            self.forecast,
            0.10,
            0.025,
            0,
            10_000_000
        )

        self.assertGreater(
            resultado["intrinsic_price"], 0
        )

    def test_higher_wacc_reduces_value(self):
        bajo = calcular_dcf(
            self.forecast, 0.09, 0.025,
            0, 10_000_000
        )

        alto = calcular_dcf(
            self.forecast, 0.12, 0.025,
            0, 10_000_000
        )

        self.assertGreater(
            bajo["intrinsic_price"],
            alto["intrinsic_price"]
        )

    def test_higher_growth_increases_value(self):
        bajo = calcular_dcf(
            self.forecast, 0.10, 0.02,
            0, 10_000_000
        )

        alto = calcular_dcf(
            self.forecast, 0.10, 0.03,
            0, 10_000_000
        )

        self.assertGreater(
            alto["intrinsic_price"],
            bajo["intrinsic_price"]
        )

    def test_invalid_terminal_growth(self):
        with self.assertRaises(ValueError):
            calcular_dcf(
                self.forecast,
                0.025,
                0.03,
                0,
                10_000_000
            )


if __name__ == "__main__":
    unittest.main()
