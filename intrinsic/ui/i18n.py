"""Interface language (English / Spanish). Presentation only.

Usage: t('English text {x}', x=...) returns the text in the language chosen in the sidebar.
The English sentence is the key, so code stays readable and a missing translation falls back to
English instead of failing. Engine diagnostics (driver notes, data-check messages) stay in English.
tests/test_i18n.py checks that every t('...') literal in the UI has a Spanish entry.
"""
from __future__ import annotations

import streamlit as st

LANGUAGES = {'en': 'English', 'es': 'Español'}
STATE_KEY = 'ix_lang'


def lang():
    return st.session_state.get(STATE_KEY, 'en')


def t(text, **kw):
    out = ES.get(text, text) if lang() == 'es' else text
    return out.format(**kw) if kw else out


def scenario(s):
    return t({'conservative': 'Conservative', 'base': 'Base', 'optimistic': 'Optimistic'}[s])


ES = {
    # ---- brand, intro, footer
    'Equity valuation workspace': 'Espacio de valoración de acciones',
    'Equity valuation': 'Valoración de acciones',
    'Language': 'Idioma',
    'INTRINSIC · Model 27 · Data: SEC EDGAR, Yahoo Finance, Damodaran (Jan 2026)':
        'INTRINSIC · Modelo 27 · Datos: SEC EDGAR, Yahoo Finance, Damodaran (ene 2026)',
    'Student portfolio project — not a professional investment tool or investment advice':
        'Proyecto de portafolio de un estudiante — no es una herramienta profesional ni asesoría de inversión',

    # ---- company selection
    'Company': 'Empresa',
    'Company source': 'Origen de la empresa',
    'Top 25 companies': 'Top 25 empresas',
    'SEC company search': 'Buscador SEC',
    'Selected company': 'Empresa seleccionada',
    'Search name or ticker': 'Buscar nombre o ticker',
    'Search Coca-Cola, KO, etc.': 'Busca Coca-Cola, KO, etc.',
    'SEC directory unavailable: {err}': 'Directorio de la SEC no disponible: {err}',
    'Configure INTRINSIC_SEC_USER_AGENT with a real contact email.':
        'Configura INTRINSIC_SEC_USER_AGENT con un correo de contacto real.',
    'Search any company filed with the SEC in the sidebar to open its workspace. For the fully tested '
    'experience, switch back to <b>Top 25 companies</b>.':
        'Busca en la barra lateral cualquier empresa registrada en la SEC para abrir su espacio de trabajo. '
        'Para la experiencia completamente probada, vuelve a <b>Top 25 empresas</b>.',
    'Universal engine · beta': 'Motor universal · beta',
    'Top 25 · fully tested': 'Top 25 · probado a fondo',

    # ---- beta notice
    'Beta': 'Beta',
    'Universal engine in development': 'Motor universal en desarrollo',
    "You are searching the full SEC universe. Intrinsic's model is fully tested on the <b>25 largest US "
    "companies</b>; extending it to every company that files with the SEC is still in progress. Some companies "
    "will be refused, show incomplete data or need manual inputs while that work continues &mdash; thank you for "
    "your patience. In a random test of 60 non-financial SEC companies, about 1 in 3 can be valued today; the rest "
    "are refused with the reason shown (foreign filers, loss-making companies, missing data).":
        'Estás buscando en todo el universo de la SEC. El modelo de Intrinsic está probado a fondo con las '
        '<b>25 empresas más grandes de EE. UU.</b>; extenderlo a todas las empresas que reportan a la SEC sigue en '
        'desarrollo. Algunas empresas serán rechazadas, mostrarán datos incompletos o necesitarán datos manuales '
        'mientras avanza ese trabajo &mdash; gracias por tu paciencia. En una prueba aleatoria con 60 empresas no '
        'financieras de la SEC, hoy se puede valorar aproximadamente 1 de cada 3; las demás se rechazan mostrando '
        'el motivo (emisores extranjeros, empresas con pérdidas, datos faltantes).',
    'Intrinsic is a portfolio project by a recent graduate, built to demonstrate financial modelling and data '
    'engineering. It is not a professional investment tool, and nothing here is investment advice.':
        'Intrinsic es un proyecto de portafolio de un recién graduado, creado para demostrar modelación financiera '
        'e ingeniería de datos. No es una herramienta profesional de inversión y nada aquí constituye asesoría de '
        'inversión.',

    # ---- header and routing
    'DCF · FCFF, 10-year': 'DCF · FCFF, 10 años',
    'Not valued': 'No valorada',
    'Research tool, not investment advice': 'Herramienta de investigación, no asesoría de inversión',
    'Outside the scope of this model': 'Fuera del alcance de este modelo',
    'Banks earn money on their balance sheet: debt is raw material, not financing, so free cash flow to the firm '
    'and WACC are not meaningful. They need an equity-based model (dividend or excess-return) with regulatory capital.':
        'Los bancos ganan dinero con su balance: la deuda es materia prima, no financiamiento, así que el flujo de '
        'caja libre de la empresa y el WACC no tienen sentido. Necesitan un modelo basado en el patrimonio '
        '(dividendos o retorno en exceso) con capital regulatorio.',
    'Insurers invest premiums before paying claims; cash flow depends on reserves and regulatory capital, which an '
    'FCFF model does not capture.':
        'Las aseguradoras invierten las primas antes de pagar siniestros; su flujo de caja depende de reservas y '
        'capital regulatorio, que un modelo FCFF no captura.',
    'REITs are valued on funds from operations (FFO/AFFO) or net asset value.':
        'Los REIT se valoran por fondos de operaciones (FFO/AFFO) o por valor neto de activos.',
    'Holding and investment companies are valued as the sum of their parts.':
        'Las sociedades de cartera y de inversión se valoran como la suma de sus partes.',
    'Intrinsic values non-financial operating companies with a free-cash-flow-to-the-firm model. Rather than force '
    'a number that would look precise but be wrong, this company is not valued. A sector-specific engine for '
    'financial companies is on the roadmap.':
        'Intrinsic valora empresas operativas no financieras con un modelo de flujo de caja libre de la empresa. En '
        'lugar de forzar un número que parecería preciso pero sería incorrecto, esta empresa no se valora. Un motor '
        'específico para empresas financieras está en la hoja de ruta.',
    'Not enough SEC data to value this company': 'No hay suficientes datos de la SEC para valorar esta empresa',
    'Rather than fill gaps with guesses, Intrinsic does not produce a value. Try another company, or one of the Top 25.':
        'En lugar de llenar los vacíos con suposiciones, Intrinsic no produce un valor. Prueba con otra empresa o '
        'con una del Top 25.',

    # ---- sidebar: assumptions and WACC
    'Assumptions': 'Supuestos',
    'Discount rate (WACC)': 'Tasa de descuento (WACC)',
    'WACC Calculation Mode': 'Modo de cálculo del WACC',
    'Automatic Calculation': 'Cálculo automático',
    'Manual Override': 'Ingreso manual',
    'Automatic WACC uses company-specific market and financial data. Review source dates and assumptions before '
    'relying on the result.':
        'El WACC automático usa datos financieros y de mercado de la empresa. Revisa las fechas de las fuentes y '
        'los supuestos antes de confiar en el resultado.',
    'Loading market and SEC data...': 'Cargando datos de mercado y de la SEC...',
    'Unable to load automatic WACC data: {err}': 'No se pudieron cargar los datos automáticos del WACC: {err}',
    'Check the data sources or switch to Manual Override.':
        'Revisa las fuentes de datos o cambia a ingreso manual.',
    'Market data {market} · SEC debt balance {debt}': 'Datos de mercado {market} · deuda en balance SEC {debt}',
    'Risk-free rate (%)': 'Tasa libre de riesgo (%)',
    'Stock regression (Blume-adjusted)': 'Regresión de la acción (ajuste de Blume)',
    'Yahoo regression beta {raw:.2f}, Blume-adjusted {blume:.2f}':
        'beta de regresión de Yahoo {raw:.2f}, ajustada por Blume {blume:.2f}',
    'Yahoo Finance has no regression beta for this stock': 'Yahoo Finance no tiene beta de regresión para esta acción',
    'Beta basis (industry)': 'Base de la beta (industria)',
    'Matched automatically from SEC SIC {sic} ({match} match). ':
        'Asignada automáticamente desde el SIC {sic} de la SEC (coincidencia {match}). ',
    'No industry match ({reason}). ': 'Sin industria asignada ({reason}). ',
    "Change it when the company's main risk sits in another business (one SIC code cannot describe a "
    "multi-segment company).":
        'Cámbiala cuando el riesgo principal de la empresa esté en otro negocio (un solo código SIC no describe a '
        'una empresa con varios segmentos).',
    "Industry (bottom-up) beta: {industry} unlevered beta {bu:.2f} (cash-corrected, {n} US firms; Damodaran, Jan "
    "2026), relevered with this company's debt / market equity of {de:.0%} at a {tax:.0%} marginal tax rate. For "
    "comparison: {regression}. Industry averages are far less noisy than one stock's regression. Type another "
    "value to override.":
        'Beta de industria (bottom-up): {industry}, beta desapalancada {bu:.2f} (corregida por caja, {n} empresas de '
        'EE. UU.; Damodaran, ene 2026), reapalancada con la deuda / capitalización de esta empresa de {de:.0%} y una '
        'tasa impositiva marginal de {tax:.0%}. Como comparación: {regression}. Los promedios de industria tienen '
        'mucho menos ruido que la regresión de una sola acción. Escribe otro valor para reemplazarla.',
    'Yahoo regression beta {raw:.2f} with the Blume adjustment (0.67 × raw + 0.33). Single-stock betas are noisy. '
    'Type another value to override.':
        'Beta de regresión de Yahoo {raw:.2f} con el ajuste de Blume (0,67 × original + 0,33). Las betas de una sola '
        'acción tienen mucho ruido. Escribe otro valor para reemplazarla.',
    'Beta (levered)': 'Beta (apalancada)',
    'broad SIC match, check the industry': 'coincidencia SIC amplia, revisa la industria',
    'only {n} firms in industry': 'solo {n} empresas en la industria',
    'Beta source: industry · {detail}': 'Fuente de la beta: industria · {detail}',
    'Beta source: stock regression (Blume)': 'Fuente de la beta: regresión de la acción (Blume)',
    'Equity risk premium (%)': 'Prima de riesgo de mercado (%)',
    'The premium investors demand over Treasuries for the US market as a whole.':
        'La prima que exigen los inversionistas sobre los bonos del Tesoro para el mercado de EE. UU. en conjunto.',
    'Assumption: risk-free + 1.11% (BBB default spread, Damodaran Jan 2026) because SEC filings do not tag interest '
    'expense for this company. Edit if you know its rating.':
        'Supuesto: tasa libre de riesgo + 1,11% (spread de una calificación BBB, Damodaran ene 2026), porque los '
        'reportes de la SEC no etiquetan el gasto por intereses de esta empresa. Edítalo si conoces su calificación.',
    '. For comparison, historical interest / average debt was {kd:.2%} (FY {fy}), which reflects older coupons '
    "rather than today's borrowing cost.":
        '. Como comparación, el interés histórico / deuda promedio fue {kd:.2%} (año fiscal {fy}), que refleja '
        'cupones antiguos y no el costo actual de endeudarse.',
    'Pre-tax cost of debt (%)': 'Costo de la deuda antes de impuestos (%)',
    'Cost of debt: synthetic rating from interest coverage': 'Costo de la deuda: calificación sintética por cobertura de intereses',
    'Cost of debt: assumed BBB spread · interest coverage unavailable':
        'Costo de la deuda: spread BBB supuesto · cobertura de intereses no disponible',
    'Marginal tax rate (%)': 'Tasa impositiva marginal (%)',
    'Used for the debt tax shield; matches the long-run tax rate in the forecast.':
        'Se usa para el escudo fiscal de la deuda; coincide con la tasa impositiva de largo plazo de la proyección.',
    'Market capitalization': 'Capitalización de mercado',
    'Total debt': 'Deuda total',
    'Cost of equity': 'Costo del patrimonio',
    'WACC': 'WACC',
    'Every input shows its source under the ? icon and stays editable. Defaults: live 10-year Treasury, Damodaran '
    'implied ERP and industry beta, synthetic-rating cost of debt, 25% marginal tax.':
        'Cada dato muestra su fuente en el ícono ? y se puede editar. Valores por defecto: bono del Tesoro a 10 años '
        'del día, prima implícita y beta de industria de Damodaran, costo de la deuda por calificación sintética y '
        'tasa marginal de 25%.',
    'Manual WACC (%)': 'WACC manual (%)',
    'Terminal growth (%)': 'Crecimiento terminal (%)',

    # ---- sidebar: market reference
    'Market price & shares': 'Precio de mercado y acciones',
    'Market Data Mode': 'Modo de datos de mercado',
    'Automatic': 'Automático',
    'Loading market reference...': 'Cargando referencia de mercado...',
    'Market reference unavailable: {err}': 'Referencia de mercado no disponible: {err}',
    'Market data unavailable. Retry or use manual inputs after restoring the data source.':
        'Datos de mercado no disponibles. Reintenta o usa datos manuales.',
    'Market price': 'Precio de mercado',
    'Shares outstanding': 'Acciones en circulación',
    'Yahoo Finance · retrieved {ts} UTC': 'Yahoo Finance · obtenido {ts} UTC',
    'Market Price (USD)': 'Precio de mercado (USD)',
    'Shares Outstanding (shares)': 'Acciones en circulación (acciones)',
    'Manual values are illustrative until verified.': 'Los valores manuales son ilustrativos hasta verificarlos.',
    'Fallback share count from SEC common stock is not necessarily diluted; market price default $100 is a '
    'placeholder. Enter verified figures.':
        'El número de acciones de respaldo de la SEC no necesariamente está diluido; el precio de $100 por defecto es '
        'un marcador. Ingresa cifras verificadas.',
    'WACC must be greater than Terminal Growth.': 'El WACC debe ser mayor que el crecimiento terminal.',
    'Discount rate': 'Tasa de descuento',
    'Terminal growth': 'Crecimiento terminal',
    'Manual': 'Manual',
    'Auto': 'Auto',
    'Edited': 'Editado',
    'Default': 'Por defecto',
    'Manual input': 'Dato manual',
    'Yahoo Finance · {ts} UTC': 'Yahoo Finance · {ts} UTC',

    # ---- forecast assumptions (sidebar)
    'Forecast assumptions': 'Supuestos de proyección',
    'Pre-filled with Model 27 values. Change any number to run your own case; changed inputs are labelled '
    '"Your input".':
        'Precargados con los valores del Modelo 27. Cambia cualquier número para correr tu propio caso; los datos '
        'cambiados se marcan como "Tu dato".',
    'Reset to model values': 'Volver a los valores del modelo',
    'Revenue growth next year (%)': 'Crecimiento de ingresos el próximo año (%)',
    'Model estimate for next year. Growth then slows toward the terminal rate at the calibrated speed.':
        'Estimación del modelo para el próximo año. Luego el crecimiento se desacelera hacia la tasa terminal a la '
        'velocidad calibrada.',
    'Long-run operating margin (%)': 'Margen operativo de largo plazo (%)',
    "Operating margin before amortisation of acquired intangibles that the business converges to. Default: median "
    "of the company's prior 9 years.":
        'Margen operativo, antes de la amortización de intangibles adquiridos, al que converge el negocio. Por '
        'defecto: mediana de los 9 años anteriores de la empresa.',
    'Fixed assets per $ of revenue (%)': 'Activos fijos por cada $ de ingresos (%)',
    'Net PP&E / revenue in the long run. Higher = more capital-intensive = more CapEx to grow.':
        'Activo fijo neto / ingresos en el largo plazo. Más alto = más intensivo en capital = más CapEx para crecer.',
    'Working capital % of revenue (%)': 'Capital de trabajo como % de ingresos (%)',
    'Operating working capital / revenue. Negative values mean suppliers/customers finance growth.':
        'Capital de trabajo operativo / ingresos. Los valores negativos significan que proveedores o clientes '
        'financian el crecimiento.',
    'Long-run tax rate (%)': 'Tasa impositiva de largo plazo (%)',
    'Tax rate the company converges to by year 10 (US statutory 21% + ~4% state by default).':
        'Tasa impositiva a la que converge la empresa al año 10 (21% federal de EE. UU. + ~4% estatal por defecto).',

    # ---- workspace controls and states
    'Loading SEC financial statements...': 'Cargando estados financieros de la SEC...',
    'SEC financial data unavailable for {ticker}: {err}': 'Datos financieros de la SEC no disponibles para {ticker}: {err}',
    'Not valued with FCFF: {category} — {reason}': 'No valorada con FCFF: {category} — {reason}',
    'Valuation blocked: the debt, cash or share count could not be verified from SEC filings.':
        'Valoración bloqueada: no se pudo verificar la deuda, la caja o el número de acciones en los reportes de la SEC.',
    'Valuation blocked — required SEC data is missing:': 'Valoración bloqueada — faltan datos requeridos de la SEC:',
    'Dashboard section': 'Sección del dashboard',
    'Overview': 'Resumen',
    'Forecast': 'Proyección',
    'Valuation': 'Valoración',
    'Sensitivity': 'Sensibilidad',
    'Model & Data': 'Modelo y datos',
    'Risk & return': 'Riesgo y rendimiento',
    'Security Market Line': 'Línea del mercado de valores (SML)',
    '{scen} scenario · CAPM required return vs the return implied by the market price':
        'Escenario {scen} · rendimiento requerido por CAPM vs el implícito en el precio de mercado',
    'Needs the automatic discount rate': 'Requiere la tasa de descuento automática',
    'The Security Market Line is built from the beta, risk-free rate and equity risk premium. With a manual WACC those '
    'inputs are unknown; switch the discount rate to Automatic Calculation in the sidebar.':
        'La línea del mercado de valores se construye con la beta, la tasa libre de riesgo y la prima de riesgo del '
        'mercado. Con un WACC manual esos datos no se conocen; cambia la tasa de descuento a Cálculo automático en la '
        'barra lateral.',
    'Required return': 'Rendimiento requerido',
    'Implied return': 'Rendimiento implícito',
    'Alpha': 'Alfa',
    '{rf} + {b:.2f} × {erp}': '{rf} + {b:.2f} × {erp}',
    'at market price {mp}': 'al precio de mercado {mp}',
    'implied − required': 'implícito − requerido',
    'Reference': 'Referencia',
    'Risk-free': 'Libre de riesgo',
    'Market': 'Mercado',
    'Expected return (%)': 'Rendimiento esperado (%)',
    'stock regression (Blume)': 'regresión de la acción (Blume)',
    'No implied return: the market price is outside the values the model produces for a discount rate between '
    'terminal growth and 40%.':
        'Sin rendimiento implícito: el precio de mercado está fuera de los valores que el modelo produce con una tasa '
        'de descuento entre el crecimiento terminal y 40%.',
    'Above the line: at {mp} the stock offers more return than CAPM requires for its beta — it looks undervalued for '
    'its risk.':
        'Sobre la línea: a {mp} la acción ofrece más rendimiento del que CAPM exige para su beta — parece '
        'infravalorada para su riesgo.',
    'Below the line: at {mp} the stock offers less return than CAPM requires for its beta — it looks overvalued for '
    'its risk.':
        'Bajo la línea: a {mp} la acción ofrece menos rendimiento del que CAPM exige para su beta — parece '
        'sobrevalorada para su riesgo.',
    "Implied return = cost of equity that makes the DCF value equal the market price (implied WACC {w}, capital weights "
    "held at market values). The beta that would justify today's price is {bi:.2f}.":
        'Rendimiento implícito = costo del patrimonio con el que el valor DCF iguala el precio de mercado (WACC implícito '
        '{w}, pesos de capital a valor de mercado). La beta que justificaría el precio actual es {bi:.2f}.',
    'Scenario': 'Escenario',
    'Conservative': 'Conservador',
    'Base': 'Base',
    'Optimistic': 'Optimista',
    'Not valued in the {scen} scenario': 'No valorada en el escenario {scen}',
    'In this scenario the forecast never reaches a positive operating profit, so there is no going-concern terminal '
    'value to discount. Intrinsic does not value loss-making companies yet; try another scenario if one is '
    'available, or adjust the long-run margin under Forecast assumptions.':
        'En este escenario la proyección nunca alcanza una utilidad operativa positiva, así que no hay un valor '
        'terminal de empresa en marcha que descontar. Intrinsic todavía no valora empresas con pérdidas; prueba otro '
        'escenario si está disponible o ajusta el margen de largo plazo en Supuestos de proyección.',
    'Some inputs are estimated or adjusted — see Model & Data for details.':
        'Algunos datos son estimados o ajustados — ver Modelo y datos para más detalle.',
    'Your case': 'Tu caso',
    'You are viewing YOUR case: <b>{fields}</b> changed from model values. Use "Reset to model values" in the '
    'sidebar to go back.':
        'Estás viendo TU caso: cambiaste <b>{fields}</b> respecto de los valores del modelo. Usa "Volver a los '
        'valores del modelo" en la barra lateral para regresar.',
    'revenue growth': 'crecimiento de ingresos',
    'long-run margin': 'margen de largo plazo',
    'fixed assets per $ of revenue': 'activos fijos por $ de ingresos',
    'working capital': 'capital de trabajo',
    'tax rate': 'tasa impositiva',

    # ---- company strip
    'Market price · USD': 'Precio de mercado · USD',
    'Market cap': 'Capitalización',
    'price × shares outstanding': 'precio × acciones en circulación',
    'Financials': 'Estados financieros',
    '{n} 10-K years · FYE {fye}': '{n} años de 10-K · cierre {fye}',
    'Balance sheet': 'Balance',
    'Industry (SIC)': 'Industria (SIC)',
    'Data status': 'Estado de los datos',
    'Complete': 'Completo',
    'Degraded': 'Degradado',
    'see Model & Data': 'ver Modelo y datos',
    'Latest market reference': 'Última referencia de mercado',

    # ---- overview
    'Model estimate · {scen}': 'Estimación del modelo · {scen}',
    'Intrinsic value per share · 10-year FCFF DCF': 'Valor intrínseco por acción · DCF FCFF a 10 años',
    'Market · your input': 'Mercado · tu dato',
    'Live market data': 'Datos de mercado en vivo',
    'Implied': 'Implícito',
    'Upside': 'Potencial alza',
    'Downside': 'Potencial baja',
    '{word} · intrinsic vs market': '{word} · intrínseco vs mercado',
    'Valuation range vs market price': 'Rango de valoración vs precio de mercado',
    'Enterprise value': 'Valor de la empresa',
    'PV FCFF + PV terminal': 'VP FCFF + VP terminal',
    'Equity value': 'Valor del patrimonio',
    'EV − net debt': 'VE − deuda neta',
    'Net debt': 'Deuda neta',
    'SEC balance sheet': 'Balance SEC',
    'manual override': 'ingreso manual',
    'sourced inputs · editable': 'datos con fuente · editables',
    'your input': 'tu dato',
    'default · editable': 'por defecto · editable',
    'Terminal share of EV': 'Peso terminal en el VE',
    'value after year 10': 'valor después del año 10',
    'Not valued: {scenarios} scenario — {reasons}.': 'No valorado: escenario {scenarios} — {reasons}.',
    'no positive terminal operating profit': 'sin utilidad operativa terminal positiva',
    'Market price is above the optimistic case': 'El precio de mercado está por encima del caso optimista',
    'Market price is below the conservative case': 'El precio de mercado está por debajo del caso conservador',
    'Market price is inside the model range': 'El precio de mercado está dentro del rango del modelo',
    "The market price (${mp:,.2f}) is ABOVE even the optimistic scenario (${hi:,.2f}): the market expects more "
    "growth, margin or longer-lasting advantages than the model's optimistic case.":
        'El precio de mercado (${mp:,.2f}) está POR ENCIMA incluso del escenario optimista (${hi:,.2f}): el mercado '
        'espera más crecimiento, margen o ventajas más duraderas que el caso optimista del modelo.',
    "The market price (${mp:,.2f}) is BELOW even the conservative scenario (${lo:,.2f}): the market is more "
    "pessimistic than the model's conservative case.":
        'El precio de mercado (${mp:,.2f}) está POR DEBAJO incluso del escenario conservador (${lo:,.2f}): el mercado '
        'es más pesimista que el caso conservador del modelo.',
    "The market price (${mp:,.2f}) is INSIDE the model's range (${lo:,.2f} – ${hi:,.2f}): the market's expectations "
    "are consistent with the model's uncertainty.":
        'El precio de mercado (${mp:,.2f}) está DENTRO del rango del modelo (${lo:,.2f} – ${hi:,.2f}): las '
        'expectativas del mercado son consistentes con la incertidumbre del modelo.',
    'falls': 'baja',
    'rises': 'sube',
    'stays': 'se mantiene',
    'to': 'a',
    'near': 'cerca de',
    '<strong>Biggest assumption — operating margin:</strong> the forecast assumes it {move} from {m0:.1%} (latest '
    'year) {prep} {mT:.1%} in the long run ({note}). ':
        '<strong>Supuesto más importante — margen operativo:</strong> la proyección supone que {move} de {m0:.1%} '
        '(último año) {prep} {mT:.1%} en el largo plazo ({note}). ',
    'Tested out of sample, this anchor beat recent-level alternatives on average, but a company whose business '
    'changed for good would be undervalued. ':
        'Probado fuera de muestra, este ancla superó en promedio a las alternativas basadas en niveles recientes, '
        'pero una empresa cuyo negocio cambió para siempre quedaría subvalorada. ',
    'Change it under <em>Forecast assumptions</em> to test your own view.':
        'Cámbialo en <em>Supuestos de proyección</em> para probar tu propia visión.',
    'What this means': 'Qué significa',
    '<strong>Terminal value:</strong> {share:.0%} of enterprise value comes from cash flows after year 10.':
        '<strong>Valor terminal:</strong> el {share:.0%} del valor de la empresa proviene de flujos después del año 10.',
    "<strong>How to read the range:</strong> conservative/optimistic come from the model's measured forecast "
    "errors (20th/80th percentile), not from arbitrary ±%.":
        '<strong>Cómo leer el rango:</strong> conservador/optimista salen de los errores de proyección medidos del '
        'modelo (percentiles 20/80), no de un ±% arbitrario.',
    'Data complete': 'Datos completos',
    '{n} warnings': '{n} advertencias',
    '{n} notes': '{n} notas',
    'Model transparency': 'Transparencia del modelo',
    '<strong>Validated:</strong> revenue and EBIT-margin forecasts, out of sample.<br><strong>Not validated:</strong> '
    'CapEx, D&amp;A, working-capital paths and the final valuation. Read the range, not a single number. Details '
    'under <em>Model &amp; Data</em>.':
        '<strong>Validado:</strong> proyecciones de ingresos y margen EBIT, fuera de muestra.<br><strong>No '
        'validado:</strong> trayectorias de CapEx, D&amp;A, capital de trabajo y la valoración final. Lee el rango, no '
        'un solo número. Detalles en <em>Modelo y datos</em>.',
    'company median of {n} prior years; no industry shrinkage yet':
        'mediana de la empresa en los {n} años anteriores; aún sin ajuste por industria',
    'Market data & capital structure': 'Datos de mercado y estructura de capital',
    'Net debt used (negative = net cash)': 'Deuda neta usada (negativa = caja neta)',
    'Shares used': 'Acciones usadas',
    'Share source': 'Fuente de las acciones',
    'SEC balance date': 'Fecha del balance SEC',

    # ---- forecast section
    'Financial forecast': 'Proyección financiera',
    '{scen} scenario · USD millions · years 1–5 forecast, years 6–10 fade to steady state before the terminal value':
        'Escenario {scen} · millones de USD · años 1–5 de proyección, años 6–10 de convergencia antes del valor terminal',
    'Reported': 'Reportado',
    'Revenue': 'Ingresos',
    'USD billions': 'Miles de millones USD',
    'Reported 10-K history and the three scenarios': 'Historia reportada en el 10-K y los tres escenarios',
    'EBIT margin (reported)': 'Margen EBIT (reportado)',
    'Growth (reported)': 'Crecimiento (reportado)',
    'EBIT margin': 'Margen EBIT',
    'Revenue growth': 'Crecimiento de ingresos',
    'Revenue growth and EBIT margin': 'Crecimiento de ingresos y margen EBIT',
    '{scen} scenario vs reported history': 'Escenario {scen} vs historia reportada',
    'Free cash flow to the firm': 'Flujo de caja libre de la empresa',
    'NOPAT + D&A − CapEx − change in NWC': 'NOPAT + D&A − CapEx − cambio en capital de trabajo',
    'CapEx (reported)': 'CapEx (reportado)',
    'CapEx and D&A': 'CapEx y D&A',
    'From the PP&E roll-forward, so the two stay consistent': 'Del roll-forward del activo fijo, para que ambos sean consistentes',
    'Forecast →': 'Proyección →',
    'USD millions': 'Millones de USD',
    'Growth': 'Crecimiento',
    'Change in NWC': 'Cambio en capital de trabajo',
    'A = reported (SEC 10-K, FY{y}); E = model estimate. Years 6–10 (dimmed) complete the fade to steady state. '
    'Negative values in parentheses.':
        'A = reportado (10-K de la SEC, año fiscal {y}); E = estimación del modelo. Los años 6–10 (atenuados) completan '
        'la convergencia. Valores negativos entre paréntesis.',
    'Download forecast CSV': 'Descargar proyección (CSV)',

    # ---- valuation section
    'DCF valuation breakdown': 'Desglose de la valoración DCF',
    '{scen} scenario · from free cash flow to value per share': 'Escenario {scen} · del flujo de caja libre al valor por acción',
    'PV of forecast FCFF (10 years)': 'VP del FCFF proyectado (10 años)',
    'PV of terminal value': 'VP del valor terminal',
    'Net debt (negative = net cash)': 'Deuda neta (negativa = caja neta)',
    'Diluted shares': 'Acciones diluidas',
    'Intrinsic value / share': 'Valor intrínseco / acción',
    'Equity bridge': 'Puente al patrimonio',
    'Metric': 'Métrica',
    'Value': 'Valor',
    'steady-state reinvestment (advantages persist)': 'reinversión de estado estable (las ventajas persisten)',
    'RONIC = WACC (advantages fade)': 'RONIC = WACC (las ventajas se desvanecen)',
    'Terminal value': 'Valor terminal',
    'Method': 'Método',
    'Reinvestment rate': 'Tasa de reinversión',
    '{x:.1%} of NOPAT': '{x:.1%} del NOPAT',
    'Implied RONIC': 'RONIC implícito',
    'Share of enterprise value': 'Peso en el valor de la empresa',
    'Balance date {date} · Debt: {debt} · Non-operating investments at book value (verify their income is excluded '
    'from EBIT).':
        'Fecha del balance {date} · Deuda: {debt} · Inversiones no operativas a valor en libros (verifica que su '
        'ingreso esté excluido del EBIT).',
    'How the value builds up': 'Cómo se construye el valor',
    "Present value of each year's free cash flow, then the terminal value → enterprise value":
        'Valor presente del flujo de caja libre de cada año, luego el valor terminal → valor de la empresa',
    'Enterprise Value': 'Valor de la empresa',
    'Total debt (incl. finance leases)': 'Deuda total (incl. arrendamientos financieros)',
    'Cash & equivalents': 'Efectivo y equivalentes',
    'Short-term investments': 'Inversiones de corto plazo',
    'Equity-method investments': 'Inversiones por método de participación',
    'Long-term marketable securities': 'Valores negociables de largo plazo',
    'Equity Value': 'Valor del patrimonio',
    'From enterprise value to equity value': 'Del valor de la empresa al valor del patrimonio',
    'Debt is deducted; cash, short-term and non-operating investments are added':
        'Se resta la deuda; se suman la caja, las inversiones de corto plazo y las no operativas',

    # ---- sensitivity
    'WACC × terminal growth sensitivity': 'Sensibilidad WACC × crecimiento terminal',
    '{scen} scenario · intrinsic value per share and upside vs market price':
        'Escenario {scen} · valor intrínseco por acción y potencial vs precio de mercado',
    'Colour midpoint = market price (${mp:,.2f}): green cells are above the market, red below. Outlined cell = '
    'current inputs. N/A = WACC not above growth, or no positive terminal profit.':
        'Punto medio del color = precio de mercado (${mp:,.2f}): las celdas verdes están por encima del mercado y las '
        'rojas por debajo. Celda remarcada = datos actuales. N/A = WACC no mayor que el crecimiento, o sin utilidad '
        'terminal positiva.',
    'Download Sensitivity CSV': 'Descargar sensibilidad (CSV)',

    # ---- model & data
    'Model & data': 'Modelo y datos',
    'What is validated, where each assumption comes from, and every data check':
        'Qué está validado, de dónde sale cada supuesto y todas las revisiones de datos',
    'Validated out of sample': 'Validado fuera de muestra',
    'Revenue and EBIT-margin forecasts passed <strong>{ok}/{n}</strong> pre-registered out-of-sample criteria '
    '(fresh companies, parameters estimated with data ≤2018, forecasts 2019–2025).':
        'Las proyecciones de ingresos y margen EBIT cumplieron <strong>{ok}/{n}</strong> criterios fuera de muestra '
        'registrados de antemano (empresas nuevas, parámetros estimados con datos ≤2018, proyecciones 2019–2025).',
    'Not validated': 'No validado',
    'What is NOT validated: CapEx, D&amp;A and working-capital paths (consistent by construction, not tested as '
    'forecasts) and the final valuation. Use the range, not a single number.':
        'Lo que NO está validado: las trayectorias de CapEx, D&amp;A y capital de trabajo (consistentes por '
        'construcción, no probadas como proyecciones) y la valoración final. Usa el rango, no un solo número.',
    'Assumptions and where each comes from': 'Supuestos y de dónde sale cada uno',
    'Company data': 'Dato de la empresa',
    'Calibrated (panel)': 'Calibrado (panel)',
    'Economic assumption': 'Supuesto económico',
    'Your input': 'Tu dato',
    'Driver': 'Variable',
    'Source': 'Fuente',
    'Explanation': 'Explicación',
    'Data quality and consistency checks': 'Calidad de datos y revisiones de consistencia',
    'No blockers': 'Sin bloqueos',
    'No degradations': 'Sin degradaciones',
    'Required SEC inputs were found for this scenario.': 'Se encontraron los datos requeridos de la SEC para este escenario.',
    'Notes': 'Notas',
    'Consistency checks and capital flags': 'Revisiones de consistencia y alertas de capital',
    'Method: driver-based FCFF with panel-calibrated mean reversion (2,578 US companies), PP&E roll-forward, full '
    'operating NWC, capitalised R&D and steady-state terminal reinvestment.':
        'Método: FCFF basado en impulsores con reversión a la media calibrada en un panel (2.578 empresas de EE. UU.), '
        'roll-forward del activo fijo, capital de trabajo operativo completo, I+D capitalizado y reinversión terminal '
        'de estado estable.',
    'Explanations in this table come from the valuation engine and are shown in English.':
        'Las explicaciones de esta tabla vienen del motor de valoración y se muestran en inglés.',

    # ---- acronyms used as row labels (identical in Spanish)
    'CapEx': 'CapEx', 'D&A': 'D&A', 'EBIT': 'EBIT', 'FCFF': 'FCFF', 'NOPAT': 'NOPAT', 'ROIC': 'ROIC',

    # ---- range bar / legend
    'USD per share': 'USD por acción',
    'MKT': 'MERC.',
    '(selected)': '(seleccionado)',
    'Band = conservative → optimistic': 'Banda = conservador → optimista',
}

