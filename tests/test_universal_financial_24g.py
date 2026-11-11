import unittest
from unittest.mock import patch
import universal_financial_24g as g

END='2025-12-31'

def baseline(missing=None, sector='fcff'):
    return {'status':'MISSING_DATA','latest_year':END,'missing':list(missing or ['D&A verified']),
            'warnings':[],'history':{'rows':[{'Fiscal year end':END,'D&A verified':None,'source_tags':{},'warnings':[]}]},
            'balance':{},'recovery':{}}

def payload(tag='Depreciation', val=21136000000, start='2025-01-01', end=END):
    return {'facts':{'us-gaap':{tag:{'units':{'USD':[{'val':val,'start':start,'end':end,'form':'10-K','filed':'2026-02-01'}]}}}}}

class ResolverTests(unittest.TestCase):
    @patch.object(g,'assess_24e',side_effect=lambda *a,**kw: baseline())
    def test_proxy_keeps_verified_empty(self,_):
        r=g.assess_company(payload())
        self.assertEqual(r['status'],'PROVISIONAL_PROXY_SCENARIO_ONLY')
        self.assertIsNone(r['history']['rows'][-1]['D&A verified'])
        self.assertEqual(r['proxies'][END]['value'],21136000000)
    @patch.object(g,'assess_24e',side_effect=lambda *a,**kw: baseline())
    def test_disabled_proxy(self,_):
        r=g.assess_company(payload(),allow_depreciation_proxy=False)
        self.assertEqual(r['status'],'MISSING_DATA')
    @patch.object(g,'assess_24e',side_effect=lambda *a,**kw: baseline())
    def test_wrong_period_rejected(self,_):
        r=g.assess_company(payload(start='2025-10-01'))
        self.assertEqual(r['status'],'MISSING_DATA')
    @patch.object(g,'assess_24e',side_effect=lambda *a,**kw: baseline())
    def test_instant_rejected(self,_):
        p=payload(); del p['facts']['us-gaap']['Depreciation']['units']['USD'][0]['start']
        self.assertEqual(g.assess_company(p)['status'],'MISSING_DATA')
    @patch.object(g,'assess_24e',side_effect=lambda *a,**kw: baseline(['D&A verified','EBIT']))
    def test_other_missing_still_blocks(self,_):
        self.assertEqual(g.assess_company(payload())['missing'],['EBIT'])
    @patch.object(g,'assess_24e',side_effect=lambda *a,**kw: baseline())
    def test_sector_unsupported(self,_):
        self.assertEqual(g.assess_company(payload(),sector_model='unsupported')['status'],'UNSUPPORTED_SECTOR')
    @patch.object(g,'assess_24e',side_effect=lambda *a,**kw: baseline([]))
    def test_no_mutation(self,_):
        r=g.assess_company(payload())
        self.assertIn(r['status'],('PROVISIONAL_PROXY_SCENARIO_ONLY','PROVISIONAL_SCENARIO_ONLY'))

if __name__=='__main__': unittest.main()
