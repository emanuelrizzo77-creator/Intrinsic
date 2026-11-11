import unittest
from universal_financial_24e import _shares
class Tests(unittest.TestCase):
 def test_year_end_share_snapshot(self):
  f={'us-gaap':{'CommonStockSharesOutstanding':{'units':{'shares':[{'end':'2025-12-31','val':465300000,'form':'10-K','filed':'2026-02-01'}]}}}}
  self.assertEqual(_shares(f,'2025-12-31')[0],465300000)
 def test_reject_weighted_average(self):
  f={'us-gaap':{'WeightedAverageNumberOfDilutedSharesOutstanding':{'units':{'shares':[{'end':'2025-12-31','start':'2025-01-01','val':100,'form':'10-K','filed':'2026-02-01'}]}}}}
  self.assertIsNone(_shares(f,'2025-12-31')[0])
 def test_reject_wrong_date(self):
  f={'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':[{'end':'2026-02-01','val':100,'form':'10-K','filed':'2026-02-01'}]}}}}
  self.assertIsNone(_shares(f,'2025-12-31')[0])
 def test_dei_fallback(self):
  f={'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':[{'end':'2025-12-31','val':100,'form':'10-K','filed':'2026-02-01'}]}}}}
  self.assertEqual(_shares(f,'2025-12-31')[0],100)
if __name__=='__main__':unittest.main()
