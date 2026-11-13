"""Intrinsic 21B: conservative SEC annual financial-data audit for new tickers.
Discovery/diagnostics only: NOT a DCF valuation or an approval for DCF.
"""
from __future__ import annotations
import json, math, os
from datetime import date
from urllib.request import Request, urlopen

TAGS = {
    'Revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet',
                # appended (lowest priority): gross-of-tax contract revenue and the utility total
                'RevenueFromContractWithCustomerIncludingAssessedTax', 'RegulatedAndUnregulatedOperatingRevenue'),
    'EBIT': ('OperatingIncomeLoss',),
    'Depreciation': ('Depreciation', 'DepreciationDepletionAndAmortizationPropertyPlantAndEquipment'),
    'Amortization': ('AmortizationOfIntangibleAssets',),
    'D&A combined': ('DepreciationDepletionAndAmortization', 'DepreciationAndAmortization',
                     'DepreciationAmortizationAndAccretionNet'),
    'CapEx': ('PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets',),
    'Operating Cash Flow': ('NetCashProvidedByUsedInOperatingActivities',),
}

def fetch_companyfacts(cik: int, user_agent=None, timeout=20):
    agent = user_agent or os.environ.get('INTRINSIC_SEC_USER_AGENT', '')
    if '@' not in agent:
        raise ValueError('Set INTRINSIC_SEC_USER_AGENT with a real contact email.')
    if not isinstance(cik, int) or cik <= 0:
        raise ValueError('Invalid SEC CIK')
    url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'
    req = Request(url, headers={'User-Agent':agent, 'Accept':'application/json', 'Accept-Encoding':'identity'})
    with urlopen(req, timeout=timeout) as response:
        return json.load(response)

def _annual_observations(fact):
    for item in fact.get('units', {}).get('USD', []):
        if item.get('form') != '10-K' or not all(k in item for k in ('start','end','filed','val')):
            continue
        value = item['val']
        if isinstance(value, bool) or not isinstance(value, (float,int)) or not math.isfinite(value):
            continue
        try:
            start, end, filed = (date.fromisoformat(item[k]) for k in ('start','end','filed'))
        except (TypeError, ValueError):
            continue
        if 340 <= (end-start).days <= 400:
            yield end.isoformat(), filed.isoformat(), float(value)

def audit_companyfacts(payload, last_n=5):
    facts = payload.get('facts', {}).get('us-gaap', {})
    rows = {}
    for label, candidates in TAGS.items():
        # Do not mix different tags for the same fiscal period without disclosing provenance.
        for tag in candidates:
            for end, filed, value in _annual_observations(facts.get(tag, {})):
                slot = rows.setdefault(end, {})
                old = slot.get(label)
                if old is None or (candidates.index(tag), -int(filed.replace('-',''))) < (old['priority'], -int(old['filed'].replace('-',''))):
                    slot[label] = {'value':value, 'tag':tag, 'filed':filed, 'priority':candidates.index(tag)}
    output = []
    for end in sorted(rows)[-last_n:]:
        values = rows[end]
        row = {'Fiscal year end':end}
        for label in TAGS:
            row[label] = values[label]['value'] if label in values else None
        # Do not add combined D&A to component depreciation/amortization (double counting).
        row['D&A verified'] = (row['D&A combined'] if row['D&A combined'] is not None else
                             row['Depreciation'] + row['Amortization'] if row['Depreciation'] is not None and row['Amortization'] is not None else None)
        row['Revenue growth'] = None
        row['EBIT margin'] = row['EBIT']/row['Revenue'] if row['EBIT'] is not None and row['Revenue'] and row['Revenue'] > 0 else None
        row['D&A / Revenue'] = row['D&A verified']/row['Revenue'] if row['D&A verified'] is not None and row['Revenue'] and row['Revenue'] > 0 else None
        row['CapEx / Revenue'] = row['CapEx']/row['Revenue'] if row['CapEx'] is not None and row['Revenue'] and row['Revenue'] > 0 else None
        row['SEC tag provenance'] = {label:values[label]['tag'] for label in TAGS if label in values}
        output.append(row)
    for i in range(1, len(output)):
        prev, cur = output[i-1], output[i]
        if prev['Revenue'] and prev['Revenue'] > 0 and cur['Revenue'] is not None:
            # Only compare fiscal years approximately 1 year apart.
            if 340 <= (date.fromisoformat(cur['Fiscal year end']) - date.fromisoformat(prev['Fiscal year end'])).days <= 400:
                cur['Revenue growth'] = cur['Revenue']/prev['Revenue'] - 1
    latest = output[-1] if output else {}
    required = ('Revenue','EBIT','D&A verified','CapEx')
    missing = [key for key in required if latest.get(key) is None]
    return {
        'company': payload.get('entityName', 'Unknown'), 'rows': output,
        'missing_latest': missing,
        'ready_for_dcf': False,
        'warnings': [
            'Diagnostic SEC data only. No DCF has been calculated.',
            'Full operating net working capital, net debt, shares, WACC, fiscal-period consistency and sector suitability require separate validation.',
            'SEC tags may represent company-specific definitions; verify against the original 10-K.',
        ] + ([f'Missing latest annual metrics: {", ".join(missing)}'] if missing else []),
    }
