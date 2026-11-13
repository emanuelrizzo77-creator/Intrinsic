"""Intrinsic Milestone 18C: read-only SEC tag audit. Does not change valuation inputs."""
import argparse
from datetime import date
from financial_engine import descargar_datos

TAGS = {
    'NVDA': ['PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets','PaymentsForProceedsFromOtherInvestingActivities','DepreciationDepletionAndAmortization'],
    'GOOGL': ['Depreciation','AmortizationOfIntangibleAssets','DepreciationDepletionAndAmortization','DepreciationAmortizationAndAccretionNet','InventoryNet','InventoryFinishedGoods','InventoryRawMaterialsAndSupplies','AccountsReceivableNetCurrent','AccountsPayableCurrent'],
}

def records(fact, min_year):
    out = []
    for unit, values in fact.get('units', {}).items():
        if unit != 'USD':
            continue
        for r in values:
            if r.get('form') != '10-K' or not r.get('end') or not isinstance(r.get('val'), (int,float)):
                continue
            if int(r['end'][:4]) < min_year:
                continue
            start = r.get('start')
            if start:
                try:
                    days = (date.fromisoformat(r['end']) - date.fromisoformat(start)).days
                except ValueError:
                    continue
                if not 340 <= days <= 400:
                    continue
            out.append((r['end'], r.get('filed',''), r['val'], r.get('fp'), r.get('fy'), start))
    # One observation per end date, most recent filing. Keep distinct end dates.
    selected = {}
    for row in out:
        if row[0] not in selected or row[1] > selected[row[0]][1]:
            selected[row[0]] = row
    return sorted(selected.values(), reverse=True)[:6]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('ticker', choices=['NVDA','GOOGL'])
    p.add_argument('--since', type=int, default=2022)
    args = p.parse_args()
    facts = descargar_datos(args.ticker).get('facts',{}).get('us-gaap',{})
    for tag in TAGS[args.ticker]:
        fact = facts.get(tag)
        print(f'\n{tag}:')
        if not fact:
            print('  NOT PRESENT')
            continue
        print('  Label:', fact.get('label',''))
        print('  Description:', fact.get('description','')[:300].replace('\n',' '))
        obs = records(fact, args.since)
        if not obs:
            print('  NO RECENT ANNUAL 10-K USD OBSERVATIONS')
        for end, filed, value, fp, fy, start in obs:
            print(f'  {start or "instant":>10} -> {end} | filed {filed} | {value/1e6:,.1f} USD M | fp={fp} fy={fy}')
    if args.ticker == 'GOOGL':
        print('\nOTHER POSSIBLE INVENTORY / D&A TAGS (names only):')
        for tag in sorted(facts):
            if ('Inventor' in tag or 'Amortiz' in tag or 'Depreciat' in tag) and tag not in TAGS[args.ticker]:
                obs = records(facts[tag], args.since)
                if obs:
                    print(' ',tag,'latest:',obs[0][0])

if __name__ == '__main__':
    main()
