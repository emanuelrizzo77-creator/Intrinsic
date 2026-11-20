"""Foreign private issuers: form relabelling, IFRS mapping, currency conversion, ADS ratio (no network)."""
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic.foreign_filers import (FxConverter, ForeignFilerUnsupported, ads_ratio, is_foreign_filer,  # noqa: E402
                                      normalize_payload)
from intrinsic.sec_data import annual_flows, annual_points  # noqa: E402


def fixed_fx(rate, currency='GBP'):
    days = pd.date_range('2015-01-01', '2026-12-31', freq='D')
    return FxConverter(currency, series=pd.Series(rate, index=days))


def flow(val, year, form='20-F'):
    return {'val': val, 'start': f'{year}-01-01', 'end': f'{year}-12-31', 'form': form,
            'filed': f'{year + 1}-03-01', 'accn': f'a{year}', 'fp': 'FY'}


def point(val, year, form='20-F'):
    return {'val': val, 'end': f'{year}-12-31', 'form': form, 'filed': f'{year + 1}-03-01', 'accn': f'a{year}'}


def ifrs_payload(currency='GBP'):
    return {'entityName': 'Example plc', 'facts': {
        'dei': {'EntityCommonStockSharesOutstanding': {'units': {'shares': [point(1000, 2024)]}}},
        'ifrs-full': {
            'Revenue': {'units': {currency: [flow(100.0, 2022)]}},
            'RevenueFromContractsWithCustomers': {'units': {currency: [flow(110.0, 2023), flow(120.0, 2024),
                                                                       flow(999.0, 2022)]}},
            'ProfitLossFromOperatingActivities': {'units': {currency: [flow(20.0, 2024)]}},
            'PropertyPlantAndEquipment': {'units': {currency: [point(50.0, 2024)]}},
            'LeaseLiabilities': {'units': {currency: [point(8.0, 2024)]}},
            'BasicEarningsLossPerShare': {'units': {f'{currency}/shares': [flow(1.5, 2024)]}},
        }}}


class ForeignFilerTests(unittest.TestCase):
    def test_us_filer_untouched(self):
        payload = {'facts': {'us-gaap': {'Revenues': {'units': {'USD': [flow(1.0, 2024, form='10-K')]}}}}}
        out, meta = normalize_payload(payload)
        self.assertIs(out, payload)
        self.assertIsNone(meta)
        self.assertFalse(is_foreign_filer(payload))

    def test_ifrs_mapped_converted_and_relabelled(self):
        out, meta = normalize_payload(ifrs_payload(), fx=fixed_fx(1.25))
        self.assertEqual((meta['standard'], meta['currency']), ('IFRS', 'GBP'))
        rev = annual_flows(out, ['Revenues'])                       # engine sees US GAAP, USD, 10-K
        self.assertEqual(sorted(rev), ['2022-12-31', '2023-12-31', '2024-12-31'])
        self.assertAlmostEqual(rev['2024-12-31']['value'], 150.0)  # 120 GBP x 1.25
        self.assertAlmostEqual(rev['2022-12-31']['value'], 125.0)  # primary concept wins its period (not 999)
        self.assertAlmostEqual(annual_flows(out, ['OperatingIncomeLoss'])['2024-12-31']['value'], 25.0)
        self.assertAlmostEqual(annual_points(out, ['PropertyPlantAndEquipmentNet'])['2024-12-31']['value'], 62.5)
        self.assertAlmostEqual(annual_points(out, ['FinanceLeaseLiability'])['2024-12-31']['value'], 10.0)
        eps = annual_flows(out, ['BasicEarningsLossPerShare'], unit='USD/shares')
        self.assertEqual(eps, {})                                   # unmapped IFRS concepts are not carried over
        shares = annual_points(out, ['EntityCommonStockSharesOutstanding'], namespace='dei', unit='shares')
        self.assertEqual(shares['2024-12-31']['value'], 1000)

    def test_flows_use_average_rate_and_balances_closing_rate(self):
        days = pd.date_range('2024-01-01', '2024-12-31', freq='D')
        series = pd.Series([1.0] * 183 + [2.0] * (len(days) - 183), index=days)
        fx = FxConverter('GBP', series=series)
        out, _ = normalize_payload(ifrs_payload(), fx=fx)
        rev = annual_flows(out, ['Revenues'])['2024-12-31']['value']
        self.assertAlmostEqual(rev, 120.0 * series.mean())
        ppe = annual_points(out, ['PropertyPlantAndEquipmentNet'])['2024-12-31']['value']
        self.assertAlmostEqual(ppe, 50.0 * 2.0)

    def test_convenience_usd_translation_is_dropped(self):
        payload = {'facts': {'us-gaap': {'Revenues': {'units': {
            'SGD': [flow(100.0, 2024)], 'USD': [flow(70.0, 2024)]}}}}}
        out, meta = normalize_payload(payload, fx=fixed_fx(0.75, 'SGD'))
        self.assertEqual(meta['currency'], 'SGD')
        self.assertAlmostEqual(annual_flows(out, ['Revenues'])['2024-12-31']['value'], 75.0)

    def test_hyperinflationary_currency_refused(self):
        with self.assertRaises(ForeignFilerUnsupported):
            normalize_payload(ifrs_payload('ARS'), fx=fixed_fx(0.001, 'ARS'))

    def test_ads_ratio(self):
        self.assertEqual(ads_ratio(1_240e6, 310e6), 4)             # 1 ADS = 4 ordinary shares
        self.assertEqual(ads_ratio(100e6, 101e6), 1)
        self.assertAlmostEqual(ads_ratio(50e6, 100e6), 0.5)          # 1 ordinary share = 2 ADSs
        self.assertIsNone(ads_ratio(100e6, 37e6))                    # 2.7: does not reconcile
        self.assertIsNone(ads_ratio(None, 10))


if __name__ == '__main__':
    unittest.main()
