
# INTRINSIC — CUSTOM SCENARIO

from copy import deepcopy

from assumptions_engine import (
    SCENARIOS,
    obtener_base_historica,
    proyectar_escenario,
    mostrar_escenario
)


# Copiar escenario base
hipotesis = deepcopy(SCENARIOS["base"])


# ==========================================
# HIPÓTESIS EDITABLES
# ==========================================

# Crecimiento de ingresos 2027–2031
hipotesis["growth"] = [
    0.15,
    0.13,
    0.11,
    0.09,
    0.07
]

# Margen EBIT
hipotesis["ebit_margin"] = [
    0.48,
    0.48,
    0.47,
    0.47,
    0.46
]

# CapEx / Revenue
hipotesis["capex_ratio"] = [
    0.30,
    0.28,
    0.25,
    0.22,
    0.20
]

# D&A / Revenue
hipotesis["da_ratio"] = [
    0.12,
    0.12,
    0.11,
    0.11,
    0.10
]

# Delta NWC / Delta Revenue
hipotesis["nwc_ratio"] = 0.04


# ==========================================
# EJECUTAR
# ==========================================

revenue, ultimo_anio = obtener_base_historica()

resultado = proyectar_escenario(
    revenue,
    ultimo_anio,
    hipotesis
)

mostrar_escenario(
    "CUSTOM",
    resultado
)
