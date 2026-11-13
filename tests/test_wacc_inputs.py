import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic import wacc_inputs as mi
class MarketInputsTests(unittest.TestCase):
    def test_synthetic_rating_boundaries(self):
        self.assertEqual(mi.synthetic_rating(50.0)[0], 'Aaa/AAA')
        self.assertEqual(mi.synthetic_rating(float('inf'))[0], 'Aaa/AAA')
        rating, spread = mi.synthetic_rating(5.0)
        self.assertEqual(rating, 'A2/A')
        self.assertAlmostEqual(spread, 0.0078)
        self.assertEqual(mi.synthetic_rating(2.7)[0], 'Baa2/BBB')
        self.assertEqual(mi.synthetic_rating(2.9999995)[0], 'Baa2/BBB')   # gap between table rows
        self.assertEqual(mi.synthetic_rating(-3.0)[0], 'D2/D')
        self.assertEqual(mi.synthetic_rating(None), (None, None))

    def test_spreads_fall_as_coverage_rises(self):
        spreads = [mi.synthetic_rating(c)[1] for c in (0.1, 0.7, 1.0, 1.3, 1.6, 1.8, 2.1, 2.3, 2.6, 3.5, 5, 6, 7, 9)]
        self.assertEqual(spreads, sorted(spreads, reverse=True))

    def test_cost_of_debt_adds_spread_to_risk_free(self):
        kd, source = mi.cost_of_debt(0.04, 5.0)
        self.assertAlmostEqual(kd, 0.0478)
        self.assertIn('A2/A', source)
        self.assertEqual(mi.cost_of_debt(0.04, None)[0], None)

    def test_dated_sources(self):
        erp, src = mi.equity_risk_premium()
        self.assertTrue(0 < erp < 0.1)
        self.assertIn('2026-01-01', src)
        self.assertEqual(mi.marginal_tax_rate()[0], 0.25)


if __name__ == '__main__':
    unittest.main()
