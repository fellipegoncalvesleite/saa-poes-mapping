import unittest
import numpy as np,pandas as pd
from saa import channel_assurance as ca
from saa.aggregate import build_grid_table

class ChannelAssuranceTests(unittest.TestCase):
    def test_draw_calendar_no_wrap_multiplicity_determinism(self):
        for length in [1,3,7]:
            a,starts=ca.draw_days(length,20,42);b,_=ca.draw_days(length,20,42)
            np.testing.assert_array_equal(a,b);self.assertEqual(a.shape,(20,31))
            self.assertTrue(((starts>=0)&(starts<=31-length)).all())
            expanded=(starts[:,:,None]+np.arange(length)).reshape(20,-1)[:,:31]
            np.testing.assert_array_equal(a,expanded)
            self.assertTrue(any(len(set(row))<31 for row in a))
    def test_daily_sums_counts_equal_explicit_repeated_records_and_missing_days(self):
        d=pd.DataFrame({'time':pd.to_datetime(['2024-01-01Z'.replace('Z','T00:00:00Z')]*2+['2024-01-02T00:00:00Z']*3),'lat':[-20.]*5,'lon180':[-50.]*5,'p1':[2.,4.,10.,20.,np.nan],'p2':[1.,0.,np.nan,4.,6.]})
        sums,counts=ca.daily_cells(d,['p1','p2']);draw=np.array([0,1,1,2])
        got_s,got_n=ca.combine_days(sums,counts,draw)
        repeated=pd.concat([d[d.time.dt.day==x+1] for x in draw])
        for c,channel in enumerate(['p1','p2']):
            g=build_grid_table(repeated,channel,5,5);i=int((g.lat_bin_center.iloc[0]+70)/5);j=int((g.lon_bin_center.iloc[0]+100)/5);k=i*24+j
            self.assertEqual(got_n[c,k],int(g.sample_count.iloc[0]));self.assertAlmostEqual(got_s[c,k]/got_n[c,k],g.mean_flux.iloc[0])
        self.assertEqual(got_n[0].sum(),6);self.assertEqual(got_n[1].sum(),6)
    def test_field_identical_scaling_unequal_area_zero_missing(self):
        lat=np.array([0.,60.]);lon=np.array([0.,10.]);area=np.array([2.,1.]);f=np.array([[1.,1.],[10.,10.],[1.,0.]])
        p,cen=ca.normalized_fields(f,lat,lon,area)
        np.testing.assert_allclose(cen[0],[20.,10/3]);self.assertAlmostEqual(np.minimum(p[0],p[1]).sum(),1)
        np.testing.assert_allclose(p,ca.normalized_fields(f*np.array([3,5,7])[:,None],lat,lon,area)[0])
        self.assertEqual(p[2,1],0)
        for invalid in [np.zeros((3,2)),np.array([[1.,-1.]]),np.array([[1.,np.nan]])]:
            with self.assertRaises(ValueError):ca.normalized_fields(invalid,lat,lon,area)
        with self.assertRaises(ValueError):ca.normalized_fields(np.empty((3,0)),np.array([]),np.array([]),np.array([]))
    def test_common_support_excludes_missing_not_zero(self):
        f=np.array([[0.,2.,np.nan],[1.,4.,5.]]);m=np.array([[True,True,True],[True,False,True]])
        np.testing.assert_array_equal(ca.common_support(f,m),[True,False,False])
    def test_replicate_rebuilds_coverage_percentiles_and_reports_undefined(self):
        sums=np.zeros((3,432));counts=np.zeros((3,432),int)
        sums[:,0]=40;counts[:,0]=40;sums[:,1]=300;counts[:,1]=29
        r=ca.replicate_metrics(sums,counts)
        self.assertEqual(r[0]['eligible_cells'],1);self.assertEqual(r[0]['selected_cells'],1)
        sums[0]=0;r=ca.replicate_metrics(sums,counts);self.assertEqual(r[0]['status'],'zero_mass')
        counts[1]=0;r=ca.replicate_metrics(sums,counts);self.assertEqual(r[1]['status'],'empty_support')
    def test_protocol_cannot_silently_mislabel_fixed_calculations(self):
        import json,copy
        from pathlib import Path
        protocol=json.loads((Path(__file__).resolve().parents[1]/'paper/inputs/channel_assurance_protocol.json').read_text())
        ca.validate_protocol(protocol)
        for key,value in [('grid_deg',2),('percentile',95),('coverage_min_samples',10),('statistic','median_flux'),('month','2024-02'),('wrap',True)]:
            altered=copy.deepcopy(protocol);altered[key]=value
            with self.assertRaisesRegex(ValueError,key):ca.validate_protocol(altered)
        altered=copy.deepcopy(protocol);altered['morphology']['grids']=[5]
        with self.assertRaisesRegex(ValueError,'morphology'):ca.validate_protocol(altered)
