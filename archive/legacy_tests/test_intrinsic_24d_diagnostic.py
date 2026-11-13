import unittest
from intrinsic_24d_diagnostic import discover, directory_from_cache
from pathlib import Path
from tempfile import TemporaryDirectory

class DiagnosticTests(unittest.TestCase):
    def test_annual_and_instant(self):
        facts={'us-gaap':{'OperatingIncomeLoss':{'label':'Operating income','units':{'USD':[
            {'start':'2025-01-01','end':'2025-12-31','filed':'2026-02-01','form':'10-K','val':100},
            {'start':'2025-10-01','end':'2025-12-31','filed':'2026-02-01','form':'10-K','val':25}]}}}}
        result=discover(facts,'EBIT','2025-12-31')
        self.assertEqual(result[0]['period_type'],'annual_flow')
        self.assertEqual(result[1]['period_type'],'other_duration')
    def test_no_10q_or_wrong_units(self):
        facts={'us-gaap':{'OperatingIncomeLoss':{'units':{'USD':[{'end':'2025-12-31','filed':'2026-02-01','form':'10-Q','val':100}], 'shares':[{'end':'2025-12-31','filed':'2026-02-01','form':'10-K','val':200}]}}}}
        self.assertEqual(discover(facts,'EBIT','2025-12-31'),[])
    def test_custom_namespace_is_candidate(self):
        facts={'custom':{'OperatingProfit':{'units':{'USD':[{'start':'2025-01-01','end':'2025-12-31','filed':'2026-02-01','form':'10-K','val':50}]}}}}
        self.assertEqual(discover(facts,'EBIT','2025-12-31')[0]['review'],'CANDIDATE_ONLY_NOT_VERIFIED')
    def test_directory_cache(self):
        with TemporaryDirectory() as folder:
            p=Path(folder)/'cache.json';p.write_text('{"entries":[{"ticker":"KO","cik":21344}]}')
            self.assertEqual(directory_from_cache(p)['KO'],21344)

if __name__=='__main__':unittest.main()
