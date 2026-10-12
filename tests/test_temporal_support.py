import math
import unittest

import numpy as np
import pandas as pd

from saa.temporal_support import (
    area_jaccard, area_of, compare_window, distinct_days_per_cell, weighted_centroid,
)
from saa.threshold_analysis import cell_area_km2

MASK = "enough_samples_5deg"


def table(cells, values, passed=None, stat="mean_flux"):
    """Synthetic 5-degree grid table: cells are (lat, lon) centers."""
    passed = [True] * len(cells) if passed is None else passed
    return pd.DataFrame({
        "lat_bin_center": [c[0] for c in cells], "lon_bin_center": [c[1] for c in cells],
        stat: values, "median_flux": values, "sample_count": [30] * len(cells), MASK: passed,
    })


CELLS = [(-27.5, -52.5), (-22.5, -47.5), (-17.5, -42.5), (-62.5, -97.5), (12.5, 17.5)]


def run(w, m, pct=80):
    return compare_window(w, m, grid_deg=5, mask_col=MASK, stat="mean_flux", percentile=pct)


class TemporalSupportTests(unittest.TestCase):
    def test_identical_maps_agree_exactly(self):
        t = table(CELLS, [5.0, 4.0, 3.0, 1.0, 0.5])
        r = run(t, t)
        self.assertEqual(r["area_jaccard_original"], 1.0)
        self.assertEqual(r["centroid_distance_km_original"], 0.0)
        self.assertEqual(r["area_jaccard_common"], 1.0)
        self.assertEqual(r["monthly_footprint_observability"], 1.0)
        self.assertEqual(r["original_undefined_reason"], "")

    def test_disjoint_footprints_have_zero_jaccard(self):
        m = table(CELLS, [5.0, 1.0, 1.0, 1.0, 1.0])
        w = table(CELLS, [1.0, 1.0, 1.0, 1.0, 5.0])
        r = run(w, m, pct=90)
        self.assertEqual(r["area_jaccard_original"], 0.0)
        self.assertGreater(r["centroid_distance_km_original"], 0.0)

    def test_absent_common_support_is_undefined_not_zero(self):
        m = table(CELLS[:2], [5.0, 4.0])
        w = table(CELLS[3:], [5.0, 4.0])
        r = run(w, m)
        self.assertEqual(r["common_support_cells"], 0)
        self.assertEqual(r["common_undefined_reason"], "empty_common_support")
        self.assertTrue(math.isnan(r["area_jaccard_common"]))
        self.assertEqual(r["monthly_footprint_observability"], 0.0)

    def test_empty_union_is_undefined(self):
        value, reason = area_jaccard(set(), set(), 5.0)
        self.assertTrue(math.isnan(value))
        self.assertEqual(reason, "empty_union")

    def test_unequal_cell_area_differs_from_count_jaccard(self):
        a = {(-2.5, -52.5), (-67.5, -52.5)}
        b = {(-2.5, -52.5)}
        value, _ = area_jaccard(a, b, 5.0)
        equatorial = cell_area_km2(-2.5, 5, 5)
        polar = cell_area_km2(-67.5, 5, 5)
        self.assertAlmostEqual(value, equatorial / (equatorial + polar), places=12)
        self.assertNotAlmostEqual(value, 0.5, places=3)
        self.assertAlmostEqual(area_of(a, 5.0), equatorial + polar, places=6)

    def test_threshold_ties_are_all_selected(self):
        t = table(CELLS, [5.0, 5.0, 5.0, 1.0, 1.0])
        r = run(t, t, pct=80)
        self.assertEqual(r["window_selected_cells_original"], 3)

    def test_valid_zero_is_eligible_but_zero_mass_is_undefined(self):
        t = table(CELLS[:3], [0.0, 0.0, 0.0])
        r = run(t, t)
        self.assertEqual(r["window_coverage_passed_cells"], 3)
        self.assertEqual(r["window_selected_cells_original"], 3)
        self.assertIn("zero_mass", r["original_undefined_reason"])
        self.assertTrue(math.isnan(r["centroid_distance_km_original"]))
        lat, lon, reason = weighted_centroid(t, "mean_flux", 5.0)
        self.assertEqual(reason, "zero_mass")

    def test_missing_flux_is_not_zero_filled(self):
        t = table(CELLS, [5.0, 4.0, np.nan, 1.0, 0.5])
        r = run(t, t)
        self.assertEqual(r["window_coverage_passed_cells"], 4)
        self.assertEqual(r["window_valid_observed_cells"], 4)

    def test_coverage_change_alone_separates_end_to_end_from_conditional(self):
        # Same field values; the window loses coverage on the highest cell only.
        values = [9.0, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.5]
        cells = [(-67.5 + 5 * i, -52.5) for i in range(10)]
        m = table(cells, values)
        w = table(cells, values, passed=[False] + [True] * 9)
        r = run(w, m, pct=80)
        self.assertLess(r["area_jaccard_original"], 1.0)
        self.assertLess(r["monthly_footprint_observability"], 1.0)
        self.assertEqual(r["common_support_cells"], 9)
        self.assertEqual(r["area_jaccard_common"], 1.0)
        self.assertEqual(r["centroid_distance_km_common"], 0.0)
        self.assertEqual(r["window_observed_below_coverage_cells"], 1)

    def test_distinct_days_counts_days_not_records(self):
        region = pd.DataFrame({
            "time": pd.to_datetime(["2024-01-01T01:00Z", "2024-01-01T02:00Z", "2024-01-02T00:00Z",
                                    "2024-01-03T00:00Z"]),
            "lat": [-27.0, -27.0, -27.0, -27.0], "lon180": [-52.0, -52.0, -52.0, -52.0],
            "mep_omni_flux_p1": [1.0, 2.0, 3.0, np.nan],
        })
        d = distinct_days_per_cell(region, "mep_omni_flux_p1", 5)
        self.assertEqual(d.distinct_valid_days.tolist(), [2])


if __name__ == "__main__":
    unittest.main()
