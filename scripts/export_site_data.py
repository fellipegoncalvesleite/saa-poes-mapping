#!/usr/bin/env python3
"""Generate the public site's neutral JSON from canonical viewer authority."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.viewer_export import build_viewer_payload, write_viewer_json  # noqa: E402


def main() -> int:
    output = ROOT / "site" / "public" / "data" / "viewer_data.json"
    payload = build_viewer_payload(ROOT / "outputs" / "tables")
    digest = write_viewer_json(payload, output)
    counts = {name: item["configuration_count"] for name, item in payload["experiments"].items()}
    print(f"wrote {output.relative_to(ROOT)}")
    print(f"sha256 {digest}")
    print(f"configurations {counts}; total={sum(counts.values())}")
    print(f"deduplicated grids {len(payload['grids'])}; CP5C {payload['cp5c']['classification']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
