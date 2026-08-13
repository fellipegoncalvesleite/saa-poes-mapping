"""Unit tests for independent CP5C validator predicates."""
from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from scripts.validate_cp5c_outputs import (
    forbidden_cross_satellite_flux_columns,
    independent_classification,
    main,
    notebook_has_outputs,
    source_name_matches_satellite,
)


class CP5CValidatorPredicateTests(unittest.TestCase):
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

    def test_validator_fails_loudly_when_outputs_are_missing(self) -> None:
        with TemporaryDirectory() as tmp, redirect_stdout(StringIO()) as captured:
            exit_code = main(Path(tmp))

        self.assertEqual(exit_code, 1)
        self.assertIn("MISSING", captured.getvalue())


if __name__ == "__main__":
    unittest.main()
