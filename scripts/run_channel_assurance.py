"""Run frozen Phase 3 protocol against reconciled real January NOAA-19 data."""
from pathlib import Path
import sys,json,itertools,hashlib
import numpy as np,pandas as pd
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from saa.channel_assurance import draw_days,daily_cells,combine_days,replicate_metrics,common_support,normalized_fields,validate_protocol
from saa.aggregate import build_grid_table
from saa.threshold_analysis import cell_area_km2,haversine_km
from saa.integrity import reference_area,reference_centroid,reference_distance
import argparse,shutil
_ap=argparse.ArgumentParser();_ap.add_argument('--output',type=Path,default=Path('outputs/paper_integrity/20260929_phases1_3/phase3'))
_ap.add_argument('--protocol',type=Path,help='frozen protocol to replay (default: OUTPUT/protocol.json)')
_args=_ap.parse_args() if __name__=='__main__' else _ap.parse_args([])
R=_args.output;T=Path('outputs/tables');R.mkdir(parents=True,exist_ok=True)
# Replay copies the frozen protocol byte-for-byte; it is never rewritten here.
if _args.protocol and _args.protocol.resolve()!=(R/'protocol.json').resolve():shutil.copyfile(_args.protocol,R/'protocol.json')
config=json.loads((R/'protocol.json').read_text());validate_protocol(config);channels=config['channels']
def save(d,name):d.to_csv(R/(name+'.csv'),index=False)
def pairs(rows,**meta):
 out=[]
 for a,b in itertools.combinations(range(3),2):
  ra,rb=rows[a],rows[b];ok=ra['status']=='ok' and rb['status']=='ok'
  out.append(dict(**meta,channel_a=channels[a],channel_b=channels[b],status='ok' if ok else 'undefined',delta_lat=rb['lat']-ra['lat'] if ok else np.nan,delta_lon=rb['lon']-ra['lon'] if ok else np.nan,distance_km=haversine_km(ra['lat'],ra['lon'],rb['lat'],rb['lon']) if ok else np.nan))
 return out

