"""Safely patch company assumptions and dashboard in-place, with backups.
Run from ~/Projects/Intrinsic after copying googl_alternative_18h.py.
"""
from pathlib import Path
from datetime import datetime
import ast

p = Path('company_assumptions_engine.py')
s = p.read_text()
old_import = 'from historical_ratios_engine import obtener_ratios_empresa'
new_import = old_import + '\nfrom googl_alternative_18h import obtener_ratios_alternativos_googl'
old_policy = '    "NVDA": {"terminal_growth_anchor": 0.06, "growth_ceiling": 0.35},'
new_policy = old_policy + '\n    "GOOGL": {"terminal_growth_anchor": 0.035, "growth_ceiling": 0.22},  # illustrative policy, not SEC data'
old_block = '''    if ticker not in POLICY:
        if ticker == "GOOGL":
            raise ValueError("GOOGL bloqueado: D&A completo y NWC comparable no disponibles. No se generará un DCF automático.")
        raise ValueError(f"Ticker no configurado para escenarios: {ticker}")
    result = datos_historicos if datos_historicos is not None else obtener_ratios_empresa(ticker)'''
new_block = '''    if ticker not in POLICY:
        raise ValueError(f"Ticker no configurado para escenarios: {ticker}")
    if datos_historicos is not None:
        result = datos_historicos
        if ticker == "GOOGL" and result.get("methodology") != "GOOGL_DEPRECIATION_ONLY_AR_MINUS_AP_PROXY":
            raise ValueError("GOOGL requiere ratios alternativos etiquetados explícitamente")
    elif ticker == "GOOGL":
        result = obtener_ratios_alternativos_googl()
    else:
        result = obtener_ratios_empresa(ticker)'''
for old, new in [(old_import, new_import), (old_policy, new_policy), (old_block, new_block)]:
    if s.count(old) != 1:
        raise SystemExit(f'BLOCKED: company_assumptions_engine.py does not match expected version: {old[:55]!r}')
    s = s.replace(old, new, 1)
ast.parse(s)

# Dashboard is optional, but if present, remove only the explicit hard stop.
d = Path('dashboard.py')
updated_dashboard = None
if d.exists():
    ds = d.read_text()
    block = '''if ticker == "GOOGL":
    st.info("Alphabet: historical data available, but automatic DCF is blocked until complete D&A and comparable operating NWC are validated.")
    st.stop()
'''
    if ds.count(block) == 1:
        ds = ds.replace(block, '''if ticker == "GOOGL":
    st.warning("GOOGL 18H — PROXY DCF: D&A uses reported depreciation only; working capital uses AR - AP. These are NOT complete D&A/ONWC. Illustrative valuation only.")
''', 1)
        ast.parse(ds)
        updated_dashboard = ds
    else:
        print('NOTICE: Dashboard GOOGL stop differs from expected version; not modified. Inspect manually.')

stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
p.with_name(p.name + '.backup_18h_' + stamp).write_text(p.read_text())
p.write_text(s)
print('Updated:', p)
if updated_dashboard is not None:
    d.with_name(d.name + '.backup_18h_' + stamp).write_text(d.read_text())
    d.write_text(updated_dashboard)
    print('Updated:', d)
print('Original backups saved with timestamp:', stamp)
