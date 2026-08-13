"""Unit tests for static-viewer validation predicates and failure behavior."""
from __future__ import annotations

import copy
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd

from scripts.validate_viewer_outputs import (
    _grid_matches,
    deep_payload_matches,
    main,
    static_files_are_file_openable,
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

    def test_static_contract_rejects_fetch_and_module_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            viewer = Path(tmp)
            (viewer / "viewer_data.js").write_text("window.SAA_VIEWER_DATA = {};\n", encoding="utf-8")
            (viewer / "geography.js").write_text(
                'window.SAA_VIEWER_GEOGRAPHY = {"region":{"lat_min":-70.0,'
                '"lat_max":20.0,"lon_min":-100.0,"lon_max":20.0},'
                '"coastlines":[[[-40,-10],[-35,-5]]],'
                '"borders":[[[-60,-20],[-55,-15]]]};\n',
                encoding="utf-8",
            )
            (viewer / "viewer.js").write_text("fetch('data.json');\n", encoding="utf-8")
            (viewer / "index.html").write_text(
                '<script type="module" src="viewer.js"></script>', encoding="utf-8"
            )
            ok, details = static_files_are_file_openable(viewer)

            self.assertFalse(ok)
            self.assertIn("fetch", details)
            self.assertIn("module", details)

    def test_static_contract_requires_the_bundled_geography_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            viewer = Path(tmp)
            (viewer / "viewer_data.js").write_text(
                "window.SAA_VIEWER_DATA = {};\n", encoding="utf-8"
            )
            (viewer / "viewer.js").write_text("void 0;\n", encoding="utf-8")
            (viewer / "index.html").write_text(
                '<script src="viewer_data.js"></script>'
                '<script src="geography.js"></script>'
                '<script src="viewer.js"></script>',
                encoding="utf-8",
            )

            ok, details = static_files_are_file_openable(viewer)

            self.assertFalse(ok)
            self.assertIn("geography.js", details)

    def test_validator_fails_loudly_when_outputs_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            root = Path(tmp)
            result = main(table_dir=root / "tables", viewer_dir=root / "viewer")
        self.assertEqual(result, 1)

    @unittest.skipUnless(
        (ROOT / "outputs" / "viewer" / "viewer_data.js").exists(),
        "generated viewer data is not present",
    )
    def test_current_payload_corruption_is_detected(self) -> None:
        from scripts.validate_viewer_outputs import load_viewer_data

        actual = load_viewer_data(ROOT / "outputs" / "viewer" / "viewer_data.js")
        altered = copy.deepcopy(actual)
        altered["experiments"]["threshold"]["configurations"][0]["metrics"]["selected_cells"] += 1
        self.assertFalse(deep_payload_matches(altered, actual))


class ViewerLauncherContractTests(unittest.TestCase):
    def test_launcher_supports_macos_linux_and_legacy_command(self) -> None:
        launcher = (ROOT / "scripts" / "open_viewer.sh").read_text(encoding="utf-8")
        legacy = (ROOT / "scripts" / "open_cp3_viewer.sh").read_text(encoding="utf-8")

        self.assertIn("Darwin", launcher)
        self.assertIn("open", launcher)
        self.assertIn("xdg-open", launcher)
        self.assertIn("open_viewer.sh", legacy)


if __name__ == "__main__":
    unittest.main()
