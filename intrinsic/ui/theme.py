"""Design system: colour tokens, global CSS, Plotly template and loading indicator.

Concept — "an instrument, not a poster": a dark graphite research terminal where colour encodes
*provenance*, not decoration. Teal = model estimate, white = market data, lavender = your override,
amber = warning, green/red = sign of a difference. Keep in sync with .streamlit/config.toml.
"""
from __future__ import annotations

from urllib.parse import quote

import plotly.graph_objects as go
import plotly.io as pio

# ---------------------------------------------------------------- tokens
T = {
    'bg': '#0B0E13', 'surface': '#121821', 'surface2': '#18202B', 'raised': '#1C2531',
    'line': '#232C38', 'line_soft': '#1A222D', 'line_strong': '#2F3A48',
    'text': '#E7EBF0', 'text2': '#9BA6B5', 'text3': '#808B9B',
    'model': '#5CCFBF', 'model_soft': 'rgba(92,207,191,.12)',
    'market': '#E7EBF0', 'user': '#B9A6FF', 'user_soft': 'rgba(185,166,255,.12)',
    'pos': '#4BCB8B', 'pos_soft': 'rgba(75,203,139,.12)',
    'neg': '#F2707B', 'neg_soft': 'rgba(242,112,123,.12)',
    'warn': '#F0B04A', 'warn_soft': 'rgba(240,176,74,.12)',
}
# Scenario colours: base carries the model accent; the two bounds are distinct but quieter.
SCENARIO_COLORS = {'conservative': '#D9976A', 'base': T['model'], 'optimistic': '#8E9CF5'}
HISTORY_COLOR = '#9BA6B5'
MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
SANS = "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

# ---------------------------------------------------------------- plotly
pio.templates['intrinsic'] = go.layout.Template(pio.templates['plotly_dark'])
pio.templates['intrinsic'].layout.update(
    font=dict(family=SANS, size=12, color=T['text2']),
    title=dict(font=dict(size=13, color=T['text'])),
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    colorway=[T['model'], SCENARIO_COLORS['conservative'], SCENARIO_COLORS['optimistic'], HISTORY_COLOR],
    xaxis=dict(gridcolor=T['line_soft'], linecolor=T['line'], zerolinecolor=T['line_strong'], tickcolor=T['line'],
               tickfont=dict(family=MONO, size=11), title=dict(font=dict(size=11, color=T['text3'])), showgrid=False),
    yaxis=dict(gridcolor=T['line_soft'], linecolor='rgba(0,0,0,0)', zerolinecolor=T['line_strong'],
               tickfont=dict(family=MONO, size=11), title=dict(font=dict(size=11, color=T['text3']))),
    hoverlabel=dict(bgcolor=T['raised'], bordercolor=T['line_strong'],
                    font=dict(color=T['text'], family=MONO, size=12)),
    legend=dict(font=dict(size=11, color=T['text2']), bgcolor='rgba(0,0,0,0)'),
    margin=dict(l=8, r=8, t=16, b=8),
    hovermode='x unified',
)
CHART_CONFIG = {'displayModeBar': False}

# ---------------------------------------------------------------- loader
_LOADER_SVG = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 44 22'>
<line x1='2' y1='20.5' x2='42' y2='20.5' stroke='{T['line_strong']}' stroke-width='1'/>
<polyline fill='none' stroke='{T['model']}' stroke-width='1.8' stroke-linejoin='round' stroke-linecap='round'
 points='2,15 8,12 14,14 20,8 26,10 32,5 40,7'>
<animate attributeName='points' dur='2.4s' repeatCount='indefinite' calcMode='spline'
 keyTimes='0;.33;.66;1' keySplines='.45 0 .2 1;.45 0 .2 1;.45 0 .2 1'
 values='2,15 8,12 14,14 20,8 26,10 32,5 40,7;2,13 8,15 14,10 20,12 26,7 32,9 40,4;2,16 8,11 14,13 20,10 26,6 32,8 40,3;2,15 8,12 14,14 20,8 26,10 32,5 40,7'/>
</polyline>
<circle cx='40' cy='7' r='2.2' fill='{T['model']}'>
<animate attributeName='cy' dur='2.4s' repeatCount='indefinite' calcMode='spline'
 keyTimes='0;.33;.66;1' keySplines='.45 0 .2 1;.45 0 .2 1;.45 0 .2 1' values='7;4;3;7'/>
