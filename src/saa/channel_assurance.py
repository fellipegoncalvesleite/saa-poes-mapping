"""January NOAA-19 assurance: paired calendar blocks and common-support morphology.

Outputs describe conditional resampling stability, not physical-position confidence.
No map configuration is added to the explorer.
"""
from __future__ import annotations
import numpy as np
from .threshold_analysis import cell_area_km2


def draw_days(length,replicates,seed):
    """All fitting calendar starts; replacement, no wrapping, retain 31 day slots."""
    if length not in (1,3,7):raise ValueError('protocol block length must be 1, 3 or 7')
    rng=np.random.Generator(np.random.PCG64(seed))
    starts=rng.integers(0,32-length,size=(replicates,int(np.ceil(31/length))))
    days=(starts[:,:,None]+np.arange(length)).reshape(replicates,-1)[:,:31]
    return days,starts


def daily_cells(frame,channels):
    """Channel-specific finite sums/counts per UTC day/cell; no daily-mean averaging."""
    if str(frame.time.dt.tz) != 'UTC':raise ValueError('UTC timestamps required')
    if not ((frame.time.dt.year==2024)&(frame.time.dt.month==1)).all():raise ValueError('January 2024 only')
    day=frame.time.dt.day.to_numpy()-1
    li=np.floor((frame.lat.to_numpy()+70)/5).astype(int);lj=np.floor((frame.lon180.to_numpy()+100)/5).astype(int)
    inside=(li>=0)&(li<18)&(lj>=0)&(lj<24);key=day*432+li*24+lj
    sums=np.zeros((31,len(channels),432));counts=np.zeros_like(sums,dtype=np.int64)
    for c,col in enumerate(channels):
        v=frame[col].to_numpy(float)
        if np.any(v[np.isfinite(v)]<0):raise ValueError('negative flux must be resolved upstream')
        valid=inside&np.isfinite(v)
        sums[:,c,:]=np.bincount(key[valid],weights=v[valid],minlength=31*432).reshape(31,432)
        counts[:,c,:]=np.bincount(key[valid],minlength=31*432).reshape(31,432)
    return sums,counts


def combine_days(sums,counts,days):
    # Advanced indexing deliberately repeats source days and includes missing-day zeros in counts.
    return sums[days].sum(axis=0),counts[days].sum(axis=0)


def geometry(step=5):
    lat,lon=np.meshgrid(np.arange(-70+step/2,20,step),np.arange(-100+step/2,20,step),indexing='ij')
    return lat.ravel(),lon.ravel(),cell_area_km2(lat.ravel(),step,step)


def replicate_metrics(sums,counts):
    lat,lon,area=geometry();rows=[]
    for s,n in zip(sums,counts):
        f=np.divide(s,n,out=np.full_like(s,np.nan,dtype=float),where=n>0);eligible=(n>=30)&np.isfinite(f)
        row=dict(eligible_cells=int(eligible.sum()),valid_samples=int(n.sum()),selected_cells=0,cutoff=np.nan,lat=np.nan,lon=np.nan,area_km2=np.nan,status='empty_support')
        if eligible.any():
            cut=float(np.percentile(f[eligible],90,method='linear'));sel=eligible&(f>=cut);w=f[sel]*area[sel]
            row.update(cutoff=cut,selected_cells=int(sel.sum()),area_km2=float(area[sel].sum()))
            if np.any(f[eligible]<0):row['status']='negative_flux'
            elif not np.isfinite(w.sum()) or w.sum()<=0:row['status']='zero_mass'
            else:row.update(lat=float(np.dot(lat[sel],w)/w.sum()),lon=float(np.dot(lon[sel],w)/w.sum()),status='ok')
        rows.append(row)
    return rows


def common_support(fields,masks):
    fields=np.asarray(fields);return np.all(np.asarray(masks,dtype=bool)&np.isfinite(fields),axis=0)


def normalized_fields(fields,lat,lon,area):
    """p=F*A/sum(F*A). Coordinate averages over common support, not probability/dose."""
    f=np.asarray(fields,dtype=float);a=np.asarray(area,dtype=float)
    if f.ndim!=2 or f.shape[1]==0:raise ValueError('empty support')
    if not np.isfinite(f).all() or (f<0).any():raise ValueError('flux must be finite nonnegative on common support')
    if not np.isfinite(a).all() or (a<=0).any():raise ValueError('areas must be finite positive')
    mass=f*a;tot=mass.sum(axis=1)
    if not np.isfinite(tot).all() or (tot<=0).any():raise ValueError('zero or invalid normalization total')
    p=mass/tot[:,None]
    return p,np.column_stack([p@np.asarray(lat),p@np.asarray(lon)])


def validate_protocol(protocol):
    """Reject edited labels that the deliberately bounded implementation cannot run."""
    fixed={'satellite':'noaa19','month':'2024-01',
           'channels':[f'mep_omni_flux_p{i}' for i in (1,2,3)],
           'grid_deg':5,'statistic':'mean_flux','percentile':90,
           'percentile_method':'linear','coverage_min_samples':30,
           'block_lengths':[1,3,7],'replicates_per_length':1000,
           'calendar_days':31,'trim_to_slots':31,'paired_channels':True,
           'replacement':True,'wrap':False,
           'generator':'numpy.PCG64; reset same seed per block length'}
    for key,value in fixed.items():
        if protocol.get(key)!=value:raise ValueError(f'unsupported frozen protocol {key}: {protocol.get(key)!r}')
    if type(protocol.get('seed')) is not int or protocol['seed']<0:raise ValueError('seed must be a recorded nonnegative integer')
    morphology=protocol.get('morphology',{})
    for key,value in {'grids':[5,2],'statistics':['mean_flux','median_flux'],'percentile_on_common_support':90}.items():
        if morphology.get(key)!=value:raise ValueError(f'unsupported morphology {key}')
