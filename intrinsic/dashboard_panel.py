"""Intrinsic 27 — Streamlit workspace for the integrated driver model.

Sections: Overview · Forecast · Valuation · Sensitivity · Model & Data, with three validated-uncertainty
scenarios and editable inputs. This module is presentation only: every number comes from
intrinsic.forecast (dm.run / dm.derive_assumptions) or from the inputs passed in by app.py.
Visual building blocks live in intrinsic/ui.
"""
from __future__ import annotations

import json
import math
import os
import re
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from intrinsic import forecast as dm
from intrinsic import sml
from intrinsic.inputs import DataUnavailable, load_inputs
from intrinsic.sec_data import is_number
from intrinsic.paths import ROOT
from intrinsic.ui import components as ui
from intrinsic.ui.i18n import GLOSSARY_ES, lang, scenario, t
from intrinsic.ui.theme import CHART_CONFIG, HISTORY_COLOR, SCENARIO_COLORS, T

HERE = ROOT   # project root (intrinsic.paths)
SCENARIOS = ('conservative', 'base', 'optimistic')
SOURCE_BADGE = {'data': 'Company data', 'calibrated': 'Calibrated (panel)',
                'assumption': 'Economic assumption', 'user': 'Your input'}
SOURCE_TAG_KIND = {'data': 'market', 'calibrated': 'model', 'assumption': 'warn', 'user': 'user'}
COLORS = {**SCENARIO_COLORS, 'market': T['market']}


def _chart(fig, title=None, caption=None, key=None):
    """Render a figure inside a bordered glass card (key → stable CSS class st-key-ixcard-*).

    `title` and `caption` are English source strings; they are translated here, while the CSS key is
    derived from the English title so it stays the same in every language."""
    slug = key or re.sub(r'[^a-z0-9]+', '-', (title or 'chart').lower()).strip('-')
    with st.container(border=True, key=f'ixcard-{slug}'):
        if title:
            ui.md(f'<div class="ix-card-title">{escape(t(title))}</div>')
        if caption:
            ui.md(f'<div class="ix-card-sub">{escape(t(caption))}</div>')
        st.plotly_chart(fig, width='stretch', config=CHART_CONFIG)


GLOSSARY = {
    'Intrinsic value': 'Estimated fair value per share: present value of projected free cash flows plus terminal value, '
                       'minus net debt, divided by diluted shares.',
    'Market price': 'Current share price reference (Yahoo Finance or your manual input).',
    'Upside / downside': 'Intrinsic value vs market price: (intrinsic / market − 1) × 100.',
    'WACC': 'Weighted average cost of capital: the discount rate for future cash flows. Higher WACC → lower value.',
    'Scenario': 'Conservative and optimistic use the 20th / 80th percentile of the model\'s real out-of-sample '
                'forecast errors for revenue and margin. Conservative also assumes competitive advantages fade '
                '(new investments earn only WACC).',
    'Revenue growth': 'Expected annual change in sales. Model 27 starts from the latest year and slows toward '
                      'long-run growth at the speed observed across thousands of companies.',
    'EBIT': 'Earnings before interest and taxes: operating profit.',
    'EBIT margin': 'EBIT as a percentage of revenue.',
    'NOPAT': 'Net operating profit after taxes: EBIT × (1 − tax rate). With R&D capitalised, R&D is added back '
             'and its amortisation charged.',
    'D&A': 'Depreciation and amortisation: non-cash cost of using fixed assets, added back to cash flow.',
    'CapEx': 'Capital expenditures: cash invested in long-lived assets. In Model 27 CapEx = growth in fixed '
             'assets + depreciation (+ assets that leave without depreciation), so CapEx and D&A stay consistent.',
    'Change in NWC': 'Change in operating working capital (receivables + inventory − payables, etc.). Negative '
                     'means growth releases cash (e.g. Amazon).',
    'FCFF': 'Free cash flow to the firm: NOPAT + D&A − CapEx − change in NWC. Cash available to all investors.',
    'ROIC': 'Return on invested capital: NOPAT / operating capital at the start of the year.',
    'Reinvestment rate': 'Share of NOPAT reinvested (net CapEx + working capital + R&D) to fund growth.',
    'PV of FCFF': 'Present value of the 10 projected free cash flows discounted at WACC.',
    'Terminal value': 'Value of all cash flows after year 10, growing at the terminal rate. It deducts the '
                      'reinvestment needed to sustain that growth.',
    'Enterprise value': 'Value of the operating business: PV of FCFF + PV of terminal value.',
    'Net debt': 'Debt (incl. finance leases) − cash − short-term investments − non-operating investments. '
                'Negative = net cash.',
    'Equity value': 'Enterprise value − net debt: value belonging to shareholders.',
    'Terminal growth': 'Perpetual growth after year 10. Must be below WACC; usually ≤ long-run GDP growth.',
    'Sensitivity matrix': 'Intrinsic value per share for different WACC and terminal growth combinations. '
                          'Not a probability forecast.',
    'Terminal share': 'Share of enterprise value that comes from cash flows after year 10 (PV of terminal value / EV).',
    'Security Market Line': 'CAPM line: required return = risk-free rate + beta × equity risk premium. Every '
                            'fairly priced stock sits on it.',
    'Beta': 'Sensitivity of the stock to the market. Beta 1 moves with the market; above 1 amplifies it.',
    'Required return': 'Return investors demand for the stock\'s risk: the CAPM cost of equity, a point on the line.',
    'Implied return': 'Cost of equity at which the DCF value equals today\'s market price: the return earned buying '
                      'at the market price if the forecast comes true.',
    'Alpha': 'Implied return − required return. Positive (above the line) = cheap for its risk; negative = expensive.',
    'Excess return model': 'Bank value = common book value + present value of future profits above the cost of equity '
                           '((ROE − Ke) × book value).',
    'Dividend discount model': 'Bank value = present value of dividends and buybacks to common shareholders, in two '
                               'stages: today\'s payout and growth, then a stable phase.',
    'Book value': 'Common equity on the balance sheet (total equity − preferred stock), per share.',
    'Justified P/B': 'Price-to-book ratio the excess-return model supports: equity value / book value. Above 1 only if '
                     'long-run ROE exceeds the cost of equity.',
    'Cost of equity': 'Return shareholders require (CAPM: risk-free rate + beta × equity risk premium). Banks are '
                      'discounted at this rate, not at WACC.',
    'ROE': 'Return on equity: net income to common / common equity at the start of the year.',
    'Long-run ROE': 'ROE the bank is assumed to earn after the fade period; the gap to the cost of equity drives value.',
    'Model gap': 'Dividend discount value vs excess-return value. Large gaps flag a payout or growth policy that does '
                 'not match the ROE path.',
}


def _term(term):
    """(display name, explanation) of a glossary term in the current language."""
    if lang() == 'es' and term in GLOSSARY_ES:
        return GLOSSARY_ES[term]
    return term, GLOSSARY.get(term, '')


