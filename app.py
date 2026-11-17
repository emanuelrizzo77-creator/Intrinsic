# INTRINSIC — Streamlit dashboard (entry point).
# Presentation and user inputs only; the valuation engine lives in intrinsic/forecast.py
# and the discount-rate inputs in intrinsic/wacc_data.py / intrinsic/wacc_inputs.py.

from html import escape as html_escape

import os

import streamlit as st

# On Streamlit Community Cloud the SEC contact string comes from st.secrets.
try:
    if "INTRINSIC_SEC_USER_AGENT" in st.secrets and not os.environ.get("INTRINSIC_SEC_USER_AGENT"):
        os.environ["INTRINSIC_SEC_USER_AGENT"] = st.secrets["INTRINSIC_SEC_USER_AGENT"]
except Exception:   # no secrets file locally: the environment variable is used instead
    pass

from intrinsic.company_directory import fetch_sec_directory
from intrinsic.dashboard_panel import render_model_27
from intrinsic.inputs import DataUnavailable
from intrinsic.industry_beta import bottom_up_beta, load_industry_betas
from intrinsic.wacc_inputs import (risk_free_rate as _live_risk_free_rate, equity_risk_premium as equity_risk_premium_default,
                              marginal_tax_rate, cost_of_debt as synthetic_cost_of_debt)
from intrinsic.sector_routing import classify_sic
from intrinsic.market_reference import obtener_referencia_mercado
from intrinsic.wacc_calculator import calculate_wacc
from intrinsic.wacc_data import obtener_datos_wacc
from intrinsic.ui import components as ui
from intrinsic.ui import theme as ui_theme
from intrinsic.ui.i18n import LANGUAGES, STATE_KEY as LANG_KEY, t

MANUAL_WACC_DEFAULT = 0.09      # starting value for the manual override only
TERMINAL_GROWTH = 0.025         # long-run nominal growth; editable in the sidebar

# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Intrinsic | Equity Valuation",
    page_icon=":material/query_stats:",
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

# Design system (tokens, CSS, chart template) lives in intrinsic/ui/theme.py — presentation only.
st.markdown(ui_theme.CSS, unsafe_allow_html=True)

# Opening sequence: once per browser session (the "I", the hairline, the name typing itself).
_show_intro = not st.session_state.get("intrinsic_intro_seen", False)
st.session_state["intrinsic_intro_seen"] = True
if _show_intro:
    st.markdown(ui_theme.INTRO_CSS, unsafe_allow_html=True)
    ui.intro()

# ==========================================
# HISTORICAL DATA
# ==========================================


# Initial Top 25 candidate universe.
# Membership is a curated selection, not a live market-cap ranking.
# Shown whenever the SEC company search (universal engine) is in use.
def beta_notice():
    return (f'<div class="ix-beta"><div class="ix-beta-head">{ui.tag(t("Beta"), "warn")}'
            f'<b>{t("Universal engine in development")}</b></div>'
            f'<p>{t(BETA_BODY)}</p><p class="ix-beta-note">{t(BETA_NOTE)}</p></div>')


BETA_BODY = ("You are searching the full SEC universe. Intrinsic's model is fully tested on the <b>25 largest US "
             "companies</b>; extending it to every company that files with the SEC is still in progress. Some companies "
             "will be refused, show incomplete data or need manual inputs while that work continues &mdash; thank you for "
             "your patience. In a random test of 60 non-financial SEC companies, about 1 in 3 can be valued today; the rest "
             "are refused with the reason shown (foreign filers, loss-making companies, missing data).")
BETA_NOTE = ("Intrinsic is a portfolio project by a recent graduate, built to demonstrate financial modelling and data "
             "engineering. It is not a professional investment tool, and nothing here is investment advice.")

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
ui.brand(st.sidebar, animate=_show_intro)
st.sidebar.segmented_control(
    "Language", list(LANGUAGES), format_func=LANGUAGES.get, default="en", key=LANG_KEY,
    label_visibility="collapsed", width="stretch",
)
if not st.session_state.get(LANG_KEY):        # segmented control can be cleared; keep a language
    st.session_state[LANG_KEY] = "en"
