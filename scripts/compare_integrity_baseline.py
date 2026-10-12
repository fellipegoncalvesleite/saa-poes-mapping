from pathlib import Path
import tarfile,io,json,sys,shutil
import numpy as np,pandas as pd
sys.path[:0]=['src','scripts']
import run_integrity_audit as audit
r=Path('outputs/paper_integrity/20260929_phases1_3');rows=[]
with tarfile.open(r/'phase1/baseline.tar.gz') as archive:
 for f in ['cp4b_threshold_sensitivity','cp4c_channel_threshold_sensitivity','cp4d_time_window_threshold_sensitivity','cp4e_satellite_pilot_threshold_sensitivity','cp4f_multisatellite_threshold_sensitivity','cp5c_multisatellite_magnetic_generality_summary']:
  old=pd.read_parquet(io.BytesIO(archive.extractfile('outputs/tables/'+f+'.parquet').read()));new=pd.read_parquet('outputs/tables/'+f+'.parquet')
  keys=[c for c in ['satellite','channel','window_label','grid_deg','statistic_used','threshold_label'] if c in old and c in new];a=old.set_index(keys).sort_index();b=new.set_index(keys).sort_index();assert a.index.equals(b.index)
  for col in a.select_dtypes(include='number').columns.intersection(b.columns):
   delta=b[col]-a[col]
   for key,val in delta.items():
    if abs(val)>1e-12:rows.append(dict(artifact=f,key=str(key),metric=col,before=float(a.loc[key,col]),after=float(b.loc[key,col]),delta=float(val)))
pd.DataFrame(rows).to_csv(r/'phase2/baseline_to_current.csv',index=False)
sub=r/'phase2/quality_sensitivity';sub.mkdir(exist_ok=True);shutil.copy2(r/'phase1/event_dossier.json',sub/'event_dossier.json');audit.R=sub
regions={}
for sat in audit.SAT:
 d=pd.read_parquet(r/f'phase1/{sat}_reconstructed_region.parquet')
 for c in [x for x in d if x.startswith('mep_omni_flux_p')]:d.loc[(d[c]<0)|(d.mep_omni_flux_flag_fit==-1),c]=np.nan
 regions[sat]=d
# Rerun exact-identity sensitivity after population quality correction, independently of primary export.
audit.influence(regions)