def _help(term, explanation=None):
    name, text = _term(term)
    text = escape(explanation or text)
    return (f'<span class="intrinsic-help" tabindex="0" role="note" aria-label="{escape(name)}: {text}">'
            f'?<span class="intrinsic-tip" role="tooltip">{text}</span></span>')


def _glossary(terms):
    st.markdown('<div class="intrinsic-glossary">' + ''.join(
        f'<span class="intrinsic-glossary-item">{escape(_term(term)[0])}{_help(term)}</span>' for term in terms)
        + '</div>', unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def _inputs(ticker):
    data = load_inputs(ticker.replace('.', '-'))
    data['decision'] = vars(data['decision'])
    return data


def _validation_note():
    path = os.path.join(HERE, 'validation/results/final_validation.json')
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        rep = json.load(fh)
    v = rep.get('verdict', {})
    return sum(1 for x in v.values() if x.get('pass')), len(v)


# ------------------------------------------------------------------
# Editable inputs (plain language) -> driver overrides   [logic unchanged]
# ------------------------------------------------------------------

def _sidebar_inputs(ticker, probe):
    d = probe['drivers']
    v = {k: x['value'] for k, x in d.items()}
    phi, gT = v['growth_fade'], v['terminal_growth']
    year1 = gT + (v['growth_start'] - gT) * phi        # what the user actually sees for next year
    overrides = {}
    box = st.sidebar.expander(t('Forecast assumptions'), expanded=False)
    box.caption(t('Pre-filled with Model 27 values. Change any number to run your own case; changed inputs are labelled '
                  '"Your input".'))
    if box.button(t('Reset to model values'), key=f'm27_reset_{ticker}', width='stretch'):
        for k in list(st.session_state):
            if k.startswith(f'm27_in_{ticker}_'):
                del st.session_state[k]
    fields = (
        ('year1', 'Revenue growth next year (%)', year1,
         'Model estimate for next year. Growth then slows toward the terminal rate at the calibrated speed.'),
        ('margin_target', 'Long-run operating margin (%)', v.get('margin_target'),
         'Operating margin before amortisation of acquired intangibles that the business converges to. '
         'Default: median of the company\'s prior 9 years.'),
        ('intensity_target', 'Fixed assets per $ of revenue (%)', v.get('intensity_target'),
         'Net PP&E / revenue in the long run. Higher = more capital-intensive = more CapEx to grow.'),
        ('nwc_ratio_target', 'Working capital % of revenue (%)', v.get('nwc_ratio_target'),
         'Operating working capital / revenue. Negative values mean suppliers/customers finance growth.'),
        ('tax_terminal', 'Long-run tax rate (%)', v.get('tax_terminal'),
         'Tax rate the company converges to by year 10 (US statutory 21% + ~4% state by default).'),
    )
    path = 'profit_years' in d          # loss-making company on an explicit path to profitability
    if path:
        fields = tuple((k, l, dv, 'Target operating margin for this loss-making company: its industry\'s margin '
                                  '(Damodaran, Jan 2026), because its own history implies losses forever.')
                       if k == 'margin_target' else (k, l, dv, h) for k, l, dv, h in fields)
    for key, label, default, help_text in fields:
        if not is_number(default):
            continue
        val = box.number_input(t(label), value=float(round(default * 100, 2)), step=0.5, help=t(help_text),
                                      key=f'm27_in_{ticker}_{key}') / 100
        if abs(val - round(default, 4)) > 1e-6:
            if key == 'year1':
                overrides['growth_start'] = gT + (val - gT) / max(phi, 1e-6)
            else:
                overrides[key] = val
    if path:
        years0 = int(v['profit_years'])
        years = box.number_input(t('Years to reach the target margin'), min_value=1, max_value=10, value=years0, step=1,
                                 help=t('The margin moves in a straight line from today to the target, then holds.'),
                                 key=f'm27_in_{ticker}_profit_years')
        if years != years0:
            overrides['profit_years'] = int(years)
        p0 = v['failure_prob']
        p = box.number_input(t('Probability of failure (%)'), min_value=0.0, max_value=100.0,
                             value=float(round(p0 * 100, 1)), step=5.0,
                             help=t('Chance the company fails before becoming profitable. If it fails, shareholders get '
                                    'its net cash (or nothing). Default from cash runway: 5 or more years of cash 10%, '
                                    '2–5 years 20%, 1–2 years 35%, under 1 year 50%; 5% if already profitable.'),
                             key=f'm27_in_{ticker}_failure_prob') / 100
        if abs(p - round(p0, 3)) > 1e-6:
            overrides['failure_prob'] = p
    return overrides


def _run_all(data, wacc, g, overrides):
    br = data['bridge']
    return {s: dm.run(data['history'], wacc=wacc, terminal_growth=g, net_debt=br['net_debt'], shares=br['shares'],
                      scenario=s, overrides=overrides or None, rd_life=data['rd_life'], rd_life_note=data['rd_note'], industry_margin=data.get('industry_margin'))
            for s in SCENARIOS}


def _price(res):
    v = res.get('valuation')
    return v['intrinsic_price'] if v else None


def _history_series(data, field):
    """(fiscal years, values) of a reported SEC history field, skipping missing values. Display only."""
    xs, ys = [], []
    for r in data.get('history', []):
        y, x = r.get('Fiscal year end'), r.get(field)
        if y and is_number(x):
            xs.append(int(str(y)[:4]))
            ys.append(x)
    return xs, ys


def _forecast_divider(fig, year0):
    fig.add_vline(x=year0 + 0.5, line=dict(color=T['line_strong'], width=1, dash='dot'))
    fig.add_annotation(x=year0 + 0.5, y=1, yref='paper', text=t('Forecast →'), showarrow=False, xanchor='left',
                       yanchor='top', xshift=4, font=dict(size=10, color=T['text3']))


# ------------------------------------------------------------------
# Company strip (header metadata)
# ------------------------------------------------------------------

def _company_strip(slot, ctx, data, market_price, market_shares, status):
    br = data['bridge']
    hist = data.get('history') or []
    years = [str(r.get('Fiscal year end', ''))[:4] for r in hist if r.get('Fiscal year end')]
    cells = [(t('Market price · USD'), ui.usd(market_price), escape(ctx.get('price_source', '')))]
    if market_shares:
        cells.append((t('Market cap'), ui.usd_b(market_price * market_shares), t('price × shares outstanding')))
    if years:
        cells.append((t('Financials'), f'FY{years[0]}–FY{years[-1]}',
                      t('{n} 10-K years · FYE {fye}', n=len(years), fye=escape(str(hist[-1]["Fiscal year end"])))))
    cells.append((t('Balance sheet'), escape(str(br.get('balance_date') or '—')), 'SEC EDGAR'))
    if ctx.get('industry'):
        cells.append((t('Industry (SIC)'), escape(str(ctx.get('sic') or '—')), escape(ctx['industry'])))
    st_label = {'DATA_COMPLETE': t('Complete'), 'DEGRADED': t('Degraded')}.get(status, status.title())
    cells.append((t('Data status'), st_label, t('see Model & Data')))
    slot.markdown('<div class="ix-strip">' + ''.join(
        f'<div><span>{k}</span><b>{v}</b><small>{f}</small></div>' for k, v, f in cells) + '</div>',
        unsafe_allow_html=True)


# ------------------------------------------------------------------
# Sections
# ------------------------------------------------------------------

def _not_valued_reason(res):
    err = str(res.get('valuation_error', ''))
    if 'Terminal NOPAT is not positive' in err or not err:
        if 'profit_years' in res['assumptions']['drivers']:
            return t('in this scenario the company never becomes profitable, so it would be worth only its net cash')
        return t('no positive terminal operating profit')
    return err


def _overview(results, scen, wacc, market_price, market_shares, data, g=None, ctx=None):
    ctx = ctx or {}
    val = results[scen]['valuation']
    price = val['intrinsic_price']
    upside = (price / market_price - 1) * 100 if market_price else 0.0
    cls = 'pos' if upside >= 0 else 'neg'
    prices = {s: _price(results[s]) for s in SCENARIOS}
    manual_price = ctx.get('price_mode') == 'manual'
    mkt_tag = ui.tag(t('Market · your input'), 'user') if manual_price else ui.tag(t('Live market data'), 'market live')

    ui.md(f"""
    <div class="ix-hero">
      <div class="ix-hero-top">
        <div class="ix-hero-cell">{ui.tag(t('Model estimate · {scen}', scen=scenario(scen).lower()), 'model')}
          <div class="ix-big model">{ui.usd(price)}</div>
          <div class="ix-big-sub">{t('Intrinsic value per share · 10-year FCFF DCF')} {_help('Intrinsic value')}</div></div>
        <div class="ix-hero-cell">{mkt_tag}
          <div class="ix-big">{ui.usd(market_price)}</div>
          <div class="ix-big-sub">{escape(ctx.get('price_source', t('Latest market reference')))} {_help('Market price')}</div></div>
        <div class="ix-hero-cell">{ui.tag(t('Implied'), 'plain')}
          <div class="ix-big {cls}">{'+' if upside >= 0 else '−'}{abs(upside):.1f}%</div>
          <div class="ix-big-sub">{t('{word} · intrinsic vs market', word=t('Upside') if upside >= 0 else t('Downside'))} {_help('Upside / downside')}</div></div>
      </div>
      <div class="ix-range"><div class="ix-label">{t('Valuation range vs market price')}</div>
        {ui.range_bar(prices, market_price, scen)}</div>
    </div>""")

    wacc_cls = 'user' if ctx.get('wacc_mode') == 'manual' else ''
    g_cls = 'user' if ctx.get('g_changed') else ''
    ui.md('<div class="ix-metrics">'
          + ui.metric(t('Enterprise value'), ui.usd_b(val['enterprise_value']), t('PV FCFF + PV terminal'), 'model',
                      _help('Enterprise value'))
          + ui.metric(t('Equity value'), ui.usd_b(val['equity_value']),
                      t('probability-weighted') if 'failure_prob' in val else t('EV − net debt'), 'model',
                      _help('Equity value'))
          + ui.metric(t('Net debt'), ui.usd_b(data['bridge']['net_debt']), t('SEC balance sheet'), '', _help('Net debt'))
          + ui.metric('WACC', ui.pct(wacc), t('manual override') if wacc_cls else t('sourced inputs · editable'), wacc_cls,
                      _help('WACC'))
          + ui.metric(t('Terminal growth'), ui.pct(g) if g is not None else '—',
                      t('your input') if g_cls else t('default · editable'), g_cls, _help('Terminal growth'))
          + ui.metric(t('Terminal share of EV'), f"{val['terminal_share_of_ev']:.0%}", t('value after year 10'), '',
                      _help('Terminal share'))
          + '</div>')

    missing = [s for s in SCENARIOS if prices[s] is None]
    if missing:
        st.warning(t('Not valued: {scenarios} scenario — {reasons}.',
                     scenarios=', '.join(scenario(m) for m in missing),
                     reasons='; '.join(_not_valued_reason(results[m]) for m in missing)))
    lo, hi = prices['conservative'], prices['optimistic']
    if lo is None or hi is None:
        known = [p for p in prices.values() if p is not None]
        lo = lo if lo is not None else min(known)
        hi = hi if hi is not None else max(known)
    if hi is not None and market_price > hi:
        tone, head = 'above', t('Market price is above the optimistic case')
        verdict = t("The market price (${mp:,.2f}) is ABOVE even the optimistic scenario (${hi:,.2f}): the market expects more "
                    "growth, margin or longer-lasting advantages than the model's optimistic case.", mp=market_price, hi=hi)
    elif lo is not None and market_price < lo:
        tone, head = 'below', t('Market price is below the conservative case')
        verdict = t("The market price (${mp:,.2f}) is BELOW even the conservative scenario (${lo:,.2f}): the market is more "
                    "pessimistic than the model's conservative case.", mp=market_price, lo=lo)
    else:
        tone, head = 'inside', t('Market price is inside the model range')
        verdict = t("The market price (${mp:,.2f}) is INSIDE the model's range (${lo:,.2f} – ${hi:,.2f}): the market's expectations "
                    "are consistent with the model's uncertainty.", mp=market_price, lo=lo, hi=hi)
    share = val['terminal_share_of_ev']
    drv = results[scen]['assumptions']['drivers']
    m0, mT = drv['margin_start']['value'], drv['margin_target']['value']
    if is_number(m0) and is_number(mT):
        gap = mT - m0
        move = ('falls' if gap < -0.005 else 'rises' if gap > 0.005 else 'stays')
        margin_line = ('<li>' + t('<strong>Biggest assumption — operating margin:</strong> the forecast assumes it {move} from {m0:.1%} (latest '
                                  'year) {prep} {mT:.1%} in the long run ({note}). ', move=t(move), m0=m0,
                                  prep=t('to') if move != 'stays' else t('near'), mT=mT,
                                  note=escape(_engine_note(drv['margin_target']['note'])))
                       + (t('Tested out of sample, this anchor beat recent-level alternatives on average, but a company whose business '
                            'changed for good would be undervalued. ') if gap < -0.05 else '')
                       + t('Change it under <em>Forecast assumptions</em> to test your own view.') + '</li>')
    else:
        margin_line = ''
    if 'failure_prob' in val:
        margin_line = ('<li>' + t('<strong>Loss-making company — path to profitability:</strong> its own history implies '
                                  'losses forever, so the margin is assumed to rise in a straight line from {m0:.1%} to its '
                                  'industry\'s {mT:.1%} in {n} years. This is an assumption, not a forecast the model has '
                                  'validated.', m0=m0, mT=mT, n=int(drv['profit_years']['value'])) + '</li>'
                       + '<li>' + t('<strong>Probability of failure {p:.0%}:</strong> value = {q:.0%} × {gc} if it gets '
                                    'there + {p:.0%} × {ds} if it fails (shareholders keep only net cash).',
                                    p=val['failure_prob'], q=1 - val['failure_prob'], gc=ui.usd(val['going_concern_price']),
                                    ds=ui.usd(val['distress_price'])) + '</li>')

    left, right = st.columns([1.55, 1], gap='medium')
    with left:
        ui.md(f'<div class="ix-note"><div class="ix-label">{t("What this means")}</div>'
              f'<div class="ix-verdict {tone}"><strong>{head}.</strong> {verdict}</div><ul>'
              + margin_line +
              '<li>' + t('<strong>Terminal value:</strong> {share:.0%} of enterprise value comes from cash flows after year 10.',
                         share=share) + '</li>'
              '<li>' + t("<strong>How to read the range:</strong> conservative/optimistic come from the model's measured forecast "
                         "errors (20th/80th percentile), not from arbitrary ±%.") + '</li></ul></div>')
    with right:
        a = results[scen]['assumptions']
        status = results[scen]['status']
        st_tag = (ui.tag(t('Data complete'), 'pos') if status == 'DATA_COMPLETE'
                  else ui.tag(t('Degraded') if status == 'DEGRADED' else status.title(), 'warn'))
        ui.md(f'<div class="ix-note"><div class="ix-label">{t("Model transparency")}</div>'
              f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">{st_tag}'
              f'{ui.tag(t("{n} warnings", n=len(a["degradations"])), "warn" if a["degradations"] else "plain")}'
              f'{ui.tag(t("{n} notes", n=len(a.get("notes", []))), "plain")}</div>'
              + t('<strong>Validated:</strong> revenue and EBIT-margin forecasts, out of sample.<br><strong>Not validated:</strong> '
                  'CapEx, D&amp;A, working-capital paths and the final valuation. Read the range, not a single number. Details '
                  'under <em>Model &amp; Data</em>.') + '</div>')

    with st.expander(t('Market data & capital structure')):
        br = data['bridge']
        rows = []
        if market_shares:
            rows.append((t('Market capitalization'), f'${market_price * market_shares / 1e9:,.2f} B'))
        rows += [(t('Net debt used (negative = net cash)'), f"${br['net_debt'] / 1e9:,.2f} B"),
                 (t('Shares used'), f"{br['shares']:,.0f}"),
                 (t('Share source'), escape(str(br['shares_source']))),
                 (t('SEC balance date'), escape(str(br['balance_date'])))]
        ui.md('<div class="ix-state">' + ui.kv_rows(rows) + '</div>')


def _engine_note(note):
    """Translate the engine notes that appear in prominent places (the rest stay in English)."""
    m = re.fullmatch(r'company median of (\d+) prior years; no industry shrinkage yet', str(note))
    return t('company median of {n} prior years; no industry shrinkage yet', n=m.group(1)) if m else note


def _fmt_m(x):
    """USD millions, accounting style (negatives in parentheses). Display only."""
    if not is_number(x):
        return '—'
    v = round(x / 1e6)
    return f'({abs(v):,.0f})' if v < 0 else f'{v:,.0f}'


def _fmt_p(x):
    return f'{x * 100:.1f}%' if is_number(x) else '—'


def _forecast(results, scen, ticker, data=None):
    ui.heading(t('Financial forecast'), t('{scen} scenario · USD millions · years 1–5 forecast, years 6–10 fade to steady '
                                          'state before the terminal value', scen=escape(scenario(scen))))
    _glossary(['Revenue growth', 'EBIT', 'NOPAT', 'D&A', 'CapEx', 'Change in NWC', 'FCFF', 'ROIC', 'Reinvestment rate'])
    rows = results[scen]['projection']['rows']
    df = pd.DataFrame({
        'Fiscal Year': [r['year'] for r in rows],
        'Revenue': [r['revenue'] / 1e6 for r in rows],
        'Growth %': [r['growth'] * 100 for r in rows],
        'EBIT': [r['ebit'] / 1e6 for r in rows],
        'EBIT margin %': [r['ebit_margin'] * 100 for r in rows],
        'NOPAT': [r['nopat'] / 1e6 for r in rows],
        'D&A': [r['da'] / 1e6 for r in rows],
        'CapEx': [r['capex'] / 1e6 for r in rows],
        'Change in NWC': [r['delta_nwc'] / 1e6 for r in rows],
        'FCFF': [r['fcff'] / 1e6 for r in rows],
        'ROIC %': [r['roic'] * 100 if r['roic'] is not None else None for r in rows],
    })
    data = data or {}
    hist = data.get('history') or []
    last = hist[-1] if hist else {}
    year0 = rows[0]['year'] - 1

    # ---- charts
    c1, c2 = st.columns(2, gap='small')
    with c1:
        fig = go.Figure()
        hx, hy = _history_series(data, 'Revenue')
        if hx:
            fig.add_trace(go.Scatter(x=hx, y=[y / 1e9 for y in hy], mode='lines+markers', name=t('Reported'),
                                     line=dict(color=HISTORY_COLOR, width=1.6), marker=dict(size=4),
                                     hovertemplate='$%{y:,.1f} B'))
        for s in SCENARIOS:
            p = results[s].get('projection')
            if p:
                fig.add_trace(go.Scatter(x=[r['year'] for r in p['rows']], y=[r['revenue'] / 1e9 for r in p['rows']],
                                         mode='lines', name=scenario(s), hovertemplate='$%{y:,.1f} B',
                                         line=dict(color=COLORS[s], width=2.6 if s == scen else 1.4,
                                                   dash='solid' if s == scen else 'dot')))
        _forecast_divider(fig, year0)
        fig.update_layout(template='intrinsic', yaxis_title=t('USD billions'), height=300,
                          legend=dict(orientation='h', y=-0.18, x=0))
        _chart(fig, 'Revenue', 'Reported 10-K history and the three scenarios')
    with c2:
        fig = go.Figure()
        hx, hy = _history_series(data, 'EBIT margin')
        if hx:
            fig.add_trace(go.Scatter(x=hx, y=[y * 100 for y in hy], mode='lines+markers', name=t('EBIT margin (reported)'),
                                     line=dict(color=HISTORY_COLOR, width=1.6), marker=dict(size=4),
                                     hovertemplate='%{y:.1f}%'))
        gx, gy = _history_series(data, 'Revenue growth')
        if gx:
            fig.add_trace(go.Scatter(x=gx, y=[y * 100 for y in gy], mode='lines', name=t('Growth (reported)'),
                                     line=dict(color=HISTORY_COLOR, width=1.2, dash='dot'), hovertemplate='%{y:.1f}%'))
        fig.add_trace(go.Scatter(x=[r['year'] for r in rows], y=[r['ebit_margin'] * 100 for r in rows], mode='lines',
                                 name=t('EBIT margin'), line=dict(color=COLORS[scen], width=2.6), hovertemplate='%{y:.1f}%'))
        fig.add_trace(go.Scatter(x=[r['year'] for r in rows], y=[r['growth'] * 100 for r in rows], mode='lines',
                                 name=t('Revenue growth'), line=dict(color=COLORS[scen], width=1.6, dash='dot'),
                                 hovertemplate='%{y:.1f}%'))
        _forecast_divider(fig, year0)
        fig.update_layout(template='intrinsic', yaxis_title='%', height=300, legend=dict(orientation='h', y=-0.18, x=0))
        _chart(fig, 'Revenue growth and EBIT margin', t('{scen} scenario vs reported history', scen=scenario(scen)))
    c3, c4 = st.columns(2, gap='small')
    with c3:
        fc = [r['fcff'] / 1e9 for r in rows]
        fig = go.Figure(go.Bar(x=[r['year'] for r in rows], y=fc, name='FCFF', hovertemplate='$%{y:,.2f} B',
                               marker_color=[COLORS[scen] if y >= 0 else T['neg'] for y in fc], marker_line_width=0))
        fig.update_layout(template='intrinsic', yaxis_title=t('USD billions'), height=280, bargap=0.4, showlegend=False)
        _chart(fig, 'Free cash flow to the firm', 'NOPAT + D&A − CapEx − change in NWC')
    with c4:
        fig = go.Figure()
        hx, hy = _history_series(data, 'CapEx')
        if hx:
            fig.add_trace(go.Scatter(x=hx, y=[y / 1e9 for y in hy], mode='lines+markers', name=t('CapEx (reported)'),
                                     line=dict(color=HISTORY_COLOR, width=1.4), marker=dict(size=4),
                                     hovertemplate='$%{y:,.2f} B'))
        fig.add_trace(go.Scatter(x=[r['year'] for r in rows], y=[r['capex'] / 1e9 for r in rows], mode='lines',
                                 name='CapEx', line=dict(color=COLORS[scen], width=2.4), hovertemplate='$%{y:,.2f} B'))
        fig.add_trace(go.Scatter(x=[r['year'] for r in rows], y=[r['da'] / 1e9 for r in rows], mode='lines',
                                 name='D&A', line=dict(color=T['text'], width=1.4, dash='dash'),
                                 hovertemplate='$%{y:,.2f} B'))
        _forecast_divider(fig, year0)
        fig.update_layout(template='intrinsic', yaxis_title=t('USD billions'), height=280,
                          legend=dict(orientation='h', y=-0.22, x=0))
        _chart(fig, 'CapEx and D&A', 'From the PP&E roll-forward, so the two stay consistent')

    # ---- statement-style table (years as columns)
    a_lbl = f'FY{year0}A' if last else None
    header = [t('USD millions')] + ([a_lbl] if a_lbl else []) + [f'{r["year"]}E' for r in rows]
    hcls = [''] + (['a'] if a_lbl else []) + ['' if r['t'] <= 5 else 'fade' for r in rows]

    def line(label, key, fmt, actual=None, rc='', neg_red=False):
        cells = [(escape(t(label)), '')]
        if a_lbl:
            cells.append((fmt(actual) if actual is not None else '—', 'a'))
        for r in rows:
            x = r.get(key)
            c = 'fade' if r['t'] > 5 else ''
            if neg_red and is_number(x) and x < 0:
                c += ' neg'
            cells.append((fmt(x), c))
        return (rc, cells)

    body = [
        line('Revenue', 'revenue', _fmt_m, last.get('Revenue')),
        line('Growth', 'growth', _fmt_p, last.get('Revenue growth'), 'sub'),
        line('EBIT', 'ebit', _fmt_m, last.get('EBIT')),
        line('EBIT margin', 'ebit_margin', _fmt_p, last.get('EBIT margin'), 'sub'),
        line('NOPAT', 'nopat', _fmt_m),
        line('D&A', 'da', _fmt_m),
        line('CapEx', 'capex', _fmt_m, last.get('CapEx')),
        line('Change in NWC', 'delta_nwc', _fmt_m),
        line('FCFF', 'fcff', _fmt_m, None, 'total key', neg_red=True),
        line('ROIC', 'roic', _fmt_p, None, 'sub'),
    ]
    ui.md(ui.html_table(header, body, hcls))
    st.caption(t('A = reported (SEC 10-K, FY{y}); E = model estimate. Years 6–10 (dimmed) complete the fade to steady state. '
                 'Negative values in parentheses.', y=year0))
    st.download_button(t('Download forecast CSV'), df.to_csv(index=False),
                       file_name=f'intrinsic_{ticker.lower()}_forecast_{scen}.csv', mime='text/csv')


def _waterfall(labels, values, measures, title, caption=None, height=380):
    fig = go.Figure(go.Waterfall(
        orientation='v', measure=measures, x=labels, y=values,
        text=[f'${abs(v):,.1f} B' for v in values], textposition='outside',
        textfont=dict(family="'IBM Plex Mono', monospace", size=10, color=T['text2']),
        connector={'line': {'color': T['line_strong'], 'width': 1}},
        increasing={'marker': {'color': 'rgba(75,203,139,.75)'}},
        decreasing={'marker': {'color': 'rgba(242,112,123,.75)'}},
        totals={'marker': {'color': T['model']}}))
    fig.update_layout(template='intrinsic', yaxis_title=t('USD billions'), height=height, showlegend=False,
                      hovermode='closest')
    fig.update_xaxes(tickfont=dict(family="'IBM Plex Sans', sans-serif", size=11))
    _chart(fig, title, caption)


def _valuation(results, scen, data):
    ui.heading(t('DCF valuation breakdown'), t('{scen} scenario · from free cash flow to value per share',
                                               scen=escape(scenario(scen))))
    _glossary(['PV of FCFF', 'Terminal value', 'Enterprise value', 'Net debt', 'Equity value', 'Intrinsic value'])
    res, br = results[scen], data['bridge']
    v, term = res['valuation'], res['valuation']['terminal']

    left, right = st.columns([1.3, 1], gap='medium')
    with left:
        ledger = [
            ('', [(t('PV of forecast FCFF (10 years)'), ''), (f"${v['pv_fcff'] / 1e9:,.2f} B", '')]),
            ('', [(t('PV of terminal value'), ''), (f"${v['pv_terminal'] / 1e9:,.2f} B", '')]),
            ('total', [(t('Enterprise value'), ''), (f"${v['enterprise_value'] / 1e9:,.2f} B", '')]),
            ('', [(t('Net debt (negative = net cash)'), ''), (f"${br['net_debt'] / 1e9:,.2f} B", '')]),
        ]
        if 'failure_prob' in v:
            p = v['failure_prob']
            ledger += [
                ('total', [(t('Equity value if it becomes profitable'), ''), (f"${v['going_concern_equity'] / 1e9:,.2f} B", '')]),
                ('', [(t('Equity value if it fails (net cash, floored at 0)'), ''), (f"${v['distress_equity'] / 1e9:,.2f} B", '')]),
                ('', [(t('Probability of failure'), ''), (f'{p:.0%}', '')]),
                ('total', [(t('Probability-weighted equity value'), ''), (f"${v['equity_value'] / 1e9:,.2f} B", '')]),
            ]
        else:
            ledger.append(('total', [(t('Equity value'), ''), (f"${v['equity_value'] / 1e9:,.2f} B", '')]))
        ledger += [
            ('', [(t('Diluted shares'), ''), (f"{br['shares']:,.0f}", '')]),
            ('total key', [(t('Intrinsic value / share'), ''), (f"${v['intrinsic_price']:,.2f}", '')]),
        ]
        ui.md(f'<div class="ix-label">{t("Equity bridge")}</div>' + ui.html_table([t('Metric'), t('Value')], ledger))
    with right:
        method = (t('steady-state reinvestment (advantages persist)') if term['mode'] == 'steady_state'
                  else t('RONIC = WACC (advantages fade)'))
        ui.md(f'<div class="ix-label">{t("Terminal value")}</div><div class="ix-state">' + ui.kv_rows([
            (t('Method'), escape(method)),
            (t('Reinvestment rate'), t('{x:.1%} of NOPAT', x=term['reinvestment_rate'])),
            (t('Implied RONIC'), f"{term['ronic']:.1%}" if term['ronic'] else 'n/a'),
            (t('Share of enterprise value'), f"{v['terminal_share_of_ev']:.0%}"),
        ]) + '</div>')
        st.caption(t('Balance date {date} · Debt: {debt} · Non-operating investments at book value (verify their income is '
                     'excluded from EBIT).', date=br['balance_date'], debt=br['debt_source']))

    rows = res['projection']['rows']
    pv = v['pv_fcff_by_year']
    _waterfall([str(r['year']) for r in rows] + [t('Terminal value'), t('Enterprise value')],
               [x / 1e9 for x in pv] + [v['pv_terminal'] / 1e9, v['enterprise_value'] / 1e9],
               ['relative'] * (len(pv) + 1) + ['total'], 'How the value builds up',
               'Present value of each year\'s free cash flow, then the terminal value → enterprise value')

    labels, values, measures = [t('Enterprise Value')], [v['enterprise_value'] / 1e9], ['absolute']
    labels.append(t('Total debt (incl. finance leases)')); values.append(-(br['total_debt'] or 0) / 1e9); measures.append('relative')
    labels.append(t('Cash & equivalents')); values.append((br['cash'] or 0) / 1e9); measures.append('relative')
    labels.append(t('Short-term investments')); values.append((br['short_term_investments'] or 0) / 1e9); measures.append('relative')
    for k, x in br.get('non_operating_assets', {}).items():
        labels.append(t(k)); values.append(x / 1e9); measures.append('relative')
    labels.append(t('Equity Value')); values.append(v.get('going_concern_equity', v['equity_value']) / 1e9)
    measures.append('total')
    _waterfall(labels, values, measures, 'From enterprise value to equity value',
               'Debt is deducted; cash, short-term and non-operating investments are added')
    if 'failure_prob' in v:
        st.caption(t('Equity value shown if the company becomes profitable; the valuation then weights it with the '
                     'probability of failure (see Equity bridge).'))


def _sensitivity(data, scen, wacc, g, overrides, market_price, ticker):
    ui.heading(t('WACC × terminal growth sensitivity'),
               t('{scen} scenario · intrinsic value per share and upside vs market price', scen=escape(scenario(scen))))
    _glossary(['WACC', 'Terminal growth', 'Sensitivity matrix'])
    waccs = [wacc + d for d in (-0.02, -0.01, 0, 0.01, 0.02)]
    growths = [g + d for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    br, matrix = data['bridge'], []
    for w in waccs:
        row = []
        for gg in growths:
            if w <= gg or w <= 0 or gg < 0:
                row.append(float('nan'))
                continue
            out = dm.run(data['history'], wacc=w, terminal_growth=gg, net_debt=br['net_debt'], shares=br['shares'],
                         scenario=scen, overrides=overrides or None, rd_life=data['rd_life'],
                         rd_life_note=data['rd_note'], industry_margin=data.get('industry_margin'))
            row.append(_price(out) if _price(out) is not None else float('nan'))
        matrix.append(row)
    text = [[(f'<b>${x:,.0f}</b><br>{(x / market_price - 1) * 100:+.0f}%' if not math.isnan(x) else 'N/A') for x in r]
            for r in matrix]
    xl, yl = [f'{x * 100:.2f}%' for x in growths], [f'{w * 100:.2f}%' for w in waccs]
    fig = go.Figure(go.Heatmap(z=matrix, x=xl, y=yl,
                               colorscale=[[0, '#7A2E38'], [0.5, T['surface2']], [1, '#1F6B4A']], zmid=market_price,
                               text=text, texttemplate='%{text}',
                               textfont=dict(color=T['text'], family="'IBM Plex Mono', monospace", size=12),
                               xgap=2, ygap=2, hovertemplate='Terminal growth %{x}<br>WACC %{y}<br>%{text}<extra></extra>',
                               colorbar=dict(title=dict(text='$/share', font=dict(size=11)), thickness=10,
                                             outlinewidth=0, tickfont=dict(size=10))))
    fig.add_shape(type='rect', xref='x', yref='y', x0=1.5, x1=2.5, y0=1.5, y1=2.5,
                  line=dict(color=T['text'], width=1.5))
    fig.update_layout(template='intrinsic', xaxis_title=t('Terminal growth'), yaxis_title='WACC', height=430,
                      hovermode='closest')
    fig.update_xaxes(side='top', showgrid=False)
    fig.update_yaxes(autorange='reversed', showgrid=False)
    _chart(fig, key='sensitivity')
    st.caption(t('Colour midpoint = market price (${mp:,.2f}): green cells are above the market, red below. Outlined cell = '
                 'current inputs. N/A = WACC not above growth, or no positive terminal profit.', mp=market_price))
    export = pd.DataFrame(matrix, index=[f'{w * 100:.2f}%' for w in waccs], columns=[f'{x * 100:.2f}%' for x in growths])
    export.index.name = 'WACC / Terminal Growth'
    st.download_button(t('Download Sensitivity CSV'), export.to_csv(),
                       file_name=f'intrinsic_{ticker.lower()}_sensitivity_{scen}.csv', mime='text/csv')


def _risk_return(ticker, scen, data, g, overrides, market_price, capm):
    ui.heading(t('Security Market Line'),
               t('{scen} scenario · CAPM required return vs the return implied by the market price',
                 scen=escape(scenario(scen))))
    _glossary(['Security Market Line', 'Beta', 'Required return', 'Implied return', 'Alpha'])
    if not capm:
        ui.state_card(t('Needs the automatic discount rate'),
                      t('The Security Market Line is built from the beta, risk-free rate and equity risk premium. '
                        'With a manual WACC those inputs are unknown; switch the discount rate to Automatic Calculation '
                        'in the sidebar.'))
        return
    rf, beta, erp = capm['risk_free_rate'], capm['beta'], capm['equity_risk_premium']
    required = sml.required_return(rf, beta, erp)
    br = data['bridge']

    def value_at(w):
        out = dm.run(data['history'], wacc=w, terminal_growth=g, net_debt=br['net_debt'], shares=br['shares'],
                     scenario=scen, overrides=overrides or None, rd_life=data['rd_life'], rd_life_note=data['rd_note'], industry_margin=data.get('industry_margin'))
        return _price(out)

    implied_w = _implied_wacc(ticker, data, scen, g, overrides, market_price, value_at)
    implied = (sml.implied_cost_of_equity(implied_w, capm['after_tax_cost_of_debt'], capm['equity_weight'],
                                          capm['debt_weight']) if implied_w is not None else None)
    alpha = implied - required if implied is not None else None
    b_implied = sml.implied_beta(implied, rf, erp)

    a_cls = '' if alpha is None else ('pos' if alpha >= 0 else 'neg')
    ui.md('<div class="ix-metrics">'
          + ui.metric(t('Beta'), f'{beta:.2f}', escape(capm.get('beta_source') or ''), '', _help('Beta'))
          + ui.metric(t('Required return'), ui.pct(required),
                      t('{rf} + {b:.2f} × {erp}', rf=ui.pct(rf), b=beta, erp=ui.pct(erp)), 'model', _help('Required return'))
          + ui.metric(t('Implied return'), ui.pct(implied), t('at market price {mp}', mp=ui.usd(market_price)), '',
                      _help('Implied return'))
          + ui.metric(t('Alpha'), ui.pct(alpha, signed=True), t('implied − required'), a_cls, _help('Alpha'))
          + '</div>')

    pts = [beta, 1.0] + ([b_implied] if b_implied is not None else [])
    beta_max = min(max(2.0, max(pts) * 1.25), 4.0)
    xs, ys = sml.line(rf, erp, beta_max)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=[y * 100 for y in ys], mode='lines', name=t('Security Market Line'),
                             line=dict(color=T['text3'], width=2),
                             hovertemplate='β %{x:.2f}<br>' + t('Required return') + ' %{y:.2f}%<extra></extra>'))
    fig.add_trace(go.Scatter(x=[0, 1], y=[rf * 100, (rf + erp) * 100], mode='markers', name=t('Reference'),
                             marker=dict(size=9, color=T['market'], symbol='diamond'), cliponaxis=False,
                             text=[t('Risk-free'), t('Market')],
                             hovertemplate='%{text}<br>β %{x:.2f} · %{y:.2f}%<extra></extra>'))
    for x, y, label, anchor in ((0, rf, t('Risk-free'), 'left'), (1, rf + erp, t('Market'), 'right')):
        fig.add_annotation(x=x, y=y * 100, text=label, showarrow=False, xanchor=anchor, yanchor='bottom',
                           xshift=6 if anchor == 'left' else -6, yshift=4, font=dict(size=11, color=T['text2']))
    fig.add_trace(go.Scatter(x=[beta], y=[required * 100], mode='markers', name=t('Required return'),
                             marker=dict(size=13, color=T['model'], line=dict(color=T['bg'], width=2)),
                             hovertemplate=t('Required return') + '<br>β %{x:.2f} · %{y:.2f}%<extra></extra>'))
    if implied is not None:
        col = T['pos'] if alpha >= 0 else T['neg']
        fig.add_trace(go.Scatter(x=[beta, beta], y=[required * 100, implied * 100], mode='lines', showlegend=False,
                                 line=dict(color=col, width=2, dash='dot'), hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=[beta], y=[implied * 100], mode='markers', name=t('Implied return'),
                                 marker=dict(size=13, color=col, symbol='circle-open', line=dict(width=3)),
                                 hovertemplate=t('Implied return') + '<br>β %{x:.2f} · %{y:.2f}%<extra></extra>'))
        fig.add_annotation(x=beta, y=(required + implied) / 2 * 100, text=f'α {alpha * 100:+.2f}%', showarrow=False,
                           xanchor='left', xshift=10, font=dict(size=12, color=col, family="'IBM Plex Mono', monospace"))
    fig.update_layout(template='intrinsic', height=440, hovermode='closest', xaxis_title='Beta (β)',
                      yaxis_title=t('Expected return (%)'),
                      legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0))
    fig.update_xaxes(range=[0, beta_max], showgrid=True)
    fig.update_yaxes(ticksuffix='%', rangemode='tozero')
    _chart(fig, key='sml')
    if implied is None:
        st.caption(t('No implied return: the market price is outside the values the model produces for a discount rate '
                     'between terminal growth and 40%.'))
    else:
        verdict = (t('Above the line: at {mp} the stock offers more return than CAPM requires for its beta — it looks '
                     'undervalued for its risk.', mp=ui.usd(market_price)) if alpha >= 0 else
                   t('Below the line: at {mp} the stock offers less return than CAPM requires for its beta — it looks '
                     'overvalued for its risk.', mp=ui.usd(market_price)))
        st.caption(verdict + ' ' + t('Implied return = cost of equity that makes the DCF value equal the market price '
                                     '(implied WACC {w}, capital weights held at market values). The beta that would '
                                     'justify today\'s price is {bi:.2f}.', w=ui.pct(implied_w), bi=b_implied))


