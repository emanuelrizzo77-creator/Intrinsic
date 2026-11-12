# INTRINSIC — Streamlit dashboard (entry point).
# Presentation and user inputs only; the valuation engine lives in driver_forecast_27.py
# and the discount-rate inputs in wacc_data.py / market_inputs_27.py.

from html import escape as html_escape

import streamlit as st

from company_explorer_21a import fetch_sec_directory
from dashboard_27_panel import render_model_27
from industry_beta_27 import bottom_up_beta, load_industry_betas
from market_inputs_27 import (risk_free_rate as _live_risk_free_rate, equity_risk_premium as equity_risk_premium_default,
                              marginal_tax_rate, cost_of_debt as synthetic_cost_of_debt)
from universal_valuation_21c import classify_sic
from valuation_bridge import obtener_referencia_mercado
from wacc_calculator import calculate_wacc
from wacc_data import obtener_datos_wacc

MANUAL_WACC_DEFAULT = 0.09      # starting value for the manual override only
TERMINAL_GROWTH = 0.025         # long-run nominal growth; editable in the sidebar

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
def cargar_tasa_libre_riesgo():
    return _live_risk_free_rate()
@st.cache_data(ttl=900, show_spinner=False)
def cargar_referencia_mercado(ticker):
    return obtener_referencia_mercado(ticker)

