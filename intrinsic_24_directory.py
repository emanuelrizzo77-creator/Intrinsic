"""Intrinsic Milestone 24: SEC ticker directory (discovery, not valuation).

Usage:
  python intrinsic_24_directory.py refresh
  python intrinsic_24_directory.py search 'coca cola'
  python intrinsic_24_directory.py search MSFT
  python intrinsic_24_directory.py stats

SEC requests require an identifiable User-Agent. Set SEC_USER_AGENT to
'Your Name your.email@example.com' before refresh.
"""
import argparse
import csv
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen

PRIMARY_URL = 'https://www.sec.gov/files/company_tickers_exchange.json'
FALLBACK_URL = 'https://www.sec.gov/files/company_tickers.json'
DEFAULT_CACHE = Path(__file__).resolve().parent / '.intrinsic_cache' / 'sec_company_directory.json'


def normalize_entries(payload):
    """Convert either SEC directory format to a list of CIK/ticker/company rows."""
    rows = []
    if isinstance(payload, dict) and isinstance(payload.get('fields'), list) and isinstance(payload.get('data'), list):
        fields = [str(x).lower() for x in payload['fields']]
        for values in payload['data']:
            record = dict(zip(fields, values))
            rows.append({'cik': record.get('cik'), 'ticker': record.get('ticker'),
                         'company': record.get('name') or record.get('title'),
                         'exchange': record.get('exchange')})
    elif isinstance(payload, dict):
        for record in payload.values():
            if isinstance(record, dict):
                rows.append({'cik': record.get('cik_str') or record.get('cik'),
                             'ticker': record.get('ticker'),
                             'company': record.get('title') or record.get('name'),
                             'exchange': record.get('exchange')})
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError('Unsupported SEC directory format')
    clean, seen = [], set()
    for row in rows:
        try:
            cik = int(row['cik'])
        except (ValueError, TypeError, KeyError):
            continue
        ticker = str(row.get('ticker') or '').strip().upper()
        company = str(row.get('company') or '').strip()
        if not ticker or not company or (cik, ticker) in seen:
            continue
        seen.add((cik, ticker))
        clean.append({'cik': cik, 'ticker': ticker, 'company': company,
                      'exchange': str(row.get('exchange') or '')})
    return sorted(clean, key=lambda r: (r['ticker'], r['cik']))


def download_directory(user_agent, opener=urlopen):
    if not user_agent or '@' not in user_agent or 'example.com' in user_agent:
        raise ValueError('Set SEC_USER_AGENT to your real name and contact email before downloading SEC data.')
    errors = []
    for url in (PRIMARY_URL, FALLBACK_URL):
        try:
            req = Request(url, headers={'User-Agent': user_agent, 'Accept': 'application/json'})
            with opener(req, timeout=30) as response:
                payload = json.load(response)
            rows = normalize_entries(payload)
            if not rows:
                raise ValueError('SEC returned no usable tickers')
            return rows, url
        except Exception as exc:
            errors.append(f'{url}: {exc}')
    raise RuntimeError('Unable to download SEC directory. ' + ' | '.join(errors))


def save_cache(rows, source, path=DEFAULT_CACHE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = {'updated_utc': datetime.now(timezone.utc).isoformat(), 'source': source, 'entries': rows}
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(content, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)
    return path


def load_cache(path=DEFAULT_CACHE):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError('No local directory yet. Run: python intrinsic_24_directory.py refresh')
    payload = json.loads(path.read_text(encoding='utf-8'))
    return normalize_entries(payload['entries']), payload


def search(rows, query, limit=20):
    q = query.strip().casefold()
    if not q:
        return []
    def score(r):
        t, n = r['ticker'].casefold(), r['company'].casefold()
        if t == q: return 0
        if t.startswith(q): return 1
        if n.startswith(q): return 2
        if q in t: return 3
        if q in n: return 4
        return 99
    return sorted((r for r in rows if score(r) < 99), key=lambda r: (score(r), r['ticker']))[:limit]


def main():
    parser = argparse.ArgumentParser(description='Intrinsic SEC company directory')
    parser.add_argument('--cache', type=Path, default=DEFAULT_CACHE)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('refresh')
    p = sub.add_parser('search'); p.add_argument('query'); p.add_argument('--limit', type=int, default=20)
    sub.add_parser('stats')
    p = sub.add_parser('export'); p.add_argument('--output', default='intrinsic_sec_companies.csv')
    args = parser.parse_args()
    if args.action == 'refresh':
        rows, source = download_directory(os.environ.get('SEC_USER_AGENT', ''))
        path = save_cache(rows, source, args.cache)
        print(f'Saved {len(rows):,} ticker entries to {path}')
        print(f'Source: {source}')
        return
    rows, metadata = load_cache(args.cache)
    if args.action == 'stats':
        print(f'Tickers: {len(rows):,} | Unique CIKs: {len({r["cik"] for r in rows}):,}')
        print(f'Updated: {metadata.get("updated_utc")} | Source: {metadata.get("source")}')
    elif args.action == 'search':
        found = search(rows, args.query, max(0, args.limit))
        for r in found:
            print(f'{r["ticker"]:10} CIK {r["cik"]:<10} {r["company"]}  [{r["exchange"]}]')
        if not found: print('No matches in SEC directory.')
    elif args.action == 'export':
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['ticker', 'cik', 'company', 'exchange'])
            writer.writeheader(); writer.writerows(rows)
        print(f'Exported {len(rows):,} entries to {args.output}')


if __name__ == '__main__':
    main()
