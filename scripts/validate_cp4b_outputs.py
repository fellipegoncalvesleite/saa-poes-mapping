#!/usr/bin/env python3
"""Validate Checkpoint 4B threshold-sensitivity outputs.

Checks (against real CP4A inputs; nothing fabricated):

* CP4A 5deg/2deg grid tables exist (the real inputs)
* the threshold sensitivity CSV and Parquet exist
* the sensitivity table has the required columns
* it has exactly 20 rows (2 grids x 2 statistics x 5 thresholds)
* selected_cell_count > 0 for every threshold
* selected_area_km2 > 0 for every threshold (area, not raw count)
* both centroids (unweighted + flux-weighted) are inside the analysis region
* flux_cutoff_value is finite for every row
* the five required figures exist and are non-empty
* the notebook was executed (has cell outputs)
* no fake data: cells_available_after_coverage_mask matches the real CP4A coverage-passed counts

Exit 0 if all pass, 1 otherwise.  Usage: python scripts/validate_cp4b_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.threshold_analysis import SENSITIVITY_COLUMNS, coverage_passed  # noqa: E402

TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
T5 = TBL / "cp4a_noaa19_2024-01_grid_5deg.parquet"
T2 = TBL / "cp4a_noaa19_2024-01_grid_2deg.parquet"
CSV = TBL / "cp4b_threshold_sensitivity.csv"
PARQ = TBL / "cp4b_threshold_sensitivity.parquet"
NB = ROOT / "notebooks" / "04b_threshold_sensitivity.ipynb"
FIGS = [
    "cp4b_threshold_overlay_5deg_mean.png", "cp4b_threshold_overlay_5deg_median.png",
    "cp4b_threshold_overlay_2deg_mean.png", "cp4b_threshold_overlay_2deg_median.png",
    "cp4b_centroid_shift_by_threshold.png",
]
LAT_RANGE, LON_RANGE = (-70, 20), (-100, 20)


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    add = lambda n, ok, d="": checks.append((n, bool(ok), d))  # noqa: E731

    # 1) CP4A inputs exist
    add("CP4A 5deg grid table exists", T5.exists(), T5.name)
    add("CP4A 2deg grid table exists", T2.exists(), T2.name)
    if not (T5.exists() and T2.exists()):
        return _report(checks)

    # 2) sensitivity outputs exist
    add("sensitivity CSV exists", CSV.exists(), CSV.name)
    add("sensitivity Parquet exists", PARQ.exists(), PARQ.name)
    if not PARQ.exists():
        return _report(checks)
    sens = pd.read_parquet(PARQ)

    # 3) required columns
    miss = [c for c in SENSITIVITY_COLUMNS if c not in sens.columns]
    add("sensitivity has required columns", not miss, "all present" if not miss else f"missing {miss}")

    # 4) 20 rows
    add("sensitivity has 20 rows", len(sens) == 20, f"{len(sens)} rows")

    # 5) selected_cell_count > 0
    add("selected_cell_count > 0 for all", (sens["selected_cell_count"] > 0).all(),
        f"min={int(sens['selected_cell_count'].min())}")

    # 6) selected_area_km2 > 0
    add("selected_area_km2 > 0 for all", (sens["selected_area_km2"] > 0).all(),
        f"min={sens['selected_area_km2'].min():.3e} km2")

    # 7) centroids inside region (both unweighted + flux-weighted)
    def inside(latc, lonc):
        return (sens[latc].between(*LAT_RANGE).all() and sens[lonc].between(*LON_RANGE).all())
    uw = inside("centroid_lat_unweighted", "centroid_lon_unweighted")
    fw = inside("centroid_lat_flux_weighted", "centroid_lon_flux_weighted")
    add("centroids inside analysis region", uw and fw,
        f"lat {sens[['centroid_lat_unweighted','centroid_lat_flux_weighted']].min().min():.1f}.."
        f"{sens[['centroid_lat_unweighted','centroid_lat_flux_weighted']].max().max():.1f}")

    # 8) flux cutoffs finite
    add("flux_cutoff_value finite for all", np.isfinite(sens["flux_cutoff_value"]).all())

    # 9) figures exist
    for fig in FIGS:
        p = FIG / fig
        add(f"figure exists: {fig}", p.exists() and p.stat().st_size > 1000,
            f"{p.stat().st_size} bytes" if p.exists() else "MISSING")

    # 10) notebook executed
    if NB.exists():
        nb = json.loads(NB.read_text())
        code = [c for c in nb["cells"] if c.get("cell_type") == "code"]
        add("notebook executed (cells have outputs)",
            bool(code) and all(c.get("outputs") for c in code),
            f"{sum(1 for c in code if c.get('outputs'))}/{len(code)} code cells with outputs")
    else:
        add("notebook executed (cells have outputs)", False, "notebook missing")

    # 11) no fake data: available-cell counts match the real CP4A coverage-passed counts
    real5 = len(coverage_passed(pd.read_parquet(T5), "enough_samples_5deg"))
    real2 = len(coverage_passed(pd.read_parquet(T2), "enough_samples_2deg"))
    av5 = set(sens.loc[sens.grid_deg == 5, "cells_available_after_coverage_mask"].unique())
    av2 = set(sens.loc[sens.grid_deg == 2, "cells_available_after_coverage_mask"].unique())
    add("available counts match real CP4A coverage (no fake data)",
        av5 == {real5} and av2 == {real2}, f"5deg {av5} vs {real5}; 2deg {av2} vs {real2}")

    return _report(checks)


def _report(checks: list[tuple[str, bool, str]]) -> int:
    print("=" * 70)
    print("CHECKPOINT 4B OUTPUT VALIDATION")
    print("=" * 70)
    all_ok = True
    for name, ok, detail in checks:
        all_ok &= ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ->  {detail}" if detail else ""))
    print("-" * 70)
    print("RESULT:", "ALL CHECKS PASSED" if all_ok else "ONE OR MORE CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
