"""Regression guard: the engine must reproduce the frozen Top 25 baseline (validation/top25_baseline.py).

Inputs are frozen in tests/fixtures, so this runs offline and only fails when the engine, the calibration or the
Monte Carlo error pool changes. If the change is intended, refreeze with `python -m validation.top25_baseline freeze`
and say why in the commit."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validation import top25_baseline as tb  # noqa: E402


class Top25Baseline(unittest.TestCase):
    def test_engine_reproduces_the_frozen_top25(self):
        diffs = tb.compare()
        self.assertEqual(diffs, [], 'Top 25 values moved:\n' + '\n'.join(diffs[:40]))

    def test_baseline_covers_the_fcff_top25(self):
        import json
        with open(tb.BASELINE) as fh:
            companies = json.load(fh)['companies']
        self.assertEqual(len(companies), 22)                 # Top 25 minus BRK-B, JPM, BAC (not FCFF)
        self.assertTrue(all(c['scenarios']['base'] is not None for c in companies.values()))


if __name__ == '__main__':
    unittest.main()
