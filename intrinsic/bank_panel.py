"""Streamlit workspace for banks: excess-return model and dividend discount model side by side.

Presentation only: every number comes from intrinsic.bank_model / intrinsic.bank_inputs or from the
market and discount-rate inputs loaded here. Visual building blocks are shared with the FCFF workspace.
"""
from __future__ import annotations

import math
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from intrinsic import bank_model as bm
from intrinsic import sml
from intrinsic.bank_inputs import load_bank_inputs
from intrinsic.dashboard_panel import _chart, _glossary, _help, _waterfall
from intrinsic.industry_beta import load_industry_betas
from intrinsic.inputs import DataUnavailable
from intrinsic.sec_data import is_number
from intrinsic.ui import components as ui
from intrinsic.ui.i18n import lang, scenario, t
from intrinsic.ui.theme import HISTORY_COLOR, SCENARIO_COLORS, T

SCENARIOS = bm.SCENARIOS
MONEY_CENTER_ASSETS = 500e9     # above this, the Damodaran "Bank (Money Center)" beta applies; else regional
SOURCE_BADGE = {'data': 'Company data', 'calibrated': 'Calibrated (panel)',
                'assumption': 'Economic assumption', 'user': 'Your input'}
SOURCE_TAG_KIND = {'data': 'market', 'calibrated': 'model', 'assumption': 'warn', 'user': 'user'}
DRIVER_NAMES = {
    'cost_of_equity': 'Cost of equity', 'terminal_growth': 'Terminal growth', 'roe_start': 'ROE today',
    'roe_long': 'Long-run ROE', 'fade_speed': 'Fade speed', 'book_growth_start': 'Book value growth today',
    'payout_start': 'Payout ratio today', 'sustainable_growth': 'Sustainable growth today',
    'stable_payout': 'Stable payout ratio', 'normalized_earnings': 'Normalized earnings',
    'book_value': 'Common book value',
}


@st.cache_data(ttl=3600, show_spinner=False)
def _bank_inputs(ticker):
    return load_bank_inputs(ticker.replace('.', '-'))


@st.cache_data(ttl=900, show_spinner=False)
def _market(ticker):
    from intrinsic.market_data import obtener_mercado
    return obtener_mercado(ticker)


# ------------------------------------------------------------------
# Sidebar: cost of equity, growth, market price, bank assumptions
# ------------------------------------------------------------------

def _industry_beta(total_assets):
    betas = load_industry_betas()
    name = 'Bank (Money Center)' if is_number(total_assets) and total_assets >= MONEY_CENTER_ASSETS else 'Banks (Regional)'
    row = betas.get(name) or {}
    try:
        return name, float(row['levered_beta']), int(row['n_firms'])
    except (KeyError, TypeError, ValueError):
        return name, None, None


