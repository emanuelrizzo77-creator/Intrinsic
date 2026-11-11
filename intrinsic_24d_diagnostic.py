"""Intrinsic 24D: read-only SEC XBRL evidence report for missing financial fields.

Requires modules from prior Intrinsic milestones. Does NOT alter the valuation.
"""
import argparse
import csv
import json
import math
import os
import time
from datetime import date
from pathlib import Path
from financial_audit_21b import fetch_companyfacts
from universal_financial_24c import assess_company
from universal_valuation_21c import fetch_sec_profile, classify_sic

DEFAULT = 'PEP,WMT,NKE,MCD,CAT,GOOGL'
TERMS = {
    'Net debt (cash-only)': ('debt','borrow','credit','cash','equivalent','commercial paper','note payable','finance lease'),
    'D&A verified': ('depreciation','amortization','depletion'),
    'Shares outstanding': ('sharesoutstanding','commonstockshares','entitycommonstockshares','weightedaveragenumberof','stockoutstanding'),
    'EBIT': ('operatingincome','operatingprofit','incomefromoperations','earningsbeforeinterest'),
    'Effective tax rate': ('incometax','beforeincometax','pretax','effectiveincometax'),
}
UNITS = {'Shares outstanding': ('shares',), 'Effective tax rate': ('USD','pure'),
         'Net debt (cash-only)': ('USD',), 'D&A verified': ('USD',), 'EBIT': ('USD',)}

def discover(facts, field, fiscal_end, max_per_tag=2):
    """Show candidate observations; NEVER assert accounting equivalence."""
    target = date.fromisoformat(fiscal_end)
    tokens = TERMS.get(field, ())
    matches = []
    for namespace, tags in facts.items():
        if not isinstance(tags, dict):
            continue
        for tag, fact in tags.items():
            label = str(fact.get('label', ''))
            description = str(fact.get('description', ''))
            haystack = (tag + ' ' + label + ' ' + description[:250]).lower().replace(' ', '')
            hits = sum(term.replace(' ','') in haystack for term in tokens)
            if not hits:
                continue
            for unit, observations in fact.get('units', {}).items():
                if unit not in UNITS.get(field, ('USD',)):
                    continue
                valid = []
                for r in observations:
                    if r.get('form') not in ('10-K','10-K/A') or not r.get('filed') or not r.get('end'):
                        continue
                    value = r.get('val')
                    if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
                        continue
                    try:
                        end = date.fromisoformat(r['end'])
                        distance = abs((end-target).days)
                        days = (end-date.fromisoformat(r['start'])).days if r.get('start') else None
                    except (ValueError, TypeError):
                        continue
                    if distance > 450:
                        continue
                    period_type = 'annual_flow' if days is not None and 340 <= days <= 400 else ('instant' if days is None else 'other_duration')
                    valid.append((distance, -int(r['filed'].replace('-','')), r, period_type, days))
                valid.sort(key=lambda x:(x[0],x[1]))
                for distance, _, r, kind, days in valid[:max_per_tag]:
                    matches.append({'field':field,'namespace':namespace,'tag':tag,'label':label,
                        'value':r['val'],'unit':unit,'start':r.get('start',''),'end':r['end'],
                        'days':days if days is not None else '', 'period_type':kind,
                        'days_from_fiscal_end':distance,'filed':r['filed'],'form':r['form'],
                        'fy':r.get('fy',''),'fp':r.get('fp',''),'frame':r.get('frame',''),
                        'accn':r.get('accn',''), 'semantic_matches':hits,
                        'review':'CANDIDATE_ONLY_NOT_VERIFIED'})
    matches.sort(key=lambda r:(r['days_from_fiscal_end'], -r['semantic_matches'], r['namespace']!='us-gaap',r['tag']))
    return matches

def directory_from_cache(path):
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding='utf-8'))
    # Cache layouts may evolve: accept entries only with explicitly recognized fields.
    items = payload if isinstance(payload, list) else next((payload[k] for k in ('entries','companies','tickers') if isinstance(payload.get(k),list)), [])
    output = {}
    for item in items:
        if isinstance(item,dict):
            ticker = item.get('ticker') or item.get('symbol')
            cik = item.get('cik') or item.get('cik_str')
            if ticker and cik:
                output[str(ticker).upper()] = int(cik)
    return output

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tickers',default=DEFAULT)
    p.add_argument('--delay',type=float,default=0.5)
    p.add_argument('--top',type=int,default=12,help='Max candidates per missing field in summary JSON')
    p.add_argument('--output-prefix',default='intrinsic_24d')
    a=p.parse_args()
    if a.delay < .2 or a.top < 1: p.error('Require --delay >= 0.2 and --top >= 1')
    if '@' not in os.getenv('INTRINSIC_SEC_USER_AGENT',''):
        p.error('Set INTRINSIC_SEC_USER_AGENT="Intrinsic Your Name real@email.com"')
    directory=directory_from_cache(Path('.intrinsic_cache/sec_company_directory.json'))
    if not directory:
        from company_explorer_21a import fetch_sec_directory
        directory={ticker:cik for ticker,_,cik in fetch_sec_directory()}
    summaries=[]; candidates=[]
    for ticker in dict.fromkeys(s.strip().upper() for s in a.tickers.split(',') if s.strip()):
        cik=directory.get(ticker)
        if cik is None:
            print(f'{ticker}: NOT_IN_DIRECTORY (check directory cache format)');continue
        try:
            profile=fetch_sec_profile(cik)
            payload=fetch_companyfacts(cik)
            assessment=assess_company(payload,classify_sic(profile.get('sic')).model)
            end=assessment['latest_year']
            missing=assessment['missing']
            summary={'ticker':ticker,'cik':cik,'company':payload.get('entityName'),
                     'fiscal_end':end,'status':assessment['status'],'missing':missing,'diagnostics':{}}
            if end:
                for field in missing:
                    found=discover(payload.get('facts',{}),field,end)
                    candidates.extend([{'ticker':ticker,'cik':cik,**r} for r in found])
                    summary['diagnostics'][field]={'candidate_count':len(found),'candidates':found[:a.top]}
                    print(f'  {field}: {len(found)} candidate observations (NOT verified)')
            summaries.append(summary)
            print(f'{ticker}: {assessment["status"]} | {end} | {", ".join(missing)}',flush=True)
        except Exception as exc:
            summaries.append({'ticker':ticker,'cik':cik,'status':'ERROR','error':f'{type(exc).__name__}: {exc}'})
            print(f'{ticker}: ERROR: {exc}',flush=True)
        time.sleep(a.delay)
    prefix=Path(a.output_prefix)
    json_path=prefix.with_name(prefix.name+'_report.json')
    csv_path=prefix.with_name(prefix.name+'_candidates.csv')
    json_path.write_text(json.dumps(summaries,indent=2,ensure_ascii=False),encoding='utf-8')
    columns=('ticker','cik','field','namespace','tag','label','value','unit','start','end','days','period_type','days_from_fiscal_end','filed','form','fy','fp','frame','accn','semantic_matches','review')
    with csv_path.open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=columns);writer.writeheader();writer.writerows(candidates)
    print(f'\nSaved {json_path} and {csv_path}')

if __name__=='__main__': main()
