import unittest
from unittest.mock import patch
from intrinsic.market_reference import obtener_puente_financiero, calcular_precio_intrinseco, calcular_upside


def balance(investment_date="2025-12-31"):
    values = {"Cash": 30, "Short Term Investments": 10, "Long Term Debt": 50, "Current Debt": 5, "Long Term Investments": 12}
    return {k: {"value": v, "date": investment_date if k == "Long Term Investments" else "2025-12-31"} for k, v in values.items()}


class TestBridge19C(unittest.TestCase):
    def run_bridge(self, data):
        with patch("intrinsic.market_reference.descargar_datos", return_value={}), \
             patch("intrinsic.market_reference.obtener_balance_sec", return_value=data), \
             patch("intrinsic.market_reference.extraer_finance_leases_sec", side_effect=ValueError("tag not found")):
            return obtener_puente_financiero("MSFT")

    def test_net_debt(self):
        r = self.run_bridge(balance())
        self.assertEqual(r["net_debt"], 15)
        self.assertEqual(r["balance_date"], "2025-12-31")

    def test_optional_investment_mismatch(self):
        r = self.run_bridge(balance("2024-12-31"))
        self.assertIsNone(r["long_term_investments"])
        self.assertEqual(r["long_term_investments_status"], "DATE_MISMATCH_EXCLUDED")

    def test_optional_investment_match(self):
        r = self.run_bridge(balance())
        self.assertEqual(r["long_term_investments"], 12)

    def test_required_date_mismatch(self):
        b = balance()
        b["Cash"]["date"] = "2024-12-31"
        with self.assertRaises(ValueError):
            self.run_bridge(b)

    def test_required_missing(self):
        b = balance()
        del b["Current Debt"]
        with self.assertRaises(ValueError):
            self.run_bridge(b)

    def test_invalid_optional_amount(self):
        b = balance()
        b["Long Term Investments"]["value"] = float("nan")
        with self.assertRaises(ValueError):
            self.run_bridge(b)

    def test_equity_value_invalid(self):
        with self.assertRaises(ValueError):
            calcular_precio_intrinseco(float("nan"), 10)

    def test_upside_invalid(self):
        with self.assertRaises(ValueError):
            calcular_upside(float("inf"), 10)


if __name__ == "__main__":
    unittest.main()
