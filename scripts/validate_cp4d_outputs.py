#!/usr/bin/env python3
"""Validate Checkpoint 4D.1 time-window-sensitivity outputs.

Checks (against real data; nothing fabricated):

* the 31 NOAA-19 Jan-2024 raw daily files exist (or report missing)
* all 9 expected window labels are present (incl. the 3-day cumulative state),
  with no duplicates and dates/day-counts matching the canonical TIME_WINDOWS
* grid tables exist for every window x {5deg, 2deg} (18) with required columns + coverage mask
* the cumulative regional processed Parquets exist (incl. the new 3-day slice)
* the time-window threshold sensitivity table (CSV + Parquet) exists with required columns
  and 180 rows (9 windows x 2 grids x 2 stats x 5 thresholds)
* selected_cell_count > 0 and selected_area_km2 > 0 for every row
* both centroids are inside the analysis region
* coverage accounting is coherent: passing <= observed <= nominal, nominal matches the
  regional grid, zero-observation and pass fractions are in [0, 1]
* peak-flux coordinates are finite when a peak exists, lie inside the region, match an
  independently recomputed coverage-passed maximum (deterministic tie-break), and the
  tie count is >= 1
* window-to-month stability metrics: full-month identity is exact (distance 0, area
  ratio 1, area difference 0, Jaccard 1); Jaccard is within [0, 1]; the principal-case
  distance and Jaccard are independently recomputed from the grid tables
* coverage_threshold_used values match the canonical rule (incl. floor-bound 3-day)
* the thirteen required figures exist and are non-empty
* the notebook was executed
* no fake data: the full-month window reproduces CP4A coverage (432 / 2685); the one-day
  window is honestly flagged orbit-track sparse

Exit 0 if all pass.  Usage: python scripts/validate_cp4d_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.aggregate import GRID_COLUMNS  # noqa: E402
from saa.threshold_analysis import (  # noqa: E402
    add_cell_area,
    coverage_passed,
    haversine_km,
)
from saa.time_window_analysis import (  # noqa: E402
    TIME_WINDOW_SENSITIVITY_COLUMNS,
    TIME_WINDOWS,
    choose_coverage_threshold,
    region_cell_count,
    window_day_count,
)

RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
NB = ROOT / "notebooks" / "04d_time_window_sensitivity.ipynb"

WINDOW_LABELS = [w["window_label"] for w in TIME_WINDOWS]
WINDOW_DATES = {w["window_label"]: (w["start_date"], w["end_date"]) for w in TIME_WINDOWS}
SENS_CSV = TBL / "cp4d_time_window_threshold_sensitivity.csv"
SENS_PARQ = TBL / "cp4d_time_window_threshold_sensitivity.parquet"
CUM_PARQUETS = [
    "cp4d_noaa19_2024-01-01_mep_omni_flux_p1_region.parquet",
    "cp4d_noaa19_2024-01-01_to_03_mep_omni_flux_p1_region.parquet",
    "cp4d_noaa19_2024-01-01_to_07_mep_omni_flux_p1_region.parquet",
    "cp4d_noaa19_2024-01-01_to_14_mep_omni_flux_p1_region.parquet",
    "cp4d_noaa19_2024-01_full_month_mep_omni_flux_p1_region.parquet",
]
FIGS = [
    "cp4d_mean_flux_5deg_day_2024-01-01.png",
    "cp4d_mean_flux_5deg_days_2024-01-01_to_03.png",
    "cp4d_mean_flux_5deg_days_2024-01-01_to_07.png",
    "cp4d_mean_flux_5deg_days_2024-01-01_to_14.png",
    "cp4d_mean_flux_5deg_month_2024-01.png",
    "cp4d_sample_count_5deg_time_windows.png",
    "cp4d_sample_count_2deg_time_windows.png",
    "cp4d_centroid_by_time_window_top10.png",
    "cp4d_centroid_by_time_window_top5.png",
    "cp4d_area_by_time_window.png",
    "cp4d_stabilization_vs_duration_top10.png",
    "cp4d_weekly_centroid_comparison.png",
    "cp4d_weekly_mean_flux_5deg_comparison.png",
]
LAT_RANGE, LON_RANGE = (-70, 20), (-100, 20)
EXPECTED_RAW = [f"poes_n19_202401{d:02d}_proc.nc" for d in range(1, 32)]


def _selected_keys(grid_path: Path, grid_deg: int, stat: str, cutoff: float) -> set:
    table = add_cell_area(pd.read_parquet(grid_path), grid_deg, grid_deg)
    covered = coverage_passed(table, f"enough_samples_{grid_deg}deg")
    sel = covered[covered[stat] >= cutoff]
    return set(zip(sel["lat_bin_center"].to_numpy(), sel["lon_bin_center"].to_numpy()))


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

    # 3) grid tables x 9 windows x 2 res
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
    add("sensitivity has 180 rows", len(sens) == 180, f"{len(sens)} rows")
    add("all 9 windows present", set(sens["window_label"].unique()) == set(WINDOW_LABELS),
        str(sorted(set(sens["window_label"].unique()))))
    add("no duplicate configuration rows",
        not sens.duplicated(["window_label", "grid_deg", "statistic_used", "threshold_label"]).any())
    add("3-day cumulative state exists",
        (sens["window_label"] == "days_2024-01-01_to_03").any(),
        f"{int((sens['window_label'] == 'days_2024-01-01_to_03').sum())} rows")

    # 4b) window dates / day counts match the canonical definitions
    dates_ok = True
    for label, (start, end) in WINDOW_DATES.items():
        rows = sens[sens["window_label"] == label]
        if not len(rows) == 20:
            dates_ok = False; break
        if not ((rows["start_date"] == start).all() and (rows["end_date"] == end).all()):
            dates_ok = False; break
        if not (rows["day_count"] == window_day_count(start, end)).all():
            dates_ok = False; break
    add("window dates/day counts match canonical TIME_WINDOWS", dates_ok)
    three = sens[sens["window_label"] == "days_2024-01-01_to_03"].iloc[0]
    add("3-day state spans Jan 1-3 (day_count 3)",
        three["start_date"] == "2024-01-01" and three["end_date"] == "2024-01-03"
        and int(three["day_count"]) == 3)

    add("selected_cell_count > 0 for all", (sens["selected_cell_count"] > 0).all(),
        f"min={int(sens['selected_cell_count'].min())}")
    add("selected_area_km2 > 0 for all", (sens["selected_area_km2"] > 0).all(),
        f"min={sens['selected_area_km2'].min():.3g}")
    inside = (sens["centroid_lat_unweighted"].between(*LAT_RANGE).all()
              and sens["centroid_lon_unweighted"].between(*LON_RANGE).all()
              and sens["centroid_lat_flux_weighted"].between(*LAT_RANGE).all()
              and sens["centroid_lon_flux_weighted"].between(*LON_RANGE).all())
    add("centroids inside analysis region", inside)

    # 4c) coverage thresholds follow the canonical rule
    thr_ok = all(
        (sens[sens["window_label"] == label]["coverage_threshold_used"]
         == choose_coverage_threshold(window_day_count(*WINDOW_DATES[label]))).all()
        for label in WINDOW_LABELS)
    add("coverage thresholds match canonical rule", thr_ok,
        f"values {sorted(sens['coverage_threshold_used'].unique())}")
    add("3-day threshold is floor-bound at 3",
        int(three["coverage_threshold_used"]) == 3 == choose_coverage_threshold(3))

    # 4d) coverage accounting: passing <= observed <= nominal; fractions in [0, 1]
    nominal_ok = all(
        (sens[sens["grid_deg"] == gd]["nominal_region_cells"] == region_cell_count(gd)).all()
        for gd in (5, 2))
    add("nominal cells match regional grid (432 / 2700)", nominal_ok)
    nested = ((sens["cells_available_after_coverage_mask"] <= sens["cells_with_observation"]).all()
              and (sens["cells_with_observation"] <= sens["nominal_region_cells"]).all())
    add("passing <= observed <= nominal for all rows", nested)
    fracs = ["zero_observation_fraction", "coverage_pass_fraction",
             "selected_area_fraction_of_covered_region"]
    add("fractions within [0, 1]",
        all(sens[c].between(0, 1).all() for c in fracs))
    add("coverage_warning column present", "coverage_warning" in sens.columns,
        f"{int((sens['coverage_warning'].str.len() > 0).sum())} rows flagged")

    # 4e) peak-flux location: finite, in-region, matches independent recomputation
    peak_finite = sens["peak_flux"].notna().all() \
        and sens["peak_flux_lat"].between(*LAT_RANGE).all() \
        and sens["peak_flux_lon"].between(*LON_RANGE).all() \
        and (sens["peak_flux_tie_count"] >= 1).all()
    add("peak coordinates finite, in-region, tie_count >= 1", bool(peak_finite))
    peak_ok, peak_detail = True, "all principal rows match"
    for label in ["day_2024-01-01", "days_2024-01-01_to_03", "days_2024-01-01_to_07",
                  "days_2024-01-01_to_14", "month_2024-01"]:
        for gd in (5, 2):
            for stat in ("mean_flux", "median_flux"):
                row = sens[(sens.window_label == label) & (sens.grid_deg == gd)
                           & (sens.statistic_used == stat)
                           & (sens.threshold_label == "top10")].iloc[0]
                grid = add_cell_area(
                    pd.read_parquet(TBL / f"cp4d_{label}_grid_{gd}deg.parquet"), gd, gd)
                covered = coverage_passed(grid, f"enough_samples_{gd}deg")
                mx = float(covered[stat].max())
                tied = covered[covered[stat] == mx].sort_values(
                    ["lat_bin_center", "lon_bin_center"]).iloc[0]
                if not (np.isclose(row["peak_flux"], mx, rtol=1e-9, atol=1e-12)
                        and row["peak_flux_lat"] == tied["lat_bin_center"]
                        and row["peak_flux_lon"] == tied["lon_bin_center"]
                        and int(row["peak_flux_tie_count"]) == int((covered[stat] == mx).sum())):
                    peak_ok, peak_detail = False, f"mismatch at {label} {gd}deg {stat}"
                    break
    add("peak location matches independent grid recomputation", peak_ok, peak_detail)

    # 4f) window-to-month stability: exact month identity + independent principal recompute
    month = sens[sens["window_label"] == "month_2024-01"]
    identity = ((month["centroid_distance_to_month_km"] == 0.0).all()
                and (month["selected_area_ratio_to_month"] == 1.0).all()
                and (month["selected_area_difference_to_month_km2"] == 0.0).all()
                and (month["footprint_jaccard_vs_month"] == 1.0).all())
    add("full-month identity metrics exact (0/1/0/1)", bool(identity))
    add("Jaccard within [0, 1]", bool(sens["footprint_jaccard_vs_month"].between(0, 1).all()),
        f"range {sens['footprint_jaccard_vs_month'].min():.3f}..{sens['footprint_jaccard_vs_month'].max():.3f}")
    stab_ok, stab_detail = True, "principal cumulative rows match"
    for label in ["day_2024-01-01", "days_2024-01-01_to_03",
                  "days_2024-01-01_to_07", "days_2024-01-01_to_14"]:
        row = sens[(sens.window_label == label) & (sens.grid_deg == 5)
                   & (sens.statistic_used == "mean_flux")
                   & (sens.threshold_label == "top10")].iloc[0]
        ref = sens[(sens.window_label == "month_2024-01") & (sens.grid_deg == 5)
                   & (sens.statistic_used == "mean_flux")
                   & (sens.threshold_label == "top10")].iloc[0]
        mine = _selected_keys(TBL / f"cp4d_{label}_grid_5deg.parquet", 5,
                              "mean_flux", float(row["flux_cutoff_value"]))
        theirs = _selected_keys(TBL / "cp4d_month_2024-01_grid_5deg.parquet", 5,
                                "mean_flux", float(ref["flux_cutoff_value"]))
        union = mine | theirs
        expected_j = len(mine & theirs) / len(union) if union else float("nan")
        expected_d = haversine_km(float(row["centroid_lat_flux_weighted"]),
                                  float(row["centroid_lon_flux_weighted"]),
                                  float(ref["centroid_lat_flux_weighted"]),
                                  float(ref["centroid_lon_flux_weighted"]))
        if not (np.isclose(row["footprint_jaccard_vs_month"], expected_j, rtol=1e-9, atol=1e-12)
                and np.isclose(row["centroid_distance_to_month_km"], expected_d,
                               rtol=1e-9, atol=1e-12)):
            stab_ok, stab_detail = False, f"mismatch at {label}"
            break
    add("stability metrics match independent grid recomputation", stab_ok, stab_detail)

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
    print("CHECKPOINT 4D.1 OUTPUT VALIDATION")
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
