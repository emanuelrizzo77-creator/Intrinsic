"""Read-only SEC balance audit for Intrinsic. Does not alter valuation inputs."""
import argparse
from financial_engine import descargar_datos
from market_data import obtener_balance_sec

TERMS = ('CashAndCashEquivalents', 'CashCashEquivalents', 'ShortTermInvest',
         'MarketableSecurit', 'AvailableForSaleSecurit', 'TradingSecurit',
         'DebtSecurit', 'OtherShortTermInvest', 'OtherCurrentFinancialAsset',
         'LongTermInvest', 'LongTermDebt', 'ShortTermBorrow', 'CurrentPortionOfLongTermDebt')

def observations(fact, years=5):
    values = fact.get('units', {}).get('USD', [])
    candidates = [r for r in values if r.get('form') == '10-K'
                  and not r.get('start') and r.get('end')
                  and isinstance(r.get('val'), (int, float))
                  and not isinstance(r.get('val'), bool) and r['val'] >= 0]
    if not candidates:
        return []
    latest_year = max(int(r['end'][:4]) for r in candidates)
    selected = {}
    for r in candidates:
        if int(r['end'][:4]) < latest_year - years + 1:
            continue
        key = r['end']
        if key not in selected or r.get('filed', '') > selected[key].get('filed', ''):
            selected[key] = r
    return sorted(selected.values(), key=lambda r: r['end'], reverse=True)[:years]

def main():
    p = argparse.ArgumentParser()
    p.add_argument('ticker', choices=['MSFT', 'AAPL', 'NVDA', 'GOOGL'])
    args = p.parse_args()
    data = descargar_datos(args.ticker)
    print('\n=== CURRENT BALANCE MAPPING ===')
    try:
        balance = obtener_balance_sec(data)
        for name, record in balance.items():
            print(f'{name}: {record}')
    except Exception as error:
        print(f'Balance extraction error: {type(error).__name__}: {error}')
    print('\n=== RELEVANT SEC US-GAAP TAGS ===')
    facts = data.get('facts', {}).get('us-gaap', {})
    for tag in sorted(facts):
        if not any(term.lower() in tag.lower() for term in TERMS):
            continue
        obs = observations(facts[tag])
        if not obs:
            continue
        print(f'\n{tag} | {facts[tag].get("label", "")}')
        print('Description:', facts[tag].get('description', '')[:190].replace('\n', ' '))
        for r in obs[:3]:
            print(f'  {r["end"]} | {r["val"]/1e9:,.3f} USD B | filed {r.get("filed", "")}')
    print('\nNOTE: Tags may overlap or include cash. Do not add amounts without reconciliation.')

if __name__ == '__main__':
    main()
