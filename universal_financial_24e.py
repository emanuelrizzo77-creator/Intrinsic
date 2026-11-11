"""Intrinsic 24E: audited SEC XBRL recovery, generic (no ticker-specific exceptions).

No replacement for review of issuer footnotes, leases or capital structure.
"""
from __future__ import annotations
from statistics import median
from universal_financial_24b import point, annual, valid
from universal_financial_24c import resolve_history, resolve_balance


def _shares(facts, end):
    for ns, tag in [('us-gaap','CommonStockSharesOutstanding'), ('dei','EntityCommonStockSharesOutstanding')]:
        records=facts.get(ns,{}).get(tag,{}).get('units',{}).get('shares',[])
        matches=[r for r in records if r.get('end')==end and not r.get('start') and r.get('form') in ('10-K','10-K/A') and valid(r.get('val')) and r['val']>0 and r.get('filed')]
        if matches:
            r=max(matches,key=lambda x:(x['filed'],x.get('accn','')))
            return r['val'],f'{ns}:{tag}', 'FISCAL_END_SNAPSHOT'
    return None,None,'MISSING_FISCAL_END_SHARES'


def assess_company(payload, sector_model='fcff', last_n=5):
    history=resolve_history(payload,last_n)
    rows=history.get('rows',[])
    if not rows:
        return {'status':'MISSING_DATA','latest_year':None,'missing':['Annual financial history'],'warnings':[],'history':history,'balance':None,'recovery':{}}
    facts=payload.get('facts',{})
    recovery={}
    for row in rows:
        end=row['Fiscal year end']; tags=row.setdefault('source_tags',{}); notes=row.setdefault('warnings',[])
        if row.get('D&A verified') is None:
            v,t=annual(facts,('DepreciationAmortizationAndAccretionNet',),end)
            if valid(v) and v>=0:
                row['D&A verified']=v;tags['D&A verified']=t
                notes.append('Broad D&A includes accretion; validate cash-flow classification before investment use.')
                recovery[f'{end}:D&A']={'value':v,'tag':t,'quality':'BROAD_DA_INCLUDES_ACCRETION'}
        if row.get('Effective tax rate') is None:
            records=facts.get('us-gaap',{}).get('EffectiveIncomeTaxRateContinuingOperations',{}).get('units',{}).get('pure',[])
            matches=[]
            from datetime import date
            for r in records:
                try: duration=(date.fromisoformat(end)-date.fromisoformat(r['start'])).days
                except (KeyError,ValueError,TypeError):continue
                if r.get('end')==end and 340<=duration<=400 and r.get('form') in ('10-K','10-K/A') and r.get('filed') and valid(r.get('val')) and 0<=r['val']<=.6: matches.append(r)
            if matches:
                r=max(matches,key=lambda x:(x['filed'],x.get('accn','')))
                row['Effective tax rate']=r['val'];tags['Effective tax rate']='us-gaap:EffectiveIncomeTaxRateContinuingOperations'
                recovery[f'{end}:Tax']={'value':r['val'],'tag':tags['Effective tax rate'],'quality':'REPORTED_EFFECTIVE_RATE'}
        rev=row.get('Revenue')
        for ratio,numerator in [('EBIT margin','EBIT'),('D&A / Revenue','D&A verified'),('CapEx / Revenue','CapEx')]:
            row[ratio]=row[numerator]/rev if valid(rev) and rev>0 and valid(row.get(numerator)) else None
    for metric in ('EBIT margin','D&A / Revenue','CapEx / Revenue','Effective tax rate'):
        vals=[r[metric] for r in rows if valid(r.get(metric))]
        history['historical_medians'][metric]=median(vals) if vals else None
        history['sample_counts'][metric]=len(vals)
    latest=rows[-1];end=latest['Fiscal year end']
    balance=resolve_balance(payload,[end])[0]
    if balance.get('Shares outstanding') is None:
        shares,source,quality=_shares(facts,end)
        if shares is not None:
            balance['Shares outstanding']=shares;balance.setdefault('tags',{})['Shares outstanding']=source
            recovery['Shares outstanding']={'value':shares,'tag':source,'quality':quality}
    if balance.get('Net debt (cash-only)') is None:
        cash,cash_tag=point(facts,('CashAndCashEquivalentsAtCarryingValue',),end)
        noncurrent,nc_tag=point(facts,('LongTermDebtNoncurrent',),end)
        current,cur_tag=point(facts,('DebtCurrent',),end)
        if all(valid(x) and x>=0 for x in (cash,noncurrent,current)):
            # DebtCurrent may include a different perimeter than long-term debt;
            # require explicit review, not an investment-grade assertion.
            total=noncurrent+current
            balance.update({'Cash':cash,'Total debt':total,'Long-term debt':noncurrent,'Current debt':current,'Net debt (cash-only)':total-cash})
            balance.setdefault('tags',{})['Net debt (cash-only)']=f'derived:{nc_tag}+{cur_tag}-{cash_tag}'
            balance.setdefault('warnings',[]).append('DebtCurrent + LongTermDebtNoncurrent is a provisional debt perimeter; verify notes and lease inclusion.')
            recovery['Net debt (cash-only)']={'value':total-cash,'tag':balance['tags']['Net debt (cash-only)'],'quality':'PROVISIONAL_DEBT_PERIMETER_REVIEW'}
    required=('Revenue','EBIT','D&A verified','CapEx','Effective tax rate')
    missing=[k for k in required if latest.get(k) is None]
    missing += [k for k in ('Net debt (cash-only)','Shares outstanding') if balance.get(k) is None]
    if len(rows)<3: missing.append('3+ fiscal periods')
    warnings=['Scenario only: WACC, equity bridge, dilution, leases and full operating NWC require validation.',
              'A missing Delta NWC requires an explicit scenario assumption, never an implicit zero.']
    if any(v['quality']=='PROVISIONAL_DEBT_PERIMETER_REVIEW' for v in recovery.values()):warnings.append('Debt perimeter needs review against financial statement footnotes.')
    status='UNSUPPORTED_SECTOR' if sector_model!='fcff' else 'MISSING_DATA' if missing else 'PROVISIONAL_SCENARIO_ONLY'
    return {'status':status,'latest_year':end,'missing':missing,'warnings':warnings,'history':history,'balance':balance,'recovery':recovery}
