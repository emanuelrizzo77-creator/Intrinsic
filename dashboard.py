# INTRINSIC — FINANCIAL DASHBOARD
# Milestone 13

from copy import deepcopy

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from wacc_data import obtener_datos_wacc
from wacc_calculator import calculate_wacc
from valuation_bridge import (
    obtener_referencia_mercado,
    calcular_upside,
    obtener_puente_financiero,
)

from company_assumptions_engine import generar_escenarios_empresa

from assumptions_engine import (
    obtener_base_historica,
    proyectar_escenario,
)
from scenario_dcf import (
    calcular_dcf,
    WACC,
    TERMINAL_GROWTH,
    NET_DEBT,
)
from valuation_bridge import comparar_puentes_valoracion
from terminal_normalization import (
    calcular_fcff_terminal_normalizado,
)

from terminal_roic_model import (
    calcular_terminal_roic,
)

# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Intrinsic | Equity Valuation",
    page_icon="📈",
    layout="wide",
)
@st.cache_data(ttl=3600, show_spinner=False)
def cargar_datos_wacc(ticker):
    return obtener_datos_wacc(ticker)
@st.cache_data(ttl=3600, show_spinner=False)
def cargar_puente_financiero(ticker):
    return obtener_puente_financiero(ticker)
@st.cache_data(ttl=900, show_spinner=False)
def cargar_referencia_mercado(ticker):
    return obtener_referencia_mercado(ticker)

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1320px; }
h1 { letter-spacing: 0.065em; font-weight: 750; }
h2, h3 { letter-spacing: -0.015em; }
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #172438, #111b2c);
    padding: 18px 20px;
    border-radius: 14px;
    border: 1px solid #2d405b;
    min-height: 116px;
}
[data-testid="stMetricLabel"] { color: #b8c9dd; }
[data-testid="stMetricValue"] { font-weight: 700; letter-spacing: -0.025em; }
[data-testid="stSidebar"] { border-right: 1px solid #26374d; }
.stTabs [data-baseweb="tab-list"] { gap: 12px; border-bottom: 1px solid #30415b; }
.stTabs [data-baseweb="tab"] { font-weight: 600; padding-left: 16px; padding-right: 16px; }
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
.intrinsic-insight {
    background: #142237;
    border: 1px solid #30415b;
    border-left: 3px solid #4da3ff;
    border-radius: 10px;
    padding: 16px 18px;
    margin: 12px 0 18px;
    line-height: 1.6;
    color: #e0e9f5;
}
.intrinsic-insight-title { color: #9fcaff; font-size: .78rem; font-weight: 750; letter-spacing: .09em; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# HISTORICAL DATA
# ==========================================

@st.cache_data(ttl=3600, show_spinner=False)
def cargar_historico(ticker):
    return obtener_base_historica(ticker)


COMPANIES = {
    "MSFT": "Microsoft Corporation",
    "AAPL": "Apple Inc.",
    "NVDA": "NVIDIA Corporation",
    "GOOGL": "Alphabet Inc.",
}

st.sidebar.title("Company Selection")
ticker = st.sidebar.selectbox(
    "Selected Company",
    list(COMPANIES),
    format_func=lambda symbol: f"{COMPANIES[symbol]} ({symbol})",
    key="selected_company_ticker",
)
st.sidebar.caption("Experimental multi-company mode")

# Do not silently value Alphabet using Microsoft assumptions.
if ticker == "GOOGL":
    st.warning("GOOGL 18H — PROXY DCF: D&A uses reported depreciation only; working capital uses AR - AP. These are NOT complete D&A/ONWC. Illustrative valuation only.")


if ticker != "MSFT":
    st.warning(
        "EXPERIMENTAL COMPANY SELECTION — SEC accounting tags, balance "
        "availability, fiscal-year alignment and company-specific forecast "
        "assumptions have not yet been validated for this ticker. "
        "Results must not be used for investment decisions."
    )

st.title("INTRINSIC")
st.caption("Equity Valuation & Financial Analytics")

st.divider()

st.subheader(COMPANIES[ticker])
st.caption(
    f"NASDAQ: {ticker} | SEC EDGAR | "
    "Experimental financial model"
)

st.warning(
    "PROTOTYPE — VALUATION NOT VALIDATED. "
    "Financial assumptions and market reference "
    "are illustrative, not investment advice."
)

try:
    with st.spinner("Loading SEC financial data..."):
        revenue, ultimo_anio = cargar_historico(ticker)

except Exception as error:
    st.error(f"Unable to load SEC data: {error}")
    st.stop()
try:
    with st.spinner("Loading SEC balance sheet..."):
        puente = cargar_puente_financiero(ticker)

    net_debt = puente["net_debt"]

except (ValueError, KeyError, TypeError) as error:
    st.error(
        f"Unable to validate SEC net debt: {error}"
    )
    st.stop()

# ==========================================
# SIDEBAR — ASSUMPTIONS
# ==========================================

@st.cache_data(ttl=3600, show_spinner=False)
def cargar_escenarios_empresa(ticker):
    return generar_escenarios_empresa(ticker)

try:
    with st.spinner("Calculating company-specific historical assumptions..."):
        company_assumptions = cargar_escenarios_empresa(ticker)
except (ValueError, KeyError, TypeError) as error:
    st.error(f"Company-specific assumptions unavailable: {error}")
    st.stop()

st.sidebar.caption("Company-specific SEC historical ratios + illustrative scenario rules")
with st.sidebar.expander("Historical assumptions & methodology"):
    for metric, value in company_assumptions["historical_medians"].items():
        st.write(f"{metric}: {value:.2%} | FY {company_assumptions['historical_years'].get(metric, [])}")
    for warning in company_assumptions["warnings"]:
        st.caption(warning)

st.sidebar.title("Valuation Settings")

escenario = st.sidebar.selectbox(
    "Financial Scenario",
    ["base", "conservative", "optimistic", "custom"],
    format_func=lambda x: x.capitalize()
)

if escenario == "custom":
    hipotesis = deepcopy(company_assumptions["scenarios"]["base"])
else:
    hipotesis = deepcopy(company_assumptions["scenarios"][escenario])

st.sidebar.divider()
st.sidebar.subheader("Forecast Assumptions")

# Each year can be edited independently.

for i in range(5):
    year = ultimo_anio + i + 1

    with st.sidebar.expander(
        f"FY {year}",
        expanded=(i == 0)
    ):
        hipotesis["growth"][i] = (
            st.number_input(
                "Revenue Growth (%)",
                min_value=-50.0,
                max_value=100.0,
                value=hipotesis["growth"][i] * 100,
                step=0.5,
                key=f"growth_{ticker}_{escenario}_{year}"
            ) / 100
        )

        hipotesis["ebit_margin"][i] = (
            st.number_input(
                "EBIT Margin (%)",
                min_value=0.0,
                max_value=100.0,
                value=hipotesis["ebit_margin"][i] * 100,
                step=0.5,
                key=f"margin_{ticker}_{escenario}_{year}"
            ) / 100
        )

        hipotesis["capex_ratio"][i] = (
            st.number_input(
                "CapEx / Revenue (%)",
                min_value=0.0,
                max_value=100.0,
                value=hipotesis["capex_ratio"][i] * 100,
                step=0.5,
                key=f"capex_{ticker}_{escenario}_{year}"
            ) / 100
        )

        hipotesis["da_ratio"][i] = (
            st.number_input(
                "D&A / Revenue (%)",
                min_value=0.0,
                max_value=100.0,
                value=hipotesis["da_ratio"][i] * 100,
                step=0.5,
                key=f"da_{ticker}_{escenario}_{year}"
            ) / 100
        )

hipotesis["nwc_ratio"] = (
    st.sidebar.number_input(
        "Delta NWC / Delta Revenue (%)",
        min_value=0.0,
        max_value=99.0,
        value=hipotesis["nwc_ratio"] * 100,
        step=0.5,
        key=f"nwc_{ticker}_{escenario}",
    ) / 100
)

st.sidebar.divider()
st.sidebar.subheader("DCF Assumptions")


# ==========================================
# DYNAMIC WACC SETTINGS
# ==========================================

wacc_mode = st.sidebar.radio(
    "WACC Calculation Mode",
    ["Automatic Calculation", "Manual Override"]
)

if wacc_mode == "Automatic Calculation":

    
    # ==========================================
    # AUTOMATIC MARKET DATA
    # ==========================================

    try:
        with st.spinner("Loading market and SEC data..."):
            datos_wacc = cargar_datos_wacc(ticker)

    except Exception as error:
        st.error(
            f"Unable to load automatic WACC data: {error}"
        )
        st.info(
            "Check the data sources or switch to "
            "Manual Override."
        )
        st.stop()

    st.sidebar.success("Market data loaded")

    st.sidebar.caption(
        f"Market data: {datos_wacc['market_date']}"
    )

    st.sidebar.caption(
        f"SEC debt balance: {datos_wacc['debt_date']}"
    )

    st.sidebar.divider()

    # ==========================================
    # EDITABLE FINANCIAL ASSUMPTIONS
    # ==========================================

    risk_free_rate = st.sidebar.number_input(
        "Risk-Free Rate (%)",
        min_value=0.0,
        max_value=20.0,
        value=4.0,
        step=0.25,
        key="wacc_risk_free"
    ) / 100

    beta = st.sidebar.number_input(
        "Beta",
        min_value=0.0,
        max_value=5.0,
        value=float(datos_wacc["beta"]),
        step=0.05,
        key=f"wacc_beta_{ticker}"
    )

    equity_risk_premium = st.sidebar.number_input(
        "Equity Risk Premium (%)",
        min_value=0.0,
        max_value=20.0,
        value=5.0,
        step=0.25,
        key="wacc_erp"
    ) / 100

    cost_of_debt = st.sidebar.number_input(
        "Pre-Tax Cost of Debt (%)",
        min_value=0.0,
        max_value=30.0,
        value=5.0,
        step=0.25,
        key="wacc_cost_debt"
    ) / 100

    tax_rate = st.sidebar.number_input(
        "Tax Rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=21.0,
        step=0.5,
        key="wacc_tax_rate"
    ) / 100

    # ==========================================
    # AUTOMATIC CAPITAL STRUCTURE
    # ==========================================

    market_equity = datos_wacc["market_equity"]
    total_debt = datos_wacc["total_debt"]

    st.sidebar.divider()

    st.sidebar.subheader("Capital Structure")

    st.sidebar.metric(
        "Market Capitalization",
        f"${market_equity / 1e9:,.2f} B"
    )

    st.sidebar.metric(
        "Total Debt",
        f"${total_debt / 1e9:,.2f} B"
    )

    # ==========================================
    # WACC CALCULATION
    # ==========================================

    wacc_result = calculate_wacc(
        risk_free_rate=risk_free_rate,
        beta=beta,
        equity_risk_premium=equity_risk_premium,
        cost_of_debt=cost_of_debt,
        tax_rate=tax_rate,
        market_equity=market_equity,
        total_debt=total_debt
    )

    wacc = wacc_result["wacc"]

    st.sidebar.metric(
        "Calculated WACC",
        f"{wacc * 100:.2f}%"
    )

    st.sidebar.caption(
        "Beta and capital structure use external "
        "data. Risk-free rate, ERP, debt cost and "
        "tax rate remain illustrative assumptions."
    )

else:
    tax_rate = st.sidebar.number_input(
        "Forecast Tax Rate (%)", min_value=0.0, max_value=99.0,
        value=21.0, step=0.5, key=f"forecast_tax_{ticker}"
    ) / 100

    wacc = st.sidebar.number_input(
        "Manual WACC (%)",
        min_value=1.0,
        max_value=30.0,
        value=WACC * 100,
        step=0.25,
        key=f"manual_wacc_{ticker}"
    ) / 100

# ==========================================
# MARKET REFERENCE — AUTOMATIC OR MANUAL
# ==========================================
st.sidebar.divider()
st.sidebar.subheader("Market Reference")
reference_mode = st.sidebar.radio(
    "Market Data Mode",
    ["Automatic", "Manual Override"],
    key="market_reference_mode",
)

try:
    with st.spinner("Loading market reference..."):
        market_reference = cargar_referencia_mercado(ticker)
except Exception as error:
    market_reference = None
    st.sidebar.warning(f"Market reference unavailable: {error}")

if reference_mode == "Automatic":
    if market_reference is None:
        st.error("Market data unavailable. Retry or use manual inputs after restoring the data source.")
        st.stop()
    market_price = market_reference["market_price"]
    shares_outstanding = market_reference["shares_outstanding"]
    st.sidebar.metric("Market Price", f"${market_price:,.2f}")
    st.sidebar.metric("Shares Outstanding", f"{shares_outstanding:,.0f}")
    st.sidebar.caption(f"Yahoo Finance | Retrieved UTC: {market_reference['retrieved_at']}")
else:
    market_price = st.sidebar.number_input(
        "Market Price (USD)", min_value=0.01,
        value=float(market_reference["market_price"]) if market_reference else 100.0,
        step=1.0, key=f"manual_market_price_{ticker}",
    )
    shares_outstanding = st.sidebar.number_input(
        "Shares Outstanding (shares)", min_value=1,
        value=int(market_reference["shares_outstanding"]) if market_reference else 1_000_000_000,
        step=1_000_000, key=f"manual_shares_outstanding_{ticker}",
    )
    st.sidebar.caption("Manual values are illustrative until verified.")

terminal_growth = st.sidebar.number_input(
    "Terminal Growth (%)",
    min_value=0.0,
    max_value=10.0,
    value=TERMINAL_GROWTH * 100,
    step=0.25,
    key=f"terminal_growth_{ticker}"
) / 100

# ==========================================
# CALCULATIONS
# ==========================================

if wacc <= terminal_growth:
    st.error(
        "WACC must be greater than Terminal Growth."
    )
    st.stop()

try:
    forecast = proyectar_escenario(
        revenue,
        ultimo_anio,
        hipotesis,
        tax_rate=tax_rate,
    )

    valuation = calcular_dcf(
        forecast,
        wacc,
        terminal_growth,
        net_debt,
        shares_outstanding
    )

except ValueError as error:
    st.error(f"Invalid assumptions: {error}")
    st.stop()

intrinsic_price = valuation["intrinsic_price"]

upside = calcular_upside(intrinsic_price, market_price)

# ==========================================
# DASHBOARD NAVIGATION
# ==========================================

tab_overview, tab_forecast, tab_valuation, tab_sensitivity = st.tabs(
    ["Overview", "Forecast", "Valuation", "Sensitivity"]
)

with tab_overview:
    # ==========================================
    # MAIN KPIs
    # ==========================================

    st.subheader("Valuation Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Intrinsic Value",
        f"${intrinsic_price:,.2f}"
    )

    c2.metric(
        "Market Price",
        f"${market_price:,.2f}"
    )

    c3.metric(
        "Upside / Downside",
        f"{upside:+.2f}%"
    )

    c4.metric(
        "WACC",
        f"{wacc * 100:.2f}%"
    )

    terminal_share = (
        valuation["pv_terminal"] / valuation["enterprise_value"]
        if valuation["enterprise_value"] > 0
        else None
    )
    # Executive interpretation only: no changes to DCF calculations.
    if terminal_share is not None:
        terminal_note = (
            f"{terminal_share:.1%} of enterprise value comes from the discounted "
            "terminal value. Long-term growth, reinvestment and WACC assumptions "
            "therefore have a material influence on this estimate."
        )
    else:
        terminal_note = (
            "Terminal value as a share of enterprise value is not meaningful "
            "when enterprise value is zero or negative."
        )

    if upside < 0:
        pricing_note = (
            f"The model-implied price is {abs(upside):.1f}% below the selected "
            "market reference. This is a scenario result, not a trading recommendation."
        )
    elif upside > 0:
        pricing_note = (
            f"The model-implied price is {upside:.1f}% above the selected "
            "market reference. This is a scenario result, not a trading recommendation."
        )
    else:
        pricing_note = (
            "The model-implied price matches the selected market reference. "
            "This is not an investment recommendation."
        )

    st.markdown(
        '<div class="intrinsic-insight">'
        '<div class="intrinsic-insight-title">VALUATION INSIGHTS</div>'
        f'<strong>Terminal value:</strong> {terminal_note}<br>'
        f'<strong>Market comparison:</strong> {pricing_note}'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.expander("Market Data & Capital Structure"):
        st.write(f"Market capitalization: ${market_price * shares_outstanding / 1e9:,.2f} B")
        st.write(f"SEC net debt: ${net_debt / 1e9:,.2f} B")
        st.write(f"Shares outstanding: {shares_outstanding:,.0f}")
        st.write(f"SEC balance date: {puente['balance_date']}")


with tab_forecast:
    # ==========================================
    # FINANCIAL FORECAST
    # ==========================================

    st.subheader("Financial Forecast")

    df = pd.DataFrame(forecast)

    # Internal amounts are USD.
    # Display amounts in USD millions.

    financial_columns = [
        "revenue",
        "ebit",
        "nopat",
        "da",
        "capex",
        "delta_nwc",
        "fcff",
    ]

    df_display = df.copy()

    for col in financial_columns:
        df_display[col] = df_display[col] / 1e6

    st.caption("Financial figures in USD millions (USD M).")

    forecast_table = df_display[["year"] + financial_columns].rename(
        columns={
            "year": "Fiscal Year",
            "revenue": "Revenue",
            "ebit": "EBIT",
            "nopat": "NOPAT",
            "da": "D&A",
            "capex": "CapEx",
            "delta_nwc": "Change in NWC",
            "fcff": "FCFF",
        }
    )

    st.dataframe(
        forecast_table.round(2),
        hide_index=True,
        use_container_width=True,
    )

    # ==========================================
    # REVENUE & FCFF CHARTS
    # ==========================================

    left, right = st.columns(2)

    with left:
        st.subheader("Revenue Projection")

        fig_revenue = go.Figure()

        fig_revenue.add_trace(
            go.Scatter(
                x=df["year"],
                y=df["revenue"] / 1e9,
                mode="lines+markers",
                name="Revenue",
                line=dict(color="#4da3ff", width=3)
            )
        )

        fig_revenue.update_layout(
            template="plotly_dark",
            xaxis_title="Fiscal Year",
            yaxis_title="USD Billions",
            height=350
        )

        st.plotly_chart(
            fig_revenue,
            use_container_width=True
        )

    with right:
        st.subheader("Free Cash Flow Forecast")

        fig_fcff = go.Figure()

        fig_fcff.add_trace(
            go.Bar(
                x=df["year"],
                y=df["fcff"] / 1e9,
                name="FCFF",
                marker_color="#36c5a0"
            )
        )

        fig_fcff.update_layout(
            template="plotly_dark",
            xaxis_title="Fiscal Year",
            yaxis_title="USD Billions",
            height=350
        )

        st.plotly_chart(
            fig_fcff,
            use_container_width=True
        )

with tab_valuation:
    # ==========================================
    # VALUATION SUMMARY
    # ==========================================

    st.subheader("DCF Valuation Breakdown")

    valuation_table = pd.DataFrame({
        "Metric": [
            "PV of Forecast FCFF",
            "PV of Terminal Value",
            "Enterprise Value",
            "Net Debt",
            "Equity Value",
        ],
        "USD Billions": [
            valuation["pv_fcff"] / 1e9,
            valuation["pv_terminal"] / 1e9,
            valuation["enterprise_value"] / 1e9,
            net_debt / 1e9,
            valuation["equity_value"] / 1e9,
        ]
    })

    st.dataframe(
        valuation_table.round(2),
        hide_index=True,
        use_container_width=True
    )


    # ==========================================
    # TERMINAL VALUE METHODOLOGY COMPARISON
    # ==========================================

    st.subheader("Terminal Value Methodology Comparison")

    st.caption(
        "Alternative terminal valuation methodologies. "
        "All scenarios share the current forecast, WACC, "
        "terminal growth, net debt, and share count. "
        "The primary DCF valuation remains unchanged."
    )

    with st.expander("Terminal Normalization Assumptions"):
        terminal_ebit_margin = st.number_input(
            "Terminal EBIT Margin (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(hipotesis["ebit_margin"][-1] * 100),
            key=f"terminal_margin_{ticker}_{escenario}",
            step=1.0,
        ) / 100

        terminal_tax_rate = st.number_input(
            "Terminal Tax Rate (%)",
            min_value=0.0,
            max_value=99.0,
            value=float(tax_rate * 100),
            step=1.0,
            key=f"terminal_tax_{ticker}_{escenario}",
        ) / 100

        terminal_da_ratio = st.number_input(
            "Terminal D&A / Revenue (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(hipotesis["da_ratio"][-1] * 100),
            key=f"terminal_da_{ticker}_{escenario}",
            step=1.0,
        ) / 100

        terminal_capex_ratio = st.number_input(
            "Terminal CapEx / Revenue (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(hipotesis["capex_ratio"][-1] * 100),
            key=f"terminal_capex_{ticker}_{escenario}",
            step=1.0,
        ) / 100

        terminal_nwc_ratio = st.number_input(
            "Terminal Incremental NWC / Revenue Change (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(hipotesis["nwc_ratio"] * 100),
            key=f"terminal_nwc_{ticker}_{escenario}",
            step=1.0,
        ) / 100

    try:
        normalizado = calcular_fcff_terminal_normalizado(
            revenue_final=forecast[-1]["revenue"],
            terminal_growth=terminal_growth,
            ebit_margin=terminal_ebit_margin,
            tax_rate=terminal_tax_rate,
            da_ratio=terminal_da_ratio,
            capex_ratio=terminal_capex_ratio,
            nwc_ratio=terminal_nwc_ratio,
        )

        n = len(forecast)
        pv_fcff = valuation["pv_fcff"]

        pv_terminal_normalizado = (
            normalizado["fcff_terminal"]
            / (wacc - terminal_growth)
            / (1 + wacc) ** n
        )

        precio_normalizado = (
            pv_fcff
            + pv_terminal_normalizado
            - net_debt
        ) / shares_outstanding

        comparacion_terminal = [
            {
                "Method": "Gordon Growth (Base)",
                "Intrinsic Price ($)": intrinsic_price,
                "vs. Base (%)": 0.0,
            },
            {
                "Method": "Normalized Terminal FCFF",
                "Intrinsic Price ($)": precio_normalizado,
                "vs. Base (%)": (
                    precio_normalizado / intrinsic_price - 1
                ) * 100 if intrinsic_price > 0 else None,
            },
        ]

        for roic in [0.10, 0.15, 0.20, 0.25]:
            resultado_roic = calcular_terminal_roic(
                nopat_terminal=normalizado["nopat_terminal"],
                terminal_growth=terminal_growth,
                roic=roic,
                wacc=wacc,
                forecast_years=n,
            )

            precio_roic = (
                pv_fcff
                + resultado_roic["pv_terminal"]
                - net_debt
            ) / shares_outstanding

            comparacion_terminal.append({
                "Method": f"Terminal ROIC {roic:.0%}",
                "Intrinsic Price ($)": precio_roic,
                "vs. Base (%)": (
                    precio_roic / intrinsic_price - 1
                ) * 100 if intrinsic_price > 0 else None,
            })

        tabla_terminal = pd.DataFrame(comparacion_terminal)

        st.dataframe(
            tabla_terminal.round(2),
            hide_index=True,
            use_container_width=True,
        )

        st.caption(
            "ROIC scenarios represent assumed incremental returns "
            "on terminal reinvestment, not historical company ROIC. "
            "Normalization assumptions are illustrative."
        )

    except ValueError as error:
        st.warning(
            f"Terminal methodology comparison unavailable: {error}"
        )

    # ==========================================
    # EV-TO-EQUITY RECONCILIATION
    # ==========================================

    st.subheader("EV-to-Equity Reconciliation")

    st.caption(
        "Illustrative bridge adjustments. "
        "The primary DCF valuation remains unchanged."
    )

    # ==========================================
    # AUTOMATED LONG-TERM INVESTMENTS
    # ==========================================

    inversiones_ajuste = puente.get(
        "long_term_investments"
    )

    if inversiones_ajuste is None:
        st.info(
            "Long-term investments are unavailable "
            "for the selected SEC balance."
        )


    escenarios_puente = comparar_puentes_valoracion(
        enterprise_value=valuation["enterprise_value"],
        net_debt=net_debt,
        shares=shares_outstanding,
        finance_lease_liabilities=puente.get(
            "finance_lease_liabilities"
        ),
        non_operating_investments=inversiones_ajuste,
    )

    nombres_escenarios = {
        "base": "Base DCF",
        "including_finance_leases": "Finance Leases",
        "including_investments": "Long-Term Investments",
        "leases_and_investments": "Combined Adjustments",
    }

    precio_base = escenarios_puente[
        "base"
    ]["intrinsic_price"]

    filas_puente = []

    for clave, resultado in escenarios_puente.items():
        precio = resultado["intrinsic_price"]

        diferencia = (
            (precio / precio_base - 1) * 100
            if precio_base != 0
            else None
        )

        filas_puente.append({
            "Scenario": nombres_escenarios.get(
                clave, clave
            ),
            "Net Debt ($B)": (
                resultado["net_debt"] / 1e9
            ),
            "Equity Value ($B)": (
                resultado["equity_value"] / 1e9
            ),
            "Intrinsic Price ($)": precio,
            "vs. Base (%)": diferencia,
        })

    tabla_puente = pd.DataFrame(filas_puente)

    st.dataframe(
        tabla_puente.style.format({
            "Net Debt ($B)": "{:,.2f}",
            "Equity Value ($B)": "{:,.2f}",
            "Intrinsic Price ($)": "${:,.2f}",
            "vs. Base (%)": "{:+.2f}%",
        }, na_rep="N/A"),
        hide_index=True,
        use_container_width=True,
    )

    st.warning(
        "Adjusted scenarios are arithmetic illustrations, "
        "not independently validated fair values. "
        "Finance lease adjustments require FCFF consistency. "
        "The investment adjustment assumes all reported "
        "long-term investments are non-operating."
    )


    st.subheader("Enterprise to Equity Bridge")

    bridge_data = pd.DataFrame({
        "Component": [
            "Enterprise Value",
            "Total Debt",
            "Cash & Equivalents",
            "Short-Term Investments",
            "Equity Value",
        ],
        "USD Billions": [
            valuation["enterprise_value"] / 1e9,
            -puente["total_debt"] / 1e9,
            puente["cash"] / 1e9,
            puente["short_term_investments"] / 1e9,
            valuation["equity_value"] / 1e9,
        ],
    })

    fig_bridge = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=[
                "absolute",
                "relative",
                "relative",
                "relative",
                "total",
            ],
            x=bridge_data["Component"],
            y=bridge_data["USD Billions"],
            text=[
                f"${abs(v):,.2f} B"
                for v in bridge_data["USD Billions"]
            ],
            textposition="outside",
            connector={"line": {"color": "#64748b"}},
            increasing={"marker": {"color": "#36c5a0"}},
            decreasing={"marker": {"color": "#ff6b6b"}},
            totals={"marker": {"color": "#4da3ff"}},
        )
    )

    fig_bridge.update_layout(
        template="plotly_dark",
        title="Enterprise Value to Equity Value",
        yaxis_title="USD Billions",
        height=480,
        showlegend=False,
    )

    st.plotly_chart(
        fig_bridge,
        use_container_width=True
    )

    st.caption(
        f"Balance date: {puente['balance_date']} | "
        f"Source: {puente['source']} | "
        "Net debt = Debt - Cash - Short-Term Investments. "
        "Other potential EV-to-equity adjustments "
        "have not yet been validated."
    )

with tab_sensitivity:
    # ==========================================
    # SENSITIVITY MATRIX
    # ==========================================

    st.subheader("WACC × Terminal Growth Sensitivity")

    wacc_values = [
        wacc - 0.02,
        wacc - 0.01,
        wacc,
        wacc + 0.01,
        wacc + 0.02,
    ]

    growth_values = [
        terminal_growth - 0.01,
        terminal_growth - 0.005,
        terminal_growth,
        terminal_growth + 0.005,
        terminal_growth + 0.01,
    ]

    matrix = []

    for w in wacc_values:
        row = []

        for g in growth_values:
            if w <= g or w <= 0 or g <= -1:
                row.append(float("nan"))
                continue

            result = calcular_dcf(
                forecast,
                w,
                g,
                net_debt,
                shares_outstanding
            )

            row.append(result["intrinsic_price"])

        matrix.append(row)

    fig_heatmap = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=[f"{g*100:.2f}%" for g in growth_values],
            y=[f"{w*100:.2f}%" for w in wacc_values],
            colorscale="RdYlGn",
            text=[
                [
                    f"${v:.2f}" if pd.notna(v) else "N/A"
                    for v in row
                ]
                for row in matrix
            ],
            texttemplate="%{text}",
            hovertemplate=(
                "Growth: %{x}<br>"
                "WACC: %{y}<br>"
                "Price: %{text}<extra></extra>"
            )
        )
    )

    fig_heatmap.update_layout(
        template="plotly_dark",
        xaxis_title="Terminal Growth",
        yaxis_title="WACC",
        height=420
    )

    st.plotly_chart(
        fig_heatmap,
        use_container_width=True
    )

    # ==========================================
    # EXPORT
    # ==========================================

    csv_data = df_display.to_csv(index=False)

    st.download_button(
        "Download Forecast CSV",
        data=csv_data,
        file_name=f"intrinsic_{ticker.lower()}_forecast.csv",
        mime="text/csv"
    )

    st.caption(
        "Intrinsic MVP | Data: SEC EDGAR | "
        "Illustrative assumptions | "
        "Market reference: Yahoo Finance or manual | "
        "Valuation not validated"
    )


