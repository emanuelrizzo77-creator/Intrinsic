
from datetime import datetime, timezone

from market_data import obtener_mercado
from financial_engine import descargar_datos
from market_data import obtener_balance_sec

def validar_positivo(valor, nombre):
    if isinstance(valor, bool) or not isinstance(
        valor, (int, float)
    ):
        raise ValueError(f"{nombre} debe ser numérico")

    if not (0 < valor < float("inf")):
        raise ValueError(f"{nombre} debe ser positivo")

    return float(valor)


def obtener_referencia_mercado(
    ticker="MSFT",
    precio_manual=None,
    acciones_manuales=None,
):
    """
    Obtiene precio y acciones en circulación.

    Los valores manuales tienen prioridad.
    Las unidades son USD y número de acciones.
    """

    necesita_mercado = (
        precio_manual is None
        or acciones_manuales is None
    )

    mercado = (
        obtener_mercado(ticker)
        if necesita_mercado
        else {}
    )

    precio = (
        precio_manual
        if precio_manual is not None
        else mercado.get("price")
    )

    acciones = (
        acciones_manuales
        if acciones_manuales is not None
        else mercado.get("shares")
    )

    precio = validar_positivo(
        precio, "Precio de mercado"
    )

    acciones = validar_positivo(
        acciones, "Acciones en circulación"
    )

    return {
        "ticker": ticker,
        "market_price": precio,
        "shares_outstanding": acciones,
        "market_cap": precio * acciones,
        "price_source": (
            "Manual"
            if precio_manual is not None
            else "Yahoo Finance"
        ),
        "shares_source": (
            "Manual"
            if acciones_manuales is not None
            else "Yahoo Finance"
        ),
        "retrieved_at": mercado.get("retrieved_at"),
    }


def calcular_precio_intrinseco(
    equity_value_usd,
    shares_outstanding,
):
    """
    Equity Value debe expresarse en USD,
    no en millones ni miles de millones.
    """

    acciones = validar_positivo(
        shares_outstanding,
        "Acciones en circulación",
    )

    return equity_value_usd / acciones


def calcular_upside(
    intrinsic_price,
    market_price,
):
    precio = validar_positivo(
        market_price, "Precio de mercado"
    )

    return (
        intrinsic_price / precio - 1
    ) * 100


def obtener_puente_financiero(ticker="MSFT"):
    """
    Obtiene deuda neta desde SEC EDGAR.

    Todas las cantidades monetarias se expresan
    internamente en USD, no en millones.
    """

    datos = datos = descargar_datos(ticker)
    balance = obtener_balance_sec(datos)

    
    
    campos = {
        "cash": "Cash",
        "short_term_investments": "Short Term Investments",
        "long_term_investments": "Long Term Investments",
        "long_term_debt": "Long Term Debt",
        "current_debt": "Current Debt",
    }

    valores = {}
    fechas = set()

    for clave, etiqueta in campos.items():
        registro = balance.get(etiqueta)

        if registro is None:
            if clave == "long_term_investments":
                valores[clave] = None
                continue

            raise ValueError(
                f"SEC data missing: {etiqueta}"
            )

        valor = registro["value"]

        if (
            isinstance(valor, bool)
            or not isinstance(valor, (int, float))
            or not 0 <= valor < float("inf")
        ):
            raise ValueError(
                f"Invalid SEC value: {etiqueta}"
            )

        valores[clave] = float(valor)
        fechas.add(registro["date"])

    if len(fechas) != 1:
        raise ValueError(
            "SEC balance dates do not match"
        )

    total_debt = (
        valores["long_term_debt"]
        + valores["current_debt"]
    )

    total_liquidity = (
        valores["cash"]
        + valores["short_term_investments"]
    )

    net_debt = total_debt - total_liquidity
    
    fecha_balance = next(iter(fechas))

    
    try:
        finance_leases = extraer_finance_leases_sec(
            datos,
            fecha_balance,
        )
    except ValueError as error:
        # Solo permitimos continuar cuando el dato
        # de finance leases no está disponible.
        if (
            "tag not found" not in str(error)
            and "No finance lease data" not in str(error)
        ):
            raise

        finance_leases = None

    if finance_leases is not None:
        net_debt_including_finance_leases = (
            calcular_deuda_neta_con_leases(
                net_debt,
                finance_leases["value"],
            )
        )
    else:
        net_debt_including_finance_leases = None
    
    return {
        **valores,
        "total_debt": total_debt,
        "total_liquidity": total_liquidity,
        "net_debt": net_debt,
        
        "finance_lease_liabilities": (
            finance_leases["value"]
            if finance_leases is not None
            else None
        ),
        "net_debt_including_finance_leases": (
            net_debt_including_finance_leases
        ),
        "finance_lease_status": (
            "AVAILABLE"
            if finance_leases is not None
            else "NOT_AVAILABLE"
        ),

        "balance_date": fecha_balance,
        "source": "SEC EDGAR / Company Facts",
        "finance_lease_source": (
    finance_leases["tag"]
    if finance_leases is not None
    else None
),
    }

