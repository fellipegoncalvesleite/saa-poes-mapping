"""QC-1 evidence: exclusion ledger, population envelopes, parameter perturbations and science impact.

Run from repository root after notebooks 02-05c:

    PYTHONPATH=src python scripts/run_qc_sensitivity.py [--output DIR] [--raw DIR]

Writes the canonical ledger ``outputs/tables/qc1_omni_exclusions.csv`` and, under ``--output``
(default ``outputs/qc_sensitivity``):

  population.csv               per satellite/channel: records, isolated fallbacks, ratio envelopes
  perturbation.csv             records QC-1 would exclude under one-at-a-time and joint parameter changes
  sensitivity.csv              5 satellites x 2 grids x 2 statistics x 5 thresholds, scenarios qc_primary/unfiltered
  pairwise.csv                 all 10 satellite pairs for every setting and scenario
  changed_cells.csv            grid cells whose count/mean/median differ between scenarios
  footprint_changes.csv        cells entering or leaving each footprint between scenarios
  cp5_changed_memberships.csv  regional records whose CP5 footprint flags differ between scenarios
  event_cell.csv               the grid cell of each excluded record per scenario and setting (rank, selection, weight)
  grid_reconciliation.csv      qc_primary grids equal the canonical cp4f grids (required, exact)
  event_context.csv            +-30 native records around every excluded record, OMNI and co-located MEPED fields
  unfiltered_grids/            unfiltered cp4f-equivalent grids (input of the omission provenance replay)
  summary.json

The primary analysis is the notebook chain (QC-1 on). The unfiltered scenario re-extracts the same
raw files with ``qc=False`` and is a provenance/sensitivity case only. Raw files are never modified.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import itertools
import json
import sys

import netCDF4
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.aggregate import add_coverage_mask, build_grid_table  # noqa: E402
from saa.grid_flux import prepare_region  # noqa: E402
from saa.integrity import reference_area, reference_centroid, reference_distance  # noqa: E402
from saa.load_poes import (SAT_FILE_TOKEN, _valid_flux, extract_channels_dataframe, file_sha256,  # noqa: E402
                           omni_qc_ledger, open_poes_netcdf)
from saa.magnetic_generality import add_cp5c_footprint_flags  # noqa: E402
from saa.quality import QC1, isolated_fallback_discontinuity  # noqa: E402
from saa.satellite_analysis import run_multisatellite_sensitivity  # noqa: E402
from saa.threshold_analysis import add_cell_area, haversine_km  # noqa: E402

SAT = ["noaa15", "noaa18", "noaa19", "metop01", "metop03"]
P1 = "mep_omni_flux_p1"
CHANNELS = QC1["channels"]
LAT, LON = (-70.0, 20.0), (-100.0, 20.0)
NOTE_04F = ("CP4F multi-satellite footprint-location consistency; same SEM-2/MEPED p1 metadata; "
            "absolute flux NOT cross-calibrated; mep_IFC_on==-1 uninterpreted")  # as in notebook 04f
CONTEXT = ["mep_IFC_on", "mep_omni_flux_flag_fit", "mep_omni_flux_flag_iter_lim", *CHANNELS, "mep_omni_gamma_p1",
           "mep_omni_gamma_p2", "mep_omni_gamma_p3", "mep_pro_tel0_flux_p6", "mep_pro_tel90_flux_p6",
           "mep_pro_tel0_flux_p5", "mep_pro_tel90_flux_p5", "mep_ele_tel0_flux_e1", "mep_ele_tel90_flux_e1",
           "Btot_sat", "L_IGRF"]


def files(raw: Path, sat: str) -> list[Path]:
    paths = sorted(raw.glob(f"poes_{SAT_FILE_TOKEN[sat]}_202401*_proc.nc"))
    if len(paths) != 31:
        raise RuntimeError(f"{sat}: {len(paths)}/31 January files present")
    return paths


def native_arrays(path: Path) -> dict:
    """Native-order inputs of QC-1 for one file, through the production validity rule."""
    with open_poes_netcdf(str(path)) as ds:
        out = {"time": np.asarray(ds["time"].values).astype("int64"),
               "fit": np.asarray(ds["mep_omni_flux_flag_fit"].values),
               "lat": np.asarray(ds["lat"].values, float), "lon": np.asarray(ds["lon"].values, float),
               "ifc": np.asarray(ds["mep_IFC_on"].values)}
        out["channels"] = {c: _valid_flux(ds, c) for c in CHANNELS}
    lon180 = (out["lon"] + 180) % 360 - 180
    out["in_region"] = (out["lat"] >= LAT[0]) & (out["lat"] <= LAT[1]) & (lon180 >= LON[0]) & (lon180 <= LON[1]) \
        & (out["ifc"] != 1)
    return out


# ---------------------------------------------------------------------------------------------- ledger
def ledger(raw: Path) -> pd.DataFrame:
    rows = []
    for sat in SAT:
        for p in files(raw, sat):
            with open_poes_netcdf(str(p)) as ds:
                led = omni_qc_ledger(ds, str(p), file_sha256(str(p)))
            if len(led):
                led.insert(0, "satellite", sat)
                rows.append(led)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if len(out):
        out["in_region_after_ifc"] = (out.lat.between(*LAT) & out.lon180.between(*LON) & (out.mep_IFC_on != 1))
        out["multi_channel"] = out.channels_triggered > 1
    return out


def event_context(raw: Path, led: pd.DataFrame, half: int = 30) -> pd.DataFrame:
    rows = []
    for r in led.itertuples():
        with netCDF4.Dataset(raw / r.source_file) as nc:
            nc.set_auto_maskandscale(False)
            i0, i1 = max(0, r.native_index - half), min(len(nc["time"]), r.native_index + half + 1)
            t = np.asarray(nc["time"][i0:i1]).astype("int64")
            d = pd.DataFrame({"source_file": r.source_file, "event_native_index": r.native_index,
                              "native_index": np.arange(i0, i1),
                              "offset": np.arange(i0, i1) - r.native_index,
                              "utc": pd.to_datetime(t, unit="ms", utc=True).strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3] + "Z",
                              "gap_s": np.r_[np.nan, np.diff(t) / 1000.0],
                              "lat": np.asarray(nc["lat"][i0:i1], float),
                              "lon180": (np.asarray(nc["lon"][i0:i1], float) + 180) % 360 - 180})
            for v in CONTEXT:
                if v in nc.variables:
                    d[v] = np.asarray(nc[v][i0:i1])
        rows.append(d)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------------------------- population
def population(raw: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ratio envelopes of regular fits and of isolated fallbacks, plus the perturbation study."""
    base = dict(k=QC1["neighbours_per_side"], max_step_seconds=QC1["max_step_seconds"], ratio=QC1["ratio"],
                min_regular_fraction=1.0, require_fallback=True, trigger="any")
    variants = [("adopted rule", {})]
    variants += [(f"ratio {r:g}x", {"ratio": float(r)}) for r in (5, 10, 15, 20, 30, 50, 200, 500, 1000, 2000, 3000)]
    variants += [(f"{k} neighbours per side", {"k": k}) for k in (3, 5, 7, 15, 20, 30)]
    variants += [(f"max step {s:g} s", {"max_step_seconds": s}) for s in (3.0, 10.0, 20.0)]
    variants += [(f"regular-fit neighbours >= {f:.0%}", {"min_regular_fraction": f}) for f in (0.9, 0.75, 0.5)]
    variants += [("no regular-fit neighbour requirement", {"min_regular_fraction": 0.0}),
                 ("fallback fit not required", {"require_fallback": False}),
                 ("trigger on p1 only", {"trigger": "p1"}), ("trigger on all channels", {"trigger": "all"}),
                 ("no fit conditions (pure two-sided ratio)", {"min_regular_fraction": 0.0, "require_fallback": False})]
    variants += [(f"ratio {r:g}x, {k} neighbours", {"ratio": float(r), "k": k}) for r in (10, 20, 30) for k in (5, 20)]
    pop, flagged = [], {name: [] for name, _ in variants}
    for sat in SAT:
        acc = {c: dict(records=0, region_records=0, region_regular_neighbourhood=0, isolated_fallback=0,
                       isolated_fallback_region=0, regular_evaluable=0, regular_max=0.0, fallback_ratios=[])
               for c in CHANNELS}
        for p in files(raw, sat):
            a = native_arrays(p)
            prod = isolated_fallback_discontinuity(a["time"], a["fit"], a["channels"])
            reg = isolated_fallback_discontinuity(a["time"], a["fit"], a["channels"], require_fallback=False)
            fit0 = np.asarray(a["fit"]) == 0
            for c in CHANNELS:
                s = acc[c]
                s["records"] += len(a["fit"])
                s["region_records"] += int(a["in_region"].sum())
                s["region_regular_neighbourhood"] += int((reg.evaluable & a["in_region"]).sum())
                iso = prod.evaluable & np.isfinite(prod.ratio_left[c])
                s["isolated_fallback"] += int(iso.sum())
                s["isolated_fallback_region"] += int((iso & a["in_region"]).sum())
                s["fallback_ratios"] += np.fmin(prod.ratio_left[c][iso], prod.ratio_right[c][iso]).tolist()
                r0 = fit0 & np.isfinite(reg.ratio_left[c])
                s["regular_evaluable"] += int(r0.sum())
                if r0.any():
                    s["regular_max"] = max(s["regular_max"], float(np.fmin(reg.ratio_left[c][r0], reg.ratio_right[c][r0]).max()))
            for name, ov in variants:
                kw = {**base, **ov}
                chans = {P1: a["channels"][P1]} if kw.pop("trigger") == "p1" else a["channels"]
                trig = "all" if ov.get("trigger") == "all" else "any"
                m = isolated_fallback_discontinuity(a["time"], a["fit"], chans, trigger=trig, **kw).excluded
                for i in np.flatnonzero(m):
                    flagged[name].append((sat, p.name, int(i), bool(a["in_region"][i])))
        for c in CHANNELS:
            s = acc[c]
            fr = np.sort(np.asarray(s.pop("fallback_ratios")))
            flagged_here = fr > QC1["ratio"]
            kept = fr[~flagged_here]
            pop.append({"satellite": sat, "channel": c, **s, "isolated_fallback_flagged": int(flagged_here.sum()),
                        "fallback_ratio_median": float(np.median(fr)) if len(fr) else np.nan,
                        "fallback_ratio_q99": float(np.quantile(fr, 0.99)) if len(fr) else np.nan,
                        "fallback_ratio_max_kept": float(kept.max()) if len(kept) else np.nan,
                        "flagged_ratio_min": float(fr[flagged_here].min()) if flagged_here.any() else np.nan})
    adopted = sorted(flagged["adopted rule"])
    pert = []
    for name, ov in variants:
        f = sorted(flagged[name])
        region = [x for x in f if x[3]]
        pert.append({"variant": name, **{k: str(v) for k, v in {**base, **ov}.items()},
                     "excluded_global": len(f), "excluded_in_region": len(region),
                     "same_set_as_adopted": f == adopted,
                     "records_in_region": ";".join(f"{s}:{n}:{i}" for s, n, i, _ in region[:15])
                     + (";..." if len(region) > 15 else "")})
    return pd.DataFrame(pop), pd.DataFrame(pert)


