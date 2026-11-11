
from financial_engine import descargar_datos


def auditar_etiquetas():
    datos = descargar_datos()
    conceptos = datos["facts"].get("us-gaap", {})

    palabras = [
        "Intangible",
        "FinanceLease",
        "RightOfUse",
    ]

    print("\nINTRINSIC — MISSING ASSET TAG AUDIT")
    print("=" * 75)

    for tag, concepto in conceptos.items():

        if not any(
            palabra.lower() in tag.lower()
            for palabra in palabras
        ):
            continue

        registros = concepto.get(
            "units", {}
        ).get("USD", [])

        candidatos = [
            r for r in registros
            if r.get("form") == "10-K"
            and r.get("end") == "2026-06-30"
            and "start" not in r
            and isinstance(r.get("val"), (int, float))
            and not isinstance(r.get("val"), bool)
        ]

        if not candidatos:
            continue

        ultimo = max(
            candidatos,
            key=lambda r: r.get("filed", "")
        )

        print(
            f"{tag:<55}"
            f"${ultimo['val'] / 1e9:>10,.3f} B"
        )


if __name__ == "__main__":
    auditar_etiquetas()
