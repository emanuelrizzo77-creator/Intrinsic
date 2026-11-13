import unittest
from universal_financial_23d import forecast_23d

H = {'company':'COCA COLA CO', 'rows':[{'Fiscal year end':'2025-12-31','Revenue':47941000000}],
     'historical_medians':{'Revenue growth':.0462566741,'EBIT margin':.2536740768,
     'Effective tax rate':.180985795,'D&A / Revenue':.0246535822,
     'CapEx / Revenue':.0404773353,'Delta partial NWC / Delta Revenue':-.0204950354}}
class Test23D(unittest.TestCase):
    def test_five_years(self):
        r=forecast_23d(H)
        self.assertEqual(len(r['rows']),5)
        self.assertEqual(r['rows'][0]['Year'],'2026E')
        self.assertEqual(r['rows'][-1]['Year'],'2030E')
        self.assertFalse(r['valuation_ready'])
    def test_fcff_identity(self):
        row=forecast_23d(H)['rows'][0]
        self.assertAlmostEqual(row['FCFF'],row['NOPAT']+row['D&A']-row['CapEx']-row['Delta NWC'])
    def test_override(self):
        r=forecast_23d(H,overrides={'Revenue growth':0.03})
        self.assertAlmostEqual(r['rows'][0]['Revenue'],47941000000*1.03)
        self.assertEqual(r['assumption_sources']['Revenue growth'],'manual override')
    def test_nwc_modes(self):
        z=forecast_23d(H)['rows'][0]
        p=forecast_23d(H,nwc_policy='partial_proxy')['rows'][0]
        self.assertEqual(z['Delta NWC'],0)
        self.assertNotEqual(p['Delta NWC'],0)
        m=forecast_23d(H,nwc_policy='manual_ratio',nwc_ratio=.05)['rows'][0]
        self.assertAlmostEqual(m['Delta NWC'],(m['Revenue']-47941000000)*.05)
    def test_missing_median_rejected(self):
        h={**H,'historical_medians':{}}
        with self.assertRaises(ValueError): forecast_23d(h)
    def test_bad_inputs_rejected(self):
        with self.assertRaises(ValueError): forecast_23d(H,overrides={'Revenue growth':float('nan')})
        with self.assertRaises(ValueError): forecast_23d(H,nwc_policy='manual_ratio')
        with self.assertRaises(ValueError): forecast_23d(H,years=0)
if __name__=='__main__': unittest.main()
