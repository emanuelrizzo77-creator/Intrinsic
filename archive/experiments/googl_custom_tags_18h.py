"""Intrinsic 18H: read-only audit of Alphabet custom XBRL facts.

No financial values are imputed; no production modules are modified.
"""
from __future__ import annotations
from datetime import date
import re
from financial_engine import descargar_datos

PATTERN = re.compile(r"depreci|amorti|inventor|workingcapital|operatingasset|operatingliabil", re.I)

def main():
    datos = descargar_datos('GOOGL')
    print('\nALPHABET: 10-K XBRL tags across namespaces (2022-2025)')
    for namespace, facts in sorted(datos.get('facts', {}).items()):
        for tag, fact in sorted(facts.items()):
            if not (PATTERN.search(tag) or PATTERN.search(fact.get('label') or '')):
                continue
            candidates = []
            for unit, records in fact.get('units', {}).items():
                if unit != 'USD':
                    continue
                for r in records:
                    if r.get('form') != '10-K' or not all(k in r for k in ('end','filed','val')):
                        continue
                    try:
                        end = date.fromisoformat(r['end'])
                        filed = date.fromisoformat(r['filed'])
                        if end.year not in (2022,2023,2024,2025):
                            continue
                        if 'start' in r:
                            start = date.fromisoformat(r['start'])
                            if not 340 <= (end-start).days <= 400:
                                continue
                            kind = 'annual duration'
                        else:
                            kind = 'instant'
                    except (ValueError, TypeError):
                        continue
                    if not isinstance(r['val'], (int,float)) or isinstance(r['val'], bool):
                        continue
                    candidates.append((end, filed, r['val'], kind))
            # One latest-filed observation per fiscal end date; do not mix periods.
            by_end = {}
            for end, filed, val, kind in candidates:
                if end not in by_end or filed > by_end[end][0]:
                    by_end[end] = (filed, val, kind)
            if not by_end:
                continue
            print(f'\n{namespace}:{tag} | {fact.get("label", "")}')
            for end, (filed, val, kind) in sorted(by_end.items()):
                print(f'  {end} | {val/1e9:,.3f} B | {kind} | filed {filed}')
    print('\nAUDIT ONLY: matching names do not prove equivalent accounting scope.')
    print('Review original 10-K notes before mapping custom tags to D&A or NWC.')

if __name__ == '__main__':
    main()
