
import unittest

from financial_validation import (
    validar_fcff,
    validar_enterprise_value,
    validar_equity_value,
    validar_precio,
    validar_terminal_growth,
)


class TestFinancialValidation(unittest.TestCase):

    def test_fcff(self):
        self.assertTrue(
            validar_fcff(100, 0.21, 10, 20, 5, 64)
        )

    def test_fcff_incorrecto(self):
        self.assertFalse(
            validar_fcff(100, 0.21, 10, 20, 5, 70)
        )

    def test_enterprise_value(self):
        self.assertTrue(
            validar_enterprise_value(400, 600, 1000)
        )

    def test_equity_value(self):
        self.assertTrue(
            validar_equity_value(1000, -100, 1100)
        )

    def test_intrinsic_price(self):
        self.assertTrue(
            validar_precio(1000, 10, 100)
        )

    def test_terminal_growth(self):
        self.assertTrue(
            validar_terminal_growth(0.09, 0.025)
        )

    def test_invalid_terminal_growth(self):
        with self.assertRaises(ValueError):
            validar_terminal_growth(0.02, 0.03)


if __name__ == "__main__":
    unittest.main()