# ---------------------------------------------------------------------------------------------- science impact
def regions(raw: Path, qc: bool) -> dict:
    out = {}
    for sat in SAT:
        frames = []
        for p in files(raw, sat):
            with open_poes_netcdf(str(p)) as ds:
                d = extract_channels_dataframe(ds, str(p), channels=[P1], qc=qc)
            d["source_sha256"] = file_sha256(str(p))
            d["native_index"] = np.arange(len(d))
            frames.append(d)
        out[sat], _ = prepare_region(pd.concat(frames, ignore_index=True))
    return out


def grids_for(region: pd.DataFrame) -> dict:
    return {gd: add_coverage_mask(build_grid_table(region, lat_step=float(gd), lon_step=float(gd)), 30,
                                  f"enough_samples_{gd}deg") for gd in (5, 2)}


def science(raw: Path, out: Path, tables: Path) -> dict:
    scen = {"qc_primary": regions(raw, True), "unfiltered": regions(raw, False)}
    grids = {s: {sat: grids_for(r) for sat, r in reg.items()} for s, reg in scen.items()}
    recon, sens_rows, pairs, changed, fp, cp5 = [], [], [], [], [], []
    (out / "unfiltered_grids").mkdir(parents=True, exist_ok=True)
    for sat in SAT:
        for gd in (5, 2):
            canon = pd.read_parquet(tables / f"cp4f_{sat}_2024-01_grid_{gd}deg.parquet")
            try:
                pd.testing.assert_frame_equal(grids["qc_primary"][sat][gd], canon, check_exact=True)
                ok = True
            except AssertionError:
                ok = False
            recon.append({"satellite": sat, "grid_deg": gd, "qc_primary_equals_canonical": ok})
            grids["unfiltered"][sat][gd].to_parquet(out / "unfiltered_grids" / f"cp4f_{sat}_2024-01_grid_{gd}deg.parquet",
                                                    index=False)
            a, b = grids["unfiltered"][sat][gd], grids["qc_primary"][sat][gd]
            m = a.merge(b, on=["lat_bin_center", "lon_bin_center"], suffixes=("_unfiltered", "_qc"))
            diff = (m.sample_count_unfiltered != m.sample_count_qc) | ~np.isclose(m.mean_flux_unfiltered, m.mean_flux_qc,
                                                                                   rtol=0, atol=0, equal_nan=True)
            for r in m.loc[diff].itertuples():
                changed.append({"satellite": sat, "grid_deg": gd, "lat": r.lat_bin_center, "lon": r.lon_bin_center,
                                "count_unfiltered": r.sample_count_unfiltered, "count_qc": r.sample_count_qc,
                                "mean_unfiltered": r.mean_flux_unfiltered, "mean_qc": r.mean_flux_qc,
                                "median_unfiltered": r.median_flux_unfiltered, "median_qc": r.median_flux_qc})
    for s in scen:
        specs = [{"satellite": sat, "note": NOTE_04F, "grids": [
            {"grid_deg": gd, "step": float(gd), "table": grids[s][sat][gd], "mask_col": f"enough_samples_{gd}deg",
             "coverage_threshold": 30} for gd in (5, 2)]} for sat in SAT]
        sens = run_multisatellite_sensitivity(specs)
        sens.insert(0, "scenario", s)
        sens_rows.append(sens)
        for (gd, stat, thr), sub in sens.groupby(["grid_deg", "statistic_used", "threshold_label"]):
            for (_, x), (_, y) in itertools.combinations(sub.iterrows(), 2):
                c = (x.centroid_lat_flux_weighted, x.centroid_lon_flux_weighted, y.centroid_lat_flux_weighted,
                     y.centroid_lon_flux_weighted)
                d = haversine_km(*c)
                np.testing.assert_allclose(d, reference_distance(*c), rtol=1e-12, atol=1e-9)
                pairs.append({"scenario": s, "grid_deg": gd, "statistic": stat, "threshold": thr,
                              "satellite_a": x.satellite, "satellite_b": y.satellite, "distance_km": d})
    sens = pd.concat(sens_rows, ignore_index=True)
    # independent recomputation of every footprint's area and centroid from its grid
    for r in sens.itertuples():
        g = add_cell_area(grids[r.scenario][r.satellite][r.grid_deg], r.grid_deg, r.grid_deg)
        cov = g.loc[g[f"enough_samples_{r.grid_deg}deg"]]
        sel = cov.loc[cov[r.statistic_used] >= r.flux_cutoff_value]
        area = reference_area(sel.lat_bin_center.to_numpy(), r.grid_deg)
        lat, lon = reference_centroid(sel.lat_bin_center, sel.lon_bin_center, sel[r.statistic_used], area)
        np.testing.assert_allclose([area.sum(), lat, lon],
                                   [r.selected_area_km2, r.centroid_lat_flux_weighted, r.centroid_lon_flux_weighted],
                                   rtol=1e-12, atol=1e-10)
    # footprint membership changes
    for sat in SAT:
        for gd in (5, 2):
            for stat in ("mean_flux", "median_flux"):
                for thr in ("top20", "top10", "top5", "top2", "top1"):
                    cells = {}
                    for s in scen:
                        r = sens[(sens.scenario == s) & (sens.satellite == sat) & (sens.grid_deg == gd)
                                 & (sens.statistic_used == stat) & (sens.threshold_label == thr)].iloc[0]
                        g = grids[s][sat][gd]
                        cov = g.loc[g[f"enough_samples_{gd}deg"]]
                        cells[s] = set(map(tuple, cov.loc[cov[stat] >= r.flux_cutoff_value,
                                                          ["lat_bin_center", "lon_bin_center"]].to_numpy()))
                    for cell in sorted(cells["unfiltered"] ^ cells["qc_primary"]):
                        fp.append({"satellite": sat, "grid_deg": gd, "statistic": stat, "threshold": thr,
                                   "lat": cell[0], "lon": cell[1], "in_unfiltered": cell in cells["unfiltered"],
                                   "in_qc_primary": cell in cells["qc_primary"]})
        reg = scen["unfiltered"][sat]
        fa = add_cp5c_footprint_flags(reg, grid5=grids["unfiltered"][sat][5], grid2=grids["unfiltered"][sat][2])
        fb = add_cp5c_footprint_flags(reg, grid5=grids["qc_primary"][sat][5], grid2=grids["qc_primary"][sat][2])
        for col in [c for c in fa.columns if c.startswith("in_top")]:
            ch = fa[col] != fb[col]
            c = reg.loc[ch, ["source_sha256", "native_index", "time", "lat", "lon180"]].copy()
            c.insert(0, "satellite", sat)
            c["footprint"] = col
            c["in_unfiltered"] = fa.loc[ch, col]
            c["in_qc_primary"] = fb.loc[ch, col]
            cp5.append(c)
    cp5 = pd.concat(cp5, ignore_index=True)
    changed = pd.DataFrame(changed)
    for name, frame in (("grid_reconciliation", pd.DataFrame(recon)), ("sensitivity", sens), ("pairwise", pd.DataFrame(pairs)),
                        ("changed_cells", changed), ("footprint_changes", pd.DataFrame(fp)),
                        ("cp5_changed_memberships", cp5)):
        frame.to_csv(out / f"{name}.csv", index=False)
    if not pd.DataFrame(recon).qc_primary_equals_canonical.all():
        raise SystemExit("qc_primary grids differ from the canonical cp4f grids: rerun notebooks 02-05c first")
    key = ["satellite", "grid_deg", "statistic_used", "threshold_label"]
    canon_sens = pd.read_parquet(tables / "cp4f_multisatellite_threshold_sensitivity.parquet")
    canon_sens = canon_sens.sort_values(key).reset_index(drop=True)
    mine = sens[sens.scenario == "qc_primary"].drop(columns="scenario")[canon_sens.columns]
    pd.testing.assert_frame_equal(mine.sort_values(key).reset_index(drop=True), canon_sens, check_exact=True)
    return {"scen": scen, "grids": grids, "sens": sens, "pairs": pd.DataFrame(pairs), "fp": pd.DataFrame(fp),
            "changed": changed, "cp5": cp5}


