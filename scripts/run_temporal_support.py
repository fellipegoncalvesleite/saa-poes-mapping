"""Phase 4B: temporal coverage vs conditional morphology on existing NOAA-19 p1 windows.

Run from repository root: PYTHONPATH=src python scripts/run_temporal_support.py
Reads existing CP4D grid tables and the processed full-month region; writes
outputs/tables/cp4d_temporal_support*.{csv,parquet}. Fails if the recomputed original-support
footprints disagree with the stored CP4D sensitivity table.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from saa.temporal_support import run_temporal_support  # noqa: E402
from saa.time_window_analysis import TIME_WINDOWS, slice_window  # noqa: E402

T = Path("outputs/tables")
REGION = Path("data/processed/cp4d_noaa19_2024-01_full_month_mep_omni_flux_p1_region.parquet")


def grid_path(label: str, grid_deg: int) -> Path:
    return T / f"cp4d_{label}_grid_{grid_deg}deg.parquet"


def main() -> None:
    grids = {(w["window_label"], g): pd.read_parquet(grid_path(w["window_label"], g))
             for w in TIME_WINDOWS for g in (5, 2)}
    month = pd.read_parquet(REGION)
    regions = {w["window_label"]: slice_window(month, w["start_date"], w["end_date"]) for w in TIME_WINDOWS}
    rows, cells, days = run_temporal_support(grids, regions)

    stored = pd.read_parquet(T / "cp4d_time_window_threshold_sensitivity.parquet")
    key = ["window_label", "grid_deg", "statistic_used", "threshold_label"]
    joined = rows.merge(stored, on=key, how="left", validate="one_to_one")
    checks = {
        "window_selected_cells_original": "selected_cell_count",
        "window_selected_area_km2_original": "selected_area_km2",
        "window_cutoff_original": "flux_cutoff_value",
        "window_coverage_passed_cells": "cells_available_after_coverage_mask",
        "window_valid_observed_cells": "cells_with_observation",
        "centroid_distance_km_original": "centroid_distance_to_month_km",
        "count_jaccard_original": "footprint_jaccard_vs_month",
    }
    for mine, theirs in checks.items():
        np.testing.assert_allclose(joined[mine].to_numpy(float), joined[theirs].to_numpy(float),
                                   rtol=1e-12, atol=1e-9, err_msg=f"{mine} vs stored {theirs}")
    alias = rows[rows.window_label == "week1"].drop(columns=["window_label", "alias_of"]).reset_index(drop=True)
    target = rows[rows.window_label == "days_2024-01-01_to_07"].drop(columns=["window_label", "alias_of"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(alias, target)
    month_rows = rows[rows.window_label == "month_2024-01"]
    assert (month_rows.area_jaccard_original == 1).all() and (month_rows.area_jaccard_common == 1).all()
    assert (month_rows.centroid_distance_km_common == 0).all()

    rows.to_csv(T / "cp4d_temporal_support.csv", index=False)
    rows.to_parquet(T / "cp4d_temporal_support.parquet", index=False)
    cells.to_csv(T / "cp4d_temporal_support_selected_cells.csv", index=False)
    days.to_csv(T / "cp4d_temporal_support_distinct_days.csv", index=False)
    principal = rows[(rows.grid_deg == 5) & (rows.statistic_used == "mean_flux") & (rows.threshold_label == "top10")]
    print(principal[["window_label", "window_coverage_passed_cells", "area_jaccard_original",
                     "monthly_footprint_observability", "common_support_cells", "area_jaccard_common",
                     "centroid_distance_km_original", "centroid_distance_km_common"]].to_string(index=False))
    print(f"rows={len(rows)} undefined_original={int((rows.original_undefined_reason != '').sum())} "
          f"undefined_common={int((rows.common_undefined_reason != '').sum())}")


if __name__ == "__main__":
    main()
