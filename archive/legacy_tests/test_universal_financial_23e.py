import unittest
from universal_financial_23e import value_fcff_23e, calculate_wacc_23e, sensitivity_23e

class Test23E(unittest.TestCase):
    def setUp(self):
        self.f = {'rows': [{'Year': f'{2026+i}E', 'FCFF': 100.0} for i in range(5)]}
        self.k = {'wacc': .1, 'terminal_growth': .02, 'net_debt': 50, 'shares_outstanding': 10}
    def test_dcf_math(self):
        r = value_fcff_23e(self.f, **self.k)
        expected = sum(100/1.1**t for t in range(1,6)) + (102/.08)/1.1**5
        self.assertAlmostEqual(r['enterprise_value'], expected)
        self.assertAlmostEqual(r['intrinsic_value_per_share'], (expected-50)/10)
    def test_provisional(self):
        self.assertEqual(value_fcff_23e(self.f, **self.k)['status'], 'SCENARIO_ONLY')
    def test_invalid_spread(self):
        with self.assertRaises(ValueError):
            value_fcff_23e(self.f, **{**self.k, 'terminal_growth': .1})
    def test_missing_shares(self):
        with self.assertRaises(ValueError):
            value_fcff_23e(self.f, **{**self.k, 'shares_outstanding': None})
    def test_sensitivity(self):
        x = sensitivity_23e(self.f, wacc_values=[.08,.1], growth_values=[.02,.1], net_debt=50, shares_outstanding=10)
        self.assertEqual(len(x), 2)
        self.assertIsNone(x[1][1])
    def test_wacc_existing_engine(self):
        r = calculate_wacc_23e(risk_free_rate=.04, beta=1, equity_risk_premium=.05,
                               cost_of_debt=.05, tax_rate=.2, market_equity=100, total_debt=100)
        self.assertAlmostEqual(r['wacc'], .065)
    def test_date_warning(self):
        r = value_fcff_23e(self.f, **self.k, balance_date='2025-12-31', shares_date='2026-02-18')
        self.assertTrue(any('different measurement dates' in w for w in r['warnings']))

if __name__ == '__main__':
    unittest.main()
