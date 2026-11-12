"""Intrinsic 27 — Streamlit panel for the integrated driver model.

Called from dashboard_23f_integrated.py when "Driver Model 27" is selected.
Self-contained: loads its own SEC inputs (cached), runs three scenarios, and
shows every driver with its source, data-quality status and consistency checks.
"""
from __future__ import annotations

import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import driver_forecast_27 as dm
from run_driver_27 import load_inputs
from sec_annual_27 import is_number

LABEL = 'Driver Model 27 (10-year, validated)'
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_BADGE = {'data': '🟦 data', 'calibrated': '🟩 calibrated', 'assumption': '🟨 assumption', 'user': '🟥 user'}
EDITABLE = (  # driver, label, percent?
    ('growth_start', 'Starting revenue growth', True),
    ('margin_target', 'Long-run EBIT margin target', True),
    ('intensity_target', 'Long-run Net PP&E / revenue', True),
    ('nwc_ratio_target', 'Long-run operating NWC / revenue', True),
    ('dep_rate', 'Depreciation / prior Net PP&E', True),
)


@st.cache_data(ttl=3600, show_spinner=False)
def _inputs(ticker):
    data = load_inputs(ticker)
    data['decision'] = data['decision']._asdict() if hasattr(data['decision'], '_asdict') else vars(data['decision'])
    return data


def _validation_note():
    path = os.path.join(HERE, 'final_validation_27.json')
    if not os.path.exists(path):
        return 'Validation report not found.'
    with open(path) as fh:
        rep = json.load(fh)
    passed = sum(1 for v in rep.get('verdict', {}).values() if v.get('pass'))
    total = len(rep.get('verdict', {}))
    return (f'Revenue and EBIT-margin paths: pre-registered out-of-sample test passed {passed}/{total} criteria '
            '(fresh companies, parameters estimated ≤2018, forecasts 2019–2025). '
            'CapEx, D&A and NWC are consistent by construction but not validated as forecasts; '
            'the valuation itself is NOT validated.')


def _fmt(value, pct):
    if isinstance(value, list):
        return ', '.join(f'{x:.3g}' for x in value[:5]) + (' …' if len(value) > 5 else '')
    if not is_number(value):
        return str(value)
    if pct:
        return f'{value:.2%}'
    return f'{value / 1e9:,.2f} B' if abs(value) >= 1e6 else f'{value:,.4g}'


PCT_KEYS = {'growth_start', 'terminal_growth', 'margin_start', 'margin_target', 'tax_start', 'tax_terminal',
            'intensity_start', 'intensity_target', 'dep_rate', 'nwc_ratio_start', 'nwc_ratio_target', 'wacc',
            'rd_ratio_start', 'rd_ratio_target'}