def _sidebar(ticker, data, market, rf_loader, erp_default, terminal_default):
    st.sidebar.subheader(t('Assumptions'))
    status = st.sidebar.container()
    box = st.sidebar.expander(t('Cost of equity (CAPM)'), expanded=False)
    rf_value, rf_source = rf_loader()
    rf = box.number_input(t('Risk-free rate (%)'), min_value=0.0, max_value=15.0, value=round(rf_value * 100, 2),
                          step=0.05, key='bank_rf', help=rf_source) / 100
    latest = data['history'][-1]
    ind_name, ind_beta, n_firms = _industry_beta(latest.get('Total assets'))
    raw = market.get('beta') if market else None
    blume = 0.67 * raw + 0.33 if is_number(raw) else None
    options = ['industry'] + (['regression'] if blume is not None else [])
    basis = box.selectbox(t('Beta basis'), options, key=f'bank_beta_basis_{ticker}',
                          format_func=lambda o: (t('Industry: {name} (levered)', name=ind_name) if o == 'industry'
                                                 else t('Stock regression (Blume-adjusted)')))
    default_beta = ind_beta if basis == 'industry' and is_number(ind_beta) else (blume or 1.0)
    beta_help = (t('Damodaran levered beta for {name} ({n} US firms, Jan 2026). For banks the levered beta is used '
                   'directly: deposits are operating liabilities, so un/re-levering with debt is not meaningful.',
                   name=ind_name, n=n_firms) if basis == 'industry'
                 else t('Yahoo regression beta {raw:.2f} with the Blume adjustment (0.67 × raw + 0.33).', raw=raw))
    beta = box.number_input(t('Beta'), min_value=0.1, max_value=3.0, value=float(round(default_beta, 2)), step=0.05,
                            key=f'bank_beta_{ticker}_{basis}', help=beta_help)
    erp_value, erp_source = erp_default
    erp = box.number_input(t('Equity risk premium (%)'), min_value=0.0, max_value=15.0, value=round(erp_value * 100, 2),
                           step=0.05, key='bank_erp', help=erp_source) / 100
    ke = sml.required_return(rf, beta, erp)
    box.markdown('<div class="ix-state">' + ui.kv_rows([(t('Risk-free rate'), ui.pct(rf)), ('Beta', f'{beta:.2f}'),
                                                        (t('Equity risk premium'), ui.pct(erp))],
                                                       total=(t('Cost of equity'), ui.pct(ke))) + '</div>',
                 unsafe_allow_html=True)
    g = box.number_input(t('Terminal growth (%)'), min_value=0.0, max_value=6.0, value=terminal_default * 100,
                         step=0.25, key=f'bank_g_{ticker}') / 100

    mbox = st.sidebar.expander(t('Market price & shares'), expanded=False)
    mode = mbox.radio(t('Market Data Mode'), ['Automatic', 'Manual Override'], format_func=t, horizontal=True,
                      key='bank_market_mode')
    price_auto = market.get('price') if market else None
    shares_auto = data['shares'] or (market.get('shares') if market else None)
    if mode == 'Automatic' and is_number(price_auto) and is_number(shares_auto):
        price, shares = float(price_auto), float(shares_auto)
        mbox.markdown('<div class="ix-state">' + ui.kv_rows([(t('Market price'), ui.usd(price)),
                                                             (t('Shares outstanding'), f'{shares / 1e9:,.3f} B')])
                      + '</div>', unsafe_allow_html=True)
        mbox.caption(t('Price: Yahoo Finance. Shares: {src}, {date}.', src=data['shares_source'] or 'Yahoo Finance',
                       date=data['shares_date'] or '—'))
        price_manual = False
    else:
        price = mbox.number_input(t('Market Price (USD)'), min_value=0.01, value=float(price_auto or 100.0), step=1.0,
                                  key=f'bank_price_{ticker}')
        shares = mbox.number_input(t('Shares Outstanding (shares)'), min_value=1.0, value=float(shares_auto or 1e9),
                                   step=1e6, key=f'bank_shares_{ticker}')
        price_manual = True

    abox = st.sidebar.expander(t('Bank assumptions'), expanded=False)
    probe = bm.derive_assumptions(data['history'], ke, g, 'base')['drivers']
    overrides = {}
    for key, label in (('roe_start', 'ROE today (%)'), ('roe_long', 'Long-run ROE (%)'),
                       ('payout_start', 'Payout ratio today (%)')):
        model_val = probe[key]['value'] * 100
        val = abox.number_input(t(label), value=round(model_val, 2), step=0.25, key=f'bank_{key}_{ticker}',
                                help=probe[key]['note'])
        if abs(val - round(model_val, 2)) > 1e-9:
            overrides[key] = val / 100
    abox.caption(t('Base-scenario model values. Editing one applies it to every scenario.'))
    if overrides and abox.button(t('Reset to model values'), key=f'bank_reset_{ticker}'):
        for key in ('roe_start', 'roe_long', 'payout_start'):
            st.session_state.pop(f'bank_{key}_{ticker}', None)
        st.rerun()

    status.markdown('<div class="ix-state">' + ui.kv_rows([
        (t('Cost of equity'), f'{ui.tag(t("Auto"), "model")}&nbsp; {ui.pct(ke)}'),
        (t('Market price'), f'{ui.tag(t("Manual") if price_manual else t("Auto"), "user" if price_manual else "model")}'
                            f'&nbsp; {ui.usd(price)}'),
        (t('Terminal growth'), ui.pct(g)),
    ]) + '</div>', unsafe_allow_html=True)
    capm = {'risk_free_rate': rf, 'beta': beta, 'equity_risk_premium': erp,
            'beta_source': ind_name if basis == 'industry' else t('stock regression (Blume)')}
    return ke, g, price, shares, price_manual, overrides, capm


