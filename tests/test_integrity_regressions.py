"""Regressions for issues demonstrated by the Phase 1 executable probes."""
import unittest,tempfile,shutil
from pathlib import Path
import numpy as np,pandas as pd,xarray as xr
from saa.load_poes import extract_channels_dataframe
from saa.viewer_export import build_viewer_payload,_cp5c_payload
from saa.magnetic_generality import classify_generality

ROOT=Path(__file__).resolve().parents[1]
class IntegrityRegressions(unittest.TestCase):
    def test_missing_flag_stays_missing(self):
        ds=xr.Dataset({k:(k,[v]) for k,v in {'time':1704067200000,'lat':-20.,'lon':300.,'mep_omni_flux_p1':1.,'mep_IFC_on':np.nan,'mep_omni_flux_flag_fit':np.nan}.items()})
        d=extract_channels_dataframe(ds,'poes_n19_20240101_proc.nc')
        self.assertTrue(pd.isna(d.mep_IFC_on.iloc[0]));self.assertTrue(pd.isna(d.mep_omni_flux_flag_fit.iloc[0]))
    def test_export_rejects_stale_centroid(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            for f in (ROOT/'outputs/tables').glob('*.parquet'):shutil.copy2(f,p/f.name)
            build_viewer_payload(p)
            f=p/'cp4b_threshold_sensitivity.parquet';d=pd.read_parquet(f);d.loc[0,'centroid_lat_flux_weighted']+=1;d.to_parquet(f,index=False)
            with self.assertRaisesRegex(ValueError,'centroid'):build_viewer_payload(p)
    def test_active_magnetic_payload_retires_mlt_dominance(self):
        d=pd.read_parquet(ROOT/'outputs/tables/cp5c_multisatellite_magnetic_generality_summary.parquet');p=_cp5c_payload(d)
        self.assertEqual(p['classification'],'RETIRED_MLT_RUBRIC')
        self.assertIsNone(p['btot_dominance_support_count'])
        self.assertTrue(all(r['mlt_separation'] is None and r['btot_dominance_support'] is None for r in p['satellites']))
    def test_separate_count_legacy_contract(self):
        d=pd.DataFrame({'low_btot_support':[True,True,True,True,False],'btot_dominance_support':[True,True,True,False,True],'btot_separation_metric':[1.]*5})
        self.assertEqual(classify_generality(d),'CONSISTENT')
    def test_no_fit_and_negative_omni_values_are_missing_zero_and_fit1_kept(self):
        ds=xr.Dataset({k:(k,v) for k,v in {'time':[1704067200000+i*2000 for i in range(5)],'lat':[-20.]*5,'lon':[300.]*5,'mep_omni_flux_p1':[-999.,4.,0.,36016.,-2.],'mep_omni_flux_flag_fit':[-1,-1,0,1,0]}.items()})
        d=extract_channels_dataframe(ds,'poes_n19_20240101_proc.nc')
        np.testing.assert_allclose(d.mep_omni_flux_p1,[np.nan,np.nan,0,36016,np.nan],equal_nan=True)
    def test_file_fill_scale_and_separate_dimensions_decode_positionally(self):
        import netCDF4
        from saa.load_poes import open_poes_netcdf
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'poes_n19_20240101_proc.nc'
            with netCDF4.Dataset(p,'w') as ds:
                for name,typ,values in [('time','u8',[1704067200000,1704067202000]),('lat','f4',[-20,-19]),('lon','f4',[300,301]),('mep_omni_flux_p1','i2',[4,-999]),('mep_IFC_on','i2',[0,-99])]:
                    ds.createDimension(name,2)
                    kw={'fill_value':-999} if name=='mep_omni_flux_p1' else ({'fill_value':-99} if name=='mep_IFC_on' else {})
                    v=ds.createVariable(name,typ,(name,),**kw)
                    if name=='mep_omni_flux_p1':v.scale_factor=.5;v.add_offset=1.
                    v.set_auto_maskandscale(False);v[:]=values
            with open_poes_netcdf(str(p)) as ds:d=extract_channels_dataframe(ds,str(p))
            self.assertEqual(len(d),2);np.testing.assert_allclose(d.mep_omni_flux_p1,[3.,np.nan],equal_nan=True)
            self.assertTrue(pd.isna(d.mep_IFC_on.iloc[1]))
    def test_export_rejects_other_stale_display_metrics(self):
        for column in ['peak_flux','selected_area_fraction_of_covered_region','selected_area_km2']:
            with self.subTest(column=column), tempfile.TemporaryDirectory() as temp:
                p=Path(temp)
                for f in (ROOT/'outputs/tables').glob('*.parquet'):shutil.copy2(f,p/f.name)
                f=p/'cp4b_threshold_sensitivity.parquet';d=pd.read_parquet(f);d.loc[0,column]+=1;d.to_parquet(f,index=False)
                with self.assertRaises(ValueError):build_viewer_payload(p)