def impact_columns(led: pd.DataFrame, sci: dict) -> pd.DataFrame:
    """Per excluded record: its 5 deg cell before/after, principal footprint and centroid effects."""
    led = led.copy()
    sens, pairs = sci["sens"], sci["pairs"]
    for i, r in led.iterrows():
        if not r.in_region_after_ifc:
            continue
        sat = r.satellite
        la = LAT[0] + (np.floor((r.lat - LAT[0]) / 5) + 0.5) * 5
        lo = LON[0] + (np.floor((r.lon180 - LON[0]) / 5) + 0.5) * 5
        for s, tag in (("unfiltered", "unfiltered"), ("qc_primary", "qc")):
            g = sci["grids"][s][sat][5]
            cov = g.loc[g.enough_samples_5deg]
            cell = cov.loc[(cov.lat_bin_center == la) & (cov.lon_bin_center == lo)]
            if len(cell):
                c = cell.iloc[0]
                led.loc[i, f"cell5_count_{tag}"] = int(c.sample_count)
                led.loc[i, f"cell5_mean_{tag}"] = c.mean_flux
                led.loc[i, f"cell5_median_{tag}"] = c.median_flux
                led.loc[i, f"cell5_mean_rank_{tag}"] = int(cov.mean_flux.rank(method="min", ascending=False).loc[c.name])
        led.loc[i, "cell5_lat"], led.loc[i, "cell5_lon"] = la, lo
        fp = sci["fp"]
        led.loc[i, "principal_footprint_cells_changed"] = int(((fp.satellite == sat) & (fp.grid_deg == 5)
                                                                & (fp.statistic == "mean_flux") & (fp.threshold == "top10")).sum())
        pr = sens[(sens.satellite == sat) & (sens.grid_deg == 5) & (sens.statistic_used == "mean_flux")
                  & (sens.threshold_label == "top10")].set_index("scenario")
        led.loc[i, "principal_centroid_shift_km"] = haversine_km(
            pr.loc["unfiltered", "centroid_lat_flux_weighted"], pr.loc["unfiltered", "centroid_lon_flux_weighted"],
            pr.loc["qc_primary", "centroid_lat_flux_weighted"], pr.loc["qc_primary", "centroid_lon_flux_weighted"])
        pp = pairs[(pairs.grid_deg == 5) & (pairs.statistic == "mean_flux") & (pairs.threshold == "top10")]
        led.loc[i, "max_spread_unfiltered_km"] = pp[pp.scenario == "unfiltered"].distance_km.max()
        led.loc[i, "max_spread_qc_km"] = pp[pp.scenario == "qc_primary"].distance_km.max()
        led.loc[i, "cp5_records_changed_top10_5deg"] = int(((sci["cp5"].satellite == sat)
                                                             & (sci["cp5"].footprint == "in_top10_5deg")).sum())
    return led


