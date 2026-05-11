#!/usr/bin/env python3
"""Validate Checkpoint 3 exploratory-map outputs.

Checks, against the **real** processed table and the generated figures:

* the processed one-day Parquet exists and references the real NCEI source file (no fake data)
* the four required figures exist and are non-empty
* the region-filtered dataset has > 0 rows
* longitude was converted to [-180, 180) and the region is within the requested box
* the 5deg and 2deg grids have at least some non-null cells
* the sample-count grid exists and has populated cells
* the top-flux grid cells can be computed

Exit 0 if every check passes, 1 otherwise.

Usage::  python scripts/validate_cp3_outputs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.grid_flux import (  # noqa: E402
    prepare_region, grid_statistics, top_cells, DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE,
)

PARQUET = ROOT / "data" / "processed" / "noaa19_2024-01-01_mep_omni_flux_p1.parquet"
EXPECTED_SOURCE = "poes_n19_20240101_proc.nc"
CHANNEL = "mep_omni_flux_p1"
FIGS = [
    "cp3_noaa19_2024-01-01_mean_flux_5deg.png",
    "cp3_noaa19_2024-01-01_median_flux_5deg.png",
    "cp3_noaa19_2024-01-01_mean_flux_2deg.png",
    "cp3_noaa19_2024-01-01_sample_count_5deg.png",
]
FIG_DIR = ROOT / "outputs" / "figures"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    # 1) processed parquet exists
    if not PARQUET.exists():
        check("processed parquet exists", False, str(PARQUET))
        return _report(checks)
    check("processed parquet exists", True, PARQUET.name)

    df = pd.read_parquet(PARQUET)

    # 2) no fake data: every row references the real NCEI source file
    srcs = set(df["source_file"].unique()) if "source_file" in df.columns else set()
    check("real source file referenced (no fake data)",
          srcs == {EXPECTED_SOURCE}, f"source_file values: {sorted(srcs)}")

    # 3) required figures exist and are non-empty
    for fig in FIGS:
        p = FIG_DIR / fig
        ok = p.exists() and p.stat().st_size > 1000
        check(f"figure exists: {fig}", ok, f"{p.stat().st_size} bytes" if p.exists() else "MISSING")

    # 4) region filter -> rows > 0
    region, counts = prepare_region(df, DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE)
    check("region-filtered rows > 0", len(region) > 0,
          f"{counts['n_total']} -> geo {counts['n_after_geo']} -> ifc {counts['n_after_ifc']}")

    # 5) longitude converted to [-180,180) and within requested region box
    if len(region):
        lon_ok = region["lon180"].between(-180, 180).all() and region["lon180"].between(-100, 20).all()
        lat_ok = region["lat"].between(-70, 20).all()
        check("longitude converted & region within box", bool(lon_ok and lat_ok),
              f"lon180 {region['lon180'].min():.2f}..{region['lon180'].max():.2f}; "
              f"lat {region['lat'].min():.2f}..{region['lat'].max():.2f}")

    # 6) grids have some non-null cells
    g5 = grid_statistics(region, CHANNEL, 5.0, 5.0, DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE)
    g2 = grid_statistics(region, CHANNEL, 2.0, 2.0, DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE)
    check("5deg grid has non-null cells", g5.n_nonempty > 0, f"{g5.n_nonempty}/{g5.n_cells}")
    check("2deg grid has non-null cells", g2.n_nonempty > 0, f"{g2.n_nonempty}/{g2.n_cells}")

    # 7) sample-count grid populated
    check("sample-count grid populated", int(g5.count.sum()) > 0, f"total samples={int(g5.count.sum())}")

    # 8) top-flux cells computable
    tm = top_cells(g5, "mean", 10)
    tmed = top_cells(g5, "median", 10)
    check("top-flux cells computable", len(tm) > 0 and len(tmed) > 0,
          f"mean rows={len(tm)}, median rows={len(tmed)}")

    return _report(checks)


def _report(checks: list[tuple[str, bool, str]]) -> int:
    print("=" * 66)
    print("CHECKPOINT 3 OUTPUT VALIDATION")
    print("=" * 66)
    all_ok = True
    for name, ok, detail in checks:
        all_ok &= ok
        line = f"[{'PASS' if ok else 'FAIL'}] {name}"
        if detail:
            line += f"  ->  {detail}"
        print(line)
    print("-" * 66)
    print("RESULT:", "ALL CHECKS PASSED" if all_ok else "ONE OR MORE CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
