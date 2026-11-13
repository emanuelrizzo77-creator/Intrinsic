import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intrinsic.inputs import _debt_from_components

END = '2025-12-31'


def payload(**tags):
    """Minimal CompanyFacts payload with instant 10-K facts at END (values in USD)."""
    facts = {t: {'units': {'USD': [{'end': END, 'val': v, 'form': '10-K', 'filed': '2026-02-01', 'accn': 'x'}]}}
             for t, v in tags.items()}
    return {'facts': {'us-gaap': facts}}


class DebtBridgeTests(unittest.TestCase):
    def test_noncurrent_plus_current_first(self):
        total, source, _ = _debt_from_components(
            payload(LongTermDebtNoncurrent=900, DebtCurrent=100, DebtInstrumentCarryingAmount=5000), END)
        self.assertEqual(total, 1000)
        self.assertIn('noncurrent', source)

    def test_reported_total_beats_partial_components(self):
        # Tesla-style: current debt plus a carrying-amount total, no LongTermDebtNoncurrent tag
        total, source, _ = _debt_from_components(payload(DebtCurrent=1569, DebtInstrumentCarryingAmount=8177), END)
        self.assertEqual(total, 8177)
        self.assertIn('DebtInstrumentCarryingAmount', source)

    def test_components_when_no_total(self):
        total, source, flags = _debt_from_components(payload(ConvertibleDebtNoncurrent=2280), END)
        self.assertEqual(total, 2280)
        self.assertTrue(source.startswith('components'))
        self.assertTrue(flags)

    def test_one_tag_per_group(self):
        total, _, _ = _debt_from_components(payload(DebtCurrent=0, LineOfCredit=398, CommercialPaper=50), END)
        self.assertEqual(total, 50)        # CommercialPaper outranks LineOfCredit inside the same group

    def test_no_debt_tags_means_debt_free_and_flagged(self):
        total, source, flags = _debt_from_components(payload(), END)
        self.assertEqual(total, 0.0)
        self.assertIn('debt-free', source)
        self.assertTrue(flags)

    def test_unrecognised_debt_blocks(self):
        total, _, _ = _debt_from_components(payload(SecuredDebt=700), END)
        self.assertIsNone(total)


if __name__ == '__main__':
    unittest.main()
