# INTRINSIC — FINANCIAL DASHBOARD
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
if ticker == "GOOGL":
    st.warning("GOOGL 18H — PROXY DCF: D&A uses reported depreciation only; working capital uses AR - AP. These are NOT complete D&A/ONWC. Illustrative valuation only.")


if ticker != "MSFT" and not new_company:
    st.warning(
        "EXPERIMENTAL COMPANY SELECTION — SEC accounting tags, balance "
        "availability, fiscal-year alignment and company-specific forecast "
        "assumptions have not yet been validated for this ticker. "
        "Results must not be used for investment decisions."
    )

st.markdown(
    f"""<section class="intrinsic-hero">
      <div class="eyebrow">INTRINSIC / EQUITY RESEARCH</div>
      <h1>{html_escape(company_name)}</h1>
      <p>{ticker} &nbsp;·&nbsp; Discounted Cash Flow Analysis &nbsp;·&nbsp; SEC EDGAR + Market Data</p>
      <span class="pill">RESEARCH WORKSPACE &nbsp; / &nbsp; EXPERIMENTAL MODEL</span>
    </section>""", unsafe_allow_html=True,
)

st.warning(
    "PROTOTYPE — VALUATION NOT VALIDATED. "
    "Financial assumptions and market reference "
    "are illustrative, not investment advice."
)

