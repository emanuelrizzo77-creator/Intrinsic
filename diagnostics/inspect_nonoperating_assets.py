
from financial_engine import descargar_datos


def inspeccionar_inversiones():
    datos = descargar_datos()
    conceptos = datos["facts"].get("us-gaap", {})

    fechas = {
        "2025-06-30",
        "2026-06-30",
    }

    print("\nINTRINSIC — NON-OPERATING ASSETS AUDIT")
    print("=" * 65)

    for etiqueta, concepto in conceptos.items():
        nombre = etiqueta.lower()

        if not any(
            palabra in nombre
            for palabra in (
                "equitymethod",
                "equitysecurit",
                "otherinvestment",
                "longterminvestment",
                "marketablesecurit",
            )
        ):
            continue

        registros = concepto.get(
            "units", {}
        ).get("USD", [])

        candidatos = [
            registro
            for registro in registros
            if registro.get("form") == "10-K"
            and registro.get("end") in fechas
            and "start" not in registro
            and isinstance(
                registro.get("val"), (int, float)
            )
            and not isinstance(
                registro.get("val"), bool
            )
            and registro["val"] >= 0
        ]

        for fecha in sorted(fechas):
            coincidentes = [
                registro
                for registro in candidatos
                if registro["end"] == fecha
            ]

            if not coincidentes:
                continue

            seleccionado = max(
                coincidentes,
                key=lambda r: r.get("filed", "")
            )

            valor = seleccionado["val"] / 1e9

            print(
                f"{fecha} | "
                f"{etiqueta:<48} "
                f"${valor:,.3f} B"
            )


if __name__ == "__main__":
    inspeccionar_inversiones()

