"""Loss-making companies: explicit path to the industry margin, probability of failure, development-stage refusal."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intrinsic import forecast as dm  # noqa: E402
from intrinsic.industry_margin import industry_margin_for_sic, load_industry_margins  # noqa: E402
from test_forecast import history  # noqa: E402

INDUSTRY = {'margin': 0.12, 'industry': 'Test industry', 'n_firms': 100, 'note': 'Test industry margin'}


def losing(margin=-0.05, cash=500.0, n=6):
    rows = history(n=n, margin=margin)
    for r in rows:
        r['Cash'] = cash
        r['Short-term investments'] = 0.0
    return rows


def run(h, **kw):
    params = dict(wacc=0.09, terminal_growth=0.03, net_debt=-200.0, shares=100.0, calibration=None,
                  industry_margin=INDUSTRY)
    params.update(kw)
    return dm.run(h, **params)


class ProfitPathTests(unittest.TestCase):
    def test_profitable_company_is_unchanged(self):
        out = run(history())
        d = out['assumptions']['drivers']
        self.assertNotIn('profit_years', d)
        self.assertNotIn('failure_prob', out['valuation'])
        self.assertAlmostEqual(d['margin_target']['value'], 0.20)

    def test_loss_maker_targets_industry_margin_on_a_straight_line(self):
        out = run(losing())
        d = out['assumptions']['drivers']
        self.assertAlmostEqual(d['margin_target']['value'], 0.12)
        n = d['profit_years']['value']
        rows = out['projection']['rows']
        for r in rows:
            expected = -0.05 + (0.12 + 0.05) * min(r['t'] / n, 1.0)
            self.assertAlmostEqual(r['ebita_margin'], expected, places=9)
        self.assertIn('valuation', out)

    def test_value_is_probability_weighted(self):
        out = run(losing(cash=500.0))           # runway 500 / 50 = 10 years -> 10%
        v = out['valuation']
        self.assertAlmostEqual(v['failure_prob'], 0.10)
        self.assertAlmostEqual(v['distress_equity'], 200.0)          # net cash
        expected = 0.9 * v['going_concern_equity'] + 0.1 * 200.0
        self.assertAlmostEqual(v['equity_value'], expected, places=6)
        self.assertAlmostEqual(v['intrinsic_price'], expected / 100.0, places=9)

    def test_distress_value_floored_at_zero_with_net_debt(self):
        v = run(losing(), net_debt=300.0)['valuation']
        self.assertEqual(v['distress_equity'], 0.0)

    def test_short_runway_raises_failure_probability(self):
        p_long = run(losing(cash=500.0))['valuation']['failure_prob']
        p_short = run(losing(cash=10.0))['valuation']['failure_prob']   # < 1 year of losses
        self.assertGreater(p_short, p_long)
        self.assertAlmostEqual(p_short, 0.50)

    def test_user_overrides_years_and_probability(self):
        out = run(losing(), overrides={'profit_years': 3, 'failure_prob': 0.0})
        rows = out['projection']['rows']
        self.assertAlmostEqual(rows[2]['ebita_margin'], 0.12)
        self.assertNotIn('failure_prob', out['valuation'])               # p = 0 -> pure going concern

    def test_development_stage_is_refused(self):
        out = run(losing(margin=-2.5))
        self.assertEqual(out['status'], 'BLOCKED')
        self.assertTrue(any('Development-stage' in b for b in out['assumptions']['blockers']))

    def test_loss_maker_without_industry_margin_is_blocked(self):
        out = run(losing(), industry_margin=None)
        self.assertEqual(out['status'], 'BLOCKED')


class IndustryMarginTests(unittest.TestCase):
    def test_mapped_industry(self):
        m = industry_margin_for_sic(7372)          # prepackaged software
        self.assertEqual(m['industry'], 'Software (System & Application)')
        self.assertGreater(m['margin'], 0)

    def test_fallback_to_market_for_unmapped_or_losing_industry(self):
        market = load_industry_margins()['Total Market (without financials)']['margin']
        self.assertAlmostEqual(industry_margin_for_sic(None)['margin'], market)
        table = {'Total Market (without financials)': {'margin': 0.13, 'n_firms': 4800},
                 'Software (System & Application)': {'margin': -0.02, 'n_firms': 300}}
        m = industry_margin_for_sic(7372, table=table)
        self.assertEqual(m['margin'], 0.13)
        self.assertIn('loses money', m['note'])


if __name__ == '__main__':
    unittest.main()
