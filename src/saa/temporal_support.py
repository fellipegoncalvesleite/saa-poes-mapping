"""Temporal coverage versus conditional morphology diagnostics (paper Phase 4B).

Separates two things that the CP4D window-to-month metrics report together:

* **end-to-end agreement** — each window's *original* percentile footprint ``F_W`` (selected on its
  own coverage-passed support ``C_W``) against the January reference footprint ``F_M`` (selected on
  ``C_M``); and
* **conditional agreement on shared support** — both fields restricted to ``S = C_W ∩ C_M`` for that
  one window/reference pair, with each field's percentile cutoff *recomputed on S* under the
  existing convention (NumPy linear percentile, select ``value >= cutoff``).

It uses only existing NOAA-19 p1 grid tables, grids, statistics, thresholds and coverage rules.
Nothing here is a new eligibility filter, window, pool or resampling protocol.

Definitions (all areas are spherical cell areas from
:func:`saa.threshold_analysis.cell_area_km2`, km²):

* ``J_area(X, Y) = area(X ∩ Y) / area(X ∪ Y)`` on cell identities of the *same* grid.
* monthly-footprint observability ``O = area(F_M ∩ C_W) / area(F_M)``: how much of the monthly
  selected area meets the window's eligibility — not agreement of the window's footprint.
* centroids are the existing coordinate moments weighted by ``statistic × cell area``.

Undefined cases return NaN together with an explicit ``*_undefined_reason`` string, never a fake
zero or a coerced perfect agreement: empty common support, empty union, or zero total weight.
Valid zero flux is kept as a value (it can be eligible and contributes zero weight); missing flux
is absent from the grid table and is never zero-filled.

Distinct valid UTC observation days per cell describe sampling only. They are not an eligibility
rule, and an observation count is not an independent-pass count.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .threshold_analysis import (
    PERCENTILES, STATISTICS, cell_area_km2, haversine_km, percentile_threshold,
)
from .time_window_analysis import MONTH_REFERENCE_LABEL, TIME_WINDOWS, region_cell_count

KEY = ["lat_bin_center", "lon_bin_center"]

#: Windows whose date range duplicates another window; reported once, flagged as aliases.
WINDOW_ALIASES: dict[str, str] = {"week1": "days_2024-01-01_to_07"}

TEMPORAL_SUPPORT_COLUMNS = [
    "window_label", "alias_of", "reference_label", "grid_deg", "statistic_used", "threshold_label",
    "percentile_cutoff",
    # sampling / support accounting
    "nominal_cells", "nominal_area_km2",
    "window_valid_observed_cells", "window_valid_observed_area_fraction",
    "window_observed_below_coverage_cells", "window_no_valid_observation_cells",
    "window_coverage_passed_cells", "window_coverage_passed_area_fraction",
    "reference_coverage_passed_cells", "reference_coverage_passed_area_fraction",
    # end-to-end (original supports)
    "window_cutoff_original", "reference_cutoff_original",
    "window_selected_cells_original", "reference_selected_cells_original",
    "window_eligible_unselected_cells_original",
    "window_selected_area_km2_original", "reference_selected_area_km2_original",
    "selected_area_ratio_original", "area_jaccard_original", "count_jaccard_original",
    "centroid_distance_km_original", "original_undefined_reason",
    "monthly_footprint_observability", "observability_undefined_reason",
    # conditional (shared support S = C_W ∩ C_M)
    "common_support_cells", "common_support_area_km2", "common_support_area_fraction",
    "window_cutoff_common", "reference_cutoff_common",
    "window_selected_cells_common", "reference_selected_cells_common",
    "window_selected_area_km2_common", "reference_selected_area_km2_common",
    "selected_area_ratio_common", "area_jaccard_common", "centroid_distance_km_common",
    "common_undefined_reason",
    # sampling description (not a filter)
    "window_distinct_days_median_coverage_passed", "window_distinct_days_min_coverage_passed",
    "window_day_count",
]


# ------------------------------------------------------------------ primitives
def _keys(frame: pd.DataFrame) -> set:
    return set(zip(frame["lat_bin_center"].to_numpy(dtype=float),
                   frame["lon_bin_center"].to_numpy(dtype=float)))


def area_of(cells: set, step: float) -> float:
    """Spherical area (km²) of a set of ``(lat_center, lon_center)`` cells of one grid."""
    if not cells:
        return 0.0
    # sorted + fsum: identical sets give bit-identical areas regardless of set iteration order
    lat = np.array([c[0] for c in sorted(cells)], dtype=float)
    return math.fsum(cell_area_km2(lat, step, step))


def area_jaccard(a: set, b: set, step: float) -> tuple[float, str]:
    """Area-weighted Jaccard of two cell sets on the same aligned grid.

    Returns ``(value, reason)``; ``reason`` is empty when defined. Two empty sets are undefined.
    """
    union = a | b
    if not union:
        return float("nan"), "empty_union"
    return area_of(a & b, step) / area_of(union, step), ""


def weighted_centroid(frame: pd.DataFrame, stat: str, step: float) -> tuple[float, float, str]:
    """Existing coordinate-moment centroid (weights ``stat × cell area``) with explicit reasons."""
    if len(frame) == 0:
        return float("nan"), float("nan"), "empty_selection"
    w = frame[stat].to_numpy(float) * cell_area_km2(frame["lat_bin_center"].to_numpy(float), step, step)
    if np.any(~np.isfinite(w)) or np.any(w < 0):
        raise ValueError("centroid weights must be finite and nonnegative")
    total = float(w.sum())
    if total <= 0:
        return float("nan"), float("nan"), "zero_mass"
    lat = float((frame["lat_bin_center"].to_numpy(float) * w).sum() / total)
    lon = float((frame["lon_bin_center"].to_numpy(float) * w).sum() / total)
    return lat, lon, ""


def select_footprint(support: pd.DataFrame, stat: str, percentile: float) -> tuple[pd.DataFrame, float]:
    """Existing convention: linear percentile over the given support, keep ``value >= cutoff``."""
    if len(support) == 0:
        return support.iloc[0:0], float("nan")
    cutoff = percentile_threshold(support[stat], percentile)
    return support[support[stat] >= cutoff], cutoff


def coverage_passed(table: pd.DataFrame, mask_col: str, stat: str) -> pd.DataFrame:
    """Coverage-passed cells with a finite statistic (valid zero kept)."""
    ok = table[mask_col].astype(bool) & np.isfinite(table[stat].to_numpy(float))
    return table[ok]


# ------------------------------------------------------------------ one comparison
def compare_window(window: pd.DataFrame, reference: pd.DataFrame, *, grid_deg: int, mask_col: str,
                   stat: str, percentile: float) -> dict:
    """Original-support and shared-support comparison of one window against the reference.

    ``window``/``reference`` are grid tables on the same aligned grid (one row per observed cell,
    ``mask_col`` coverage flag). Returns a dict of the diagnostics named in
    :data:`TEMPORAL_SUPPORT_COLUMNS` (excluding labels filled by the caller).
    """
    step = float(grid_deg)
    nominal = region_cell_count(grid_deg)
    nominal_area = float(cell_area_km2(
        np.repeat(np.arange(-70 + step / 2, 20, step), int(round(120 / step))), step, step).sum())

    valid_w = window[np.isfinite(window[stat].to_numpy(float))]
    cw = coverage_passed(window, mask_col, stat)
    cm = coverage_passed(reference, mask_col, stat)
    k_valid, k_cw, k_cm = _keys(valid_w), _keys(cw), _keys(cm)

    fw, cut_w = select_footprint(cw, stat, percentile)
    fm, cut_m = select_footprint(cm, stat, percentile)
    k_fw, k_fm = _keys(fw), _keys(fm)
    a_fw, a_fm = area_of(k_fw, step), area_of(k_fm, step)

    row: dict = {
        "nominal_cells": nominal, "nominal_area_km2": nominal_area,
        "window_valid_observed_cells": len(k_valid),
        "window_valid_observed_area_fraction": area_of(k_valid, step) / nominal_area,
        "window_observed_below_coverage_cells": len(k_valid - k_cw),
        "window_no_valid_observation_cells": nominal - len(k_valid),
        "window_coverage_passed_cells": len(k_cw),
        "window_coverage_passed_area_fraction": area_of(k_cw, step) / nominal_area,
        "reference_coverage_passed_cells": len(k_cm),
        "reference_coverage_passed_area_fraction": area_of(k_cm, step) / nominal_area,
        "window_cutoff_original": cut_w, "reference_cutoff_original": cut_m,
        "window_selected_cells_original": len(k_fw), "reference_selected_cells_original": len(k_fm),
        "window_eligible_unselected_cells_original": len(k_cw - k_fw),
        "window_selected_area_km2_original": a_fw, "reference_selected_area_km2_original": a_fm,
    }
    reasons = []
    row["selected_area_ratio_original"] = a_fw / a_fm if a_fm > 0 else float("nan")
    if a_fm <= 0:
        reasons.append("empty_reference_footprint")
    row["area_jaccard_original"], r = area_jaccard(k_fw, k_fm, step)
    if r:
        reasons.append(r)
    union = k_fw | k_fm
    row["count_jaccard_original"] = len(k_fw & k_fm) / len(union) if union else float("nan")
    wlat, wlon, rw = weighted_centroid(fw, stat, step)
    mlat, mlon, rm = weighted_centroid(fm, stat, step)
    if rw or rm:
        reasons.append(f"centroid:{rw or 'ok'}/{rm or 'ok'}")
        row["centroid_distance_km_original"] = float("nan")
    else:
        row["centroid_distance_km_original"] = haversine_km(wlat, wlon, mlat, mlon)
    row["original_undefined_reason"] = ";".join(reasons)

    if a_fm > 0:
        row["monthly_footprint_observability"] = area_of(k_fm & k_cw, step) / a_fm
        row["observability_undefined_reason"] = ""
    else:
        row["monthly_footprint_observability"] = float("nan")
        row["observability_undefined_reason"] = "empty_reference_footprint"

    # conditional comparison on S = C_W ∩ C_M, cutoffs recomputed on S for each field
    k_s = k_cw & k_cm
    row["common_support_cells"] = len(k_s)
    row["common_support_area_km2"] = area_of(k_s, step)
    row["common_support_area_fraction"] = row["common_support_area_km2"] / nominal_area
    if not k_s:
        row.update({c: float("nan") for c in (
            "window_cutoff_common", "reference_cutoff_common", "window_selected_area_km2_common",
            "reference_selected_area_km2_common", "selected_area_ratio_common",
            "area_jaccard_common", "centroid_distance_km_common")})
        row["window_selected_cells_common"] = 0
        row["reference_selected_cells_common"] = 0
        row["common_undefined_reason"] = "empty_common_support"
        return row
    sw = cw[[k in k_s for k in zip(cw["lat_bin_center"].astype(float), cw["lon_bin_center"].astype(float))]]
    sm = cm[[k in k_s for k in zip(cm["lat_bin_center"].astype(float), cm["lon_bin_center"].astype(float))]]
    gw, cut_ws = select_footprint(sw, stat, percentile)
    gm, cut_ms = select_footprint(sm, stat, percentile)
    k_gw, k_gm = _keys(gw), _keys(gm)
    a_gw, a_gm = area_of(k_gw, step), area_of(k_gm, step)
    reasons = []
    row.update({
        "window_cutoff_common": cut_ws, "reference_cutoff_common": cut_ms,
        "window_selected_cells_common": len(k_gw), "reference_selected_cells_common": len(k_gm),
        "window_selected_area_km2_common": a_gw, "reference_selected_area_km2_common": a_gm,
        "selected_area_ratio_common": a_gw / a_gm if a_gm > 0 else float("nan"),
    })
    row["area_jaccard_common"], r = area_jaccard(k_gw, k_gm, step)
    if r:
        reasons.append(r)
    wlat, wlon, rw = weighted_centroid(gw, stat, step)
    mlat, mlon, rm = weighted_centroid(gm, stat, step)
    if rw or rm:
        reasons.append(f"centroid:{rw or 'ok'}/{rm or 'ok'}")
        row["centroid_distance_km_common"] = float("nan")
    else:
        row["centroid_distance_km_common"] = haversine_km(wlat, wlon, mlat, mlon)
    row["common_undefined_reason"] = ";".join(reasons)
    row["_selected_common"] = (k_gw, k_gm)
    return row


# ------------------------------------------------------------------ sampling description
def distinct_days_per_cell(region: pd.DataFrame, value_col: str, grid_deg: int,
                           lat_range=(-70.0, 20.0), lon_range=(-100.0, 20.0)) -> pd.DataFrame:
    """Distinct UTC calendar days with at least one finite ``value_col`` record in each cell.

    Binning matches :func:`saa.aggregate.build_grid_table`. Descriptive only.
    """
    step = float(grid_deg)
    v = region[value_col].to_numpy(float)
    li = np.floor((region["lat"].to_numpy(float) - lat_range[0]) / step).astype(int)
    lj = np.floor((region["lon180"].to_numpy(float) - lon_range[0]) / step).astype(int)
    n_lat = int(round((lat_range[1] - lat_range[0]) / step))
    n_lon = int(round((lon_range[1] - lon_range[0]) / step))
    ok = (li >= 0) & (li < n_lat) & (lj >= 0) & (lj < n_lon) & np.isfinite(v)
    day = pd.to_datetime(region["time"], utc=True).dt.normalize().to_numpy()[ok]
    d = pd.DataFrame({"lat_bin_center": lat_range[0] + (li[ok] + 0.5) * step,
                      "lon_bin_center": lon_range[0] + (lj[ok] + 0.5) * step, "day": day})
    out = d.groupby(KEY)["day"].nunique().rename("distinct_valid_days").reset_index()
    return out.sort_values(KEY).reset_index(drop=True)


# ------------------------------------------------------------------ sweep
def run_temporal_support(grids: dict, regions: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Sweep every non-reference CP4D window × grid × statistic × threshold.

    ``grids`` maps ``(window_label, grid_deg)`` to the existing CP4D grid table;
    ``regions`` optionally maps ``window_label`` to the window's region frame for distinct-day
    counts. Returns ``(rows, selected_cells, distinct_days)``.
    """
    rows, cells, days = [], [], []
    labels = [w["window_label"] for w in TIME_WINDOWS]
    day_counts = {w["window_label"]: (pd.Timestamp(w["end_date"]) - pd.Timestamp(w["start_date"])).days + 1
                  for w in TIME_WINDOWS}
    for label in labels:
        for grid_deg in (5, 2):
            mask_col = f"enough_samples_{grid_deg}deg"
            table, ref = grids[(label, grid_deg)], grids[(MONTH_REFERENCE_LABEL, grid_deg)]
            dd = None
            if regions is not None and label in regions:
                dd = distinct_days_per_cell(regions[label], "mep_omni_flux_p1", grid_deg)
                dd.insert(0, "grid_deg", grid_deg)
                dd.insert(0, "window_label", label)
                days.append(dd)
            for stat in STATISTICS:
                cw_keys = _keys(coverage_passed(table, mask_col, stat))
                for pct, tl in PERCENTILES:
                    r = compare_window(table, ref, grid_deg=grid_deg, mask_col=mask_col,
                                       stat=stat, percentile=pct)
                    sel = r.pop("_selected_common", (set(), set()))
                    r.update({"window_label": label, "alias_of": WINDOW_ALIASES.get(label, ""),
                              "reference_label": MONTH_REFERENCE_LABEL, "grid_deg": grid_deg,
                              "statistic_used": stat, "threshold_label": tl,
                              "percentile_cutoff": pct, "window_day_count": day_counts[label]})
                    if dd is not None:
                        passed = dd[[k in cw_keys for k in zip(dd.lat_bin_center, dd.lon_bin_center)]]
                        r["window_distinct_days_median_coverage_passed"] = float(passed.distinct_valid_days.median()) if len(passed) else float("nan")
                        r["window_distinct_days_min_coverage_passed"] = float(passed.distinct_valid_days.min()) if len(passed) else float("nan")
                    else:
                        r["window_distinct_days_median_coverage_passed"] = float("nan")
                        r["window_distinct_days_min_coverage_passed"] = float("nan")
                    rows.append(r)
                    for role, ks in (("window_common", sel[0]), ("reference_common", sel[1])):
                        for la, lo in sorted(ks):
                            cells.append({"window_label": label, "grid_deg": grid_deg,
                                          "statistic_used": stat, "threshold_label": tl,
                                          "role": role, "lat_bin_center": la, "lon_bin_center": lo})
    out = pd.DataFrame(rows)[TEMPORAL_SUPPORT_COLUMNS]
    sel = pd.DataFrame(cells, columns=["window_label", "grid_deg", "statistic_used", "threshold_label",
                                       "role", "lat_bin_center", "lon_bin_center"])
    dist = pd.concat(days, ignore_index=True) if days else pd.DataFrame()
    return out, sel, dist
