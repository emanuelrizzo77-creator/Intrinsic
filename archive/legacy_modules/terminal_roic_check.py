
from terminal_normalization import (
    calcular_fcff_terminal_normalizado
)

WACC = 0.0917
G = 0.025

terminal = calcular_fcff_terminal_normalizado(
    revenue_final=500_000_000_000,
    terminal_growth=G,
    ebit_margin=0.45,
    tax_rate=0.21,
    da_ratio=0.11,
    capex_ratio=0.23,
    nwc_ratio=0.03,
)

nopat = terminal["nopat_terminal"]

net_reinvestment = (
    terminal["capex_terminal"]
    - terminal["da_terminal"]
    + terminal["delta_nwc_terminal"]
)

reinvestment_rate = net_reinvestment / nopat

if reinvestment_rate <= 0:
    raise ValueError(
        "Reinvestment rate must be positive"
    )

implied_roic = G / reinvestment_rate

print("\nINTRINSIC — TERMINAL ROIC CHECK")
print("=" * 60)

print(
    f"Net Reinvestment: "
    f"${net_reinvestment / 1e9:,.2f} B"
)

print(
    f"Reinvestment Rate: "
    f"{reinvestment_rate * 100:.2f}%"
)

print(f"Implied ROIC: {implied_roic * 100:.2f}%")
print(f"WACC: {WACC * 100:.2f}%")

print(
    "ROIC - WACC Spread: "
    f"{(implied_roic - WACC) * 100:.2f} pp"
)
