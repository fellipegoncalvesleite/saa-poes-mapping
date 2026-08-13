"""Behavioral contracts for the viewer's bundled geographic context."""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GEOGRAPHY_PATH = ROOT / "outputs" / "viewer" / "geography.js"
REGION = {"lat_min": -70.0, "lat_max": 20.0, "lon_min": -100.0, "lon_max": 20.0}


def load_geography() -> dict:
    source = GEOGRAPHY_PATH.read_text(encoding="utf-8")
    prefix = "window.SAA_VIEWER_GEOGRAPHY = "
    suffix = ";\n"
    if not source.startswith(prefix) or not source.endswith(suffix):
        raise ValueError("geography.js is not the required classic global assignment")
    return json.loads(source[len(prefix) : -len(suffix)])


def line_intersects_region(line: list[list[float]]) -> bool:
    longitudes = [point[0] for point in line]
    latitudes = [point[1] for point in line]
    return not (
        max(longitudes) < REGION["lon_min"]
        or min(longitudes) > REGION["lon_max"]
        or max(latitudes) < REGION["lat_min"]
        or min(latitudes) > REGION["lat_max"]
    )


class ViewerGeographyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geography = load_geography()

    def test_asset_declares_real_versioned_natural_earth_sources(self) -> None:
        self.assertEqual(self.geography["schema_version"], 1)
        self.assertEqual(self.geography["region"], REGION)
        self.assertEqual(self.geography["projection"], "WGS84 geographic longitude/latitude")
        self.assertEqual(self.geography["license"], "public domain")
        self.assertEqual(
            self.geography["terms_url"],
            "https://www.naturalearthdata.com/about/terms-of-use/",
        )
        sources = {source["layer"]: source for source in self.geography["sources"]}
        self.assertEqual(set(sources), {"coastlines", "borders"})
        for layer, expected_theme in (
            ("coastlines", "ne_110m_coastline.geojson"),
            ("borders", "ne_110m_admin_0_boundary_lines_land.geojson"),
        ):
            source = sources[layer]
            self.assertEqual(source["dataset"], "Natural Earth")
            self.assertEqual(source["revision"], "v5.1.2")
            self.assertTrue(source["url"].endswith(f"/v5.1.2/geojson/{expected_theme}"))
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")

    def test_linework_is_finite_wgs84_geometry_intersecting_the_viewer_region(self) -> None:
        for layer in ("coastlines", "borders"):
            lines = self.geography[layer]
            self.assertGreater(len(lines), 0)
            for line in lines:
                self.assertGreaterEqual(len(line), 2)
                self.assertTrue(line_intersects_region(line))
                for point in line:
                    self.assertEqual(len(point), 2)
                    longitude, latitude = point
                    self.assertTrue(math.isfinite(longitude))
                    self.assertTrue(math.isfinite(latitude))
                    self.assertGreaterEqual(longitude, -180.0)
                    self.assertLessEqual(longitude, 180.0)
                    self.assertGreaterEqual(latitude, -90.0)
                    self.assertLessEqual(latitude, 90.0)

    def test_regional_context_contains_south_american_coast_and_country_boundaries(self) -> None:
        coastline_points = [point for line in self.geography["coastlines"] for point in line]
        border_points = [point for line in self.geography["borders"] for point in line]

        self.assertTrue(any(-55 < lon < -30 and -35 < lat < 10 for lon, lat in coastline_points))
        self.assertTrue(any(-75 < lon < -45 and -35 < lat < 10 for lon, lat in border_points))


if __name__ == "__main__":
    unittest.main()
