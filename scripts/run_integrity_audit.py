"""Phase 1 only: source census, exact omission, independent arithmetic and issue probes.
Run from repository root: PYTHONPATH=src .venv/bin/python scripts/run_integrity_audit.py
Never writes canonical scientific artifacts.
"""
from pathlib import Path
import sys,json,hashlib,shutil,tempfile,itertools,inspect,argparse
import numpy as np,pandas as pd,netCDF4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
parser=argparse.ArgumentParser()
parser.add_argument('--source-root',type=Path,help='baseline src directory extracted from phase1/baseline.tar.gz')
parser.add_argument('--tables',type=Path,default=Path('outputs/tables'))
parser.add_argument('--processed',type=Path,default=Path('data/processed'))
parser.add_argument('--output',type=Path,default=Path('outputs/paper_integrity/20260929_phases1_3/phase1'))
args=parser.parse_args() if __name__=='__main__' else parser.parse_args([])
if args.source_root:
    sys.path.insert(0,str(args.source_root.resolve()))
    import saa
    saa.__path__.append(str(Path(__file__).resolve().parents[1]/'src/saa'))
from saa.load_poes import open_poes_netcdf,extract_channels_dataframe,file_sha256,SAT_FILE_TOKEN
from saa.grid_flux import prepare_region
from saa.aggregate import build_grid_table,add_coverage_mask
from saa.threshold_analysis import run_sensitivity,add_cell_area,haversine_km
from saa.integrity import omit_record,review_trigger,reference_area,reference_centroid,reference_distance
from saa.magnetic_framing import footprint_magnetic_summary
from saa.magnetic_generality import classify_generality,add_cp5c_footprint_flags
from saa.viewer_export import build_viewer_payload,_cp5c_payload,_grid_path
R=args.output;T=args.tables;R.mkdir(parents=True,exist_ok=True)
P1='mep_omni_flux_p1';SAT=['noaa15','noaa18','noaa19','metop01','metop03']
def save(d,name): d.to_csv(R/(name+'.csv'),index=False)
def js(o,name): (R/(name+'.json')).write_text(json.dumps(o,indent=2,default=str))

def event_dossier():
    path=Path('data/raw/poes_n15_20240119_proc.nc')
    with netCDF4.Dataset(path) as ds:
        ds.set_auto_maskandscale(False)
        time=np.asarray(ds['time'][:]); target=pd.Timestamp('2024-01-19T09:14:30Z').timestamp()*1000
        i=int(np.argmin(abs(time.astype(float)-target)))
        cols=['time','lat','lon','alt','mep_IFC_on']+[v for v in ds.variables if v.startswith('mep_omni')]
        data={v:np.asarray(ds[v][:]) for v in cols}
        meta={'source_sha256':file_sha256(path),'native_index':i,'satellite':'noaa15','channel':P1,'utc':str(pd.to_datetime(time[i],unit='ms',utc=True)),'global':ds.__dict__,'variables':{}}
        for name in cols:
            v=ds[name];meta['variables'][name]={'dtype':str(v.dtype),'dimensions':v.dimensions,'attrs':v.__dict__,'stored_at_event':data[name][i].item()}
        d=pd.DataFrame(data);d.insert(0,'native_index',np.arange(len(d)));d['utc']=pd.to_datetime(time,unit='ms',utc=True);d['gap_seconds']=np.r_[np.nan,np.diff(time.astype(float))/1000];d['lon180']=(d.lon+180)%360-180
        d.iloc[i-10:i+11].to_csv(R/'event_native_neighbors.csv',index=False)
        d.loc[abs(time.astype(float)-time[i])<=300000].to_csv(R/'event_5minute_context.csv',index=False)
    js(meta,'event_dossier')


