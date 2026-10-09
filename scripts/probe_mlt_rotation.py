from pathlib import Path
import sys,json
import pandas as pd,numpy as np
sys.path.insert(0,'src')
from saa.magnetic_generality import add_cp5c_footprint_flags,evaluate_satellite_support
from saa.magnetic_framing import footprint_magnetic_summary
R=Path('outputs/paper_integrity/20260929_phases1_3/phase1');T=Path('outputs/tables');rows=[]
for sat in ['noaa15','noaa18','noaa19','metop01','metop03']:
 d=pd.read_parquet(R/f'{sat}_reconstructed_region.parquet');d=add_cp5c_footprint_flags(d,pd.read_parquet(T/f'cp4f_{sat}_2024-01_grid_5deg.parquet'),pd.read_parquet(T/f'cp4f_{sat}_2024-01_grid_2deg.parquet'))
 original=pd.read_parquet(T/'cp5c_multisatellite_magnetic_generality_summary.parquet').set_index('satellite').loc[sat].to_dict()
 for shift in [0,12]:
  f=d.copy();f['MLT']=(f.MLT+shift)%24;s=footprint_magnetic_summary(f,variables=['MLT']).iloc[0];r=original.copy();r['mlt_separation_metric']=s.separation_metric;lo,dom=evaluate_satellite_support(r)
  rows.append(dict(satellite=sat,shift=shift,mlt_separation=s.separation_metric,btot_separation=r['btot_separation_metric'],low_btot_support=lo,legacy_dominance=dom))
pd.DataFrame(rows).to_csv(R/'actual_mlt_rotation.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