GLOSSARY_ES = {
    'Security Market Line': ('Línea del mercado de valores', 'Recta del CAPM: rendimiento requerido = tasa libre de '
                             'riesgo + beta × prima de riesgo del mercado. Toda acción con precio justo está sobre ella.'),
    'Beta': ('Beta', 'Sensibilidad de la acción al mercado. Beta 1 se mueve con el mercado; mayor que 1 lo amplifica.'),
    'Required return': ('Rendimiento requerido', 'Rendimiento que exigen los inversionistas por el riesgo de la acción: '
                        'el costo del patrimonio según CAPM, un punto sobre la recta.'),
    'Implied return': ('Rendimiento implícito', 'Costo del patrimonio con el que el valor DCF iguala el precio de mercado '
                       'actual: lo que se gana comprando a ese precio si se cumple la proyección.'),
    'Alpha': ('Alfa', 'Rendimiento implícito − requerido. Positivo (sobre la recta) = barata para su riesgo; negativo = cara.'),
    'Intrinsic value': ('Valor intrínseco', 'Valor justo estimado por acción: valor presente de los flujos de caja '
                        'libres proyectados más el valor terminal, menos la deuda neta, dividido por las acciones diluidas.'),
    'Market price': ('Precio de mercado', 'Referencia actual del precio de la acción (Yahoo Finance o tu dato manual).'),
    'Upside / downside': ('Potencial alza / baja', 'Valor intrínseco vs precio de mercado: (intrínseco / mercado − 1) × 100.'),
    'WACC': ('WACC', 'Costo de capital promedio ponderado: la tasa con que se descuentan los flujos futuros. Un WACC '
             'más alto → menor valor.'),
    'Scenario': ('Escenario', 'Conservador y optimista usan los percentiles 20 y 80 de los errores reales fuera de '
                 'muestra del modelo para ingresos y margen. El conservador además supone que las ventajas '
                 'competitivas se desvanecen (las nuevas inversiones solo rinden el WACC).'),
    'Revenue growth': ('Crecimiento de ingresos', 'Cambio anual esperado en las ventas. El Modelo 27 parte del último '
                       'año y se desacelera hacia el crecimiento de largo plazo a la velocidad observada en miles de '
                       'empresas.'),
    'EBIT': ('EBIT', 'Utilidad antes de intereses e impuestos: utilidad operativa.'),
    'EBIT margin': ('Margen EBIT', 'EBIT como porcentaje de los ingresos.'),
    'NOPAT': ('NOPAT', 'Utilidad operativa neta después de impuestos: EBIT × (1 − tasa impositiva). Con el I+D '
              'capitalizado, el I+D se suma de vuelta y se carga su amortización.'),
    'D&A': ('D&A', 'Depreciación y amortización: costo no monetario de usar activos fijos, que se suma de vuelta al '
            'flujo de caja.'),
    'CapEx': ('CapEx', 'Inversión de capital: efectivo invertido en activos de largo plazo. En el Modelo 27, CapEx = '
              'crecimiento del activo fijo + depreciación (+ activos que salen sin depreciarse), así CapEx y D&A son '
              'consistentes.'),
    'Change in NWC': ('Cambio en capital de trabajo', 'Cambio en el capital de trabajo operativo (cuentas por cobrar + '
                      'inventario − cuentas por pagar, etc.). Negativo significa que el crecimiento libera caja '
                      '(p. ej. Amazon).'),
    'FCFF': ('FCFF', 'Flujo de caja libre de la empresa: NOPAT + D&A − CapEx − cambio en capital de trabajo. Caja '
             'disponible para todos los inversionistas.'),
    'ROIC': ('ROIC', 'Retorno sobre el capital invertido: NOPAT / capital operativo al inicio del año.'),
    'Reinvestment rate': ('Tasa de reinversión', 'Parte del NOPAT que se reinvierte (CapEx neto + capital de trabajo + '
                          'I+D) para financiar el crecimiento.'),
    'PV of FCFF': ('VP del FCFF', 'Valor presente de los 10 flujos de caja libres proyectados, descontados al WACC.'),
    'Terminal value': ('Valor terminal', 'Valor de todos los flujos después del año 10, creciendo a la tasa terminal. '
                       'Descuenta la reinversión necesaria para sostener ese crecimiento.'),
    'Enterprise value': ('Valor de la empresa', 'Valor del negocio operativo: VP del FCFF + VP del valor terminal.'),
    'Net debt': ('Deuda neta', 'Deuda (incl. arrendamientos financieros) − caja − inversiones de corto plazo − '
                 'inversiones no operativas. Negativa = caja neta.'),
    'Equity value': ('Valor del patrimonio', 'Valor de la empresa − deuda neta: el valor que pertenece a los accionistas.'),
    'Terminal growth': ('Crecimiento terminal', 'Crecimiento perpetuo después del año 10. Debe ser menor que el WACC; '
                        'normalmente ≤ crecimiento del PIB de largo plazo.'),
    'Sensitivity matrix': ('Matriz de sensibilidad', 'Valor intrínseco por acción para distintas combinaciones de WACC '
                           'y crecimiento terminal. No es un pronóstico de probabilidades.'),
    'Terminal share': ('Peso terminal', 'Parte del valor de la empresa que proviene de flujos después del año 10 '
                       '(VP del valor terminal / VE).'),
}