def comparar_puentes_valoracion(
    enterprise_value,
    net_debt,
    shares,
    finance_lease_liabilities=None,
    non_operating_investments=None,
):
    """
    Compara puentes EV-to-Equity.

    Valores monetarios en USD.
    Acciones en unidades.

    Los escenarios ajustados son ilustrativos.
    """

    ev = validar_positivo(
        enterprise_value,
        "Enterprise Value",
    )

    acciones = validar_positivo(
        shares,
        "Acciones en circulación",
    )

    if (
        isinstance(net_debt, bool)
        or not isinstance(net_debt, (int, float))
        or not float("-inf") < net_debt < float("inf")
    ):
        raise ValueError("Invalid net debt")

    def validar_ajuste(valor, nombre):
        if valor is None:
            return None

        if (
            isinstance(valor, bool)
            or not isinstance(valor, (int, float))
            or not 0 <= valor < float("inf")
        ):
            raise ValueError(f"Invalid {nombre}")

        return float(valor)

    leases = validar_ajuste(
        finance_lease_liabilities,
        "finance leases",
    )

    inversiones = validar_ajuste(
        non_operating_investments,
        "non-operating investments",
    )

    escenarios = {}

    def agregar_escenario(nombre, deuda_ajustada):
        equity = ev - deuda_ajustada

        escenarios[nombre] = {
            "net_debt": deuda_ajustada,
            "equity_value": equity,
            "intrinsic_price": equity / acciones,
        }

    agregar_escenario("base", net_debt)

    if leases is not None:
        agregar_escenario(
            "including_finance_leases",
            net_debt + leases,
        )

    if inversiones is not None:
        agregar_escenario(
            "including_investments",
            net_debt - inversiones,
        )

    if leases is not None and inversiones is not None:
        agregar_escenario(
            "leases_and_investments",
            net_debt + leases - inversiones,
        )

    return escenarios



def calcular_deuda_neta_con_leases(
    net_debt,
    finance_lease_liabilities,
):
    """
    Calcula deuda neta incluyendo finance leases.

    Ambas cantidades deben estar expresadas en USD.

    Esta función no modifica el DCF existente.
    """

    for nombre, valor in {
        "Net Debt": net_debt,
        "Finance Lease Liabilities": finance_lease_liabilities,
    }.items():
        if (
            isinstance(valor, bool)
            or not isinstance(valor, (int, float))
            or not float("-inf") < valor < float("inf")
        ):
            raise ValueError(
                f"Invalid financial value: {nombre}"
            )

    if finance_lease_liabilities < 0:
        raise ValueError(
            "Finance lease liabilities cannot be negative"
        )

    return net_debt + finance_lease_liabilities

def extraer_finance_leases_sec(datos, fecha_balance):
    """
    Extrae obligaciones de finance leases desde SEC.

    Utiliza la misma fecha que el balance financiero.
    Valores expresados en USD.
    """

    conceptos = datos["facts"].get("us-gaap", {})

    concepto = conceptos.get("FinanceLeaseLiability")

    if not concepto:
        raise ValueError(
            "SEC FinanceLeaseLiability tag not found"
        )

    registros = concepto.get(
        "units", {}
    ).get("USD", [])

    candidatos = [
        r for r in registros
        if r.get("form") == "10-K"
        and r.get("end") == fecha_balance
        and "start" not in r
        and isinstance(r.get("val"), (int, float))
        and not isinstance(r.get("val"), bool)
        and r["val"] >= 0
    ]

    if not candidatos:
        raise ValueError(
            f"No finance lease data for {fecha_balance}"
        )

    seleccionado = max(
        candidatos,
        key=lambda r: r.get("filed", "")
    )

    return {
        "value": float(seleccionado["val"]),
        "date": seleccionado["end"],
        "tag": "FinanceLeaseLiability",
        "filed": seleccionado.get("filed"),
    }


if __name__ == "__main__":
    referencia = obtener_referencia_mercado()

    print("\nINTRINSIC — VALUATION BRIDGE")
    print("-" * 55)

    print("Ticker:", referencia["ticker"])

    print(
        "Market Price:",
        f'${referencia["market_price"]:,.2f}'
    )

    print(
        "Shares Outstanding:",
        f'{referencia["shares_outstanding"]:,.0f}'
    )

    print(
        "Market Cap:",
        f'${referencia["market_cap"] / 1e9:,.2f} B'
    )

    print("Price Source:", referencia["price_source"])
    print("Shares Source:", referencia["shares_source"])
    print("Retrieved At:", referencia["retrieved_at"])
