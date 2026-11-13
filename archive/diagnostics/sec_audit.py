
# INTRINSIC — SEC XBRL AUDIT
# Milestone 11B

from datetime import date

from financial_engine import (
    descargar_datos,
    METRICAS,
)


def auditar_metrica(datos, nombre, anios=(2024, 2025, 2026)):
    hechos = datos["facts"].get("us-gaap", {})

    print(f"\n{'=' * 85}")
    print(f"AUDIT: {nombre}")
    print(f"{'=' * 85}")

    for etiqueta in METRICAS[nombre]:
        concepto = hechos.get(etiqueta)

        if not concepto:
            print(f"\nTag: {etiqueta} — NOT FOUND")
            continue

        print(f"\nTag: {etiqueta}")
        print("Label:", concepto.get("label", "N/A"))
        print("Description:", concepto.get("description", "N/A")[:180])

        registros = concepto.get("units", {}).get("USD", [])

        candidatos = []

        for r in registros:
            if r.get("form") != "10-K":
                continue

            if not all(
                k in r for k in ("start", "end", "val", "filed")
            ):
                continue

            inicio = date.fromisoformat(r["start"])
            fin = date.fromisoformat(r["end"])

            if fin.year not in anios:
                continue

            if (fin.month, fin.day) != (6, 30):
                continue

            if not 340 <= (fin - inicio).days <= 400:
                continue

            candidatos.append(r)

        for anio in anios:
            registros_anio = [
                r for r in candidatos
                if r["end"].startswith(str(anio))
            ]

            if not registros_anio:
                print(f"FY{anio}: N/A")
                continue

            seleccionado = max(
                registros_anio,
                key=lambda r: r["filed"]
            )

            print(
                f"FY{anio} | "
                f"Value: ${seleccionado['val'] / 1e9:,.3f} B | "
                f"Period: {seleccionado['start']} to "
                f"{seleccionado['end']} | "
                f"Filed: {seleccionado['filed']} | "
                f"Accession: {seleccionado.get('accn', 'N/A')}"
            )


if __name__ == "__main__":
    datos = descargar_datos()

    for nombre in (
        "Depreciation",
        "Amortization",
        "CapEx",
        "CFO",
    ):
        auditar_metrica(datos, nombre)

    print("\nSEC AUDIT COMPLETED")

