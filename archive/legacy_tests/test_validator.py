
import unittest

from data_validator import calcular_deuda_neta


class TestDataValidator(unittest.TestCase):

    def test_deuda_neta(self):
        balance = {
            "Cash": {"value": 20_000_000},
            "Short Term Investments": {
                "value": 30_000_000
            },
            "Long Term Debt": {
                "value": 40_000_000
            },
            "Current Debt": {
                "value": 5_000_000
            }
        }

        resultado = calcular_deuda_neta(balance)

        self.assertEqual(
            resultado["debt"],
            45_000_000
        )

        self.assertEqual(
            resultado["cash_and_investments"],
            50_000_000
        )

        self.assertEqual(
            resultado["net_debt"],
            -5_000_000
        )


if __name__ == "__main__":
    unittest.main()