def event_cells(led: pd.DataFrame, sci: dict) -> pd.DataFrame:
    """The grid cell of every excluded in-region record, per scenario and setting."""
    rows = []
    sens = sci["sens"]
    for r in led[led.in_region_after_ifc].itertuples():
        for s in ("unfiltered", "qc_primary"):
            for gd in (5, 2):
                la = LAT[0] + (np.floor((r.lat - LAT[0]) / gd) + 0.5) * gd
                lo = LON[0] + (np.floor((r.lon180 - LON[0]) / gd) + 0.5) * gd
                g = add_cell_area(sci["grids"][s][r.satellite][gd], gd, gd)
                cov = g.loc[g[f"enough_samples_{gd}deg"]]
                cell = cov.loc[(cov.lat_bin_center == la) & (cov.lon_bin_center == lo)].iloc[0]
                for stat in ("mean_flux", "median_flux"):
                    for thr in ("top20", "top10", "top5", "top2", "top1"):
                        x = sens[(sens.scenario == s) & (sens.satellite == r.satellite) & (sens.grid_deg == gd)
                                 & (sens.statistic_used == stat) & (sens.threshold_label == thr)].iloc[0]
                        selected = bool(cell[stat] >= x.flux_cutoff_value)
                        rows.append({"satellite": r.satellite, "native_index": r.native_index, "scenario": s,
                                     "grid_deg": gd, "statistic": stat, "threshold": thr, "lat": la, "lon": lo,
                                     "count": int(cell.sample_count), "mean": cell.mean_flux, "median": cell.median_flux,
                                     "descending_rank": int(cov[stat].rank(method="min", ascending=False).loc[cell.name]),
                                     "selected": selected,
                                     "cell_centroid_weight": (cell[stat] * cell.cell_area_km2 / x.total_flux_area_proxy
                                                              if selected else 0.0)})
    return pd.DataFrame(rows)


