"""Contracts for the public site's deterministic geographic context."""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "site" / "public" / "data" / "geography.json"
REGION = {"lat_min": -70.0, "lat_max": 20.0, "lon_min": -100.0, "lon_max": 20.0}


class SiteGeographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geography = json.loads(PATH.read_text(encoding="utf-8"))

    def test_asset_is_versioned_and_matches_the_scientific_region(self) -> None:
        self.assertEqual(self.geography["schema_version"], 1)
        self.assertEqual(self.geography["region"], REGION)
        self.assertEqual(self.geography["projection"], "WGS84 geographic longitude/latitude")
        self.assertEqual(self.geography["license"], "public domain")
        sources = {item["layer"]: item for item in self.geography["sources"]}
        self.assertEqual(set(sources), {"coastlines", "borders"})
        self.assertTrue(all(item["revision"] == "v5.1.2" for item in sources.values()))
        self.assertTrue(all(len(item["sha256"]) == 64 for item in sources.values()))

    def test_lines_are_finite_and_context_contains_south_america(self) -> None:
        for layer in ("coastlines", "borders"):
            self.assertGreater(len(self.geography[layer]), 0)
            for line in self.geography[layer]:
                self.assertGreaterEqual(len(line), 2)
                self.assertTrue(all(math.isfinite(value) for point in line for value in point))
        coast = [point for line in self.geography["coastlines"] for point in line]
        borders = [point for line in self.geography["borders"] for point in line]
        self.assertTrue(any(-55 < lon < -30 and -35 < lat < 10 for lon, lat in coast))
        self.assertTrue(any(-75 < lon < -45 and -35 < lat < 10 for lon, lat in borders))


if __name__ == "__main__":
    unittest.main()
