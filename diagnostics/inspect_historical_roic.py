
from financial_engine import descargar_datos
from market_data import obtener_balance_historico_sec


def inspeccionar():
    datos = descargar_datos()

    fechas = [
        "2025-06-30",
        "2026-06-30",
    ]

    print("\nINTRINSIC — HISTORICAL SEC AUDIT")
    print("=" * 65)

    for fecha in fechas:
        print(f"\nBALANCE DATE: {fecha}")
        print("-" * 65)

        balance = obtener_balance_historico_sec(
            datos,
            fecha,
        )

        for nombre, registro in balance.items():
            valor = registro["value"] / 1e9

            print(
                f"{nombre:<25}"
                f"${valor:>12,.3f} B  "
                f"[{registro['tag']}]"
            )


if __name__ == "__main__":
    inspeccionar()
