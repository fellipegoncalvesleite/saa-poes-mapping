"""Bounded review diagnostics. Candidate detection never changes scientific inputs."""
from __future__ import annotations
import math
import numpy as np


def omit_record(frame, sha256, native_index):
    """Omit exactly one source record, rejecting absent or duplicated identities."""
    match=(frame.source_sha256 == sha256)&(frame.native_index == native_index)
    if int(match.sum()) != 1:
        raise ValueError('omission requires exactly one stable source identity')
    return frame.loc[~match].copy()


def review_trigger(time_seconds, flux, cadence):
    """Frozen 100x two-sided ten-record triage; gaps and invalid neighbors unevaluable."""
    t=np.asarray(time_seconds,dtype=float);v=np.asarray(flux,dtype=float)
    evaluable=np.zeros(len(v),bool);candidate=evaluable.copy()
    if len(v)<21:return evaluable,candidate
    breaks=np.r_[0,np.cumsum((np.diff(t)<=0)|(np.diff(t)>3*cadence)|~np.isfinite(np.diff(t)))]
    win=np.lib.stride_tricks.sliding_window_view(v,21)
    left=win[:,:10];right=win[:,11:]
    ok=(breaks[:-20]==breaks[20:])&np.all(np.isfinite(left)&(left>0),axis=1)&np.all(np.isfinite(right)&(right>0),axis=1)&np.isfinite(win[:,10])&(win[:,10]>0)
    evaluable[10:-10]=ok
    candidate[10:-10]=ok&(win[:,10]>100*np.median(left,axis=1))&(win[:,10]>100*np.median(right,axis=1))
    return evaluable,candidate


def reference_area(lat,step):
    """Independent spherical-zone integral via cos(midpoint)*sin(half-width)."""
    return 2*6371.**2*math.radians(step)*np.cos(np.deg2rad(lat))*math.sin(math.radians(step)/2)


def reference_centroid(lat,lon,flux,area):
    w=np.asarray(flux)*np.asarray(area);total=math.fsum(w)
    return math.fsum(np.asarray(lat)*w)/total, math.fsum(np.asarray(lon)*w)/total


def reference_distance(lat1,lon1,lat2,lon2):
    """atan2 of vector cross norm and dot, independent of production haversine."""
    def xyz(lat,lon):
        p,l=map(math.radians,(lat,lon));return np.array([math.cos(p)*math.cos(l),math.cos(p)*math.sin(l),math.sin(p)])
    a,b=xyz(lat1,lon1),xyz(lat2,lon2)
    return 6371*math.atan2(np.linalg.norm(np.cross(a,b)),np.dot(a,b))
