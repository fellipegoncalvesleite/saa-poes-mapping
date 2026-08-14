"""Contracts for the public site's neutral scientific payload."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.viewer_export import build_viewer_payload, write_viewer_json  # noqa: E402
from scripts.validate_viewer_outputs import deep_payload_matches  # noqa: E402


class SiteJsonSerializationTests(unittest.TestCase):
    def test_writer_is_deterministic_neutral_json(self) -> None:
        payload = {"schema_version": 1, "nested": {"b": 2, "a": 1}}
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.json"
            second = Path(tmp) / "second.json"
            one = write_viewer_json(payload, first)
            two = write_viewer_json(payload, second)
            self.assertEqual(one, two)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(json.loads(first.read_text()), payload)
            self.assertFalse(first.read_text().startswith("window."))

    def test_site_payload_matches_fresh_canonical_export(self) -> None:
        expected = build_viewer_payload(ROOT / "outputs" / "tables")
        actual = json.loads((ROOT / "site/public/data/viewer_data.json").read_text())
        self.assertTrue(deep_payload_matches(actual, expected))
        self.assertEqual(
            sum(item["configuration_count"] for item in actual["experiments"].values()),
            340,
        )


if __name__ == "__main__":
    unittest.main()
