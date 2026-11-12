# INTRINSIC — FINANCIAL DASHBOARD (Model 27, single engine)
# Milestone 13

from copy import deepcopy
from html import escape as html_escape
from math import isfinite
from company_explorer_21a import fetch_sec_directory
from financial_audit_21b import fetch_companyfacts, audit_companyfacts
from universal_valuation_21c import fetch_sec_profile, classify_sic
from universal_financial_23b import normalize_balance_23b
from universal_financial_23c import analyze_historical_23c
from universal_financial_23e import value_fcff_23e

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
from universal_financial_24g import assess_company as assess_company_24g

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

# Intro animation only once per Streamlit session.
# No JavaScript, external assets, or financial-engine changes.
_show_intro = not st.session_state.get("intrinsic_intro_seen", False)
st.session_state["intrinsic_intro_seen"] = True
# The opening is CSS-only and does not delay or change financial calculations.

st.markdown("""
<style>
/* INTRINSIC 20A — presentation-only fintech theme */
:root { --ink:#0b1220; --panel:#172338; --accent:#3b82f6; --mint:#2dd4bf; }
.stApp { background: #0b1220; color: #e9f1fb; }
.block-container { padding-top: 1.6rem; padding-bottom: 3.5rem; max-width: 1380px; }
h1 { font-size: clamp(2.25rem,4vw,3.15rem); letter-spacing: -.045em; font-weight: 780; }
h2 { letter-spacing: -.028em; font-weight: 700; }
h3 { letter-spacing: -.02em; }
[data-testid="stSidebar"] { background: #101b2c; border-right: 1px solid #273a55; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { line-height: 1.5; }
[data-testid="stMetric"] {
    background: linear-gradient(150deg,#192b44 0%,#142239 65%,#101c30 100%);
    padding: 20px 22px; border-radius: 16px;
    border: 1px solid #2b4161; min-height: 126px;
    box-shadow: 0 7px 24px rgba(0,0,0,.13);
}
[data-testid="stMetricLabel"] { color: #a8bfd9; font-size: .84rem; }
[data-testid="stMetricValue"] { font-weight: 750; letter-spacing: -.04em; }
[data-testid="stMetricDelta"] { font-weight: 600; }
.stTabs [data-baseweb="tab-list"] { gap: 9px; border-bottom: 1px solid #2a405e; }
.stTabs [data-baseweb="tab"] { font-weight: 650; padding: 12px 19px; border-radius: 9px 9px 0 0; }
.stTabs [aria-selected="true"] { color: #79b7ff !important; }
[data-testid="stDataFrame"] { border: 1px solid #293e59; border-radius: 12px; overflow: hidden; }
[data-testid="stExpander"] { border: 1px solid #2b405d; border-radius: 12px; background: #121f32; }
[data-testid="stAlert"] { border-radius: 12px; }
[data-testid="stPlotlyChart"] { border: 1px solid #233952; border-radius: 14px; overflow: hidden; }
.intrinsic-insight {
    background: linear-gradient(120deg,#152942,#122238);
    border: 1px solid #315074; border-left: 3px solid #3b82f6;
    border-radius: 13px; padding: 18px 20px; margin: 14px 0 20px;
    line-height: 1.65; color: #e2edfa;
}
.intrinsic-insight-title { color: #8bc0ff; font-size: .77rem; font-weight: 800; letter-spacing: .11em; margin-bottom: 8px; }
.intrinsic-eyebrow { font-size: .76rem; letter-spacing: .19em; color: #2dd4bf; font-weight: 750; margin-bottom: .25rem; }
.intrinsic-subtitle { color: #a5bbd3; margin-top: -.65rem; margin-bottom: 1.3rem; font-size: 1rem; }


/* 20A REDESIGN: intentionally new information architecture */
[data-testid="stHeader"] {background:rgba(7,14,27,.92)}
[data-testid="stSidebar"] {background:#0b1525!important}
.block-container {max-width:1460px;padding-top:2rem}
.intrinsic-hero {padding:30px 34px 28px;border:1px solid #244365;border-radius:22px;background:radial-gradient(circle at 86% 18%,rgba(45,212,191,.17),transparent 35%),linear-gradient(125deg,#172e4b,#0d1c30 75%);margin:0 0 24px;position:relative;overflow:hidden}
.intrinsic-hero .eyebrow {color:#5eead4;font-size:12px;font-weight:750;letter-spacing:2.2px}
.intrinsic-hero h1 {font-size:44px;line-height:1.1;margin:13px 0 10px;color:#f8fafc;letter-spacing:-1.7px}
.intrinsic-hero p {color:#a8c2db;margin:0;font-size:15px}
.intrinsic-hero .pill {display:inline-block;background:#123b45;border:1px solid #267e79;color:#9ff6df;padding:6px 12px;border-radius:50px;font-size:11px;font-weight:750;margin-top:22px;letter-spacing:.6px}
.intrinsic-section-label {font-size:11px;letter-spacing:2px;color:#5eead4;font-weight:800;margin:14px 0 9px}
.intrinsic-dashboard-heading {font-size:27px;color:#f8fafc;font-weight:750;margin:0 0 6px;letter-spacing:-.6px}
.intrinsic-dashboard-sub {color:#8da9c4;font-size:14px;margin:0 0 23px}
.intrinsic-kpi-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;margin:8px 0 25px}
.intrinsic-kpi {background:#111f33;border:1px solid #29415d;border-radius:17px;padding:22px 20px;min-height:133px;box-shadow:0 12px 25px rgba(0,0,0,.1)}
.intrinsic-kpi.primary {background:linear-gradient(140deg,#1b4670,#163253);border-color:#3c7fc0}
.intrinsic-kpi .label {font-size:12px;color:#aac2d9;font-weight:600;margin-bottom:13px}
.intrinsic-kpi .value {font-size:30px;line-height:1.15;color:#f7fbff;font-weight:800;letter-spacing:-1px}
.intrinsic-kpi .foot {font-size:11px;color:#7999b5;margin-top:10px}
.intrinsic-kpi .positive {color:#5eead4}.intrinsic-kpi .negative {color:#fda4af}
.intrinsic-comparison {border:1px solid #29415d;background:#101d30;border-radius:16px;padding:20px 23px;margin:0 0 25px}
.intrinsic-comparison .top {display:flex;justify-content:space-between;color:#c7d9e9;font-size:13px;margin-bottom:13px}
.intrinsic-comparison .track {height:11px;background:#27384d;border-radius:20px;overflow:hidden}
.intrinsic-comparison .fill {height:100%;background:linear-gradient(90deg,#3b82f6,#2dd4bf);border-radius:20px}
.intrinsic-comparison .note {font-size:12px;color:#8da9c4;margin-top:12px}
@media(max-width:1050px){.intrinsic-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.intrinsic-kpi-grid{grid-template-columns:1fr}.intrinsic-hero{padding:22px}.intrinsic-hero h1{font-size:33px}}


/* MILESTONE 20A — MONOCHROME CINEMATIC OPENING */
@keyframes intrinsicCurtain {0%,77%{opacity:1;visibility:visible}100%{opacity:0;visibility:hidden;pointer-events:none}}
@keyframes intrinsicWhiteI {0%,14%{opacity:0;transform:translateY(9px) scale(.96);filter:blur(5px)}44%,74%{opacity:1;transform:translateY(0) scale(1);filter:blur(0)}100%{opacity:0;transform:translateY(-3px) scale(1.025);filter:blur(0)}}
@keyframes intrinsicType {from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}
@keyframes intrinsicCaretMove {from{left:0}to{left:100%}}
@keyframes intrinsicCaretFade {0%,90%{opacity:1}100%{opacity:0}}
@keyframes intrinsicCursor {0%,100%{border-right-color:#fff}50%{border-right-color:transparent}}
.intrinsic-intro{position:fixed;inset:0;z-index:2147483000;background:#000;display:flex;align-items:center;justify-content:center;pointer-events:auto;animation:intrinsicCurtain 2.55s ease-in-out forwards}
.intrinsic-intro-mark{font-family:Georgia,'Times New Roman',serif;font-size:clamp(130px,20vw,220px);font-weight:400;line-height:1;color:#fff;animation:intrinsicWhiteI 2.35s ease-in-out both;user-select:none}
.intrinsic-wordmark{position:relative;display:inline-block;width:max-content;max-width:100%;color:#f8fafc;font-size:clamp(20px,2.7vw,32px);font-weight:800;letter-spacing:.16em;white-space:nowrap;overflow:visible;border:0}
.intrinsic-wordmark.animate{clip-path:inset(0 100% 0 0);animation:intrinsicType 1.35s steps(9,end) 2.58s forwards}
.intrinsic-wordmark.animate::after{content:"";position:absolute;top:0;bottom:0;left:0;width:2px;background:#fff;animation:intrinsicCaretMove 1.35s steps(9,end) 2.58s forwards,intrinsicCaretFade .25s linear 3.98s forwards}
/* Native Streamlit segmented control, replacing fragile tab DOM selectors. */
[data-testid="stSegmentedControl"] {margin:8px 0 24px}
[data-testid="stSegmentedControl"] [role="radiogroup"] {background:#0e1d31;border:1px solid #2b4665;border-radius:999px;padding:5px;gap:3px;display:flex;width:100%}
[data-testid="stSegmentedControl"] label {flex:1;justify-content:center;border-radius:999px!important;transition:background-color .3s ease,color .3s ease,box-shadow .3s ease}
[data-testid="stSegmentedControl"] label:has(input:checked),[data-testid="stSegmentedControl"] [aria-checked="true"] {background:#24598c!important;color:white!important;box-shadow:0 2px 12px #0004}
@media(prefers-reduced-motion:reduce){.intrinsic-intro{display:none!important}.intrinsic-wordmark.animate{animation:none!important;clip-path:none!important}.intrinsic-wordmark.animate::after{display:none!important}}


/* MILESTONE 20C — accessible contextual hover explanations */
.intrinsic-kpi{position:relative;overflow:visible}
.intrinsic-kpi .label{display:flex;align-items:center;gap:8px}
.intrinsic-help{position:relative;display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;flex:none;border:1px solid #6c92b6;border-radius:50%;font:700 11px/1 system-ui,sans-serif;color:#a8c9e9;cursor:help;outline-offset:3px;vertical-align:middle}
.intrinsic-help:hover,.intrinsic-help:focus-visible{border-color:#2dd4bf;color:#2dd4bf;background:#183e49}
.intrinsic-help .intrinsic-tip{pointer-events:none;position:absolute;bottom:calc(100% + 12px);left:50%;transform:translate(-50%,5px);width:max-content;max-width:min(300px,75vw);min-width:210px;white-space:normal;text-align:left;text-transform:none;letter-spacing:normal;line-height:1.5;font-size:12px;font-weight:450;color:#e7f2ff;background:#071525;border:1px solid #3c668a;border-radius:11px;padding:12px 14px;box-shadow:0 14px 35px #0009;opacity:0;visibility:hidden;transition:opacity .17s ease,transform .17s ease,visibility .17s;z-index:1000}
.intrinsic-help:hover .intrinsic-tip,.intrinsic-help:focus-visible .intrinsic-tip{opacity:1;visibility:visible;transform:translate(-50%,0)}
.intrinsic-kpi:first-child .intrinsic-tip{left:0;transform:translate(0,5px)}
.intrinsic-kpi:first-child .intrinsic-help:hover .intrinsic-tip,.intrinsic-kpi:first-child .intrinsic-help:focus-visible .intrinsic-tip{transform:translate(0,0)}
.intrinsic-kpi:last-child .intrinsic-tip{left:auto;right:0;transform:translate(0,5px)}
.intrinsic-kpi:last-child .intrinsic-help:hover .intrinsic-tip,.intrinsic-kpi:last-child .intrinsic-help:focus-visible .intrinsic-tip{transform:translate(0,0)}
.intrinsic-glossary{display:flex;flex-wrap:wrap;gap:8px;margin:9px 0 20px}
.intrinsic-glossary-item{display:inline-flex;align-items:center;gap:7px;background:#14243a;border:1px solid #2b4664;border-radius:999px;padding:7px 11px;color:#bcd2e8;font-size:12px}
@media(prefers-reduced-motion:reduce){.intrinsic-help .intrinsic-tip{transition:none}}

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

# Initial Top 25 candidate universe.
# Membership is a curated selection, not a live market-cap ranking.
TOP_25 = {
    **COMPANIES,
    "AMZN": "Amazon.com Inc.",
    "META": "Meta Platforms Inc.",
    "AVGO": "Broadcom Inc.",
    "TSLA": "Tesla Inc.",
    "BRK-B": "Berkshire Hathaway Inc.",
    "WMT": "Walmart Inc.",
    "LLY": "Eli Lilly and Company",
    "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.",
    "MA": "Mastercard Incorporated",
    "XOM": "Exxon Mobil Corporation",
    "JNJ": "Johnson & Johnson",
    "ORCL": "Oracle Corporation",
    "COST": "Costco Wholesale Corporation",
    "HD": "The Home Depot Inc.",
    "PG": "The Procter & Gamble Company",
    "ABBV": "AbbVie Inc.",
    "BAC": "Bank of America Corporation",
    "NFLX": "Netflix Inc.",
    "KO": "The Coca-Cola Company",
    "AMD": "Advanced Micro Devices Inc.",
}
if _show_intro:
    st.markdown('<div class="intrinsic-intro" aria-hidden="true"><div class="intrinsic-intro-mark">I</div></div>', unsafe_allow_html=True)

st.markdown(
    '<div class="intrinsic-wordmark ' + ('animate' if _show_intro else '') + '">INTRINSIC</div>',
    unsafe_allow_html=True,
)

st.sidebar.markdown("**INTRINSIC**  ·  RESEARCH TERMINAL")
st.sidebar.caption("Equity valuation workspace")
st.sidebar.divider()
st.sidebar.title("Company Selection")
selection_mode = st.sidebar.radio(
    "Company source",
    ["Top 25 companies", "SEC company search"],
    key="m22_source",
)
new_company = selection_mode == "SEC company search"
selected_cik = None
if not new_company:
    ticker = st.sidebar.selectbox(
        "Selected Company",
        list(TOP_25),
        format_func=lambda symbol: f"{TOP_25[symbol]} ({symbol})",
        key="selected_company_ticker",
    )
    company_name = TOP_25[ticker]
    # Companies without a dedicated model use the SEC pipeline.
    new_company = ticker not in COMPANIES
    if new_company:
        @st.cache_data(ttl=86400, show_spinner=False)
        def _top25_sec_directory():
            return fetch_sec_directory()

        try:
            directory = _top25_sec_directory()
            matches = [
                cik for symbol, name, cik in directory
                if symbol.upper().replace(".", "-") == ticker.upper()
            ]
            if not matches:
                st.error(f"SEC CIK not found for {ticker}.")
                st.stop()
            selected_cik = matches[0]
        except Exception as exc:
            st.error(f"SEC company lookup failed: {exc}")
            st.stop()
else:
    @st.cache_data(ttl=86400, show_spinner=False)
    def _m22_directory():
        return fetch_sec_directory()
    try:
        directory = _m22_directory()
    except Exception as exc:
        st.error(f"SEC directory unavailable: {exc}")
        st.info("Configure INTRINSIC_SEC_USER_AGENT with a real contact email.")
        st.stop()
    options = {f"{name} ({symbol})": (symbol, name, cik) for symbol, name, cik in directory}
    choice = st.sidebar.selectbox("Search name or ticker", list(options), index=None,
                                  placeholder="Search Coca-Cola, KO, etc.", key="m22_search")
    if choice is None:
        st.info("Choose a company from the sidebar to open its Intrinsic workspace.")
        st.stop()
    ticker, company_name, selected_cik = options[choice]
    if ticker in COMPANIES:
        new_company = False
    else:
        st.sidebar.caption(f"SEC CIK: {selected_cik:010d}")

# Do not silently value Alphabet using Microsoft assumptions.
st.markdown(
    f"""<section class="intrinsic-hero">
      <div class="eyebrow">INTRINSIC / EQUITY RESEARCH</div>
      <h1>{html_escape(company_name)}</h1>
      <p>{ticker} &nbsp;·&nbsp; Discounted Cash Flow Analysis &nbsp;·&nbsp; SEC EDGAR + Market Data</p>
      <span class="pill">RESEARCH WORKSPACE &nbsp; / &nbsp; EXPERIMENTAL MODEL</span>
    </section>""", unsafe_allow_html=True,
)

st.caption(
    "Research tool · Revenue and margin forecasts validated out of sample · "
    "The valuation is an estimate with a range, not investment advice."
)

# Model 27 is the single forecasting engine; it loads and audits its own SEC inputs.
medians = {}
balance = {}

st.sidebar.subheader("DCF Assumptions")


# ==========================================
# DYNAMIC WACC SETTINGS
# ==========================================

wacc_mode = st.sidebar.radio(
    "WACC Calculation Mode",
    ["Automatic Calculation", "Manual Override"],
    key=f"wacc_mode_{ticker}",
)

if new_company:
    st.sidebar.caption(
        "Automatic WACC uses company-specific market and financial data. "
        "Review source dates and assumptions before relying on the result."
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

    
    historical_kd = datos_wacc.get("historical_kd")

    if historical_kd is not None:
        default_kd = historical_kd["cost_of_debt"] * 100
        kd_source = (
            f"SEC historical estimate ({historical_kd['fiscal_end']})"
        )
    else:
        default_kd = 5.0
        kd_source = "Manual assumption — SEC historical Kd unavailable"

    cost_of_debt = st.sidebar.number_input(
        "Pre-Tax Cost of Debt (%)",
        value=float(default_kd),
        min_value=0.0,
        max_value=30.0,
        step=0.1,
        key=f"wacc_cost_debt_{ticker}",
    ) / 100

    st.sidebar.caption(f"Cost of debt source: {kd_source}")


    tax_rate = st.sidebar.number_input(
        "Tax Rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=21.0,
        step=0.5,
        key=f"wacc_tax_rate_{ticker}"
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
        value=float(medians["Effective tax rate"] * 100) if new_company and medians.get("Effective tax rate") is not None else 21.0, step=0.5, key=f"forecast_tax_{ticker}"
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
    if new_company and market_reference is None:
        st.sidebar.warning("Fallback share count from SEC common stock is not necessarily diluted; market price default $100 is a placeholder. Enter verified figures.")

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

# ==========================================
# INTRINSIC 27 WORKSPACE (single model)
# ==========================================
from dashboard_27_panel import render_model_27
render_model_27(ticker, wacc, terminal_growth, market_price, shares_outstanding)
