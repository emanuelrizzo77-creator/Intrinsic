"""Monte Carlo verdict (intrinsic/value_simulation.py), empirical distribution and price-consistent implied-return
weights. Synthetic, deterministic data only."""
import math
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intrinsic import forecast as dm  # noqa: E402
from intrinsic import sml  # noqa: E402
from intrinsic import value_simulation as vs  # noqa: E402
from intrinsic import verdict as vd  # noqa: E402
from test_forecast import history  # noqa: E402

CAL = {'growth_fade': {'all': {'phi': 0.2}}, 'margin_fade': {'all': {'phi': 0.8}}, 'growth_center': 0.07,
       'sigma_floors': {'growth': 0.03, 'margin': 0.01}}
NET_DEBT, SHARES = 150.0, 100.0
CAPM = {'risk_free_rate': 0.045, 'beta': 1.0, 'equity_risk_premium': 0.045, 'equity_weight': 0.9, 'debt_weight': 0.1,
        'after_tax_cost_of_debt': 0.04}


def errors(vectors, kind='scaled', high=None):
    groups = {'<1B': {'kind': kind, 'min_revenue': 0.0, 'max_revenue': 1e9, 'vectors': vectors}}
    if high is not None:
        groups['high_growth'] = {'kind': 'scaled', 'min_revenue': None, 'max_revenue': None, 'vectors': high}
    return {'groups': groups}


ZERO = [[0.0] * 10] * 300


def base(**kw):
    wacc = CAPM['equity_weight'] * (CAPM['risk_free_rate'] + CAPM['beta'] * CAPM['equity_risk_premium']) + \
        CAPM['debt_weight'] * CAPM['after_tax_cost_of_debt']
    p = dict(wacc=wacc, terminal_growth=0.025, net_debt=NET_DEBT, shares=SHARES, calibration=CAL)
    p.update(kw)
    return dm.run(history(), **p)


def simulate(res, errs, **kw):
    return vs.simulate(res, history(), net_debt=NET_DEBT, shares=SHARES, calibration=CAL, errors=errs, **kw)


class Simulation(unittest.TestCase):
    def test_no_uncertainty_reproduces_the_base_value(self):
        res = base()
        with mock.patch.multiple(vs, BETA_SD=0.0, ERP_SD=0.0, G_HALF_RANGE=0.0):
            sim = simulate(res, errors(ZERO), capm=CAPM, n=50)
        for v in sim['values']:
            self.assertAlmostEqual(v, res['valuation']['intrinsic_price'], places=9)

    def test_deterministic_with_a_seed(self):
        res = base()
        rng_vectors = [[(i % 7 - 3) * 0.3] * 5 + [(i % 5 - 2) * 0.4] * 5 for i in range(300)]
        a = simulate(res, errors(rng_vectors), capm=CAPM, n=200)
        b = simulate(res, errors(rng_vectors), capm=CAPM, n=200)
        self.assertEqual(a['values'], b['values'])
        self.assertGreater(len(set(round(x, 6) for x in a['values'])), 10)

    def test_scaled_errors_use_the_company_volatility_and_raw_errors_do_not(self):
        res = base()
        sg, sm, _ = dm.company_volatility(history(), CAL)
        one = [[0.0] * 4 + [1.0] + [0.0] * 5] * 300          # +1 on log revenue at year 5 only
        with mock.patch.multiple(vs, BETA_SD=0.0, ERP_SD=0.0, G_HALF_RANGE=0.0):
            scaled = simulate(res, errors(one, 'scaled'), capm=CAPM, n=5)['values'][0]
            raw = simulate(res, errors(one, 'raw'), capm=CAPM, n=5)['values'][0]
            a = res['assumptions']

            def price(band):
                x = vs._with(a, revenue_band=[0, 0, 0, 0, band], margin_band=[0] * 5)
                return dm.value(dm.project(x, 10), x, net_debt=NET_DEBT, shares=SHARES)['intrinsic_price']
        self.assertAlmostEqual(scaled, price(sg), places=9)
        self.assertAlmostEqual(raw, price(1.0), places=9)

    def test_one_year_margin_spike_is_not_held_forever(self):
        res = base()
        spike = [[0.0] * 9 + [-0.9]] * 300                   # margin collapses only in year 5 (a write-off)
        with mock.patch.multiple(vs, BETA_SD=0.0, ERP_SD=0.0, G_HALF_RANGE=0.0):
            sim = simulate(res, errors(spike, 'raw'), capm=CAPM, n=5)
        self.assertAlmostEqual(sim['values'][0], res['valuation']['intrinsic_price'], places=9)

    def test_high_growth_company_uses_the_high_growth_pool(self):
        h = history(g=0.40)
        res = dm.run(h, wacc=0.09, terminal_growth=0.025, net_debt=NET_DEBT, shares=SHARES, calibration=CAL)
        high_pool = [[0.1] * 10] * 300
        sim = vs.simulate(res, h, net_debt=NET_DEBT, shares=SHARES, calibration=CAL,
                          errors=errors(ZERO, high=high_pool), capm=CAPM, n=20)
        self.assertEqual(sim['inputs']['size_group'], 'high_growth')

    def test_failure_probability_is_sampled_not_averaged(self):
        res = base()
        res['assumptions']['drivers']['failure_prob'] = {'value': 0.3, 'source': 'assumption', 'note': ''}
        with mock.patch.multiple(vs, BETA_SD=0.0, ERP_SD=0.0, G_HALF_RANGE=0.0):
            sim = simulate(res, errors(ZERO), capm=CAPM, n=2000)
        distress = max(0.0, -NET_DEBT) / SHARES
        self.assertAlmostEqual(sim['distress_share'], 0.3, delta=0.03)
        self.assertAlmostEqual(sum(v == distress for v in sim['values']) / 2000, sim['distress_share'], places=9)

    def test_terminal_growth_stays_below_wacc_and_risk_free(self):
        res = base()
        draws = []
        orig = vs._with

        def spy(a, **values):
            draws.append((values.get('wacc'), values.get('terminal_growth')))
            return orig(a, **values)
        with mock.patch.object(vs, '_with', spy):
            simulate(res, errors(ZERO), capm={**CAPM, 'risk_free_rate': 0.03}, n=300)
        self.assertTrue(all(g <= w - vs.WACC_GAP + 1e-12 and g <= 0.03 + 1e-12 for w, g in draws if w is not None))
        draws.clear()
        with mock.patch.object(vs, '_with', spy):         # risk-free below the user's g: the cap is the user's g
            simulate(res, errors(ZERO), capm={**CAPM, 'risk_free_rate': 0.01}, n=300)
        gs = [g for w, g in draws if w is not None]
        self.assertTrue(all(g <= 0.025 + 1e-12 for g in gs))
        self.assertGreater(min(gs), 0.01)

    def test_missing_inputs_give_no_simulation(self):
        self.assertIsNone(simulate({'status': 'BLOCKED'}, errors(ZERO)))
        self.assertIsNone(simulate(base(), errors([[0.0] * 10] * 10)))       # pool too small
        self.assertIsNone(vs.simulate(base(), history(n=3), net_debt=0, shares=1, calibration=CAL, errors=errors(ZERO)))