</circle></svg>"""
_LOADER_URI = 'data:image/svg+xml;utf8,' + quote(' '.join(_LOADER_SVG.split()), safe="=:;,/'() ")

# ---------------------------------------------------------------- css
_VARS = ''.join(f'--ix-{k.replace("_", "-")}:{v};' for k, v in T.items())

CSS = f"""<style>
:root {{ {_VARS} --ix-mono:{MONO}; --ix-sans:{SANS}; --ix-r:6px; }}
html, body {{ font-feature-settings: "tnum" 1, "zero" 0; }}
.block-container {{ max-width: 1360px; padding-top: 3.2rem; padding-bottom: 2.5rem; }}
[data-testid="stHeader"] {{ background: rgba(11,14,19,.86); backdrop-filter: blur(8px); }}
[data-testid="stSidebarContent"] {{ padding-top: .2rem; }}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
  font: 600 .68rem/1.2 var(--ix-sans); text-transform: uppercase; letter-spacing: .12em;
  color: var(--ix-text3); margin: 1rem 0 .35rem; padding: 0; }}
[data-testid="stSidebar"] [data-testid="stExpander"] details {{ background: var(--ix-surface); border-color: var(--ix-line); }}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {{ font-weight: 500; font-size: .86rem; }}
[data-testid="stAlert"] {{ border-radius: var(--ix-r); }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 8px; }}
[data-testid="stDownloadButton"] button {{ font-size: .78rem; padding: .25rem .7rem; min-height: 0; }}
hr {{ margin: .8rem 0 !important; border-color: var(--ix-line) !important; }}
.ix-mono {{ font-family: var(--ix-mono); }}

/* ---- loader (replaces the default spinner glyph) */
[data-testid="stSpinnerIcon"] {{ width: 44px !important; height: 22px !important; border: 0 !important;
  border-radius: 0 !important; animation: none !important;
  background: url("{_LOADER_URI}") center / contain no-repeat !important; }}
[data-testid="stSpinner"] {{ color: var(--ix-text2); font-size: .84rem; }}

/* ---- brand */
.ix-brand {{ display:flex; align-items:center; gap:10px; padding: 2px 0 6px; }}
.ix-mark {{ width:28px; height:28px; border-radius:6px; border:1px solid var(--ix-line-strong);
  background: var(--ix-surface2); display:flex; align-items:center; justify-content:center; }}
.ix-brand b {{ display:block; font: 600 .95rem/1.1 var(--ix-sans); letter-spacing:.14em; color: var(--ix-text); }}
.ix-brand span {{ display:block; font-size:.72rem; color: var(--ix-text3); margin-top:2px; }}

/* ---- sidebar status ledger */
.ix-state {{ border:1px solid var(--ix-line); border-radius: var(--ix-r); background: var(--ix-surface);
  padding: 4px 10px; margin: 0 0 8px; }}
.ix-kv {{ display:flex; justify-content:space-between; align-items:baseline; gap:10px; padding: 6px 0;
  border-bottom: 1px solid var(--ix-line-soft); font-size: .8rem; }}
.ix-kv:last-child {{ border-bottom:0; }}
.ix-kv span {{ color: var(--ix-text2); }}
.ix-kv b {{ font: 500 .82rem/1.2 var(--ix-mono); color: var(--ix-text); text-align:right; }}
.ix-kv.total {{ border-top:1px solid var(--ix-line); margin-top:2px; }}
.ix-kv.total b {{ color: var(--ix-model); }}

/* ---- provenance tags */
.ix-tag {{ display:inline-flex; align-items:center; gap:5px; font: 600 .62rem/1 var(--ix-sans); letter-spacing:.1em;
  text-transform: uppercase; padding: 4px 6px; border-radius: 4px; border:1px solid var(--ix-line-strong);
  color: var(--ix-text2); white-space: nowrap; vertical-align: middle; }}
