#!/usr/bin/env python3
"""Validate Checkpoint 4D time-window-sensitivity outputs.

Checks (against real data; nothing fabricated):

* the 31 NOAA-19 Jan-2024 raw daily files exist (or report missing)
* all 8 expected window labels are present in the sensitivity table
* grid tables exist for every window x {5deg, 2deg} (16) with required columns + coverage mask
* the cumulative regional processed Parquets exist
* the time-window threshold sensitivity table (CSV + Parquet) exists with required columns and 160 rows
* selected_cell_count > 0 and selected_area_km2 > 0 for every row
* both centroids are inside the analysis region
* coverage_threshold_used and coverage_warning columns exist and are populated
* the eleven required figures exist and are non-empty
* the notebook was executed
* no fake data: the full-month window reproduces CP4A coverage (432 / 2685); the one-day window is
  honestly flagged orbit-track sparse

Exit 0 if all pass.  Usage: python scripts/validate_cp4d_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.aggregate import GRID_COLUMNS  # noqa: E402
from saa.time_window_analysis import TIME_WINDOW_SENSITIVITY_COLUMNS, TIME_WINDOWS  # noqa: E402

RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
NB = ROOT / "notebooks" / "04d_time_window_sensitivity.ipynb"

WINDOW_LABELS = [w["window_label"] for w in TIME_WINDOWS]
SENS_CSV = TBL / "cp4d_time_window_threshold_sensitivity.csv"
SENS_PARQ = TBL / "cp4d_time_window_threshold_sensitivity.parquet"
CUM_PARQUETS = [
    "cp4d_noaa19_2024-01-01_mep_omni_flux_p1_region.parquet",
    "cp4d_noaa19_2024-01-01_to_07_mep_omni_flux_p1_region.parquet",
    "cp4d_noaa19_2024-01-01_to_14_mep_omni_flux_p1_region.parquet",
    "cp4d_noaa19_2024-01_full_month_mep_omni_flux_p1_region.parquet",
]
FIGS = [
    "cp4d_mean_flux_5deg_day_2024-01-01.png",
    "cp4d_mean_flux_5deg_days_2024-01-01_to_07.png",
    "cp4d_mean_flux_5deg_days_2024-01-01_to_14.png",
    "cp4d_mean_flux_5deg_month_2024-01.png",
    "cp4d_sample_count_5deg_time_windows.png",
    "cp4d_sample_count_2deg_time_windows.png",
    "cp4d_centroid_by_time_window_top10.png",
    "cp4d_centroid_by_time_window_top5.png",
    "cp4d_area_by_time_window.png",
    "cp4d_weekly_centroid_comparison.png",
    "cp4d_weekly_mean_flux_5deg_comparison.png",
]
LAT_RANGE, LON_RANGE = (-70, 20), (-100, 20)
EXPECTED_RAW = [f"poes_n19_202401{d:02d}_proc.nc" for d in range(1, 32)]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    add = lambda n, ok, d="": checks.append((n, bool(ok), d))  # noqa: E731

    # 1) raw daily files
    present = sum((RAW / f).exists() for f in EXPECTED_RAW)
    missing = [f for f in EXPECTED_RAW if not (RAW / f).exists()]
    add("31 NOAA-19 Jan-2024 raw files present", present == 31,
        f"{present}/31" + ("" if not missing else f"; missing {missing}"))

    # 2) cumulative regional parquets
    for f in CUM_PARQUETS:
        p = PROC / f
        add(f"regional parquet exists: {f}", p.exists() and p.stat().st_size > 1000,
            f"{p.stat().st_size} B" if p.exists() else "MISSING")

    # 3) grid tables x 8 windows x 2 res
    for label in WINDOW_LABELS:
        for res, mask_col in [("5deg", "enough_samples_5deg"), ("2deg", "enough_samples_2deg")]:
            p = TBL / f"cp4d_{label}_grid_{res}.parquet"
            if not p.exists():
                add(f"grid table exists: {label} {res}", False, "MISSING"); continue
            g = pd.read_parquet(p)
            miss = [c for c in GRID_COLUMNS if c not in g.columns]
            ok = (not miss) and (mask_col in g.columns)
            add(f"grid table ok: {label} {res}", ok, "cols ok + mask" if ok else f"missing {miss or mask_col}")

    # 4) sensitivity table
    add("sensitivity CSV exists", SENS_CSV.exists(), SENS_CSV.name)
    if not SENS_PARQ.exists():
        add("sensitivity Parquet exists", False, "MISSING"); return _report(checks)
    add("sensitivity Parquet exists", True, SENS_PARQ.name)
    sens = pd.read_parquet(SENS_PARQ)
    miss = [c for c in TIME_WINDOW_SENSITIVITY_COLUMNS if c not in sens.columns]
    add("sensitivity has required columns", not miss, "all present" if not miss else f"missing {miss}")
    add("sensitivity has 160 rows", len(sens) == 160, f"{len(sens)} rows")
    add("all 8 windows present", set(sens["window_label"].unique()) == set(WINDOW_LABELS),
        str(sorted(set(sens["window_label"].unique()))))
    add("selected_cell_count > 0 for all", (sens["selected_cell_count"] > 0).all(),
        f"min={int(sens['selected_cell_count'].min())}")
    add("selected_area_km2 > 0 for all", (sens["selected_area_km2"] > 0).all(),
        f"min={sens['selected_area_km2'].min():.3g}")
    inside = (sens["centroid_lat_unweighted"].between(*LAT_RANGE).all()
              and sens["centroid_lon_unweighted"].between(*LON_RANGE).all()
              and sens["centroid_lat_flux_weighted"].between(*LAT_RANGE).all()
              and sens["centroid_lon_flux_weighted"].between(*LON_RANGE).all())
    add("centroids inside analysis region", inside)
    add("coverage_threshold_used populated", sens["coverage_threshold_used"].notna().all()
        and (sens["coverage_threshold_used"] > 0).all(),
        f"values {sorted(sens['coverage_threshold_used'].unique())}")
    add("coverage_warning column present", "coverage_warning" in sens.columns,
        f"{int((sens['coverage_warning'].str.len() > 0).sum())} rows flagged")

    # 5) no fake data: month reproduces CP4A coverage; one-day flagged sparse
    m5 = sens[(sens.window_label == "month_2024-01") & (sens.grid_deg == 5)]["cells_available_after_coverage_mask"].unique()
    m2 = sens[(sens.window_label == "month_2024-01") & (sens.grid_deg == 2)]["cells_available_after_coverage_mask"].unique()
    add("full-month coverage matches CP4A (no fake data)", set(m5) == {432} and set(m2) == {2685},
        f"5deg {set(m5)}, 2deg {set(m2)}")
    day_flag = sens[sens.window_label == "day_2024-01-01"]["coverage_warning"].str.contains("one-day").all()
    add("one-day window honestly flagged sparse", bool(day_flag))

    # 6) figures
    for fig in FIGS:
        p = FIG / fig
        add(f"figure exists: {fig}", p.exists() and p.stat().st_size > 1000,
            f"{p.stat().st_size} B" if p.exists() else "MISSING")

    # 7) notebook executed
    if NB.exists():
        nb = json.loads(NB.read_text())
        codecells = [c for c in nb["cells"] if c.get("cell_type") == "code"]
        add("notebook executed (cells have outputs)",
            bool(codecells) and all(c.get("outputs") for c in codecells),
            f"{sum(1 for c in codecells if c.get('outputs'))}/{len(codecells)} with outputs")
    else:
        add("notebook executed (cells have outputs)", False, "missing")

    return _report(checks)


def _report(checks: list[tuple[str, bool, str]]) -> int:
    print("=" * 72)
    print("CHECKPOINT 4D OUTPUT VALIDATION")
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
