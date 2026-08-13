"""Behavior tests for Checkpoint 5C magnetic generality helpers."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.magnetic_framing import concentration_metrics, magnetic_validity_table  # noqa: E402
from saa.magnetic_generality import (  # noqa: E402
    add_cp5c_footprint_flags,
    ifc_counts,
    omni_fit_flag_diagnostic,
    summaries_by_satellite,
    validity_by_satellite,
)


def _grid(rows: list[tuple[float, float, float]], resolution: int) -> pd.DataFrame:
    mask = f"enough_samples_{resolution}deg"
    return pd.DataFrame(
        {
            "lat_bin_center": [r[0] for r in rows],
            "lon_bin_center": [r[1] for r in rows],
            "mean_flux": [r[2] for r in rows],
            mask: [True] * len(rows),
        }
    )


class MagneticGeneralityCoreTests(unittest.TestCase):
    def test_footprint_membership_is_satellite_specific(self) -> None:
        region = pd.DataFrame(
            {
                "lat": [-67.2, -62.2],
                "lon180": [-97.2, -92.2],
            }
        )
        grids_a = (
            _grid([(-67.5, -97.5, 10.0), (-62.5, -92.5, 1.0)], 5),
            _grid([(-67.0, -97.0, 10.0), (-63.0, -93.0, 1.0)], 2),
        )
        grids_b = (
            _grid([(-67.5, -97.5, 1.0), (-62.5, -92.5, 10.0)], 5),
            _grid([(-67.0, -97.0, 1.0), (-63.0, -93.0, 10.0)], 2),
        )

        flagged_a = add_cp5c_footprint_flags(region, *grids_a)
        flagged_b = add_cp5c_footprint_flags(region, *grids_b)

        self.assertEqual(flagged_a["in_top10_5deg"].tolist(), [True, False])
        self.assertEqual(flagged_b["in_top10_5deg"].tolist(), [False, True])
        self.assertEqual(flagged_a["in_top10_2deg"].tolist(), [True, False])
        self.assertEqual(flagged_b["in_top10_2deg"].tolist(), [False, True])

    def test_validity_reuses_cp5b_rules(self) -> None:
        frame = pd.DataFrame(
            {
                "Btot_sat": [10.0, 0.0, np.nan],
                "L_IGRF": [1.2, -1.0, 0.0],
                "mag_lat_sat": [0.0, 91.0, -91.0],
                "mag_lon_sat": [0.0, 360.0, 361.0],
                "MLT": [0.0, 24.0, 25.0],
            }
        )
        expected = magnetic_validity_table(frame)

        actual = validity_by_satellite(frame, "noaa15")

        self.assertEqual(actual.pop("satellite").tolist(), ["noaa15"] * len(expected))
        self.assertEqual(actual.pop("analysis_month").tolist(), ["2024-01"] * len(expected))
        assert_frame_equal(actual.reset_index(drop=True), expected.reset_index(drop=True))

    def test_l_igrf_minus_one_is_excluded(self) -> None:
        frame = pd.DataFrame(
            {
                "Btot_sat": [10.0, 11.0, 12.0],
                "L_IGRF": [1.2, -1.0, 1.5],
                "mag_lat_sat": [0.0, 1.0, 2.0],
                "mag_lon_sat": [10.0, 20.0, 30.0],
                "MLT": [1.0, 2.0, 3.0],
            }
        )

        validity = validity_by_satellite(frame, "noaa19")
        l_row = validity.loc[validity["variable_name"] == "L_IGRF"].iloc[0]

        self.assertEqual(int(l_row["rows_valid"]), 2)
        self.assertEqual(int(l_row["rows_invalid"]), 1)
        self.assertEqual(float(l_row["valid_min"]), 1.2)

    def test_ifc_counts_drop_one_and_retain_minus_one(self) -> None:
        filtered = pd.DataFrame({"mep_IFC_on": [-1, 0, -1]})
        preparation = {
            "n_after_geo": 4,
            "n_ifc_on_dropped": 1,
            "n_ifc_minus1": 2,
            "n_after_ifc": 3,
        }

        actual = ifc_counts(filtered, preparation)

        self.assertEqual(
            actual,
            {
                "regional_rows_before_ifc": 4,
                "regional_rows_after_ifc": 3,
                "ifc_on_dropped": 1,
                "ifc_minus1_retained": 2,
                "ifc_zero_retained": 1,
                "ifc_other_retained": 0,
            },
        )

    def test_concentration_matches_cp5b_primitive(self) -> None:
        frame = pd.DataFrame(
            {
                "Btot_sat": [10.0, 20.0, 30.0, 40.0],
                "L_IGRF": [1.1, 1.2, 1.3, 1.4],
                "mag_lat_sat": [-10.0, -9.0, 10.0, 11.0],
                "MLT": [1.0, 2.0, 3.0, 4.0],
                "in_top10_5deg": [True, True, False, False],
                "in_top5_5deg": [True, False, False, False],
                "in_top10_2deg": [True, True, False, False],
                "in_top5_2deg": [True, False, False, False],
            }
        )
        expected = concentration_metrics(frame)

        _, actual = summaries_by_satellite(frame, "metop01")

        self.assertEqual(actual.pop("satellite").tolist(), ["metop01"] * len(expected))
        self.assertEqual(actual.pop("analysis_month").tolist(), ["2024-01"] * len(expected))
        assert_frame_equal(actual.reset_index(drop=True), expected.reset_index(drop=True))
        capture90 = actual.loc[
            (actual["metric"] == "regional_fraction_to_capture_90pct")
            & (actual["footprint"] == "top10")
            & (actual["variable"] == "Btot_sat"),
            "value",
        ].iloc[0]
        self.assertAlmostEqual(float(capture90), 0.475)

    def test_omni_fit_flag_diagnostic_does_not_filter(self) -> None:
        frame = pd.DataFrame(
            {
                "mep_omni_flux_flag_fit": [0, 1, 1, 2],
                "in_top10_5deg": [True, True, False, True],
            }
        )

        diagnostic = omni_fit_flag_diagnostic(frame, "metop03")

        regional = diagnostic.loc[diagnostic["scope"] == "regional_sample"]
        footprint = diagnostic.loc[diagnostic["scope"] == "top10_5deg_mean_footprint"]
        self.assertEqual(int(regional["sample_count"].sum()), 4)
        self.assertEqual(set(regional["flag_value"]), {0, 1, 2})
        self.assertEqual(int(footprint["sample_count"].sum()), 3)
        self.assertEqual(set(footprint["flag_value"]), {0, 1, 2})
        self.assertTrue((regional["scope_total"] == 4).all())
        self.assertTrue((footprint["scope_total"] == 3).all())
        self.assertEqual(len(frame), 4)


if __name__ == "__main__":
    unittest.main()