def blocks():
 path=Path('data/processed/noaa19_2024-01_mep_omni_flux_p1_p2_p3_region.parquet');df=pd.read_parquet(path);sums,counts=daily_cells(df,channels)
 rows=[];pairrows=[];equivalence=[];draws={};daily=[]
 baseline=replicate_metrics(sums.sum(axis=0),counts.sum(axis=0));save(pd.DataFrame([dict(channel=c,**r) for c,r in zip(channels,baseline)]),'monthly_baseline');save(pd.DataFrame(pairs(baseline)),'monthly_pairs')
 # Exact repeated-record reference vs accelerated sufficient statistics, including a missing calendar slot.
 for days in [np.array([0,0,1,3,3,30]),np.arange(31),draw_days(7,1,config['seed'])[0][0]]:
  repeated=pd.concat([df.loc[df.time.dt.day==day+1] for day in days],ignore_index=True);s,n=combine_days(sums,counts,days)
  for ci,c in enumerate(channels):
   g=build_grid_table(repeated,c,5,5);key=(np.floor((g.lat_bin_center+70)/5).astype(int)*24+np.floor((g.lon_bin_center+100)/5).astype(int)).to_numpy();np.testing.assert_array_equal(n[ci,key],g.sample_count);np.testing.assert_allclose(s[ci,key]/n[ci,key],g.mean_flux,rtol=1e-12,atol=1e-12)
   # Actual percentile/membership equivalence, not only the cell means.
   eligible=g.sample_count>=30;cut=np.percentile(g.loc[eligible,'mean_flux'],90);sel=g.loc[eligible&(g.mean_flux>=cut)];a=reference_area(sel.lat_bin_center,5);lat,lon=reference_centroid(sel.lat_bin_center,sel.lon_bin_center,sel.mean_flux,a)
   metric=replicate_metrics(s,n)[ci];np.testing.assert_allclose([lat,lon,cut],[metric['lat'],metric['lon'],metric['cutoff']],rtol=1e-12,atol=1e-12)
   equivalence.append(dict(draw_days=','.join(str(x+1) for x in days),channel=c,records=len(repeated),cell_mean_max_abs_error=float(np.max(abs(s[ci,key]/n[ci,key]-g.mean_flux))),selected_cells=len(sel),status='pass'))
 save(pd.DataFrame(equivalence),'repeated_record_equivalence')
 for day in range(31):
  metrics=replicate_metrics(sums[day],counts[day])
  for i,c in enumerate(channels):daily.append(dict(day=day+1,channel=c,source_records=int(counts[day,i].sum()),regional_mean=float(sums[day,i].sum()/counts[day,i].sum()),**metrics[i]))
 save(pd.DataFrame(daily),'daily_diagnostics')
 for length in config['block_lengths']:
  days,starts=draw_days(length,config['replicates_per_length'],config['seed']);draws[str(length)]={'starts_zero_based':starts.tolist(),'day_slots_zero_based':days.tolist()}
  for rep,day in enumerate(days):
   s,n=combine_days(sums,counts,day);metrics=replicate_metrics(s,n)
   for ci,c in enumerate(channels):
    present=np.flatnonzero(counts[:,ci,:].sum(axis=1)>0);unique=np.intersect1d(day,present)
    rows.append(dict(block_length=length,replicate=rep,channel=c,unique_source_days=len(unique),unique_calendar_days=len(set(day)),observed_day_slots=int(np.isin(day,present).sum()),**metrics[ci]))
   pairrows.extend(pairs(metrics,block_length=length,replicate=rep))
  print('completed block length',length,flush=True)
 (R/'block_draws.json').write_text(json.dumps(draws,separators=(',',':'))+'\n')
 save(pd.DataFrame(rows),'replicates');p=pd.DataFrame(pairrows);save(p,'paired_replicates')
 summary=[]
 for key,g in p.groupby(['block_length','channel_a','channel_b']):
  ok=g[g.status=='ok']
  for metric in ['delta_lat','delta_lon','distance_km']:
   q=ok[metric].quantile(config['quantiles']);summary.append(dict(block_length=key[0],channel_a=key[1],channel_b=key[2],metric=metric,attempted=len(g),defined=len(ok),failed=len(g)-len(ok),q025=q.iloc[0],q50=q.iloc[1],q975=q.iloc[2]))
 summary=pd.DataFrame(summary);save(summary,'paired_quantiles')
 d=pd.DataFrame(daily);depend=[]
 for c,g in d.groupby('channel'):
  for variable in ['regional_mean','lat','lon']:
   for lag in [1,3,7]:depend.append(dict(channel=c,variable=variable,lag_days=lag,lag_correlation=g[variable].autocorr(lag),first_half_mean=g.loc[g.day<=15,variable].mean(),second_half_mean=g.loc[g.day>15,variable].mean(),note='descriptive diagnostic only, neither stationarity proof nor valid effective sample size'))
 save(pd.DataFrame(depend),'dependence_diagnostics')
 fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
 for ax,metric in zip(axes,['delta_lat','delta_lon']):
  for pair,g in summary[summary.metric==metric].groupby(['channel_a','channel_b']):
   x=g.block_length.to_numpy();y=g.q50.to_numpy();ax.errorbar(x,y,yerr=[y-g.q025,g.q975-y],marker='o',capsize=4,label=pair[1][-2:]+' − '+pair[0][-2:])
  ax.axhline(0,color='gray',lw=.7);ax.set(xlabel='block length (calendar days)',ylabel=metric+' (degrees)');ax.legend(fontsize=8)
 fig.suptitle('Conditional resampling stability • marginal 2.5–97.5% quantiles\nNot a calibrated physical-position confidence region',fontsize=11);fig.savefig(R/'block_stability.png',dpi=160);plt.close(fig)
 return path