if new_company:
    @st.cache_data(ttl=3600, show_spinner=False)
    def _m22_sec_bundle(cik):
        payload = fetch_companyfacts(cik)
        audit = audit_companyfacts(payload)
        profile = fetch_sec_profile(cik)
        balances = normalize_balance_23b(payload, [r["Fiscal year end"] for r in audit["rows"]])
        historical = analyze_historical_23c(payload)
        decision = classify_sic(profile.get("sic"))
        quality_24g = assess_company_24g(
        payload,
        sector_model=decision.model,
        last_n=5,
        allow_depreciation_proxy=True,
        )
        blockers = list(historical["latest_data_blockers"])
        if decision.model != "fcff":
            blockers.append("Sector is not eligible for standard non-financial FCFF valuation.")
        if not balances or balances[-1].get("Net debt (cash-only)") is None:
            blockers.append("Missing latest cash-only net debt")
        if not balances or balances[-1].get("Shares outstanding") is None:
            blockers.append("Missing latest reported shares snapshot")
        return audit, profile, balances, decision, blockers, historical, quality_24g
    try:
        with st.spinner("Auditing SEC annual financials..."):
            sec_audit, sec_profile, sec_balances, sec_decision, blockers, historical_23c, quality_24g = _m22_sec_bundle(selected_cik)
    except Exception as exc:
        st.error(f"SEC financial extraction failed: {exc}")
        st.stop()
    st.caption(f"SEC industry: {sec_decision.category} · Model: {sec_decision.model.upper()} · Status: illustrative / unvalidated")
    
    with st.expander("Data Sources & Methodology · SEC audit", expanded=False):
        st.write("The model uses audited SEC tag extraction, not independently reconciled 10-K financials.")
        st.dataframe(pd.DataFrame(sec_audit["rows"]), hide_index=True, use_container_width=True)

        if sec_balances:
            st.dataframe(
                pd.DataFrame(sec_balances).drop(columns=["tags"], errors="ignore"),
                hide_index=True,
                use_container_width=True,
            )
            st.json(sec_balances[-1]["tags"])

        for issue in blockers:
            st.warning(issue)

        st.markdown("### Financial Data Quality · 24G")

        status_24g = quality_24g.get("status", "UNKNOWN")
        st.write("Coverage status:", status_24g)

        if quality_24g.get("missing"):
            st.warning("Missing financial fields:")
            st.write(quality_24g["missing"])

        if quality_24g.get("proxies"):
            st.info("Provisional financial proxies detected.")
            st.json(quality_24g["proxies"])

        if quality_24g.get("warnings"):
            for warning in quality_24g["warnings"]:
                st.caption(str(warning))

    if blockers:
        # Keep the SAME four-section research terminal, even when SEC facts are incomplete.
        # Do not manufacture equity values, share counts, or working-capital components.
        st.warning("DCF not available yet: required SEC inputs are missing. The same research workspace remains accessible.")
        section = st.segmented_control(
            "Dashboard section", options=["Overview", "Forecast", "Valuation", "Sensitivity"],
            default="Overview", key="intrinsic_section", label_visibility="collapsed",
        )
        if section == "Overview":
            st.markdown('<div class="intrinsic-section-label">01 / VALUATION SNAPSHOT</div>', unsafe_allow_html=True)
            st.markdown('<div class="intrinsic-dashboard-heading">Valuation at a glance</div>', unsafe_allow_html=True)
            st.markdown('<div class="intrinsic-dashboard-sub">Five-year cash flow forecast · pending verified financial inputs</div>', unsafe_allow_html=True)
            st.markdown('''<div class="intrinsic-kpi-grid">
              <div class="intrinsic-kpi primary"><div class="label">INTRINSIC VALUE / SHARE</div><div class="value">N/A</div><div class="foot">Awaiting SEC reconciliation</div></div>
              <div class="intrinsic-kpi"><div class="label">MARKET PRICE / SHARE</div><div class="value">N/A</div><div class="foot">Not loaded for blocked valuation</div></div>
              <div class="intrinsic-kpi"><div class="label">UPSIDE / DOWNSIDE</div><div class="value">N/A</div><div class="foot">Requires intrinsic value</div></div>
              <div class="intrinsic-kpi"><div class="label">DISCOUNT RATE / WACC</div><div class="value">N/A</div><div class="foot">Requires verified capital structure</div></div>
            </div>''', unsafe_allow_html=True)
            st.info("Financial coverage is incomplete. Open Forecast to inspect reported historical figures, or Data Sources & Methodology for missing inputs.")
        elif section == "Forecast":
            st.subheader("Financial Forecast")
            st.caption("A five-year FCFF forecast is withheld until the required inputs can be reconciled. Reported SEC historical data are shown below.")
            history = pd.DataFrame(sec_audit["rows"])
            display_cols = [c for c in ("Fiscal year end", "Revenue", "Revenue growth", "EBIT", "EBIT margin", "D&A verified", "CapEx", "Operating Cash Flow") if c in history.columns]
            if not history.empty:
                st.dataframe(history[display_cols], hide_index=True, use_container_width=True)
            else:
                st.info("No comparable SEC annual operating history available.")
        elif section == "Valuation":
            st.subheader("DCF Valuation Breakdown")
            st.caption("Enterprise value, equity value and price per share are not calculated from incomplete financial inputs.")
            st.dataframe(pd.DataFrame({"Metric": ["PV of Forecast FCFF", "PV of Terminal Value", "Enterprise Value", "Net Debt", "Equity Value", "Intrinsic / Share"], "Value": ["N/A — pending validation"] * 6}), hide_index=True, use_container_width=True)
        else:
            st.subheader("WACC × Terminal Growth Sensitivity")
            st.info("Sensitivity analysis will be available when a valid DCF valuation can be calculated.")
        with st.expander("Missing financial inputs and model eligibility", expanded=False):
            for issue in blockers:
                st.write("• " + issue)
        st.stop()
    last = sec_audit["rows"][-1]
    balance = sec_balances[-1]
    revenue = float(last["Revenue"])
    ultimo_anio = int(last["Fiscal year end"][:4])
    net_debt = float(balance["Net debt (cash-only)"])
    puente = {
        "net_debt": net_debt, "total_debt": float(balance["Total debt"]),
        "cash": float(balance["Cash"]), "short_term_investments": None,
        "balance_date": balance["Fiscal year end"], "source": "SEC 23B (cash-only bridge; leases included)",
        "long_term_investments": None, "finance_lease_liabilities": None,
    }
    st.warning("ILLUSTRATIVE FCFF · Cash-only net debt excludes unverified investments; NWC uses a partial AR + inventory − AP proxy; SEC common shares may not be fully diluted. Not a validated price target.")
else:
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
        st.error(f"Unable to validate SEC net debt: {error}")
        st.stop()

# ==========================================
# SIDEBAR — ASSUMPTIONS
# ==========================================

@st.cache_data(ttl=3600, show_spinner=False)
def cargar_escenarios_empresa(ticker):
    return generar_escenarios_empresa(ticker)

