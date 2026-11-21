"""Intrinsic 21C: reusable valuation routing and conservative data-readiness checks.

This module deliberately does not invent missing financial data or return a
price target before a suitable sector model has been implemented and tested.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

import json, math, os
from urllib.request import Request, urlopen

@dataclass(frozen=True)
class ModelDecision:
    model: str
    category: str
    eligible: bool
    reason: str


def classify_sic(sic):
    """Classify a US SIC code for valuation routing; unknown stays unclassified."""
    try:
        n = int(sic)
    except (ValueError, TypeError):
        return ModelDecision('unclassified', 'Unknown', False, 'No reliable SIC classification')
    if 6000 <= n <= 6199:
        return ModelDecision('bank_equity', 'Bank / credit institution', False, 'Equity engine (excess return + dividend discount), not FCFF')
    if 6300 <= n <= 6411:
        return ModelDecision('insurance_equity', 'Insurance', False, 'Equity engine on operating earnings (excess return + dividend discount), not FCFF')
    if 6798 == n:
        return ModelDecision('reit_affo', 'REIT', False, 'Requires FFO/AFFO or NAV and property-specific inputs')
    if 6700 <= n <= 6799:
        return ModelDecision('holding_sotp', 'Investment / holding', False, 'May require sum-of-parts or net asset valuation')
    if 100 <= n <= 9999:
        return ModelDecision('fcff', 'Nonfinancial / operating company', True, 'FCFF is a candidate, subject to complete data checks')
    return ModelDecision('unclassified', 'Unknown', False, 'SIC outside supported classification')


def fetch_sec_profile(cik: int, user_agent=None, timeout=20):
    agent = user_agent or os.environ.get('INTRINSIC_SEC_USER_AGENT', '')
    if '@' not in agent:
        raise ValueError('Set INTRINSIC_SEC_USER_AGENT with a real contact email')
    if not isinstance(cik, int) or cik <= 0:
        raise ValueError('Invalid SEC CIK')
    req = Request(f'https://data.sec.gov/submissions/CIK{cik:010d}.json',
                  headers={'User-Agent': agent, 'Accept': 'application/json', 'Accept-Encoding': 'identity'})
    with urlopen(req, timeout=timeout) as response:
        data = json.load(response)
    return {'name': data.get('name'), 'sic': data.get('sic'), 'sic_description': data.get('sicDescription'),
            'fiscal_year_end': data.get('fiscalYearEnd')}


def _finite_positive(v):
    return isinstance(v, (int,float)) and not isinstance(v,bool) and math.isfinite(v) and v > 0


def assess_readiness(audit, profile):
    """Evaluate prerequisites, never claim a full DCF is validated."""
    decision = classify_sic(profile.get('sic'))
    rows = audit.get('rows') or []
    latest = rows[-1] if rows else {}
    issues = []
    if not decision.eligible:
        issues.append(decision.reason)
    if len(rows) < 3:
        issues.append(f'Only {len(rows)} historical fiscal periods; minimum 3 for initial forecast assumptions')
    for label in ('Revenue', 'EBIT', 'D&A verified', 'CapEx'):
        value = latest.get(label)
        if value is None or isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
            issues.append(f'Missing or invalid latest-year {label}')
    if not _finite_positive(latest.get('Revenue')):
        issues.append('Latest revenue must be positive')
    # A SEC tag alone is not proof of correct accounting semantics.
    issues.extend([
        'Full operating working capital and annual changes not validated',
        'Net debt, diluted shares and fiscal-date alignment not validated',
        'Company-specific cost of capital and five-year assumptions not validated',
        'Historical SEC XBRL tag definitions not independently reconciled to 10-K',
    ])
    return {
        'company': audit.get('company'), 'classification': asdict(decision),
        'fiscal_year_end': profile.get('fiscal_year_end'),
        'sic': profile.get('sic'), 'sic_description': profile.get('sic_description'),
        'historical_periods': len(rows), 'issues': issues,
        'status': 'REQUIRES_VALIDATION', 'price_target': None,
        'message': 'Universal routing is operational; a defensible intrinsic value is not yet available.',
    }
