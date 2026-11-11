"""Intrinsic 27 — annual SEC fact selection with explicit vintage control.

vintage='latest' -> latest-filed value per fiscal period (restated; live valuation)
vintage='first'  -> first-filed value per period (as originally reported; backtests)
as_of            -> ignore facts filed after this date (point-in-time reconstruction)

Tags are tried in priority order per fiscal period. Values from different tags
are NEVER added together. Company-specific extension tags are not present in
SEC CompanyFacts; a missing series may require the Financial Statement Data Sets.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date
from math import isfinite
from urllib.request import Request, urlopen

ANNUAL_FORMS = ('10-K', '10-K/A', '10-KT')
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.intrinsic_cache')


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v)


def _d(text):
    try:
        return date.fromisoformat(str(text))
    except (TypeError, ValueError):
        return None


def _as_date(as_of):
    if as_of is None or isinstance(as_of, date):
        return as_of
    parsed = _d(as_of)
    if parsed is None:
        raise ValueError('as_of must be YYYY-MM-DD')
    return parsed


def _better(cand, cur, vintage):
    if cand['priority'] != cur['priority']:
        return cand['priority'] < cur['priority']
    if vintage == 'first':
        return (cand['filed'], cand['accn'] or '') < (cur['filed'], cur['accn'] or '')
    return (cand['filed'], cand['accn'] or '') > (cur['filed'], cur['accn'] or '')


def _select(payload, tags, *, duration, vintage, as_of, namespace, unit):
    if vintage not in ('latest', 'first'):
        raise ValueError("vintage must be 'latest' or 'first'")
    as_of = _as_date(as_of)
    facts = (payload or {}).get('facts', {}).get(namespace, {})
    out = {}
    for priority, tag in enumerate(tags):
        for r in facts.get(tag, {}).get('units', {}).get(unit, []):
            if r.get('form') not in ANNUAL_FORMS or not is_number(r.get('val')):
                continue
            end, filed = _d(r.get('end')), _d(r.get('filed'))
            if end is None or filed is None or (as_of and filed > as_of):
                continue
            if duration:
                start = _d(r.get('start'))
                if start is None or not 340 <= (end - start).days <= 400:
                    continue
            elif 'start' in r:
                continue
            cand = {'value': float(r['val']), 'tag': f'{namespace}:{tag}',
                    'filed': filed.isoformat(), 'accn': r.get('accn'), 'priority': priority}
            key = end.isoformat()
            if key not in out or _better(cand, out[key], vintage):
                out[key] = cand
    return out


def annual_flows(payload, tags, *, vintage='latest', as_of=None, namespace='us-gaap', unit='USD'):
    """{fiscal_end: fact} for ~12-month duration facts in annual filings."""
    return _select(payload, tags, duration=True, vintage=vintage, as_of=as_of,
                   namespace=namespace, unit=unit)


def annual_points(payload, tags, *, vintage='latest', as_of=None, namespace='us-gaap', unit='USD'):
    """{date: fact} for instant (balance-sheet) facts in annual filings."""
    return _select(payload, tags, duration=False, vintage=vintage, as_of=as_of,
                   namespace=namespace, unit=unit)


def consecutive(a, b):
    """True when fiscal year end b follows a by roughly one year."""
    da, db = _d(a), _d(b)
    return da is not None and db is not None and 340 <= (db - da).days <= 400


# ------------------------------------------------------------------
# Cached SEC access (respect SEC fair-access: <=10 requests/second)
# ------------------------------------------------------------------

def _agent(user_agent=None):
    agent = user_agent or os.environ.get('INTRINSIC_SEC_USER_AGENT', '')
    if '@' not in agent:
        raise ValueError('Set INTRINSIC_SEC_USER_AGENT="Intrinsic your@email.com"')
    return agent


def _cached_json(url, path, user_agent=None, max_age_days=7, pause=0.12):
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < max_age_days * 86400:
        with open(path) as fh:
            return json.load(fh)
    req = Request(url, headers={'User-Agent': _agent(user_agent), 'Accept': 'application/json',
                                'Accept-Encoding': 'identity'})
    with urlopen(req, timeout=30) as response:
        payload = json.load(response)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as fh:
        json.dump(payload, fh)
    time.sleep(pause)
    return payload


def companyfacts_cached(cik, user_agent=None, max_age_days=7):
    cik = int(cik)
    return _cached_json(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',
                        os.path.join(CACHE_DIR, 'companyfacts', f'CIK{cik:010d}.json'),
                        user_agent, max_age_days)


def submissions_cached(cik, user_agent=None, max_age_days=30):
    cik = int(cik)
    return _cached_json(f'https://data.sec.gov/submissions/CIK{cik:010d}.json',
                        os.path.join(CACHE_DIR, 'submissions', f'CIK{cik:010d}.json'),
                        user_agent, max_age_days)
