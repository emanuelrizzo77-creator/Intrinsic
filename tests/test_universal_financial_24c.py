import unittest
from unittest.mock import patch
from universal_financial_24c import assess_company, resolve_history, resolve_balance

def fact(v, end='2025-12-31', start=None, unit='USD'):
    r={'val':v,'end':end,'filed':'2026-02-20','form':'10-K'}
    if start:r['start']=start
    return {'units':{unit:[r]}}

class ResolverTests(unittest.TestCase):
    def test_reconstruct_da_from_nonoverlapping_components(self):
        p={'facts':{'us-gaap':{
            'Depreciation':fact(70,start='2025-01-01'),
            'AmortizationOfIntangibleAssets':fact(30,start='2025-01-01')}}}
        base={'rows':[{'Fiscal year end':'2025-12-31','Revenue':1000,'D&A verified':None,'EBIT':200,'CapEx':50}],
              'historical_medians':{},'sample_counts':{}}
        with patch('universal_financial_24c.history_24b',return_value=base):
            r=resolve_history(p)
        self.assertEqual(r['rows'][0]['D&A verified'],100)
        self.assertEqual(r['rows'][0]['D&A / Revenue'],.1)

    def test_does_not_invent_missing_amortization(self):
        p={'facts':{'us-gaap':{'Depreciation':fact(70,start='2025-01-01')}}}
        base={'rows':[{'Fiscal year end':'2025-12-31','Revenue':1000,'D&A verified':None,'EBIT':200,'CapEx':50}],
              'historical_medians':{},'sample_counts':{}}
        with patch('universal_financial_24c.history_24b',return_value=base):
            self.assertIsNone(resolve_history(p)['rows'][0]['D&A verified'])

    def test_debt_reconstruction(self):
        p={'facts':{'us-gaap':{'LongTermDebtNoncurrent':fact(400), 'LongTermDebtCurrent':fact(100)}}}
        b={'Fiscal year end':'2025-12-31','Total debt':None,'Net debt (cash-only)':None,
           'Cash':50,'Shares outstanding':None,'Partial operating NWC':None,
           'tags':{'Cash':'us-gaap:CashAndCashEquivalentsAtCarryingValue'},'warnings':[]}
        with patch('universal_financial_24c.balance_24b',return_value=[b]):
            row=resolve_balance(p,['2025-12-31'])[0]
        self.assertEqual(row['Total debt'],500)
        self.assertEqual(row['Net debt (cash-only)'],450)

    def test_nwc_missing_is_not_hard_blocker(self):
        h={'rows':[{'Fiscal year end':'2025-12-31',**{k:1 for k in ('Revenue','EBIT','D&A verified','CapEx','Effective tax rate')}}]*3}
        b={'Net debt (cash-only)':20,'Shares outstanding':10}
        with patch('universal_financial_24c.resolve_history',return_value=h), patch('universal_financial_24c.resolve_balance',return_value=[b]):
            r=assess_company({},'fcff')
        self.assertEqual(r['status'],'PROVISIONAL_SCENARIO_ONLY')
        self.assertTrue(any('ΔNWC' in w for w in r['warnings']))

    def test_financial_sector_excluded(self):
        h={'rows':[{'Fiscal year end':'2025-12-31','Revenue':1,'EBIT':1,'D&A verified':1,'CapEx':1,'Effective tax rate':.2}]*3}
        with patch('universal_financial_24c.resolve_history',return_value=h),patch('universal_financial_24c.resolve_balance',return_value=[{'Net debt (cash-only)':1,'Shares outstanding':1}]):
            self.assertEqual(assess_company({},'bank')['status'],'UNSUPPORTED_SECTOR')

if __name__=='__main__':unittest.main()
