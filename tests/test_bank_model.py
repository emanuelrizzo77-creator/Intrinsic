"""Bank equity engine (intrinsic/bank_model.py) and SEC history assembly (intrinsic/bank_inputs.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic import bank_model as bm  # noqa: E402
from intrinsic.bank_inputs import build_history  # noqa: E402


def _history(roes=(0.10, 0.12, 0.14, 0.13, 0.15, 0.14), payout=0.6, bv0=100e9):
    rows, bv = [], bv0
    rows.append({'Fiscal year end': '2019-12-31', 'Common equity': bv, 'Net income to common': 12e9, 'ROE': None,
                 'Book value growth': None, 'Payout ratio': payout})
    for i, roe in enumerate(roes):
        ni = roe * bv
        new_bv = bv + ni * (1 - payout)
        rows.append({'Fiscal year end': f'{2020 + i}-12-31', 'Common equity': new_bv, 'Net income to common': ni,
                     'ROE': roe, 'Book value growth': new_bv / bv - 1, 'Payout ratio': payout})
        bv = new_bv
    return rows


class BankModelTests(unittest.TestCase):
    def test_no_excess_return_means_value_equals_book(self):
        h = _history()
        ke, g = 0.10, 0.03
        out = bm.run(h, ke, g, shares=1e9, overrides={'roe_start': ke, 'roe_long': ke})
        ri = out['excess_return']
        self.assertAlmostEqual(ri['equity_value'], ri['book_value'], delta=1)
        self.assertAlmostEqual(out['justified_pb'], 1.0, places=9)

    def test_excess_return_matches_clean_surplus_perpetuity(self):
        # Flat ROE, book growth already at g: value = BV0 · (ROE − g) / (Ke − g), the Gordon P/B.
        h = _history()
        ke, g, roe = 0.10, 0.03, 0.15
        for r in h:
            if r['Book value growth'] is not None:
                r['Book value growth'] = g
        out = bm.run(h, ke, g, shares=1e9, overrides={'roe_start': roe, 'roe_long': roe})
        bv0 = h[-1]['Common equity']
        self.assertAlmostEqual(out['excess_return']['equity_value'] / bv0, (roe - g) / (ke - g), places=9)

    def test_ddm_equals_excess_return_when_consistent(self):
        # Stable bank: payout = 1 − g/ROE, earnings = ROE · BV, growth = g → both models must agree.
        ke, g, roe = 0.10, 0.03, 0.15
        h = _history(roes=(roe,) * 6, payout=1 - g / roe)
        for r in h:
            if r['Book value growth'] is not None:
                r['Book value growth'] = g
        bv0 = h[-1]['Common equity']
        h[-1]['Net income to common'] = roe * bv0 / (1 + g)   # last 3 years: E0 · (1+g) = ROE · BV0 next year
        h[-2]['Net income to common'] = h[-3]['Net income to common'] = h[-1]['Net income to common']
        out = bm.run(h, ke, g, shares=1e9, overrides={'roe_start': roe, 'roe_long': roe, 'payout_start': 1 - g / roe})
        self.assertAlmostEqual(out['ddm']['equity_value'] / out['excess_return']['equity_value'], 1.0, places=6)

    def test_higher_cost_of_equity_lowers_value(self):
        h = _history()
        lo = bm.run(h, 0.09, 0.025, 1e9)
        hi = bm.run(h, 0.11, 0.025, 1e9)
        self.assertGreater(lo['excess_return']['per_share'], hi['excess_return']['per_share'])
        self.assertGreater(lo['ddm']['per_share'], hi['ddm']['per_share'])

    def test_scenarios_are_ordered(self):
        res = bm.run_all(_history(), 0.10, 0.025, 1e9)
        v = {s: res[s]['excess_return']['per_share'] for s in bm.SCENARIOS}
        self.assertLessEqual(v['conservative'], v['base'])
        self.assertLessEqual(v['base'], v['optimistic'])

    def test_blocks_when_growth_not_below_cost_of_equity(self):
        out = bm.run(_history(), 0.03, 0.03, 1e9)
        self.assertEqual(out['status'], 'BLOCKED')
        self.assertTrue(any('Cost of equity' in b for b in out['assumptions']['blockers']))

    def test_blocks_without_shares(self):
        self.assertEqual(bm.run(_history(), 0.10, 0.025, None)['status'], 'BLOCKED')


def _fact(val, end, start=None, form='10-K', filed='2026-02-15'):
    r = {'val': val, 'end': end, 'form': form, 'filed': filed, 'accn': 'x'}
    if start:
        r['start'] = start
    return r


class BankInputsTests(unittest.TestCase):
    def _payload(self):
        years = [('2023', 10e9, 100e9), ('2024', 12e9, 110e9), ('2025', 13e9, 118e9)]
        flows = lambda v: {'units': {'USD': [_fact(x, f'{y}-12-31', f'{y}-01-01') for y, x in v]}}
        points = lambda v: {'units': {'USD': [_fact(x, f'{y}-12-31') for y, x in v]}}
        return {'facts': {'us-gaap': {
            'NetIncomeLoss': flows([(y, ni + 1e9) for y, ni, _ in years]),
            'DividendsPreferredStock': flows([(y, 1e9) for y, _, _ in years]),
            'StockholdersEquity': points([(y, eq + 10e9) for y, _, eq in years]),
            'PreferredStockValue': points([(y, 10e9) for y, _, _ in years]),
            'Goodwill': points([(y, 20e9) for y, _, _ in years]),
            'DividendsCommonStockCash': flows([(y, 3e9) for y, _, _ in years]),
            'PaymentsForRepurchaseOfCommonStock': flows([(y, 2e9) for y, _, _ in years]),
        }}}

    def test_common_equity_net_income_and_roe(self):
        rows, prov = build_history(self._payload())
        last = rows[-1]
        self.assertEqual(last['Common equity'], 118e9)                 # total − preferred
        self.assertEqual(last['Tangible common equity'], 98e9)         # − goodwill
        self.assertEqual(last['Net income to common'], 13e9)           # net income − preferred dividends
        self.assertAlmostEqual(last['ROE'], 13e9 / 110e9)              # on beginning-of-year common equity
        self.assertAlmostEqual(last['Payout ratio'], 5e9 / 13e9)       # (dividends + buybacks) / net income
        self.assertIsNone(rows[0]['ROE'])                              # no prior year
        self.assertEqual(prov['Net income to common'], 'Net income − preferred dividends')


if __name__ == '__main__':
    unittest.main()