def single_record_flags(led: pd.DataFrame, ctx: pd.DataFrame) -> pd.DataFrame:
    """Is the departure confined to the record itself (adjacent records within the regular-fit envelope)?"""
    led = led.copy()
    for i, r in led.iterrows():
        c = ctx[(ctx.source_file == r.source_file) & (ctx.event_native_index == r.native_index)].set_index("offset")
        nb = c.loc[[-1, 1], P1].to_numpy(float)
        med = np.median(c.loc[list(range(-10, 0)) + list(range(1, 11)), P1].to_numpy(float))
        led.loc[i, "adjacent_p1_over_neighbour_median_max"] = float(np.max(nb / med))
        led.loc[i, "single_record"] = bool(np.all(nb / med < 3.5) and (c.loc[[-1, 1], "mep_omni_flux_flag_fit"] == 0).all())
    return led


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path("outputs/qc_sensitivity"))
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--tables", type=Path, default=Path("outputs/tables"))
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    led = ledger(a.raw)
    ctx = event_context(a.raw, led)
    ctx.to_csv(a.output / "event_context.csv", index=False)
    pop, pert = population(a.raw)
    pop.to_csv(a.output / "population.csv", index=False)
    pert.to_csv(a.output / "perturbation.csv", index=False)
    sci = science(a.raw, a.output, a.tables)
    led = single_record_flags(impact_columns(led, sci), ctx)
    event_cells(led, sci).to_csv(a.output / "event_cell.csv", index=False)
    led.to_csv(a.tables / "qc1_omni_exclusions.csv", index=False)
    led.to_csv(a.output / "qc1_omni_exclusions.csv", index=False)
    pp = sci["pairs"]
    principal = pp[(pp.grid_deg == 5) & (pp.statistic == "mean_flux") & (pp.threshold == "top10")]
    summary = {"rule": QC1, "excluded_records_global": int(len(led)),
               "excluded_records_in_region": int(led.in_region_after_ifc.sum()) if len(led) else 0,
               "excluded_channel_values_in_analysed_combinations": None,
               "max_principal_spread_km": principal.groupby("scenario").distance_km.max().to_dict(),
               "perturbation_variants_with_adopted_set": int(pert.same_set_as_adopted.sum()),
               "perturbation_variants": int(len(pert))}
    analysed = {"noaa19": CHANNELS}
    n = 0
    for r in led.itertuples():
        if r.in_region_after_ifc:
            n += len(analysed.get(r.satellite, [P1]))
    summary["excluded_channel_values_in_analysed_combinations"] = n
    (a.output / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
