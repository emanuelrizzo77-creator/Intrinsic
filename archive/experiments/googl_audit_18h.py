"""Intrinsic 18H: read-only audit of Alphabet D&A and operating working capital."""
from financial_engine import descargar_datos, construir_tabla
from historical_ratios_engine import obtener_ratios_empresa

TAGS = {
    'D&A candidates (inspect scope and overlap)': [
        'DepreciationDepletionAndAmortization',
        'DepreciationDepletionAndAmortizationPropertyPlantAndEquipment',
        'DepreciationAmortizationAndAccretionNet',
        'Depreciation', 'AmortizationOfIntangibleAssets',
        'DepreciationAndAmortizationInCashFlowStatement',
    ],
    'Working capital (instant balance)': [
        'AccountsReceivableNetCurrent', 'AccountsNotesAndOtherReceivablesNetCurrent',
        'InventoryNet', 'AccountsPayableCurrent', 'OtherAssetsCurrent',
        'OtherLiabilitiesCurrent',
    ],
    'Cash-flow working-capital changes (duration; not balance)': [
        'IncreaseDecreaseInAccountsReceivable',
        'IncreaseDecreaseInInventories',
        'IncreaseDecreaseInAccountsPayable',
        'IncreaseDecreaseInOtherOperatingAssets',
        'IncreaseDecreaseInOtherOperatingLiabilities',
    ],
}

def main():
    data = descargar_datos('GOOGL')
    facts = data.get('facts', {}).get('us-gaap', {})
    table = construir_tabla(data)
    print('\nALPHABET — RAW ANNUAL TABLE (USD B)')
    for metric in ('Revenue', 'EBIT', 'Depreciation', 'Amortization', 'CapEx'):
        values = table.get(metric, {})
        print(metric, {year: round(val / 1e9, 3) for year, val in sorted(values.items()) if year >= 2021})
    print('\nALPHABET — SEC TAG AUDIT (10-K, 2022 onwards)')
    for group, tags in TAGS.items():
        print('\n' + group)
        for tag in tags:
            concept = facts.get(tag, {})
            candidates = []
            for record in concept.get('units', {}).get('USD', []):
                if record.get('form') != '10-K' or record.get('end', '')[:4] < '2022':
                    continue
                value = record.get('val')
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                start = record.get('start')
                if start:
                    from datetime import date
                    try:
                        days = (date.fromisoformat(record['end']) - date.fromisoformat(start)).days
                    except (ValueError, KeyError):
                        continue
                    if not 340 <= days <= 400:
                        continue
                candidates.append(record)
            latest = {}
            for record in candidates:
                key = (record['end'], 'duration' if 'start' in record else 'instant')
                if key not in latest or record.get('filed', '') > latest[key].get('filed', ''):
                    latest[key] = record
            selected = sorted(latest.values(), key=lambda r: r['end'], reverse=True)[:5]
            if not selected:
                print(f'  {tag}: MISSING')
            for r in selected:
                print(f"  {tag}: {r['end']} | {r['val']/1e9:.3f} B | "
                      f"{'duration' if 'start' in r else 'instant'} | filed {r.get('filed')}")
    print('\nALPHABET — CURRENT RATIOS')
    result = obtener_ratios_empresa('GOOGL')
    for metric, stat in result['summary'].items():
        print(metric, stat)
    print('\nWARNINGS')
    for warning in result['warnings']:
        print('-', warning)
    print('\nDiagnostic only: no DCF inputs changed.')

if __name__ == '__main__':
    main()
