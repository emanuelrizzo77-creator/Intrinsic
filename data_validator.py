
# INTRINSIC — DATA VALIDATOR
# Milestone 07B

from datetime import date

from financial_engine import descargar_datos
from market_data import (
    obtener_mercado,
    obtener_balance_sec
)


def validar_mercado(mercado):
    campos = ["price", "shares", "market_cap"]

    for campo in campos:
        valor = mercado.get(campo)

        if valor is None or valor <= 0:
            raise ValueError(
                f"Dato de mercado inválido: {campo}"
            )

    if mercado.get("currency") != "USD":
        raise ValueError(
            "Esta versión requiere datos en USD."
        )

    precio = mercado["price"]
    acciones = mercado["shares"]
    capitalizacion = mercado["market_cap"]

    estimacion = precio * acciones

    diferencia = abs(
        estimacion - capitalizacion
    ) / capitalizacion

    if diferencia > 0.02:
        raise ValueError(
            "Precio, acciones y capitalización "
            "difieren más del 2%."
        )

    return True


def validar_balance(balance):
    obligatorios = [
        "Cash",
        "Short Term Investments",
        "Long Term Debt",
        "Current Debt"
    ]

    fechas = set()

    for campo in obligatorios:
        registro = balance.get(campo)

        if registro is None:
            raise ValueError(
                f"Falta una partida: {campo}"
            )

        if registro["value"] < 0:
            raise ValueError(
                f"Saldo negativo inesperado: {campo}"
            )

        fechas.add(registro["date"])

    if len(fechas) != 1:
        raise ValueError(
            "Los saldos pertenecen a fechas distintas."
        )

    fecha_balance = date.fromisoformat(
        fechas.pop()
    )

    if fecha_balance > date.today():
        raise ValueError(
            "El balance tiene una fecha futura."
        )

    return fecha_balance


def calcular_deuda_neta(balance):
    efectivo = balance["Cash"]["value"]

    inversiones = balance[
        "Short Term Investments"
    ]["value"]

    deuda_largo = balance[
        "Long Term Debt"
    ]["value"]

    deuda_corto = balance[
        "Current Debt"
    ]["value"]

    deuda_total = deuda_largo + deuda_corto
    liquidez = efectivo + inversiones

    deuda_neta = deuda_total - liquidez

    return {
        "debt": deuda_total,
        "cash_and_investments": liquidez,
        "net_debt": deuda_neta
    }


def obtener_datos_validados(ticker="MSFT"):
    if ticker != "MSFT":
        raise ValueError(
            "El conector SEC actual solo admite MSFT."
        )

    datos = descargar_datos()
    mercado = obtener_mercado(ticker)
    balance = obtener_balance_sec(datos)

    validar_mercado(mercado)
    fecha_balance = validar_balance(balance)

    deuda = calcular_deuda_neta(balance)

    return {
        "market": mercado,
        "balance": balance,
        "balance_date": fecha_balance.isoformat(),
        "debt": deuda
    }


if __name__ == "__main__":
    resultado = obtener_datos_validados()

    mercado = resultado["market"]
    deuda = resultado["debt"]

    print("\nINTRINSIC — DATA VALIDATION")
    print("-" * 55)

    print("Market data: VALID")
    print("Balance date:", resultado["balance_date"])
    print("Currency:", mercado["currency"])

    print(
        f"Market Price: ${mercado['price']:,.2f}"
    )

    print(
        f"Market Cap: "
        f"${mercado['market_cap'] / 1e9:,.2f} B"
    )

    print(
        f"Total Debt: "
        f"${deuda['debt'] / 1e6:,.0f} M"
    )

    print(
        f"Cash + Investments: "
        f"${deuda['cash_and_investments'] / 1e6:,.0f} M"
    )

    print(
        f"Net Debt: "
        f"${deuda['net_debt'] / 1e6:,.0f} M"
    )

    print("-" * 55)
    print("VALIDACIÓN ESTRUCTURAL COMPLETADA")
    print(
        "Pendiente: revisión de etiquetas, "
        "solapamientos y fecha de cotización."
    )
