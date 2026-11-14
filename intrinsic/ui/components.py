"""Small HTML building blocks. Inputs are already-computed values; functions only format and lay out."""
from __future__ import annotations

import math
from html import escape

import streamlit as st

from intrinsic.ui.i18n import scenario, t
from intrinsic.ui.theme import MARK_SVG, SCENARIO_COLORS


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def usd(x, d=2):
    return f'${x:,.{d}f}' if is_num(x) else '—'


def usd_b(x, d=1):
    """Dollar amount shown in billions (display only)."""
    if not is_num(x):
        return '—'
    return f'−${abs(x) / 1e9:,.{d}f} B' if x < 0 else f'${x / 1e9:,.{d}f} B'


def pct(x, d=2, signed=False):
    if not is_num(x):
        return '—'
    return f'{x * 100:+.{d}f}%' if signed else f'{x * 100:.{d}f}%'


def tag(text, kind=''):
    return f'<span class="ix-tag {kind}">{escape(text)}</span>'


def md(html):
    st.markdown(html, unsafe_allow_html=True)


def brand(container, animate=False):
    a = ' animate' if animate else ''
    container.markdown(
        f'<div class="ix-brand"><div class="ix-mark{a}">{MARK_SVG}</div><div><b class="{a.strip()}">INTRINSIC</b>'
        f'<span class="{a.strip()}">{escape(t("Equity valuation workspace"))}</span></div></div>',
        unsafe_allow_html=True)


def intro():
    """Opening curtain (theme.INTRO_CSS styles it). Rendered once per browser session by app.py."""
    md('<div class="ix-intro" aria-hidden="true"><div class="ix-intro-inner">'
       '<div class="ix-intro-mark">I</div><div class="ix-intro-rule"></div>'
       f'<div class="ix-intro-word">INTRINSIC</div><div class="ix-intro-tag">{escape(t("Equity valuation"))}</div>'
       '</div></div>')


def heading(title, sub=None):
    md(f'<div class="ix-h"><h3>{escape(title)}</h3>' + (f'<p>{sub}</p>' if sub else '') + '</div>')


def kv_rows(rows, total=None):
    """rows: [(label, value_text)] → sidebar-style key/value ledger."""
    out = ''.join(f'<div class="ix-kv"><span>{escape(k)}</span><b>{v}</b></div>' for k, v in rows)
    if total:
        out += f'<div class="ix-kv total"><span>{escape(total[0])}</span><b>{total[1]}</b></div>'
    return out


def metric(label, value, foot='', cls='', help_html=''):
    return (f'<div class="ix-metric"><div class="k">{escape(label)}{help_html}</div>'
            f'<div class="v {cls}">{value}</div>' + (f'<div class="f">{foot}</div>' if foot else '') + '</div>')


def state_card(title, body_html, kind=''):
    md(f'<div class="ix-state-card {kind}" role="status"><h4>{escape(title)}</h4>{body_html}</div>')


def range_bar(prices, market_price, scen):
    """Football-field strip: conservative→optimistic band, scenario ticks and the market price.

    `prices` maps scenario → intrinsic price (or None). Purely positional; values are printed as given.
    """
    known = [p for p in prices.values() if is_num(p)]
    if not known or not is_num(market_price):
        return ''
    lo_v, hi_v = min(known + [market_price]), max(known + [market_price])
    span = hi_v - lo_v or abs(hi_v) or 1.0
    lo_d, hi_d = lo_v - 0.08 * span, hi_v + 0.08 * span

    def pos(x):
        return (x - lo_d) / (hi_d - lo_d) * 100

    parts = ['<div class="ix-range-track"><div class="ix-range-axis"></div>']
    c, o = prices.get('conservative'), prices.get('optimistic')
    if is_num(c) and is_num(o):
        a, b = sorted((pos(c), pos(o)))
        parts.append(f'<div class="ix-range-band" style="left:{a:.2f}%;width:{b - a:.2f}%"></div>')
    for s in ('conservative', 'base', 'optimistic'):
        p = prices.get(s)
        if is_num(p):
            w = '5px' if s == scen else '3px'
            parts.append(f'<div class="ix-range-pt" style="left:{pos(p):.2f}%;width:{w};background:{SCENARIO_COLORS[s]}">'
                         f'<i>{usd(p, 0)}</i></div>')
    mp = pos(market_price)
    parts.append(f'<div class="ix-range-mkt{" flip" if mp > 78 else ""}" style="left:{mp:.2f}%">'
                 f'<i>{t("MKT")} {usd(market_price)}</i></div></div>')
    parts.append(f'<div class="ix-range-ends"><span>{usd(lo_d, 0)}</span><span>{t("USD per share")}</span>'
                 f'<span>{usd(hi_d, 0)}</span></div>')
    legend = ''.join(f'<span><i style="background:{SCENARIO_COLORS[s]}"></i>{scenario(s)}'
                     f'{" " + t("(selected)") if s == scen else ""}</span>' for s in ('conservative', 'base', 'optimistic')
                     if is_num(prices.get(s)))
    parts.append(f'<div class="ix-legend">{legend}<span><i class="dash"></i>{t("Market price")}</span>'
                 f'<span>{t("Band = conservative → optimistic")}</span></div>')
    return ''.join(parts)


def html_table(header, rows, header_classes=None):
    """header: [str]; rows: [(row_class, [(cell_text, cell_class)])]. Cell text is trusted, pre-escaped HTML."""
    hc = header_classes or [''] * len(header)
    head = ''.join(f'<th class="{c}">{h}</th>' for h, c in zip(header, hc))
    body = ''.join(f'<tr class="{rc}">' + ''.join(f'<td class="{cc}">{txt}</td>' for txt, cc in cells) + '</tr>'
                   for rc, cells in rows)
    return f'<div class="ix-table-wrap"><table class="ix-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def footer():
    md(f'<div class="ix-footer"><span>{t("INTRINSIC · Model 27 · Data: SEC EDGAR, Yahoo Finance, Damodaran (Jan 2026)")}</span>'
       f'<span>{t("Student portfolio project — not a professional investment tool or investment advice")}</span></div>')
