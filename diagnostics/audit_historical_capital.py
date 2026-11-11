
from financial_engine import descargar_datos

TAGS = {
    "Assets": "Assets",
    "Liabilities": "Liabilities",
    "Equity": "StockholdersEquity",
    "Cash": "CashAndCashEquivalentsAtCarryingValue",
    "Short Term Investments": "ShortTermInvestments",
    "Long Term Debt": "LongTermDebtNoncurrent",
    "Current Debt": "LongTermDebtCurrent",
    "Finance Leases": "FinanceLeaseLiability",
    "Operating Leases": "OperatingLeaseLiability",
}

FECHAS = ["2025-06-30", "2026-06-30"]


def auditar():
    datos = descargar_datos()
    conceptos = datos["facts"].get("us-gaap", {})

    print("\nINTRINSIC — HISTORICAL CAPITAL AUDIT")
    print("=" * 75)

    for fecha in FECHAS:
        print(f"\nBALANCE DATE: {fecha}")
        print("-" * 75)

        for nombre, tag in TAGS.items():
            registros = conceptos.get(
                tag, {}
            ).get("units", {}).get("USD", [])

            candidatos = [
                r for r in registros
                if r.get("form") == "10-K"
                and r.get("end") == fecha
                and "start" not in r
                and isinstance(r.get("val"), (int, float))
                and not isinstance(r.get("val"), bool)
            ]

            if not candidatos:
                print(f"{nombre}: NOT FOUND")
                continue

            ultimo = max(
                candidatos,
                key=lambda r: r.get("filed", "")
            )

            print(
                f"{nombre:<25}"
                f"${ultimo['val'] / 1e9:>12,.3f} B"
            )


if __name__ == "__main__":
    auditar()
