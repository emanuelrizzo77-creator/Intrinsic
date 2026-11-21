"""Insurer inputs (intrinsic/insurance_inputs.py) and the equity portfolio in the equity engine. Synthetic data."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic import bank_model as bm  # noqa: E402
from intrinsic import insurance_inputs as ii  # noqa: E402
from intrinsic.sector_routing import classify_sic  # noqa: E402


def row(year, ni, equity, div=1.0, buy=0.0):
    return {'Fiscal year end': f'{year}-12-31', 'Net income to common': ni, 'Common equity': equity,
            'Common dividends': div, 'Buybacks': buy, 'Goodwill': 0.0, 'Intangibles': 0.0}


def series(values):
    return {f'{y}-12-31': {'value': v, 'tag': 'x'} for y, v in values.items()}


YEARS = range(2019, 2025)
EXTRA = {
    'Investment gains': series({y: (20.0 if y % 2 else -10.0) for y in YEARS}),
    'Dividend income': {},
    'Premiums earned': {}, 'Net investment income': {},
    'Equity securities (fair value)': series({y: 100.0 for y in YEARS}),
    'Equity securities (cost)': series({y: 40.0 for y in YEARS}),
    'AOCI': series({y: -5.0 for y in YEARS}),
}


def rows():
    return [row(y, 10.0 + (20.0 if y % 2 else -10.0) * (1 - ii.TAX_RATE), 300.0 + 10 * i) for i, y in enumerate(YEARS)]


class OperatingFigures(unittest.TestCase):
    def test_portfolio_after_tax(self):
        self.assertAlmostEqual(ii.portfolio_after_tax(100.0, 40.0, 0.21), 100.0 - 0.21 * 60.0)
        self.assertEqual(ii.portfolio_after_tax(100.0, 120.0, 0.21), 100.0)      # no tax credit on a loss

    def test_gains_removed_and_portfolio_separated(self):
        out, notes = ii.operating_history(rows(), EXTRA, separate=True)
        pat = 100.0 - 0.21 * 60.0
        div = 0.02 * 100.0 * (1 - 0.21)                    # untagged dividends: assumed yield on average fair value
        for r in out:
            self.assertAlmostEqual(r['Net income to common'], 10.0 - div, places=9)    # gains swing gone
            self.assertAlmostEqual(r['Common equity'], r['Reported common equity'] + 5.0 - pat, places=9)
            self.assertAlmostEqual(r['Equity portfolio (after tax)'], pat)
        roes = [r['ROE'] for r in out if r['ROE'] is not None]
        self.assertEqual(len(roes), len(out) - 1)
        self.assertTrue(any('not tagged' in n for n in notes))

    def test_without_separation_only_gains_and_aoci_change(self):
        out, _ = ii.operating_history(rows(), EXTRA, separate=False)
        for r in out:
            self.assertAlmostEqual(r['Net income to common'], 10.0, places=9)
            self.assertAlmostEqual(r['Common equity'], r['Reported common equity'] + 5.0, places=9)
            self.assertIsNone(r['Equity portfolio (after tax)'])

    def test_tagged_dividend_income_is_used(self):
        extra = {**EXTRA, 'Dividend income': series({y: 4.0 for y in YEARS})}
        out, notes = ii.operating_history(rows(), extra, separate=True)
        self.assertAlmostEqual(out[-1]['Portfolio dividends (after tax)'], 4.0 * (1 - 0.21))
        self.assertFalse(any('not tagged' in n for n in notes))


class PortfolioInTheModels(unittest.TestCase):
    def history(self):
        out, _ = ii.operating_history(rows(), EXTRA, separate=True)
        return out

    def test_portfolio_adds_its_value_to_both_models(self):
        h = self.history()
        a = bm.run(h, 0.08, 0.025, 10.0, 'base')
        b = bm.run(h, 0.08, 0.025, 10.0, 'base', portfolio=50.0)
        for m in ('excess_return', 'ddm'):
            self.assertAlmostEqual(b[m]['equity_value'] - a[m]['equity_value'], 50.0, places=9)
            self.assertAlmostEqual(b[m]['per_share'] - a[m]['per_share'], 5.0, places=9)
        self.assertAlmostEqual(b['midpoint'] - a['midpoint'], 5.0, places=9)
        bv = b['assumptions']['drivers']['book_value']['value']
        self.assertAlmostEqual(b['justified_pb'], b['excess_return']['equity_value'] / (bv + 50.0))

    def test_zero_portfolio_is_the_bank_engine(self):
        h = self.history()
        self.assertEqual(bm.run(h, 0.08, 0.025, 10.0)['midpoint'], bm.run(h, 0.08, 0.025, 10.0, portfolio=0.0)['midpoint'])


class Routing(unittest.TestCase):
    def test_insurers_route_to_the_equity_engine(self):
        for sic in (6311, 6321, 6331, 6411):
            self.assertEqual(classify_sic(sic).model, 'insurance_equity')
        self.assertEqual(classify_sic(6021).model, 'bank_equity')


if __name__ == '__main__':
    unittest.main()