# ------------------------------------------------------------------
# Sections
# ------------------------------------------------------------------

def _strip(slot, data, price, shares, ctx):
    latest = data['history'][-1]
    cells = [(t('Market price · USD'), ui.usd(price), escape(ctx.get('price_source', ''))),
             (t('Market cap'), ui.usd_b(price * shares), t('price × shares outstanding')),
             (t('Total assets'), ui.usd_b(latest.get('Total assets'), 0), 'SEC EDGAR'),
             (t('Deposits'), ui.usd_b(latest.get('Deposits'), 0), 'SEC EDGAR'),
             (t('Financials'), f"FY{data['history'][0]['Fiscal year end'][:4]}–FY{latest['Fiscal year end'][:4]}",
              t('{n} 10-K years · FYE {fye}', n=len(data['history']), fye=escape(latest['Fiscal year end']))),
             (t('Industry (SIC)'), escape(str(data.get('sic') or '—')), escape(str(data.get('sic_description') or '')))]
    slot.markdown('<div class="ix-strip">' + ''.join(
        f'<div><span>{k}</span><b>{v}</b><small>{f}</small></div>' for k, v, f in cells) + '</div>',
        unsafe_allow_html=True)


def _overview(res, scen, price, data, ke, g):
    r = res[scen]
    ri, ddm = r['excess_return']['per_share'], r['ddm']['per_share']
    mid = r['midpoint']
    up = (mid / price - 1) * 100
    cls = 'pos' if up >= 0 else 'neg'
    mids = {s: res[s].get('midpoint') for s in SCENARIOS}
    ui.md(f"""
    <div class="ix-hero">
      <div class="ix-hero-top">
        <div class="ix-hero-cell">{ui.tag(t('Excess return · {scen}', scen=scenario(scen).lower()), 'model')}
          <div class="ix-big model">{ui.usd(ri)}</div>
          <div class="ix-big-sub">{t('Book value + PV of returns above the cost of equity')} {_help('Excess return model')}</div></div>
        <div class="ix-hero-cell">{ui.tag(t('Dividend discount · {scen}', scen=scenario(scen).lower()), 'model')}
          <div class="ix-big model">{ui.usd(ddm)}</div>
          <div class="ix-big-sub">{t('PV of dividends + buybacks to common shareholders')} {_help('Dividend discount model')}</div></div>
        <div class="ix-hero-cell">{ui.tag(t('Implied'), 'plain')}
          <div class="ix-big {cls}">{'+' if up >= 0 else '−'}{abs(up):.1f}%</div>
          <div class="ix-big-sub">{t('Midpoint {mid} vs market price {mp}', mid=ui.usd(mid), mp=ui.usd(price))}</div></div>
      </div>
      <div class="ix-range"><div class="ix-label">{t('Valuation range vs market price (midpoint of both models)')}</div>
        {ui.range_bar(mids, price, scen)}</div>
    </div>""")
    latest = data['history'][-1]
    pb_mkt = price / r['book_value_per_share'] if r['book_value_per_share'] > 0 else None
    ui.md('<div class="ix-metrics">'
          + ui.metric(t('Book value / share'), ui.usd(r['book_value_per_share']), t('common equity · SEC'), '',
                      _help('Book value'))
          + ui.metric(t('Justified P/B'), f"{r['justified_pb']:.2f}×", t('market P/B {pb:.2f}×', pb=pb_mkt or 0), 'model',
                      _help('Justified P/B'))
          + ui.metric(t('Cost of equity'), ui.pct(ke), t('CAPM'), '', _help('Cost of equity'))
          + ui.metric('ROE', ui.pct(latest.get('ROE')), t('latest year'), '', _help('ROE'))
          + ui.metric(t('Long-run ROE'), ui.pct(r['assumptions']['drivers']['roe_long']['value']), escape(scenario(scen)),
                      'model', _help('Long-run ROE'))
          + ui.metric(t('Model gap'), ui.pct(r['model_gap'], 1, signed=True), t('DDM vs excess return'), '',
                      _help('Model gap'))
          + '</div>')
    d = r['assumptions']['drivers']
    spread = d['roe_long']['value'] - ke
    verdict = (t('The bank is expected to keep earning <b>{s} above</b> its cost of equity in the long run, so it is worth '
                 'more than its book value.', s=ui.pct(spread)) if spread > 0.0005 else
               t('In the long run the bank earns only its cost of equity, so growth adds no value and the price converges '
                 'to book value.'))
    ui.md(f'<div class="ix-note"><div class="ix-label">{t("What this means")}</div><ul>'
          f'<li>{verdict}</li>'
          f'<li>{t("<b>Two models, one range.</b> With perfectly consistent inputs both give the same value. Here the excess-return model follows book value and ROE, while the DDM follows the bank&#39;s actual payout policy; a large gap means today&#39;s payout and growth differ from what the ROE path implies.")}</li>'
          f'<li>{t("<b>Why not FCFF:</b> deposits and borrowings are a bank&#39;s raw material, not financing, so free cash flow to the firm and WACC do not apply. Both models discount at the cost of equity.")}</li>'
          '</ul></div>')


