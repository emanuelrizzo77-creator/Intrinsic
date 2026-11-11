
# INTRINSIC — ACCOUNTING RECONCILIATION
# Milestone 12
#
# Documentary reference: Microsoft FY2026 10-K
# All amounts in USD.

from financial_engine import descargar_datos, construir_tabla


FY2026_REFERENCE = {
    "cfo": 182_935_000_000,
    "cash_capex": 115_948_000_000,
    "cash_flow_da_and_other": 38_534_000_000,
    "new_finance_lease_assets": 24_608_000_000,
    "finance_lease_liabilities": 66_594_000_000,
}


def comparar_importes(nombre, obtenido, esperado, tolerancia=1):
    if obtenido is None:
        return {
            "metric": nombre,
            "status": "MISSING",
            "difference": None,
        }

    diferencia = obtenido - esperado

    return {
        "metric": nombre,
        "status": (
            "MATCH"
            if abs(diferencia) <= tolerancia
            else "REVIEW"
        ),
        "difference": diferencia,
    }


def reconciliar_fy2026(tabla):
    year = 2026
    ref = FY2026_REFERENCE

    cfo = tabla["CFO"].get(year)
    capex = tabla["CapEx"].get(year)
    depreciation = tabla["Depreciation"].get(year)
    amortization = tabla["Amortization"].get(year)

    resultados = [
        comparar_importes(
            "Operating Cash Flow",
            cfo,
            ref["cfo"]
        ),
        comparar_importes(
            "Cash CapEx",
            capex,
            ref["cash_capex"]
        ),
    ]

    print("\nINTRINSIC — FY2026 ACCOUNTING RECONCILIATION")
    print("=" * 70)

    for resultado in resultados:
        print(
            f"{resultado['metric']}: "
            f"{resultado['status']}"
        )

        if resultado["difference"] is not None:
            print(
                f"  Difference: "
                f"${resultado['difference'] / 1e6:,.3f} M"
            )

    if depreciation is not None and amortization is not None:
        da_xbrl = depreciation + amortization

        da_reported = ref["cash_flow_da_and_other"]
        difference = da_xbrl - da_reported

        print("\nD&A RECONCILIATION")
        print("-" * 70)
        print(f"Depreciation: ${depreciation / 1e9:,.3f} B")
        print(f"Amortization: ${amortization / 1e9:,.3f} B")
        print(f"XBRL D&A Sum: ${da_xbrl / 1e9:,.3f} B")
        print(f"10-K D&A and Other: ${da_reported / 1e9:,.3f} B")
        print(f"Difference: ${difference / 1e6:,.3f} M")
        print("Status: REVIEW — definitions require reconciliation")
    else:
        print("\nD&A Status: MISSING DATA")

    print("\nLEASE DISCLOSURES")
    print("-" * 70)
    print(
        "New finance lease assets: "
        f"${ref['new_finance_lease_assets'] / 1e9:,.3f} B"
    )
    print(
        "Finance lease liabilities: "
        f"${ref['finance_lease_liabilities'] / 1e9:,.3f} B"
    )
    print("Status: DISCLOSED — not added to DCF")

    if cfo is not None and capex is not None:
        fcf = cfo - capex
        print("\nCASH FLOW CROSS-CHECK")
        print("-" * 70)
        print(f"CFO - Cash CapEx: ${fcf / 1e9:,.3f} B")
        print("This is not equivalent to unlevered FCFF.")

    print("\nNo valuation assumptions were modified.")

    return resultados


if __name__ == "__main__":
    datos = descargar_datos()
    tabla = construir_tabla(datos)
    reconciliar_fy2026(tabla)