forecast_method = st.sidebar.radio(
    "Forecast Methodology",
    ["Historical Median", "Normalized Forecast"],
    key=f"forecast_method_{ticker}",
)
if new_company:
    medians = historical_23c["historical_medians"]
    required = {"Revenue growth": "growth", "EBIT margin": "ebit_margin",
                "D&A / Revenue": "da_ratio", "CapEx / Revenue": "capex_ratio"}
    for metric in required:
        if medians.get(metric) is None:
            st.error(f"Historical SEC assumption unavailable: {metric}")
            st.stop()
    base = {out: [float(medians[key])] * 5 for key, out in required.items()}

    if forecast_method == "Normalized Forecast":
        st.sidebar.caption(
            "Set year-five target ratios. Intrinsic gradually "
            "interpolates from historical medians to your targets."
        )

        targets = {}

        for label, metric in (
            ("EBIT Margin", "ebit_margin"),
            ("CapEx / Revenue", "capex_ratio"),
            ("D&A / Revenue", "da_ratio"),
        ):
            start = base[metric][0]

            target_pct = st.sidebar.number_input(
                f"Normalized Target · {label} (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(start * 100),
                step=0.5,
                key=f"normalized_{metric}_{ticker}",
            )

            targets[metric] = target_pct / 100

        for metric, target in targets.items():
            start = base[metric][0]

            base[metric] = [
                start + (target - start) * (i + 1) / 5
                for i in range(5)
            ]

    # Zero incremental NWC is a declared scenario assumption, NOT a measured fact.
    base["nwc_ratio"] = 0.0
    conservative = deepcopy(base)
    conservative["growth"] = [max(-0.5, g - 0.03) for g in base["growth"]]
    conservative["ebit_margin"] = [max(0.0, m - 0.02) for m in base["ebit_margin"]]
    optimistic = deepcopy(base)
    optimistic["growth"] = [min(1.0, g + 0.03) for g in base["growth"]]
    optimistic["ebit_margin"] = [min(1.0, m + 0.02) for m in base["ebit_margin"]]
    company_assumptions = {
        "scenarios": {"base": base, "conservative": conservative, "optimistic": optimistic},
        "historical_medians": {k: v for k, v in medians.items() if v is not None},
        "historical_years": {},
        "warnings": historical_23c["warnings"] + [
            "23C historical medians; per-year overrides remain editable.",
            "Incremental NWC defaults to ZERO as an explicit provisional assumption, not a verified fact."]}

else:
    try:
        with st.spinner("Calculating company-specific historical assumptions..."):
            company_assumptions = cargar_escenarios_empresa(ticker)
    except (ValueError, KeyError, TypeError) as error:
        st.error(f"Company-specific assumptions unavailable: {error}")
        st.stop()
if not new_company and forecast_method == "Normalized Forecast":
    base = deepcopy(company_assumptions["scenarios"]["base"])

    for label, metric in (
        ("EBIT Margin", "ebit_margin"),
        ("CapEx / Revenue", "capex_ratio"),
        ("D&A / Revenue", "da_ratio"),
    ):
        start = base[metric][0]

        target_pct = st.sidebar.number_input(
            f"Normalized Target · {label} (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(start * 100),
            step=0.5,
            key=f"normalized_{metric}_{ticker}",
        )

        target = target_pct / 100

        base[metric] = [
            start + (target - start) * (i + 1) / 5
            for i in range(5)
        ]

    conservative = deepcopy(base)
    conservative["growth"] = [
        max(-0.5, g - 0.03) for g in base["growth"]
    ]
    conservative["ebit_margin"] = [
        max(0.0, m - 0.02) for m in base["ebit_margin"]
    ]

    optimistic = deepcopy(base)
    optimistic["growth"] = [
        min(1.0, g + 0.03) for g in base["growth"]
    ]
    optimistic["ebit_margin"] = [
        min(1.0, m + 0.02) for m in base["ebit_margin"]
    ]

    company_assumptions["scenarios"] = {
        "base": base,
        "conservative": conservative,
        "optimistic": optimistic,
    }
st.sidebar.caption("Company-specific SEC historical ratios + illustrative scenario rules")
with st.sidebar.expander("Historical assumptions & methodology"):
    for metric, value in company_assumptions["historical_medians"].items():
        st.write(f"{metric}: {value:.2%} | FY {company_assumptions['historical_years'].get(metric, [])}")
    for warning in company_assumptions["warnings"]:
        st.caption(warning)

