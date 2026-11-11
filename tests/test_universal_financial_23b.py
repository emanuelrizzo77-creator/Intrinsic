import unittest
from universal_financial_23b import normalize_balance_23b

END = '2025-12-31'
def fact(value, end=END, unit='USD', filed='2026-02-20'):
    return {'units': {unit: [{'form': '10-K', 'end': end, 'filed': filed, 'val': value}]}}

def sample():
    return {'facts': {'us-gaap': {
        'CashAndCashEquivalentsAtCarryingValue': fact(10270000000),
        'LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities': fact(43941000000),
        'LongTermDebtAndCapitalLeaseObligations': fact(42119000000),
        'AccountsPayableTradeCurrent': fact(5649000000),
        'AccountsPayableAndAccruedLiabilitiesCurrent': fact(14813000000),
        'AccountsReceivableNetCurrent': fact(5000000000),
        'InventoryNet': fact(4000000000),
    }, 'dei': {'EntityCommonStockSharesOutstanding': fact(4300723069, '2026-02-18', 'shares')}}}

class Test23B(unittest.TestCase):
    def test_ko_debt_reconciliation(self):
        r = normalize_balance_23b(sample(), [END])[0]
        self.assertEqual(r['Current debt'], 1822000000)
        self.assertEqual(r['Total debt'], 43941000000)
        self.assertEqual(r['Net debt (cash-only)'], 33671000000)
    def test_trade_payables_not_combined(self):
        r = normalize_balance_23b(sample(), [END])[0]
        self.assertEqual(r['Payables'], 5649000000)
        self.assertEqual(r['Payables and accrued liabilities'], 14813000000)
        self.assertEqual(r['Partial operating NWC'], 3351000000)
    def test_shares_snapshot(self):
        r = normalize_balance_23b(sample(), [END])[0]
        self.assertEqual(r['Shares outstanding'], 4300723069)
        self.assertEqual(r['Shares measurement date'], '2026-02-18')
    def test_missing_not_zero(self):
        r = normalize_balance_23b({'facts': {}}, [END])[0]
        self.assertIsNone(r['Net debt (cash-only)'])
        self.assertIsNone(r['Shares outstanding'])
        self.assertIsNone(r['Partial operating NWC'])
    def test_no_issued_shares_substitution(self):
        p = sample()
        p['facts']['dei'] = {}
        p['facts']['us-gaap']['CommonStockSharesIssued'] = fact(5000000000, unit='shares')
        self.assertIsNone(normalize_balance_23b(p, [END])[0]['Shares outstanding'])
    def test_combined_payables_not_used_as_trade(self):
        p = sample()
        del p['facts']['us-gaap']['AccountsPayableTradeCurrent']
        r = normalize_balance_23b(p, [END])[0]
        self.assertIsNone(r['Payables'])
        self.assertIsNone(r['Partial operating NWC'])
    def test_no_double_count_total_debt(self):
        p = sample()
        p['facts']['us-gaap']['LongTermDebtAndCapitalLeaseObligationsCurrent'] = fact(1822000000)
        r = normalize_balance_23b(p, [END])[0]
        self.assertEqual(r['Total debt'], 43941000000)

if __name__ == '__main__':
    unittest.main()