def _forecast(res, scen, data, ke):
    ui.heading(t('Return on equity: history and forecast'),
               t('Fades from today\'s level to the long-run level; the dotted line is the cost of equity'))
    _glossary(['ROE', 'Long-run ROE', 'Cost of equity'])
    hist = [(int(r['Fiscal year end'][:4]), r['ROE']) for r in data['history'] if is_number(r.get('ROE'))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[x for x, _ in hist], y=[y * 100 for _, y in hist], mode='lines+markers',
                             name=t('Reported'), line=dict(color=HISTORY_COLOR, width=2)))
    y0 = res[scen]['assumptions']['year0']
    for s in SCENARIOS:
        if res[s]['status'] != 'OK':
            continue
        rows = res[s]['excess_return']['rows']
        fig.add_trace(go.Scatter(x=[y0] + [r['year'] for r in rows],
                                 y=[hist[-1][1] * 100] + [r['roe'] * 100 for r in rows], mode='lines',
                                 name=scenario(s), line=dict(color=SCENARIO_COLORS[s], width=3 if s == scen else 1.5,
                                                             dash='solid' if s == scen else 'dot')))
    fig.add_hline(y=ke * 100, line=dict(color=T['warn'], width=1, dash='dot'),
                  annotation_text=t('Cost of equity {ke}', ke=ui.pct(ke)), annotation_position='bottom right',
                  annotation_font=dict(size=10, color=T['warn']))
    fig.add_vline(x=y0 + 0.5, line=dict(color=T['line_strong'], width=1, dash='dot'))
    fig.update_layout(template='intrinsic', height=380, yaxis_title='ROE (%)', hovermode='x unified',
                      legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0))
    fig.update_yaxes(ticksuffix='%')
    _chart(fig, key='bank-roe')

    r = res[scen]
    rows = r['excess_return']['rows']
    ddm_rows = r['ddm']['rows']
    head = [t('Year')] + [str(x['year']) for x in rows]

    def line(label, vals, fmt):
        return ('', [(t(label), '')] + [(fmt(v), '') for v in vals])
    b = lambda v: f'{v / 1e9:,.1f}'
    p = lambda v: f'{v * 100:.1f}%'
    body = [line('ROE', [x['roe'] for x in rows], p),
            line('Book value, start (USD B)', [x['book_begin'] for x in rows], b),
            line('Net income to common (USD B)', [x['net_income'] for x in rows], b),
            line('Excess return (USD B)', [x['excess_return'] for x in rows], b),
            line('PV of excess return (USD B)', [x['pv'] for x in rows], b),
            line('DDM: earnings growth', [x['growth'] for x in ddm_rows], p),
            line('DDM: payout ratio', [x['payout_ratio'] for x in ddm_rows], p),
            line('DDM: dividends + buybacks (USD B)', [x['payout'] for x in ddm_rows], b),
            line('DDM: present value (USD B)', [x['pv'] for x in ddm_rows], b)]
    ui.heading(t('10-year projection · {scen}', scen=escape(scenario(scen))))
    ui.md(ui.html_table(head, body))