def render_model_27(ticker, wacc, terminal_growth, market_price=None):
    st.markdown('### Driver Model 27 · integrated 10-year FCFF')
    st.info(_validation_note())
    try:
        with st.spinner('Loading SEC inputs for Model 27...'):
            data = _inputs(ticker)
    except Exception as exc:          # network / missing filer
        st.error(f'Model 27 inputs unavailable: {exc}')
        return
    if data['decision'].get('model') != 'fcff':
        st.error(f"Not valued: {data['decision'].get('category')} — {data['decision'].get('reason')}")
        return
    br = data['bridge']
    if br['net_debt'] is None or not br['shares']:
        st.error('BLOCKED: incomplete enterprise-to-equity bridge (debt, cash, short-term investments or shares).')
        return

    base_probe = dm.derive_assumptions(data['history'], wacc=wacc, terminal_growth=terminal_growth,
                                       calibration=dm.load_calibration(), rd_life=data['rd_life'],
                                       rd_life_note=data['rd_note'])
    overrides = {}
    with st.sidebar.expander('Model 27 · override drivers', expanded=False):
        st.caption('Leave unchanged to use data/calibrated values. Changed values are labelled USER.')
        for key, label, pct in EDITABLE:
            default = base_probe['drivers'].get(key, {}).get('value')
            if not is_number(default):
                continue
            val = st.number_input(f'{label} (%)', value=float(round(default * 100, 2)), step=0.5,
                                  key=f'm27_{key}_{ticker}') / 100
            if abs(val - round(default, 4)) > 1e-6:
                overrides[key] = val

    results = {}
    for s in ('conservative', 'base', 'optimistic'):
        results[s] = dm.run(data['history'], wacc=wacc, terminal_growth=terminal_growth, net_debt=br['net_debt'],
                            shares=br['shares'], scenario=s, overrides=overrides or None,
                            rd_life=data['rd_life'], rd_life_note=data['rd_note'])
    base = results['base']
    status = base['status']
    (st.success if status == 'DATA_COMPLETE' else st.warning if status == 'DEGRADED' else st.error)(
        f'Data status: {status}')
    for b in base['assumptions']['blockers']:
        st.error(b)
    for d in base['assumptions']['degradations']:
        st.warning(d)
    for n in base['assumptions'].get('notes', []):
        st.caption('ℹ️ ' + n)
    if 'valuation' not in base:
        st.error(base.get('valuation_error', 'Valuation not available.'))
        return

    cols = st.columns(3)
    for col, s in zip(cols, ('conservative', 'base', 'optimistic')):
        v = results[s].get('valuation')
        if not v:
            col.metric(s.capitalize(), 'N/A')
            continue
        delta = f"{v['intrinsic_price'] / market_price - 1:+.0%} vs market" if market_price else None
        col.metric(f'{s.capitalize()} · value / share', f"${v['intrinsic_price']:,.2f}", delta)
    st.caption('Conservative/optimistic = p20/p80 out-of-sample forecast-error bands for revenue AND margin '
               'applied together (joint scenario is more extreme than p20/p80). Conservative terminal also assumes '
               'excess returns vanish (RONIC = WACC).')

    fig = go.Figure()
    for s in ('conservative', 'base', 'optimistic'):
        p = results[s].get('projection')
        if p:
            fig.add_trace(go.Scatter(x=[r['year'] for r in p['rows']], y=[r['revenue'] / 1e9 for r in p['rows']],
                                     name=s.capitalize(), mode='lines+markers'))
    fig.update_layout(title='Revenue by scenario (USD billions)', height=340, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('#### Base-case drivers and their sources')
    st.dataframe(pd.DataFrame([{'Driver': k, 'Value': _fmt(x['value'], k in PCT_KEYS),
                                'Source': SOURCE_BADGE.get(x['source'], x['source']), 'Note': x['note']}
                               for k, x in base['assumptions']['drivers'].items()]),
                 hide_index=True, use_container_width=True)

    st.markdown('#### Base-case projection (USD billions)')
    rows = base['projection']['rows']
    table = pd.DataFrame({
        'Year': [r['year'] for r in rows],
        'Revenue': [r['revenue'] / 1e9 for r in rows], 'Growth': [r['growth'] for r in rows],
        'EBIT margin': [r['ebit_margin'] for r in rows], 'NOPAT': [r['nopat'] / 1e9 for r in rows],
        'D&A': [r['da'] / 1e9 for r in rows], 'CapEx': [r['capex'] / 1e9 for r in rows],
        'ΔNWC': [r['delta_nwc'] / 1e9 for r in rows], 'FCFF': [r['fcff'] / 1e9 for r in rows],
        'Reinvestment rate': [r['reinvestment_rate'] for r in rows], 'ROIC': [r['roic'] for r in rows],
    })
    st.dataframe(table.style.format({c: '{:,.1f}' for c in ('Revenue', 'NOPAT', 'D&A', 'CapEx', 'ΔNWC', 'FCFF')} |
                                    {c: '{:.1%}' for c in ('Growth', 'EBIT margin', 'Reinvestment rate', 'ROIC')},
                                    na_rep='n/a'), hide_index=True, use_container_width=True)

    v = base['valuation']
    t = v['terminal']
    st.markdown('#### Valuation bridge (base)')
    st.dataframe(pd.DataFrame({'Item': ['PV explicit FCFF (10y)', 'PV terminal value', 'Enterprise value',
                                        'Net debt (− = net cash & non-operating assets)', 'Equity value',
                                        'Shares', 'Value per share', 'Terminal share of EV',
                                        'Terminal reinvestment rate', 'Implied RONIC'],
                               'Value': [f"{v['pv_fcff'] / 1e9:,.1f} B", f"{v['pv_terminal'] / 1e9:,.1f} B",
                                         f"{v['enterprise_value'] / 1e9:,.1f} B", f"{br['net_debt'] / 1e9:,.1f} B",
                                         f"{v['equity_value'] / 1e9:,.1f} B", f"{br['shares']:,.0f} ({br['shares_source']})",
                                         f"${v['intrinsic_price']:,.2f}", f"{v['terminal_share_of_ev']:.0%}",
                                         f"{t['reinvestment_rate']:.1%} ({t['mode']})",
                                         f"{t['ronic']:.1%}" if t['ronic'] else 'n/a']}),
                 hide_index=True, use_container_width=True)
    with st.expander('Consistency checks and data notes', expanded=False):
        for c in base.get('checks', []):
            st.write('• ' + c)
        st.write(f"• Debt source: {br['debt_source']}")
        for k, val in br.get('non_operating_assets', {}).items():
            st.write(f'• {k} credited at book value: {val / 1e9:,.2f} B (verify its income is excluded from EBIT)')
        for f in data.get('capital_flags', []):
            st.write('• ' + f)
    st.caption('Model 27 is a research model. validated=False refers to the valuation; see the validation note above.')
