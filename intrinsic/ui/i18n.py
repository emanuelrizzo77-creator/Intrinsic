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
    "your patience. In a random test of 60 non-financial SEC companies, about 2 in 3 can be valued today; the "
    "rest are refused with the reason shown (development-stage companies, missing or unusable data).":
        'Estás buscando en todo el universo de la SEC. El modelo de Intrinsic está probado a fondo con las '
        '<b>25 empresas más grandes de EE. UU.</b>; extenderlo a todas las empresas que reportan a la SEC sigue en '
        'desarrollo. Algunas empresas serán rechazadas, mostrarán datos incompletos o necesitarán datos manuales '
        'mientras avanza ese trabajo &mdash; gracias por tu paciencia. En una prueba aleatoria con 60 empresas no '
        'financieras de la SEC, hoy se pueden valorar aproximadamente 2 de cada 3; las demás se rechazan mostrando '
        'el motivo (empresas en etapa de desarrollo, datos faltantes o inutilizables).',
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
    'What the three cases mean': 'Qué significa cada caso',
    'Three versions of the future, not three opinions: the range shows how much the value depends on how the business turns out':
        'Tres versiones del futuro, no tres opiniones: el rango muestra cuánto depende el valor de cómo le vaya al negocio',
    'not valued': 'sin valorar',
    "What the stock is worth if things go worse than expected. Revenue and margin land at the 20th percentile of the model's past forecast errors (only 1 in 5 past forecasts came out worse), and after year 10 new investment earns only its cost of capital, so growth adds no value.":
        'Lo que vale la acción si las cosas salen peor de lo esperado. Ingresos y margen quedan en el percentil 20 de '
        'los errores pasados del modelo (solo 1 de cada 5 pronósticos salió peor), y después del año 10 la nueva '
        'inversión rinde solo su costo de capital, así que crecer no agrega valor.',
    "The central case: the most likely path. Growth fades from its latest rate toward typical company growth and then to the terminal rate; the margin moves toward the company's own long-run median.":
        'El caso central: el camino más probable. El crecimiento baja desde su último nivel hacia el de una empresa '
        'típica y luego a la tasa terminal; el margen se acerca a la mediana histórica de la propia empresa.',
    "What the stock is worth if things go better than expected. Revenue and margin land at the 80th percentile of the model's past forecast errors (only 1 in 5 past forecasts came out better). It is a good outcome, not the best possible one.":
        'Lo que vale la acción si las cosas salen mejor de lo esperado. Ingresos y margen quedan en el percentil 80 de '
        'los errores pasados del modelo (solo 1 de cada 5 pronósticos salió mejor). Es un buen resultado, no el '
        'mejor posible.',
    'Reset to model values': 'Volver a los valores del modelo',
    'Revenue growth next year (%)': 'Crecimiento de ingresos el próximo año (%)',
    'Model estimate for next year. The excess over typical company growth then fades at the calibrated speed, and '
    'growth reaches the terminal rate by year 10.':
        'Estimación del modelo para el próximo año. Luego el exceso sobre el crecimiento típico de una empresa se '
        'disipa a la velocidad calibrada, y el crecimiento llega a la tasa terminal en el año 10.',
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
    # ---- final verdict
    'Final verdict': 'Veredicto final',
    "What the model's numbers say about buying, holding or selling at today's price":
        'Lo que dicen los números del modelo sobre comprar, mantener o vender al precio de hoy',
    'Margin of safety': 'Margen de seguridad',
    'How far value and price must differ before the model says buy or sell. A wider margin makes Hold more likely.':
        'Cuánto deben diferir el valor y el precio antes de que el modelo diga comprar o vender. Un margen más amplio '
        'hace más probable Mantener.',
    'No verdict': 'Sin veredicto',
    'The valuation range is not available for this company, so the model cannot estimate how likely each outcome is.':
        'El rango de valoración no está disponible para esta empresa, así que el modelo no puede estimar la '
        'probabilidad de cada resultado.',
    'The base scenario is not valued, so there is no verdict.':
        'El escenario base no está valorado, así que no hay veredicto.',
    'Model verdict': 'Veredicto del modelo',
    'Buy': 'Comprar',
    'Hold': 'Mantener',
    'Sell': 'Vender',
    '{p:.0%} of the model outcomes': '{p:.0%} de los resultados del modelo',
    'What it means': 'Qué significa',
    'The model values the stock above the market price by more than the margin of safety in most outcomes.':
        'En la mayoría de los resultados, el modelo valora la acción por encima del precio de mercado en más que el '
        'margen de seguridad.',
    'The model values the stock below the market price by more than the margin of safety in most outcomes.':
        'En la mayoría de los resultados, el modelo valora la acción por debajo del precio de mercado en más que el '
        'margen de seguridad.',
    'Neither buying nor selling holds a majority of the model outcomes: keep it if you own it, but there is no strong '
    'reason to buy more or to sell.':
        'Ni comprar ni vender reúne la mayoría de los resultados del modelo: mantenla si la tienes, pero no hay una '
        'razón fuerte para comprar más ni para vender.',
    'no side reaches 50% of the outcomes': 'ningún lado llega al 50% de los resultados',
    'Probability of each verdict': 'Probabilidad de cada veredicto',
    "Share of the model's value distribution in each zone":
        'Parte de la distribución de valor del modelo que cae en cada zona',
    'Where the probabilities come from': 'De dónde salen las probabilidades',
    'Model value distribution from the conservative, base and optimistic scenarios, split at the market price ± the '
    'margin of safety':
        'Distribución de valor del modelo a partir de los escenarios conservador, base y optimista, dividida en el '
        'precio de mercado ± el margen de seguridad',
    'Market {p}': 'Mercado {p}',
    'Base {p}': 'Base {p}',
    'Intrinsic value per share (USD)': 'Valor intrínseco por acción (USD)',
    'Likelihood': 'Probabilidad relativa',
    'Buy if value is above': 'Comprar si el valor supera',
    'Sell if value is below': 'Vender si el valor es menor que',
    'Probability value is above the market price': 'Probabilidad de que el valor supere el precio de mercado',
    'Why': 'Por qué',
    "This is what the model's numbers say, not investment advice or a recommendation for your portfolio.":
        'Esto es lo que dicen los números del modelo, no asesoría de inversión ni una recomendación para tu portafolio.',
    "The spread comes from the model's conservative and optimistic scenarios; uncertainty in the discount rate and "
    "terminal growth is not included, so real outcomes are wider.":
        'La dispersión viene de los escenarios conservador y optimista del modelo; no incluye la incertidumbre de la '
        'tasa de descuento ni del crecimiento terminal, así que los resultados reales son más amplios.',
    'One scenario is not valued, so the spread is estimated from the other side and assumed symmetric.':
        'Un escenario no está valorado, así que la dispersión se estima con el otro lado y se supone simétrica.',
    '<strong>Value vs price:</strong> base value {v} against a market price of {p} ({u:+.0%}).':
        '<strong>Valor vs precio:</strong> valor base {v} frente a un precio de mercado de {p} ({u:+.0%}).',
    '<strong>Value vs price:</strong> base value {v} (midpoint of both models) against a market price of {p} ({u:+.0%}).':
        '<strong>Valor vs precio:</strong> valor base {v} (punto medio de ambos modelos) frente a un precio de mercado '
        'de {p} ({u:+.0%}).',
    '<strong>Biggest assumption:</strong> operating margin from {m0:.1%} today to {mT:.1%} in the long run{path}.':
        '<strong>Supuesto principal:</strong> margen operativo de {m0:.1%} hoy a {mT:.1%} en el largo plazo{path}.',
    ' (path to its industry margin)': ' (camino al margen de su industria)',
    '<strong>Long-term weight:</strong> {s:.0%} of the value comes from after year 10, so the verdict leans on '
    'long-run assumptions.':
        '<strong>Peso del largo plazo:</strong> {s:.0%} del valor viene de después del año 10, así que el veredicto '
        'depende de supuestos de largo plazo.',
    '<strong>Loss-making company:</strong> includes a {p:.0%} probability of failure.':
        '<strong>Empresa con pérdidas:</strong> incluye una probabilidad de quiebra de {p:.0%}.',
    "<strong>Risk and return:</strong> buying at today's price implies a {i:.1%} return against the {r:.1%} its risk "
    "requires (alpha {a:+.1%}).":
        '<strong>Riesgo y rendimiento:</strong> comprar al precio de hoy implica un rendimiento de {i:.1%} frente al '
        '{r:.1%} que exige su riesgo (alfa {a:+.1%}).',
    '<strong>Data quality:</strong> some inputs are estimated or adjusted (see Model &amp; Data); treat the verdict '
    'with extra caution.':
        '<strong>Calidad de datos:</strong> algunos datos son estimados o ajustados (ver Modelo y datos); toma el '
        'veredicto con más cautela.',
    '<strong>Foreign filer:</strong> figures converted to US GAAP / USD from its Form 20-F.':
        '<strong>Emisor extranjero:</strong> cifras convertidas a US GAAP / USD desde su Form 20-F.',
    '<strong>Price to book:</strong> the market pays {m:.2f}× book value; the model justifies {j:.2f}×.':
        '<strong>Precio/valor contable:</strong> el mercado paga {m:.2f}× el valor contable; el modelo justifica {j:.2f}×.',
    '<strong>Biggest assumption:</strong> long-run ROE of {r:.1%} against a {k:.1%} cost of equity.':
        '<strong>Supuesto principal:</strong> ROE de largo plazo de {r:.1%} frente a un costo del patrimonio de {k:.1%}.',
    '<strong>Model agreement:</strong> the dividend model is {g:+.0%} from the excess-return model.':
        '<strong>Acuerdo entre modelos:</strong> el modelo de dividendos está a {g:+.0%} del de retorno en exceso.',
    # ---- loss-making companies: path to profitability
    "<strong>Loss-making company — path to profitability:</strong> its own history implies losses forever, so the "
    "margin is assumed to rise in a straight line from {m0:.1%} to its industry's {mT:.1%} in {n} years. This is an "
    "assumption, not a forecast the model has validated.":
        '<strong>Empresa con pérdidas — camino a la rentabilidad:</strong> su propia historia implica pérdidas para '
        'siempre, así que se supone que el margen sube en línea recta de {m0:.1%} al {mT:.1%} de su industria en {n} '
        'años. Es un supuesto, no una proyección que el modelo haya validado.',
    '<strong>Probability of failure {p:.0%}:</strong> value = {q:.0%} × {gc} if it gets there + {p:.0%} × {ds} if it '
    'fails (shareholders keep only net cash).':
        '<strong>Probabilidad de quiebra {p:.0%}:</strong> valor = {q:.0%} × {gc} si lo logra + {p:.0%} × {ds} si '
        'quiebra (los accionistas conservan solo la caja neta).',
    'Chance the company fails before becoming profitable. If it fails, shareholders get its net cash (or nothing). '
    'Default from cash runway: 5 or more years of cash 10%, 2–5 years 20%, 1–2 years 35%, under 1 year 50%; 5% if '
    'already profitable.':
        'Probabilidad de que la empresa quiebre antes de ser rentable. Si quiebra, los accionistas reciben su caja neta '
        '(o nada). Valor por defecto según cuántos años de caja le quedan: 5 o más años 10%, 2–5 años 20%, 1–2 años '
        '35%, menos de 1 año 50%; 5% si ya es rentable.',
    'Equity value if it becomes profitable': 'Valor del patrimonio si se vuelve rentable',
    'Equity value if it fails (net cash, floored at 0)': 'Valor del patrimonio si quiebra (caja neta, mínimo 0)',
    'Equity value shown if the company becomes profitable; the valuation then weights it with the probability of '
    'failure (see Equity bridge).':
        'Valor del patrimonio si la empresa se vuelve rentable; luego la valoración lo pondera con la probabilidad de '
        'quiebra (ver Puente al patrimonio).',
    'In this scenario the forecast never reaches a positive operating profit, so there is no going-concern terminal '
    'value to discount: the company would be worth only its net cash. Try another scenario, or adjust the long-run '
    'margin or the years to reach it under Forecast assumptions.':
        'En este escenario la proyección nunca llega a una utilidad operativa positiva, así que no hay valor terminal '
        'de empresa en marcha que descontar: la empresa valdría solo su caja neta. Prueba otro escenario, o ajusta el '
        'margen de largo plazo o los años para alcanzarlo en Supuestos de proyección.',
    'Probability of failure': 'Probabilidad de quiebra',
    'Probability of failure (%)': 'Probabilidad de quiebra (%)',
    'Probability-weighted equity value': 'Valor del patrimonio ponderado por probabilidad',
    "Target operating margin for this loss-making company: its industry's margin (Damodaran, Jan 2026), because its "
    "own history implies losses forever.":
        'Margen operativo meta para esta empresa con pérdidas: el margen de su industria (Damodaran, ene 2026), porque '
        'su propia historia implica pérdidas para siempre.',
    'The margin moves in a straight line from today to the target, then holds.':
        'El margen avanza en línea recta desde hoy hasta la meta y luego se mantiene.',
    'Years to reach the target margin': 'Años para alcanzar el margen meta',
    'in this scenario the company never becomes profitable, so it would be worth only its net cash':
        'en este escenario la empresa nunca se vuelve rentable, así que valdría solo su caja neta',
    'probability-weighted': 'ponderado por probabilidad',
    'years to target margin': 'años hasta el margen meta',
    'probability of failure': 'probabilidad de quiebra',
    # ---- bank engine (excess return + dividend discount)
    'Bank · excess return + DDM': 'Banco · retorno en exceso + DDM',
    'Bank assumptions': 'Supuestos del banco',
    'Cost of equity (CAPM)': 'Costo del patrimonio (CAPM)',
    'Beta basis': 'Base de la beta',
    'Industry: {name} (levered)': 'Industria: {name} (apalancada)',
    'Damodaran levered beta for {name} ({n} US firms, Jan 2026). For banks the levered beta is used directly: deposits '
    'are operating liabilities, so un/re-levering with debt is not meaningful.':
        'Beta apalancada de Damodaran para {name} ({n} empresas de EE. UU., ene 2026). En bancos se usa directamente la '
        'beta apalancada: los depósitos son pasivos operativos, así que desapalancar y reapalancar con deuda no tiene sentido.',
    'Yahoo regression beta {raw:.2f} with the Blume adjustment (0.67 × raw + 0.33).':
        'Beta de regresión de Yahoo {raw:.2f} con el ajuste de Blume (0.67 × bruta + 0.33).',
    'Risk-free rate': 'Tasa libre de riesgo',
    'Equity risk premium': 'Prima de riesgo del mercado',
    'Price: Yahoo Finance. Shares: {src}, {date}.': 'Precio: Yahoo Finance. Acciones: {src}, {date}.',
    'ROE today (%)': 'ROE actual (%)',
    'Long-run ROE (%)': 'ROE de largo plazo (%)',
    'Payout ratio today (%)': 'Tasa de pago actual (%)',
    'Base-scenario model values. Editing one applies it to every scenario.':
        'Valores del modelo en el escenario base. Si editas uno, se aplica a todos los escenarios.',
    'You are viewing YOUR case: bank assumptions changed from model values.':
        'Estás viendo TU caso: los supuestos del banco cambiaron respecto a los valores del modelo.',
    'Valuation blocked': 'Valoración bloqueada',
    'Total assets': 'Activos totales',
    'Deposits': 'Depósitos',
    'Excess return · {scen}': 'Retorno en exceso · {scen}',
    'Dividend discount · {scen}': 'Descuento de dividendos · {scen}',
    'Book value + PV of returns above the cost of equity': 'Valor contable + VP de los retornos sobre el costo del patrimonio',
    'PV of dividends + buybacks to common shareholders': 'VP de dividendos + recompras a los accionistas comunes',
    'Midpoint {mid} vs market price {mp}': 'Punto medio {mid} vs precio de mercado {mp}',
    'Valuation range vs market price (midpoint of both models)':
        'Rango de valoración vs precio de mercado (punto medio de ambos modelos)',
    'Book value / share': 'Valor contable / acción',
    'common equity · SEC': 'patrimonio común · SEC',
    'Justified P/B': 'P/VC justificado',
    'market P/B {pb:.2f}×': 'P/VC de mercado {pb:.2f}×',
    'CAPM': 'CAPM',
    'ROE': 'ROE',
    'latest year': 'último año',
    'Long-run ROE': 'ROE de largo plazo',
    'Model gap': 'Brecha entre modelos',
    'DDM vs excess return': 'DDM vs retorno en exceso',
    'The bank is expected to keep earning <b>{s} above</b> its cost of equity in the long run, so it is worth more '
    'than its book value.':
        'Se espera que el banco siga ganando <b>{s} por encima</b> de su costo del patrimonio en el largo plazo, así que '
        'vale más que su valor contable.',
    'In the long run the bank earns only its cost of equity, so growth adds no value and the price converges to book '
    'value.':
        'En el largo plazo el banco gana solo su costo del patrimonio, así que el crecimiento no agrega valor y el precio '
        'converge al valor contable.',
    '<b>Two models, one range.</b> With perfectly consistent inputs both give the same value. Here the excess-return '
    'model follows book value and ROE, while the DDM follows the bank&#39;s actual payout policy; a large gap means '
    'today&#39;s payout and growth differ from what the ROE path implies.':
        '<b>Dos modelos, un rango.</b> Con supuestos perfectamente consistentes ambos dan el mismo valor. Aquí el modelo '
        'de retorno en exceso sigue el valor contable y el ROE, mientras que el DDM sigue la política de pagos real del '
        'banco; una brecha grande significa que el pago y el crecimiento actuales difieren de lo que implica la '
        'trayectoria del ROE.',
    '<b>Why not FCFF:</b> deposits and borrowings are a bank&#39;s raw material, not financing, so free cash flow to '
    'the firm and WACC do not apply. Both models discount at the cost of equity.':
        '<b>Por qué no FCFF:</b> los depósitos y préstamos son la materia prima de un banco, no su financiamiento, así '
        'que el flujo de caja libre de la empresa y el WACC no aplican. Ambos modelos descuentan al costo del patrimonio.',
    'Return on equity: history and forecast': 'Rendimiento sobre el patrimonio: historia y proyección',
    "Fades from today's level to the long-run level; the dotted line is the cost of equity":
        'Converge del nivel actual al de largo plazo; la línea punteada es el costo del patrimonio',
    'Cost of equity {ke}': 'Costo del patrimonio {ke}',
    'Year': 'Año',
    'Book value, start (USD B)': 'Valor contable inicial (USD B)',
    'Net income to common (USD B)': 'Utilidad neta para comunes (USD B)',
    'Excess return (USD B)': 'Retorno en exceso (USD B)',
    'PV of excess return (USD B)': 'VP del retorno en exceso (USD B)',
    'DDM: earnings growth': 'DDM: crecimiento de utilidades',
    'DDM: payout ratio': 'DDM: tasa de pago',
    'DDM: dividends + buybacks (USD B)': 'DDM: dividendos + recompras (USD B)',
    'DDM: present value (USD B)': 'DDM: valor presente (USD B)',
    '10-year projection · {scen}': 'Proyección a 10 años · {scen}',
    'Valuation bridge · {scen}': 'Puente de valoración · {scen}',
    'From book value to equity value, and from payouts to equity value':
        'Del valor contable al valor del patrimonio, y de los pagos al valor del patrimonio',
    'Book value': 'Valor contable',
    'PV excess returns': 'VP retornos en exceso',
    'PV terminal': 'VP terminal',
    'PV dividends + buybacks': 'VP dividendos + recompras',
    'Excess return model (USD B)': 'Modelo de retorno en exceso (USD B)',
    'Dividend discount model (USD B)': 'Modelo de descuento de dividendos (USD B)',
    'Terminal value share': 'Peso del valor terminal',
    'Shares': 'Acciones',
    'Value per share': 'Valor por acción',
    'Implied P/B': 'P/VC implícito',
    'Excess return': 'Retorno en exceso',
    'Dividend discount': 'Descuento de dividendos',
    'Model': 'Modelo',
    'Cost of equity × terminal growth sensitivity': 'Sensibilidad costo del patrimonio × crecimiento terminal',
    '{scen} scenario · value per share and upside vs market price':
        'Escenario {scen} · valor por acción y potencial vs precio de mercado',
    'Colour midpoint = market price (${mp:,.2f}). Outlined cell = current inputs. N/A = cost of equity not above growth, '
    'or long-run ROE not above growth.':
        'Punto medio del color = precio de mercado (${mp:,.2f}). Celda marcada = supuestos actuales. N/A = costo del '
        'patrimonio no mayor que el crecimiento, o ROE de largo plazo no mayor que el crecimiento.',
    'No implied return: the market price is outside the values the excess-return model produces for a cost of equity '
    'between terminal growth and 40%.':
        'Sin rendimiento implícito: el precio de mercado está fuera de los valores que produce el modelo de retorno en '
        'exceso con un costo del patrimonio entre el crecimiento terminal y 40%.',
    "Implied return = cost of equity at which the excess-return value equals the market price. The beta that would "
    "justify today's price is {bi:.2f}.":
        'Rendimiento implícito = costo del patrimonio con el que el valor por retorno en exceso iguala el precio de '
        'mercado. La beta que justificaría el precio actual es {bi:.2f}.',
    'Where each assumption comes from, and the SEC history behind it':
        'De dónde viene cada supuesto y la historia de la SEC que lo respalda',
    'The bank engine has not been backtested out of sample yet (the FCFF model has). Fade speed and scenario rules are '
    'economic assumptions. Use the range, not a single number.':
        'El motor bancario aún no se ha probado fuera de muestra (el modelo FCFF sí). La velocidad de convergencia y las '
        'reglas de escenarios son supuestos económicos. Usa el rango, no un solo número.',
    'SEC history (USD B unless noted)': 'Historia SEC (USD B salvo indicación)',
    'SEC tags and data notes': 'Etiquetas SEC y notas de datos',
    'Method: excess-return (residual income) model and two-stage dividend discount model on total payout, both '
    'discounted at the CAPM cost of equity; ROE fades from its recent level to its long-run level.':
        'Método: modelo de retorno en exceso (ingreso residual) y modelo de descuento de dividendos en dos etapas sobre '
        'el pago total, ambos descontados al costo del patrimonio CAPM; el ROE converge de su nivel reciente al de '
        'largo plazo.',
    # driver and history labels
    'ROE today': 'ROE actual',
    'Fade speed': 'Velocidad de convergencia',
    'Book value growth today': 'Crecimiento del valor contable actual',
    'Payout ratio today': 'Tasa de pago actual',
    'Sustainable growth today': 'Crecimiento sostenible actual',
    'Stable payout ratio': 'Tasa de pago estable',
    'Normalized earnings': 'Utilidad normalizada',
    'Common book value': 'Valor contable común',
    'Net income to common': 'Utilidad neta para comunes',
    'Common equity': 'Patrimonio común',
    'Tangible common equity': 'Patrimonio común tangible',
    'ROTCE': 'ROTCE',
    'Common dividends': 'Dividendos comunes',
    'Buybacks': 'Recompras',
    'Payout ratio': 'Tasa de pago',
    'Net interest income': 'Ingreso neto por intereses',
    'Noninterest income': 'Ingresos no financieros',
    'Credit provisions': 'Provisiones de crédito',
    'Diluted EPS': 'UPA diluida',
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
    'Excess return model': ('Modelo de retorno en exceso', 'Valor del banco = valor contable común + valor presente de '
                            'las utilidades futuras por encima del costo del patrimonio ((ROE − Ke) × valor contable).'),
    'Dividend discount model': ('Modelo de descuento de dividendos', 'Valor del banco = valor presente de dividendos y '
                                'recompras a los accionistas comunes, en dos etapas: pago y crecimiento actuales, luego '
                                'una fase estable.'),
    'Book value': ('Valor contable', 'Patrimonio común en el balance (patrimonio total − acciones preferentes), por acción.'),
    'Justified P/B': ('P/VC justificado', 'Relación precio/valor contable que respalda el modelo de retorno en exceso: '
                      'valor del patrimonio / valor contable. Mayor que 1 solo si el ROE de largo plazo supera el costo '
                      'del patrimonio.'),
    'Cost of equity': ('Costo del patrimonio', 'Rendimiento que exigen los accionistas (CAPM: tasa libre de riesgo + beta × '
                       'prima de riesgo). Los bancos se descuentan a esta tasa, no al WACC.'),
    'ROE': ('ROE', 'Rendimiento sobre el patrimonio: utilidad neta para comunes / patrimonio común al inicio del año.'),
    'Long-run ROE': ('ROE de largo plazo', 'ROE que se supone gana el banco después del periodo de convergencia; la '
                     'diferencia con el costo del patrimonio genera el valor.'),
    'Model gap': ('Brecha entre modelos', 'Valor por descuento de dividendos vs valor por retorno en exceso. Una brecha '
                  'grande indica una política de pagos o crecimiento que no coincide con la trayectoria del ROE.'),
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