st.sidebar.title("Valuation Settings")
st.sidebar.caption("Customize projections and valuation inputs")

escenario = st.sidebar.selectbox(
    "Financial Scenario",
    ["base", "conservative", "optimistic", "custom"],
    format_func=lambda x: x.capitalize()
)
forecast_key = forecast_method.lower().replace(" ", "_")

if escenario == "custom":
    hipotesis = deepcopy(company_assumptions["scenarios"]["base"])
else:
    hipotesis = deepcopy(company_assumptions["scenarios"][escenario])

# Synchronize annual inputs when normalized targets change.
if forecast_method == "Normalized Forecast":
    target_signature = tuple(
        round(float(value), 8)
        for metric in ("ebit_margin", "capex_ratio", "da_ratio")
        for value in hipotesis[metric]
    )

    signature_key = f"normalized_signature_{ticker}_{escenario}"

    if st.session_state.get(signature_key) != target_signature:
        for i in range(5):
            year = ultimo_anio + i + 1

            for metric, prefix in (
                ("ebit_margin", "margin"),
                ("capex_ratio", "capex"),
                ("da_ratio", "da"),
            ):
                widget_key = (
                    f"{prefix}_{ticker}_{forecast_key}_{escenario}_{year}"
                )

                st.session_state[widget_key] = (
                    float(hipotesis[metric][i]) * 100
                )

        st.session_state[signature_key] = target_signature

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
                key=f"growth_{ticker}_{forecast_key}_{escenario}_{year}"
            ) / 100
        )

        hipotesis["ebit_margin"][i] = (
            st.number_input(
                "EBIT Margin (%)",
                min_value=0.0,
                max_value=100.0,
                value=hipotesis["ebit_margin"][i] * 100,
                step=0.5,
               key=f"margin_{ticker}_{forecast_key}_{escenario}_{year}"
            ) / 100
        )

        hipotesis["capex_ratio"][i] = (
            st.number_input(
                "CapEx / Revenue (%)",
                min_value=0.0,
                max_value=100.0,
                value=hipotesis["capex_ratio"][i] * 100,
                step=0.5,
                key=f"capex_{ticker}_{forecast_key}_{escenario}_{year}"
            ) / 100
        )

        hipotesis["da_ratio"][i] = (
            st.number_input(
                "D&A / Revenue (%)",
                min_value=0.0,
                max_value=100.0,
                value=hipotesis["da_ratio"][i] * 100,
                step=0.5,
                key=f"da_{ticker}_{forecast_key}_{escenario}_{year}"
            ) / 100
        )

hipotesis["nwc_ratio"] = (
    st.sidebar.number_input(
        "Delta NWC / Delta Revenue (%)",
        min_value=-99.0,
        max_value=99.0,
        value=hipotesis["nwc_ratio"] * 100,
        step=0.5,
        key=f"nwc_{ticker}_{forecast_key}_{escenario}",
    ) / 100
)

st.sidebar.divider()
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
        value=int(market_reference["shares_outstanding"]) if market_reference else (int(balance["Shares outstanding"]) if new_company else 1_000_000_000),
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

try:
    forecast = proyectar_escenario(
        revenue,
        ultimo_anio,
        hipotesis,
        tax_rate=tax_rate,
    )

    if new_company:
        # Feed the exact five editable annual projections into 23E, retaining
        # the dashboard's original forecast and sensitivity presentation.
        dcf_input = {"company": ticker, "rows": [
            {"Year": str(row["year"]), "FCFF": row["fcff"]} for row in forecast
        ], "warnings": ["Provisional working capital assumption; historical 23C medians are descriptive."]}
        model_23e = value_fcff_23e(
            dcf_input, wacc=wacc, terminal_growth=terminal_growth,
            net_debt=net_debt, shares_outstanding=shares_outstanding,
            balance_date=puente["balance_date"],
            shares_date=balance["Shares measurement date"],
            market_price=market_price, working_capital_validated=False)
        valuation = {
            "pv_fcff": model_23e["pv_fcff"],
            "pv_terminal": model_23e["pv_terminal_value"],
            "terminal_value": model_23e["terminal_value"],
            "enterprise_value": model_23e["enterprise_value"],
            "equity_value": model_23e["equity_value"],
            "intrinsic_price": model_23e["intrinsic_value_per_share"],
        }
    else:
        valuation = calcular_dcf(
            forecast, wacc, terminal_growth, net_debt, shares_outstanding
        )

