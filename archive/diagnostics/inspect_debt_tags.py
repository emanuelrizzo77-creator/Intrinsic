
from financial_engine import descargar_datos
from market_data import obtener_balance_sec


datos = descargar_datos()
balance = obtener_balance_sec(datos)

print("\nINTRINSIC — DEBT CLASSIFICATION AUDIT")
print("=" * 70)

for nombre, registro in balance.items():
    print(f"\nConcept: {nombre}")

    if registro is None:
        print("Status: MISSING")
        continue

    print(f"Value: ${registro['value'] / 1e9:,.3f} B")
    print(f"Date: {registro['date']}")

print("\nLEASE DISCLOSURES — FY2026")
print("-" * 70)

LEASE_TAGS = [
    "FinanceLeaseLiabilityCurrent",
    "FinanceLeaseLiabilityNoncurrent",
    "FinanceLeaseLiability",
    "OperatingLeaseLiabilityCurrent",
    "OperatingLeaseLiabilityNoncurrent",
]

hechos = datos["facts"].get("us-gaap", {})

for tag in LEASE_TAGS:
    concepto = hechos.get(tag)

    if not concepto:
        print(f"{tag}: NOT FOUND")
        continue

    registros = concepto.get("units", {}).get("USD", [])

    candidatos = [
        r for r in registros
        if r.get("form") == "10-K"
        and r.get("end") == "2026-06-30"
        and "start" not in r
        and isinstance(r.get("val"), (int, float))
    ]

    if not candidatos:
        print(f"{tag}: NO FY2026 DATA")
        continue

    ultimo = max(
        candidatos,
        key=lambda r: r.get("filed", "")
    )

    print(
        f"{tag}: "
        f"${ultimo['val'] / 1e9:,.3f} B"
    )

print("\nAUDIT COMPLETED")
