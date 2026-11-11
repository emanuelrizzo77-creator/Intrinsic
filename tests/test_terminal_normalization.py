
import unittest

from terminal_normalization import (
    calcular_fcff_terminal_normalizado
)


class TestTerminalNormalization(unittest.TestCase):

    def setUp(self):
        self.params = {
            "revenue_final": 500_000_000_000,
            "terminal_growth": 0.025,
            "ebit_margin": 0.45,
            "tax_rate": 0.21,
            "da_ratio": 0.11,
            "capex_ratio": 0.20,
            "nwc_ratio": 0.03,
        }

    def calcular(self, **cambios):
        params = {**self.params, **cambios}
        return calcular_fcff_terminal_normalizado(
            **params
        )

    
    
    def test_revenue_terminal(self):
        resultado = self.calcular()

        self.assertAlmostEqual(
            resultado["revenue_terminal"],
            512_500_000_000,
            delta=0.01,
        )


    def test_fcff_identity(self):
        resultado = self.calcular()

        esperado = (
            resultado["nopat_terminal"]
            + resultado["da_terminal"]
            - resultado["capex_terminal"]
            - resultado["delta_nwc_terminal"]
        )

        self.assertAlmostEqual(
            resultado["fcff_terminal"],
            esperado,
        )

    def test_higher_capex_reduces_fcff(self):
        base = self.calcular(capex_ratio=0.20)
        elevado = self.calcular(capex_ratio=0.30)

        self.assertLess(
            elevado["fcff_terminal"],
            base["fcff_terminal"],
        )

    def test_higher_margin_increases_fcff(self):
        base = self.calcular(ebit_margin=0.45)
        mayor = self.calcular(ebit_margin=0.50)

        self.assertGreater(
            mayor["fcff_terminal"],
            base["fcff_terminal"],
        )

    def test_invalid_growth(self):
        with self.assertRaises(ValueError):
            self.calcular(terminal_growth=-0.01)


if __name__ == "__main__":
    unittest.main()
