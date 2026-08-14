"""Behavior and authority-contract tests for the static scientific viewer exporter."""
from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.viewer_export import (  # noqa: E402
    EXPECTED_CONFIGURATION_COUNTS,
    EXPERIMENT_DIMENSIONS,
    build_viewer_payload,
    export_grid,
    haversine_km,
    selected_cell_indices,
    stable_configuration_id,
    write_viewer_data,
)


class ViewerGridExportTests(unittest.TestCase):
    def test_grid_export_sorts_cells_and_blanks_coverage_failures(self) -> None:
        table = pd.DataFrame(
            {
                "lat_bin_center": [-62.5, -67.5, -67.5],
                "lon_bin_center": [-97.5, -92.5, -97.5],
                "mean_flux": [10.0, 5.0, 1.0],
                "median_flux": [8.0, 4.0, 0.5],
                "sample_count": [31, 2, 12],
                "enough_samples_5deg": [True, False, True],
            }
        )

        actual = export_grid(table, grid_deg=5, mask_col="enough_samples_5deg")

        self.assertEqual(
            actual["columns"],
            ["lat", "lon", "mean_flux", "median_flux", "sample_count", "covered", "north_south_km", "east_west_km", "cell_area_km2"],
        )
        self.assertEqual([cell[:6] for cell in actual["cells"]], [
            [-67.5, -97.5, 1.0, 0.5, 12, True],
            [-67.5, -92.5, None, None, 2, False],
            [-62.5, -97.5, 10.0, 8.0, 31, True],
        ])
        north_south = 6371.0 * math.radians(5)
        self.assertAlmostEqual(actual["cells"][0][6], north_south)
        self.assertAlmostEqual(actual["cells"][0][7], north_south * math.cos(math.radians(-67.5)))
        self.assertGreater(actual["cells"][2][7], actual["cells"][0][7])
        self.assertGreater(actual["cells"][0][8], 0)
        self.assertEqual(actual["color_domains"]["mean_flux"], [1.0, 10.0])
        self.assertEqual(actual["color_domains"]["median_flux"], [0.5, 8.0])

    def test_grid_export_rejects_null_and_non_boolean_coverage_masks(self) -> None:
        base = {
            "lat_bin_center": [-67.5],
            "lon_bin_center": [-97.5],
            "mean_flux": [1.0],
            "median_flux": [0.5],
            "sample_count": [31],
        }
        for invalid in (None, 1, "true"):
            with self.subTest(invalid=invalid):
                table = pd.DataFrame({**base, "enough_samples_5deg": [invalid]})
                with self.assertRaises(TypeError):
                    export_grid(table, grid_deg=5, mask_col="enough_samples_5deg")

    def test_selected_indices_reject_non_boolean_exported_coverage(self) -> None:
        grid = {
            "columns": ["lat", "lon", "mean_flux", "median_flux", "sample_count", "covered"],
            "cells": [[-67.5, -97.5, 1.0, 0.5, 31, None]],
        }

        with self.assertRaises(TypeError):
            selected_cell_indices(grid, "mean_flux", 0.5)

    def test_selected_indices_use_exported_coverage_and_canonical_cutoff(self) -> None:
        grid = {
            "columns": ["lat", "lon", "mean_flux", "median_flux", "sample_count", "covered"],
            "cells": [
                [-67.5, -97.5, 1.0, 0.5, 12, True],
                [-67.5, -92.5, None, None, 2, False],
                [-62.5, -97.5, 10.0, 8.0, 31, True],
            ],
        }

        self.assertEqual(selected_cell_indices(grid, "mean_flux", 5.0), [2])
        self.assertEqual(selected_cell_indices(grid, "median_flux", 0.5), [0, 2])


