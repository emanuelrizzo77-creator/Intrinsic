"""Audit of the decision layer (November 2026): distribution, probabilities, thresholds, implied return, terminal
weight and the DCF it rests on. Synthetic, deterministic data only."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intrinsic import forecast as dm  # noqa: E402
from intrinsic import reverse_dcf as rv  # noqa: E402
from intrinsic import sml  # noqa: E402
from intrinsic import verdict as vd  # noqa: E402
from test_forecast import history  # noqa: E402

CAL = {'growth_fade': {'all': {'phi': 0.2}}, 'margin_fade': {'all': {'phi': 0.8}}, 'growth_center': 0.07}
NET_DEBT, SHARES, WACC, G = 150.0, 100.0, 0.09, 0.03
# Golden prices of the synthetic case, recorded before the audit changes (which touch only the decision layer).
GOLDEN = {'conservative': 33.98903814504272, 'base': 44.86520990902254, 'optimistic': 49.51818840551154}


def run(scenario='base', **kw):
    p = dict(wacc=WACC, terminal_growth=G, net_debt=NET_DEBT, shares=SHARES, calibration=CAL, scenario=scenario)
    p.update(kw)
    return dm.run(history(), **p)


def integrate(dist, a, b, n=200_000):
    """Midpoint rule; the density has a step at the median, which the rule handles."""
    h = (b - a) / n
    return sum(vd.pdf(dist, a + (i + 0.5) * h) for i in range(n)) * h


class Distribution(unittest.TestCase):
    ASYM = (171.0, 247.0, 314.0)          # Microsoft-like: wider below the base than above

    def test_split_fit_passes_through_all_three_scenarios(self):
        d = vd.value_distribution(*self.ASYM)
        self.assertAlmostEqual(vd.cdf(d, 171.0), 0.20, places=9)
        self.assertAlmostEqual(vd.cdf(d, 247.0), 0.50, places=9)
        self.assertAlmostEqual(vd.cdf(d, 314.0), 0.80, places=9)
        self.assertGreater(d['spread_lo'], d['spread_hi'])

    def test_density_is_normalised(self):
        d = vd.value_distribution(*self.ASYM)
        self.assertAlmostEqual(integrate(d, 1e-6, vd.quantile(d, 1 - 1e-9)), 1.0, places=4)
        n = vd.value_distribution(-20.0, 10.0, 25.0)               # split normal (a value below zero)
        self.assertEqual(n['kind'], 'normal')
        self.assertAlmostEqual(integrate(n, vd.quantile(n, 1e-10), vd.quantile(n, 1 - 1e-10)), 1.0, places=4)
        self.assertAlmostEqual(vd.cdf(n, -20.0), 0.20, places=9)

    def test_base_is_the_median_not_the_mean(self):
        d = vd.value_distribution(*self.ASYM)
        self.assertAlmostEqual(vd.quantile(d, 0.5), 247.0, places=4)
        sym = vd.value_distribution(100.0, 200.0, 400.0)             # symmetric in logs: mean = median * e^(s^2/2)
        s = sym['spread_lo']
        self.assertAlmostEqual(integrate_moment(sym), 200.0 * math.exp(s * s / 2), delta=0.05)
        self.assertGreater(integrate_moment(sym), 200.0)

    def test_misordered_scenarios_give_no_distribution(self):
        self.assertIsNone(vd.value_distribution(260.0, 247.0, 314.0))
        self.assertIsNone(vd.value_distribution(171.0, 247.0, 240.0))


def integrate_moment(d, n=200_000):
    hi = vd.quantile(d, 1 - 1e-9)
    h = hi / n
    return sum((i + 0.5) * h * vd.pdf(d, (i + 0.5) * h) for i in range(n)) * h


class Probabilities(unittest.TestCase):
    def test_probability_above_price_is_the_integral_above_price(self):
        v = vd.verdict({'conservative': 171.0, 'base': 247.0, 'optimistic': 314.0}, 300.0, 0.15)
        d = v['distribution']
        self.assertAlmostEqual(v['prob_above_market'], integrate(d, 300.0, vd.quantile(d, 1 - 1e-12)), places=4)

    def test_shares_sum_to_one_and_match_the_thresholds(self):
        prices = {'conservative': 171.0, 'base': 247.0, 'optimistic': 314.0}
        v = vd.verdict(prices, 250.0, 0.15)
        d = v['distribution']
        self.assertAlmostEqual(sum(v['probabilities'].values()), 1.0, places=12)
        self.assertAlmostEqual(v['probabilities']['sell'], vd.cdf(d, 250.0 * 0.85), places=12)
        self.assertAlmostEqual(v['probabilities']['buy'], 1 - vd.cdf(d, 250.0 * 1.15), places=12)

    def test_thresholds_are_classification_bounds_on_value(self):
        v = vd.verdict({'conservative': 171.0, 'base': 247.0, 'optimistic': 314.0}, 484.52, 0.15)
        self.assertAlmostEqual(v['buy_above'], 484.52 * 1.15)       # A: thresholds on the model value
        self.assertAlmostEqual(v['sell_below'], 484.52 * 0.85)
        self.assertAlmostEqual(v['price_with_margin'], 247.0 * 0.85)  # B: margin of safety on the base value
        self.assertEqual(v['action'], 'sell')

    def test_majority_rule_edges(self):
        # Base exactly at the buy threshold: Prob(buy) = 50%, not a majority -> Hold
        v = vd.verdict({'conservative': 100.0, 'base': 115.0, 'optimistic': 130.0}, 100.0, 0.15)
        self.assertAlmostEqual(v['probabilities']['buy'], 0.5, places=12)
        self.assertEqual(v['action'], 'hold')
        self.assertEqual(vd.verdict({'conservative': 100.0, 'base': 116.0, 'optimistic': 130.0}, 100.0, 0.15)['action'],
                         'buy')

    def test_margin_of_safety_is_applied_symmetrically(self):
        prices = {'conservative': 90.0, 'base': 100.0, 'optimistic': 111.0}
        for m in (0.0, 0.1, 0.3):
            v = vd.verdict(prices, 100.0, m)
            self.assertAlmostEqual(v['buy_above'] / 100.0 - 1, m)
            self.assertAlmostEqual(1 - v['sell_below'] / 100.0, m)
        self.assertEqual(vd.verdict(prices, 100.0, 0.0)['probabilities']['hold'], 0.0)


class Engine(unittest.TestCase):
    def test_dcf_unchanged(self):
        for s, p in GOLDEN.items():
            self.assertAlmostEqual(run(s)['valuation']['intrinsic_price'], p, places=9, msg=s)

    def test_price_reproduced_independently(self):
        res = run()
        rows, v = res['projection']['rows'], res['valuation']
        pv = sum(r['fcff'] / (1 + WACC) ** r['t'] for r in rows)
        pv_tv = v['terminal']['fcff'] / (WACC - G) / (1 + WACC) ** len(rows)
        self.assertAlmostEqual(pv, v['pv_fcff'], places=9)
        self.assertAlmostEqual(pv_tv, v['pv_terminal'], places=9)
        self.assertAlmostEqual((pv + pv_tv - NET_DEBT) / SHARES, v['intrinsic_price'], places=9)

    def test_terminal_weight_uses_present_values_over_enterprise_value(self):
        v = run()['valuation']
        self.assertAlmostEqual(v['terminal_share_of_ev'], v['pv_terminal'] / (v['pv_fcff'] + v['pv_terminal']), places=12)
        self.assertAlmostEqual(v['enterprise_value'], v['pv_fcff'] + v['pv_terminal'], places=9)
        self.assertAlmostEqual(v['equity_value'], v['enterprise_value'] - NET_DEBT, places=9)

    def test_scenarios_are_ordered(self):
        p = {s: run(s)['valuation']['intrinsic_price'] for s in GOLDEN}
        self.assertLess(p['conservative'], p['base'])
        self.assertLess(p['base'], p['optimistic'])
        self.assertIsNotNone(vd.verdict(p, p['base'], 0.15))


class ImpliedReturn(unittest.TestCase):
    def test_implied_wacc_reprices_to_market_and_matches_reverse_dcf(self):
        res = run()
        market = res['valuation']['intrinsic_price'] * 1.5

        def value_at(w):
            o = run(wacc=w)
            return o['valuation']['intrinsic_price'] if 'valuation' in o else None
        iw = sml.implied_wacc(value_at, market, lo=G + 0.0025, hi=0.40, tol=1e-10)
        self.assertAlmostEqual(value_at(iw), market, delta=1e-6 * market)
        rev = rv.implied(res, 'wacc', market, net_debt=NET_DEBT, shares=SHARES)
        self.assertAlmostEqual(rev['root'], iw, places=7)

    def test_implied_cost_of_equity_is_consistent_with_the_wacc_identity(self):
        we, wd, kd_at = 0.97, 0.03, 0.04
        ke = sml.implied_cost_of_equity(0.0644, kd_at, we, wd)
        self.assertAlmostEqual(we * ke + wd * kd_at, 0.0644, places=12)
        self.assertIsNone(sml.implied_cost_of_equity(0.06, kd_at, 0.0, 1.0))


if __name__ == '__main__':
    unittest.main()
