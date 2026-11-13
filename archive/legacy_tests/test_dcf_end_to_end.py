
import unittest

from assumptions_engine import proyectar_escenario, SCENARIOS
from scenario_dcf import calcular_dcf

from financial_validation import (
    validar_fcff,
    validar_enterprise_value,
    validar_equity_value,
    validar_precio,
)


class TestDCFEndToEnd(unittest.TestCase):

    def setUp(self):
        self.revenue = 331_000_000_000
        self.year = 2026

        self.wacc = 0.0917
        self.growth = 0.025
        self.net_debt = -36_549_000_000
        self.shares = 7_426_194_552

        self.forecast = proyectar_escenario(
            self.revenue,
            self.year,
            SCENARIOS["base"],
        )

        self.valuation = calcular_dcf(
            self.forecast,
            self.wacc,
            self.growth,
            self.net_debt,
            self.shares,
        )

    def test_fcff_consistency(self):
        for row in self.forecast:
            self.assertAlmostEqual(
                row["fcff"],
                row["nopat"]
                + row["da"]
                - row["capex"]
                - row["delta_nwc"],
                places=2,
            )

    def test_enterprise_value(self):
        self.assertTrue(
            validar_enterprise_value(
                self.valuation["pv_fcff"],
                self.valuation["pv_terminal"],
                self.valuation["enterprise_value"],
            )
        )

    def test_equity_value(self):
        self.assertTrue(
            validar_equity_value(
                self.valuation["enterprise_value"],
                self.net_debt,
                self.valuation["equity_value"],
            )
        )

    def test_intrinsic_price(self):
        self.assertTrue(
            validar_precio(
                self.valuation["equity_value"],
                self.shares,
                self.valuation["intrinsic_price"],
            )
        )


if __name__ == "__main__":
    unittest.main()
