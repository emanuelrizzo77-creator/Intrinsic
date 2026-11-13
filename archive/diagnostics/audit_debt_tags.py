
from financial_engine import descargar_datos

datos = descargar_datos()
conceptos = datos["facts"].get("us-gaap", {})

tags = [
    "LongTermDebtNoncurrent",
    "LongTermDebtCurrent",
    "LongTermDebt",
    "ShortTermBorrowings",
    "FinanceLeaseLiability",
    "FinanceLeaseLiabilityCurrent",
    "FinanceLeaseLiabilityNoncurrent",
    "OperatingLeaseLiability",
    "OperatingLeaseLiabilityCurrent",
    "OperatingLeaseLiabilityNoncurrent",
]

print("\nINTRINSIC — DEBT COMPOSITION AUDIT")
print("=" * 75)

for tag in tags:
    registros = conceptos.get(
        tag, {}
    ).get("units", {}).get("USD", [])

    candidatos = [
        r for r in registros
        if r.get("form") == "10-K"
        and r.get("end") == "2026-06-30"
        and "start" not in r
        and isinstance(r.get("val"), (int, float))
        and not isinstance(r.get("val"), bool)
    ]

    if candidatos:
        ultimo = max(
            candidatos,
            key=lambda r: r.get("filed", "")
        )

        print(
            f"{tag:<45}"
            f"${ultimo['val']/1e9:>10,.3f} B"
        )
    else:
        print(f"{tag:<45} NOT FOUND")

