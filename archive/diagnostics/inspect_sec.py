
from financial_engine import descargar_datos

datos = descargar_datos()

print("\nBUSCANDO ETIQUETAS DE DEPRECIACIÓN")
print("-" * 60)

for namespace, conceptos in datos["facts"].items():
    for etiqueta, informacion in conceptos.items():
        nombre = informacion.get("label", "")

        texto = (etiqueta + " " + nombre).lower()

        if "depreciation" in texto or "amortization" in texto:
            print(f"\nNamespace: {namespace}")
            print(f"Etiqueta: {etiqueta}")
            print(f"Descripción: {nombre}")

            unidades = informacion.get("units", {})

            for unidad, registros in unidades.items():
                anuales = [
                    r for r in registros
                    if r.get("form") == "10-K"
                    and r.get("fp") == "FY"
                    and r.get("start")
                    and r.get("end")
                    and r.get("val") is not None
                ]

                if anuales:
                    ultimo = max(
                        anuales,
                        key=lambda r: r.get("filed", "")
                    )

                    print(f"Unidad: {unidad}")
                    print(f"Último registro: {ultimo['val']:,}")
                    print(f"Período: {ultimo['start']} a {ultimo['end']}")
