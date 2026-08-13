#!/usr/bin/env python3
"""Generate the file-openable static viewer data from validated checkpoint tables."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.viewer_export import build_viewer_payload, write_viewer_data  # noqa: E402


def main() -> int:
    output = ROOT / "outputs" / "viewer" / "viewer_data.js"
    payload = build_viewer_payload(ROOT / "outputs" / "tables")
    digest = write_viewer_data(payload, output)
    counts = {
        name: spec["configuration_count"]
        for name, spec in payload["experiments"].items()
    }
    print(f"wrote {output.relative_to(ROOT)}")
    print(f"sha256 {digest}")
    print(f"configurations {counts}")
    print(f"deduplicated grids {len(payload['grids'])}")
    print(f"CP5C {payload['cp5c']['classification']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
