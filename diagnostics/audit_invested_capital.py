
from financial_engine import descargar_datos


TAGS = [
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "ShortTermInvestments",
    "Goodwill",
    "IntangibleAssetsNetExcludingGoodwill",
    "PropertyPlantAndEquipmentNet",
    "OperatingLeaseRightOfUseAsset",
    "FinanceLeaseRightOfUseAsset",
    "OperatingLeaseLiability",
    "FinanceLeaseLiability",
]


def auditar():
    datos = descargar_datos()
    conceptos = datos["facts"].get("us-gaap", {})

    print("\nINTRINSIC — INVESTED CAPITAL AUDIT")
    print("=" * 75)

    for tag in TAGS:
        concepto = conceptos.get(tag, {})
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
            print(f"{tag}: NOT FOUND")
            continue

        ultimo = max(
            candidatos,
            key=lambda r: r.get("filed", "")
        )

        print(
            f"{tag}: "
            f"${ultimo['val'] / 1e9:,.3f} B"
        )


if __name__ == "__main__":
    auditar()
