"""Intrinsic 27 — full Streamlit workspace for the integrated driver model.

Keeps the original dashboard experience (Overview · Forecast · Valuation ·
Sensitivity, KPI cards, "?" definitions, waterfall bridge, WACC × g heatmap,
editable inputs) and adds the Model 27 outputs: three validated-uncertainty
scenarios, DCF vs market chart, value build-up and a Model & Data tab.
"""
from __future__ import annotations

import json
import math
import os
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import driver_forecast_27 as dm
from run_driver_27 import load_inputs
from sec_annual_27 import is_number

HERE = os.path.dirname(os.path.abspath(__file__))
SCENARIOS = ('conservative', 'base', 'optimistic')
SOURCE_BADGE = {'data': '🟦 Company data', 'calibrated': '🟩 Calibrated (panel)',
                'assumption': '🟨 Economic assumption', 'user': '🟥 Your input'}
COLORS = {'conservative': '#ff6b6b', 'base': '#4da3ff', 'optimistic': '#36c5a0', 'market': '#fbbf24'}

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
}


def _help(term, explanation=None):
    text = escape(explanation or GLOSSARY.get(term, ''))
    return (f'<span class="intrinsic-help" tabindex="0" role="note" aria-label="{escape(term)}: {text}">'
            f'?<span class="intrinsic-tip" role="tooltip">{text}</span></span>')


