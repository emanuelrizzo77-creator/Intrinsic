"""Intrinsic 21A: SEC company directory and conservative DCF eligibility gate.

The SEC ticker directory is a discovery source, NOT proof of DCF compatibility.
Requires internet and a truthful contact-bearing User-Agent for SEC requests.
"""
from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

SEC_DIRECTORY_URL = "https://www.sec.gov/files/company_tickers.json"
VALIDATED_TICKERS = ("MSFT", "AAPL", "NVDA", "GOOGL")


def parse_sec_directory(payload):
    """Return unique (ticker, name, cik) tuples from SEC company_tickers.json."""
    entries = payload.values() if isinstance(payload, dict) else payload
    result = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker", "")).strip().upper()
        title = str(item.get("title", "")).strip()
        try:
            cik = int(item["cik_str"])
        except (KeyError, TypeError, ValueError):
            continue
        if ticker and title and cik > 0 and ticker not in result:
            result[ticker] = (ticker, title, cik)
    return sorted(result.values(), key=lambda item: (item[1].casefold(), item[0]))


def fetch_sec_directory(user_agent=None, timeout=12):
    agent = user_agent or os.environ.get("INTRINSIC_SEC_USER_AGENT", "")
    if not agent or "@" not in agent:
        raise ValueError("Set INTRINSIC_SEC_USER_AGENT to an app name and real contact email before querying SEC.")
    request = Request(SEC_DIRECTORY_URL, headers={
        "User-Agent": agent,
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    })
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    companies = parse_sec_directory(payload)
    if not companies:
        raise ValueError("SEC returned an empty or unexpected ticker directory")
    return companies


def coverage_status(ticker):
    """21A is discovery-only for newly found tickers."""
    if ticker in VALIDATED_TICKERS:
        return "existing_experimental"
    return "research_required"