st.sidebar.subheader(t("Company"))
selection_mode = st.sidebar.radio(
    t("Company source"),
    ["Top 25 companies", "SEC company search"],
    format_func=t,
    key="m22_source",
    horizontal=True,
    label_visibility="collapsed",
)
new_company = selection_mode == "SEC company search"
selected_cik = None
if not new_company:
    ticker = st.sidebar.selectbox(
        t("Selected company"),
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
        st.error(t("SEC directory unavailable: {err}", err=exc))
        st.info(t("Configure INTRINSIC_SEC_USER_AGENT with a real contact email."))
        st.stop()
    options = {f"{name} ({symbol})": (symbol, name, cik) for symbol, name, cik in directory}
    choice = st.sidebar.selectbox(t("Search name or ticker"), list(options), index=None,
                                  placeholder=t("Search Coca-Cola, KO, etc."), key="m22_search")
    st.markdown(beta_notice(), unsafe_allow_html=True)
    if choice is None:
        st.markdown('<div class="ix-empty">' + t(
            'Search any company filed with the SEC in the sidebar to open its workspace. For the fully tested '
            'experience, switch back to <b>Top 25 companies</b>.') + '</div>', unsafe_allow_html=True)
        st.stop()
    ticker, company_name, selected_cik = options[choice]
    st.sidebar.caption(f"SEC CIK: {selected_cik:010d}")
    st.sidebar.caption(t("Universal engine · beta"))

# Route by SEC industry BEFORE any market or WACC work: FCFF does not apply to
# banks, insurers, REITs or holding companies, and failing later looks like a bug.
@st.cache_data(ttl=86400, show_spinner=False)
def cargar_clasificacion(ticker, cik=None):
    from intrinsic.inputs import lookup_cik
    from intrinsic.sec_data import submissions_cached
    if cik is None:
        try:
            cik, _ = lookup_cik(ticker)
        except LookupError:
            return None
    profile = submissions_cached(int(cik))
    decision = classify_sic(profile.get("sic"))
    return {"model": decision.model, "category": decision.category, "reason": decision.reason,
            "sic": profile.get("sic"), "sic_description": profile.get("sicDescription")}

try:
    _route = cargar_clasificacion(ticker, selected_cik)
except Exception:
    _route = None          # classification unavailable: let the model's own checks decide
# Do not silently value Alphabet using Microsoft assumptions.
_valued = not _route or _route["model"] == "fcff"
st.markdown(
    f"""<div class="ix-head"><div>
      <div class="ix-eyebrow"><span>{t("Equity valuation")}</span><span>·</span><b>{t("DCF · FCFF, 10-year") if _valued else t("Not valued")}</b>
        <span>·</span><span>{t("Research tool, not investment advice")}</span></div>
      <div class="ix-name"><h1>{html_escape(company_name)}</h1><span class="ix-ticker">{html_escape(ticker)}</span></div>
    </div><div>{ui.tag(t("Universal engine · beta"), "warn") if new_company else ui.tag(t("Top 25 · fully tested"), "plain")}</div>
    </div>""", unsafe_allow_html=True,
)
# Filled by the dashboard once SEC and market data are loaded (company metadata strip).
header_strip = st.container()

if _route and _route["model"] != "fcff":
    _why = t({
        "bank_equity": "Banks earn money on their balance sheet: debt is raw material, not financing, so "
                       "free cash flow to the firm and WACC are not meaningful. They need an equity-based "
                       "model (dividend or excess-return) with regulatory capital.",
        "insurance_equity": "Insurers invest premiums before paying claims; cash flow depends on reserves and "
                            "regulatory capital, which an FCFF model does not capture.",
        "reit_affo": "REITs are valued on funds from operations (FFO/AFFO) or net asset value.",
        "holding_sotp": "Holding and investment companies are valued as the sum of their parts.",
    }.get(_route["model"], _route["reason"]))
    ui.state_card(
        t("Outside the scope of this model"),
        f'''<div class="ix-verdict"><strong>{html_escape(_route["category"])}</strong> ·
        SEC SIC {html_escape(str(_route["sic"]))} ({html_escape(str(_route["sic_description"] or ""))})</div>
        {html_escape(_why)}<br><br>{t("Intrinsic values non-financial operating companies with a free-cash-flow-to-the-firm model. Rather than force a number that would look precise but be wrong, this company is not valued. A sector-specific engine for financial companies is on the roadmap.")}''',
        "info",
    )
    st.stop()

# Model 27 is the single forecasting engine; it loads and audits its own SEC inputs.

st.sidebar.subheader(t("Assumptions"))
assumption_status = st.sidebar.container()   # filled below with the active mode of each input group
wacc_box = st.sidebar.expander(t("Discount rate (WACC)"), expanded=False)


# ==========================================
# DYNAMIC WACC SETTINGS
# ==========================================

wacc_mode = wacc_box.radio(
    t("WACC Calculation Mode"),
    ["Automatic Calculation", "Manual Override"],
    format_func=t,
    key=f"wacc_mode_{ticker}",
)

if new_company:
    wacc_box.caption(t(
        "Automatic WACC uses company-specific market and financial data. Review source dates and assumptions before "
        "relying on the result."))

if wacc_mode == "Automatic Calculation":

    
    # ==========================================
    # AUTOMATIC MARKET DATA
    # ==========================================

    try:
        with st.spinner(t("Loading market and SEC data...")):
            datos_wacc = cargar_datos_wacc(ticker)

    except DataUnavailable as error:
        ui.state_card(t("Not enough SEC data to value this company"),
                      f'{html_escape(str(error))}<br><br>' + t("Rather than fill gaps with guesses, Intrinsic does not "
                                                               "produce a value. Try another company, or one of the Top 25."))
        st.stop()
    except Exception as error:
        st.error(t("Unable to load automatic WACC data: {err}", err=error))
        st.info(t("Check the data sources or switch to Manual Override."))
        st.stop()

    wacc_box.caption(t("Market data {market} · SEC debt balance {debt}", market=str(datos_wacc['market_date'])[:10],
                       debt=datos_wacc['debt_date']))

    # ==========================================
    # EDITABLE FINANCIAL ASSUMPTIONS
    # ==========================================

    _rf_default, _rf_source = cargar_tasa_libre_riesgo()
    risk_free_rate = wacc_box.number_input(
        t("Risk-free rate (%)"),
        min_value=0.0,
        max_value=20.0,
        value=round(_rf_default * 100, 2),
        step=0.05,
        key="wacc_risk_free",
        help=_rf_source,
    ) / 100

    _bu = datos_wacc.get("beta_bottom_up") or {}
    _blume = datos_wacc.get("beta_adjusted")
    _REGRESSION = "Stock regression (Blume-adjusted)"   # internal option value; label translated via format_func
    _industries = [name for name in load_industry_betas() if not name.startswith("Total Market (")]
    _auto = _bu.get("industry")
    _choices = _industries + ([_REGRESSION] if _blume is not None else [])
    _regression_text = (t("Yahoo regression beta {raw:.2f}, Blume-adjusted {blume:.2f}", raw=datos_wacc['beta'], blume=_blume)
                        if _blume is not None else t("Yahoo Finance has no regression beta for this stock"))
    beta_basis = wacc_box.selectbox(
        t("Beta basis (industry)"),
        _choices,
        format_func=lambda c: t(c) if c == _REGRESSION else c,
        index=_choices.index(_auto) if _auto in _choices else len(_choices) - 1,
        key=f"wacc_beta_industry_{ticker}",
        help=(t("Matched automatically from SEC SIC {sic} ({match} match). ", sic=_bu['sic'], match=_bu['match'])
              if _auto else t("No industry match ({reason}). ", reason=_bu.get('reason', 'no SIC')))
             + t("Change it when the company's main risk sits in another business (one SIC code cannot describe a "
                 "multi-segment company)."),
    )
    if beta_basis != _REGRESSION:
        _bu = bottom_up_beta(_bu.get("sic"), market_equity=datos_wacc["market_equity"],
                             total_debt=datos_wacc["total_debt"],
                             industry=None if beta_basis == _auto else beta_basis)
    if beta_basis != _REGRESSION and _bu.get("beta") is not None:
        _beta_default = _bu["beta"]
        _beta_help = t(
            "Industry (bottom-up) beta: {industry} unlevered beta {bu:.2f} (cash-corrected, {n} US firms; Damodaran, Jan "
            "2026), relevered with this company's debt / market equity of {de:.0%} at a {tax:.0%} marginal tax rate. For "
            "comparison: {regression}. Industry averages are far less noisy than one stock's regression. Type another "
            "value to override.", industry=_bu['industry'], bu=_bu['unlevered_beta'], n=_bu['n_firms'],
            de=_bu['de_ratio'], tax=_bu['tax'], regression=_regression_text)
    else:
        _beta_default = _blume
        _beta_help = t("Yahoo regression beta {raw:.2f} with the Blume adjustment (0.67 × raw + 0.33). Single-stock betas "
                       "are noisy. Type another value to override.", raw=datos_wacc['beta'])
    beta = wacc_box.number_input(
        t("Beta (levered)"),
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
            _warn.append(t("broad SIC match, check the industry"))
        if _bu.get("small_industry"):
            _warn.append(t("only {n} firms in industry", n=_bu['n_firms']))
        wacc_box.caption(t("Beta source: industry · {detail}", detail=" · ".join([_bu["industry"]] + _warn)))
    else:
        wacc_box.caption(t("Beta source: stock regression (Blume)"))

    _erp_default, _erp_source = equity_risk_premium_default()
    equity_risk_premium = wacc_box.number_input(
        t("Equity risk premium (%)"),
        min_value=0.0,
        max_value=20.0,
        value=round(_erp_default * 100, 2),
        step=0.05,
        key="wacc_erp",
        help=_erp_source + ". " + t("The premium investors demand over Treasuries for the US market as a whole."),
    ) / 100

    
    historical_kd = datos_wacc.get("historical_kd")
    _cov = datos_wacc.get("interest_coverage")
    _kd, kd_source = synthetic_cost_of_debt(
        risk_free_rate, _cov["coverage"] if _cov else None,
        f", FY ending {_cov['fiscal_end']}" if _cov else "")
    if _kd is None:
        _kd = risk_free_rate + 0.0111
        kd_source = t("Assumption: risk-free + 1.11% (BBB default spread, Damodaran Jan 2026) because SEC filings do "
                      "not tag interest expense for this company. Edit if you know its rating.")
    if historical_kd is not None:
        kd_source += t(". For comparison, historical interest / average debt was {kd:.2%} (FY {fy}), which reflects "
                       "older coupons rather than today's borrowing cost.", kd=historical_kd['cost_of_debt'],
                       fy=historical_kd['fiscal_end'])

    cost_of_debt = wacc_box.number_input(
        t("Pre-tax cost of debt (%)"),
        value=round(_kd * 100, 2),
        min_value=0.0,
        max_value=30.0,
        step=0.05,
        key=f"wacc_cost_debt_{ticker}_{round(risk_free_rate, 4)}",
        help=kd_source,
    ) / 100
    wacc_box.caption(t("Cost of debt: synthetic rating from interest coverage") if _cov else
                     t("Cost of debt: assumed BBB spread · interest coverage unavailable"))

    _tax_default, _tax_source = marginal_tax_rate()
    tax_rate = wacc_box.number_input(
        t("Marginal tax rate (%)"),
        min_value=0.0,
        max_value=100.0,
        value=round(_tax_default * 100, 2),
        step=0.5,
        key=f"wacc_tax_rate_{ticker}",
        help=_tax_source + ". " + t("Used for the debt tax shield; matches the long-run tax rate in the forecast."),
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
    capm_inputs = {
        "risk_free_rate": risk_free_rate,
        "beta": beta,
        "equity_risk_premium": equity_risk_premium,
        "cost_of_equity": wacc_result["cost_of_equity"],
        "after_tax_cost_of_debt": wacc_result["after_tax_cost_of_debt"],
        "equity_weight": wacc_result["equity_weight"],
        "debt_weight": wacc_result["debt_weight"],
        "beta_source": (_bu["industry"] if beta_basis != _REGRESSION and _bu.get("beta") is not None
                        else t("stock regression (Blume)")),
    }

    wacc_box.markdown(
        '<div class="ix-state">' + ui.kv_rows(
            [(t("Market capitalization"), f"${market_equity / 1e9:,.1f} B"),
             (t("Total debt"), f"${total_debt / 1e9:,.1f} B"),
             (t("Cost of equity"), f"{(risk_free_rate + beta * equity_risk_premium) * 100:.2f}%")],
            total=(t("WACC"), f"{wacc * 100:.2f}%")) + '</div>',
        unsafe_allow_html=True,
    )

    wacc_box.caption(t(
        "Every input shows its source under the ? icon and stays editable. Defaults: live 10-year Treasury, Damodaran "
        "implied ERP and industry beta, synthetic-rating cost of debt, 25% marginal tax."))

else:
    capm_inputs = None
    wacc = wacc_box.number_input(
        t("Manual WACC (%)"),
        min_value=1.0,
        max_value=30.0,
        value=MANUAL_WACC_DEFAULT * 100,
        step=0.25,
        key=f"manual_wacc_{ticker}"
    ) / 100

# ==========================================
# MARKET REFERENCE — AUTOMATIC OR MANUAL
# ==========================================
mkt_box = st.sidebar.expander(t("Market price & shares"), expanded=False)
reference_mode = mkt_box.radio(
    t("Market Data Mode"),
    ["Automatic", "Manual Override"],
    format_func=t,
    key="market_reference_mode",
    horizontal=True,
)

try:
    with st.spinner(t("Loading market reference...")):
        market_reference = cargar_referencia_mercado(ticker)
except Exception as error:
    market_reference = None
    mkt_box.warning(t("Market reference unavailable: {err}", err=error))

if reference_mode == "Automatic":
    if market_reference is None:
        st.error(t("Market data unavailable. Retry or use manual inputs after restoring the data source."))
        st.stop()
    market_price = market_reference["market_price"]
    shares_outstanding = market_reference["shares_outstanding"]
    mkt_box.markdown(
        '<div class="ix-state">' + ui.kv_rows(
            [(t("Market price"), f"${market_price:,.2f}"),
             (t("Shares outstanding"), f"{shares_outstanding / 1e9:,.3f} B")]) + '</div>',
        unsafe_allow_html=True,
    )
    mkt_box.caption(t("Yahoo Finance · retrieved {ts} UTC", ts=str(market_reference['retrieved_at'])[:16].replace('T', ' ')))
else:
    market_price = mkt_box.number_input(
        t("Market Price (USD)"), min_value=0.01,
        value=float(market_reference["market_price"]) if market_reference else 100.0,
        step=1.0, key=f"manual_market_price_{ticker}",
    )
    shares_outstanding = mkt_box.number_input(
        t("Shares Outstanding (shares)"), min_value=1,
        value=int(market_reference["shares_outstanding"]) if market_reference else 1_000_000_000,
        step=1_000_000, key=f"manual_shares_outstanding_{ticker}",
    )
    mkt_box.caption(t("Manual values are illustrative until verified."))
    if new_company and market_reference is None:
        mkt_box.warning(t("Fallback share count from SEC common stock is not necessarily diluted; market price default "
                          "$100 is a placeholder. Enter verified figures."))

terminal_growth = wacc_box.number_input(
    t("Terminal growth (%)"),
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
    st.error(t("WACC must be greater than Terminal Growth."))
    st.stop()

# ==========================================
# INTRINSIC 27 WORKSPACE (single model)
# ==========================================
_wacc_manual = wacc_mode != "Automatic Calculation"
_price_manual = reference_mode != "Automatic"
_g_changed = abs(terminal_growth - TERMINAL_GROWTH) > 1e-12
assumption_status.markdown(
    '<div class="ix-state">' + ui.kv_rows([
        (t("Discount rate"), f'{ui.tag(t("Manual"), "user") if _wacc_manual else ui.tag(t("Auto"), "model")}&nbsp; {wacc * 100:.2f}%'),
        (t("Market price"), f'{ui.tag(t("Manual"), "user") if _price_manual else ui.tag(t("Auto"), "model")}&nbsp; ${market_price:,.2f}'),
        (t("Terminal growth"), f'{ui.tag(t("Edited"), "user") if _g_changed else ui.tag(t("Default"), "model")}&nbsp; {terminal_growth * 100:.2f}%'),
    ]) + '</div>', unsafe_allow_html=True)

render_model_27(ticker, wacc, terminal_growth, market_price, shares_outstanding, context={
    "slot": header_strip,
    "price_mode": "manual" if _price_manual else "auto",
    "price_source": (t("Manual input") if _price_manual else
                     t("Yahoo Finance · {ts} UTC", ts=str(market_reference['retrieved_at'])[:16].replace('T', ' '))),
    "wacc_mode": "manual" if _wacc_manual else "auto",
    "g_changed": _g_changed,
    "sic": (_route or {}).get("sic"),
    "industry": (_route or {}).get("sic_description"),
    "capm": capm_inputs,
})