def _glossary(terms):
    st.markdown('<div class="intrinsic-glossary">' + ''.join(
        f'<span class="intrinsic-glossary-item">{t}{_help(t)}</span>' for t in terms) + '</div>',
        unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def _inputs(ticker):
    data = load_inputs(ticker.replace('.', '-'))
    data['decision'] = vars(data['decision'])
    return data


def _validation_note():
    path = os.path.join(HERE, 'final_validation_27.json')
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        rep = json.load(fh)
    v = rep.get('verdict', {})
    return sum(1 for x in v.values() if x.get('pass')), len(v)


# ------------------------------------------------------------------
# Editable inputs (plain language) -> driver overrides
# ------------------------------------------------------------------

def _sidebar_inputs(ticker, probe):
    d = probe['drivers']
    v = {k: x['value'] for k, x in d.items()}
    phi, gT = v['growth_fade'], v['terminal_growth']
    year1 = gT + (v['growth_start'] - gT) * phi        # what the user actually sees for next year
    overrides = {}
    st.sidebar.divider()
    st.sidebar.subheader('Your assumptions')
    st.sidebar.caption('Pre-filled with Model 27 values. Change any number to run your own case; '
                       'changed inputs are labelled "Your input".')
    if st.sidebar.button('Reset to model values', key=f'm27_reset_{ticker}'):
        for k in list(st.session_state):
            if k.startswith(f'm27_in_{ticker}_'):
                del st.session_state[k]
    fields = (
        ('year1', 'Revenue growth next year (%)', year1,
         'Model estimate for next year. Growth then slows toward the terminal rate at the calibrated speed.'),
        ('margin_target', 'Long-run EBIT margin (%)', v.get('margin_target'),
         'Operating margin the business converges to. Default: median of the company\'s prior 9 years.'),
        ('intensity_target', 'Fixed assets per $ of revenue (%)', v.get('intensity_target'),
         'Net PP&E / revenue in the long run. Higher = more capital-intensive = more CapEx to grow.'),
        ('nwc_ratio_target', 'Working capital % of revenue (%)', v.get('nwc_ratio_target'),
         'Operating working capital / revenue. Negative values mean suppliers/customers finance growth.'),
        ('tax_terminal', 'Long-run tax rate (%)', v.get('tax_terminal'),
         'Tax rate the company converges to by year 10 (US statutory 21% + ~4% state by default).'),
    )
    for key, label, default, help_text in fields:
        if not is_number(default):
            continue
        val = st.sidebar.number_input(label, value=float(round(default * 100, 2)), step=0.5, help=help_text,
                                      key=f'm27_in_{ticker}_{key}') / 100
        if abs(val - round(default, 4)) > 1e-6:
            if key == 'year1':
                overrides['growth_start'] = gT + (val - gT) / max(phi, 1e-6)
            else:
                overrides[key] = val
    return overrides


def _run_all(data, wacc, g, overrides):
    br = data['bridge']
    return {s: dm.run(data['history'], wacc=wacc, terminal_growth=g, net_debt=br['net_debt'], shares=br['shares'],
                      scenario=s, overrides=overrides or None, rd_life=data['rd_life'], rd_life_note=data['rd_note'])
            for s in SCENARIOS}


def _price(res):
    v = res.get('valuation')
    return v['intrinsic_price'] if v else None


# ------------------------------------------------------------------
# Sections
# ------------------------------------------------------------------

def _overview(results, scen, wacc, market_price, market_shares, data):
    st.markdown('<div class="intrinsic-section-label">01 / VALUATION SNAPSHOT</div>', unsafe_allow_html=True)
    st.markdown('<div class="intrinsic-dashboard-heading">DCF value vs market price</div>', unsafe_allow_html=True)
    st.markdown('<div class="intrinsic-dashboard-sub">Model 27 · 10-year FCFF forecast · '
                f'{scen.capitalize()} scenario selected</div>', unsafe_allow_html=True)
    val = results[scen]['valuation']
    price = val['intrinsic_price']
    upside = (price / market_price - 1) * 100 if market_price else 0.0
    cls = 'positive' if upside >= 0 else 'negative'
    st.markdown(f"""
    <div class="intrinsic-kpi-grid">
      <div class="intrinsic-kpi primary"><div class="label">INTRINSIC VALUE / SHARE {_help('Intrinsic value')}</div><div class="value">${price:,.2f}</div><div class="foot">{scen.capitalize()} scenario</div></div>
      <div class="intrinsic-kpi"><div class="label">MARKET PRICE / SHARE {_help('Market price')}</div><div class="value">${market_price:,.2f}</div><div class="foot">Selected market reference</div></div>
      <div class="intrinsic-kpi"><div class="label">UPSIDE / DOWNSIDE {_help('Upside / downside')}</div><div class="value {cls}">{upside:+.1f}%</div><div class="foot">Not a recommendation</div></div>
      <div class="intrinsic-kpi"><div class="label">DISCOUNT RATE / WACC {_help('WACC')}</div><div class="value">{wacc * 100:.2f}%</div><div class="foot">Selected capital cost</div></div>
    </div>""", unsafe_allow_html=True)

    # DCF range vs market ("football field")
    prices = {s: _price(results[s]) for s in SCENARIOS}
    fig = go.Figure()
    lo, hi = prices['conservative'], prices['optimistic']
    if lo is not None and hi is not None:
        fig.add_trace(go.Bar(y=['DCF range'], x=[hi - lo], base=[lo], orientation='h', marker_color='#334155',
                             name='Conservative → optimistic', hovertemplate='$%{base:,.2f} – $%{x:,.2f}<extra></extra>'))
    for s in SCENARIOS:
        if prices[s] is not None:
            fig.add_trace(go.Scatter(y=['DCF range'], x=[prices[s]], mode='markers+text', name=s.capitalize(),
                                     marker=dict(size=16, color=COLORS[s], symbol='diamond'),
                                     text=[f'${prices[s]:,.0f}'], textposition='top center'))
    fig.add_vline(x=market_price, line=dict(color=COLORS['market'], width=3, dash='dash'),
                  annotation_text=f'Market ${market_price:,.2f}', annotation_position='bottom right')
    fig.update_layout(template='plotly_dark', height=230, margin=dict(l=10, r=10, t=30, b=10),
                      xaxis_title='USD per share', legend=dict(orientation='h', y=-0.45))
    st.plotly_chart(fig, use_container_width=True)

    if hi is not None and market_price > hi:
        verdict = (f'The market price (${market_price:,.2f}) is ABOVE even the optimistic scenario (${hi:,.2f}): '
                   'the market expects more growth, margin or longer-lasting advantages than the model\'s optimistic case.')
    elif lo is not None and market_price < lo:
        verdict = (f'The market price (${market_price:,.2f}) is BELOW even the conservative scenario (${lo:,.2f}): '
                   'the market is more pessimistic than the model\'s conservative case.')
    else:
        verdict = (f'The market price (${market_price:,.2f}) is INSIDE the model\'s range '
                   f'(${lo:,.2f} – ${hi:,.2f}): the market\'s expectations are consistent with the model\'s uncertainty.')
    share = val['terminal_share_of_ev']
    st.markdown('<div class="intrinsic-insight"><div class="intrinsic-insight-title">VALUATION INSIGHTS</div>'
                f'<strong>Market comparison:</strong> {verdict}<br>'
                f'<strong>Terminal value:</strong> {share:.0%} of enterprise value comes from cash flows after year 10.<br>'
                '<strong>How to read the range:</strong> conservative/optimistic come from the model\'s measured '
                'forecast errors (20th/80th percentile), not from arbitrary ±%.</div>', unsafe_allow_html=True)
    with st.expander('Market data & capital structure'):
        br = data['bridge']
        if market_shares:
            st.write(f'Market capitalization: ${market_price * market_shares / 1e9:,.2f} B')
        st.write(f"Net debt used: ${br['net_debt'] / 1e9:,.2f} B (negative = net cash)")
        st.write(f"Shares used: {br['shares']:,.0f} — {br['shares_source']}")
        st.write(f"SEC balance date: {br['balance_date']}")


def _forecast(results, scen, ticker):
    st.subheader('Financial Forecast')
    _glossary(['Revenue growth', 'EBIT', 'NOPAT', 'D&A', 'CapEx', 'Change in NWC', 'FCFF', 'ROIC', 'Reinvestment rate'])
    st.caption(f'{scen.capitalize()} scenario · years 1–5 are the forecast period; years 6–10 complete the fade '
               'to steady state before the terminal value. Figures in USD millions.')
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
    st.dataframe(df.round(1), hide_index=True, use_container_width=True)
    st.download_button('Download forecast CSV', df.to_csv(index=False),
                       file_name=f'intrinsic_{ticker.lower()}_forecast_{scen}.csv', mime='text/csv')
    left, right = st.columns(2)
    with left:
        st.subheader('Revenue Projection')
        fig = go.Figure()
        for s in SCENARIOS:
            p = results[s].get('projection')
            if p:
                fig.add_trace(go.Scatter(x=[r['year'] for r in p['rows']], y=[r['revenue'] / 1e9 for r in p['rows']],
                                         mode='lines+markers', name=s.capitalize(),
                                         line=dict(color=COLORS[s], width=4 if s == scen else 2)))
        fig.update_layout(template='plotly_dark', xaxis_title='Fiscal Year', yaxis_title='USD Billions', height=350,
                          legend=dict(orientation='h', y=-0.25))
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader('Free Cash Flow Forecast')
        fig = go.Figure(go.Bar(x=[r['year'] for r in rows], y=[r['fcff'] / 1e9 for r in rows],
                               marker_color=COLORS[scen], name='FCFF'))
        fig.update_layout(template='plotly_dark', xaxis_title='Fiscal Year', yaxis_title='USD Billions', height=350)
        st.plotly_chart(fig, use_container_width=True)


def _waterfall(labels, values, measures, title):
    fig = go.Figure(go.Waterfall(
        orientation='v', measure=measures, x=labels, y=values,
        text=[f'${abs(v):,.1f} B' for v in values], textposition='outside',
        connector={'line': {'color': '#64748b'}}, increasing={'marker': {'color': '#36c5a0'}},
        decreasing={'marker': {'color': '#ff6b6b'}}, totals={'marker': {'color': '#4da3ff'}}))
    fig.update_layout(template='plotly_dark', title=title, yaxis_title='USD Billions', height=460, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def _valuation(results, scen, data):
    st.subheader('DCF Valuation Breakdown')
    _glossary(['PV of FCFF', 'Terminal value', 'Enterprise value', 'Net debt', 'Equity value', 'Intrinsic value'])
    res, br = results[scen], data['bridge']
    v, t = res['valuation'], res['valuation']['terminal']
    st.dataframe(pd.DataFrame({
        'Metric': ['PV of Forecast FCFF (10 years)', 'PV of Terminal Value', 'Enterprise Value', 'Net Debt',
                   'Equity Value', 'Diluted shares', 'Intrinsic value / share'],
        'Value': [f"${v['pv_fcff'] / 1e9:,.2f} B", f"${v['pv_terminal'] / 1e9:,.2f} B",
                  f"${v['enterprise_value'] / 1e9:,.2f} B", f"${br['net_debt'] / 1e9:,.2f} B",
                  f"${v['equity_value'] / 1e9:,.2f} B", f"{br['shares']:,.0f}", f"${v['intrinsic_price']:,.2f}"],
    }), hide_index=True, use_container_width=True)

    st.subheader('How the value builds up')
    st.caption('Each bar is the present value of one year\'s free cash flow; the last adds the terminal value.')
    rows = res['projection']['rows']
    pv = v['pv_fcff_by_year']
    _waterfall([str(r['year']) for r in rows] + ['Terminal value', 'Enterprise value'],
               [x / 1e9 for x in pv] + [v['pv_terminal'] / 1e9, v['enterprise_value'] / 1e9],
               ['relative'] * (len(pv) + 1) + ['total'], 'Present value of cash flows → Enterprise value')

    st.subheader('Enterprise to Equity Bridge')
    labels, values, measures = ['Enterprise Value'], [v['enterprise_value'] / 1e9], ['absolute']
    labels.append('Total debt (incl. finance leases)'); values.append(-(br['total_debt'] or 0) / 1e9); measures.append('relative')
    labels.append('Cash & equivalents'); values.append((br['cash'] or 0) / 1e9); measures.append('relative')
    labels.append('Short-term investments'); values.append((br['short_term_investments'] or 0) / 1e9); measures.append('relative')
    for k, x in br.get('non_operating_assets', {}).items():
        labels.append(k); values.append(x / 1e9); measures.append('relative')
    labels.append('Equity Value'); values.append(v['equity_value'] / 1e9); measures.append('total')
    _waterfall(labels, values, measures, 'Enterprise Value to Equity Value')
    st.caption(f"Balance date {br['balance_date']} · Debt: {br['debt_source']} · Non-operating investments at book "
               'value (verify their income is excluded from EBIT).')

    with st.expander('Terminal value details'):
        st.write(f"Terminal method: {'steady-state reinvestment (advantages persist)' if t['mode'] == 'steady_state' else 'RONIC = WACC (advantages fade)'}")
        st.write(f"Terminal reinvestment rate: {t['reinvestment_rate']:.1%} of NOPAT")
        st.write(f"Implied return on new capital (RONIC): {t['ronic']:.1%}" if t['ronic'] else 'Implied RONIC: n/a')
        st.write(f"Terminal value share of enterprise value: {v['terminal_share_of_ev']:.0%}")


def _sensitivity(data, scen, wacc, g, overrides, market_price, ticker):
    st.subheader('WACC × Terminal Growth Sensitivity')
    _glossary(['WACC', 'Terminal growth', 'Sensitivity matrix'])
    st.caption(f'{scen.capitalize()} scenario · intrinsic value per share · cells show upside vs market price')
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
                         rd_life_note=data['rd_note'])
            row.append(_price(out) if _price(out) is not None else float('nan'))
        matrix.append(row)
    text = [[(f'${x:,.0f}<br>{(x / market_price - 1) * 100:+.0f}%' if not math.isnan(x) else 'N/A') for x in r]
            for r in matrix]
    fig = go.Figure(go.Heatmap(z=matrix, x=[f'{x * 100:.2f}%' for x in growths], y=[f'{w * 100:.2f}%' for w in waccs],
                               colorscale='RdYlGn', zmid=market_price, text=text, texttemplate='%{text}',
                               hovertemplate='Growth %{x}<br>WACC %{y}<br>%{text}<extra></extra>',
                               colorbar=dict(title='$/share')))
    fig.update_layout(template='plotly_dark', xaxis_title='Terminal Growth', yaxis_title='WACC', height=440)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f'Colour midpoint = market price (${market_price:,.2f}): green cells are above the market, red below.')
    export = pd.DataFrame(matrix, index=[f'{w * 100:.2f}%' for w in waccs], columns=[f'{x * 100:.2f}%' for x in growths])
    export.index.name = 'WACC / Terminal Growth'
    st.download_button('Download Sensitivity CSV', export.to_csv(),
                       file_name=f'intrinsic_{ticker.lower()}_sensitivity_{scen}.csv', mime='text/csv')


