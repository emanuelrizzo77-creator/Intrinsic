import unittest
from intrinsic_24f_regression import classify

BASE={'end':'2025-12-31','period_type':'annual_flow','unit':'USD','form':'10-K','filed':'2026-02-01'}
def r(tag,value,**kwargs):return {**BASE,'tag':tag,'value':value,**kwargs}
class RegressionTests(unittest.TestCase):
    def test_proxy_not_full_da(self):
        x=classify([r('Depreciation',21136000000)],'2025-12-31')
        self.assertEqual(x['status'],'DEPRECIATION_ONLY_PROXY')
        self.assertFalse(x['dcf_eligible_as_verified'])
    def test_full_da(self):
        x=classify([r('DepreciationDepletionAndAmortization',22000000000)],'2025-12-31')
        self.assertTrue(x['dcf_eligible_as_verified'])
    def test_components(self):
        x=classify([r('Depreciation',20),r('AmortizationOfIntangibleAssets',3)],'2025-12-31')
        self.assertEqual(x['value'],23)
    def test_reject_instant_and_wrong_year(self):
        x=classify([r('Depreciation',20,period_type='instant'),r('Depreciation',30,end='2024-12-31')],'2025-12-31')
        self.assertEqual(x['status'],'MISSING_DA')
if __name__=='__main__':unittest.main()