except ValueError as error:
    st.error(f"Invalid assumptions: {error}")
    st.stop()

intrinsic_price = valuation["intrinsic_price"]
if new_company:
    with st.expander("23F · Model limitations and valuation warnings", expanded=False):
        st.caption("SCENARIO ONLY — not an independently validated price target.")
        for warning in model_23e["warnings"]:
            st.warning(warning)

upside = calcular_upside(intrinsic_price, market_price)

# ==========================================
# DASHBOARD NAVIGATION
# ==========================================

# Display-only glossary: does not touch financial engines or Streamlit state.
def _help(term, explanation):
    from html import escape
    return (f'<span class="intrinsic-help" tabindex="0" role="note" aria-label="{escape(term)}: {escape(explanation)}">'
            f'?<span class="intrinsic-tip" role="tooltip">{escape(explanation)}</span></span>')


def _glossary(items):
    html = '<div class="intrinsic-glossary">' + ''.join(
        f'<span class="intrinsic-glossary-item">{term}{_help(term, definition)}</span>'
        for term, definition in items
    ) + '</div>'
    st.markdown(html, unsafe_allow_html=True)


section = st.segmented_control(
    "Dashboard section",
    options=["Overview", "Forecast", "Valuation", "Sensitivity"],
    default="Overview",
    key="intrinsic_section",
    label_visibility="collapsed",
)

if section == "Overview":
    # ==========================================
    # MAIN KPIs
    # ==========================================

    st.markdown('<div class="intrinsic-section-label">01 / VALUATION SNAPSHOT</div>', unsafe_allow_html=True)
    st.markdown('<div class="intrinsic-dashboard-heading">Valuation at a glance</div>', unsafe_allow_html=True)
    st.markdown('<div class="intrinsic-dashboard-sub">Five-year cash flow forecast · selected financial scenario</div>', unsafe_allow_html=True)

    upside_class = "positive" if upside >= 0 else "negative"
    upside_caption = "Model upside" if upside >= 0 else "Model downside"
    st.markdown(f"""
    <div class="intrinsic-kpi-grid">
      <div class="intrinsic-kpi primary"><div class="label">INTRINSIC VALUE / SHARE {_help("Intrinsic value", "Estimated fair value per share from discounted projected free cash flows and terminal value, adjusted for net debt.")}</div><div class="value">${intrinsic_price:,.2f}</div><div class="foot">Discounted cash flow estimate</div></div>
      <div class="intrinsic-kpi"><div class="label">MARKET PRICE / SHARE {_help("Market price", "Selected share-price reference used to compare the model estimate with the market; it may not be a live quote.")}</div><div class="value">${market_price:,.2f}</div><div class="foot">Selected market reference</div></div>
      <div class="intrinsic-kpi"><div class="label">UPSIDE / DOWNSIDE {_help("Upside / downside", "Percentage difference between intrinsic value per share and the selected market price: (intrinsic / market − 1) × 100.")}</div><div class="value {upside_class}">{upside:+.2f}%</div><div class="foot">{upside_caption} · illustrative</div></div>
      <div class="intrinsic-kpi"><div class="label">DISCOUNT RATE / WACC {_help("WACC", "Weighted average cost of capital: the selected discount rate used to value future free cash flows, reflecting equity and debt financing costs.")}</div><div class="value">{wacc*100:.2f}%</div><div class="foot">Selected capital cost assumptions</div></div>
    </div>""", unsafe_allow_html=True)

    comparison_percent = max(0, min(100, 100 * intrinsic_price / market_price)) if intrinsic_price >= 0 else 0
    st.markdown(f"""
    <div class="intrinsic-comparison">
      <div class="top"><strong>Intrinsic value vs. market reference</strong><span>${intrinsic_price:,.2f} / ${market_price:,.2f}</span></div>
      <div class="track"><div class="fill" style="width:{comparison_percent:.2f}%"></div></div>
      <div class="note">Bar shows intrinsic value as a percentage of market price, capped at 100% for display. Exact comparison is shown above.</div>
    </div>""", unsafe_allow_html=True)

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
        st.write(f"SEC {'cash-only net debt' if new_company else 'net debt'}: ${net_debt / 1e9:,.2f} B")
        st.write(f"Shares outstanding: {shares_outstanding:,.0f}")
        st.write(f"SEC balance date: {puente['balance_date']}")


