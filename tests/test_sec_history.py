import unittest
from intrinsic.sec_history import analyze_historical_23c

ENDS = ['2022-12-31','2023-12-31','2024-12-31','2025-12-31']
def fact(vals, unit='USD', instant=False):
    return {'units': {unit: [dict(end=e, **({} if instant else {'start':f'{int(e[:4])-1}-12-31'}), val=v, form='10-K', filed=f'{int(e[:4])+1}-02-20') for e,v in zip(ENDS,vals)]}}

def sample():
    gaap = {
        'RevenueFromContractWithCustomerExcludingAssessedTax':fact([100,110,120,130]),
        'OperatingIncomeLoss':fact([20,22,24,26]),
        'DepreciationDepletionAndAmortization':fact([5,5,6,6]),
        'PaymentsToAcquirePropertyPlantAndEquipment':fact([7,7,8,8]),
        'IncomeTaxExpenseBenefit':fact([3,4,4,5]),
        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest':fact([15,20,20,25]),
        'CashAndCashEquivalentsAtCarryingValue':fact([10]*4,instant=True),
        'AccountsReceivableNetCurrent':fact([20,22,24,26],instant=True),
        'InventoryNet':fact([5,6,7,8],instant=True),
        'AccountsPayableTradeCurrent':fact([10,11,12,13],instant=True),
        'LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities':fact([50]*4,instant=True),
        'LongTermDebtAndCapitalLeaseObligations':fact([40]*4,instant=True),
    }
    return {'entityName':'Test Co','facts':{'us-gaap':gaap}}

class Test23C(unittest.TestCase):
    def test_ratios_and_delta(self):
        data = analyze_historical_23c(sample())
        self.assertEqual(len(data['rows']),4)
        self.assertAlmostEqual(data['rows'][-1]['Revenue growth'], 130/120-1)
        self.assertEqual(data['rows'][-1]['Delta partial NWC'],2)
        self.assertAlmostEqual(data['rows'][-1]['Effective tax rate'],.2)
        self.assertAlmostEqual(data['rows'][-1]['Historical FCFF (partial NWC proxy)'],16.8)
        self.assertFalse(data['ready_for_automatic_dcf'])
    def test_missing_tax_not_zero(self):
        p=sample(); del p['facts']['us-gaap']['IncomeTaxExpenseBenefit']
        d=analyze_historical_23c(p)
        self.assertIsNone(d['rows'][-1]['Effective tax rate'])
        self.assertIsNone(d['rows'][-1]['Historical FCFF (partial NWC proxy)'])
        self.assertIn('Missing latest Effective tax rate',d['latest_data_blockers'])
    def test_bad_period_rejected(self):
        p=sample(); p['facts']['us-gaap']['OperatingIncomeLoss']['units']['USD'][-1]['start']='2025-10-01'
        self.assertIsNone(analyze_historical_23c(p)['rows'][-1]['EBIT'])
    def test_invalid_n(self):
        with self.assertRaises(ValueError): analyze_historical_23c(sample(),last_n=1)
if __name__=='__main__': unittest.main()
