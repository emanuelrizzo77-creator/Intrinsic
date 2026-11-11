
# INTRINSIC — NET DEBT ENGINE
# Milestone 14

from market_data import obtener_balance_sec
from financial_engine import descargar_datos


def calcular_deuda_neta(balance, incluir_inversiones=True):
    """
    Calcula deuda neta a partir del balance SEC.

    Todos los valores se expresan en USD.
    """

    claves = [
        "Long Term Debt",
        "Current Debt",
        "Cash",
    ]

    if incluir_inversiones:
        claves.append("Short Term Investments")

    valores = {}

    for clave in claves:
        registro = balance.get(clave)

        if registro is None:
            raise ValueError(
                f"Missing financial data: {clave}"
            )

        valor = registro["value"]

        if valor is None or valor < 0:
            raise ValueError(
                f"Invalid financial data: {clave}"
            )

        valores[clave] = valor

    # All balance components must refer
    # to the same reporting date.
    fechas = {
        balance[clave]["date"]
        for clave in claves
    }

    if len(fechas) != 1:
        raise ValueError(
            "Balance sheet dates are inconsistent"
        )

    deuda_total = (
        valores["Long Term Debt"]
        + valores["Current Debt"]
    )

    efectivo = valores["Cash"]

    inversiones = (
        valores["Short Term Investments"]
        if incluir_inversiones
        else 0
    )

    deuda_neta = (
        deuda_total - efectivo - inversiones
    )

    return {
        "total_debt": deuda_total,
        "cash": efectivo,
        "short_term_investments": inversiones,
        "net_debt": deuda_neta,
        "balance_date": fechas.pop(),
        "includes_investments": incluir_inversiones,
    }


if __name__ == "__main__":
    datos = descargar_datos()
    balance = obtener_balance_sec(datos)

    resultado = calcular_deuda_neta(balance)

    print("\nINTRINSIC — NET DEBT ANALYSIS")
    print("-" * 55)

    for clave in [
        "total_debt",
        "cash",
        "short_term_investments",
        "net_debt",
    ]:
        valor = resultado[clave] / 1e9
        print(f"{clave:<25}${valor:,.2f} B")

    print("-" * 55)
    print("Balance Date:", resultado["balance_date"])
    print(
        "Includes Investments:",
        resultado["includes_investments"]
    )
