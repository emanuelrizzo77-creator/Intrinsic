
import unittest
from copy import deepcopy

from assumptions_engine import SCENARIOS, proyectar_escenario
from scenario_dcf import calcular_dcf


class TestCapExSensitivity(unittest.TestCase):

    def setUp(self):
        self.revenue = 331_839_000_000
        self.year = 2026

        self.wacc = 0.0917
        self.terminal_growth = 0.025
        self.net_debt = -36_549_000_000
        self.shares = 7_426_194_552

    def valorar(self, hipotesis):
        forecast = proyectar_escenario(
            self.revenue,
            self.year,
            hipotesis,
        )

        return calcular_dcf(
            forecast,
            self.wacc,
            self.terminal_growth,
            self.net_debt,
            self.shares,
        )

    def test_higher_capex_reduces_value(self):
        base = deepcopy(SCENARIOS["base"])
        high_capex = deepcopy(base)

        high_capex["capex_ratio"] = [
            0.35, 0.33, 0.30, 0.28, 0.26
        ]

        base_value = self.valorar(base)["intrinsic_price"]
        high_value = self.valorar(high_capex)["intrinsic_price"]

        self.assertLess(high_value, base_value)

    def test_original_assumptions_unchanged(self):
        base = deepcopy(SCENARIOS["base"])
        original = deepcopy(base)

        self.valorar(base)

        self.assertEqual(base, original)


if __name__ == "__main__":
    unittest.main()

