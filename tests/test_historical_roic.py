
import unittest

from historical_roic import (
    BALANCES,
    EBIT_2026,
    TAX_RATE,
    calcular_capital_invertido,
    calcular_roic,
)


class TestHistoricalROIC(unittest.TestCase):

    def test_capital_conventional(self):
        resultado = calcular_capital_invertido(
            BALANCES[2026]
        )

        self.assertAlmostEqual(
            resultado["conventional"],
            405.838,
            places=3,
        )

    def test_finance_leases(self):
        resultado = calcular_capital_invertido(
            BALANCES[2026]
        )

        self.assertAlmostEqual(
            resultado["finance_leases"],
            472.432,
            places=3,
        )

    def test_all_leases(self):
        resultado = calcular_capital_invertido(
            BALANCES[2026]
        )

        self.assertAlmostEqual(
            resultado["all_leases"],
            494.357,
            places=3,
        )

    def test_average_capital(self):
        capital_2025 = calcular_capital_invertido(
            BALANCES[2025]
        )
        capital_2026 = calcular_capital_invertido(
            BALANCES[2026]
        )

        promedio = (
            capital_2025["conventional"]
            + capital_2026["conventional"]
        ) / 2

        self.assertAlmostEqual(
            promedio,
            348.9515,
            delta=0.0001,
        )

    def test_roic_identity(self):
        nopat = EBIT_2026 * (1 - TAX_RATE)

        resultado = calcular_roic(
            nopat,
            348.9515,
        )

        esperado = nopat / 348.9515

        self.assertAlmostEqual(
            resultado,
            esperado,
        )

    def test_invalid_capital(self):
        with self.assertRaises(ValueError):
            calcular_roic(
                100,
                0,
            )


if __name__ == "__main__":
    unittest.main()
