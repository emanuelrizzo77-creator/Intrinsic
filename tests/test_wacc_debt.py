"""WACC weights use the same debt the equity bridge deducts (finance leases included)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic.wacc_calculator import calculate_wacc  # noqa: E402
from intrinsic.wacc_data import wacc_debt  # noqa: E402


class WaccDebtTests(unittest.TestCase):
    def test_uses_bridge_debt_including_finance_leases(self):
        bridge = {'total_debt': 106.9e9, 'balance_date': '2026-06-30',
                  'debt_source': 'SEC 23B + finance lease liabilities 66.59B'}
        debt, date, source = wacc_debt(bridge)
        self.assertEqual(debt, 106.9e9)
        self.assertEqual(date, '2026-06-30')
        self.assertIn('finance lease', source)

    def test_missing_debt_blocks(self):
        with self.assertRaises(ValueError):
            wacc_debt({'total_debt': None})
        with self.assertRaises(ValueError):
            wacc_debt({})

    def test_more_debt_raises_debt_weight(self):
        base = dict(risk_free_rate=0.045, beta=1.1, equity_risk_premium=0.0423, cost_of_debt=0.05, tax_rate=0.25,
                    market_equity=3_700e9)
        narrow = calculate_wacc(total_debt=40.3e9, **base)
        wide = calculate_wacc(total_debt=106.9e9, **base)
        self.assertGreater(wide['debt_weight'], narrow['debt_weight'])
        self.assertLess(wide['wacc'], narrow['wacc'])    # cheaper after-tax debt gets more weight


if __name__ == '__main__':
    unittest.main()