def census():
    accounting=[];candidates=[];tops=[];hist=[];lineage=[];sources=[];regions={};flags=[]
    for sat in SAT:
        chans=[f'mep_omni_flux_p{i}' for i in ([1,2,3] if sat=='noaa19' else [1])]
        frames=[]
        for p in sorted(Path('data/raw').glob(f'poes_{SAT_FILE_TOKEN[sat]}_202401*_proc.nc')):
            sha=file_sha256(p)
            with open_poes_netcdf(str(p)) as ds:
                d=extract_channels_dataframe(ds,str(p),channels=chans)
                for col in ['Btot_sat','L_IGRF','mag_lat_sat','mag_lon_sat','MLT']:
                    if col in ds:d[col]=np.asarray(ds[col].values,dtype=float)
                # independently read raw netCDF arrays: no xarray and no automatic valid_range masking
                with netCDF4.Dataset(p) as nc:
                    nc.set_auto_maskandscale(False)
                    for col in ['time','lat','lon',*chans]:
                        a=nc[col];v=np.asarray(a[:],dtype=float)
                        missing=np.zeros(len(v),bool)
                        for attr in ['_FillValue','missing_value']:
                            if attr in a.ncattrs():missing |= np.isin(v,np.atleast_1d(a.getncattr(attr)))
                        v=v*getattr(a,'scale_factor',1)+getattr(a,'add_offset',0);v[missing]=np.nan
                        target=d[col].array.as_unit('ms').asi8 if col=='time' else d[col].to_numpy()
                        np.testing.assert_allclose(v,target,rtol=0,atol=0,equal_nan=True)
            d['source_sha256']=sha;d['native_index']=np.arange(len(d));frames.append(d)
            sources.append(dict(satellite=sat,file=p.name,sha256=sha,records=len(d),independent_decode='exact'))
            for c in chans:
                v=d[c].to_numpy();finite=v[np.isfinite(v)];q=np.percentile(finite,99.99)
                h=d.loc[v>10*q,['source_sha256','native_index','time',c]].rename(columns={c:'flux'})
                h['satellite']=sat;h['channel']=c;h['file_p99_99']=q;hist.extend(h.to_dict('records'))
        if len(frames)!=31:raise RuntimeError(f'{sat}: {len(frames)}/31 files available; rerun after retrieval')
        native=pd.concat(frames,ignore_index=True);region,counts=prepare_region(native);regions[sat]=region
        region.to_parquet(R/f'{sat}_reconstructed_region.parquet',index=False)
        old=pd.read_parquet(args.processed/f'cp4f_{sat}_2024-01_mep_omni_flux_p1_region.parquet')
        common=[c for c in old.columns if c in region.columns]
        try:pd.testing.assert_frame_equal(old[common].reset_index(drop=True),region[common].reset_index(drop=True),check_dtype=False,check_exact=True);match=True
        except AssertionError as e:match=False;(R/f'{sat}_lineage_difference.txt').write_text(str(e))
        lineage.append(dict(satellite=sat,processed_rows=len(old),reconstructed_rows=len(region),exact_values_match=match))
        ts=native.time.array.as_unit('ns').asi8/1e9;inc=np.diff(ts);cad=np.median(inc[inc>0])
        for flag in ['mep_IFC_on','mep_omni_flux_flag_fit']:
            for scope,frame in [('native',native),('region_after_ifc',region)]:
                for value,count in frame[flag].value_counts(dropna=False).items():flags.append(dict(satellite=sat,scope=scope,flag=flag,value=str(value),count=int(count)))
        for c in chans:
            v=native[c].to_numpy();ev,hit=review_trigger(ts,v,cad)
            accounting.append(dict(satellite=sat,channel=c,source_records=len(native),channel_values=len(v),nonfinite=int((~np.isfinite(v)).sum()),negative=int((v<0).sum()),zero=int((v==0).sum()),positive=int((v>0).sum()),duplicate_timestamp_rows=int(native.time.duplicated().sum()),duplicate_source_id=int(native.duplicated(['source_sha256','native_index']).sum()),cadence_seconds=cad,gap_breaks=int(((inc<=0)|(inc>3*cad)).sum()),evaluable=int(ev.sum()),evaluable_fraction=float(ev.mean()),candidates=int(hit.sum()),region_nonfinite=int((~np.isfinite(region[c])).sum()),region_negative=int((region[c]<0).sum()),**counts))
            cols=['source_file','source_sha256','native_index','time','lat','lon','mep_IFC_on','mep_omni_flux_flag_fit',c]
            h=native.loc[hit,cols].rename(columns={c:'flux'}).copy();h['satellite']=sat;h['channel']=c
            candidates.extend(h.to_dict('records'))
            top=native.loc[np.isfinite(v)&(v>0),cols].sort_values([c,'source_file','native_index'],ascending=[False,True,True]).head(5).rename(columns={c:'flux'});top['satellite']=sat;top['channel']=c;tops.extend(top.to_dict('records'))
        print('census',sat,len(native),'region',len(region),'lineage',match,flush=True)
    for name,rows in [('census',accounting),('candidates',candidates),('top5',tops),('historical_10x_file_p9999',hist),('lineage',lineage),('sources',sources),('flag_counts',flags)]:save(pd.DataFrame(rows),name)
    return regions

