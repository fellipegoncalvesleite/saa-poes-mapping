"""Phase 4A: claims-to-evidence register and manuscript value file.

Run from repository root: PYTHONPATH=src python scripts/build_claims_register.py
Every numerical value quoted in the manuscript/supplement is computed here from canonical outputs
and written to paper/generated/{claims_register.json,claims_register.csv,values.typ}. The paper
imports values.typ; it never hand-copies numbers. Inputs are hashed so a register row names the exact
bytes it came from.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import itertools
import json
import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from saa.threshold_analysis import haversine_km  # noqa: E402

T = Path("outputs/tables")
OM = Path("outputs/omission_sensitivity")
QS = Path("outputs/qc_sensitivity")
ROOT_SRC = Path("src")
CA = Path("outputs/channel_assurance")
OUT = Path("paper/generated")
PRINCIPAL = "NOAA-19 p1, January 2024, 5° grid, cell mean, top 10% (90th percentile), coverage ≥30 samples"

_hash_cache: dict[str, str] = {}


def sha(path: Path) -> str:
    key = str(path)
    if key not in _hash_cache:
        _hash_cache[key] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return _hash_cache[key]


CLAIMS: list[dict] = []


def fmt(value, spec: str) -> str:
    if isinstance(value, str):
        return value
    if spec == "":
        return str(value)
    if spec == "int":
        return f"{int(round(value)):,}".replace(",", " ")
    if spec.startswith("pct"):
        return f"{value * 100:.{int(spec[3:] or 1)}f}"
    if spec.startswith("sig"):
        return f"{value:+.{int(spec[3:])}f}".replace("-", "−")
    return f"{value:.{int(spec)}f}".replace("-", "−")


def claim(key, value, *, unit, spec, status, statement, inputs, formula, config, dest, caveat="",
          denominator=""):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{key}: non-finite value")
    CLAIMS.append({
        "key": key, "status": status, "statement": statement,
        "value": value if not isinstance(value, (np.floating, np.integer)) else value.item(),
        "formatted": fmt(value, spec), "unit": unit, "rounding": spec, "configuration": config,
        "inputs": [{"path": str(p), "sha256": sha(p)} for p in inputs], "formula": formula,
        "denominator": denominator, "destination": dest, "caveat": caveat,
    })


def dist(a, b):
    return haversine_km(a[0], a[1], b[0], b[1])


def _time_claims(ts, grid, pre, ps):
    tsp = ts[(ts.grid_deg == grid) & (ts.statistic_used == "mean_flux") & (ts.threshold_label == "top10")].set_index("window_label")

    names = {"day_2024-01-01": "d1", "days_2024-01-01_to_03": "d3", "days_2024-01-01_to_07": "d7",
             "days_2024-01-01_to_14": "d14", "week2": "w2", "week3": "w3", "week4": "w4"}
    for lab, k in names.items():
        rr = tsp.loc[lab]
        for col, key, unit, spec, st in (
            ("window_coverage_passed_area_fraction", "covA", "fraction", "pct1", "coverage-passed area fraction"),
            ("window_coverage_passed_cells", "covN", "cells", "int", "coverage-passed cells"),
            ("area_jaccard_original", "Je", "ratio", "3", "end-to-end area Jaccard vs month"),
            ("centroid_distance_km_original", "De", "km", "0", "end-to-end centroid distance to month"),
            ("selected_area_ratio_original", "Re", "ratio", "2", "end-to-end selected-area ratio"),
            ("monthly_footprint_observability", "Obs", "fraction", "pct1", "monthly-footprint observability"),
            ("common_support_cells", "Sn", "cells", "int", "common-support cells"),
            ("area_jaccard_common", "Jc", "ratio", "3", "shared-support area Jaccard"),
            ("centroid_distance_km_common", "Dc", "km", "0", "shared-support centroid distance"),
            ("window_distinct_days_median_coverage_passed", "days", "days", "0",
             "median distinct valid UTC days per coverage-passed cell"),
        ):
            claim(f"{pre}_{k}_{key}", float(rr[col]) if spec != "int" else int(rr[col]), unit=unit, spec=spec,
                  status="primary", statement=f"{lab}: {st}", inputs=[ps], formula=col,
                  config=f"NOAA-19 p1 {grid}° mean top10, {lab} vs month_2024-01",
                  denominator="nominal regional area" if "fraction" in col else "",
                  dest="Results 3.4; Fig. 4; Supplement S6",
                  caveat="month contains the window; descriptive agreement, not independent validation")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- data accounting
    p5 = T / "cp5c_multisatellite_magnetic_generality_summary.parquet"
    q = pd.read_parquet(p5).set_index("satellite")
    for sat in q.index:
        claim(f"rows_{sat}", int(q.loc[sat, "regional_rows_after_quality"]), unit="records", spec="int",
              status="primary", statement=f"{sat} regional records after IFC, channel-validity and QC-1 handling",
              inputs=[p5], formula="regional_rows_after_ifc - invalid_channel_dropped - qc_excluded_dropped",
              config="January 2024 region lat −70..20, lon −100..20", dest="Supplement Table S2")
        claim(f"invalid_p1_{sat}", int(q.loc[sat, "invalid_channel_dropped"]), unit="records", spec="int",
              status="primary", statement=f"{sat} regional p1 values set missing (negative or fit=−1)",
              inputs=[p5], formula="count(p1<0 or fit==-1) in region after IFC", config="integrity v2",
              dest="Methods; Supplement Table S2")
        claim(f"qc_excluded_{sat}", int(q.loc[sat, "qc_excluded_dropped"]), unit="records", spec="int",
              status="primary", statement=f"{sat} regional p1 values excluded by QC-1", inputs=[p5],
              formula="count(QC-1 flag) in region after IFC", config="QC-1 v1.0",
              dest="Methods; Supplement Table S2")
        claim(f"ifc_on_{sat}", int(q.loc[sat, "ifc_on_dropped"]), unit="records", spec="int",
              status="primary", statement=f"{sat} regional records dropped with mep_IFC_on==1",
              inputs=[p5], formula="count(mep_IFC_on==1)", config="region", dest="Supplement Table S2")
        claim(f"ifc_minus1_{sat}", int(q.loc[sat, "ifc_minus1_retained"]), unit="records", spec="int",
              status="primary", statement=f"{sat} regional records retained with undocumented mep_IFC_on==−1",
              inputs=[p5], formula="count(mep_IFC_on==-1)", config="region", dest="Supplement Table S2",
              caveat="−1 semantics undocumented; retained and uninterpreted")
    claim("invalid_p1_total", int(q.invalid_channel_dropped.sum()), unit="records", spec="int", status="primary",
          statement="regional p1 values set missing across five satellites", inputs=[p5],
          formula="sum over satellites", config="integrity v2", dest="Methods")

    # ---------------------------------------------------------------- threshold family
    pb = T / "cp4b_threshold_sensitivity.parquet"
    b = pd.read_parquet(pb)
    bi = b.set_index(["grid_deg", "statistic_used", "threshold_label"])
    r = bi.loc[(5, "mean_flux", "top10")]
    claim("p_lat", r.centroid_lat_flux_weighted, unit="deg", spec="2", status="primary",
          statement="principal centroid latitude", inputs=[pb], formula="Σ lat·F·A / Σ F·A over selected cells",
          config=PRINCIPAL, dest="Results 3.1; Fig. 1; Table 1")
    claim("p_lon", r.centroid_lon_flux_weighted, unit="deg", spec="2", status="primary",
          statement="principal centroid longitude", inputs=[pb], formula="Σ lon·F·A / Σ F·A", config=PRINCIPAL,
          dest="Results 3.1; Fig. 1")
    claim("p_cells", int(r.selected_cell_count), unit="cells", spec="int", status="primary",
          statement="principal selected cells", inputs=[pb], formula="count(F ≥ q90 over eligible cells)",
          config=PRINCIPAL, denominator="432 eligible cells", dest="Results 3.1")
    claim("p_area", r.selected_area_km2 / 1e6, unit="10^6 km²", spec="2", status="primary",
          statement="principal selected area", inputs=[pb], formula="Σ spherical cell area of selected cells",
          config=PRINCIPAL, dest="Results 3.1")
    claim("p_cut", r.flux_cutoff_value, unit="#/(cm² s sr MeV)", spec="2", status="primary",
          statement="principal 90th-percentile cutoff", inputs=[pb], formula="numpy linear percentile over 432 cells",
          config=PRINCIPAL, dest="Results 3.1")
    claim("p_peak", r.peak_flux, unit="#/(cm² s sr MeV)", spec="2", status="primary",
          statement="principal peak cell mean flux", inputs=[pb], formula="max over eligible cells",
          config=PRINCIPAL, dest="Results 3.1")
    claim("p_peak_lat", r.peak_flux_lat, unit="deg", spec="1", status="primary", statement="peak cell centre lat",
          inputs=[pb], formula="argmax", config=PRINCIPAL, dest="Results 3.1")
    claim("p_peak_lon", r.peak_flux_lon, unit="deg", spec="1", status="primary", statement="peak cell centre lon",
          inputs=[pb], formula="argmax", config=PRINCIPAL, dest="Results 3.1")
    for g in (5, 2):
        c = int(bi.loc[(g, "mean_flux", "top10")].cells_available_after_coverage_mask)
        claim(f"eligible_{g}", c, unit="cells", spec="int", status="primary",
              statement=f"monthly coverage-passed cells at {g}°", inputs=[pb], formula="count(sample_count ≥ 30)",
              config=f"NOAA-19 p1 month {g}°", denominator=f"{432 if g == 5 else 2700} nominal cells", dest="Methods")
    g2 = T / "cp4a_noaa19_2024-01_grid_2deg.parquet"
    gg = pd.read_parquet(g2)
    claim("below_min_2", int((~gg.enough_samples_2deg).sum()), unit="cells", spec="int", status="primary",
          statement="2° cells observed but below 30 samples", inputs=[g2], formula="rows with sample_count < 30",
          config="NOAA-19 p1 month 2°", dest="Results 3.1; Fig. 1c")
    claim("unobserved_2", 2700 - len(gg), unit="cells", spec="int", status="primary",
          statement="2° cells with no valid observation", inputs=[g2], formula="2700 − observed rows",
          config="NOAA-19 p1 month 2°", dest="Results 3.1; Fig. 1c")
    shifts = []
    for g in (5, 2):
        for stat in ("mean_flux", "median_flux"):
            a, z = bi.loc[(g, stat, "top20")], bi.loc[(g, stat, "top1")]
            d = dist((a.centroid_lat_flux_weighted, a.centroid_lon_flux_weighted),
                     (z.centroid_lat_flux_weighted, z.centroid_lon_flux_weighted))
            ratio = a.selected_area_km2 / z.selected_area_km2
            cratio = a.selected_cell_count / z.selected_cell_count
            tag = f"{g}_{stat.split('_')[0]}"
            shifts.append(d)
            claim(f"thr_shift_{tag}", d, unit="km", spec="0", status="primary",
                  statement=f"top20→top1 centroid displacement, {g}° {stat}", inputs=[pb],
                  formula="haversine(centroid_top20, centroid_top1)", config=f"NOAA-19 p1 month {g}° {stat}",
                  dest="Results 3.2; Fig. 2")
            claim(f"thr_area_ratio_{tag}", ratio, unit="ratio", spec="1", status="primary",
                  statement=f"top20/top1 selected-area ratio, {g}° {stat}", inputs=[pb],
                  formula="area(top20)/area(top1)", config=f"NOAA-19 p1 month {g}° {stat}", dest="Results 3.2; Fig. 2",
                  caveat="largely prescribed by the percentile rule (nominal 20×)")
            claim(f"thr_count_ratio_{tag}", cratio, unit="ratio", spec="1", status="primary",
                  statement=f"top20/top1 selected-cell-count ratio, {g}° {stat}", inputs=[pb],
                  formula="n(top20)/n(top1)", config=f"NOAA-19 p1 month {g}° {stat}", dest="Results 3.2")
    claim("thr_shift_min", min(shifts), unit="km", spec="0", status="primary",
          statement="smallest top20→top1 displacement over grid×statistic", inputs=[pb], formula="min of four",
          config="NOAA-19 p1 month", dest="Results 3.2")
    claim("thr_shift_max", max(shifts), unit="km", spec="0", status="primary",
          statement="largest top20→top1 displacement over grid×statistic", inputs=[pb], formula="max of four",
          config="NOAA-19 p1 month", dest="Results 3.2")
    for t1, t2 in (("top20", "top10"), ("top10", "top5"), ("top5", "top2"), ("top2", "top1")):
        a, z = bi.loc[(5, "mean_flux", t1)], bi.loc[(5, "mean_flux", t2)]
        claim(f"thr_step_{t1}_{t2}", dist((a.centroid_lat_flux_weighted, a.centroid_lon_flux_weighted),
                                           (z.centroid_lat_flux_weighted, z.centroid_lon_flux_weighted)),
              unit="km", spec="0", status="primary", statement=f"{t1}→{t2} step displacement 5° mean", inputs=[pb],
              formula="haversine", config="NOAA-19 p1 month 5° mean", dest="Supplement S3")

    # ---------------------------------------------------------------- channel family (original support)
    mp = CA / "morphology_pairs.csv"
    m = pd.read_csv(mp)
    for (ga, gb) in (("p1", "p2"), ("p1", "p3"), ("p2", "p3")):
        row = m[(m.grid_deg == 5) & (m.statistic == "mean_flux") & (m.channel_a == f"mep_omni_flux_{ga}")
                & (m.channel_b == f"mep_omni_flux_{gb}") & (m["mode"] == "original_percentile")].iloc[0]
        cont = m[(m.grid_deg == 5) & (m.statistic == "mean_flux") & (m.channel_a == f"mep_omni_flux_{ga}")
                 & (m.channel_b == f"mep_omni_flux_{gb}") & (m["mode"] == "common_continuous")].iloc[0]
        k = f"{gb}{ga}"
        claim(f"ch_d_{k}", row.distance_km, unit="km", spec="1", status="primary",
              statement=f"{gb}−{ga} percentile-footprint centroid distance", inputs=[mp],
              formula="haversine of area-flux centroids", config=PRINCIPAL.replace("p1", "p1/p2/p3"),
              dest="Results 3.3; Fig. 3")
        claim(f"ch_dlat_{k}", row.delta_lat, unit="deg", spec="sig3", status="primary",
              statement=f"{gb} minus {ga} centroid latitude", inputs=[mp], formula="lat(second) − lat(first)",
              config=PRINCIPAL, dest="Results 3.3", caveat="orientation: second channel minus first")
        claim(f"ch_dlon_{k}", row.delta_lon, unit="deg", spec="sig3", status="primary",
              statement=f"{gb} minus {ga} centroid longitude", inputs=[mp], formula="lon(second) − lon(first)",
              config=PRINCIPAL, dest="Results 3.3")
        claim(f"ch_jac_{k}", row.area_jaccard, unit="ratio", spec="3", status="primary",
              statement=f"{ga}/{gb} footprint area-weighted Jaccard", inputs=[mp],
              formula="area(∩)/area(∪)", config=PRINCIPAL, dest="Results 3.3")
        claim(f"ch_ov_{k}", cont.continuous_overlap, unit="ratio", spec="3", status="primary",
              statement=f"{ga}/{gb} normalized continuous-field overlap", inputs=[mp],
              formula="Σ min(p_a,p_b), p = F·A/Σ F·A over common support", config="NOAA-19 5° mean, 432 common cells",
              dest="Results 3.3; Fig. 3", caveat="mass overlap, not footprint Jaccard or % of SAA shared")
        claim(f"ch_cd_{k}", cont.distance_km, unit="km", spec="1", status="primary",
              statement=f"{ga}/{gb} whole-field normalized centroid distance", inputs=[mp],
              formula="haversine of Σ lat·p, Σ lon·p", config="NOAA-19 5° mean, whole region",
              dest="Results 3.3; Fig. 3", caveat="whole-region field summary, not an SAA centre")
        claim(f"ch_cdlat_{k}", cont.delta_lat, unit="deg", spec="sig3", status="primary",
              statement=f"{gb} minus {ga} whole-field centroid latitude", inputs=[mp], formula="second − first",
              config="NOAA-19 5° mean", dest="Results 3.3")
    ov = m[m["mode"] == "common_continuous"].continuous_overlap
    claim("ch_ov_min", ov.min(), unit="ratio", spec="3", status="primary", statement="minimum pairwise overlap, 4 grid/stat",
          inputs=[mp], formula="min", config="NOAA-19 month, 5°/2° × mean/median", dest="Results 3.3")
    claim("ch_ov_max", ov.max(), unit="ratio", spec="3", status="primary", statement="maximum pairwise overlap, 4 grid/stat",
          inputs=[mp], formula="max", config="NOAA-19 month, 5°/2° × mean/median", dest="Results 3.3")
    op = m[m["mode"] == "original_percentile"]
    claim("ch_pd_min", op.distance_km.min(), unit="km", spec="0", status="primary",
          statement="minimum channel percentile-centroid distance over 4 grid/stat × 3 pairs", inputs=[mp],
          formula="min", config="top 10%", dest="Supplement S4")
    claim("ch_pd_max", op.distance_km.max(), unit="km", spec="0", status="primary",
          statement="maximum channel percentile-centroid distance over 4 grid/stat × 3 pairs", inputs=[mp],
          formula="max", config="top 10%", dest="Supplement S4")
    cs = CA / "common_support.csv"
    c = pd.read_csv(cs)
    claim("cs_cells_5", int(c[c.grid_deg == 5].common_cells.iloc[0]), unit="cells", spec="int", status="primary",
          statement="three-channel common support, 5°", inputs=[cs], formula="∩ coverage masks and finite flux",
          config="NOAA-19 month", dest="Results 3.3")
    claim("cs_cells_2", int(c[c.grid_deg == 2].common_cells.iloc[0]), unit="cells", spec="int", status="primary",
          statement="three-channel common support, 2°", inputs=[cs], formula="∩ coverage masks and finite flux",
          config="NOAA-19 month", dest="Results 3.3")

    # ---------------------------------------------------------------- paired resampling
    pq = CA / "paired_quantiles.csv"
    qq = pd.read_csv(pq)
    for L in (1, 3, 7):
        for (ga, gb) in (("p1", "p2"), ("p1", "p3"), ("p2", "p3")):
            for metric in ("delta_lat", "delta_lon", "distance_km"):
                row = qq[(qq.block_length == L) & (qq.channel_a == f"mep_omni_flux_{ga}")
                         & (qq.channel_b == f"mep_omni_flux_{gb}") & (qq.metric == metric)].iloc[0]
                if int(row.defined) != 1000 or int(row.failed) != 0:
                    raise ValueError("unexpected undefined replicates")
                short = {"delta_lat": "lat", "delta_lon": "lon", "distance_km": "km"}[metric]
                for qn in ("q025", "q50", "q975"):
                    claim(f"bs_{L}_{gb}{ga}_{short}_{qn}", float(row[qn]), unit="km" if short == "km" else "deg",
                          spec="0" if short == "km" else "sig2", status="primary",
                          statement=f"{L}-day block, {gb}−{ga} {metric} {qn}", inputs=[pq],
                          formula="empirical quantile over 1000 paired replicates (pandas linear)",
                          config="protocol 1.0, seed 20260929", denominator="1000 defined replicates",
                          dest="Results 3.3; Fig. 3; Supplement S5",
                          caveat="conditional resampling stability, not calibrated confidence")

    # ---------------------------------------------------------------- time family
    pt = T / "cp4d_time_window_threshold_sensitivity.parquet"
    ps = T / "cp4d_temporal_support.parquet"
    tw = pd.read_parquet(pt)
    ts = pd.read_parquet(ps)
    for g_, pre in ((5, "tw"), (2, "tw2")):
        _time_claims(ts, g_, pre, ps)
    wk = tw[(tw.grid_deg == 5) & (tw.statistic_used == "mean_flux") & (tw.threshold_label == "top10")
            & tw.window_label.isin(["week1", "week2", "week3", "week4"])].set_index("window_label")
    wd = [dist((wk.loc[a].centroid_lat_flux_weighted, wk.loc[a].centroid_lon_flux_weighted),
               (wk.loc[z].centroid_lat_flux_weighted, wk.loc[z].centroid_lon_flux_weighted))
          for a, z in itertools.combinations(wk.index, 2)]
    claim("tw_week_max", max(wd), unit="km", spec="0", status="primary", statement="maximum pairwise weekly centroid distance",
          inputs=[pt], formula="max haversine over 6 disjoint week pairs", config="NOAA-19 p1 5° mean top10",
          dest="Results 3.4")
    claim("tw_week_min", min(wd), unit="km", spec="0", status="primary", statement="minimum pairwise weekly centroid distance",
          inputs=[pt], formula="min haversine over 6 disjoint week pairs", config="NOAA-19 p1 5° mean top10",
          dest="Results 3.4")
    claim("tw_rows", len(ts), unit="rows", spec="int", status="primary", statement="temporal-support diagnostic rows",
          inputs=[ps], formula="9 windows × 2 grids × 2 statistics × 5 thresholds", config="all CP4D settings",
          dest="Supplement S6")
    claim("tw_undefined", int((ts.original_undefined_reason.fillna("") != "").sum()
                              + (ts.common_undefined_reason.fillna("") != "").sum()), unit="rows", spec="int",
          status="primary", statement="undefined temporal diagnostics", inputs=[ps], formula="count non-empty reasons",
          config="all CP4D settings", dest="Supplement S6")
    nonmonth = ts[~ts.window_label.isin(["month_2024-01"])]
    better = (nonmonth.area_jaccard_common >= nonmonth.area_jaccard_original - 1e-12)
    claim("tw_jc_ge_je_n", int(better.sum()), unit="rows", spec="int", status="primary",
          statement="non-month rows where shared-support Jaccard ≥ end-to-end Jaccard", inputs=[ps], formula="count",
          config="8 windows × 20 settings", denominator=f"{len(nonmonth)} rows", dest="Results 3.4")
    claim("tw_nonmonth_n", len(nonmonth), unit="rows", spec="int", status="primary", statement="non-month rows",
          inputs=[ps], formula="count", config="8 windows (week1 alias included)", dest="Results 3.4")
    dcl = nonmonth.centroid_distance_km_common > nonmonth.centroid_distance_km_original + 1e-9
    claim("tw_dc_gt_de_n", int(dcl.sum()), unit="rows", spec="int", status="primary",
          statement="non-month rows where shared-support centroid distance exceeds end-to-end", inputs=[ps],
          formula="count", config="8 windows × 20 settings", dest="Results 3.4")

    # ---------------------------------------------------------------- satellite family, QC-1 primary vs unfiltered
    pp = QS / "pairwise.csv"
    pw = pd.read_csv(pp)
    pf = T / "cp4f_pairwise_centroid_distances.parquet"
    canon = pd.read_parquet(pf)
    cprin = canon[canon.comparison_case == "top10_5deg_mean"]
    SC = (("qc_primary", "prim", "primary", "QC-1 applied (primary)"),
          ("unfiltered", "unf", "sensitivity", "unfiltered (QC-1 not applied)"))

    def pmax(scen, grid=5, stat="mean_flux", thr="top10"):
        return pw[(pw.scenario == scen) & (pw.grid_deg == grid) & (pw.statistic == stat) & (pw.threshold == thr)]

    for case, grid, thr in (("top10_5deg_mean", 5, "top10"), ("top5_5deg_mean", 5, "top5"),
                            ("top10_2deg_mean", 2, "top10"), ("top5_2deg_mean", 2, "top5")):
        def by_pair(d):
            return d.assign(pair=[tuple(sorted(x)) for x in zip(d.satellite_a, d.satellite_b)]).set_index("pair").distance_km.sort_index()
        a = by_pair(canon[canon.comparison_case == case])
        b = by_pair(pmax("qc_primary", grid, "mean_flux", thr))
        if list(a.index) != list(b.index) or not np.allclose(a.to_numpy(), b.to_numpy(), rtol=0, atol=1e-9):
            raise ValueError(f"canonical cp4f pairwise {case} disagrees with the QC-1 primary scenario")
    # the rule-based exclusion must reproduce the recorded exact-record omission, and unfiltered the as-is data
    om = pd.read_csv(OM / "pairwise.csv")
    for mine, theirs in (("qc_primary", "omit_exact_record"), ("unfiltered", "as_is")):
        x = pw[pw.scenario == mine].drop(columns="scenario").reset_index(drop=True)
        y = om[om.scenario == theirs].drop(columns="scenario").reset_index(drop=True)
        pd.testing.assert_frame_equal(x, y, check_exact=False, rtol=0, atol=1e-9)
    for scen, tag, status, label in SC:
        sub = pmax(scen)
        top = sub.loc[sub.distance_km.idxmax()]
        claim(f"sat_max_{tag}", top.distance_km, unit="km", spec="1", status=status,
              statement=f"maximum five-satellite pairwise centroid distance, {label}", inputs=[pp],
              formula="max haversine over 10 pairs", config=PRINCIPAL.replace("NOAA-19 ", "5 satellites, "),
              dest="Abstract; Results 3.5; Fig. 5",
              caveat="" if tag == "prim" else "unfiltered data retained as provenance/sensitivity")
        names = {"noaa15": "NOAA-15", "noaa18": "NOAA-18", "noaa19": "NOAA-19", "metop01": "MetOp-01", "metop03": "MetOp-03"}
        claim(f"sat_max_pair_{tag}", f"{names[top.satellite_a]}/{names[top.satellite_b]}", unit="", spec="", status=status,
              statement=f"pair attaining the maximum, {label}", inputs=[pp], formula="argmax", config="5° mean top10",
              dest="Results 3.5")
        claim(f"sat_max_median_{tag}", pmax(scen, stat="median_flux").distance_km.max(), unit="km", spec="1",
              status=status, statement=f"maximum pairwise distance, 5° median top10, {label}", inputs=[pp],
              formula="max", config="5 satellites 5° median top10", dest="Results 3.5; Fig. 5")
        claim(f"sat_max_{tag}_2", pmax(scen, grid=2).distance_km.max(), unit="km", spec="1", status=status,
              statement=f"maximum pairwise distance, 2° mean top10, {label}", inputs=[pp], formula="max",
              config="5 satellites 2° mean top10", dest="Results 3.5")
        claim(f"sat_max_median_{tag}_2", pmax(scen, grid=2, stat="median_flux").distance_km.max(), unit="km",
              spec="1", status=status, statement=f"maximum pairwise distance, 2° median top10, {label}", inputs=[pp],
              formula="max", config="5 satellites 2° median top10", dest="Supplement S7")
        mx = [pmax(scen, thr=t).distance_km.max() for t in ("top20", "top10", "top5", "top2", "top1")]
        for fn, nm in ((min, "min"), (max, "max")):
            claim(f"sat_thr_{tag}_{nm}", fn(mx), unit="km", spec="0", status=status,
                  statement=f"{nm} over thresholds of the five-satellite maximum distance, 5° mean, {label}",
                  inputs=[pp], formula=f"{nm} over top20..top1 of max pairwise", config="5° mean",
                  dest="Results 3.5; Fig. 5b")
    med5_same = all(np.isclose(pmax("qc_primary", 5, "median_flux", t).distance_km.max(),
                               pmax("unfiltered", 5, "median_flux", t).distance_km.max(), rtol=0, atol=1e-9)
                    for t in ("top20", "top10", "top5", "top2", "top1"))
    if not med5_same:
        raise ValueError("5° median maxima differ between scenarios; manuscript wording assumes they do not")
    medthr = {t: pmax("qc_primary", 5, "median_flux", t).distance_km.max() for t in ("top20", "top10", "top5", "top2", "top1")}
    tmax = max(medthr, key=medthr.get)
    claim("sat_med_thr_prim_max", medthr[tmax], unit="km", spec="0", status="primary",
          statement="largest five-satellite maximum over thresholds, 5° median, QC-1", inputs=[pp], formula="max over thresholds",
          config="5° median", dest="Results 3.5; Fig. 5b")
    claim("sat_med_thr_prim_argmax", {"top20": "20", "top10": "10", "top5": "5", "top2": "2", "top1": "1"}[tmax],
          unit="%", spec="", status="primary", statement="threshold (top %) at which that maximum occurs", inputs=[pp],
          formula="argmax", config="5° median", dest="Results 3.5")
    claim("sat_median5_unchanged", "yes", unit="", spec="", status="primary",
          statement="5° median-based five-satellite maxima identical with and without QC-1 at every threshold",
          inputs=[pp], formula="compare 5 maxima", config="5° median, 5 thresholds", dest="Results 3.5; Fig. 5")
    claim("sat_median2_maxdiff", max(abs(pmax("qc_primary", 2, "median_flux", t).distance_km.max()
                                         - pmax("unfiltered", 2, "median_flux", t).distance_km.max())
                                     for t in ("top20", "top10", "top5", "top2", "top1")),
          unit="km", spec="3", status="sensitivity",
          statement="largest change of a 2° median-based five-satellite maximum between scenarios", inputs=[pp],
          formula="max |Δ max pairwise| over 5 thresholds", config="2° median", dest="Results 3.5; Supplement S7")
    n1819 = cprin[(cprin.satellite_a == "noaa18") & (cprin.satellite_b == "noaa19")].distance_km.iloc[0]
    claim("sat_n18n19", n1819, unit="km", spec="1", status="primary", statement="NOAA-18/NOAA-19 principal distance",
          inputs=[pf], formula="haversine", config="5° mean top10", dest="Results 3.5")
    nn15 = cprin[(cprin.satellite_a != "noaa15") & (cprin.satellite_b != "noaa15")]
    claim("sat_max_excl15", nn15.distance_km.max(), unit="km", spec="1", status="primary",
          statement="maximum principal pairwise distance among the four satellites other than NOAA-15",
          inputs=[pf], formula="max over 6 pairs", config="5° mean top10", dest="Results 3.5")
    n15 = pmax("qc_primary").distance_km.where((pmax("qc_primary").satellite_a == "noaa15")
                                               | (pmax("qc_primary").satellite_b == "noaa15")).dropna()
    claim("sat_n15_max_prim", n15.max(), unit="km", spec="1", status="primary",
          statement="largest principal distance between NOAA-15 and another satellite, QC-1 primary", inputs=[pp],
          formula="max over 4 NOAA-15 pairs", config="5° mean top10", dest="Results 3.5")
    psn = QS / "sensitivity.csv"
    sn = pd.read_csv(psn)
    n15c = sn[(sn.satellite == "noaa15") & (sn.grid_deg == 5) & (sn.statistic_used == "mean_flux")
              & (sn.threshold_label == "top10")].set_index("scenario")
    for scen, tag, status, label in SC:
        for col, k in (("centroid_lat_flux_weighted", "lat"), ("centroid_lon_flux_weighted", "lon")):
            claim(f"n15_{k}_{tag}", float(n15c.loc[scen, col]), unit="deg", spec="2", status=status,
                  statement=f"NOAA-15 principal centroid {k}, {label}", inputs=[psn], formula="Σ x·F·A / Σ F·A",
                  config="NOAA-15 5° mean top10", dest="Results 3.5; Fig. 5a")
        claim(f"n15_peak_{tag}", float(n15c.loc[scen, "peak_flux"]), unit="#/(cm² s sr MeV)", spec="1", status=status,
              statement=f"NOAA-15 highest eligible 5° cell mean, {label}", inputs=[psn], formula="max cell mean",
              config="NOAA-15 5° mean", dest="Results 3.5")
    claim("n15_shift", haversine_km(n15c.loc["unfiltered", "centroid_lat_flux_weighted"],
                                    n15c.loc["unfiltered", "centroid_lon_flux_weighted"],
                                    n15c.loc["qc_primary", "centroid_lat_flux_weighted"],
                                    n15c.loc["qc_primary", "centroid_lon_flux_weighted"]),
          unit="km", spec="0", status="sensitivity", statement="NOAA-15 principal centroid shift, unfiltered → QC-1",
          inputs=[psn], formula="haversine", config="NOAA-15 5° mean top10", dest="Results 3.5; Fig. 5a")
    pcm = QS / "cp5_changed_memberships.csv"
    cm = pd.read_csv(pcm)
    claim("ev_members_top10_5", int(((cm.satellite == "noaa15") & (cm.footprint == "in_top10_5deg")).sum()),
          unit="records", spec="int", status="sensitivity",
          statement="NOAA-15 regional records whose top10/5° footprint membership differs between scenarios",
          inputs=[pcm], formula="count(in_unfiltered != in_qc_primary)", config="NOAA-15 region, 5° mean top10",
          dest="Results 3.5; Supplement S7")
    if set(cm.satellite) - {"noaa15"}:
        raise ValueError("footprint membership changed outside NOAA-15")
    pfc = QS / "footprint_changes.csv"
    fpc = pd.read_csv(pfc)
    prin_fp = fpc[(fpc.satellite == "noaa15") & (fpc.grid_deg == 5) & (fpc.statistic == "mean_flux")
                  & (fpc.threshold == "top10")]
    claim("n15_fp_cells_changed", len(prin_fp), unit="cells", spec="int", status="sensitivity",
          statement="NOAA-15 principal footprint cells that differ between scenarios (entering + leaving)",
          inputs=[pfc], formula="symmetric difference", config="NOAA-15 5° mean top10", dest="Results 3.5")
    claim("fp_settings_changed", int(fpc.groupby(["satellite", "grid_deg", "statistic", "threshold"]).ngroups),
          unit="settings", spec="int", status="sensitivity",
          statement="satellite settings (of 100) whose footprint cell set differs between scenarios", inputs=[pfc],
          formula="count of settings with a non-empty symmetric difference", config="5 satellites × 20 settings",
          dest="Supplement S7")
    pec = QS / "event_cell.csv"
    ec = pd.read_csv(pec)
    oac = pd.read_csv(OM / "affected_cell.csv")
    for mine, theirs in (("qc_primary", "omit_exact_record"), ("unfiltered", "as_is")):
        x = ec[ec.scenario == mine].reset_index(drop=True)
        y = oac[oac.scenario == theirs].reset_index(drop=True)
        for col in ("count", "mean", "median", "descending_rank", "selected", "cell_centroid_weight"):
            if not np.allclose(x[col].astype(float), y[col].astype(float), rtol=0, atol=1e-9):
                raise ValueError(f"event cell {col} differs from the recorded omission evidence ({mine})")
    for scen, tag, status, label in SC:
        row = ec[(ec.scenario == scen) & (ec.grid_deg == 5) & (ec.statistic == "mean_flux") & (ec.threshold == "top10")].iloc[0]
        for col, k, spec, unit in (("mean", "mean", "2", "#/(cm² s sr MeV)"), ("median", "median", "2", "#/(cm² s sr MeV)"),
                                   ("count", "count", "int", "records"), ("descending_rank", "rank", "int", "rank")):
            v = row[col] if spec != "int" else int(row[col])
            claim(f"ev_{k}_{tag}", v, unit=unit, spec=spec, status=status,
                  statement=f"excluded record's 5° cell {k}, {label}", inputs=[pec], formula=col,
                  config="NOAA-15 5° cell (−12.5, −27.5)", dest="Results 3.5; Supplement S7")
        if tag == "unf":
            claim("ev_weight", row.cell_centroid_weight, unit="fraction", spec="pct1", status="sensitivity",
                  statement="that cell's share of the unfiltered NOAA-15 principal centroid weight", inputs=[pec],
                  formula="F·A(cell)/Σ F·A(selected)", config="NOAA-15 5° mean top10", dest="Results 3.5")
    pl = T / "qc1_omni_exclusions.csv"
    led = pd.read_csv(pl)
    if len(led) != 1 or int(led.native_index.iloc[0]) != 13867 or led.source_file.iloc[0] != "poes_n15_20240119_proc.nc":
        raise ValueError("manuscript text assumes QC-1 excludes exactly the one NOAA-15 record; revisit the text")
    ev0 = led.iloc[0]
    claim("ev_frac_sum", ev0.p1 / (ev0.cell5_mean_unfiltered * ev0.cell5_count_unfiltered), unit="fraction",
          spec="pct1", status="sensitivity", statement="excluded record's share of its 5° cell flux sum (unfiltered)",
          inputs=[pl], formula="p1 / Σ p1 in cell", config="NOAA-15 5° cell", dest="Results 3.5")
    for ch in ("p1", "p2", "p3"):
        claim(f"ev_{ch}", float(ev0[ch]), unit="#/(cm² s sr MeV)", spec="1" if ch != "p1" else "int",
              status="primary", statement=f"excluded record {ch} (stored float32)", inputs=[pl], formula="stored",
              config="event", dest="Methods; Results 3.5")
        for side in ("left", "right"):
            claim(f"ev_{ch}_ratio_{side}", float(ev0[f"{ch}_ratio_{side}"]), unit="ratio", spec="int", status="primary",
                  statement=f"excluded record {ch} / median of its 10 {'preceding' if side == 'left' else 'following'} records",
                  inputs=[pl], formula="value / median", config="QC-1", dest="Methods; Supplement S7")
        claim(f"ev_{ch}_nb_median_{'l'}", float(ev0[f"{ch}_left_median"]), unit="#/(cm² s sr MeV)", spec="2",
              status="primary", statement=f"median {ch} of the 10 preceding records", inputs=[pl], formula="median",
              config="QC-1", dest="Supplement S7")
    claim("ev_spectral_ratio", float(ev0.p1 / ev0.p2), unit="ratio", spec="3", status="primary",
          statement="p1/p2 of the excluded record (equal to 2^2.9 for a default-slope one-point fit)", inputs=[pl],
          formula="p1/p2", config="event", dest="Methods; Supplement S7")
    claim("ev_spectral_ratio_p2p3", float(ev0.p2 / ev0.p3), unit="ratio", spec="3", status="primary",
          statement="p2/p3 of the excluded record", inputs=[pl], formula="p2/p3", config="event", dest="Supplement S7")
    claim("gamma_default_ratio", 2 ** 2.9, unit="ratio", spec="3", status="primary",
          statement="2^2.9: flux ratio between energies a factor 2 apart for the ATBD default slope −2.9",
          inputs=[], formula="2**2.9", config="ATBD γ_default", dest="Methods")
    claim("qc_excl_global", len(led), unit="records", spec="int", status="primary",
          statement="records QC-1 excludes in the 155 analysed files (any location)", inputs=[pl], formula="count",
          config="QC-1 v1.0", dest="Abstract; Methods; Supplement S7")
    claim("qc_excl_region", int(led.in_region_after_ifc.sum()), unit="records", spec="int", status="primary",
          statement="records QC-1 excludes inside the study region", inputs=[pl], formula="count", config="QC-1 v1.0",
          dest="Methods")
    ctx = pd.read_csv(QS / "event_context.csv")
    c0 = ctx[ctx.offset == 0].iloc[0]
    nbx = ctx[(ctx.offset != 0) & (ctx.offset.abs() <= 10)]
    claim("ev_dir_p6_event", float(max(c0.mep_pro_tel0_flux_p6, c0.mep_pro_tel90_flux_p6)), unit="#/(cm² s sr)",
          spec="int", status="primary", statement="largest co-located directional MEPED P6 flux at the excluded record",
          inputs=[QS / "event_context.csv"], formula="max(0°, 90°)", config="event", dest="Methods; Supplement S7")
    claim("ev_dir_p6_nb_min", float(nbx[["mep_pro_tel0_flux_p6", "mep_pro_tel90_flux_p6"]].min().min()),
          unit="#/(cm² s sr)", spec="int", status="primary",
          statement="smallest directional P6 flux (0° or 90°) among the 20 neighbours", inputs=[QS / "event_context.csv"],
          formula="min", config="±10 records", dest="Methods; Supplement S7")
    ppo = QS / "population.csv"
    po = pd.read_csv(ppo)
    p1p = po[po.channel == "mep_omni_flux_p1"]
    claim("qc_records", int(p1p.records.sum()), unit="records", spec="int", status="primary",
          statement="native records screened by QC-1 (5 satellites, 155 files)", inputs=[ppo], formula="sum",
          config="QC-1", dest="Methods")
    claim("qc_iso_fallback", int(p1p.isolated_fallback.sum()), unit="records", spec="int", status="primary",
          statement="isolated fallback records with an evaluable p1 (fit 1/2 inside 20 contiguous regular fits)",
          inputs=[ppo], formula="sum", config="QC-1", dest="Methods; Supplement S7")
    claim("qc_regular_n", int(p1p.regular_evaluable.sum()), unit="records", spec="int", status="primary",
          statement="regular-fit records with an evaluable two-sided p1 ratio", inputs=[ppo], formula="sum",
          config="QC-1 neighbourhood", dest="Methods; Supplement S7")
    claim("qc_regular_max", float(p1p.regular_max.max()), unit="ratio", spec="1", status="primary",
          statement="largest two-sided p1 ratio of any evaluable regular-fit record", inputs=[ppo],
          formula="max min(left,right)", config="QC-1 neighbourhood, p1, 5 satellites", dest="Methods; Supplement S7")
    for fn, nm in ((min, "min"), (max, "max")):
        claim(f"qc_fallback_median_{nm}", float(fn(p1p.fallback_ratio_median)), unit="ratio", spec="1", status="primary",
              statement=f"{nm} over satellites of the median two-sided p1 ratio of isolated fallback records",
              inputs=[ppo], formula=f"{nm} of per-satellite medians", config="QC-1, p1", dest="Methods; Supplement S7")
    claim("qc_fallback_max", float(p1p.fallback_ratio_max_kept.max()), unit="ratio", spec="1", status="primary",
          statement="largest two-sided p1 ratio of any retained isolated fallback record", inputs=[ppo],
          formula="max over kept", config="QC-1, p1", dest="Methods; Supplement S7")
    if float(po.regular_max.max()) > float(p1p.regular_max.max()) or \
            float(po.fallback_ratio_max_kept.max()) > float(p1p.fallback_ratio_max_kept.max()):
        raise ValueError("p2/p3 envelopes exceed p1; the Methods wording quotes the p1 envelope as the overall one")
    from saa.quality import QC1
    for key, val_, spec, st in (("qc_k", QC1["neighbours_per_side"], "int", "neighbours per side"),
                                ("qc_step", QC1["max_step_seconds"], "0", "maximum contiguous step (s)"),
                                ("qc_ratio", QC1["ratio"], "0", "two-sided ratio threshold")):
        claim(key, val_, unit="", spec=spec, status="primary", statement=f"QC-1 parameter: {st}",
              inputs=[ROOT_SRC / "saa/quality.py"], formula="QC1 constant", config=f"QC-1 v{QC1['version']}",
              dest="Methods 2.2; Table 1")
    claim("qc_ratio_margin", QC1["ratio"] / float(p1p.fallback_ratio_max_kept.max()), unit="ratio", spec="1",
          status="primary", statement="QC-1 ratio divided by the largest retained isolated-fallback p1 departure",
          inputs=[ppo], formula="ratio / max kept", config="QC-1, p1", dest="Methods 2.2")
    claim("qc_region_regular", float(p1p.region_regular_neighbourhood.sum() / p1p.region_records.sum()),
          unit="fraction", spec="pct1", status="primary",
          statement="regional records whose 20 contiguous neighbours all received the regular fit (where QC-1 can act)",
          inputs=[ppo], formula="Σ regular-neighbourhood / Σ regional records", config="5 satellites, region after the IFC rule",
          dest="Limitations")
    ppt = QS / "perturbation.csv"
    pt = pd.read_csv(ppt)
    claim("qc_pert_same", int(pt.same_set_as_adopted.sum()), unit="variants", spec="int", status="primary",
          statement="parameter variants giving exactly the adopted exclusion set", inputs=[ppt], formula="count",
          config="perturbation study", dest="Methods; Supplement S7")
    claim("qc_pert_n", len(pt), unit="variants", spec="int", status="primary", statement="parameter variants tested",
          inputs=[ppt], formula="count", config="perturbation study", dest="Methods; Supplement S7")
    rat = pt[pt.variant.str.match(r"^ratio \d+x$") | (pt.variant == "adopted rule")].copy()
    rat["r"] = rat.ratio.astype(float)
    same = rat[rat.same_set_as_adopted]
    claim("qc_ratio_lo", same.r.min(), unit="ratio", spec="0", status="primary",
          statement="smallest tested ratio giving the adopted set", inputs=[ppt], formula="min", config="k = 10",
          dest="Methods; Supplement S7")
    claim("qc_ratio_hi", same.r.max(), unit="ratio", spec="0", status="primary",
          statement="largest tested ratio giving the adopted set", inputs=[ppt], formula="max", config="k = 10",
          dest="Methods; Supplement S7")
    for r_ in (10, 15):
        claim(f"qc_ratio_{r_}_n", int(rat[rat.r == r_].excluded_global.iloc[0]), unit="records", spec="int",
              status="primary", statement=f"records excluded with a {r_}x ratio", inputs=[ppt], formula="count",
              config="k = 10", dest="Supplement S7")
    nn = pt[pt.variant == "no regular-fit neighbour requirement"].iloc[0]
    claim("qc_nonb_n", int(nn.excluded_global), unit="records", spec="int", status="primary",
          statement="records excluded if the regular-fit neighbour condition is dropped", inputs=[ppt],
          formula="count", config="ratio 100", dest="Methods; Supplement S7")
    claim("qc_nonb_region", int(nn.excluded_in_region), unit="records", spec="int", status="primary",
          statement="of which inside the study region", inputs=[ppt], formula="count", config="ratio 100",
          dest="Supplement S7")
    prc = QS / "event_raw_counts_summary.json"
    rc = json.loads(prc.read_text())["events"][0]
    for key, k, spec in (("p7_cps", "rc_p7", "int"), ("p6_cps", "rc_p6", "int"), ("p9_cps", "rc_p9", "int"),
                         ("p6_neighbours_min", "rc_p6_nb_min", "int"), ("p6_neighbours_max", "rc_p6_nb_max", "int"),
                         ("p7_neighbours_min", "rc_p7_nb_min", "int"), ("p7_neighbours_max", "rc_p7_nb_max", "int"),
                         ("p7_over_p6_event", "rc_p7p6", "int"), ("p7_over_p6_day_max_other", "rc_p7p6_other", "1"),
                         ("p7_day_second_highest_cps", "rc_p7_second", "int"),
                         ("directional_p6_cps_neighbours_min", "rc_dir_nb_min", "1")):
        claim(k, float(rc[key]), unit="counts/s" if "over" not in key else "ratio", spec=spec, status="primary",
              statement=f"level-1a count-rate evidence: {key}", inputs=[prc], formula=key,
              config="poes_n15_20240119_raw.nc (evidence only)", dest="Results 3.5; Supplement S7",
              caveat="evidence for the excluded record; not an analysis input")
    for kind in ("proton", "electron"):
        for what in ("total", "zero_at_event"):
            claim(f"rc_dir_{kind}_{'n' if what == 'total' else 'zero'}",
                  int(rc[f"directional_{kind}_count_channels_{what}"]), unit="channels", spec="int", status="primary",
                  statement=f"directional MEPED {kind} count channels: {what.replace('_', ' ')}", inputs=[prc],
                  formula="count", config="excluded record, level-1a", dest="Supplement S7")
    claim("rc_zero_n", len(rc["variables_zero_at_event_nonzero_in_all_20_neighbours"]), unit="variables", spec="int",
          status="primary", statement="level-1a variables exactly zero at the record but non-zero in all 20 neighbours",
          inputs=[prc], formula="count", config="evidence", dest="Supplement S7")
    span = rc["bias_V_unusual_record_span"]
    claim("rc_bias_span", span[1] - span[0] + 1, unit="records", spec="int", status="primary",
          statement="records with the unusual OMNI bias-voltage housekeeping value around the event", inputs=[prc],
          formula="span", config="evidence", dest="Supplement S7", caveat="coincident; cause unknown")
    dj = OM / "event_dossier.json"
    ev = json.loads(dj.read_text())
    claim("ev_index", int(ev["native_index"]), unit="index", spec="", status="primary",
          statement="zero-based native record index", inputs=[dj], formula="source position", config="event",
          dest="Results 3.5")
    claim("ev_utc", "2024-01-19T09:14:30.051Z", unit="UTC", spec="", status="primary", statement="event time",
          inputs=[dj], formula="milliseconds since epoch → UTC", config="event", dest="Results 3.5")
    claim("ev_sha", ev["source_sha256"], unit="", spec="", status="primary", statement="source SHA-256",
          inputs=[dj], formula="sha256", config="poes_n15_20240119_proc.nc", dest="Results 3.5; Supplement")
    if ev["utc"] != "2024-01-19 09:14:30.051000+00:00" or int(ev["native_index"]) != int(ev0.native_index):
        raise ValueError("event identity mismatch between the dossier and the QC-1 ledger")

    # ---------------------------------------------------------------- recorded triage census (audit replay)
    AR = Path("outputs/audit_replay")
    pc, pk = AR / "census.csv", AR / "candidates.csv"
    cen, cand = pd.read_csv(pc), pd.read_csv(pk)
    for key, value, st in (
        ("census_records", int(cen.drop_duplicates("satellite").source_records.sum()), "native source records screened"),
        ("census_values", int(cen.channel_values.sum()), "channel values screened"),
        ("census_candidates", int(cen.candidates.sum()), "candidate channel values"),
        ("census_candidate_records", int(cand.drop_duplicates(["source_sha256", "native_index"]).shape[0]),
         "unique records with a candidate value"),
    ):
        claim(key, value, unit="count", spec="int", status="audit", statement=st, inputs=[pc, pk],
              formula="frozen two-sided 100× ten-neighbour triage (phase1/census_protocol.json)",
              config="original extractor, 155 files, 7 satellite/channel combinations", dest="Supplement S7",
              caveat="triage only; most records unevaluable; not exhaustive validation")
    claim("census_eval_min", cen.evaluable_fraction.min(), unit="fraction", spec="pct1", status="audit",
          statement="minimum evaluable fraction", inputs=[pc], formula="evaluable/records", config="per combination",
          dest="Supplement S7")
    claim("census_eval_max", cen.evaluable_fraction.max(), unit="fraction", spec="pct1", status="audit",
          statement="maximum evaluable fraction", inputs=[pc], formula="evaluable/records", config="per combination",
          dest="Supplement S7")
    pm = AR / "mlt_probe.csv"
    mp = pd.read_csv(pm)
    for shift in (0, 12):
        claim(f"mlt_probe_wrap_{shift}", float(mp[(mp.case == "wrapping") & (mp["shift"] == shift)].separation.iloc[0]),
              unit="", spec="3", status="retired", statement=f"legacy linear MLT separation, wrapping probe, {shift} h shift",
              inputs=[pm], formula="legacy footprint_magnetic_summary", config="synthetic probe",
              dest="Supplement S8 (retirement rationale)")
    nb = OM / "event_native_neighbors.csv"
    nbr = pd.read_csv(nb)
    others = nbr[nbr.native_index != int(ev["native_index"])]
    claim("ev_nb_p1_median", float(others.mep_omni_flux_p1.median()), unit="#/(cm² s sr MeV)", spec="1",
          status="primary", statement="median p1 of the 20 native neighbours", inputs=[nb], formula="median",
          config="±10 records", dest="Methods 2.8; Supplement S7")
    claim("ev_fit", int(nbr[nbr.native_index == int(ev["native_index"])].mep_omni_flux_flag_fit.iloc[0]), unit="flag",
          spec="int", status="primary", statement="event fit flag", inputs=[nb], formula="stored", config="event",
          dest="Methods 2.8")
    claim("ev_nb_fit0", int((others.mep_omni_flux_flag_fit == 0).sum()), unit="records", spec="int", status="primary",
          statement="neighbours with fit flag 0", inputs=[nb], formula="count", config="±10 records", dest="Methods 2.8")

    # ---------------------------------------------------------------- magnetic (descriptive supplement)
    claim("mag_q25_min", q.btot_fraction_below_regional_q25.min(), unit="fraction", spec="pct0", status="descriptive",
          statement="min fraction of footprint samples below regional Btot Q1", inputs=[p5], formula="per satellite",
          config="5 satellites principal case", dest="Supplement S8", caveat="modeled IGRF; descriptive only")
    claim("mag_cap90_min", q.btot_regional_fraction_to_capture_90pct.min(), unit="fraction", spec="pct1",
          status="descriptive", statement="min regional Btot fraction capturing 90% of footprint samples",
          inputs=[p5], formula="per satellite", config="principal case", dest="Supplement S8")
    claim("mag_cap90_max", q.btot_regional_fraction_to_capture_90pct.max(), unit="fraction", spec="pct1",
          status="descriptive", statement="max regional Btot fraction capturing 90% of footprint samples",
          inputs=[p5], formula="per satellite", config="principal case", dest="Supplement S8")
    claim("mag_sep_min", q.btot_separation_metric.min(), unit="", spec="3", status="descriptive",
          statement="min Btot separation metric", inputs=[p5], formula="existing CP5 metric", config="principal case",
          dest="Supplement S8")
    claim("mag_sep_max", q.btot_separation_metric.max(), unit="", spec="3", status="descriptive",
          statement="max Btot separation metric", inputs=[p5], formula="existing CP5 metric", config="principal case",
          dest="Supplement S8")
    claim("retired_classification", str(q.cp5c_classification.iloc[0]), unit="", spec="", status="retired",
          statement="legacy combined CP5C classification (retired; not a current finding)", inputs=[p5],
          formula="separate-count v1 with origin-dependent MLT dominance", config="legacy",
          dest="Supplement S8 (retired, labeled)", caveat="must not be cited as validation")

    # ---------------------------------------------------------------- configuration universe
    vj = Path("site/public/data/viewer_data.json")
    payload = json.loads(vj.read_text())
    groups: dict[tuple, list] = {}
    counts = {}
    for exp, spec in payload["experiments"].items():
        counts[exp] = len(spec["configurations"])
        for cfg in spec["configurations"]:
            v = cfg["values"]
            key = (cfg["grid_id"], v["statistic_used"], v["threshold_label"])
            groups.setdefault(key, []).append(cfg["id"])
    total = sum(counts.values())
    ids = [i for ids_ in groups.values() for i in ids_]
    if len(ids) != len(set(ids)) or total != 360:
        raise ValueError("configuration IDs not unique or total != 360")
    for exp, n in counts.items():
        claim(f"cfg_{exp}", n, unit="configurations", spec="int", status="primary", statement=f"{exp} configurations",
              inputs=[vj], formula="payload count", config="viewer export", dest="Methods; Table 1")
    claim("cfg_total", total, unit="configurations", spec="int", status="primary", statement="total configurations",
          inputs=[vj], formula="sum", config="viewer export", dest="Methods")
    claim("cfg_distinct", len(groups), unit="configurations", spec="int", status="primary",
          statement="distinct (grid content, statistic, threshold) states", inputs=[vj],
          formula="unique (grid_id, statistic, threshold)", config="viewer export", dest="Methods",
          caveat="configuration count is not a count of independent experiments")
    alias_rows = [{"canonical": sorted(v)[0], "members": sorted(v)} for v in groups.values() if len(v) > 1]
    (OUT / "configuration_aliases.json").write_text(json.dumps(alias_rows, indent=1) + "\n")

    # ---------------------------------------------------------------- write
    keys = [c["key"] for c in CLAIMS]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate claim keys")
    (OUT / "claims_register.json").write_text(json.dumps(CLAIMS, indent=1, ensure_ascii=False) + "\n")
    flat = pd.DataFrame([{**c, "inputs": ";".join(f"{i['path']}@{i['sha256'][:12]}" for i in c["inputs"])}
                         for c in CLAIMS])
    flat.to_csv(OUT / "claims_register.csv", index=False)
    lines = ["// Generated by scripts/build_claims_register.py — do not edit by hand.", "#let V = ("]
    for c in CLAIMS:
        lines.append(f'  "{c["key"]}": "{c["formatted"]}",')
    lines.append(")")
    (OUT / "values.typ").write_text("\n".join(lines) + "\n")
    print(f"{len(CLAIMS)} claims; statuses:", flat.status.value_counts().to_dict())


if __name__ == "__main__":
    main()
