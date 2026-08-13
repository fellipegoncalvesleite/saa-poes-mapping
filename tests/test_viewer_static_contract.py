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

    def test_viewer_ends_after_interactive_cp5c_material_without_legacy_gallery(self) -> None:
        self.assertIn('id="cp5c-result"', self.html)
        self.assertNotIn("STATIC / DEBUG OUTPUTS", self.html)
        self.assertNotIn("../figures/", self.html)
        self.assertNotIn("<img", self.html)
        self.assertNotIn("Static/debug figures remain below", self.html)

    def test_experiment_remains_a_select(self) -> None:
        self.assertIn('<select id="experiment-control" aria-label="experiment"></select>', self.html)

    def test_experiment_scoped_controls_wrap_within_the_viewport(self) -> None:
        self.assertIn("#viewer-controls { display: flex; flex-wrap: wrap;", self.html)
        self.assertIn("#method-controls { display: flex; flex-wrap: wrap;", self.html)


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

    def test_only_ordered_payload_controls_use_discrete_range_inputs(self) -> None:
        self.assertIn(
            'const RANGE_CONTROL_KEYS = new Set(["threshold_label", "grid_deg", "channel"]);',
            self.source,
        )
        self.assertIn('slider.type = "range"', self.source)
        self.assertIn('slider.max = String(control.options.length - 1)', self.source)
        self.assertIn('const declared = control.options[Number(slider.value)]', self.source)
        self.assertNotIn('"window_label"]);', self.source)
        self.assertNotIn('"satellite"]);', self.source)
        self.assertNotIn('"statistic_used"]);', self.source)

    def test_current_grid_color_normalization_notice_is_unconditional(self) -> None:
        notice = '["color normalization", "within the current grid only"]'
        self.assertEqual(self.source.count(notice), 1)
        self.assertLess(self.source.index(notice), self.source.index('if (state.experiment === "threshold"'))


if __name__ == "__main__":
    unittest.main()
