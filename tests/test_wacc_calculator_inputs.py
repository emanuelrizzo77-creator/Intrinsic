"""Milestone 19B: pure-unit tests; no SEC/Yahoo calls."""
import math
import unittest
from intrinsic.wacc_calculator import calculate_cost_of_equity, calculate_wacc


class TestWacc19B(unittest.TestCase):
    def setUp(self):
        self.inputs = dict(risk_free_rate=.04, beta=1.04,
                           equity_risk_premium=.05, cost_of_debt=.05,
                           tax_rate=.21, market_equity=3_852_635_209_728,
                           total_debt=40_294_000_000)

    def test_capm(self):
        self.assertAlmostEqual(calculate_cost_of_equity(.04, 1.04, .05), .092)

    def test_wacc_identity(self):
        r = calculate_wacc(**self.inputs)
        self.assertAlmostEqual(r['wacc'], r['equity_weight'] * .092 + r['debt_weight'] * .0395)

    def test_weights_sum_one(self):
        r = calculate_wacc(**self.inputs)
        self.assertAlmostEqual(r['equity_weight'] + r['debt_weight'], 1)

    def test_zero_debt(self):
        self.inputs['total_debt'] = 0
        r = calculate_wacc(**self.inputs)
        self.assertAlmostEqual(r['wacc'], .092)
        self.assertEqual(r['debt_weight'], 0)

    def test_tax_boundaries(self):
        for tax in (0, 1):
            self.inputs['tax_rate'] = tax
            self.assertTrue(math.isfinite(calculate_wacc(**self.inputs)['wacc']))

    def test_negative_beta_rejected(self):
        with self.assertRaises(ValueError):
            calculate_cost_of_equity(.04, -.5, .05)

    def test_nonfinite_capm_rejected(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                calculate_cost_of_equity(.04, value, .05)

    def test_nonfinite_wacc_inputs_rejected(self):
        for key in self.inputs:
            with self.subTest(key=key):
                p = dict(self.inputs, **{key: float('nan')})
                with self.assertRaises(ValueError):
                    calculate_wacc(**p)

    def test_bool_inputs_rejected(self):
        for key in self.inputs:
            with self.subTest(key=key):
                p = dict(self.inputs, **{key: True})
                with self.assertRaises(ValueError):
                    calculate_wacc(**p)

    def test_invalid_capital_rejected(self):
        for key, value in [('market_equity', 0), ('total_debt', -1), ('tax_rate', 1.1), ('cost_of_debt', -0.01)]:
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    calculate_wacc(**dict(self.inputs, **{key: value}))


if __name__ == '__main__':
    unittest.main()
