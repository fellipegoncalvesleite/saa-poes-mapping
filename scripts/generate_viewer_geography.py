#!/usr/bin/env python3
"""Build the viewer's local geographic context from version-pinned Natural Earth data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "viewer" / "geography.js"
REGION = {"lat_min": -70.0, "lat_max": 20.0, "lon_min": -100.0, "lon_max": 20.0}
REVISION = "v5.1.2"
BASE_URL = f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{REVISION}/geojson"
TERMS_URL = "https://www.naturalearthdata.com/about/terms-of-use/"
SOURCES = (
    {
        "layer": "coastlines",
        "filename": "ne_110m_coastline.geojson",
        "theme_version": "4.1.0",
        "information_url": (
            "https://www.naturalearthdata.com/downloads/110m-physical-vectors/"
            "110m-coastline/"
        ),
    },
    {
        "layer": "borders",
        "filename": "ne_110m_admin_0_boundary_lines_land.geojson",
        "theme_version": "5.1.0",
        "information_url": (
            "https://www.naturalearthdata.com/downloads/110m-cultural-vectors/"
            "110m-admin-0-boundary-lines/"
        ),
    },
)


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "saa-poes-mapping geography builder"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def _geometry_lines(geometry: dict[str, Any]) -> Iterable[list[list[float]]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "LineString":
        yield coordinates
    elif geometry_type == "MultiLineString":
        yield from coordinates
    else:
        raise ValueError(f"unsupported Natural Earth geometry type: {geometry_type}")


def _intersects_region(line: list[list[float]]) -> bool:
    longitudes = [float(point[0]) for point in line]
    latitudes = [float(point[1]) for point in line]
    return not (
        max(longitudes) < REGION["lon_min"]
        or min(longitudes) > REGION["lon_max"]
        or max(latitudes) < REGION["lat_min"]
        or min(latitudes) > REGION["lat_max"]
    )


def _regional_lines(document: dict[str, Any]) -> list[list[list[float]]]:
    lines = []
    for feature in document.get("features", []):
        for line in _geometry_lines(feature["geometry"]):
            if len(line) < 2 or not _intersects_region(line):
                continue
            lines.append(
                [[round(float(point[0]), 6), round(float(point[1]), 6)] for point in line]
            )
    return sorted(lines, key=lambda line: json.dumps(line, separators=(",", ":")))


def build_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "region": REGION,
        "projection": "WGS84 geographic longitude/latitude",
        "license": "public domain",
        "terms_url": TERMS_URL,
        "sources": [],
    }
    for source in SOURCES:
        url = f"{BASE_URL}/{source['filename']}"
        raw = _download(url)
        document = json.loads(raw)
        payload[source["layer"]] = _regional_lines(document)
        payload["sources"].append(
            {
                "layer": source["layer"],
                "dataset": "Natural Earth",
                "scale": "1:110m",
                "revision": REVISION,
                "theme_version": source["theme_version"],
                "url": url,
                "information_url": source["information_url"],
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return payload


def main() -> int:
    payload = build_payload()
    source = (
        "window.SAA_VIEWER_GEOGRAPHY = "
        + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + ";\n"
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(source, encoding="utf-8")
    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: "
        f"{len(payload['coastlines'])} coastline lines, {len(payload['borders'])} border lines"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
