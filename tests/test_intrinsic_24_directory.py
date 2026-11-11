import tempfile
import unittest
from pathlib import Path
from intrinsic_24_directory import normalize_entries, save_cache, load_cache, search, download_directory

class DirectoryTests(unittest.TestCase):
    def test_exchange_format(self):
        payload = {'fields': ['cik', 'name', 'ticker', 'exchange'], 'data': [[21344, 'Coca Cola', 'KO', 'NYSE'], [320193, 'Apple Inc', 'AAPL', 'Nasdaq']]}
        rows = normalize_entries(payload)
        self.assertEqual(len(rows), 2)
        self.assertEqual(search(rows, 'ko')[0]['cik'], 21344)
    def test_fallback_format(self):
        rows = normalize_entries({'0': {'cik_str': 21344, 'ticker': 'KO', 'title': 'Coca Cola'}})
        self.assertEqual(rows[0]['ticker'], 'KO')
    def test_duplicate_and_invalid(self):
        rows = normalize_entries([{'cik': 1, 'ticker': 'X', 'company': 'X'}, {'cik': 1, 'ticker': 'X', 'company': 'X'}, {'cik': None, 'ticker': 'Y', 'company': 'Y'}])
        self.assertEqual(len(rows), 1)
    def test_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cache.json'
            save_cache([{'cik': 1, 'ticker': 'X', 'company': 'X', 'exchange': ''}], 'test', path)
            rows, metadata = load_cache(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(metadata['source'], 'test')
    def test_user_agent_required(self):
        with self.assertRaises(ValueError):
            download_directory('')

if __name__ == '__main__': unittest.main()
