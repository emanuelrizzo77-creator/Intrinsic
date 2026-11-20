"""Final verdict probabilities (intrinsic/verdict.py)."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic import verdict as vd  # noqa: E402


class VerdictTests(unittest.TestCase):
    def test_scenarios_are_the_20th_and_80th_percentiles(self):
        d = vd.value_distribution(80.0, 100.0, 125.0)
        self.assertEqual(d['kind'], 'lognormal')
        self.assertAlmostEqual(vd.cdf(d, 80.0), 0.20, places=6)
        self.assertAlmostEqual(vd.cdf(d, 125.0), 0.80, places=6)
        self.assertAlmostEqual(vd.cdf(d, 100.0), 0.50, places=6)

    def test_probabilities_sum_to_one(self):
        v = vd.verdict({'conservative': 70, 'base': 100, 'optimistic': 140}, 90, 0.15)
        self.assertAlmostEqual(sum(v['probabilities'].values()), 1.0, places=9)

    def test_fair_price_is_hold(self):
        v = vd.verdict({'conservative': 90, 'base': 100, 'optimistic': 111}, 100, 0.15)
        self.assertEqual(v['action'], 'hold')
        self.assertGreater(v['probabilities']['hold'], 0.5)

    def test_cheap_stock_is_buy_and_expensive_is_sell(self):
        prices = {'conservative': 160, 'base': 200, 'optimistic': 250}
        self.assertEqual(vd.verdict(prices, 100, 0.15)['action'], 'buy')
        self.assertEqual(vd.verdict(prices, 400, 0.15)['action'], 'sell')

    def test_wide_range_centred_on_price_is_hold(self):
        v = vd.verdict({'conservative': 170, 'base': 317, 'optimistic': 390}, 320, 0.15)
        self.assertLess(max(v['probabilities']['buy'], v['probabilities']['sell']), 0.5)
        self.assertEqual(v['action'], 'hold')

    def test_wider_margin_makes_hold_more_likely(self):
        prices = {'conservative': 90, 'base': 120, 'optimistic': 160}
        narrow = vd.verdict(prices, 100, 0.05)['probabilities']['hold']
        wide = vd.verdict(prices, 100, 0.35)['probabilities']['hold']
        self.assertGreater(wide, narrow)

    def test_normal_distribution_when_a_value_is_not_positive(self):
        d = vd.value_distribution(-5.0, 10.0, 25.0)
        self.assertEqual(d['kind'], 'normal')
        self.assertAlmostEqual(vd.cdf(d, -5.0), 0.20, places=6)

    def test_one_sided_range(self):
        v = vd.verdict({'conservative': None, 'base': 100, 'optimistic': 130}, 100, 0.15)
        self.assertTrue(v['one_sided'])
        d = v['distribution']
        self.assertAlmostEqual(d['spread'], math.log(1.3) / vd.Z80)

    def test_no_range_no_verdict(self):
        self.assertIsNone(vd.verdict({'conservative': None, 'base': 100, 'optimistic': None}, 100))
        self.assertIsNone(vd.verdict({'conservative': 90, 'base': None, 'optimistic': 110}, 100))
        self.assertIsNone(vd.verdict({'conservative': 90, 'base': 100, 'optimistic': 110}, 0))

    def test_quantile_inverts_cdf(self):
        d = vd.value_distribution(80.0, 100.0, 125.0)
        self.assertAlmostEqual(vd.cdf(d, vd.quantile(d, 0.9)), 0.9, places=6)


if __name__ == '__main__':
    unittest.main()
