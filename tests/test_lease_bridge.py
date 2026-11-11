
import unittest
from unittest.mock import patch

from valuation_bridge import (
    calcular_deuda_neta_con_leases,
    extraer_finance_leases_sec,
    obtener_puente_financiero,
)


class TestLeaseBridge(unittest.TestCase):

    def setUp(self):
        self.fecha = "2026-06-30"
        self.lease = 66_594_000_000

        self.datos = {
            "facts": {
                "us-gaap": {
                    "FinanceLeaseLiability": {
                        "units": {
                            "USD": [
                                {
                                    "form": "10-K",
                                    "end": self.fecha,
                                    "filed": "2026-07-29",
                                    "val": self.lease,
                                }
                            ]
                        }
                    }
                }
            }
        }

        self.balance = {
            "Cash": {
                "value": 20_935_000_000,
                "date": self.fecha,
            },
            "Short Term Investments": {
                "value": 55_908_000_000,
                "date": self.fecha,
            },
            "Long Term Debt": {
                "value": 31_067_000_000,
                "date": self.fecha,
            },
            "Current Debt": {
                "value": 9_227_000_000,
                "date": self.fecha,
            },
        }

    def test_lease_extraction(self):
        resultado = extraer_finance_leases_sec(
            self.datos, self.fecha
        )

        self.assertEqual(resultado["value"], self.lease)
        self.assertEqual(resultado["date"], self.fecha)

    def test_lease_date_mismatch(self):
        with self.assertRaises(ValueError):
            extraer_finance_leases_sec(
                self.datos, "2025-06-30"
            )

    def test_negative_lease_rejected(self):
        self.datos["facts"]["us-gaap"][
            "FinanceLeaseLiability"
        ]["units"]["USD"][0]["val"] = -100

        with self.assertRaises(ValueError):
            extraer_finance_leases_sec(
                self.datos, self.fecha
            )

    def test_adjusted_net_debt(self):
        resultado = calcular_deuda_neta_con_leases(
            -36_549_000_000,
            self.lease,
        )

        self.assertEqual(resultado, 30_045_000_000)

    @patch("valuation_bridge.obtener_balance_sec")
    @patch("valuation_bridge.descargar_datos")
    def test_bridge_with_leases(
        self, mock_descargar, mock_balance
    ):
        mock_descargar.return_value = self.datos
        mock_balance.return_value = self.balance

        resultado = obtener_puente_financiero()

        self.assertEqual(
            resultado["net_debt"],
            -36_549_000_000,
        )
        self.assertEqual(
            resultado["net_debt_including_finance_leases"],
            30_045_000_000,
        )
        self.assertEqual(
            resultado["finance_lease_status"],
            "AVAILABLE",
        )

    @patch("valuation_bridge.obtener_balance_sec")
    @patch("valuation_bridge.descargar_datos")
    def test_bridge_without_leases(
        self, mock_descargar, mock_balance
    ):
        mock_descargar.return_value = {
            "facts": {"us-gaap": {}}
        }
        mock_balance.return_value = self.balance

        resultado = obtener_puente_financiero()

        self.assertEqual(
            resultado["net_debt"],
            -36_549_000_000,
        )
        self.assertIsNone(
            resultado["net_debt_including_finance_leases"]
        )
        self.assertEqual(
            resultado["finance_lease_status"],
            "NOT_AVAILABLE",
        )


if __name__ == "__main__":
    unittest.main()
