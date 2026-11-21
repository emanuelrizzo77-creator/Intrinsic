"""Pure pieces of the verdict backtest (validation/verdict_backtest.py) and the point-in-time payload filter."""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic.sec_data import annual_flows, payload_as_of  # noqa: E402
from validation import verdict_backtest as bt  # noqa: E402


def fact(val, end, filed, form='10-K'):
    return {'val': val, 'start': f'{int(end[:4]) - 1}{end[4:]}', 'end': end, 'filed': filed, 'form': form,
            'fp': 'FY', 'accn': filed}


class PointInTime(unittest.TestCase):
    PAYLOAD = {'facts': {'us-gaap': {'Revenues': {'units': {'USD': [
        fact(100.0, '2015-12-31', '2016-02-20'),
        fact(110.0, '2016-12-31', '2017-02-20'),
        fact(105.0, '2015-12-31', '2017-02-20'),            # 2015 restated in the 2016 10-K
    ]}}, 'Later': {'units': {'USD': [fact(1.0, '2017-12-31', '2018-02-20')]}}}}}

    def test_only_facts_filed_by_the_date_survive(self):
        pit = payload_as_of(self.PAYLOAD, '2016-03-01')
        rev = annual_flows(pit, ['Revenues'])
        self.assertEqual(list(rev), ['2015-12-31'])
        self.assertEqual(rev['2015-12-31']['value'], 100.0)          # the restatement is not known yet
        self.assertNotIn('Later', pit['facts']['us-gaap'])

    def test_later_date_sees_the_restatement_and_original_untouched(self):
        rev = annual_flows(payload_as_of(self.PAYLOAD, date(2017, 3, 1)), ['Revenues'])
        self.assertEqual(rev['2015-12-31']['value'], 105.0)
        self.assertEqual(len(self.PAYLOAD['facts']['us-gaap']['Revenues']['units']['USD']), 3)

    def test_quality_filter_and_log_excess(self):
        self.assertEqual(bt.quality_issue({'price': 0.5, 'value_to_price': 1.0}), 'price below $1')
        self.assertEqual(bt.quality_issue({'price': 20.0, 'value_to_price': -12.0}), '|value / price| above 10')
        self.assertIsNone(bt.quality_issue({'price': 20.0, 'value_to_price': 3.0}))
        self.assertAlmostEqual(bt.log_excess(0.21, 0.10), __import__('math').log(1.21 / 1.10))
        self.assertIsNone(bt.log_excess(-1.0, 0.1))
        self.assertIsNone(bt.log_excess(None, 0.1))

    def test_original_10k_filing_dates(self):
        self.assertEqual(bt.original_10k_filings(self.PAYLOAD),
                         {date(2015, 12, 31): date(2016, 2, 20), date(2016, 12, 31): date(2017, 2, 20),
                          date(2017, 12, 31): date(2018, 2, 20)})           # any one-year concept in the 10-K counts


class Prices(unittest.TestCase):
    SERIES = [(date(2020, 1, 2), 10.0), (date(2020, 1, 3), 11.0), (date(2021, 1, 4), 12.0), (date(2023, 1, 3), 15.0)]

    def test_split_factor_only_counts_later_splits(self):
        splits = [(date(2019, 6, 1), 2.0), (date(2020, 8, 31), 4.0), (date(2022, 6, 1), 3.0)]
        self.assertEqual(bt.split_factor_after(splits, date(2020, 1, 2)), 12.0)
        self.assertEqual(bt.split_factor_after(splits, date(2022, 6, 1)), 1.0)

    def test_on_or_after(self):
        self.assertEqual(bt.on_or_after(self.SERIES, date(2020, 1, 3)), (date(2020, 1, 3), 11.0))
        self.assertEqual(bt.on_or_after(self.SERIES, date(2020, 6, 1)), (date(2021, 1, 4), 12.0))
        self.assertIsNone(bt.on_or_after(self.SERIES, date(2024, 1, 1)))

    def test_total_return_needs_both_ends(self):
        self.assertAlmostEqual(bt.total_return(self.SERIES, date(2020, 1, 2), 1), 12.0 / 10.0 - 1)
        self.assertIsNone(bt.total_return(self.SERIES, date(2020, 1, 2), 5))       # series stops (delisted)
        self.assertIsNone(bt.total_return(self.SERIES, date(2020, 1, 3), 2))       # gap too long at the end

    def test_erp_uses_the_value_published_at_the_start_of_the_year(self):
        table = {'by_year': {'2014': {'implied_erp': 0.0578}, '2015': {'implied_erp': 0.0612}}}
        self.assertEqual(bt.erp_for(date(2015, 11, 20), table), 0.0578)
        self.assertIsNone(bt.erp_for(date(2010, 1, 1), table))


class Statistics(unittest.TestCase):
    def test_spearman(self):
        self.assertAlmostEqual(bt.spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1.0)
        self.assertAlmostEqual(bt.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(bt.spearman([1, 2, 2, 3], [1, 2, 2, 3]), 1.0)          # ties
        self.assertIsNone(bt.spearman([1, None], [2, 3]))

    def test_buckets_cover_every_row_once(self):
        rows = [{'k': i} for i in range(23)] + [{'k': None}]
        b = bt.quantile_buckets(rows, 'k', 5)
        self.assertEqual(sum(len(x) for x in b), 23)
        self.assertEqual(b[0][0]['k'], 0)
        self.assertEqual(b[-1][-1]['k'], 22)

    def test_company_bootstrap_keeps_companies_together(self):
        rows = [{'cik': c, 'x': float(c)} for c in range(10) for _ in range(3)]
        lo, hi = bt.bootstrap_by_company(rows, lambda s: bt.mean([r['x'] for r in s]), reps=300)
        self.assertLess(lo, 4.5)
        self.assertGreater(hi, 4.5)
        self.assertIsNone(bt.bootstrap_by_company(rows[:6], lambda s: 0.0))          # fewer than 5 companies

    def test_mean_and_median_skip_missing(self):
        self.assertEqual(bt.mean([1.0, None, 3.0]), 2.0)
        self.assertEqual(bt.median_([3.0, None, 1.0, 2.0]), 2.0)
        self.assertIsNone(bt.mean([None]))


if __name__ == '__main__':
    unittest.main()
