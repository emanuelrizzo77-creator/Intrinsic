"""Reverse DCF (intrinsic/reverse_dcf.py): synthetic, deterministic data only."""
import copy
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intrinsic import forecast as dm  # noqa: E402
from intrinsic import reverse_dcf as rv  # noqa: E402
from test_forecast import history  # noqa: E402

CAL = {'growth_fade': {'all': {'phi': 0.2}}, 'margin_fade': {'all': {'phi': 0.8}}, 'growth_center': 0.07}
NET_DEBT, SHARES = 150.0, 100.0


def run(scenario='base', **kw):
    params = dict(wacc=0.09, terminal_growth=0.03, net_debt=NET_DEBT, shares=SHARES, calibration=CAL,
                  scenario=scenario)
    params.update(kw)
    return dm.run(history(), **params)


def price(res):
    return res['valuation']['intrinsic_price']


def implied(res, mode, market, **kw):
    return rv.implied(res, mode, market, net_debt=NET_DEBT, shares=SHARES, **kw)


class Consistency(unittest.TestCase):
    """Same assumptions -> same price as the traditional DCF; nothing is mutated."""

    def test_reprice_at_original_driver_equals_traditional_dcf(self):
        for scen in ('conservative', 'base', 'optimistic'):
            res = run(scen)
            for mode in rv.MODES:
                p, proj, val = rv.reprice(res['assumptions'], mode, rv.original_value(mode, res['assumptions']),
                                          net_debt=NET_DEBT, shares=SHARES)
                self.assertAlmostEqual(p, price(res), places=9, msg=(scen, mode))
                # terminal value and the EV -> equity bridge are the traditional engine's own
                self.assertAlmostEqual(val['terminal']['terminal_value'], res['valuation']['terminal']['terminal_value'], places=6)
                self.assertAlmostEqual(val['equity_value'], val['enterprise_value'] - NET_DEBT, places=6)

    def test_traditional_dcf_unchanged_and_assumptions_not_mutated(self):
        res = run()
        before_price, before_drivers = price(res), copy.deepcopy(res['assumptions']['drivers'])
        rv.run_all(res, before_price * 1.4, net_debt=NET_DEBT, shares=SHARES)
        self.assertEqual(res['assumptions']['drivers'], before_drivers)
        self.assertNotIn('growth_premium', res['assumptions']['drivers'])
        self.assertEqual(price(run()), before_price)

    def test_market_equal_to_value_returns_original_assumption(self):
        res = run()
        for mode in rv.MODES:
            out = implied(res, mode, price(res))
            self.assertEqual(out['status'], 'solved', mode)
            self.assertAlmostEqual(out['root'], out['original'], places=5, msg=mode)

    def test_scenarios_are_independent(self):
        res = {s: run(s) for s in ('conservative', 'base', 'optimistic')}
        market = price(res['base']) * 1.3
        roots = {s: implied(res[s], 'wacc', market)['root'] for s in res}
        self.assertLess(roots['conservative'], roots['base'])
        self.assertLess(roots['base'], roots['optimistic'])
        again = implied(run('base'), 'wacc', market)['root']
        self.assertAlmostEqual(again, roots['base'], places=9)


