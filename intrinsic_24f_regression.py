"""Compare the legacy Alphabet depreciation proxy with strict universal D&A.

This is an audit, not a DCF engine and does not modify dashboard files.
"""
import argparse
import json
from pathlib import Path


def classify(candidates, fiscal_end):
    annual = [r for r in candidates if r.get('end') == fiscal_end and r.get('period_type') == 'annual_flow' and r.get('unit') == 'USD' and r.get('form') in ('10-K', '10-K/A')]
    def value(tag):
        matches = [r for r in annual if r.get('tag') == tag]
        return max(matches, key=lambda r: (r.get('filed',''),r.get('accn',''))) if matches else None
    combined = value('DepreciationDepletionAndAmortization')
    dep = value('Depreciation') or value('DepreciationDepletionAndAmortizationPropertyPlantAndEquipment')
    amort = value('AmortizationOfIntangibleAssets')
    if combined:
        return {'status':'FULL_DA_REPORTED','value':combined['value'],'sources':[combined['tag']], 'dcf_eligible_as_verified':True}
    if dep and amort:
        return {'status':'FULL_DA_COMPONENTS','value':dep['value']+amort['value'],'sources':[dep['tag'],amort['tag']], 'dcf_eligible_as_verified':True}
    if dep:
        return {'status':'DEPRECIATION_ONLY_PROXY','value':dep['value'],'sources':[dep['tag']], 'dcf_eligible_as_verified':False}
    return {'status':'MISSING_DA','value':None,'sources':[],'dcf_eligible_as_verified':False}


def report(path):
    records=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(records,list): raise ValueError('Expected a list of company diagnostics')
    output=[]
    for item in records:
        if item.get('ticker')!='GOOGL':continue
        end=item['fiscal_end']
        candidates=item.get('diagnostics',{}).get('D&A verified',{}).get('candidates',[])
        result=classify(candidates,end)
        result.update(ticker='GOOGL',fiscal_end=end,legacy_dashboard='GOOGL proxy DCF: reported depreciation only, AR-AP partial NWC',universal_24e='MISSING_DATA due to full D&A requirement',conclusion='Legacy scenario can run with a disclosed proxy; it is not evidence of full D&A validation.')
        output.append(result)
    if not output:raise ValueError('GOOGL diagnostic not found')
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',default='intrinsic_24d_report.json')
    parser.add_argument('--output',default='intrinsic_24f_regression.json')
    args=parser.parse_args()
    data=report(args.report)
    Path(args.output).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    for row in data:
        print(f"{row['ticker']} | {row['fiscal_end']} | {row['status']} | {row['value']} USD")
        print('Source:', ', '.join(row['sources']))
        print('Legacy: scenario with a disclosed depreciation-only proxy')
        print('24E: full D&A validation not met; this is not a regression in the original dashboard')
    print('Saved',args.output)

if __name__=='__main__':main()