if section == "Forecast":
    # ==========================================
    # FINANCIAL FORECAST
    # ==========================================

    st.subheader("Financial Forecast")
    _glossary([
        ("Revenue growth", "Expected annual change in company sales under the selected scenario."),
        ("EBIT", "Earnings before interest and taxes; operating profit before financing costs."),
        ("NOPAT", "Net operating profit after estimated operating taxes."),
        ("D&A", "Depreciation and amortization added back to operating cash flow. Some company data may use a disclosed proxy."),
        ("CapEx", "Capital expenditures: cash investment in long-lived operating assets."),
        ("Change in NWC", "Change in modeled net working capital. The GOOGL case uses an AR–AP proxy, not full operating NWC."),
        ("FCFF", "Free cash flow to the firm: NOPAT + D&A − CapEx − change in NWC."),
    ])
    st.caption("Five-year operating projections based on the selected scenario")

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

if section == "Valuation":
    # ==========================================
    # VALUATION SUMMARY
    # ==========================================

    st.subheader("DCF Valuation Breakdown")
    _glossary([
        ("PV of FCFF", "Present value of projected free cash flows discounted at WACC."),
        ("Terminal value", "Estimated value of cash flows beyond the explicit five-year forecast."),
        ("Enterprise value", "Total modeled operating business value before the equity bridge."),
        ("Net debt", "Debt less cash and relevant liquid investments as represented in the selected SEC bridge; accounting classifications may require review."),
        ("Equity value", "Enterprise value adjusted for net debt and any selected bridge items."),
        ("Intrinsic / share", "Modeled equity value divided by shares outstanding."),
    ])
    st.caption("Present value of forecast cash flows and terminal value")

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
            min_value=-99.0,
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
            "Investments (excluded / unknown)" if new_company else "Short-Term Investments",
            "Equity Value",
        ],
        "USD Billions": [
            valuation["enterprise_value"] / 1e9,
            -puente["total_debt"] / 1e9,
            puente["cash"] / 1e9,
            (0 if new_company else puente["short_term_investments"]) / 1e9,
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
        + ("Net debt = Debt - Cash (investments excluded / unknown). " if new_company else "Net debt = Debt - Cash - Short-Term Investments. ")
        + "Other potential EV-to-equity adjustments "
        "have not yet been validated."
    )

if section == "Sensitivity":
    # ==========================================
    # SENSITIVITY MATRIX
    # ==========================================

    st.subheader("WACC × Terminal Growth Sensitivity")
    _glossary([
        ("WACC", "Discount rate applied to future cash flows. A higher WACC generally lowers modeled value."),
        ("Terminal growth", "Perpetual cash-flow growth assumption after the explicit forecast; it must remain below WACC for the standard perpetuity formula."),
        ("Sensitivity matrix", "Scenario table showing how intrinsic price per share changes as WACC and terminal growth vary; not a probability forecast."),
    ])
    st.caption("Illustrative intrinsic price across discount rates and perpetual growth assumptions")

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

    # Build the export from the sensitivity results defined in this section.
    # df_display belongs to Forecast and is not available when Sensitivity is selected.
    sensitivity_export = pd.DataFrame(
        matrix,
        index=[f"{w * 100:.2f}%" for w in wacc_values],
        columns=[f"{g * 100:.2f}%" for g in growth_values],
    )
    sensitivity_export.index.name = "WACC / Terminal Growth"
    csv_data = sensitivity_export.to_csv()

    st.download_button(
        "Download Sensitivity CSV",
        data=csv_data,
        file_name=f"intrinsic_{ticker.lower()}_sensitivity.csv",
        mime="text/csv",
    )

    st.caption(
        "Intrinsic MVP | Data: SEC EDGAR | "
        "Illustrative assumptions | "
        "Market reference: Yahoo Finance or manual | "
        "Valuation not validated"
    )


