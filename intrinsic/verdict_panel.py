"""Final verdict section (shared by the FCFF and bank workspaces). Presentation only; numbers from intrinsic.verdict."""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

from intrinsic import verdict as vd
from intrinsic.ui import components as ui
from intrinsic.ui.i18n import t
from intrinsic.ui.theme import T

ACTION_LABEL = {'buy': 'Buy', 'hold': 'Hold', 'sell': 'Sell'}
ACTION_COLOR = {'sell': T['neg'], 'hold': '#6E7A8A', 'buy': T['pos']}
ACTION_FILL = {'sell': 'rgba(242,112,123,.28)', 'hold': 'rgba(110,122,138,.28)', 'buy': 'rgba(75,203,139,.28)'}
ACTION_TAG = {'sell': 'neg', 'hold': 'plain', 'buy': 'pos'}
ACTION_MEANING = {
    'buy': 'The model values the stock above the market price by more than the margin of safety in most outcomes.',
    'hold': 'Neither buying nor selling holds a majority of the model outcomes: keep it if you own it, but there is no '
            'strong reason to buy more or to sell.',
    'sell': 'The model values the stock below the market price by more than the margin of safety in most outcomes.',
}


def _segmented_bar(probs):
    fig = go.Figure()
    for a in vd.ACTIONS:
        p = probs[a]
        fig.add_trace(go.Bar(
            x=[p * 100], y=[''], orientation='h', name=t(ACTION_LABEL[a]),
            marker=dict(color=ACTION_COLOR[a], line=dict(color=T['bg'], width=2)),
            text=[f'{t(ACTION_LABEL[a])} {p:.0%}' if p >= 0.08 else ''], textposition='inside',
            insidetextanchor='middle', textfont=dict(color=T['bg'], size=13, family="'IBM Plex Mono', monospace"),
            hovertemplate=f'{t(ACTION_LABEL[a])}: {p:.1%}<extra></extra>'))
    fig.update_layout(template='intrinsic', barmode='stack', height=120, hovermode='closest', bargap=0.15,
                      legend=dict(orientation='h', yanchor='bottom', y=1.05, x=0, traceorder='normal'),
                      margin=dict(l=8, r=8, t=36, b=8))
    fig.update_xaxes(range=[0, 100], ticksuffix='%', showgrid=False)
    fig.update_yaxes(showticklabels=False)
    return fig


def _distribution_chart(v, base):
    dist = v['distribution']
    lo = min(vd.quantile(dist, 0.005), v['sell_below'] * 0.9)
    hi = max(vd.quantile(dist, 0.95), v['buy_above'] * 1.2, (base or 0) * 1.2)   # long right tails flatten the curve
    if dist['kind'] == 'lognormal':
        lo = max(lo, 0.0)
    n = 240
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    fig = go.Figure()
    zones = (('sell', lo, v['sell_below']), ('hold', v['sell_below'], v['buy_above']), ('buy', v['buy_above'], hi))
    for a, a0, a1 in zones:
        seg = [x for x in xs if a0 <= x <= a1] or [a0, a1]
        seg = sorted(set([a0] + seg + [a1]))
        fig.add_trace(go.Scatter(x=seg, y=[vd.pdf(dist, x) for x in seg], mode='lines', fill='tozeroy',
                                 fillcolor=ACTION_FILL[a], line=dict(color=ACTION_COLOR[a], width=2),
                                 name=t(ACTION_LABEL[a]), hoverinfo='skip'))
    ymax = max(vd.pdf(dist, x) for x in xs)
    fig.add_vline(x=v['market_price'], line=dict(color=T['market'], width=1.5, dash='dash'))
    fig.add_annotation(x=v['market_price'], y=ymax * 1.08, text=t('Market {p}', p=ui.usd(v['market_price'])),
                       showarrow=False, font=dict(size=11, color=T['text']), yanchor='bottom')
    if ui.is_num(base):
        fig.add_vline(x=base, line=dict(color=T['model'], width=1.5))
        fig.add_annotation(x=base, y=ymax * 0.92, text=t('Base {p}', p=ui.usd(base)), showarrow=False,
                           font=dict(size=11, color=T['model']), xanchor='left', xshift=4)
    fig.update_layout(template='intrinsic', height=320, hovermode='x', showlegend=False,
                      xaxis_title=t('Intrinsic value per share (USD)'), yaxis_title=t('Likelihood'))
    fig.update_yaxes(showticklabels=False, showgrid=False, range=[0, ymax * 1.25])
    fig.update_xaxes(tickprefix='$')
    return fig


def render_verdict(prices, market_price, reasons, key, chart):
    """prices: per-share {'conservative','base','optimistic'}; reasons: [html str]; chart: the _chart card helper."""
    ui.heading(t('Final verdict'), t('What the model\'s numbers say about buying, holding or selling at today\'s price'))
    margin = st.slider(t('Margin of safety'), min_value=0, max_value=40, value=15, step=5, format='%d%%',
                       key=f'verdict_margin_{key}',
                       help=t('How far value and price must differ before the model says buy or sell. A wider margin '
                              'makes Hold more likely.')) / 100
    v = vd.verdict(prices, market_price, margin)
    if v is None:
        ui.state_card(t('No verdict'), t('The valuation range is not available for this company, so the model cannot '
                                         'estimate how likely each outcome is.'))
        return
    a, probs = v['action'], v['probabilities']
    ui.md(f'<div class="ix-hero"><div class="ix-hero-top">'
          f'<div class="ix-hero-cell">{ui.tag(t("Model verdict"), ACTION_TAG[a])}'
          f'<div class="ix-big {"pos" if a == "buy" else "neg" if a == "sell" else ""}">{escape(t(ACTION_LABEL[a]))}</div>'
          f'<div class="ix-big-sub">{t("{p:.0%} of the model outcomes", p=probs[a]) if a != "hold" else t("no side reaches 50% of the outcomes")}</div></div>'
          f'<div class="ix-hero-cell" style="grid-column: span 2">{ui.tag(t("What it means"), "plain")}'
          f'<div class="ix-big-sub" style="font-size:.95rem;margin-top:10px">{t(ACTION_MEANING[a])}</div></div>'
          f'</div></div>')
    chart(_segmented_bar(probs), 'Probability of each verdict',
          'Share of the model\'s value distribution in each zone', key=f'verdict-split-{key}')
    chart(_distribution_chart(v, prices.get('base')), 'Where the probabilities come from',
          'Model value distribution from the conservative, base and optimistic scenarios, split at the market price '
          '± the margin of safety', key=f'verdict-dist-{key}')
    rows = [(t('Buy if value is above'), ui.usd(v['buy_above'])), (t('Sell if value is below'), ui.usd(v['sell_below'])),
            (t('Probability value is above the market price'), f"{v['prob_above_market']:.0%}")]
    ui.md('<div class="ix-note"><div class="ix-label">' + t('Why') + '</div><ul>'
          + ''.join(f'<li>{r}</li>' for r in reasons) + '</ul>'
          + '<div class="ix-state" style="margin-top:10px">' + ui.kv_rows(rows) + '</div></div>')
    notes = [t('This is what the model\'s numbers say, not investment advice or a recommendation for your portfolio.'),
             t('The spread comes from the model\'s conservative and optimistic scenarios; uncertainty in the discount '
               'rate and terminal growth is not included, so real outcomes are wider.')]
    if v['one_sided']:
        notes.append(t('One scenario is not valued, so the spread is estimated from the other side and assumed '
                       'symmetric.'))
    st.caption(' '.join(notes))
