
import unittest

from intrinsic.market_reference import comparar_puentes_valoracion


class TestValuationBridgeScenarios(unittest.TestCase):

    def setUp(self):
        self.resultados = comparar_puentes_valoracion(
            enterprise_value=1000,
            net_debt=-100,
            shares=10,
            finance_lease_liabilities=200,
            non_operating_investments=50,
        )

    def test_base(self):
        self.assertAlmostEqual(
            self.resultados["base"]["intrinsic_price"],
            110,
        )

    def test_finance_leases(self):
        self.assertAlmostEqual(
            self.resultados[
                "including_finance_leases"
            ]["intrinsic_price"],
            90,
        )

    def test_investments(self):
        self.assertAlmostEqual(
            self.resultados[
                "including_investments"
            ]["intrinsic_price"],
            115,
        )

    def test_combined(self):
        self.assertAlmostEqual(
            self.resultados[
                "leases_and_investments"
            ]["intrinsic_price"],
            95,
        )

    def test_invalid_shares(self):
        with self.assertRaises(ValueError):
            comparar_puentes_valoracion(
                enterprise_value=1000,
                net_debt=0,
                shares=0,
            )

    def test_negative_investments(self):
        with self.assertRaises(ValueError):
            comparar_puentes_valoracion(
                enterprise_value=1000,
                net_debt=0,
                shares=10,
                non_operating_investments=-50,
            )


if __name__ == "__main__":
    unittest.main()