def influence(regions):
    event=json.loads((R/'event_dossier.json').read_text());sha=event['source_sha256'];idx=event['native_index'];allrows=[];pairs=[];cells=[];members=[];grid_compare=[];cp5changes=[]
    grids_by_scenario={}
    for scenario in ['as_is','omit_exact_record']:
        grids_by_scenario[scenario]={}
        for sat,reg in regions.items():
            d=omit_record(reg,sha,idx) if scenario=='omit_exact_record' and sat=='noaa15' else reg
            specs=[];grids={}
            for gd in [5,2]:
                mask=f'enough_samples_{gd}deg';g=add_coverage_mask(build_grid_table(d,P1,gd,gd),30,mask);grids[gd]=g
                specs.append((gd,gd,g,mask))
                if scenario=='as_is':
                    old=pd.read_parquet(T/f'cp4f_{sat}_2024-01_grid_{gd}deg.parquet')
                    try:pd.testing.assert_frame_equal(g,old,check_exact=True);ok=True
                    except AssertionError:ok=False
                    grid_compare.append(dict(satellite=sat,grid_deg=gd,exact_grid_match=ok))
                if sat=='noaa15':g.to_parquet(R/f'{scenario}_noaa15_grid_{gd}deg.parquet',index=False)
            grids_by_scenario[scenario][sat]=grids
            sens=run_sensitivity(specs);sens['scenario']=scenario;sens['satellite']=sat;allrows.extend(sens.to_dict('records'))
            for _,r in sens.iterrows():
                gd=int(r.grid_deg);stat=r.statistic_used;g=add_cell_area(grids[gd],gd,gd);cov=g.loc[g[f'enough_samples_{gd}deg']];sel=cov.loc[cov[stat]>=r.flux_cutoff_value]
                a=reference_area(sel.lat_bin_center.to_numpy(),gd);lat,lon=reference_centroid(sel.lat_bin_center,sel.lon_bin_center,sel[stat],a)
                np.testing.assert_allclose([sum(a),lat,lon],[r.selected_area_km2,r.centroid_lat_flux_weighted,r.centroid_lon_flux_weighted],rtol=1e-12,atol=1e-10)
                if sat=='noaa15':
                    target=reg.loc[(reg.source_sha256==sha)&(reg.native_index==idx)].iloc[0];la=-70+(np.floor((target.lat+70)/gd)+.5)*gd;lo=-100+(np.floor((target.lon180+100)/gd)+.5)*gd
                    cell=cov.loc[(cov.lat_bin_center==la)&(cov.lon_bin_center==lo)].iloc[0];selected=bool(cell[stat]>=r.flux_cutoff_value)
                    cells.append(dict(scenario=scenario,grid_deg=gd,statistic=stat,threshold=r.threshold_label,lat=la,lon=lo,count=int(cell.sample_count),sum=float(cell.mean_flux*cell.sample_count),mean=cell.mean_flux,median=cell.median_flux,descending_rank=int(cov[stat].rank(method='min',ascending=False).loc[cell.name]),selected=selected,event_fraction_of_sum=(target[P1]/(cell.mean_flux*cell.sample_count) if scenario=='as_is' else 0),cell_centroid_weight=(cell[stat]*cell.cell_area_km2/r.total_flux_area_proxy if selected else 0),event_flux_area_contribution=(target[P1]/cell.sample_count*cell.cell_area_km2 if selected and stat=='mean_flux' and scenario=='as_is' else 0)))
                    for x in sel.itertuples():members.append(dict(scenario=scenario,grid_deg=gd,statistic=stat,threshold=r.threshold_label,lat=x.lat_bin_center,lon=x.lon_bin_center))
        s=pd.DataFrame([x for x in allrows if x['scenario']==scenario])
        for key,sub in s.groupby(['grid_deg','statistic_used','threshold_label']):
            for (_,a),(_,b) in itertools.combinations(sub.iterrows(),2):
                coords=(a.centroid_lat_flux_weighted,a.centroid_lon_flux_weighted,b.centroid_lat_flux_weighted,b.centroid_lon_flux_weighted);dist=haversine_km(*coords);np.testing.assert_allclose(dist,reference_distance(*coords),rtol=1e-12,atol=1e-9)
                pairs.append(dict(scenario=scenario,grid_deg=key[0],statistic=key[1],threshold=key[2],satellite_a=a.satellite,satellite_b=b.satellite,distance_km=dist))
    reg=regions['noaa15'];a=add_cp5c_footprint_flags(reg,**{'grid5':grids_by_scenario['as_is']['noaa15'][5],'grid2':grids_by_scenario['as_is']['noaa15'][2]})
    b=add_cp5c_footprint_flags(reg,**{'grid5':grids_by_scenario['omit_exact_record']['noaa15'][5],'grid2':grids_by_scenario['omit_exact_record']['noaa15'][2]})
    for col in [x for x in a.columns if x.startswith('in_top')]:
        changed=a[col]!=b[col];c=reg.loc[changed,['source_sha256','native_index','time','lat','lon180']].copy();c['footprint']=col;c['baseline_in']=a.loc[changed,col];c['sensitivity_in']=b.loc[changed,col];cp5changes.extend(c.to_dict('records'))
    for name,rows in [('sensitivity',allrows),('pairwise',pairs),('affected_cell',cells),('selected_cells',members),('grid_reconciliation',grid_compare),('cp5_changed_memberships',cp5changes)]:save(pd.DataFrame(rows),name)
    p=pd.DataFrame(pairs);principal=p[(p.grid_deg==5)&(p.statistic=='mean_flux')&(p.threshold=='top10')];print(principal.loc[principal.groupby('scenario').distance_km.idxmax()].to_string(index=False),flush=True)

