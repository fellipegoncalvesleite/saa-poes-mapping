"""Behavior tests for Checkpoint 5C magnetic generality helpers."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.magnetic_framing import concentration_metrics, magnetic_validity_table  # noqa: E402
from saa.magnetic_generality import (  # noqa: E402
    ReferenceBundle,
    add_cp5c_footprint_flags,
    assert_cross_satellite_schema_safe,
    classify_generality,
    compare_noaa19_reference,
    evaluate_satellite_support,
    finalize_generality_summary,
    footprint_cell_sets,
    ifc_counts,
    omni_fit_flag_diagnostic,
    plot_capture90_comparison,
    plot_separation_comparison,
    principal_summary_row,
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


def _reference_bundle(
    separation: float = 1.0,
    cells: set[tuple[float, float]] | None = None,
) -> ReferenceBundle:
    return ReferenceBundle(
        cell_sets={"top10_5deg_mean": cells or {(-20.0, -50.0)}},
        validity=pd.DataFrame(
            {
                "variable_name": ["Btot_sat"],
                "rows_total": [10],
                "rows_valid": [10],
                "rows_invalid": [0],
                "valid_min": [16000.0],
                "valid_max": [32000.0],
            }
        ),
        footprint_summary=pd.DataFrame(
            {
                "comparison_case": ["top10_5deg_mean"],
                "magnetic_variable": ["Btot_sat"],
                "inside_count": [2],
                "outside_count": [8],
                "median_inside": [16500.0],
                "median_outside": [20000.0],
                "iqr_inside": [500.0],
                "iqr_outside": [4000.0],
                "p10_inside": [16100.0],
                "p90_inside": [17000.0],
                "p10_outside": [17500.0],
                "p90_outside": [28000.0],
                "separation_metric": [separation],
            }
        ),
        concentration=pd.DataFrame(
            {
                "metric": ["fraction_below_regional_q25"],
                "footprint": ["top10"],
                "variable": ["Btot_sat"],
                "value": [1.0],
            }
        ),
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


class MagneticGeneralityRubricTests(unittest.TestCase):
    def test_low_btot_support_uses_predeclared_strict_boundaries(self) -> None:
        baseline = {
            "btot_separation_metric": 1.0,
            "l_igrf_separation_metric": 0.5,
            "mlt_separation_metric": 0.1,
            "btot_fraction_below_regional_q25": 0.51,
            "btot_regional_fraction_to_capture_90pct": 0.50,
        }
        cases = [
            (baseline, True),
            ({**baseline, "btot_separation_metric": 0.0}, False),
            ({**baseline, "btot_fraction_below_regional_q25": 0.50}, False),
            ({**baseline, "btot_regional_fraction_to_capture_90pct": 0.5000001}, False),
        ]

        for row, expected in cases:
            with self.subTest(row=row):
                low_btot, _ = evaluate_satellite_support(row)
                self.assertIs(low_btot, expected)

    def test_btot_dominance_uses_l_and_absolute_mlt_separation(self) -> None:
        baseline = {
            "btot_separation_metric": 1.0,
            "l_igrf_separation_metric": 0.5,
            "mlt_separation_metric": -0.9,
            "btot_fraction_below_regional_q25": 0.75,
            "btot_regional_fraction_to_capture_90pct": 0.25,
        }
        cases = [
            (baseline, True),
            ({**baseline, "l_igrf_separation_metric": 1.0}, False),
            ({**baseline, "mlt_separation_metric": -1.0}, False),
        ]

        for row, expected in cases:
            with self.subTest(row=row):
                _, dominance = evaluate_satellite_support(row)
                self.assertIs(dominance, expected)

    def test_consistent_requires_four_supporters_for_both_criteria(self) -> None:
        summary = pd.DataFrame(
            {
                "low_btot_support": [True, True, True, True, False],
                "btot_dominance_support": [True, True, True, True, False],
                "btot_separation_metric": [1.0, 1.0, 1.0, 1.0, 0.2],
            }
        )

        self.assertEqual(classify_generality(summary), "CONSISTENT")

    def test_mixed_covers_intermediate_support_counts(self) -> None:
        summary = pd.DataFrame(
            {
                "low_btot_support": [True, True, True, False, False],
                "btot_dominance_support": [True, True, True, True, False],
                "btot_separation_metric": [1.0, 1.0, 1.0, 0.2, 0.1],
            }
        )

        self.assertEqual(classify_generality(summary), "MIXED")

    def test_inconsistent_when_at_most_one_satellite_supports_low_btot(self) -> None:
        summary = pd.DataFrame(
            {
                "low_btot_support": [True, False, False, False, False],
                "btot_dominance_support": [True, True, True, True, True],
                "btot_separation_metric": [1.0, 0.2, 0.2, 0.2, 0.2],
            }
        )

        self.assertEqual(classify_generality(summary), "INCONSISTENT")

    def test_reversed_sign_safeguard_is_inconsistent(self) -> None:
        summary = pd.DataFrame(
            {
                "low_btot_support": [True, True, False, False, False],
                "btot_dominance_support": [True, True, True, True, False],
                "btot_separation_metric": [1.0, -0.1, -0.2, -0.3, -0.4],
            }
        )

        self.assertEqual(classify_generality(summary), "INCONSISTENT")


class MagneticGeneralityReferenceTests(unittest.TestCase):
    def test_noaa19_reference_requires_exact_discrete_values(self) -> None:
        expected = _reference_bundle()
        actual = _reference_bundle(cells={(-20.0, -55.0)})

        with self.assertRaises(AssertionError):
            compare_noaa19_reference(actual, expected)

    def test_noaa19_reference_uses_fixed_float_tolerances(self) -> None:
        expected = _reference_bundle(separation=1.0)
        within_tolerance = _reference_bundle(separation=1.0 + 5e-10)
        outside_tolerance = _reference_bundle(separation=1.0 + 2e-9)

        compare_noaa19_reference(within_tolerance, expected)
        with self.assertRaises(AssertionError):
            compare_noaa19_reference(outside_tolerance, expected)

    def test_cross_satellite_schema_rejects_absolute_flux_fields(self) -> None:
        assert_cross_satellite_schema_safe(
            ["satellite", "btot_separation_metric", "absolute_flux_comparison_allowed"]
        )
        for forbidden in ("mean_flux", "peak_flux", "flux_ratio_between_satellites"):
            with self.subTest(forbidden=forbidden), self.assertRaises(ValueError):
                assert_cross_satellite_schema_safe(["satellite", forbidden])


class MagneticGeneralityOutputTests(unittest.TestCase):
    def test_footprint_cell_sets_cover_all_accepted_cases(self) -> None:
        grid5 = _grid([(-67.5, -97.5, 10.0), (-62.5, -92.5, 1.0)], 5)
        grid2 = _grid([(-67.0, -97.0, 10.0), (-63.0, -93.0, 1.0)], 2)

        actual = footprint_cell_sets(grid5, grid2)

        self.assertEqual(
            actual,
            {
                "top10_5deg_mean": {(-67.5, -97.5)},
                "top5_5deg_mean": {(-67.5, -97.5)},
                "top10_2deg_mean": {(-67.0, -97.0)},
                "top5_2deg_mean": {(-67.0, -97.0)},
            },
        )

    def test_principal_summary_row_extracts_raw_metrics_and_counts(self) -> None:
        footprint_summary = pd.DataFrame(
            {
                "comparison_case": ["top10_5deg_mean"] * 3,
                "magnetic_variable": ["Btot_sat", "L_IGRF", "MLT"],
                "separation_metric": [1.2, 0.4, -0.1],
            }
        )
        concentration = pd.DataFrame(
            {
                "metric": [
                    "fraction_below_regional_q25",
                    "regional_fraction_to_capture_50pct",
                    "regional_fraction_to_capture_75pct",
                    "regional_fraction_to_capture_90pct",
                ],
                "footprint": ["top10"] * 4,
                "variable": ["Btot_sat"] * 4,
                "value": [0.8, 0.1, 0.2, 0.3],
            }
        )
        validity = pd.DataFrame(
            {
                "variable_name": ["Btot_sat", "L_IGRF", "MLT"],
                "rows_valid": [100, 95, 100],
                "rows_invalid": [0, 5, 0],
            }
        )
        flagged = pd.DataFrame({"in_top10_5deg": [True, True, False, False]})
        processing = {
            "regional_rows_before_ifc": 105,
            "regional_rows_after_ifc": 100,
            "ifc_on_dropped": 5,
            "ifc_minus1_retained": 90,
            "ifc_zero_retained": 10,
            "ifc_other_retained": 0,
            "top10_5deg_selected_cell_count": 44,
        }

        actual = principal_summary_row(
            "noaa15", footprint_summary, concentration, validity, flagged, processing
        )

        self.assertEqual(actual["satellite"], "noaa15")
        self.assertEqual(actual["analysis_month"], "2024-01")
        self.assertEqual(actual["btot_separation_metric"], 1.2)
        self.assertEqual(actual["l_igrf_separation_metric"], 0.4)
        self.assertEqual(actual["mlt_separation_metric"], -0.1)
        self.assertEqual(actual["btot_fraction_below_regional_q25"], 0.8)
        self.assertEqual(actual["btot_regional_fraction_to_capture_90pct"], 0.3)
        self.assertEqual(actual["selected_cell_count"], 44)
        self.assertEqual(actual["selected_sample_count"], 2)
        self.assertEqual(actual["l_igrf_rows_invalid"], 5)
        self.assertIs(actual["low_btot_support"], True)
        self.assertIs(actual["btot_dominance_support"], True)
        self.assertIs(actual["absolute_flux_comparison_allowed"], False)

    def test_finalize_generality_summary_adds_global_rubric_result(self) -> None:
        rows = []
        for i, satellite in enumerate(("noaa15", "noaa18", "noaa19", "metop01", "metop03")):
            rows.append(
                {
                    "satellite": satellite,
                    "low_btot_support": i < 4,
                    "btot_dominance_support": i < 4,
                    "btot_separation_metric": 1.0,
                    "absolute_flux_comparison_allowed": False,
                }
            )

        actual = finalize_generality_summary(rows)

        self.assertEqual(actual["cp5c_classification"].unique().tolist(), ["CONSISTENT"])
        self.assertTrue((actual["low_btot_support_count"] == 4).all())
        self.assertTrue((actual["btot_dominance_support_count"] == 4).all())
        self.assertTrue((actual["reversed_btot_sign_count"] == 0).all())

    def test_required_plots_are_created_and_nonempty(self) -> None:
        summary = pd.DataFrame(
            {
                "satellite": ["noaa15", "noaa18", "noaa19", "metop01", "metop03"],
                "btot_separation_metric": [1.0, 1.1, 1.2, 1.3, 1.4],
                "l_igrf_separation_metric": [0.2, 0.3, 0.4, 0.5, 0.6],
                "mlt_separation_metric": [0.0, 0.1, -0.1, 0.05, -0.05],
                "btot_regional_fraction_to_capture_90pct": [0.2, 0.2, 0.2, 0.2, 0.2],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            separation_path = Path(tmp) / "separation.png"
            capture_path = Path(tmp) / "capture.png"

            plot_separation_comparison(summary, separation_path)
            plot_capture90_comparison(summary, capture_path)

            self.assertGreater(separation_path.stat().st_size, 1000)
            self.assertGreater(capture_path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
