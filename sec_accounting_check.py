
from datetime import date

from financial_engine import descargar_datos


TAGS = [
    "Depreciation",
    "DepreciationDepletionAndAmortization",
    "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
    "AmortizationOfIntangibleAssets",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "NetCashProvidedByUsedInOperatingActivities",
]


def revisar_tag(datos, tag, year=2026):
    concepto = datos["facts"].get("us-gaap", {}).get(tag)

    if not concepto:
        print(f"{tag}: NOT FOUND")
        return

    registros = concepto.get("units", {}).get("USD", [])

    candidatos = []

    for r in registros:
        if r.get("form") != "10-K":
            continue

        if not all(k in r for k in ("start", "end", "val", "filed")):
            continue

        inicio = date.fromisoformat(r["start"])
        fin = date.fromisoformat(r["end"])

        if fin.year != year or (fin.month, fin.day) != (6, 30):
            continue

        if not 340 <= (fin - inicio).days <= 400:
            continue

        candidatos.append(r)

    if not candidatos:
        print(f"{tag}: NO FY{year} DATA")
        return

    seleccionado = max(candidatos, key=lambda r: r["filed"])

    print(f"\n{tag}")
    print(f"Label: {concepto.get('label', 'N/A')}")
    print(f"Value: ${seleccionado['val'] / 1e9:,.3f} B")
    print(f"Filed: {seleccionado['filed']}")
    print(f"Accession: {seleccionado.get('accn', 'N/A')}")


if __name__ == "__main__":
    datos = descargar_datos()

    print("\nINTRINSIC — ACCOUNTING TAG CHECK")
    print("=" * 70)

    for tag in TAGS:
        revisar_tag(datos, tag)

    print("\nACCOUNTING CHECK COMPLETED")