.ix-tag::before {{ content:""; width:6px; height:6px; border-radius:50%; background: currentColor; }}
.ix-tag.model {{ color: var(--ix-model); border-color: rgba(92,207,191,.35); background: var(--ix-model-soft); }}
.ix-tag.market {{ color: var(--ix-market); }}
.ix-tag.user {{ color: var(--ix-user); border-color: rgba(185,166,255,.35); background: var(--ix-user-soft); }}
.ix-tag.warn {{ color: var(--ix-warn); border-color: rgba(240,176,74,.35); background: var(--ix-warn-soft); }}
.ix-tag.neg {{ color: var(--ix-neg); border-color: rgba(242,112,123,.35); background: var(--ix-neg-soft); }}
.ix-tag.pos {{ color: var(--ix-pos); border-color: rgba(75,203,139,.35); background: var(--ix-pos-soft); }}
.ix-tag.plain::before {{ display:none; }}

/* ---- company header */
.ix-head {{ display:flex; justify-content:space-between; align-items:flex-end; gap:20px; flex-wrap:wrap;
  padding-bottom: 14px; border-bottom: 1px solid var(--ix-line); margin-bottom: 0; }}
.ix-eyebrow {{ font: 500 .7rem/1 var(--ix-sans); letter-spacing:.14em; text-transform:uppercase; color: var(--ix-text3);
  margin-bottom: 8px; display:flex; gap:10px; flex-wrap:wrap; }}
.ix-eyebrow b {{ color: var(--ix-text2); font-weight:500; }}
.ix-name {{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; }}
.ix-name h1 {{ font: 600 1.7rem/1.15 var(--ix-sans); letter-spacing: -.01em; color: var(--ix-text); margin:0; padding:0; }}
.ix-ticker {{ font: 600 .82rem/1 var(--ix-mono); color: var(--ix-bg); background: var(--ix-text); padding: 5px 7px;
  border-radius: 4px; letter-spacing: .04em; }}
.ix-strip {{ display:flex; flex-wrap:wrap; gap: 0; margin: 0 0 14px; border-bottom: 1px solid var(--ix-line); }}
.ix-strip > div {{ padding: 10px 14px 10px 0; margin-right: 14px; border-right: 1px solid var(--ix-line-soft); min-width: 0; }}
.ix-strip > div:last-child {{ border-right: 0; }}
.ix-strip span {{ display:block; font-size:.68rem; letter-spacing:.08em; text-transform:uppercase; color: var(--ix-text3);
  margin-bottom: 4px; }}
.ix-strip b {{ font: 500 .9rem/1.2 var(--ix-mono); color: var(--ix-text); white-space: nowrap; }}
.ix-strip small {{ display:block; font-size:.7rem; color: var(--ix-text3); margin-top:3px; }}

/* ---- section heading */
.ix-h {{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap; margin: 6px 0 10px; }}
.ix-h h3 {{ font: 600 1.02rem/1.25 var(--ix-sans); color: var(--ix-text); margin:0; padding:0; }}
.ix-h p {{ font-size:.8rem; color: var(--ix-text3); margin:0; }}
.ix-label {{ font: 600 .68rem/1 var(--ix-sans); letter-spacing:.12em; text-transform:uppercase; color: var(--ix-text3);
  margin: 0 0 8px; }}
.ix-card-title {{ font: 600 .86rem/1.3 var(--ix-sans); color: var(--ix-text); margin: 0 0 2px; }}
.ix-card-sub {{ font-size: .74rem; color: var(--ix-text3); margin: 0 0 4px; }}

/* ---- valuation hero */
.ix-hero {{ border:1px solid var(--ix-line); border-radius: 8px; background: var(--ix-surface); margin: 2px 0 12px; }}
.ix-hero-top {{ display:grid; grid-template-columns: 1.25fr 1fr 1fr; }}
.ix-hero-cell {{ padding: 16px 20px 14px; border-right:1px solid var(--ix-line); min-width:0; }}
.ix-hero-cell:last-child {{ border-right:0; }}
.ix-hero-cell .ix-tag {{ margin-bottom: 12px; }}
.ix-big {{ font: 500 2.5rem/1 var(--ix-mono); letter-spacing: -.03em; color: var(--ix-text); }}
.ix-big.model {{ color: var(--ix-model); }}
.ix-big.pos {{ color: var(--ix-pos); }} .ix-big.neg {{ color: var(--ix-neg); }}
.ix-big-sub {{ font-size: .76rem; color: var(--ix-text3); margin-top: 8px; display:flex; align-items:center; gap:6px; }}
.ix-range {{ border-top:1px solid var(--ix-line); padding: 14px 20px 12px; }}
.ix-range-track {{ position:relative; height: 46px; margin: 4px 6px 0; }}
.ix-range-axis {{ position:absolute; left:0; right:0; top: 22px; height:1px; background: var(--ix-line-strong); }}
.ix-range-band {{ position:absolute; top: 15px; height: 15px; background: var(--ix-model-soft);
  border-left: 1px solid rgba(92,207,191,.5); border-right: 1px solid rgba(92,207,191,.5); }}
