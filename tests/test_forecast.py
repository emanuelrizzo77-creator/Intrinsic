import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic import forecast as dm
from intrinsic.operating_capital import build_capital_history
from intrinsic.sec_data import annual_flows


def history(n=6, g=0.10, margin=0.20, nwc_ratio=0.10, dep=True, nwc=True):
    rows, rev, ppe = [], 1000.0, 400.0
    for i in range(n):
        if i:
            rev *= 1 + g
        new_ppe = 0.40 * rev
        dep_v = 0.10 * ppe
        rows.append({
            'Fiscal year end': f'{2015 + i}-12-31', 'Revenue': rev,
            'Revenue growth': g if i else None, 'EBIT': rev * margin, 'EBIT margin': margin,
            'D&A verified': dep_v + 5 if dep else None, 'CapEx': new_ppe - ppe + dep_v,
            'Effective tax rate': 0.18,
            'Net PP&E': new_ppe, 'Operating NWC': nwc_ratio * rev if nwc else None,
            'Operating invested capital': new_ppe + nwc_ratio * rev if nwc else None,
            'Depreciation': dep_v if dep else None, 'Amortization': 5.0 if dep else None,
        })
        ppe = new_ppe
    return rows


class DriverModel27(unittest.TestCase):
    def run_model(self, h=None, **kw):
        params = dict(wacc=0.09, terminal_growth=0.03, net_debt=0.0, shares=100.0, calibration=None)
        params.update(kw)
        return dm.run(h or history(), **params)

    def test_complete_data_runs_and_rollforward_identity_holds(self):
        out = self.run_model()
        self.assertIn(out['status'], ('DATA_COMPLETE', 'DEGRADED'))
        rows = out['projection']['rows']
        self.assertEqual(len(rows), 10)
        prev = out['assumptions']['drivers']['net_ppe0']['value']
        for r in rows:
            self.assertAlmostEqual(prev + r['capex'] - r['depreciation'], r['net_ppe'], places=6)
            self.assertAlmostEqual(r['fcff'], r['nopat'] + r['da'] - r['capex'] - r['delta_nwc'], places=6)
            prev = r['net_ppe']

    def test_growth_converges_to_terminal(self):
        out = self.run_model(history(g=0.30))
        rows = out['projection']['rows']
        self.assertGreater(rows[0]['growth'], rows[-1]['growth'])
        self.assertLess(abs(rows[-1]['growth'] - 0.03), 0.005)

    def test_negative_nwc_releases_cash_when_growing(self):
        out = self.run_model(history(nwc_ratio=-0.15))
        for r in out['projection']['rows']:
            self.assertLess(r['delta_nwc'], 0)

    def test_base_terminal_is_steady_state_consistent(self):
        out = self.run_model()
        term, last = out['valuation']['terminal'], out['projection']['rows'][-1]
        self.assertEqual(term['mode'], 'steady_state')
        expected = 0.03 * last['revenue'] * (last['ppe_intensity'] + last['nwc_ratio']) / term['nopat']
        self.assertAlmostEqual(term['reinvestment_rate'], expected, places=9)
        self.assertAlmostEqual(term['fcff'], term['nopat'] * (1 - expected), places=6)
        # no jump between the final explicit year and the terminal period
        self.assertLess(abs(last['reinvestment_rate'] - term['reinvestment_rate']), 0.05)

    def test_terminal_value_uses_value_driver_formula(self):
        out = self.run_model(scenario='conservative')
        term = out['valuation']['terminal']
        self.assertAlmostEqual(term['ronic'], 0.09)
        self.assertAlmostEqual(term['fcff'], term['nopat'] * (1 - 0.03 / 0.09), places=6)
        self.assertAlmostEqual(term['terminal_value'], term['fcff'] / (0.09 - 0.03), places=4)

    def test_missing_depreciation_blocks_and_override_unblocks(self):
        h = history(dep=False)
        self.assertEqual(self.run_model(h)['status'], 'BLOCKED')
        out = self.run_model(h, overrides={'dep_rate': 0.10})
        self.assertNotEqual(out['status'], 'BLOCKED')
        self.assertEqual(out['assumptions']['drivers']['dep_rate']['source'], 'user')

    def test_missing_nwc_is_explicit_zero_and_degraded(self):
        out = self.run_model(history(nwc=False))
        self.assertEqual(out['status'], 'DEGRADED')
        self.assertTrue(any('NWC' in x for x in out['assumptions']['degradations']))
        self.assertTrue(all(r['delta_nwc'] == 0 for r in out['projection']['rows']))

    def test_scenarios_are_ordered(self):
        prices = {s: self.run_model(scenario=s)['valuation']['intrinsic_price']
                  for s in ('conservative', 'base', 'optimistic')}
        self.assertLess(prices['conservative'], prices['base'])
        self.assertLess(prices['base'], prices['optimistic'])

    def test_every_driver_has_a_source(self):
        drivers = self.run_model()['assumptions']['drivers']
        for name, x in drivers.items():
            self.assertIn(x['source'], ('data', 'calibrated', 'assumption', 'user'), name)

    def test_calibration_is_used_when_supplied(self):
        cal = {'growth_fade': {'all': {'phi': 0.4}}, 'margin_fade': {'all': {'phi': 0.5}}}
        d = self.run_model(calibration=cal)['assumptions']['drivers']
        self.assertEqual(d['growth_fade']['value'], 0.4)
        self.assertEqual(d['growth_fade']['source'], 'calibrated')
        self.assertEqual(d['intensity_fade']['source'], 'assumption')

    def test_rd_capitalisation_changes_roic_not_cash_flow(self):
        h = history()
        for r in h:
            r['R&D'] = 0.12 * r['Revenue']
        h[-1]['R&D history'] = [x['R&D'] for x in h[-5:]]
        h[-1]['Research asset'] = sum(x * (1 - j / 5) for j, x in enumerate(reversed(h[-1]['R&D history'])))
        plain = self.run_model(h)
        cap = self.run_model(h, rd_life=5)
        self.assertIn('research_asset0', cap['assumptions']['drivers'])
        for a, b in zip(plain['projection']['rows'], cap['projection']['rows']):
            self.assertAlmostEqual(a['fcff'], b['fcff'], places=6)
            self.assertLess(b['roic'], a['roic'])
        self.assertAlmostEqual(plain['valuation']['intrinsic_price'], cap['valuation']['intrinsic_price'], places=6)
        cons_plain = self.run_model(h, scenario='conservative')['valuation']['intrinsic_price']
        cons_cap = self.run_model(h, scenario='conservative', rd_life=5)['valuation']['intrinsic_price']
        self.assertGreater(cons_cap, cons_plain)   # no double-counting of growth investment

    def test_ppe_leakage_raises_capex_and_keeps_rollforward(self):
        h = history()
        for r in h[1:]:
            r['CapEx'] += 0.05 * r['Net PP&E'] / 1.10   # 5% of prior PP&E leaves without depreciation
        out = self.run_model(h)
        leak = out['assumptions']['drivers']['ppe_leakage']['value']
        self.assertAlmostEqual(leak, 0.05, places=3)
        base = self.run_model(h, overrides={'ppe_leakage': 0.0})
        self.assertLess(out['valuation']['intrinsic_price'], base['valuation']['intrinsic_price'])
        r1 = out['projection']['rows'][0]
        self.assertAlmostEqual(r1['ppe_leakage'], leak * out['assumptions']['drivers']['net_ppe0']['value'], places=6)

    def test_wacc_must_exceed_growth(self):
        with self.assertRaises(ValueError):
            self.run_model(wacc=0.03, terminal_growth=0.03)

    def test_unknown_override_rejected(self):
        with self.assertRaises(ValueError):
            self.run_model(overrides={'not_a_driver': 1})