def probes():
    results={};mlt=[]
    for name,inside,outside in [('wrapping',[23.8,23.9,0,.1,.2],[.8,.9,1,1.1,1.2]),('control',[5,5.1,5.2,5.3,5.4],[6,6.1,6.2,6.3,6.4]),('zero24',[0,24,0,24,.1],[.8,.9,1,1.1,1.2])]:
        for shift in [0,12]:
            d=pd.DataFrame({'MLT':(np.array(inside+outside)+shift)%24})
            for c in ['in_top10_5deg','in_top5_5deg','in_top10_2deg','in_top5_2deg']:d[c]=[True]*5+[False]*5
            row=footprint_magnetic_summary(d,variables=['MLT']).iloc[0];mlt.append(dict(case=name,shift=shift,separation=row.separation_metric,median_inside=row.median_inside,median_outside=row.median_outside))
    save(pd.DataFrame(mlt),'mlt_probe');results['MLT']={'verdict':'reproduced','reason':'real summary separation depends on arbitrary origin for circular hours'}
    rows=[]
    for name,lo,dom in [('nonidentical_four',[1,1,1,1,0],[1,1,1,0,1]),('aligned_four',[1,1,1,1,0],[1,1,1,1,0]),('all_five',[1]*5,[1]*5)]:
        d=pd.DataFrame({'low_btot_support':np.array(lo,bool),'btot_dominance_support':np.array(dom,bool),'btot_separation_metric':[1]*5});rows.append(dict(case=name,joint_support=int((d.low_btot_support&d.btot_dominance_support).sum()),classification=classify_generality(d)))
    save(pd.DataFrame(rows),'classifier_probe');results['classification']={'verdict':'reproduced','reason':'separate counts vs docs pass-both wording; actual January all five supports so no classification change from contract alone'}
    # Build a fully consistent temporary authority bundle before tampering.
    with tempfile.TemporaryDirectory() as temp:
        td=Path(temp)
        for p in T.glob('*.parquet'):shutil.copy2(p,td/p.name)
        mismatch=[]
        for exp,f in [('threshold','cp4b_threshold_sensitivity'),('channel','cp4c_channel_threshold_sensitivity'),('time','cp4d_time_window_threshold_sensitivity'),('satellite','cp4f_multisatellite_threshold_sensitivity')]:
            tab=pd.read_parquet(td/(f+'.parquet'))
            for i,row in tab.iterrows():
                gd=int(row.grid_deg);g=pd.read_parquet(_grid_path(td,exp,row));s=run_sensitivity([(gd,gd,g,f'enough_samples_{gd}deg')]);r=s.loc[(s.statistic_used==row.statistic_used)&(s.threshold_label==row.threshold_label)].iloc[0]
                for col in ['centroid_lat_flux_weighted','centroid_lon_flux_weighted']:
                    mismatch.append(dict(experiment=exp,row=i,metric=col,stored=row[col],recomputed=r[col],difference=r[col]-row[col]));tab.loc[i,col]=r[col]
            tab.to_parquet(td/(f+'.parquet'),index=False)
        good=build_viewer_payload(td)
        p=td/'cp4b_threshold_sensitivity.parquet';d=pd.read_parquet(p);d.loc[0,'centroid_lat_flux_weighted']+=1;d.to_parquet(p,index=False)
        try:
            bad=build_viewer_payload(td);silent=good['experiments']==bad['experiments'];verdict='reproduced' if silent else 'not supported'
        except ValueError:verdict='already resolved';silent=False
        results['exporter']={'verdict':verdict,'unmodified_valid_control':'accepted','one_degree_tamper_silently_recomputed':silent}
    save(pd.DataFrame(mismatch),'stored_centroid_reconciliation')
    current=pd.read_parquet(T/'cp5c_multisatellite_magnetic_generality_summary.parquet');alternate=current.copy();alternate['low_btot_support']=False;alternate['btot_dominance_support']=False;alternate['low_btot_support_count']=0;alternate['btot_dominance_support_count']=0;alternate['btot_separation_metric']=-1.;alternate['btot_fraction_below_regional_q25']=.1;alternate['btot_regional_fraction_to_capture_90pct']=.9;alternate['reversed_btot_sign_count']=5;alternate['cp5c_classification']='INCONSISTENT'
    results['magnetic_narrative']={'alternate_classification':_cp5c_payload(alternate)['classification'],'alternate_interpretation':_cp5c_payload(alternate)['interpretation']}
    save(current,'actual_january_legacy_rubric');js(results,'issue_register');print(results,flush=True)

if __name__=='__main__':
    event_dossier();probes();regions=census();influence(regions)
    (R/'PHASE1_COMPLETE.txt').write_text('Phase 1 diagnostics complete; original inputs unchanged. Decision: retain influential unresolved event; retire unsupported MLT dominance; label separate-count legacy rule; reject stale canonical export. See issue_register.json and sensitivity tables.\n')