.ix-range-pt {{ position:absolute; top: 15px; width: 3px; height: 15px; margin-left:-1.5px; border-radius: 1px; }}
.ix-range-pt i {{ position:absolute; top: 20px; left: 50%; transform: translateX(-50%); font: 500 .7rem/1 var(--ix-mono);
  font-style: normal; color: var(--ix-text2); white-space: nowrap; }}
.ix-range-mkt {{ position:absolute; top: 2px; height: 42px; width: 0; border-left: 1px dashed var(--ix-text); }}
.ix-range-mkt i {{ position:absolute; top: -2px; left: 6px; font: 600 .68rem/1 var(--ix-mono); font-style: normal;
  color: var(--ix-text); white-space: nowrap; }}
.ix-range-mkt.flip i {{ left:auto; right: 6px; }}
.ix-range-ends {{ display:flex; justify-content:space-between; font: .68rem/1 var(--ix-mono); color: var(--ix-text3);
  margin-top: 6px; }}
.ix-legend {{ display:flex; gap:14px; flex-wrap:wrap; font-size:.72rem; color: var(--ix-text3); margin-top: 8px; }}
.ix-legend span {{ display:inline-flex; align-items:center; gap:6px; }}
.ix-legend i {{ width:10px; height:3px; border-radius:1px; display:inline-block; }}
.ix-legend i.dash {{ height:0; border-top: 1px dashed var(--ix-text); }}

/* ---- metric row */
.ix-metrics {{ display:grid; grid-template-columns: repeat(6, minmax(0,1fr)); border:1px solid var(--ix-line);
  border-radius: 8px; background: var(--ix-surface); margin: 0 0 12px; }}
.ix-metric {{ padding: 12px 14px; border-right: 1px solid var(--ix-line); min-width: 0; }}
.ix-metric:last-child {{ border-right: 0; }}
.ix-metric .k {{ display:flex; align-items:center; gap:5px; font-size: .7rem; color: var(--ix-text3); letter-spacing:.04em;
  margin-bottom: 7px; white-space: nowrap; }}
.ix-metric .v {{ font: 500 1.08rem/1.1 var(--ix-mono); color: var(--ix-text); white-space: nowrap; }}
.ix-metric .v.model {{ color: var(--ix-model); }} .ix-metric .v.user {{ color: var(--ix-user); }}
.ix-metric .f {{ font-size: .68rem; color: var(--ix-text3); margin-top: 5px; white-space: nowrap; overflow:hidden;
  text-overflow: ellipsis; }}

/* ---- notes / verdict / state cards */
.ix-note {{ border:1px solid var(--ix-line); border-radius: 8px; background: var(--ix-surface); padding: 14px 16px;
  margin: 0 0 12px; font-size: .84rem; line-height: 1.6; color: var(--ix-text2); }}
.ix-note strong {{ color: var(--ix-text); font-weight: 600; }}
.ix-note em {{ color: var(--ix-text); font-style: normal; border-bottom: 1px dotted var(--ix-text3); }}
.ix-note ul {{ margin: 6px 0 0; padding-left: 18px; }} .ix-note li {{ margin: 3px 0; }}
.ix-verdict {{ border-left: 2px solid var(--ix-model); padding: 2px 0 2px 12px; margin: 0 0 10px; color: var(--ix-text); }}
.ix-verdict.above {{ border-color: var(--ix-neg); }} .ix-verdict.below {{ border-color: var(--ix-pos); }}
.ix-state-card {{ border:1px solid var(--ix-line); border-left: 2px solid var(--ix-warn); border-radius: 8px;
  background: var(--ix-surface); padding: 16px 18px; margin: 4px 0 14px; font-size: .86rem; line-height: 1.6;
  color: var(--ix-text2); }}
