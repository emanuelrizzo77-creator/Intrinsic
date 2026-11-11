
import unittest

from terminal_roic_model import calcular_terminal_roic


class TestTerminalROIC(unittest.TestCase):

    def setUp(self):
        self.params = {
            "nopat_terminal": 100_000_000_000,
            "terminal_growth": 0.025,
            "roic": 0.20,
            "wacc": 0.0917,
            "forecast_years": 5,
        }

    def calcular(self, **cambios):
        params = {**self.params, **cambios}
        return calcular_terminal_roic(**params)

    def test_reinvestment_rate(self):
        resultado = self.calcular()

        self.assertAlmostEqual(
            resultado["reinvestment_rate"],
            0.125,
        )

    def test_fcff_terminal(self):
        resultado = self.calcular()

        self.assertAlmostEqual(
            resultado["fcff_terminal"],
            87_500_000_000,
            delta=0.01,
        )

    def test_terminal_value_identity(self):
        resultado = self.calcular()

        esperado = (
            resultado["fcff_terminal"]
            / (0.0917 - 0.025)
        )

        self.assertAlmostEqual(
            resultado["terminal_value"],
            esperado,
            delta=0.01,
        )

    def test_higher_roic_increases_value(self):
        bajo = self.calcular(roic=0.10)
        alto = self.calcular(roic=0.25)

        self.assertGreater(
            alto["pv_terminal"],
            bajo["pv_terminal"],
        )

    def test_growth_above_wacc_rejected(self):
        with self.assertRaises(ValueError):
            self.calcular(terminal_growth=0.10)

    def test_invalid_roic_rejected(self):
        with self.assertRaises(ValueError):
            self.calcular(roic=0)


if __name__ == "__main__":
    unittest.main()
