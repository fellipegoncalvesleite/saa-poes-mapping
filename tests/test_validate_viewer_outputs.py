"""Unit tests for public-site payload validation and failure behavior."""
from __future__ import annotations

import copy
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd

from scripts.validate_viewer_outputs import (
    _grid_matches,
    deep_payload_matches,
    load_site_data,
    main,
)


ROOT = Path(__file__).resolve().parents[1]


class ViewerValidatorPredicateTests(unittest.TestCase):
    def test_canonical_grid_rejects_null_and_non_boolean_coverage_masks(self) -> None:
        actual = {
            "grid_deg": 5,
            "mask_column": "enough_samples_5deg",
            "columns": [
                "lat",
                "lon",
                "mean_flux",
                "median_flux",
                "sample_count",
                "covered",
                "north_south_km",
                "east_west_km",
                "cell_area_km2",
            ],
        }
        base = {
            "lat_bin_center": [-67.5],
            "lon_bin_center": [-97.5],
            "mean_flux": [1.0],
            "median_flux": [0.5],
            "sample_count": [31],
        }
        for invalid in (None, 1, "true"):
            with self.subTest(invalid=invalid):
                canonical = pd.DataFrame({**base, "enough_samples_5deg": [invalid]})
                ok, detail = _grid_matches(actual, canonical, 5)
                self.assertFalse(ok)
                self.assertIn("coverage values", detail)

    def test_canonical_grid_rejects_altered_physical_geometry(self) -> None:
        canonical = pd.DataFrame({
            "lat_bin_center": [-67.5], "lon_bin_center": [-97.5], "mean_flux": [1.0],
            "median_flux": [0.5], "sample_count": [31], "enough_samples_5deg": [True],
        })
        north_south = 6371.0 * math.radians(5)
        east_west = north_south * math.cos(math.radians(-67.5))
        north = math.radians(-65); south = math.radians(-70)
        area = 6371.0 ** 2 * math.radians(5) * (math.sin(north) - math.sin(south))
        actual = {
            "grid_deg": 5, "mask_column": "enough_samples_5deg",
            "columns": ["lat", "lon", "mean_flux", "median_flux", "sample_count", "covered", "north_south_km", "east_west_km", "cell_area_km2"],
            "cells": [[-67.5, -97.5, 1.0, 0.5, 31, True, north_south, east_west, area + 10]],
            "color_domains": {"mean_flux": [1.0, 1.0], "median_flux": [0.5, 0.5]},
        }
        ok, detail = _grid_matches(actual, canonical, 5)
        self.assertFalse(ok)
        self.assertIn("cell area", detail)

    def test_deep_comparison_uses_exact_discrete_values_and_fixed_float_tolerances(self) -> None:
        expected = {
            "count": 44,
            "selected": [1, 4, 9],
            "centroid": -21.154234123456,
            "covered": True,
        }
        within_tolerance = {**expected, "centroid": expected["centroid"] + 1e-11}
        altered_count = {**expected, "count": 43}
        altered_membership = {**expected, "selected": [1, 4, 8]}
        altered_float = {**expected, "centroid": expected["centroid"] + 1e-4}

        self.assertTrue(deep_payload_matches(within_tolerance, expected))
        self.assertFalse(deep_payload_matches(altered_count, expected))
        self.assertFalse(deep_payload_matches(altered_membership, expected))
        self.assertFalse(deep_payload_matches(altered_float, expected))

    def test_site_data_loader_accepts_neutral_json_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "viewer_data.json"
            path.write_text('{"schema_version": 1}\n', encoding="utf-8")
            self.assertEqual(load_site_data(path), {"schema_version": 1})

    def test_validator_fails_loudly_when_outputs_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            root = Path(tmp)
            result = main(table_dir=root / "tables", site_data_path=root / "viewer_data.json")
        self.assertEqual(result, 1)

    @unittest.skipUnless(
        (ROOT / "site" / "public" / "data" / "viewer_data.json").exists(),
        "generated site data is not present",
    )
    def test_current_payload_corruption_is_detected(self) -> None:
        actual = load_site_data(ROOT / "site" / "public" / "data" / "viewer_data.json")
        altered = copy.deepcopy(actual)
        altered["experiments"]["threshold"]["configurations"][0]["metrics"]["selected_cells"] += 1
        self.assertFalse(deep_payload_matches(altered, actual))


if __name__ == "__main__":
    unittest.main()
