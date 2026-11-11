"""Audit 24C across SEC tickers. No dashboard modifications or valuation claims."""
import argparse, csv, time
from pathlib import Path
from company_explorer_21a import fetch_sec_directory
from financial_audit_21b import fetch_companyfacts
from universal_valuation_21c import fetch_sec_profile, classify_sic
from universal_financial_24e import assess_company

DEFAULT = 'KO,PEP,WMT,NKE,MCD,CAT,MSFT,AAPL,NVDA,GOOGL,JPM'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tickers',default=DEFAULT)
    parser.add_argument('--output',default='intrinsic_24e_coverage.csv')
    parser.add_argument('--delay',type=float,default=0.5)
    args=parser.parse_args()
    if args.delay < .2: parser.error('Use --delay >= 0.2 to avoid aggressive SEC requests')
    directory={t:(name,cik) for t,name,cik in fetch_sec_directory()}
    results=[]
    for ticker in dict.fromkeys(x.strip().upper() for x in args.tickers.split(',') if x.strip()):
        name,cik=directory.get(ticker,('',None))
        row={'ticker':ticker,'company':name,'cik':cik,'status':'NOT_IN_DIRECTORY','latest_year':'','missing':'','warnings':''}
        if cik is not None:
            try:
                profile=fetch_sec_profile(cik)
                model=classify_sic(profile.get('sic')).model
                result=assess_company(fetch_companyfacts(cik),model)
                row.update(status=result['status'],latest_year=result['latest_year'] or '',
                           missing='; '.join(result['missing']),warnings='; '.join(result['warnings']))
            except Exception as e:
                row.update(status='ERROR',missing=f'{type(e).__name__}: {e}')
            time.sleep(args.delay)
        results.append(row)
        print(f"{ticker:7} | {row['status']:27} | {row['latest_year']:10} | {row['missing']}",flush=True)
    with Path(args.output).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=('ticker','company','cik','status','latest_year','missing','warnings'))
        w.writeheader();w.writerows(results)
    print(f'\nSaved {args.output}')

if __name__=='__main__':main()
