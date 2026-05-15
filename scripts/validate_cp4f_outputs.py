#!/usr/bin/env python3
"""Validate Checkpoint 4F multi-satellite footprint-consistency outputs.

Checks (against real data; nothing fabricated):

* the CP4E audit table exists (the reused starting point)
* the CP4F compatibility table exists with an included/excluded verdict
* at least NOAA-18 and NOAA-19 are included
* every included satellite has a real monthly regional Parquet + 5deg/2deg grid tables
  (required grid columns + coverage mask)
* the multi-satellite threshold sensitivity table exists with required columns
* its row count == included_satellite_count x 2 grids x 2 stats x 5 thresholds
* absolute_flux_comparison_allowed is False on every row
* selected_cell_count > 0 and selected_area_km2 > 0 for every row
* both centroids are inside the analysis region
* the pairwise centroid-distance table exists with required columns
* the required figures exist and are non-empty (per-satellite maps + overlays + centroid + heatmap)
* the notebook was executed
* no fake data: NOAA-19 coverage reproduces CP4A (432 / 2685)

Exit 0 if all pass.  Usage: python scripts/validate_cp4f_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.aggregate import GRID_COLUMNS  # noqa: E402
from saa.satellite_analysis import MULTISAT_SENSITIVITY_COLUMNS, PAIRWISE_DISTANCE_COLUMNS  # noqa: E402

PROC = ROOT / "data" / "processed"
TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
NB = ROOT / "notebooks" / "04f_multisatellite_consistency.ipynb"

CP4E_AUDIT = TBL / "cp4e_satellite_availability_audit.parquet"
COMPAT = TBL / "cp4f_satellite_compatibility.parquet"
SENS_CSV = TBL / "cp4f_multisatellite_threshold_sensitivity.csv"
SENS_PARQ = TBL / "cp4f_multisatellite_threshold_sensitivity.parquet"
PAIR_CSV = TBL / "cp4f_pairwise_centroid_distances.csv"
PAIR_PARQ = TBL / "cp4f_pairwise_centroid_distances.parquet"
LAT_RANGE, LON_RANGE = (-70, 20), (-100, 20)


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    add = lambda n, ok, d="": checks.append((n, bool(ok), d))  # noqa: E731

    add("CP4E audit exists (reused starting point)", CP4E_AUDIT.exists(), CP4E_AUDIT.name)
    if not COMPAT.exists():
        add("CP4F compatibility table exists", False, "MISSING"); return _report(checks)
    add("CP4F compatibility table exists", True, COMPAT.name)
    compat = pd.read_parquet(COMPAT)
    add("compatibility table has included flag", "cp4f_included" in compat.columns)
    included = sorted(compat.loc[compat.cp4f_included, "satellite"]) if "cp4f_included" in compat.columns else []
    add("NOAA-18 and NOAA-19 included", {"noaa18", "noaa19"}.issubset(set(included)), str(included))

    if not SENS_PARQ.exists():
        add("sensitivity table exists", False, "MISSING"); return _report(checks)
    sens = pd.read_parquet(SENS_PARQ)
    sat_in_table = sorted(sens.satellite.unique())

    # per-satellite processed + grid tables
    for sat in sat_in_table:
        rp = PROC / f"cp4f_{sat}_2024-01_mep_omni_flux_p1_region.parquet"
        add(f"regional parquet exists: {sat}", rp.exists() and rp.stat().st_size > 1000,
            f"{rp.stat().st_size} B" if rp.exists() else "MISSING")
        for res, mask_col in [("5deg", "enough_samples_5deg"), ("2deg", "enough_samples_2deg")]:
            p = TBL / f"cp4f_{sat}_2024-01_grid_{res}.parquet"
            if not p.exists():
                add(f"grid table exists: {sat} {res}", False, "MISSING"); continue
            g = pd.read_parquet(p)
            m = [c for c in GRID_COLUMNS if c not in g.columns]
            add(f"grid table ok: {sat} {res}", (not m) and (mask_col in g.columns),
                "cols ok + mask" if (not m and mask_col in g.columns) else f"missing {m or mask_col}")

    # sensitivity table
    add("sensitivity CSV exists", SENS_CSV.exists(), SENS_CSV.name)
    m = [c for c in MULTISAT_SENSITIVITY_COLUMNS if c not in sens.columns]
    add("sensitivity has required columns", not m, "all present" if not m else f"missing {m}")
    expected = len(sat_in_table) * 2 * 2 * 5
    add(f"sensitivity row count == included x 20", len(sens) == expected, f"{len(sens)} (expected {expected})")
    add("absolute_flux_comparison_allowed is False for all",
        (sens.absolute_flux_comparison_allowed == False).all(),  # noqa: E712
        str(sorted(sens.absolute_flux_comparison_allowed.unique())))
    add("selected_cell_count > 0 for all", (sens.selected_cell_count > 0).all(),
        f"min={int(sens.selected_cell_count.min())}")
    add("selected_area_km2 > 0 for all", (sens.selected_area_km2 > 0).all(),
        f"min={sens.selected_area_km2.min():.3g}")
    inside = (sens.centroid_lat_unweighted.between(*LAT_RANGE).all()
              and sens.centroid_lon_unweighted.between(*LON_RANGE).all()
              and sens.centroid_lat_flux_weighted.between(*LAT_RANGE).all()
              and sens.centroid_lon_flux_weighted.between(*LON_RANGE).all())
    add("centroids inside analysis region", inside)

    # no fake data: NOAA-19 coverage reproduces CP4A
    if "noaa19" in sat_in_table:
        n5 = set(sens[(sens.satellite == "noaa19") & (sens.grid_deg == 5)]["cells_available_after_coverage_mask"])
        n2 = set(sens[(sens.satellite == "noaa19") & (sens.grid_deg == 2)]["cells_available_after_coverage_mask"])
        add("NOAA-19 coverage matches CP4A (no fake data)", n5 == {432} and n2 == {2685},
            f"5deg {n5}, 2deg {n2}")

    # pairwise distances
    if not PAIR_PARQ.exists():
        add("pairwise distance table exists", False, "MISSING")
    else:
        add("pairwise distance table exists (CSV+Parquet)", PAIR_CSV.exists() and PAIR_PARQ.exists())
        pw = pd.read_parquet(PAIR_PARQ)
        mp = [c for c in PAIRWISE_DISTANCE_COLUMNS if c not in pw.columns]
        add("pairwise table has required columns", not mp, "all present" if not mp else f"missing {mp}")
        add("pairwise distances non-negative", (pw.distance_km >= 0).all(), f"max={pw.distance_km.max():.0f} km")

    # figures
    figs = []
    for sat in sat_in_table:
        figs += [f"cp4f_{sat}_mean_flux_5deg.png", f"cp4f_{sat}_sample_count_5deg.png"]
    figs += [
        "cp4f_multisatellite_top10_5deg_mean_overlay.png", "cp4f_multisatellite_top10_2deg_mean_overlay.png",
        "cp4f_multisatellite_top5_5deg_mean_overlay.png", "cp4f_multisatellite_top5_2deg_mean_overlay.png",
        "cp4f_multisatellite_centroid_comparison_top10_top5.png",
        "cp4f_pairwise_centroid_distance_top10_5deg_mean.png",
    ]
    for f in figs:
        p = FIG / f
        add(f"figure exists: {f}", p.exists() and p.stat().st_size > 1000,
            f"{p.stat().st_size} B" if p.exists() else "MISSING")

    # notebook executed
    if NB.exists():
        nb = json.loads(NB.read_text())
        cc = [c for c in nb["cells"] if c.get("cell_type") == "code"]
        add("notebook executed (cells have outputs)", bool(cc) and all(c.get("outputs") for c in cc),
            f"{sum(1 for c in cc if c.get('outputs'))}/{len(cc)} with outputs")
    else:
        add("notebook executed (cells have outputs)", False, "missing")

    return _report(checks)


def _report(checks: list[tuple[str, bool, str]]) -> int:
    print("=" * 72)
    print("CHECKPOINT 4F OUTPUT VALIDATION")
    print("=" * 72)
    all_ok = True
    for name, ok, detail in checks:
        all_ok &= ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ->  {detail}" if detail else ""))
    print("-" * 72)
    print("RESULT:", "ALL CHECKS PASSED" if all_ok else "ONE OR MORE CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
