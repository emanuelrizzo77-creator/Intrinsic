
import unittest

from intrinsic.wacc_calculator import (
    calculate_cost_of_equity,
    calculate_wacc
)


class TestWACC(unittest.TestCase):

    def test_capm(self):
        result = calculate_cost_of_equity(
            0.04, 1.0, 0.05
        )
        self.assertAlmostEqual(result, 0.09)

    def test_all_equity(self):
        result = calculate_wacc(
            risk_free_rate=0.04,
            beta=1.0,
            equity_risk_premium=0.05,
            cost_of_debt=0.05,
            tax_rate=0.21,
            market_equity=100,
            total_debt=0
        )
        self.assertAlmostEqual(result["wacc"], 0.09)

    def test_negative_debt(self):
        with self.assertRaises(ValueError):
            calculate_wacc(
                0.04, 1.0, 0.05,
                0.05, 0.21, 100, -10
            )


if __name__ == "__main__":
    unittest.main()
