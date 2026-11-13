"""Intrinsic 18G: audited NVDA FY2026 current securities bridge.

Use only after market_data_18f.py is installed. No Yahoo/SEC calls in patch.
This opt-in helper validates a specific SEC annual balance and adds an
explicitly sourced current-securities line. It does not overwrite SEC facts.
"""

from copy import deepcopy

# SEC Form 10-K filed 2026-02-25, FY end 2026-01-25.
# https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm
NVDA_FY2026 = {
    "date": "2026-01-25",
    "filed": "2026-02-25",
    "cash": 10_605_000_000,
    "marketable_securities_current": 51_951_000_000,
    "total_debt": 8_468_000_000,
}


def reconciliar_nvda_2026(balance, ticker):
    """Return copy of balance with audited investment line or original balance.

    Fail closed on conflicting values/dates. This is a one-period bridge,
    not a generic rule for future NVDA reports.
    """
    if ticker.upper() != "NVDA":
        return balance
    cash = balance.get("Cash")
    if not cash or cash.get("date") != NVDA_FY2026["date"]:
        return balance
    if cash.get("value") != NVDA_FY2026["cash"]:
        raise ValueError("NVDA FY2026 cash does not match audited 10-K")
    debt_noncurrent = balance.get("Long Term Debt")
    debt_current = balance.get("Current Debt")
    if not debt_noncurrent or not debt_current:
        raise ValueError("NVDA FY2026 debt fields missing")
    for record in (debt_noncurrent, debt_current):
        if record.get("date") != NVDA_FY2026["date"]:
            raise ValueError("NVDA FY2026 balance dates do not match")
    if debt_noncurrent["value"] + debt_current["value"] != NVDA_FY2026["total_debt"]:
        raise ValueError("NVDA FY2026 debt does not match audited 10-K")
    existing = balance.get("Short Term Investments")
    if existing is not None:
        if existing["date"] != NVDA_FY2026["date"] or existing["value"] != NVDA_FY2026["marketable_securities_current"]:
            raise ValueError("NVDA SEC investment tag conflicts with audited 10-K")
        return balance
    reconciled = deepcopy(balance)
    reconciled["Short Term Investments"] = {
        "value": NVDA_FY2026["marketable_securities_current"],
        "date": NVDA_FY2026["date"],
        "filed": NVDA_FY2026["filed"],
        "tag": "AUDITED_10K_BALANCE_MARKETABLE_SECURITIES_CURRENT",
    }
    return reconciled
