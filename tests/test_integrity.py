import unittest
import numpy as np
import pandas as pd
from saa import integrity

class IntegrityTests(unittest.TestCase):
    def test_omit_uses_hash_and_native_index_not_time_or_flux(self):
        d=pd.DataFrame({'source_sha256':['a','a','b'],'native_index':[0,1,0],'time':[1,1,1],'flux':[4,4,4]})
        out=integrity.omit_record(d,'a',1)
        self.assertEqual(list(zip(out.source_sha256,out.native_index)),[('a',0),('b',0)])
        with self.assertRaises(ValueError): integrity.omit_record(d,'a',9)
    def test_trigger_gap_zero_missing_and_strict_ratio(self):
        t=np.arange(41)*2.;v=np.ones(41);v[20]=101
        ev,hit=integrity.review_trigger(t,v,2)
        self.assertTrue(ev[20]);self.assertTrue(hit[20])
        for invalid in [0,np.nan,-1]:
            w=v.copy();w[11]=invalid
            self.assertFalse(integrity.review_trigger(t,w,2)[0][20])
        for dt in [0,8]:
            u=t.copy();u[15:]+=dt-2
            self.assertFalse(integrity.review_trigger(u,v,2)[0][20])
        v[20]=100
        self.assertFalse(integrity.review_trigger(t,v,2)[1][20])
    def test_independent_area_unequal_area_centroid(self):
        a=integrity.reference_area(np.array([0.,60.]),5)
        self.assertAlmostEqual(a[0]/a[1],2)
        lat,lon=integrity.reference_centroid(np.array([0.,60.]),np.array([0.,10.]),np.ones(2),a)
        self.assertAlmostEqual(lat,20);self.assertAlmostEqual(lon,10/3)