def _implied_wacc(ticker, data, scen, g, overrides, market_price, value_at):
    """Solve for the WACC that equates the DCF value to the market price (cached per inputs)."""
    br = data['bridge']
    key = (ticker, br['net_debt'], br['shares'], scen, round(g, 6),
           json.dumps(overrides or {}, sort_keys=True, default=str), round(market_price or 0, 4))
    cache = st.session_state.setdefault('ix_sml_cache', {})
    if key not in cache:
        cache[key] = sml.implied_wacc(value_at, market_price, lo=g + 0.0025, hi=0.40, tol=1e-5)
    return cache[key]


def _model_data(results, scen, data):
    ui.heading(t('Model & data'), t('What is validated, where each assumption comes from, and every data check'))
    note = _validation_note()
    ok_card = (f'<div class="ix-state-card info"><h4>{t("Validated out of sample")}</h4>'
               + t('Revenue and EBIT-margin forecasts passed <strong>{ok}/{n}</strong> pre-registered out-of-sample criteria '
                   '(fresh companies, parameters estimated with data ≤2018, forecasts 2019–2025).', ok=note[0], n=note[1])
               + '</div>') if note else ''
    ui.md('<div class="ix-status-grid">' + ok_card +
          f'<div class="ix-state-card"><h4>{t("Not validated")}</h4>'
          + t('What is NOT validated: CapEx, D&amp;A and working-capital paths (consistent by construction, not tested as '
              'forecasts) and the final valuation. Use the range, not a single number.') + '</div></div>')

    a = results[scen]['assumptions']
    ui.heading(t('Assumptions and where each comes from'))
    legend = ''.join(ui.tag(t(SOURCE_BADGE[k]), SOURCE_TAG_KIND[k]) + ' ' for k in SOURCE_BADGE)
    ui.md(f'<div style="margin:-2px 0 10px">{legend}</div>')
    body = []
    for k, x in a['drivers'].items():
        val = x['value']
        if isinstance(val, list):
            shown = ', '.join(f'{y:.3g}' for y in val[:5])
        elif is_number(val):
            shown = f'{val:.2%}' if abs(val) < 5 and k not in ('year0', 'rd_life') else f'{val:,.4g}'
        else:
            shown = str(val)
        src = x['source']
        body.append(('', [(f'<span class="ix-mono">{escape(k)}</span>', ''), (escape(shown), ''),
                          (ui.tag(t(SOURCE_BADGE.get(src, src)), SOURCE_TAG_KIND.get(src, 'plain')), 'code'),
                          (escape(str(x['note'])), 'wrap')]))
    ui.md(ui.html_table([t('Driver'), t('Value'), t('Source'), t('Explanation')], body, ['', '', 'l', 'l']))
    if lang() == 'es':
        st.caption(t('Explanations in this table come from the valuation engine and are shown in English.'))

    ui.heading(t('Data quality and consistency checks'))
    for b in a['blockers']:
        st.error(b)
    for d in a['degradations']:
        st.warning(d)
    notes = a.get('notes', [])
    checks = list(results[scen].get('checks', [])) + list(data.get('capital_flags', []))
    if not a['blockers'] and not a['degradations']:
        ui.md(f'<div class="ix-quality">{ui.tag(t("No blockers"), "pos")}{ui.tag(t("No degradations"), "pos")}'
              f'<span>{t("Required SEC inputs were found for this scenario.")}</span></div>')
    if notes:
        ui.md(f'<div class="ix-note"><div class="ix-label">{t("Notes")}</div><ul>'
              + ''.join(f'<li>{escape(str(n))}</li>' for n in notes) + '</ul></div>')
    if checks:
        ui.md(f'<div class="ix-note"><div class="ix-label">{t("Consistency checks and capital flags")}</div><ul>'
              + ''.join(f'<li>{escape(str(c))}</li>' for c in checks) + '</ul></div>')
    st.caption(t('Method: driver-based FCFF with panel-calibrated mean reversion (2,578 US companies), PP&E roll-forward, full '
                 'operating NWC, capitalised R&D and steady-state terminal reinvestment.'))


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def _blocked(title, body_html):
    ui.state_card(title, body_html, 'block')