def morphology():
 rows=[];pairrows=[];support=[];weights=[]
 for gd in [5,2]:
  grids=[pd.read_parquet(T/f'cp4c_noaa19_2024-01_{c[-2:]}_grid_{gd}deg.parquet').set_index(['lat_bin_center','lon_bin_center']) for c in channels]
  keys=grids[0].index
  for g in grids[1:]:keys=keys.union(g.index)
  keys=keys.sort_values();lat=keys.get_level_values(0).to_numpy();lon=keys.get_level_values(1).to_numpy();a=cell_area_km2(lat,gd,gd);np.testing.assert_allclose(a,reference_area(lat,gd),rtol=1e-12)
  masks=np.array([g.reindex(keys)[f'enough_samples_{gd}deg'].fillna(False).to_numpy(bool) for g in grids])
  for stat in ['mean_flux','median_flux']:
   fields=np.array([g.reindex(keys)[stat].to_numpy(float) for g in grids]);common=common_support(fields,masks)
   for ci,c in enumerate(channels):
    orig=masks[ci]&np.isfinite(fields[ci]);support.append(dict(grid_deg=gd,statistic=stat,channel=c,original_cells=int(orig.sum()),common_cells=int(common.sum()),excluded_cells=int(orig.sum()-common.sum()),original_area_km2=float(a[orig].sum()),common_area_km2=float(a[common].sum()),excluded_area_km2=float(a[orig&~common].sum())))
   p,centroids=normalized_fields(fields[:,common],lat[common],lon[common],a[common])
   selections={};cent={}
   for ci,c in enumerate(channels):
    for k,cell in enumerate(np.flatnonzero(common)):weights.append(dict(grid_deg=gd,statistic=stat,channel=c,lat=lat[cell],lon=lon[cell],area_km2=a[cell],flux=fields[ci,cell],normalized_flux_area=p[ci,k]))
    for mode in ['original_percentile','common_percentile','common_continuous']:
     eligible=(masks[ci]&np.isfinite(fields[ci])) if mode=='original_percentile' else common
     sel=eligible.copy();cut=np.nan
     if mode!='common_continuous':cut=np.percentile(fields[ci,eligible],90,method='linear');sel &= fields[ci]>=cut
     _,cen=normalized_fields(fields[ci:ci+1,sel],lat[sel],lon[sel],a[sel]);x,y=cen[0];ref=reference_centroid(lat[sel],lon[sel],fields[ci,sel],reference_area(lat[sel],gd));np.testing.assert_allclose([x,y],ref,rtol=1e-12,atol=1e-12)
     selections[(ci,mode)]=sel;cent[(ci,mode)]=(x,y)
     rows.append(dict(grid_deg=gd,statistic=stat,channel=c,mode=mode,eligible_cells=int(eligible.sum()),selected_cells=int(sel.sum()),selected_area_km2=float(a[sel].sum()),cutoff=cut,lat=x,lon=y,status='ok'))
   for i,j in itertools.combinations(range(3),2):
    for mode in ['original_percentile','common_percentile','common_continuous']:
     si,sj=selections[(i,mode)],selections[(j,mode)];xy=(*cent[(i,mode)],*cent[(j,mode)]);dist=haversine_km(*xy);np.testing.assert_allclose(dist,reference_distance(*xy),atol=1e-9,rtol=1e-12)
     pairrows.append(dict(grid_deg=gd,statistic=stat,channel_a=channels[i],channel_b=channels[j],mode=mode,delta_lat=xy[2]-xy[0],delta_lon=xy[3]-xy[1],distance_km=dist,continuous_overlap=float(np.minimum(p[i],p[j]).sum()) if mode=='common_continuous' else np.nan,area_jaccard=float(a[si&sj].sum()/a[si|sj].sum())))
 for name,data in [('morphology_centroids',rows),('morphology_pairs',pairrows),('common_support',support),('normalized_fields',weights)]:save(pd.DataFrame(data),name)
 fig,axes=plt.subplots(2,2,figsize=(10,8),layout='constrained')
 d=pd.DataFrame(rows)
 for ax,(gd,stat) in zip(axes.ravel(),itertools.product([5,2],['mean_flux','median_flux'])):
  for mode,marker in [('original_percentile','o'),('common_percentile','x'),('common_continuous','s')]:
   sub=d[(d.grid_deg==gd)&(d.statistic==stat)&(d['mode']==mode)];ax.scatter(sub.lon,sub.lat,marker=marker,label=mode.replace('_',' '))
   for r in sub.itertuples():ax.annotate(r.channel[-2:],(r.lon,r.lat),fontsize=8)
  ax.set(title=f'{gd}° {stat}',xlabel='longitude',ylabel='latitude');ax.legend(fontsize=7)
 fig.suptitle('Channel morphology: footprint and whole-region field summaries');fig.savefig(R/'morphology.png',dpi=160);plt.close(fig)

if __name__=='__main__':
 path=blocks();morphology();inputs=[path,*T.glob('cp4c*parquet'),R/'protocol.json']
 (R/'input_hashes.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},indent=2))
 print('Phase 3 real-data execution complete',flush=True)
