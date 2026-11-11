
# INTRINSIC — INTEGRATED DCF TESTS

import math
import unittest
from unittest.mock import patch

from assumptions_engine import (
    SCENARIOS,
    proyectar_escenario,
)

from scenario_dcf import calcular_dcf

from valuation_bridge import (
    obtener_referencia_mercado,
    obtener_puente_financiero,
    calcular_precio_intrinseco,
    calcular_upside,
)


class TestIntegratedDCF(unittest.TestCase):

    def setUp(self):
        # Controlled FY2026 baseline, in USD
        self.revenue = 331_839_000_000
        self.year = 2026

        self.wacc = 0.0917
        self.growth = 0.025

        self.shares = 7_426_194_552
        self.market_price = 555.05

        self.sec_balance = {
            "Cash": {
                "value": 20_935_000_000,
                "date": "2026-06-30"
            },
            "Short Term Investments": {
                "value": 55_908_000_000,
                "date": "2026-06-30"
            },
            "Long Term Debt": {
                "value": 31_067_000_000,
                "date": "2026-06-30"
            },
            "Current Debt": {
                "value": 9_227_000_000,
                "date": "2026-06-30"
            },
        }

    def obtener_forecast(self):
        return proyectar_escenario(
            self.revenue,
            self.year,
            SCENARIOS["base"]
        )

    def obtener_bridge(self):
        with patch(
            "valuation_bridge.descargar_datos",
            return_value={"facts": {}}
        ), patch(
            "valuation_bridge.obtener_balance_sec",
            return_value=self.sec_balance
        ):
            return obtener_puente_financiero()

    def test_sec_net_debt(self):
        bridge = self.obtener_bridge()

        self.assertEqual(
            bridge["net_debt"],
            -36_549_000_000
        )

    def test_forecast_length(self):
        forecast = self.obtener_forecast()

        self.assertEqual(len(forecast), 5)

        self.assertEqual(
            [row["year"] for row in forecast],
            [2027, 2028, 2029, 2030, 2031]
        )

    def test_fcff_identity(self):
        forecast = self.obtener_forecast()

        for row in forecast:
            expected = (
                row["nopat"]
                + row["da"]
                - row["capex"]
                - row["delta_nwc"]
            )

            self.assertTrue(
                math.isclose(
                    row["fcff"],
                    expected,
                    rel_tol=1e-9,
                    abs_tol=0.01
                )
            )

    def test_full_dcf_pipeline(self):
        forecast = self.obtener_forecast()
        bridge = self.obtener_bridge()

        valuation = calcular_dcf(
            forecast,
            self.wacc,
            self.growth,
            bridge["net_debt"],
            self.shares
        )

        expected_ev = (
            valuation["pv_fcff"]
            + valuation["pv_terminal"]
        )

        self.assertAlmostEqual(
            valuation["enterprise_value"],
            expected_ev,
            delta=0.01
        )

        expected_equity = (
            expected_ev - bridge["net_debt"]
        )

        self.assertAlmostEqual(
            valuation["equity_value"],
            expected_equity,
            delta=0.01
        )

        expected_price = (
            expected_equity / self.shares
        )

        self.assertAlmostEqual(
            valuation["intrinsic_price"],
            expected_price,
            places=8
        )

    def test_market_data_integration(self):
        mock_market = {
            "price": self.market_price,
            "shares": self.shares,
            "retrieved_at": "2026-11-07T12:00:00+00:00"
        }

        with patch(
            "valuation_bridge.obtener_mercado",
            return_value=mock_market
        ):
            market = obtener_referencia_mercado("MSFT")

        self.assertEqual(
            market["shares_outstanding"],
            self.shares
        )

        self.assertEqual(
            market["market_price"],
            self.market_price
        )

        self.assertAlmostEqual(
            market["market_cap"],
            self.market_price * self.shares
        )

    def test_upside_consistency(self):
        forecast = self.obtener_forecast()
        bridge = self.obtener_bridge()

        valuation = calcular_dcf(
            forecast,
            self.wacc,
            self.growth,
            bridge["net_debt"],
            self.shares
        )

        intrinsic = calcular_precio_intrinseco(
            valuation["equity_value"],
            self.shares
        )

        upside = calcular_upside(
            intrinsic,
            self.market_price
        )

        expected = (
            intrinsic / self.market_price - 1
        ) * 100

        self.assertAlmostEqual(
            upside, expected
        )


if __name__ == "__main__":
    unittest.main()