.ix-state-card.info {{ border-left-color: var(--ix-model); }}
.ix-state-card.block {{ border-left-color: var(--ix-neg); }}
.ix-state-card h4 {{ font: 600 .95rem/1.3 var(--ix-sans); color: var(--ix-text); margin: 0 0 6px; padding:0; }}
.ix-quality {{ display:flex; flex-wrap:wrap; align-items:center; gap: 8px 14px; border:1px solid var(--ix-line);
  border-radius: 8px; padding: 10px 14px; margin: 0 0 12px; font-size: .78rem; color: var(--ix-text2);
  background: var(--ix-bg); }}
.ix-quality b {{ color: var(--ix-text); font-weight: 600; }}
.ix-status-grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 0 0 14px; }}

/* ---- tables */
.ix-table-wrap {{ overflow-x:auto; border:1px solid var(--ix-line); border-radius: 8px; background: var(--ix-surface);
  margin: 0 0 10px; }}
table.ix-table {{ width:100%; border-collapse: collapse; font-size: .8rem; }}
.ix-table th, .ix-table td {{ padding: 7px 12px; border-bottom: 1px solid var(--ix-line-soft); white-space: nowrap; }}
.ix-table thead th {{ font: 600 .68rem/1.2 var(--ix-sans); letter-spacing:.06em; text-transform: uppercase;
  color: var(--ix-text3); text-align: right; background: var(--ix-surface2); position: sticky; top: 0; }}
.ix-table thead th.l {{ text-align:left; }}
.ix-table thead th:first-child, .ix-table td:first-child {{ text-align:left; position: sticky; left:0;
  background: inherit; }}
.ix-table tbody tr {{ background: var(--ix-surface); }}
.ix-table tbody tr:hover {{ background: var(--ix-surface2); }}
.ix-table td {{ font-family: var(--ix-mono); text-align: right; color: var(--ix-text); }}
.ix-table td:first-child {{ font-family: var(--ix-sans); color: var(--ix-text2); }}
.ix-table tr.sub td {{ color: var(--ix-text3); font-size: .76rem; }}
.ix-table tr.sub td:first-child {{ padding-left: 24px; }}
.ix-table tr.total td {{ border-top: 1px solid var(--ix-line-strong); font-weight: 600; color: var(--ix-text); }}
.ix-table tr.total td:first-child {{ color: var(--ix-text); }}
.ix-table tr.key td:not(:first-child) {{ color: var(--ix-model); }}
.ix-table th.a, .ix-table td.a {{ background: var(--ix-bg); color: var(--ix-text2); }}
.ix-table th.fade, .ix-table td.fade {{ color: var(--ix-text2); }}
.ix-table tbody tr:last-child td {{ border-bottom: 0; }}
.ix-table td.neg {{ color: var(--ix-neg); }}
.ix-table td.wrap {{ white-space: normal; font-family: var(--ix-sans); text-align:left; color: var(--ix-text2);
  min-width: 260px; font-size: .76rem; line-height: 1.45; }}
.ix-table td.code {{ text-align:left; color: var(--ix-text); font-size: .76rem; }}

/* ---- "?" tooltips */
.intrinsic-help {{ position:relative; display:inline-flex; align-items:center; justify-content:center; width:14px; height:14px;
  flex:none; border:1px solid var(--ix-line-strong); border-radius:50%; font: 600 9px/1 var(--ix-sans);
  color: var(--ix-text3); cursor: help; background: transparent; text-transform:none; letter-spacing:0; }}
.intrinsic-help:hover, .intrinsic-help:focus-visible {{ border-color: var(--ix-model); color: var(--ix-model); outline: none; }}
.intrinsic-help .intrinsic-tip {{ pointer-events:none; position:absolute; bottom: calc(100% + 8px); left: 50%;
  transform: translate(-50%,3px); width:max-content; max-width: min(300px,75vw); min-width: 200px; white-space: normal;
  text-align:left; line-height:1.5; font: 400 12px/1.5 var(--ix-sans); color: var(--ix-text); background: var(--ix-raised);
  border:1px solid var(--ix-line-strong); border-radius: 6px; padding: 9px 11px; box-shadow: 0 12px 28px rgba(0,0,0,.45);
  opacity:0; visibility:hidden; transition: opacity .12s ease, transform .12s ease, visibility .12s; z-index: 1000;
  letter-spacing: 0; text-transform: none; }}
.intrinsic-help:hover .intrinsic-tip, .intrinsic-help:focus-visible .intrinsic-tip {{ opacity:1; visibility:visible;
  transform: translate(-50%,0); }}