def fact(val, start, end, filed, form='10-K'):
    r = {'val': val, 'end': end, 'filed': filed, 'form': form, 'accn': filed}
    if start:
        r['start'] = start
    return r


class SecVintage27(unittest.TestCase):
    payload = {'facts': {'us-gaap': {'Revenues': {'units': {'USD': [
        fact(100, '2020-01-01', '2020-12-31', '2021-02-01'),
        fact(105, '2020-01-01', '2020-12-31', '2022-02-01'),   # restated in next 10-K
        fact(50, '2020-07-01', '2020-12-31', '2021-02-01'),    # not annual
    ]}}}}}

    def test_vintage_and_as_of(self):
        latest = annual_flows(self.payload, ('Revenues',))
        first = annual_flows(self.payload, ('Revenues',), vintage='first')
        pit = annual_flows(self.payload, ('Revenues',), as_of='2021-06-30')
        self.assertEqual(latest['2020-12-31']['value'], 105)
        self.assertEqual(first['2020-12-31']['value'], 100)
        self.assertEqual(pit['2020-12-31']['value'], 100)


class OperatingCapital27(unittest.TestCase):
    def test_full_operating_nwc_can_be_negative(self):
        end, f = '2025-12-31', '2026-02-01'
        def p(v):
            return {'units': {'USD': [fact(v, None, end, f)]}}
        payload = {'facts': {'us-gaap': {
            'AssetsCurrent': p(500), 'LiabilitiesCurrent': p(700),
            'CashAndCashEquivalentsAtCarryingValue': p(200), 'ShortTermInvestments': p(100),
            'LongTermDebtCurrent': p(50), 'PropertyPlantAndEquipmentNet': p(900)}}}
        row = build_capital_history(payload, [end])[0]
        # (500-200-100) - (700-50) = -450
        self.assertEqual(row['Operating NWC'], -450)
        self.assertEqual(row['Operating invested capital'], 450)


if __name__ == '__main__':
    unittest.main()