st.markdown("""
<style>
/* INTRINSIC — light research workspace. Presentation only; no financial logic here. */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Instrument+Serif&display=swap');
:root {
  --ink:#18181B; --muted:#71717A; --faint:#A1A1AA; --line:#E7E7EC; --soft:#F5F5F8;
  --card:#FFFFFF; --accent:#4F46E5; --accent-soft:#EEF0FF; --pos:#16A34A; --pos-soft:#EAF7EE;
  --neg:#DC2626; --neg-soft:#FDECEC; --warn:#B45309;
}
html, body, [class*="css"] { font-feature-settings: "tnum" 1, "cv11" 1; }
.block-container { max-width: 1320px; padding-top: 3.6rem; padding-bottom: 3rem; }
[data-testid="stHeader"] { background: rgba(255,255,255,.85); backdrop-filter: blur(6px); }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: .4rem; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { font-size: .78rem; text-transform: uppercase;
  letter-spacing: .08em; color: var(--muted); font-weight: 600; margin: .4rem 0 .2rem; }
[data-testid="stSidebar"] [data-testid="stExpander"] { background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; box-shadow: none; }
[data-testid="stSidebar"] [data-testid="stExpander"] summary p { font-weight: 600; font-size: .9rem; }
[data-testid="stExpander"] { border-radius: 12px; }
[data-testid="stAlert"] { border-radius: 12px; }
hr { margin: .9rem 0 !important; }

/* Brand */
.ix-brand { display:flex; align-items:center; gap:10px; padding: 4px 2px 14px; }
.ix-logo { width:30px; height:30px; border-radius:9px; background: var(--ink); color:#fff; display:flex;
  align-items:center; justify-content:center; font: 700 16px/1 Georgia, 'Times New Roman', serif; }
.ix-brand b { display:block; font-size: .95rem; letter-spacing: .02em; color: var(--ink); }
.ix-brand span { display:block; font-size: .74rem; color: var(--muted); }

/* Sidebar key/value list (replaces oversized metric cards) */
.ix-kv { display:flex; justify-content:space-between; gap:12px; padding: 7px 0; border-bottom: 1px dashed var(--line);
  font-size: .84rem; }
.ix-kv:last-child { border-bottom: 0; }
.ix-kv span { color: var(--muted); } .ix-kv b { color: var(--ink); font-weight: 600; text-align: right; }
.ix-kv.total { border-top: 1px solid var(--line); border-bottom: 0; margin-top: 4px; padding-top: 9px; }
.ix-kv.total b { color: var(--accent); font-size: .95rem; }

/* Page header */
.ix-header { display:flex; align-items:flex-end; justify-content:space-between; gap: 16px; margin: 0 0 6px; }
.ix-crumb { font-size: .8rem; color: var(--muted); margin-bottom: 6px; }
.ix-crumb b { color: var(--ink); font-weight: 500; }
.ix-title { display:flex; align-items:center; gap: 12px; flex-wrap: wrap; }
.ix-title h1 { font-size: 1.9rem; line-height: 1.15; margin: 0; padding: 0; letter-spacing: -.02em; font-weight: 700; }
.ix-chip { display:inline-flex; align-items:center; gap:6px; border:1px solid var(--line); background: var(--soft);
  color: var(--ink); border-radius: 999px; padding: 3px 10px; font-size: .76rem; font-weight: 600; }
.ix-chip.accent { background: var(--accent-soft); border-color: #DADDFE; color: var(--accent); }
.ix-sub { color: var(--muted); font-size: .86rem; margin: 6px 0 18px; }

/* Section headings inside the workspace */
.intrinsic-section-label { font-size: .72rem; letter-spacing: .08em; color: var(--muted); font-weight: 600;
  text-transform: uppercase; margin: 6px 0 4px; }
.intrinsic-dashboard-heading { font-size: 1.15rem; color: var(--ink); font-weight: 650; margin: 0 0 2px; }
.intrinsic-dashboard-sub { color: var(--muted); font-size: .84rem; margin: 0 0 14px; }

/* KPI cards */
.intrinsic-kpi-grid { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 14px; margin: 4px 0 18px; }
.intrinsic-kpi { position:relative; background: var(--soft); border: 1px solid var(--line); border-radius: 14px;
  padding: 16px 18px 15px; min-height: 118px; overflow: visible; }
.intrinsic-kpi.primary { background: var(--card); border-color: #D9DCFB; box-shadow: 0 1px 2px rgba(24,24,27,.04),
  0 0 0 3px var(--accent-soft); }
.intrinsic-kpi .label { display:flex; align-items:center; gap:7px; font-size: .8rem; color: var(--muted);
  font-weight: 500; margin-bottom: 12px; text-transform: none; letter-spacing: 0; }
.intrinsic-kpi .value { font-size: 1.75rem; line-height: 1.1; color: var(--ink); font-weight: 650; letter-spacing: -.02em; }
.intrinsic-kpi .foot { font-size: .76rem; color: var(--faint); margin-top: 10px; }
.intrinsic-kpi .value.positive, .intrinsic-kpi .value.negative { display:inline-flex; align-items:center; gap:6px; }
.intrinsic-kpi .positive { color: var(--pos); } .intrinsic-kpi .negative { color: var(--neg); }
.ix-pill { display:inline-block; font-size: .74rem; font-weight: 600; padding: 2px 8px; border-radius: 999px; margin-left: 6px;
  vertical-align: middle; }
.ix-pill.pos { background: var(--pos-soft); color: var(--pos); } .ix-pill.neg { background: var(--neg-soft); color: var(--neg); }
@media(max-width:1050px){ .intrinsic-kpi-grid{ grid-template-columns: repeat(2,minmax(0,1fr)); } }
@media(max-width:600px){ .intrinsic-kpi-grid{ grid-template-columns: 1fr; } .ix-title h1{ font-size: 1.5rem; } }

/* Insight / verdict card */
.intrinsic-insight { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px;
  margin: 14px 0 18px; line-height: 1.6; color: #3F3F46; font-size: .9rem; }
.intrinsic-insight-title { color: var(--ink); font-size: .9rem; font-weight: 650; margin-bottom: 8px; letter-spacing: 0; }
.intrinsic-insight strong { color: var(--ink); font-weight: 600; }
.ix-verdict { display:flex; gap: 12px; align-items:flex-start; padding: 12px 14px; border-radius: 12px; margin-bottom: 10px; }
.ix-verdict.above { background: var(--neg-soft); } .ix-verdict.below { background: var(--pos-soft); } .ix-verdict.inside { background: var(--accent-soft); }

/* Bordered containers act as cards */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }

/* Section navigation: underline tabs, like a product UI */
[data-testid="stSegmentedControl"] { margin: 2px 0 18px; }
[data-testid="stSegmentedControl"] [role="radiogroup"], [data-testid="stSegmentedControl"] > div {
  gap: 4px; }
[data-testid="stSegmentedControl"] button { border-radius: 9px !important; font-weight: 500; }

/* "?" tooltips */
.intrinsic-help { position:relative; display:inline-flex; align-items:center; justify-content:center; width:16px; height:16px;
  flex:none; border:1px solid #D4D4D8; border-radius:50%; font: 600 10px/1 Inter, system-ui, sans-serif; color: var(--faint);
  cursor: help; background: #fff; }
.intrinsic-help:hover, .intrinsic-help:focus-visible { border-color: var(--accent); color: var(--accent); }
.intrinsic-help .intrinsic-tip { pointer-events:none; position:absolute; bottom: calc(100% + 10px); left: 50%;
  transform: translate(-50%,4px); width:max-content; max-width: min(300px,75vw); min-width: 210px; white-space: normal;
  text-align:left; line-height:1.5; font-size: 12px; font-weight: 400; color: #F4F4F5; background: #18181B; border-radius: 10px;
  padding: 10px 12px; box-shadow: 0 10px 30px rgba(0,0,0,.18); opacity:0; visibility:hidden;
  transition: opacity .15s ease, transform .15s ease, visibility .15s; z-index: 1000; }
.intrinsic-help:hover .intrinsic-tip, .intrinsic-help:focus-visible .intrinsic-tip { opacity:1; visibility:visible; transform: translate(-50%,0); }
.intrinsic-kpi:first-child .intrinsic-tip { left:0; transform: translate(0,4px); }
.intrinsic-kpi:first-child .intrinsic-help:hover .intrinsic-tip, .intrinsic-kpi:first-child .intrinsic-help:focus-visible .intrinsic-tip { transform: translate(0,0); }
.intrinsic-kpi:last-child .intrinsic-tip { left:auto; right:0; transform: translate(0,4px); }
.intrinsic-kpi:last-child .intrinsic-help:hover .intrinsic-tip, .intrinsic-kpi:last-child .intrinsic-help:focus-visible .intrinsic-tip { transform: translate(0,0); }
.intrinsic-glossary { display:flex; flex-wrap:wrap; gap:6px; margin: 2px 0 14px; }
.intrinsic-glossary-item { display:inline-flex; align-items:center; gap:6px; background: var(--soft); border:1px solid var(--line);
  border-radius: 999px; padding: 4px 10px; color: #52525B; font-size: .76rem; }
.ix-footer { color: var(--faint); font-size: .76rem; margin-top: 28px; padding-top: 14px; border-top: 1px solid var(--line); }
@media(prefers-reduced-motion:reduce){ .intrinsic-help .intrinsic-tip{ transition:none; } }

/* Opening sequence — once per session, CSS only, never delays the calculations underneath. */
.ix-logo { font: 400 21px/1 'Instrument Serif', Georgia, serif !important; padding-top: 2px; }
.ix-intro { position: fixed; inset: 0; z-index: 2147483000; display:flex; align-items:center; justify-content:center;
  background: radial-gradient(900px 520px at 50% 46%, #F4F4FF 0%, #FFFFFF 62%);
  animation: ixCurtain 3.6s cubic-bezier(.7,0,.2,1) forwards; }
.ix-intro-inner { display:flex; flex-direction:column; align-items:center; }
.ix-intro-mark { font: 400 clamp(120px,15vw,184px)/.86 'Instrument Serif', Georgia, 'Times New Roman', serif; color: #18181B;
  animation: ixMark 1.25s cubic-bezier(.2,.7,.2,1) .2s both; user-select:none; }
.ix-intro-rule { width: 128px; height: 1px; background: #4F46E5; margin: 26px 0 20px; transform-origin: center;
  animation: ixRule .85s cubic-bezier(.7,0,.2,1) 1.05s both; }
.ix-intro-word { position: relative; font: 600 14px/1 Inter, -apple-system, sans-serif; letter-spacing: .62em;
  padding-left: .62em; color: #18181B; white-space: nowrap; clip-path: inset(0 100% 0 0);
  animation: ixType 1.05s steps(9, end) 1.6s forwards; }
.ix-intro-word::after { content:""; position:absolute; top:-3px; bottom:-3px; left:0; width:1.5px; background:#4F46E5;
  animation: ixCaret 1.05s steps(9, end) 1.6s forwards, ixCaretOut .2s linear 2.75s forwards; }
.ix-intro-tag { margin-top: 16px; font: 400 12px/1 Inter, sans-serif; letter-spacing: .14em; color: #A1A1AA;
  text-transform: uppercase; opacity: 0; animation: ixFade .7s ease 2.55s forwards; }
@keyframes ixCurtain { 0%,82% { opacity:1; transform: translateY(0); visibility: visible; }
  100% { opacity:0; transform: translateY(-1.5%); visibility: hidden; pointer-events: none; } }
@keyframes ixMark { from { opacity:0; transform: translateY(16px) scale(.98); filter: blur(10px); }
  to { opacity:1; transform: none; filter: blur(0); } }
@keyframes ixRule { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes ixType { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
@keyframes ixCaret { from { left: 0; } to { left: 100%; } }
@keyframes ixCaretOut { to { opacity: 0; } }
@keyframes ixFade { to { opacity: 1; } }
@keyframes ixRise { from { opacity:0; transform: translateY(10px); } to { opacity:1; transform:none; } }
@keyframes ixPop { from { opacity:0; transform: scale(.82); } to { opacity:1; transform:none; } }
/* Brand in the sidebar types itself after the curtain lifts (first load only). */
.ix-brand b.animate { position: relative; width: max-content; clip-path: inset(0 100% 0 0);
  animation: ixType .75s steps(9, end) 3.45s forwards; }
.ix-brand b.animate::after { content:""; position:absolute; top:1px; bottom:1px; left:0; width:1.5px; background: var(--accent);
  animation: ixCaret .75s steps(9, end) 3.45s forwards, ixCaretOut .2s linear 4.35s forwards; }
.ix-brand span.animate { opacity:0; animation: ixFade .6s ease 4.1s forwards; }
.ix-logo.animate { animation: ixPop .6s cubic-bezier(.2,.8,.2,1.2) 3.15s both; }
@media(prefers-reduced-motion:reduce){
  .ix-intro{ display:none !important; }
  .ix-brand .animate, .ix-brand .animate::after, .ix-entrance{ animation:none !important; clip-path:none !important; opacity:1 !important; }
  .ix-brand b.animate::after{ display:none; } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# HISTORICAL DATA
# ==========================================


# Initial Top 25 candidate universe.
# Membership is a curated selection, not a live market-cap ranking.
TOP_25 = {
    "MSFT": "Microsoft Corporation",
    "AAPL": "Apple Inc.",
    "NVDA": "NVIDIA Corporation",
    "GOOGL": "Alphabet Inc.",
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
# Opening sequence: only on the first run of a browser session.
_show_intro = not st.session_state.get("intrinsic_intro_seen", False)
st.session_state["intrinsic_intro_seen"] = True
_anim = " animate" if _show_intro else ""
if _show_intro:
    st.markdown(
        '<div class="ix-intro" aria-hidden="true"><div class="ix-intro-inner">'
        '<div class="ix-intro-mark">I</div><div class="ix-intro-rule"></div>'
        '<div class="ix-intro-word">INTRINSIC</div><div class="ix-intro-tag">Equity valuation</div>'
        '</div></div>'
        '<style>@media(prefers-reduced-motion:no-preference){'
        '.block-container [data-testid="stElementContainer"]:not(:has(.ix-intro)),'
        '.block-container [data-testid="stHorizontalBlock"]'
        '{animation:ixRise .9s cubic-bezier(.2,.7,.2,1) 3.0s both}}</style>',
        unsafe_allow_html=True,
    )
st.sidebar.markdown(
    f'<div class="ix-brand"><div class="ix-logo{_anim}">I</div><div><b class="{_anim.strip()}">Intrinsic</b>'
    f'<span class="{_anim.strip()}">Equity valuation workspace</span></div></div>', unsafe_allow_html=True)
st.sidebar.subheader("Company")
selection_mode = st.sidebar.radio(
    "Company source",
    ["Top 25 companies", "SEC company search"],
    key="m22_source",
    horizontal=True,
    label_visibility="collapsed",
)
new_company = selection_mode == "SEC company search"
selected_cik = None
if not new_company:
    ticker = st.sidebar.selectbox(
        "Selected company",
        list(TOP_25),
        format_func=lambda symbol: f"{TOP_25[symbol]} ({symbol})",
        key="selected_company_ticker",
    )
    company_name = TOP_25[ticker]
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
    st.sidebar.caption(f"SEC CIK: {selected_cik:010d}")

# Do not silently value Alphabet using Microsoft assumptions.
st.markdown(
    f"""<div class="ix-header"><div>
      <div class="ix-crumb">Valuation &nbsp;›&nbsp; <b>{html_escape(company_name)}</b></div>
      <div class="ix-title"><h1>{html_escape(company_name)}</h1>
        <span class="ix-chip accent">{html_escape(ticker)}</span>
        <span class="ix-chip">DCF · FCFF</span></div>
    </div></div>
    <div class="ix-sub">10-year free cash flow valuation from SEC filings and market data ·
      research tool, not investment advice</div>""", unsafe_allow_html=True,
)

# Route by SEC industry BEFORE any market or WACC work: FCFF does not apply to
# banks, insurers, REITs or holding companies, and failing later looks like a bug.
@st.cache_data(ttl=86400, show_spinner=False)
def cargar_clasificacion(ticker, cik=None):
    from run_driver_27 import lookup_cik
    from sec_annual_27 import submissions_cached
    if cik is None:
        try:
            cik, _ = lookup_cik(ticker)
        except SystemExit:
            return None
    profile = submissions_cached(int(cik))
    decision = classify_sic(profile.get("sic"))
    return {"model": decision.model, "category": decision.category, "reason": decision.reason,
            "sic": profile.get("sic"), "sic_description": profile.get("sicDescription")}

try:
    _route = cargar_clasificacion(ticker, selected_cik)
except Exception:
    _route = None          # classification unavailable: let the model's own checks decide
if _route and _route["model"] != "fcff":
    _why = {
        "bank_equity": "Banks earn money on their balance sheet: debt is raw material, not financing, so "
                       "free cash flow to the firm and WACC are not meaningful. They need an equity-based "
                       "model (dividend or excess-return) with regulatory capital.",
        "insurance_equity": "Insurers invest premiums before paying claims; cash flow depends on reserves and "
                            "regulatory capital, which an FCFF model does not capture.",
        "reit_affo": "REITs are valued on funds from operations (FFO/AFFO) or net asset value.",
        "holding_sotp": "Holding and investment companies are valued as the sum of their parts.",
    }.get(_route["model"], _route["reason"])
    st.markdown(
        f'''<div class="intrinsic-insight"><div class="intrinsic-insight-title">Outside the scope of this model</div>
        <div class="ix-verdict inside"><div><strong>{html_escape(_route["category"])}</strong> ·
        SEC SIC {html_escape(str(_route["sic"]))} ({html_escape(str(_route["sic_description"] or ""))})</div></div>
        {html_escape(_why)}<br><br>Intrinsic values non-financial operating companies with a free-cash-flow-to-the-firm
        model. Rather than force a number that would look precise but be wrong, this company is not valued.
        A sector-specific engine for financial companies is on the roadmap.</div>''',
        unsafe_allow_html=True,
    )
    st.stop()

# Model 27 is the single forecasting engine; it loads and audits its own SEC inputs.

st.sidebar.subheader("Assumptions")
wacc_box = st.sidebar.expander("Discount rate (WACC)", expanded=False)


# ==========================================
# DYNAMIC WACC SETTINGS
# ==========================================

wacc_mode = wacc_box.radio(
    "WACC Calculation Mode",
    ["Automatic Calculation", "Manual Override"],
    key=f"wacc_mode_{ticker}",
)

if new_company:
    wacc_box.caption(
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

    wacc_box.caption(f"Market data {str(datos_wacc['market_date'])[:10]} · SEC debt balance {datos_wacc['debt_date']}")

    # ==========================================
    # EDITABLE FINANCIAL ASSUMPTIONS
    # ==========================================

    _rf_default, _rf_source = cargar_tasa_libre_riesgo()
    risk_free_rate = wacc_box.number_input(
        "Risk-free rate (%)",
        min_value=0.0,
        max_value=20.0,
        value=round(_rf_default * 100, 2),
        step=0.05,
        key="wacc_risk_free",
        help=_rf_source,
    ) / 100

    _bu = datos_wacc.get("beta_bottom_up") or {}
    _blume = datos_wacc.get("beta_adjusted", datos_wacc["beta"])
    _REGRESSION = "Stock regression (Blume-adjusted)"
    _industries = [name for name in load_industry_betas() if not name.startswith("Total Market (")]
    _auto = _bu.get("industry")
    _choices = _industries + [_REGRESSION]
    beta_basis = wacc_box.selectbox(
        "Beta basis (industry)",
        _choices,
        index=_choices.index(_auto) if _auto in _choices else len(_choices) - 1,
        key=f"wacc_beta_industry_{ticker}",
        help=(f"Matched automatically from SEC SIC {_bu['sic']} ({_bu['match']} match). " if _auto else
              f"No industry match ({_bu.get('reason', 'no SIC')}). ")
             + "Change it when the company's main risk sits in another business (one SIC code "
               "cannot describe a multi-segment company).",
    )
    if beta_basis != _REGRESSION:
        _bu = bottom_up_beta(_bu.get("sic"), market_equity=datos_wacc["market_equity"],
                             total_debt=datos_wacc["total_debt"],
                             industry=None if beta_basis == _auto else beta_basis)
    if beta_basis != _REGRESSION and _bu.get("beta") is not None:
        _beta_default = _bu["beta"]
        _beta_help = (
            f"Industry (bottom-up) beta: {_bu['industry']} unlevered beta {_bu['unlevered_beta']:.2f} "
            f"(cash-corrected, {_bu['n_firms']} US firms; Damodaran, Jan 2026), relevered with this company's "
            f"debt / market equity of {_bu['de_ratio']:.0%} at a {_bu['tax']:.0%} marginal tax rate. "
            f"For comparison: Yahoo regression beta {datos_wacc['beta']:.2f}, Blume-adjusted {_blume:.2f}. "
            "Industry averages are far less noisy than one stock's regression. Type another value to override."
        )
    else:
        _beta_default = _blume
        _beta_help = (f"Yahoo regression beta {datos_wacc['beta']:.2f} with the Blume adjustment "
                      "(0.67 × raw + 0.33). Single-stock betas are noisy. Type another value to override.")
    beta = wacc_box.number_input(
        "Beta (levered)",
        min_value=0.0,
        max_value=5.0,
        value=float(_beta_default),
        step=0.05,
        key=f"wacc_beta_{ticker}_{beta_basis}",
        help=_beta_help,
    )
    if beta_basis != _REGRESSION and _bu.get("beta") is not None:
        _warn = []
        if _bu["match"] == "broad":
            _warn.append("broad SIC match, check the industry")
        if _bu.get("small_industry"):
            _warn.append(f"only {_bu['n_firms']} firms in industry")
        wacc_box.caption("Beta source: industry · " + " · ".join([_bu["industry"]] + _warn))
    else:
        wacc_box.caption("Beta source: stock regression (Blume)")

    _erp_default, _erp_source = equity_risk_premium_default()
    equity_risk_premium = wacc_box.number_input(
        "Equity risk premium (%)",
        min_value=0.0,
        max_value=20.0,
        value=round(_erp_default * 100, 2),
        step=0.05,
        key="wacc_erp",
        help=_erp_source + ". The premium investors demand over Treasuries for the US market as a whole.",
    ) / 100

    
    historical_kd = datos_wacc.get("historical_kd")
    _cov = datos_wacc.get("interest_coverage")
    _kd, kd_source = synthetic_cost_of_debt(
        risk_free_rate, _cov["coverage"] if _cov else None,
        f", FY ending {_cov['fiscal_end']}" if _cov else "")
    if _kd is None:
        _kd = risk_free_rate + 0.0111
        kd_source = ("Assumption: risk-free + 1.11% (BBB default spread, Damodaran Jan 2026) because SEC "
                     "filings do not tag interest expense for this company. Edit if you know its rating.")
    if historical_kd is not None:
        kd_source += (f". For comparison, historical interest / average debt was "
                      f"{historical_kd['cost_of_debt']:.2%} (FY {historical_kd['fiscal_end']}), which reflects "
                      "older coupons rather than today's borrowing cost.")

    cost_of_debt = wacc_box.number_input(
        "Pre-tax cost of debt (%)",
        value=round(_kd * 100, 2),
        min_value=0.0,
        max_value=30.0,
        step=0.05,
        key=f"wacc_cost_debt_{ticker}_{round(risk_free_rate, 4)}",
        help=kd_source,
    ) / 100
    wacc_box.caption("Cost of debt: " + ("synthetic rating from interest coverage" if _cov else
                                         "assumed BBB spread · interest coverage unavailable"))

    _tax_default, _tax_source = marginal_tax_rate()
    tax_rate = wacc_box.number_input(
        "Marginal tax rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=round(_tax_default * 100, 2),
        step=0.5,
        key=f"wacc_tax_rate_{ticker}",
        help=_tax_source + ". Used for the debt tax shield; matches the long-run tax rate in the forecast.",
    ) / 100

    # ==========================================
    # AUTOMATIC CAPITAL STRUCTURE
    # ==========================================

    market_equity = datos_wacc["market_equity"]
    total_debt = datos_wacc["total_debt"]


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

    wacc_box.markdown(
        f'<div class="ix-kv"><span>Market capitalization</span><b>${market_equity / 1e9:,.1f} B</b></div>'
        f'<div class="ix-kv"><span>Total debt</span><b>${total_debt / 1e9:,.1f} B</b></div>'
        f'<div class="ix-kv"><span>Cost of equity</span><b>{(risk_free_rate + beta * equity_risk_premium) * 100:.2f}%</b></div>'
        f'<div class="ix-kv total"><span>WACC</span><b>{wacc * 100:.2f}%</b></div>',
        unsafe_allow_html=True,
    )

    wacc_box.caption(
        "Every input shows its source under the ? icon and stays editable. "
        "Defaults: live 10-year Treasury, Damodaran implied ERP and industry beta, "
        "synthetic-rating cost of debt, 25% marginal tax."
    )

else:
    wacc = wacc_box.number_input(
        "Manual WACC (%)",
        min_value=1.0,
        max_value=30.0,
        value=MANUAL_WACC_DEFAULT * 100,
        step=0.25,
        key=f"manual_wacc_{ticker}"
    ) / 100

# ==========================================
# MARKET REFERENCE — AUTOMATIC OR MANUAL
# ==========================================
mkt_box = st.sidebar.expander("Market price & shares", expanded=False)
reference_mode = mkt_box.radio(
    "Market Data Mode",
    ["Automatic", "Manual Override"],
    key="market_reference_mode",
    horizontal=True,
)

try:
    with st.spinner("Loading market reference..."):
        market_reference = cargar_referencia_mercado(ticker)
except Exception as error:
    market_reference = None
    mkt_box.warning(f"Market reference unavailable: {error}")

if reference_mode == "Automatic":
    if market_reference is None:
        st.error("Market data unavailable. Retry or use manual inputs after restoring the data source.")
        st.stop()
    market_price = market_reference["market_price"]
    shares_outstanding = market_reference["shares_outstanding"]
    mkt_box.markdown(
        f'<div class="ix-kv"><span>Market price</span><b>${market_price:,.2f}</b></div>'
        f'<div class="ix-kv"><span>Shares outstanding</span><b>{shares_outstanding / 1e9:,.3f} B</b></div>',
        unsafe_allow_html=True,
    )
    mkt_box.caption(f"Yahoo Finance · retrieved {str(market_reference['retrieved_at'])[:16].replace('T', ' ')} UTC")
else:
    market_price = mkt_box.number_input(
        "Market Price (USD)", min_value=0.01,
        value=float(market_reference["market_price"]) if market_reference else 100.0,
        step=1.0, key=f"manual_market_price_{ticker}",
    )
    shares_outstanding = mkt_box.number_input(
        "Shares Outstanding (shares)", min_value=1,
        value=int(market_reference["shares_outstanding"]) if market_reference else 1_000_000_000,
        step=1_000_000, key=f"manual_shares_outstanding_{ticker}",
    )
    mkt_box.caption("Manual values are illustrative until verified.")
    if new_company and market_reference is None:
        mkt_box.warning("Fallback share count from SEC common stock is not necessarily diluted; market price default $100 is a placeholder. Enter verified figures.")

terminal_growth = wacc_box.number_input(
    "Terminal growth (%)",
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
render_model_27(ticker, wacc, terminal_growth, market_price, shares_outstanding)
