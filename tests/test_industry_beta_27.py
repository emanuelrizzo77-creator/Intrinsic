import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import industry_beta_27 as ib


class IndustryBetaTests(unittest.TestCase):
    def setUp(self):
        self.table = ib.load_industry_betas()

    def test_every_crosswalk_industry_exists_in_beta_file(self):
        names = {x[2] for x in ib.SIC_CROSSWALK} | {x[2] for x in ib.DIVISION_FALLBACK}
        self.assertEqual(names - set(self.table), set())

    def test_narrowest_range_wins(self):
        self.assertEqual(ib.industry_for_sic(3674), ('Semiconductor', 'specific'))
        self.assertEqual(ib.industry_for_sic(3672), ('Electronics (General)', 'specific'))
        self.assertEqual(ib.industry_for_sic(7389), ('Business & Consumer Services', 'broad'))
        self.assertEqual(ib.industry_for_sic('2834'), ('Drugs (Pharmaceutical)', 'specific'))

    def test_unmapped_and_missing_sic(self):
        self.assertIsNone(ib.industry_for_sic(None)[0])
        self.assertIsNone(ib.industry_for_sic(9999)[0])
        self.assertIsNone(ib.bottom_up_beta(None, market_equity=100, total_debt=0)['beta'])

    def test_hamada_relevering(self):
        bu = float(self.table['Semiconductor']['unlevered_beta_cash_corrected'])
        r = ib.bottom_up_beta(3674, market_equity=100.0, total_debt=50.0, tax=0.25, table=self.table)
        self.assertAlmostEqual(r['beta'], bu * (1 + 0.75 * 0.5))
        unlev = ib.bottom_up_beta(3674, market_equity=100.0, total_debt=0.0, table=self.table)
        self.assertAlmostEqual(unlev['beta'], bu)

    def test_user_industry_override(self):
        r = ib.bottom_up_beta(5961, market_equity=100.0, total_debt=0.0, industry='Software (Internet)')
        self.assertEqual((r['industry'], r['match']), ('Software (Internet)', 'user'))

    def test_invalid_capital_structure_refused(self):
        self.assertIsNone(ib.bottom_up_beta(3674, market_equity=0, total_debt=10)['beta'])
        self.assertIsNone(ib.bottom_up_beta(3674, market_equity=100, total_debt=-1)['beta'])


if __name__ == '__main__':
    unittest.main()
