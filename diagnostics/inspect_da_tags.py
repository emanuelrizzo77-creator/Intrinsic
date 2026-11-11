
from financial_engine import descargar_datos

datos = descargar_datos()

hechos = datos["facts"].get("us-gaap", {})

print("\nINTRINSIC — D&A TAG DISCOVERY")
print("=" * 75)

for tag, concepto in sorted(hechos.items()):
    nombre = tag.lower()

    if "depreciation" not in nombre and "amortization" not in nombre:
        continue

    registros = concepto.get("units", {}).get("USD", [])

    valores = [
        r for r in registros
        if r.get("form") == "10-K"
        and r.get("end") == "2026-06-30"
        and r.get("start") == "2025-07-01"
        and isinstance(r.get("val"), (int, float))
    ]

    if not valores:
        continue

    ultimo = max(valores, key=lambda r: r.get("filed", ""))

    print(f"\nTag: {tag}")
    print(f"Label: {concepto.get('label', 'N/A')}")
    print(f"Value: ${ultimo['val'] / 1e9:,.3f} B")
    print(f"Filed: {ultimo.get('filed', 'N/A')}")