.ix-metric:first-child .intrinsic-tip, .ix-hero-cell:first-child .intrinsic-tip {{ left:0; transform: translate(0,3px); }}
.ix-metric:first-child .intrinsic-help:hover .intrinsic-tip, .ix-hero-cell:first-child .intrinsic-help:hover .intrinsic-tip {{
  transform: translate(0,0); }}
.ix-metric:last-child .intrinsic-tip, .ix-hero-cell:last-child .intrinsic-tip {{ left:auto; right:0; transform: translate(0,3px); }}
.ix-metric:last-child .intrinsic-help:hover .intrinsic-tip, .ix-hero-cell:last-child .intrinsic-help:hover .intrinsic-tip {{
  transform: translate(0,0); }}
.intrinsic-glossary {{ display:flex; flex-wrap:wrap; gap:6px; margin: 0 0 12px; }}
.intrinsic-glossary-item {{ display:inline-flex; align-items:center; gap:6px; border:1px solid var(--ix-line);
  border-radius: 4px; padding: 3px 8px; color: var(--ix-text2); font-size: .74rem; }}

/* ---- beta notice, empty state, footer */
.ix-beta {{ border:1px solid var(--ix-line); border-left: 2px solid var(--ix-warn); border-radius: 8px;
  background: var(--ix-surface); padding: 12px 16px; margin: 0 0 14px; }}
.ix-beta-head {{ display:flex; align-items:center; gap:10px; margin-bottom: 6px; color: var(--ix-text); font-size: .88rem; }}
.ix-beta p {{ margin: 0 0 6px; color: var(--ix-text2); font-size: .82rem; line-height: 1.55; }}
.ix-beta p.ix-beta-note {{ color: var(--ix-text3); font-size: .76rem; }}
.ix-empty {{ border: 1px dashed var(--ix-line-strong); border-radius: 8px; padding: 32px; text-align: center;
  color: var(--ix-text2); font-size: .88rem; }}
.ix-footer {{ display:flex; justify-content:space-between; gap: 12px; flex-wrap:wrap; color: var(--ix-text3);
  font-size: .72rem; margin-top: 24px; padding-top: 12px; border-top: 1px solid var(--ix-line); }}

/* ---- responsive */
@media (max-width: 1180px) {{
  .ix-metrics {{ grid-template-columns: repeat(3, minmax(0,1fr)); }}
  .ix-metric:nth-child(3) {{ border-right:0; }}
  .ix-metric:nth-child(-n+3) {{ border-bottom: 1px solid var(--ix-line); }}
}}
@media (max-width: 860px) {{
  .ix-hero-top {{ grid-template-columns: 1fr 1fr; }}
  .ix-hero-cell:first-child {{ grid-column: 1 / -1; border-right:0; border-bottom:1px solid var(--ix-line); }}
  .ix-status-grid {{ grid-template-columns: 1fr; }}
  .ix-big {{ font-size: 2.1rem; }}
}}
@media (max-width: 560px) {{
  .ix-metrics {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
  .ix-metric {{ border-bottom: 1px solid var(--ix-line); }}
  .ix-metric:nth-child(3) {{ border-right: 1px solid var(--ix-line); }}
  .ix-metric:nth-child(2n) {{ border-right: 0; }}
  .ix-name h1 {{ font-size: 1.35rem; }}
  .ix-strip {{ display:grid; grid-template-columns: 1fr 1fr; }}
  .ix-strip > div {{ border-right: 0; margin-right: 0; padding-right: 8px; min-width: 0; }}
  .ix-strip b {{ white-space: normal; }}
  .ix-big {{ font-size: 1.8rem; }}
  .ix-hero-cell {{ padding: 14px; }}
}}
@media (prefers-reduced-motion: reduce) {{ .intrinsic-help .intrinsic-tip {{ transition: none; }} }}
</style>"""

MARK_SVG = (f'<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">'
            f'<path d="M3 13.5 L6.5 8.5 L9.5 10.5 L13 3" fill="none" stroke="{T["model"]}" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round"/><circle cx="13" cy="3" r="1.6" fill="{T["model"]}"/>'
            f'<line x1="2.5" y1="14.5" x2="13.5" y2="14.5" stroke="{T["text3"]}" stroke-width="1"/></svg>')
