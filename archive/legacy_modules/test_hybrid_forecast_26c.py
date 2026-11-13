import unittest
from hybrid_forecast_26c import generar_forecast_hibrido


def sample(growth=(0.10, 0.12, 0.14, 0.16, 0.18, 0.20)):
    rows=[]
    for i,g in enumerate(growth):
        rows.append({'Fiscal year end': f'{2019+i}-12-31',
                     'Revenue growth':g, 'EBIT margin':0.20+i*0.01,
                     'D&A / Revenue':0.05, 'CapEx / Revenue':0.07})
    return {'rows': rows}

class TestHybrid(unittest.TestCase):
    def test_shapes_and_scenario_order(self):
        out=generar_forecast_hibrido(sample())
        self.assertFalse(out['validated'])
        for scenario in ('base','conservative','optimistic'):
            for key in ('growth','ebit_margin','da_ratio','capex_ratio'):
                self.assertEqual(len(out['scenarios'][scenario][key]),5)
        self.assertLess(out['scenarios']['conservative']['growth'][0],out['scenarios']['base']['growth'][0])
        self.assertLess(out['scenarios']['base']['growth'][0],out['scenarios']['optimistic']['growth'][0])

    def test_exceptional_growth_converges(self):
        out=generar_forecast_hibrido(sample((0.02,0.04,0.08,0.70,0.90,0.80)))
        growth=out['scenarios']['base']['growth']
        self.assertGreater(growth[0],growth[-1])

    def test_missing_recent_da_blocks(self):
        h=sample()
        h['rows'][-1]['D&A / Revenue']=None
        with self.assertRaisesRegex(ValueError,'Missing recent'):
            generar_forecast_hibrido(h)

    def test_no_mutation_and_determinism(self):
        h=sample()
        before=repr(h)
        a=generar_forecast_hibrido(h)
        b=generar_forecast_hibrido(h)
        self.assertEqual(a,b)
        self.assertEqual(repr(h),before)

if __name__=='__main__':
    unittest.main()
