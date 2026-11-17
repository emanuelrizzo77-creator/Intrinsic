"""Security Market Line arithmetic (intrinsic/sml.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic import sml  # noqa: E402


class SmlTests(unittest.TestCase):
    def test_required_return_is_capm(self):
        self.assertAlmostEqual(sml.required_return(0.04, 1.2, 0.05), 0.10)

    def test_line_passes_through_rf_and_market(self):
        xs, ys = sml.line(0.04, 0.05, beta_max=2.0, n=21)
        self.assertEqual(xs[0], 0.0)
        self.assertAlmostEqual(ys[0], 0.04)
        self.assertAlmostEqual(ys[10], 0.09)   # beta 1 = market return

    def test_implied_wacc_recovers_known_rate(self):
        value_at = lambda w: 100.0 / (w - 0.02)     # Gordon growth, value falls as WACC rises
        w = sml.implied_wacc(value_at, market_price=100.0 / (0.09 - 0.02), lo=0.025, hi=0.40, tol=1e-9)
        self.assertAlmostEqual(w, 0.09, places=6)

    def test_implied_wacc_none_when_price_out_of_range(self):
        value_at = lambda w: 100.0 / (w - 0.02)
        self.assertIsNone(sml.implied_wacc(value_at, 1e9, lo=0.025, hi=0.40))
        self.assertIsNone(sml.implied_wacc(value_at, 1.0, lo=0.025, hi=0.40))
        self.assertIsNone(sml.implied_wacc(value_at, None, lo=0.025, hi=0.40))
        self.assertIsNone(sml.implied_wacc(lambda w: None, 50.0, lo=0.025, hi=0.40))

    def test_implied_cost_of_equity_inverts_wacc(self):
        ke, kd_at, we, wd = 0.10, 0.04, 0.8, 0.2
        wacc = we * ke + wd * kd_at
        self.assertAlmostEqual(sml.implied_cost_of_equity(wacc, kd_at, we, wd), ke)
        self.assertIsNone(sml.implied_cost_of_equity(wacc, kd_at, 0.0, 1.0))

    def test_implied_beta(self):
        self.assertAlmostEqual(sml.implied_beta(0.10, 0.04, 0.05), 1.2)
        self.assertIsNone(sml.implied_beta(None, 0.04, 0.05))
        self.assertIsNone(sml.implied_beta(0.10, 0.04, 0.0))


if __name__ == '__main__':
    unittest.main()
