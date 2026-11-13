"""Live SEC coverage comparison of 24E vs 24G; does not change the dashboard."""
import argparse,csv,time
from company_explorer_21a import fetch_sec_directory
from financial_audit_21b import fetch_companyfacts
from universal_valuation_21c import fetch_sec_profile,classify_sic
from universal_financial_24e import assess_company as old
from universal_financial_24g import assess_company as new

def main():
    p=argparse.ArgumentParser();p.add_argument('--tickers',default='KO,PEP,WMT,NKE,MCD,CAT,MSFT,AAPL,NVDA,GOOGL,JPM');p.add_argument('--delay',type=float,default=.5);p.add_argument('--output',default='intrinsic_24g_coverage.csv');a=p.parse_args()
    if a.delay<.2:p.error('Use --delay >= 0.2')
    directory={t:(name,cik) for t,name,cik in fetch_sec_directory()}
    rows=[]
    for ticker in dict.fromkeys(t.strip().upper() for t in a.tickers.split(',') if t.strip()):
        name,cik=directory.get(ticker,('',None))
        r={'ticker':ticker,'company':name,'cik':cik,'24e_status':'NOT_IN_DIRECTORY','24g_status':'NOT_IN_DIRECTORY','missing':'','proxy':'','error':''}
        if cik is not None:
            try:
                model=classify_sic(fetch_sec_profile(cik).get('sic')).model
                data=fetch_companyfacts(cik)
                before=old(data,model);after=new(data,model)
                r.update({'24e_status':before['status'],'24g_status':after['status'],'missing':'; '.join(after['missing']), 'proxy':'; '.join(f'{year}:{v["value"]}' for year,v in after['proxies'].items())})
            except Exception as e:r['error']=f'{type(e).__name__}: {e}'
            time.sleep(a.delay)
        rows.append(r)
        print(f'{ticker:7} | {r["24e_status"]:28} -> {r["24g_status"]:32} | {r["missing"]}',flush=True)
    with open(a.output,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print('Saved',a.output)
if __name__=='__main__':main()
