"""Unit tests for independent CP5C validator predicates."""
from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from scripts.validate_cp5c_outputs import (
    circularize_mlt_hours,
    expected_fit_flag_diagnostic,
    forbidden_cross_satellite_flux_columns,
    independent_classification,
    keyed_table_matches,
    main,
    notebook_has_outputs,
    semantic_table_pair_matches,
    source_name_matches_satellite,
)


class CP5CValidatorPredicateTests(unittest.TestCase):
    def test_mlt_circularization_is_invariant_to_clock_rotation(self) -> None:
        hours = np.array([22.0, 23.0, 0.0, 1.0, 2.0, 7.0])
        rotated = (hours + 5.5) % 24.0

        np.testing.assert_allclose(
            circularize_mlt_hours(hours),
            circularize_mlt_hours(rotated),
            rtol=0.0,
            atol=1e-12,
        )

    def test_notebook_requires_output_in_every_code_cell(self) -> None:
        executed = {
            "cells": [
                {"cell_type": "markdown", "source": ["# CP5C"]},
                {"cell_type": "code", "source": ["1 + 1"], "outputs": [{"output_type": "stream"}]},
            ]
        }
        missing_output = {
            "cells": [{"cell_type": "code", "source": ["1 + 1"], "outputs": []}]
        }

        self.assertTrue(notebook_has_outputs(executed))
        self.assertFalse(notebook_has_outputs(missing_output))

    def test_forbidden_flux_predicate_allows_only_explicit_false_flag(self) -> None:
        safe = ["satellite", "btot_separation_metric", "absolute_flux_comparison_allowed"]
        unsafe = safe + ["mean_flux", "satellite_flux_ratio"]

        self.assertEqual(forbidden_cross_satellite_flux_columns(safe), [])
        self.assertEqual(
            forbidden_cross_satellite_flux_columns(unsafe),
            ["mean_flux", "satellite_flux_ratio"],
        )

    def test_independent_classification_matches_frozen_boundaries(self) -> None:
        consistent = pd.DataFrame(
            {
                "low_btot_support": [True, True, True, True, False],
                "btot_dominance_support": [True, True, True, True, False],
                "btot_separation_metric": [1.0] * 5,
            }
        )
        reversed_sign = pd.DataFrame(
            {
                "low_btot_support": [True, True, False, False, False],
                "btot_dominance_support": [True, True, True, True, False],
                "btot_separation_metric": [1.0, -0.1, -0.2, -0.3, -0.4],
            }
        )

        self.assertEqual(independent_classification(consistent), "CONSISTENT")
        self.assertEqual(independent_classification(reversed_sign), "INCONSISTENT")

    def test_source_name_must_match_claimed_satellite(self) -> None:
        self.assertTrue(
            source_name_matches_satellite("poes_n15_20240131_proc.nc", "noaa15")
        )
        self.assertTrue(
            source_name_matches_satellite("poes_m03_20240101_proc.nc", "metop03")
        )
        self.assertFalse(
            source_name_matches_satellite("poes_n19_20240101_proc.nc", "noaa15")
        )
        self.assertFalse(source_name_matches_satellite("synthetic_noaa15.nc", "noaa15"))

    def test_keyed_table_comparison_rejects_corrupted_metrics_and_counts(self) -> None:
        expected = pd.DataFrame(
            {
                "case": ["top10"],
                "inside_count": [20],
                "separation_metric": [1.5],
            }
        )
        self.assertTrue(
            keyed_table_matches(
                expected.copy(), expected, ["case"], ["inside_count"], ["separation_metric"]
            )
        )
        altered_count = expected.assign(inside_count=19)
        altered_metric = expected.assign(separation_metric=1.5001)
        self.assertFalse(
            keyed_table_matches(
                altered_count, expected, ["case"], ["inside_count"], ["separation_metric"]
            )
        )
        self.assertFalse(
            keyed_table_matches(
                altered_metric, expected, ["case"], ["inside_count"], ["separation_metric"]
            )
        )

    def test_expected_fit_flag_diagnostic_preserves_each_flag_distribution(self) -> None:
        flagged = pd.DataFrame(
            {
                "mep_omni_flux_flag_fit": [0, 0, 1, 2],
                "in_top10_5deg": [True, False, True, False],
            }
        )

        actual = expected_fit_flag_diagnostic(flagged, "noaa18")

        regional_zero = actual.loc[
            (actual["scope"] == "regional_sample") & (actual["flag_value"] == 0)
        ].iloc[0]
        footprint_one = actual.loc[
            (actual["scope"] == "top10_5deg_mean_footprint")
            & (actual["flag_value"] == 1)
        ].iloc[0]
        self.assertEqual(int(regional_zero["sample_count"]), 2)
        self.assertAlmostEqual(float(regional_zero["fraction"]), 0.5)
        self.assertEqual(int(footprint_one["sample_count"]), 1)
        self.assertAlmostEqual(float(footprint_one["fraction"]), 0.5)

    def test_csv_parquet_semantic_comparison_detects_corruption(self) -> None:
        frame = pd.DataFrame(
            {"satellite": ["noaa15", "noaa18"], "metric": [1.5, 1.6], "support": [True, False]}
        )
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "result.csv"
            parquet_path = Path(tmp) / "result.parquet"
            frame.to_csv(csv_path, index=False)
            frame.to_parquet(parquet_path, index=False)
            self.assertTrue(semantic_table_pair_matches(csv_path, parquet_path))
            frame.assign(metric=[9.0, 1.6]).to_csv(csv_path, index=False)
            self.assertFalse(semantic_table_pair_matches(csv_path, parquet_path))

    def test_validator_fails_loudly_when_outputs_are_missing(self) -> None:
        with TemporaryDirectory() as tmp, redirect_stdout(StringIO()) as captured:
            exit_code = main(Path(tmp))

        self.assertEqual(exit_code, 1)
        self.assertIn("MISSING", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