class EmpiricalVerdict(unittest.TestCase):
    VALUES = [50 + i * 0.25 for i in range(400)]              # uniform 50 .. 149.75

    def test_probabilities_are_shares_of_draws(self):
        v = vd.verdict_from_samples(self.VALUES, 100.0, 0.15, base=100.0)
        self.assertAlmostEqual(v['probabilities']['buy'], sum(x > v['buy_above'] for x in self.VALUES) / 400)
        self.assertAlmostEqual(v['probabilities']['sell'], sum(x < v['sell_below'] for x in self.VALUES) / 400)
        self.assertAlmostEqual(sum(v['probabilities'].values()), 1.0, places=12)
        self.assertAlmostEqual(v['prob_above_market'], sum(x > 100 for x in self.VALUES) / 400)
        p = v['probabilities']['hold']
        self.assertAlmostEqual(v['mc_se']['hold'], math.sqrt(p * (1 - p) / 400))
        self.assertAlmostEqual(v['price_with_margin'], 85.0)

    def test_kernel_density_integrates_to_one(self):
        d = vd.empirical_distribution(self.VALUES)
        n, lo, hi = 20000, 1.0, 400.0
        h = (hi - lo) / n
        self.assertAlmostEqual(sum(vd.pdf(d, lo + (i + .5) * h) for i in range(n)) * h, 1.0, places=2)
        self.assertAlmostEqual(vd.cdf(d, 100.0), sum(x <= 100 for x in self.VALUES) / 400)
        self.assertEqual(vd.quantile(d, 0.0), 50.0)

    def test_too_few_draws(self):
        self.assertIsNone(vd.verdict_from_samples([1.0] * 10, 100.0))


class ImpliedReturnWeights(unittest.TestCase):
    def test_weights_equal_the_dcf_equity_at_the_implied_wacc(self):
        res = base()
        market = res['valuation']['intrinsic_price'] * 1.4
        debt = 120.0

        def value_at(w):
            o = base(wacc=w)
            return o['valuation']['intrinsic_price'] if 'valuation' in o else None
        iw = sml.implied_wacc(value_at, market, lo=0.03, hi=0.40, tol=1e-12)
        we, wd = sml.weights_at_price(market, SHARES, debt)
        equity = base(wacc=iw)['valuation']['equity_value']
        self.assertAlmostEqual(we, equity / (equity + debt), places=6)
        ke = sml.implied_cost_of_equity(iw, 0.04, we, wd)
        self.assertAlmostEqual(we * ke + wd * 0.04, iw, places=12)

    def test_invalid_weights(self):
        self.assertIsNone(sml.weights_at_price(None, 10, 5))
        self.assertIsNone(sml.weights_at_price(0.0, 10, 5))
        self.assertIsNone(sml.weights_at_price(10.0, 10, -1))


if __name__ == '__main__':
    unittest.main()
