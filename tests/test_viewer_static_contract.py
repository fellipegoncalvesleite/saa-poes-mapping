"""Static-source contract tests for the file-openable scientific viewer."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / "outputs" / "viewer"


class ViewerHtmlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (VIEWER / "index.html").read_text(encoding="utf-8")

    def test_viewer_uses_ordered_classic_scripts_and_no_network_loader(self) -> None:
        data_script = '<script src="viewer_data.js"></script>'
        render_script = '<script src="viewer.js"></script>'
        self.assertIn(data_script, self.html)
        self.assertIn(render_script, self.html)
        self.assertLess(self.html.index(data_script), self.html.index(render_script))
        self.assertNotIn('type="module"', self.html)
        self.assertNotIn("fetch(", self.html)

    def test_interactive_hooks_and_scientific_caveats_are_visible(self) -> None:
        for hook in (
            'id="experiment-control"',
            'id="method-controls"',
            'id="flux-map"',
            'id="configuration-readout"',
            'id="cp5c-result"',
        ):
            self.assertIn(hook, self.html)
        for statement in (
            "not a final SAA boundary",
            "not dose",
            "not health risk",
            "cross-satellite absolute flux",
            "coverage-failed",
        ):
            self.assertIn(statement, self.html)

    def test_existing_evidence_is_preserved_under_static_debug_outputs(self) -> None:
        self.assertIn("STATIC / DEBUG OUTPUTS", self.html)
        self.assertIn("cp3_noaa19_2024-01-01_mean_flux_5deg.png", self.html)
        self.assertIn("cp5b_flux_profile_by_Btot_sat.png", self.html)
        self.assertIn("cp5c_multisatellite_magnetic_separation_top10_5deg_mean.png", self.html)
        self.assertIn("cp5c_multisatellite_low_btot_capture90_top10_5deg_mean.png", self.html)


class ViewerJavascriptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (VIEWER / "viewer.js").read_text(encoding="utf-8")

    def test_javascript_only_renders_precomputed_payload(self) -> None:
        self.assertIn("window.SAA_VIEWER_DATA", self.source)
        self.assertIn("selected_cell_indices", self.source)
        self.assertIn("centroid_lat", self.source)
        self.assertIn("createElementNS", self.source)
        self.assertNotIn("fetch(", self.source)
        self.assertNotIn("percentile", self.source.lower())
        self.assertNotIn("quantile", self.source.lower())

    def test_all_experiments_are_explicitly_available(self) -> None:
        for experiment in ("threshold", "channel", "time", "satellite"):
            self.assertIn(f'"{experiment}"', self.source)

    def test_current_grid_color_normalization_notice_is_unconditional(self) -> None:
        notice = '["color normalization", "within the current grid only"]'
        self.assertEqual(self.source.count(notice), 1)
        self.assertLess(self.source.index(notice), self.source.index('if (state.experiment === "threshold"'))


if __name__ == "__main__":
    unittest.main()