def render_model_27(ticker, wacc, terminal_growth, market_price=None, market_shares=None, context=None):
    """Render the workspace. `context` (optional, presentation only) carries display metadata from app.py:
    slot (header container), price_source, price_mode, wacc_mode, g_changed, sic, industry."""
    ctx = context or {}
    try:
        with st.spinner(t('Loading SEC financial statements...')):
            data = _inputs(ticker)
    except DataUnavailable as exc:
        ui.state_card(t('Not enough SEC data to value this company'),
                      f'{escape(str(exc))}<br><br>' + t('Rather than fill gaps with guesses, Intrinsic does not produce a '
                                                        'value. Try another company, or one of the Top 25.'))
        return
    except Exception as exc:
        st.error(t('SEC financial data unavailable for {ticker}: {err}', ticker=ticker, err=exc))
        return
    if data['decision'].get('model') != 'fcff':
        st.error(t('Not valued with FCFF: {category} — {reason}', category=data['decision'].get('category'),
                   reason=data['decision'].get('reason')))
        return
    br = data['bridge']
    if not br['shares'] and market_shares:
        br['shares'] = float(market_shares)
        br['shares_source'] = 'market data (SEC reports shares by class only) — verify share class'
    if br['net_debt'] is None or not br['shares']:
        st.error(t('Valuation blocked: the debt, cash or share count could not be verified from SEC filings.'))
        return
    probe = dm.derive_assumptions(data['history'], wacc=wacc, terminal_growth=terminal_growth,
                                  calibration=dm.load_calibration(), rd_life=data['rd_life'],
                                  rd_life_note=data['rd_note'], industry_margin=data.get('industry_margin'))
    if probe['status'] == 'BLOCKED':
        st.error(t('Valuation blocked — required SEC data is missing:'))
        for b in probe['blockers']:
            st.write('• ' + b)
        return
    nav, pick = st.columns([3, 2], vertical_alignment='bottom')
    with nav:
        section = st.segmented_control(t('Dashboard section'),
                                       options=['Overview', 'Forecast', 'Valuation', 'Sensitivity', 'Risk & return',
                                                'Model & Data'],
                                       format_func=t, default='Overview', key='intrinsic_section_27',
                                       label_visibility='collapsed') or 'Overview'
    with pick:
        scen = st.segmented_control(t('Scenario'), SCENARIOS, default='base', format_func=scenario,
                                    key=f'm27_scenario_{ticker}', help=_term('Scenario')[1],
                                    label_visibility='collapsed') or 'base'
    overrides = _sidebar_inputs(ticker, probe)
    results = _run_all(data, wacc, terminal_growth, overrides)
    if ctx.get('slot') is not None:
        _company_strip(ctx['slot'], ctx, data, market_price, market_shares, results[scen]['status'])
    if 'valuation' not in results[scen]:
        err = str(results[scen].get('valuation_error', 'Valuation not available for this scenario.'))
        if 'Terminal NOPAT is not positive' in err:
            err = t('In this scenario the forecast never reaches a positive operating profit, so there is no going-concern terminal '
                    'value to discount: the company would be worth only its net cash. Try another scenario, or adjust the '
                    'long-run margin or the years to reach it under Forecast assumptions.')
        ui.state_card(t('Not valued in the {scen} scenario', scen=scenario(scen).lower()), escape(err))
        return
    status = results[scen]['status']
    if status == 'DEGRADED':
        st.warning(t('Some inputs are estimated or adjusted — see Model & Data for details.'))
    if overrides:
        names = {'growth_start': 'revenue growth', 'margin_target': 'long-run margin', 'intensity_target':
                 'fixed assets per $ of revenue', 'nwc_ratio_target': 'working capital', 'tax_terminal': 'tax rate',
                 'profit_years': 'years to target margin', 'failure_prob': 'probability of failure'}
        ui.md('<div class="ix-quality">' + ui.tag(t('Your case'), 'user') + '<span>'
              + t('You are viewing YOUR case: <b>{fields}</b> changed from model values. Use "Reset to model values" in the '
                  'sidebar to go back.', fields=escape(', '.join(t(names.get(k, k)) for k in overrides)))
              + '</span></div>')
    if section == 'Forecast':
        _forecast(results, scen, ticker, data)
    elif section == 'Valuation':
        _valuation(results, scen, data)
    elif section == 'Sensitivity':
        _sensitivity(data, scen, wacc, terminal_growth, overrides, market_price, ticker)
    elif section == 'Risk & return':
        _risk_return(ticker, scen, data, terminal_growth, overrides, market_price, ctx.get('capm'))
    elif section == 'Model & Data':
        _model_data(results, scen, data)
    else:
        _overview(results, scen, wacc, market_price, market_shares, data, terminal_growth, ctx)
    ui.footer()
