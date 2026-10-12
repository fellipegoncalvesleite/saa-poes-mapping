"""Tests for the CP4D.1 three-day sampling-stabilization diagnostic."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.threshold_analysis import (  # noqa: E402
    add_cell_area,
    coverage_passed,
    haversine_km,
    peak_flux_location,
)
from saa.time_window_analysis import (  # noqa: E402
    CUMULATIVE_LABELS,
    MONTH_REFERENCE_LABEL,
    TIME_WINDOWS,
    add_month_stability_metrics,
    build_window_grids,
    choose_coverage_threshold,
    coverage_diagnostics,
    footprint_jaccard,
    region_cell_count,
    run_time_window_sensitivity,
    slice_window,
    window_day_count,
)


def _window(label: str) -> dict:
    return next(w for w in TIME_WINDOWS if w["window_label"] == label)


class WindowDefinitionTests(unittest.TestCase):
    def test_three_day_cumulative_state_exists_with_jan_1_to_3_dates(self) -> None:
        spec = _window("days_2024-01-01_to_03")
        self.assertEqual(spec["start_date"], "2024-01-01")
        self.assertEqual(spec["end_date"], "2024-01-03")
        self.assertEqual(window_day_count(spec["start_date"], spec["end_date"]), 3)

    def test_cumulative_sequence_is_1_3_7_14_31_days(self) -> None:
        self.assertEqual(
            CUMULATIVE_LABELS,
            ["day_2024-01-01", "days_2024-01-01_to_03", "days_2024-01-01_to_07",
             "days_2024-01-01_to_14", "month_2024-01"],
        )
        counts = [window_day_count(_window(l)["start_date"], _window(l)["end_date"])
                  for l in CUMULATIVE_LABELS]
        self.assertEqual(counts, [1, 3, 7, 14, 31])

    def test_no_duplicate_window_labels(self) -> None:
        labels = [w["window_label"] for w in TIME_WINDOWS]
        self.assertEqual(len(labels), len(set(labels)))


class CoverageThresholdTests(unittest.TestCase):
    def test_three_day_threshold_comes_from_canonical_rule_and_is_floor_bound(self) -> None:
        self.assertEqual(choose_coverage_threshold(3), 3)
        # round((30/31)*3) == 3, so the floor binds but does not change the value;
        # the rule itself is unchanged for every other window.
        self.assertEqual(choose_coverage_threshold(1), 3)
        self.assertEqual(choose_coverage_threshold(7), 7)
        self.assertEqual(choose_coverage_threshold(14), 14)
        self.assertEqual(choose_coverage_threshold(31), 30)

    def test_diagnostics_distinguish_unobserved_from_below_threshold(self) -> None:
        # Nominal 5deg region has 432 cells; fabricate a tiny populated table instead
        # and check the accounting relationships on a synthetic mask.
        table = pd.DataFrame({
            "lat_bin_center": [-20.0, -20.0, -15.0, -15.0, -10.0],
            "lon_bin_center": [-55.0, -50.0, -55.0, -50.0, -55.0],
            "mean_flux": [10.0, 9.0, 8.0, 7.0, 6.0],
            "median_flux": [10.0, 9.0, 8.0, 7.0, 6.0],
            "sample_count": [30, 5, 2, 1, 0 + 30],
            "positive_sample_count": [30, 5, 2, 1, 30],
            "min_flux": [1.0] * 5,
            "max_flux": [10.0] * 5,
        })
        table["mask"] = table["sample_count"] >= 30
        diag = coverage_diagnostics(table, "mask", 5)
        self.assertEqual(diag["nominal_region_cells"], 432)
        self.assertEqual(diag["cells_with_observation"], 5)
        self.assertEqual(diag["zero_observation_cells"], 432 - 5)
        self.assertAlmostEqual(diag["zero_observation_fraction"], (432 - 5) / 432)
        self.assertEqual(diag["cells_available_after_coverage_mask"], 2)
        self.assertEqual(diag["cells_failing_coverage"], 432 - 2)
        # Observed-but-insufficient cells are neither zero-observation nor passing.
        self.assertEqual(diag["cells_observed_below_threshold"], 3)
        self.assertLessEqual(diag["cells_available_after_coverage_mask"],
                             diag["cells_with_observation"])
        self.assertLessEqual(diag["cells_with_observation"], diag["nominal_region_cells"])

    def test_nominal_region_cell_counts(self) -> None:
        self.assertEqual(region_cell_count(5), 432)
        self.assertEqual(region_cell_count(2), 2700)


class PeakFluxLocationTests(unittest.TestCase):
    def test_peak_coordinates_match_maximum_eligible_cell(self) -> None:
        covered = pd.DataFrame({
            "lat_bin_center": [-20.0, -25.0, -15.0],
            "lon_bin_center": [-55.0, -50.0, -60.0],
            "mean_flux": [3.0, 9.0, 5.0],
        })
        peak = peak_flux_location(covered, "mean_flux")
        self.assertEqual(peak["peak_flux"], 9.0)
        self.assertEqual((peak["peak_flux_lat"], peak["peak_flux_lon"]), (-25.0, -50.0))
        self.assertEqual(peak["peak_flux_tie_count"], 1)

    def test_ties_are_deterministic_with_tie_count(self) -> None:
        covered = pd.DataFrame({
            "lat_bin_center": [-20.0, -25.0, -15.0],
            "lon_bin_center": [-55.0, -50.0, -60.0],
            "mean_flux": [9.0, 9.0, 9.0],
        })
        first = peak_flux_location(covered, "mean_flux")
        # Southernmost, then westernmost, regardless of input row order.
        self.assertEqual((first["peak_flux_lat"], first["peak_flux_lon"]), (-25.0, -50.0))
        self.assertEqual(first["peak_flux_tie_count"], 3)
        shuffled = covered.sample(frac=1.0, random_state=7).reset_index(drop=True)
        second = peak_flux_location(shuffled, "mean_flux")
        self.assertEqual(first, second)

    def test_empty_covered_field_gives_nans(self) -> None:
        peak = peak_flux_location(pd.DataFrame({"mean_flux": []}), "mean_flux")
        self.assertTrue(np.isnan(peak["peak_flux_lat"]))
        self.assertEqual(peak["peak_flux_tie_count"], 0)


class StabilityMetricTests(unittest.TestCase):
    def test_jaccard_on_known_synthetic_footprints(self) -> None:
        self.assertEqual(footprint_jaccard({1, 2, 3}, {1, 2, 3}), 1.0)
        self.assertEqual(footprint_jaccard({1, 2}, {3, 4}), 0.0)
        self.assertAlmostEqual(footprint_jaccard({1, 2, 3}, {2, 3, 4}), 2 / 4)
        self.assertTrue(np.isnan(footprint_jaccard(set(), set())))

    def test_month_compared_with_itself_is_identity(self) -> None:
        covered = add_cell_area(pd.DataFrame({
            "lat_bin_center": [-20.0, -25.0, -15.0, -10.0],
            "lon_bin_center": [-55.0, -50.0, -60.0, -55.0],
            "mean_flux": [10.0, 9.0, 2.0, 1.0],
            "median_flux": [10.0, 9.0, 2.0, 1.0],
            "sample_count": [31, 31, 31, 31],
            "positive_sample_count": [31, 31, 31, 31],
            "min_flux": [1.0, 1.0, 1.0, 1.0],
            "max_flux": [10.0, 9.0, 2.0, 1.0],
        }), 5.0, 5.0)
        covered["mask"] = True
        frame = pd.DataFrame([{
            "window_label": MONTH_REFERENCE_LABEL, "grid_deg": 5,
            "statistic_used": "mean_flux", "threshold_label": "top10",
            "flux_cutoff_value": 5.0, "selected_area_km2": 100.0,
            "centroid_lat_flux_weighted": -20.0, "centroid_lon_flux_weighted": -55.0,
        }])
        out = add_month_stability_metrics(
            frame, {(MONTH_REFERENCE_LABEL, 5): coverage_passed(covered, "mask")})
        self.assertEqual(out["centroid_distance_to_month_km"].iloc[0], 0.0)
        self.assertEqual(out["selected_area_ratio_to_month"].iloc[0], 1.0)
        self.assertEqual(out["selected_area_difference_to_month_km2"].iloc[0], 0.0)
        self.assertEqual(out["footprint_jaccard_vs_month"].iloc[0], 1.0)

    def test_centroid_distance_uses_canonical_haversine(self) -> None:
        covered = add_cell_area(pd.DataFrame({
            "lat_bin_center": [-20.0, -25.0, -15.0, -10.0],
            "lon_bin_center": [-55.0, -50.0, -60.0, -55.0],
            "mean_flux": [10.0, 9.0, 2.0, 1.0],
            "median_flux": [10.0, 9.0, 2.0, 1.0],
            "sample_count": [31, 31, 31, 31],
            "positive_sample_count": [31, 31, 31, 31],
            "min_flux": [1.0, 1.0, 1.0, 1.0],
            "max_flux": [10.0, 9.0, 2.0, 1.0],
        }), 5.0, 5.0)
        covered["mask"] = True
        frame = pd.DataFrame([
            {"window_label": MONTH_REFERENCE_LABEL, "grid_deg": 5,
             "statistic_used": "mean_flux", "threshold_label": "top10",
             "flux_cutoff_value": 5.0, "selected_area_km2": 100.0,
             "centroid_lat_flux_weighted": -20.0, "centroid_lon_flux_weighted": -55.0},
            {"window_label": "day_2024-01-01", "grid_deg": 5,
             "statistic_used": "mean_flux", "threshold_label": "top10",
             "flux_cutoff_value": 5.0, "selected_area_km2": 50.0,
             "centroid_lat_flux_weighted": -21.0, "centroid_lon_flux_weighted": -54.0},
        ])
        grids = {(MONTH_REFERENCE_LABEL, 5): coverage_passed(covered, "mask"),
                 ("day_2024-01-01", 5): coverage_passed(covered, "mask")}
        out = add_month_stability_metrics(frame, grids)
        day = out[out["window_label"] == "day_2024-01-01"].iloc[0]
        self.assertAlmostEqual(day["centroid_distance_to_month_km"],
                               haversine_km(-21.0, -54.0, -20.0, -55.0))
        self.assertAlmostEqual(day["selected_area_ratio_to_month"], 0.5)
        self.assertAlmostEqual(day["selected_area_difference_to_month_km2"], -50.0)
        self.assertEqual(day["footprint_jaccard_vs_month"], 1.0)
        self.assertGreaterEqual(day["footprint_jaccard_vs_month"], 0.0)
        self.assertLessEqual(day["footprint_jaccard_vs_month"], 1.0)


@unittest.skipUnless(
    (ROOT / "outputs" / "tables" / "cp4d_time_window_threshold_sensitivity.parquet").exists()
    and (ROOT / "data" / "processed"
         / "cp4d_noaa19_2024-01_full_month_mep_omni_flux_p1_region.parquet").exists(),
    "canonical CP4D tables and processed region data are not present",
)
class TimeWindowRegressionTests(unittest.TestCase):
    OLD_CUMULATIVE = [
        ("day_2024-01-01", "2024-01-01", "2024-01-01"),
        ("days_2024-01-01_to_07", "2024-01-01", "2024-01-07"),
        ("days_2024-01-01_to_14", "2024-01-01", "2024-01-14"),
        ("month_2024-01", "2024-01-01", "2024-01-31"),
    ]

    @classmethod
    def setUpClass(cls) -> None:
        full = pd.read_parquet(
            ROOT / "data" / "processed"
            / "cp4d_noaa19_2024-01_full_month_mep_omni_flux_p1_region.parquet")
        specs = []
        for label, start, end in cls.OLD_CUMULATIVE:
            sub = slice_window(full, start, end)
            dc = window_day_count(start, end)
            grids, _ = build_window_grids(sub, dc)
            specs.append({"window_label": label, "start_date": start, "end_date": end,
                          "day_count": dc, "files_expected": dc, "files_loaded": dc,
                          "grids": grids})
        cls.regenerated = run_time_window_sensitivity(specs)
        cls.accepted = pd.read_parquet(
            ROOT / "outputs" / "tables" / "cp4d_time_window_threshold_sensitivity.parquet")

    def test_inserting_three_day_state_does_not_alter_old_values(self) -> None:
        key = ["window_label", "grid_deg", "statistic_used", "threshold_label"]
        old = self.accepted[self.accepted["window_label"].isin(
            [label for label, _, _ in self.OLD_CUMULATIVE])]
        self.assertEqual(len(old), 4 * 2 * 2 * 5)
        merged = old.merge(self.regenerated, on=key, suffixes=("_old", "_new"))
        self.assertEqual(len(merged), len(old))
        float_cols = ["flux_cutoff_value", "selected_area_km2",
                      "selected_area_fraction_of_covered_region",
                      "centroid_lat_unweighted", "centroid_lon_unweighted",
                      "centroid_lat_flux_weighted", "centroid_lon_flux_weighted",
                      "peak_flux", "mean_flux_within_selected",
                      "median_flux_within_selected", "total_flux_area_proxy"]
        for col in float_cols:
            self.assertTrue(
                np.isclose(merged[f"{col}_old"], merged[f"{col}_new"],
                           rtol=1e-9, atol=1e-12).all(),
                f"regression drift in {col}")
        int_cols = ["day_count", "files_expected", "files_loaded",
                    "cells_available_after_coverage_mask", "selected_cell_count",
                    "coverage_threshold_used", "percentile_cutoff"]
        for col in int_cols:
            self.assertTrue((merged[f"{col}_old"] == merged[f"{col}_new"]).all(),
                            f"regression drift in {col}")
        self.assertTrue((merged["coverage_warning_old"] == merged["coverage_warning_new"]).all())


if __name__ == "__main__":
    unittest.main()