class Solutions(unittest.TestCase):
    def test_each_mode_reproduces_the_market_price(self):
        res = run()
        for factor in (0.8, 1.3):
            market = price(res) * factor
            for mode in rv.MODES:
                out = implied(res, mode, market)
                self.assertEqual(out['status'], 'solved', (mode, factor))
                self.assertLessEqual(abs(out['residual']), rv.PRICE_RTOL * market)
                self.assertAlmostEqual(out['valuation']['intrinsic_price'], market, delta=rv.PRICE_RTOL * market)

    def test_direction_of_each_driver(self):
        a = run()['assumptions']

        def p(mode, x):
            return rv.reprice(a, mode, x, net_debt=NET_DEBT, shares=SHARES)[0]
        self.assertGreater(p('growth', 0.05), p('growth', 0.0))
        self.assertGreater(p('margin', 0.30), p('margin', 0.20))
        self.assertLess(p('wacc', 0.11), p('wacc', 0.09))

    def test_higher_price_needs_more_growth_margin_and_lower_wacc(self):
        res = run()
        lo, hi = implied(res, 'growth', price(res) * 0.9), implied(res, 'growth', price(res) * 1.2)
        self.assertGreater(hi['root'], lo['root'])
        self.assertGreater(implied(res, 'margin', price(res) * 1.2)['root'], res['assumptions']['drivers']['margin_target']['value'])
        self.assertLess(implied(res, 'wacc', price(res) * 1.2)['root'], 0.09)

    def test_growth_premium_tapers_to_terminal_growth(self):
        res = run()
        out = implied(res, 'growth', price(res) * 1.3)
        base_rows, rows = res['projection']['rows'], out['projection']['rows']
        self.assertAlmostEqual(rows[0]['growth'] - base_rows[0]['growth'], out['root'], places=9)
        self.assertAlmostEqual(rows[-1]['growth'], base_rows[-1]['growth'], places=9)

    def test_no_solution_is_reported_not_forced(self):
        res = run()
        out = implied(res, 'growth', price(res) * 1000)
        self.assertEqual(out['status'], 'no_solution')
        self.assertIsNone(out['root'])
        self.assertIn('above', out['reason'])
        self.assertEqual(out['bounds'], rv.GROWTH_PREMIUM_BOUNDS)      # bounds are not widened
        w = implied(res, 'wacc', price(res) * 0.001)
        self.assertEqual(w['status'], 'no_solution')
        self.assertIn('below', w['reason'])

    def test_wacc_stays_above_terminal_growth(self):
        res = run()
        lo, _ = rv.bounds('wacc', res['assumptions'])
        self.assertAlmostEqual(lo, 0.03 + rv.WACC_MIN_GAP)
        with self.assertRaises(ValueError):
            rv.reprice(res['assumptions'], 'wacc', 0.03, net_debt=NET_DEBT, shares=SHARES)

    def test_low_implied_wacc_warns(self):
        res = run()
        out = implied(res, 'wacc', price(res) * 4, risk_free_rate=0.05)
        self.assertEqual(out['status'], 'solved')
        self.assertLess(out['root'], 0.05)
        self.assertIn('wacc_below_rf', [c for c, _ in out['warnings']])
        self.assertIn('risk-free', rv.warning_text(*out['warnings'][0]))


class Solver(unittest.TestCase):
    def test_converges_with_small_residual(self):
        out = rv.solve(lambda x: 100 * math.exp(x), 150.0, 0.0, 1.0)
        self.assertEqual(out['status'], 'solved')
        self.assertAlmostEqual(out['root'], math.log(1.5), places=7)
        self.assertLess(abs(out['residual']), 1e-6)
        self.assertTrue(out['monotone'])

    def test_multiple_solutions_are_not_picked(self):
        out = rv.solve(lambda x: 100 - 400 * (x - 0.5) ** 2, 80.0, 0.0, 1.0)   # hump: two roots
        self.assertEqual(out['status'], 'multiple')
        self.assertIsNone(out['root'])
        self.assertEqual(len(out['roots']), 2)
        self.assertFalse(out['monotone'])

    def test_non_monotone_with_one_root_is_flagged(self):
        def f(x):     # rises to 250, dips to 200, then rises to 400: one crossing of 300, not monotone
            return 100 + 500 * x if x < 0.3 else (250 - 250 * (x - 0.3) if x < 0.5 else 200 + 400 * (x - 0.5))
        out = rv.solve(f, 300.0, 0.0, 1.0)
        self.assertEqual(out['status'], 'solved')
        self.assertFalse(out['monotone'])

    def test_gaps_are_never_bracketed(self):
        def f(x):
            if 0.4 < x < 0.6:
                raise ValueError('no value')
            return 50.0 if x <= 0.4 else 150.0
        out = rv.solve(f, 100.0, 0.0, 1.0)
        self.assertEqual(out['status'], 'no_solution')

    def test_invalid_inputs(self):
        self.assertEqual(rv.solve(lambda x: x, 0.0, 0.0, 1.0)['status'], 'invalid')
        self.assertEqual(rv.solve(lambda x: x, float('nan'), 0.0, 1.0)['status'], 'invalid')
        self.assertEqual(rv.solve(lambda x: x, 1.0, 1.0, 0.0)['status'], 'invalid')
        self.assertEqual(rv.solve(lambda x: float('inf'), 1.0, 0.0, 1.0)['status'], 'no_value')
        self.assertEqual(rv.implied({'status': 'BLOCKED'}, 'growth', 100.0, net_debt=0, shares=1)['status'],
                         'not_valued')


if __name__ == '__main__':
    unittest.main()
