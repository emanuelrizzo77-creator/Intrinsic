import unittest
from universal_financial_24b import annual, point, balance_24b

class ResolverTests(unittest.TestCase):
    def test_annual_rejects_quarter(self):
        f={'us-gaap':{'PaymentsToAcquireProductiveAssets':{'units':{'USD':[
            {'form':'10-K','start':'2025-10-01','end':'2025-12-31','filed':'2026-02-01','val':5}]}}}}
        self.assertEqual(annual(f,['PaymentsToAcquireProductiveAssets'],'2025-12-31'),(None,None))
    def test_annual_alternative(self):
        f={'us-gaap':{'PaymentsToAcquireProductiveAssets':{'units':{'USD':[
            {'form':'10-K','start':'2025-01-01','end':'2025-12-31','filed':'2026-02-01','val':500}]}}}}
        self.assertEqual(annual(f,['PaymentsToAcquireProductiveAssets'],'2025-12-31')[0],500)
    def test_no_missing_to_zero(self):
        self.assertEqual(point({},['LongTermDebtNoncurrent'],'2025-12-31'),(None,None))
    def test_no_overlapping_total_debt(self):
        f={'facts':{'us-gaap':{}}}
        row=balance_24b(f,['2025-12-31'])[0]
        self.assertIsNone(row['Total debt'])
        self.assertEqual(row['NWC quality'],'MISSING')
    def test_instant_rejects_duration(self):
        f={'us-gaap':{'LongTermDebtNoncurrent':{'units':{'USD':[
            {'form':'10-K','start':'2025-01-01','end':'2025-12-31','filed':'2026-02-01','val':12}]}}}}
        self.assertIsNone(point(f,['LongTermDebtNoncurrent'],'2025-12-31')[0])

if __name__=='__main__': unittest.main()