def _valuation(res, scen, data):
    r = res[scen]
    ri, ddm = r['excess_return'], r['ddm']
    ui.heading(t('Valuation bridge · {scen}', scen=escape(scenario(scen))),
               t('From book value to equity value, and from payouts to equity value'))
    _glossary(['Excess return model', 'Dividend discount model', 'Terminal value', 'Justified P/B'])
    c1, c2 = st.columns(2)
    with c1:
        _waterfall([t('Book value'), t('PV excess returns'), t('PV terminal'), t('Equity value')],
                   [ri['book_value'] / 1e9, ri['pv_excess'] / 1e9, ri['pv_terminal'] / 1e9, ri['equity_value'] / 1e9],
                   ['absolute', 'relative', 'relative', 'total'], 'Excess return model (USD B)')
    with c2:
        _waterfall([t('PV dividends + buybacks'), t('PV terminal'), t('Equity value')],
                   [ddm['pv_payouts'] / 1e9, ddm['pv_terminal'] / 1e9, ddm['equity_value'] / 1e9],
                   ['absolute', 'relative', 'total'], 'Dividend discount model (USD B)')
    sh = r['shares']
    rows = [(t('Equity value'), ui.usd_b(ri['equity_value']), ui.usd_b(ddm['equity_value'])),
            (t('Terminal value share'), f"{ri['pv_terminal'] / ri['equity_value']:.0%}",
             f"{ddm['pv_terminal'] / ddm['equity_value']:.0%}"),
            (t('Shares'), f'{sh / 1e9:,.3f} B', f'{sh / 1e9:,.3f} B'),
            (t('Value per share'), f"<b>{ui.usd(ri['per_share'])}</b>", f"<b>{ui.usd(ddm['per_share'])}</b>"),
            (t('Implied P/B'), f"{ri['equity_value'] / ri['book_value']:.2f}×",
             f"{ddm['equity_value'] / ri['book_value']:.2f}×")]
    ui.md(ui.html_table(['', t('Excess return'), t('Dividend discount')],
                        [('', [(k, ''), (a, ''), (b, '')]) for k, a, b in rows]))


