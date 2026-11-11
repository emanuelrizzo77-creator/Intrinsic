import unittest
from universal_financial_23a import normalize_balance_23a

def fact(value, end='2025-12-31', unit='USD'):
    return {'units': {unit: [{'form':'10-K','end':end,'filed':'2026-02-20','val':value}]}}

class Test23A(unittest.TestCase):
    def test_dei_shares_and_payables(self):
        payload={'facts': {'us-gaap': {
            'CashAndCashEquivalentsAtCarryingValue':fact(100),
            'LongTermDebtCurrent':fact(40),
            'LongTermDebtNoncurrent':fact(160),
            'AccountsReceivableNetCurrent':fact(30),
            'InventoryNet':fact(20),
            'AccountsPayableCurrent':fact(15)},
            'dei':{'EntityCommonStockSharesOutstanding':fact(10,unit='shares')}}}
        row=normalize_balance_23a(payload,['2025-12-31'])[0]
        self.assertEqual(row['Shares outstanding'],10)
        self.assertEqual(row['Partial operating NWC'],35)
        self.assertEqual(row['Net debt (cash-only)'],100)
    def test_missing_not_zero(self):
        row=normalize_balance_23a({'facts':{}},['2025-12-31'])[0]
        self.assertIsNone(row['Shares outstanding'])
        self.assertIsNone(row['Net debt (cash-only)'])
    def test_issued_shares_not_accepted(self):
        row=normalize_balance_23a({'facts':{'us-gaap':{'CommonStockSharesIssued':fact(100,unit='shares')}}},['2025-12-31'])[0]
        self.assertIsNone(row['Shares outstanding'])
if __name__=='__main__': unittest.main()