class ViewerSerializationTests(unittest.TestCase):
    def test_configuration_ids_are_stable_and_experiment_scoped(self) -> None:
        values = {"threshold_label": "top10", "grid_deg": 5, "statistic_used": "mean_flux"}
        self.assertEqual(
            stable_configuration_id("threshold", values),
            "threshold|grid_deg=5|statistic_used=mean_flux|threshold_label=top10",
        )
        self.assertNotEqual(
            stable_configuration_id("channel", values),
            stable_configuration_id("threshold", values),
        )

    def test_writer_is_deterministic_classic_javascript(self) -> None:
        payload = {"schema_version": 1, "label": "raw", "nested": {"b": 2, "a": 1}}
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.js"
            second = Path(tmp) / "second.js"
            hash_one = write_viewer_data(payload, first)
            hash_two = write_viewer_data(payload, second)

            self.assertEqual(hash_one, hash_two)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            source = first.read_text(encoding="utf-8")
            self.assertTrue(source.startswith("window.SAA_VIEWER_DATA = "))
            self.assertTrue(source.endswith(";\n"))
            decoded = json.loads(source.removeprefix("window.SAA_VIEWER_DATA = ").removesuffix(";\n"))
            self.assertEqual(decoded, payload)


@unittest.skipUnless(
    (ROOT / "outputs" / "tables" / "cp4f_multisatellite_threshold_sensitivity.parquet").exists(),
    "canonical regenerated checkpoint tables are not present",
)
class ViewerCanonicalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = build_viewer_payload(ROOT / "outputs" / "tables")

    def test_exact_supported_experiment_matrix_is_exported(self) -> None:
        self.assertEqual(
            EXPECTED_CONFIGURATION_COUNTS,
            {"threshold": 20, "channel": 60, "time": 160, "satellite": 100},
        )
        self.assertEqual(
            EXPERIMENT_DIMENSIONS,
            {
                "threshold": ["grid_deg", "statistic_used", "threshold_label"],
                "channel": ["channel", "grid_deg", "statistic_used", "threshold_label"],
                "time": ["window_label", "grid_deg", "statistic_used", "threshold_label"],
                "satellite": ["satellite", "grid_deg", "statistic_used", "threshold_label"],
            },
        )
        actual = {
            name: len(spec["configurations"])
            for name, spec in self.payload["experiments"].items()
        }
        self.assertEqual(actual, EXPECTED_CONFIGURATION_COUNTS)

    def test_noaa19_principal_threshold_state_matches_canonical_metrics(self) -> None:
        config_id = (
            "threshold|grid_deg=5|statistic_used=mean_flux|threshold_label=top10"
        )
        configs = {
            row["id"]: row
            for row in self.payload["experiments"]["threshold"]["configurations"]
        }
        row = configs[config_id]

        self.assertEqual(row["metrics"]["covered_cells"], 432)
        self.assertEqual(row["metrics"]["selected_cells"], 44)
        self.assertEqual(len(row["selected_cell_indices"]), 44)
        self.assertAlmostEqual(row["metrics"]["centroid_lat"], -21.154234, places=6)
        self.assertAlmostEqual(row["metrics"]["centroid_lon"], -55.635093, places=6)

    def test_cp5c_is_fixed_raw_evidence_not_a_map_experiment(self) -> None:
        self.assertNotIn("cp5c", self.payload["experiments"])
        self.assertEqual(self.payload["cp5c"]["classification"], "CONSISTENT")
        self.assertEqual(len(self.payload["cp5c"]["satellites"]), 5)
        self.assertEqual(self.payload["cp5c"]["low_btot_support_count"], 5)
        self.assertEqual(self.payload["cp5c"]["btot_dominance_support_count"], 5)

    def test_supported_method_changes_have_distinct_canonical_display_states(self) -> None:
        def find(experiment: str, **values):
            return next(
                row for row in self.payload["experiments"][experiment]["configurations"]
                if row["values"] == values
            )

        top10 = find(
            "threshold", grid_deg=5, statistic_used="mean_flux", threshold_label="top10"
        )
        top1 = find(
            "threshold", grid_deg=5, statistic_used="mean_flux", threshold_label="top1"
        )
        fine = find(
            "threshold", grid_deg=2, statistic_used="mean_flux", threshold_label="top10"
        )
        channel_p2 = find(
            "channel", channel="mep_omni_flux_p2", grid_deg=5,
            statistic_used="mean_flux", threshold_label="top10",
        )
        day = find(
            "time", window_label="day_2024-01-01", grid_deg=5,
            statistic_used="mean_flux", threshold_label="top10",
        )
        month = find(
            "time", window_label="month_2024-01", grid_deg=5,
            statistic_used="mean_flux", threshold_label="top10",
        )
        noaa15 = find(
            "satellite", satellite="noaa15", grid_deg=5,
            statistic_used="mean_flux", threshold_label="top10",
        )
        noaa19 = find(
            "satellite", satellite="noaa19", grid_deg=5,
            statistic_used="mean_flux", threshold_label="top10",
        )

        self.assertEqual(top10["grid_id"], top1["grid_id"])
        self.assertNotEqual(top10["selected_cell_indices"], top1["selected_cell_indices"])
        self.assertNotEqual(top10["grid_id"], fine["grid_id"])
        self.assertEqual(self.payload["grids"][fine["grid_id"]]["grid_deg"], 2)
        self.assertNotEqual(top10["grid_id"], channel_p2["grid_id"])
        self.assertLess(day["metrics"]["covered_cells"], month["metrics"]["covered_cells"])
        self.assertNotEqual(noaa15["metrics"]["centroid_lon"], noaa19["metrics"]["centroid_lon"])

    def test_comparisons_change_only_each_experiments_focal_dimension(self) -> None:
        focal = {
            "threshold": "threshold_label",
            "channel": "channel",
            "time": "window_label",
            "satellite": "satellite",
        }
        self.assertEqual(len(self.payload["comparisons"]), 860)
        configs = {
            row["id"]: row
            for experiment in self.payload["experiments"].values()
            for row in experiment["configurations"]
        }
        expected_counts = {"threshold": 40, "channel": 60, "time": 560, "satellite": 200}
        actual_counts = {name: 0 for name in expected_counts}
        for comparison in self.payload["comparisons"]:
            actual_counts[comparison["experiment"]] += 1
            a = configs[comparison["configuration_a"]]
            b = configs[comparison["configuration_b"]]
            changed = {key for key in a["values"] if a["values"][key] != b["values"][key]}
            self.assertEqual(changed, {focal[comparison["experiment"]]})
            self.assertEqual(comparison["focal_dimension"], focal[comparison["experiment"]])
            self.assertGreaterEqual(comparison["centroid_distance_km"], 0)
            self.assertGreaterEqual(comparison["selected_area_difference_km2"], 0)
            self.assertGreaterEqual(comparison["selected_area_ratio"], 1)
            self.assertGreaterEqual(comparison["intersection_area_km2"], 0)
            self.assertGreater(comparison["union_area_km2"], 0)
            self.assertGreaterEqual(comparison["jaccard_overlap"], 0)
            self.assertLessEqual(comparison["jaccard_overlap"], 1)
            self.assertNotIn("flux_difference", comparison)
        self.assertEqual(actual_counts, expected_counts)

    def test_threshold_comparison_metrics_match_canonical_geometry(self) -> None:
        a_id = "threshold|grid_deg=5|statistic_used=mean_flux|threshold_label=top1"
        b_id = "threshold|grid_deg=5|statistic_used=mean_flux|threshold_label=top20"
        comparison = next(
            row for row in self.payload["comparisons"]
            if {row["configuration_a"], row["configuration_b"]} == {a_id, b_id}
        )
        configs = {
            row["id"]: row
            for row in self.payload["experiments"]["threshold"]["configurations"]
        }
        a, b = configs[a_id], configs[b_id]
        expected_distance = haversine_km(
            a["metrics"]["centroid_lat"], a["metrics"]["centroid_lon"],
            b["metrics"]["centroid_lat"], b["metrics"]["centroid_lon"],
        )
        self.assertAlmostEqual(comparison["centroid_distance_km"], expected_distance)
        self.assertAlmostEqual(
            comparison["selected_area_difference_km2"],
            abs(a["metrics"]["selected_area_km2"] - b["metrics"]["selected_area_km2"]),
        )
        self.assertAlmostEqual(
            comparison["selected_area_ratio"],
            max(a["metrics"]["selected_area_km2"], b["metrics"]["selected_area_km2"])
            / min(a["metrics"]["selected_area_km2"], b["metrics"]["selected_area_km2"]),
        )


if __name__ == "__main__":
    unittest.main()