def _sensitivity(data, scen, ke, g, shares, overrides, price, ticker):
    ui.heading(t('Cost of equity × terminal growth sensitivity'),
               t('{scen} scenario · value per share and upside vs market price', scen=escape(scenario(scen))))
    model = st.segmented_control(t('Model'), ['excess_return', 'ddm'], default='excess_return',
                                 format_func=lambda m: t('Excess return') if m == 'excess_return' else t('Dividend discount'),
                                 key='bank_sens_model') or 'excess_return'
    kes = [ke + d for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    gs = [g + d for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    matrix = []
    for k in kes:
        row = []
        for gg in gs:
            out = bm.run(data['history'], k, gg, shares, scen, overrides) if k > gg and gg >= 0 else None
            row.append(out[model]['per_share'] if out and out['status'] == 'OK' else float('nan'))
        matrix.append(row)
    text = [[(f'<b>${x:,.0f}</b><br>{(x / price - 1) * 100:+.0f}%' if not math.isnan(x) else 'N/A') for x in r]
            for r in matrix]
    xl, yl = [f'{x * 100:.2f}%' for x in gs], [f'{k * 100:.2f}%' for k in kes]
    fig = go.Figure(go.Heatmap(z=matrix, x=xl, y=yl, colorscale=[[0, '#7A2E38'], [0.5, T['surface2']], [1, '#1F6B4A']],
                               zmid=price, text=text, texttemplate='%{text}', xgap=2, ygap=2,
                               textfont=dict(color=T['text'], family="'IBM Plex Mono', monospace", size=12),
                               hovertemplate='g %{x}<br>Ke %{y}<br>%{text}<extra></extra>',
                               colorbar=dict(title=dict(text='$/share', font=dict(size=11)), thickness=10,
                                             outlinewidth=0, tickfont=dict(size=10))))
    fig.add_shape(type='rect', xref='x', yref='y', x0=1.5, x1=2.5, y0=1.5, y1=2.5, line=dict(color=T['text'], width=1.5))
    fig.update_layout(template='intrinsic', xaxis_title=t('Terminal growth'), yaxis_title=t('Cost of equity'), height=430,
                      hovermode='closest')
    fig.update_xaxes(side='top', showgrid=False)
    fig.update_yaxes(autorange='reversed', showgrid=False)
    _chart(fig, key='bank-sensitivity')
    st.caption(t('Colour midpoint = market price (${mp:,.2f}). Outlined cell = current inputs. N/A = cost of equity not '
                 'above growth, or long-run ROE not above growth.', mp=price))
    export = pd.DataFrame(matrix, index=yl, columns=xl)
    export.index.name = 'Cost of equity / Terminal growth'
    st.download_button(t('Download Sensitivity CSV'), export.to_csv(),
                       file_name=f'intrinsic_{ticker.lower()}_bank_sensitivity_{model}_{scen}.csv', mime='text/csv')


def _risk_return(data, scen, g, shares, overrides, price, capm):
    ui.heading(t('Security Market Line'),
               t('{scen} scenario · CAPM required return vs the return implied by the market price',
                 scen=escape(scenario(scen))))
    _glossary(['Security Market Line', 'Beta', 'Required return', 'Implied return', 'Alpha'])
    rf, beta, erp = capm['risk_free_rate'], capm['beta'], capm['equity_risk_premium']
    required = sml.required_return(rf, beta, erp)

    def value_at(k):
        out = bm.run(data['history'], k, g, shares, scen, overrides)
        return out['excess_return']['per_share'] if out['status'] == 'OK' else None

    implied = sml.implied_wacc(value_at, price, lo=g + 0.0025, hi=0.40, tol=1e-5)
    alpha = implied - required if implied is not None else None
    b_implied = sml.implied_beta(implied, rf, erp)
    a_cls = '' if alpha is None else ('pos' if alpha >= 0 else 'neg')
    ui.md('<div class="ix-metrics">'
          + ui.metric(t('Beta'), f'{beta:.2f}', escape(capm.get('beta_source') or ''), '', _help('Beta'))
          + ui.metric(t('Required return'), ui.pct(required),
                      t('{rf} + {b:.2f} × {erp}', rf=ui.pct(rf), b=beta, erp=ui.pct(erp)), 'model', _help('Required return'))
          + ui.metric(t('Implied return'), ui.pct(implied), t('at market price {mp}', mp=ui.usd(price)), '',
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
                      yaxis_title=t('Expected return (%)'), legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0))
    fig.update_xaxes(range=[0, beta_max], showgrid=True)
    fig.update_yaxes(ticksuffix='%', rangemode='tozero')
    _chart(fig, key='bank-sml')
    if implied is None:
        st.caption(t('No implied return: the market price is outside the values the excess-return model produces for a '
                     'cost of equity between terminal growth and 40%.'))
    else:
        verdict = (t('Above the line: at {mp} the stock offers more return than CAPM requires for its beta — it looks '
                     'undervalued for its risk.', mp=ui.usd(price)) if alpha >= 0 else
                   t('Below the line: at {mp} the stock offers less return than CAPM requires for its beta — it looks '
                     'overvalued for its risk.', mp=ui.usd(price)))
        st.caption(verdict + ' ' + t('Implied return = cost of equity at which the excess-return value equals the market '
                                     'price. The beta that would justify today\'s price is {bi:.2f}.', bi=b_implied))


def _final_verdict(ticker, res, price, ke):
    from intrinsic.verdict_panel import render_verdict
    prices = {s: res[s].get('midpoint') for s in SCENARIOS}
    b = res['base']
    if b['status'] != 'OK':
        ui.state_card(t('No verdict'), t('The base scenario is not valued, so there is no verdict.'))
        return
    d = b['assumptions']['drivers']
    pb_mkt = price / b['book_value_per_share'] if b['book_value_per_share'] > 0 else None
    reasons = [
        t('<strong>Value vs price:</strong> base value {v} (midpoint of both models) against a market price of {p} '
          '({u:+.0%}).', v=ui.usd(b['midpoint']), p=ui.usd(price), u=b['midpoint'] / price - 1),
        t('<strong>Price to book:</strong> the market pays {m:.2f}× book value; the model justifies {j:.2f}×.',
          m=pb_mkt or 0, j=b['justified_pb']),
        t('<strong>Biggest assumption:</strong> long-run ROE of {r:.1%} against a {k:.1%} cost of equity.',
          r=d['roe_long']['value'], k=ke),
        t('<strong>Model agreement:</strong> the dividend model is {g:+.0%} from the excess-return model.',
          g=b['model_gap'] or 0),
    ]
    render_verdict(prices, price, reasons, f'bank-{ticker}', _chart)


def _model_data(res, scen, data):
    ui.heading(t('Model & data'), t('Where each assumption comes from, and the SEC history behind it'))
    ui.md(f'<div class="ix-state-card"><h4>{t("Not validated")}</h4>'
          + t('The bank engine has not been backtested out of sample yet (the FCFF model has). Fade speed and scenario '
              'rules are economic assumptions. Use the range, not a single number.') + '</div>')
    a = res[scen]['assumptions']
    ui.heading(t('Assumptions and where each comes from'))
    legend = ''.join(ui.tag(t(SOURCE_BADGE[k]), SOURCE_TAG_KIND[k]) + ' ' for k in SOURCE_BADGE)
    ui.md(f'<div style="margin:-2px 0 10px">{legend}</div>')
    body = []
    for k, x in a['drivers'].items():
        v = x['value']
        shown = '—' if v is None else (f'${v / 1e9:,.1f} B' if abs(v) > 1e6 else
                                       (f'{v:.2f}' if k == 'fade_speed' else f'{v:.2%}'))
        body.append(('', [(escape(t(DRIVER_NAMES.get(k, k))), ''), (shown, ''),
                          (ui.tag(t(SOURCE_BADGE.get(x['source'], x['source'])),
                                  SOURCE_TAG_KIND.get(x['source'], 'plain')), 'code'),
                          (escape(str(x['note'])), 'wrap')]))
    ui.md(ui.html_table([t('Driver'), t('Value'), t('Source'), t('Explanation')], body, ['', '', 'l', 'l']))
    if lang() == 'es':
        st.caption(t('Explanations in this table come from the valuation engine and are shown in English.'))

    ui.heading(t('SEC history (USD B unless noted)'))
    keys = [('Net income to common', 'b'), ('Common equity', 'b'), ('Tangible common equity', 'b'), ('ROE', 'p'),
            ('ROTCE', 'p'), ('Common dividends', 'b'), ('Buybacks', 'b'), ('Payout ratio', 'p'),
            ('Net interest income', 'b'), ('Noninterest income', 'b'), ('Credit provisions', 'b'),
            ('Total assets', 'b'), ('Deposits', 'b'), ('Diluted EPS', 'u')]
    hist = data['history']
    fmt = {'b': lambda v: f'{v / 1e9:,.1f}', 'p': lambda v: f'{v * 100:.1f}%', 'u': lambda v: f'${v:,.2f}'}
    body = [('', [(t(k), '')] + [((fmt[f](r[k]) if is_number(r.get(k)) else '—'), '') for r in hist]) for k, f in keys]
    ui.md(ui.html_table([''] + [r['Fiscal year end'][:4] for r in hist], body))
    notes = list(data.get('warnings', [])) + [f'{k}: {v}' for k, v in sorted(data.get('provenance', {}).items())]
    ui.md(f'<div class="ix-note"><div class="ix-label">{t("SEC tags and data notes")}</div><ul>'
          + ''.join(f'<li>{escape(n)}</li>' for n in notes) + '</ul></div>')
    st.caption(t('Method: excess-return (residual income) model and two-stage dividend discount model on total payout, '
                 'both discounted at the CAPM cost of equity; ROE fades from its recent level to its long-run level.'))


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def render_bank(ticker, header_slot, rf_loader, erp_default, terminal_default):
    try:
        with st.spinner(t('Loading SEC financial statements...')):
            data = _bank_inputs(ticker)
    except DataUnavailable as exc:
        ui.state_card(t('Not enough SEC data to value this company'), escape(str(exc)))
        return
    except Exception as exc:
        st.error(t('SEC financial data unavailable for {ticker}: {err}', ticker=ticker, err=exc))
        return
    try:
        market = _market(ticker)
    except Exception:
        market = {}
    ke, g, price, shares, price_manual, overrides, capm = _sidebar(ticker, data, market, rf_loader, erp_default,
                                                                    terminal_default)
    res = bm.run_all(data['history'], ke, g, shares, overrides)
    _strip(header_slot, data, price, shares,
           {'price_source': t('Manual input') if price_manual else 'Yahoo Finance'})
    nav, pick = st.columns([3, 2], vertical_alignment='bottom')
    with nav:
        section = st.segmented_control(t('Dashboard section'),
                                       options=['Overview', 'Forecast', 'Valuation', 'Sensitivity', 'Risk & return',
                                                'Final verdict', 'Model & Data'],
                                       format_func=t, default='Overview', key='intrinsic_section_27',
                                       label_visibility='collapsed') or 'Overview'
    with pick:
        scen = st.segmented_control(t('Scenario'), SCENARIOS, default='base', format_func=scenario,
                                    key=f'bank_scenario_{ticker}', label_visibility='collapsed') or 'base'
    if res[scen]['status'] != 'OK':
        ui.state_card(t('Valuation blocked'), '<br>'.join(escape(b) for b in res[scen]['assumptions']['blockers']))
        return
    if overrides:
        ui.md('<div class="ix-quality">' + ui.tag(t('Your case'), 'user') + '<span>'
              + t('You are viewing YOUR case: bank assumptions changed from model values.') + '</span></div>')
    if section == 'Forecast':
        _forecast(res, scen, data, ke)
    elif section == 'Valuation':
        _valuation(res, scen, data)
    elif section == 'Sensitivity':
        _sensitivity(data, scen, ke, g, shares, overrides, price, ticker)
    elif section == 'Risk & return':
        _risk_return(data, scen, g, shares, overrides, price, capm)
    elif section == 'Final verdict':
        _final_verdict(ticker, res, price, ke)
    elif section == 'Model & Data':
        _model_data(res, scen, data)
    else:
        _overview(res, scen, price, data, ke, g)
    ui.footer()
