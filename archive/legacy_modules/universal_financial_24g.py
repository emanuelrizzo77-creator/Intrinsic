"""24G additive, generic SEC financial resolver with disclosed D&A proxy.

Does not change Streamlit UI or claim a fully verified DCF.
"""
from __future__ import annotations
from copy import deepcopy
from universal_financial_24b import annual, valid
from universal_financial_24e import assess_company as assess_24e


def assess_company(payload, sector_model='fcff', last_n=5, allow_depreciation_proxy=True):
    result = deepcopy(assess_24e(payload, sector_model=sector_model, last_n=last_n))
    result['resolver_version'] = '24G'
    result['quality'] = {}
    result['proxies'] = {}
    if not result.get('history') or not result['history'].get('rows'):
        return result
    facts = payload.get('facts', {})
    for row in result['history']['rows']:
        end = row['Fiscal year end']
        if valid(row.get('D&A verified')):
            tag = row.get('source_tags', {}).get('D&A verified', '')
            quality = 'BROAD_DA_INCLUDES_ACCRETION' if 'DepreciationAmortizationAndAccretionNet' in tag else 'REPORTED_OR_RECONSTRUCTED_DA_REVIEW'
            result['quality'][f'{end}:D&A'] = quality
            continue
        if not allow_depreciation_proxy:
            continue
        value, tag = annual(facts, ('Depreciation',), end)
        if value is None or value < 0:
            continue
        # Do not rewrite the strict 'D&A verified' field. Proxies are separate.
        row['D&A scenario proxy'] = value
        row.setdefault('source_tags', {})['D&A scenario proxy'] = tag
        row.setdefault('warnings', []).append('Depreciation-only proxy excludes unverified amortization; scenario use only.')
        result['proxies'][end] = {'field':'D&A','value':value,'source':tag,'quality':'DEPRECIATION_ONLY_PROXY'}
        result['quality'][f'{end}:D&A'] = 'DEPRECIATION_ONLY_PROXY'
    latest = result['history']['rows'][-1]
    end = latest['Fiscal year end']
    if 'D&A verified' in result.get('missing', []) and end in result['proxies']:
        result['missing'] = [m for m in result['missing'] if m != 'D&A verified']
        result['warnings'].append('Latest-year D&A uses depreciation-only proxy; amortization not verified. FCFF is scenario-only.')
    if sector_model != 'fcff':
        result['status'] = 'UNSUPPORTED_SECTOR'
    elif result.get('missing'):
        result['status'] = 'MISSING_DATA'
    elif end in result['proxies']:
        result['status'] = 'PROVISIONAL_PROXY_SCENARIO_ONLY'
    else:
        result['status'] = 'PROVISIONAL_SCENARIO_ONLY'
    return result
