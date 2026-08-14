#!/usr/bin/env python3
"""Build version-pinned Natural Earth context for the public site."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "site" / "public" / "data" / "geography.json"
REGION = {"lat_min": -70.0, "lat_max": 20.0, "lon_min": -100.0, "lon_max": 20.0}
REVISION = "v5.1.2"
BASE_URL = f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{REVISION}/geojson"
TERMS_URL = "https://www.naturalearthdata.com/about/terms-of-use/"
SOURCES = (
    {
        "layer": "coastlines",
        "filename": "ne_110m_coastline.geojson",
        "theme_version": "4.1.0",
        "information_url": "https://www.naturalearthdata.com/downloads/110m-physical-vectors/110m-coastline/",
    },
    {
        "layer": "borders",
        "filename": "ne_110m_admin_0_boundary_lines_land.geojson",
        "theme_version": "5.1.0",
        "information_url": "https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-boundary-lines/",
    },
)


def _download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "saa-poes-mapping site geography builder"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def _geometry_lines(geometry: dict[str, Any]) -> Iterable[list[list[float]]]:
    if geometry.get("type") == "LineString":
        yield geometry["coordinates"]
    elif geometry.get("type") == "MultiLineString":
        yield from geometry["coordinates"]
    else:
        raise ValueError(f"unsupported Natural Earth geometry type: {geometry.get('type')}")


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
            if len(line) >= 2 and _intersects_region(line):
                lines.append([[round(float(x), 6), round(float(y), 6)] for x, y in line])
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
        payload[source["layer"]] = _regional_lines(json.loads(raw))
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
    encoded = json.dumps(build_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(encoded, encoding="utf-8", newline="\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}; sha256 {hashlib.sha256(encoded.encode()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
