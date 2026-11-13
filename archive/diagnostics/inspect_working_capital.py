
from financial_engine import descargar_datos

from financial_reconciliation import (
    extraer_saldos,
    WORKING_CAPITAL_TAGS
)


datos = descargar_datos()

saldos = extraer_saldos(
    datos,
    WORKING_CAPITAL_TAGS
)

print("\nINTRINSIC — WORKING CAPITAL DIAGNOSTICS")
print("-" * 65)

for anio in range(2022, 2027):
    print(f"\nFY {anio}")

    for concepto, registros in saldos.items():
        registro = registros.get(anio)

        if registro is None:
            print(f"  {concepto}: MISSING")
        else:
            print(
                f"  {concepto}: "
                f"${registro['value'] / 1e6:,.0f} M"
                f" | {registro['tag']}"
                f" | {registro['end']}"
            )

print("\nDiagnóstico completado.")