def _model_data(results, scen, data):
    st.subheader('Model & Data')
    note = _validation_note()
    if note:
        st.success(f'Revenue and EBIT-margin forecasts passed {note[0]}/{note[1]} pre-registered out-of-sample '
                   'criteria (fresh companies, parameters estimated with data ≤2018, forecasts 2019–2025).')
    st.info('What is NOT validated: CapEx, D&A and working-capital paths (consistent by construction, not tested '
            'as forecasts) and the final valuation. Use the range, not a single number.')
    a = results[scen]['assumptions']
    st.markdown('#### Assumptions and where each comes from')
    rows = []
    for k, x in a['drivers'].items():
        val = x['value']
        if isinstance(val, list):
            shown = ', '.join(f'{y:.3g}' for y in val[:5])
        elif is_number(val):
            shown = f'{val:.2%}' if abs(val) < 5 and k not in ('year0', 'rd_life') else f'{val:,.4g}'
        else:
            shown = str(val)
        rows.append({'Driver': k, 'Value': shown, 'Source': SOURCE_BADGE.get(x['source'], x['source']),
                     'Explanation': x['note']})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.markdown('#### Data quality and consistency checks')
    for b in a['blockers']:
        st.error(b)
    for d in a['degradations']:
        st.warning(d)
    for n in a.get('notes', []):
        st.caption('ℹ️ ' + n)
    for c in results[scen].get('checks', []):
        st.write('• ' + c)
    for f in data.get('capital_flags', []):
        st.write('• ' + f)
    st.caption('Method: driver-based FCFF with panel-calibrated mean reversion (2,578 US companies), PP&E '
               'roll-forward, full operating NWC, capitalised R&D and steady-state terminal reinvestment.')


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def render_model_27(ticker, wacc, terminal_growth, market_price=None, market_shares=None):
    try:
        with st.spinner('Loading SEC financial statements...'):
            data = _inputs(ticker)
    except Exception as exc:
        st.error(f'SEC financial data unavailable for {ticker}: {exc}')
        return
    if data['decision'].get('model') != 'fcff':
        st.error(f"Not valued with FCFF: {data['decision'].get('category')} — {data['decision'].get('reason')}")
        return
    br = data['bridge']
    if br['net_debt'] is None or not br['shares']:
        st.error('Valuation blocked: the debt, cash or share count could not be verified from SEC filings.')
        return
    probe = dm.derive_assumptions(data['history'], wacc=wacc, terminal_growth=terminal_growth,
                                  calibration=dm.load_calibration(), rd_life=data['rd_life'],
                                  rd_life_note=data['rd_note'])
    if probe['status'] == 'BLOCKED':
        st.error('Valuation blocked — required SEC data is missing:')
        for b in probe['blockers']:
            st.write('• ' + b)
        return
    scen = st.sidebar.radio('Scenario', SCENARIOS, index=1, format_func=str.capitalize,
                            key=f'm27_scenario_{ticker}', help=GLOSSARY['Scenario'])
    overrides = _sidebar_inputs(ticker, probe)
    results = _run_all(data, wacc, terminal_growth, overrides)
    if 'valuation' not in results[scen]:
        st.error(results[scen].get('valuation_error', 'Valuation not available for this scenario.'))
        return
    status = results[scen]['status']
    if status == 'DEGRADED':
        st.warning('Some inputs are estimated or adjusted — see Model & Data for details.')
    if overrides:
        names = {'growth_start': 'revenue growth', 'margin_target': 'long-run margin', 'intensity_target':
                 'fixed assets per $ of revenue', 'nwc_ratio_target': 'working capital', 'tax_terminal': 'tax rate'}
        st.info('You are viewing YOUR case: ' + ', '.join(names.get(k, k) for k in overrides)
                + ' changed from model values. Use "Reset to model values" in the sidebar to go back.')
    section = st.segmented_control('Dashboard section',
                                   options=['Overview', 'Forecast', 'Valuation', 'Sensitivity', 'Model & Data'],
                                   default='Overview', key='intrinsic_section_27', label_visibility='collapsed')
    if section == 'Forecast':
        _forecast(results, scen, ticker)
    elif section == 'Valuation':
        _valuation(results, scen, data)
    elif section == 'Sensitivity':
        _sensitivity(data, scen, wacc, terminal_growth, overrides, market_price, ticker)
    elif section == 'Model & Data':
        _model_data(results, scen, data)
    else:
        _overview(results, scen, wacc, market_price, market_shares, data)
    st.caption('Intrinsic · Data: SEC EDGAR + market reference · Model 27 · research tool, not investment advice')
