"""Milestone 24B: cross-company SEC coverage audit. No valuations or dashboard edits.

Run inside the existing Intrinsic project with INTRINSIC_SEC_USER_AGENT set.
"""
from __future__ import annotations
import argparse
import csv
import time
from pathlib import Path
from company_explorer_21a import fetch_sec_directory
from financial_audit_21b import fetch_companyfacts
from universal_financial_24b import balance_24b, history_24b
from universal_valuation_21c import fetch_sec_profile, classify_sic

DEFAULT = 'KO,PEP,WMT,NKE,MCD,CAT,MSFT,AAPL,NVDA,GOOGL,JPM'

def audit_one(ticker, cik):
    payload = fetch_companyfacts(cik)
    profile = fetch_sec_profile(cik)
    decision = classify_sic(profile.get('sic'))
    history = history_24b(payload)
    rows = history.get('rows') or []
    latest = rows[-1] if rows else {}
    balance = balance_24b(payload, [latest['Fiscal year end']])[0] if latest else {}
    required = ['Revenue','EBIT','D&A verified','CapEx','Effective tax rate']
    missing = [k for k in required if latest.get(k) is None]
    if balance.get('Net debt (cash-only)') is None:
        missing.append('Net debt (cash-only)')
    if balance.get('Shares outstanding') is None:
        missing.append('Shares outstanding')
    if latest.get('Delta partial NWC') is None:
        missing.append('Delta partial NWC')
    if len(rows) < 3:
        missing.append('3+ fiscal periods')
    if decision.model != 'fcff':
        status = 'UNSUPPORTED_SECTOR'
    elif missing:
        status = 'MISSING_DATA'
    else:
        status = 'PROVISIONAL_SCENARIO_ONLY'
    return {'ticker':ticker,'company':payload.get('entityName',''), 'cik':cik,
            'sic':profile.get('sic',''), 'model':decision.model,
            'latest_year':latest.get('Fiscal year end',''), 'periods':len(rows),
            'status':status, 'missing':'; '.join(missing),
            'shares_date':balance.get('Shares measurement date',''),
            'warnings':'Partial NWC; WACC and lease bridge not independently validated'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tickers', default=DEFAULT, help='Comma-separated tickers')
    parser.add_argument('--output', default='intrinsic_24_coverage.csv')
    args = parser.parse_args()
    wanted = list(dict.fromkeys(x.strip().upper() for x in args.tickers.split(',') if x.strip()))
    directory = {t:(name,cik) for t,name,cik in fetch_sec_directory()}
    results = []
    for ticker in wanted:
        if ticker not in directory:
            row = {'ticker':ticker,'status':'TICKER_NOT_IN_SEC_DIRECTORY','missing':'Ticker not found'}
        else:
            name,cik = directory[ticker]
            try:
                row = audit_one(ticker,cik)
            except Exception as exc:
                row = {'ticker':ticker,'company':name,'cik':cik,'status':'ERROR',
                       'missing':f'{type(exc).__name__}: {exc}'}
            time.sleep(0.5)
        results.append(row)
        print(f"{ticker:7} | {row['status']:27} | {row.get('latest_year',''):10} | {row.get('missing','')}", flush=True)
    fields = ['ticker','company','cik','sic','model','latest_year','periods','status','missing','shares_date','warnings']
    with Path(args.output).open('w',newline='',encoding='utf-8') as file:
        writer = csv.DictWriter(file,fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f'\nReport saved to {args.output}')

if __name__ == '__main__':
    main()
