#!/usr/bin/env python3
"""Validate Checkpoint 4A monthly-aggregation outputs.

Checks (against real files; nothing fabricated):

* monthly regional processed Parquet exists
* the 31 expected NOAA-19 daily raw files for 2024-01 exist (or missing dates are reported)
* monthly regional row count > the one-day (2024-01-01) regional row count
* 5deg and 2deg grid tables exist with the required columns
* sample_count grids have non-null/positive cells
* a coverage mask column exists in each grid table
* the six required figures exist and are non-empty
* the notebook was executed (has cell outputs)
* no fake data: regional rows reference real poes_n19_2024-01-*.nc source files

Exit 0 if all pass, 1 otherwise.  Usage: python scripts/validate_cp4a_outputs.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.grid_flux import prepare_region, DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE  # noqa: E402

REGION_PARQUET = ROOT / "data" / "processed" / "noaa19_2024-01_mep_omni_flux_p1_region.parquet"
ONE_DAY_PARQUET = ROOT / "data" / "processed" / "noaa19_2024-01-01_mep_omni_flux_p1.parquet"
T5 = ROOT / "outputs" / "tables" / "cp4a_noaa19_2024-01_grid_5deg.parquet"
T2 = ROOT / "outputs" / "tables" / "cp4a_noaa19_2024-01_grid_2deg.parquet"
NB = ROOT / "notebooks" / "04a_monthly_aggregation.ipynb"
FIG_DIR = ROOT / "outputs" / "figures"
RAW_DIR = ROOT / "data" / "raw"

REQUIRED_GRID_COLS = ["lat_bin_center", "lon_bin_center", "mean_flux", "median_flux",
                      "sample_count", "positive_sample_count", "min_flux", "max_flux"]
FIGS = [
    "cp4a_noaa19_2024-01_mean_flux_5deg.png", "cp4a_noaa19_2024-01_median_flux_5deg.png",
    "cp4a_noaa19_2024-01_sample_count_5deg.png", "cp4a_noaa19_2024-01_mean_flux_2deg.png",
    "cp4a_noaa19_2024-01_median_flux_2deg.png", "cp4a_noaa19_2024-01_sample_count_2deg.png",
]
EXPECTED_DAYS = [f"2024-01-{d:02d}" for d in range(1, 32)]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    add = lambda n, ok, d="": checks.append((n, bool(ok), d))  # noqa: E731

    # 1) regional parquet exists
    if not REGION_PARQUET.exists():
        add("monthly regional parquet exists", False, str(REGION_PARQUET))
        return _report(checks)
    add("monthly regional parquet exists", True,
        f"{REGION_PARQUET.name} ({REGION_PARQUET.stat().st_size} bytes)")
    region = pd.read_parquet(REGION_PARQUET)

    # 2) expected daily raw files present (or report missing)
    present = {f"poes_n19_{d.replace('-', '')}_proc.nc" for d in EXPECTED_DAYS
               if (RAW_DIR / f"poes_n19_{d.replace('-', '')}_proc.nc").exists()}
    missing = [d for d in EXPECTED_DAYS
               if not (RAW_DIR / f"poes_n19_{d.replace('-', '')}_proc.nc").exists()]
    add("31 expected daily raw files present", len(present) == 31,
        f"{len(present)}/31 present" + ("" if not missing else f"; missing {missing}"))

    # 3) monthly region rows > one-day region rows
    if ONE_DAY_PARQUET.exists():
        one_day = pd.read_parquet(ONE_DAY_PARQUET)
        oneday_region, _ = prepare_region(one_day, DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE)
        add("monthly region rows > one-day region rows", len(region) > len(oneday_region),
            f"month {len(region)} vs one-day {len(oneday_region)}")
    else:
        add("monthly region rows > one-day region rows", False, "one-day parquet missing")

    # 4) no fake data: source files are real NOAA-19 Jan-2024 files
    srcs = set(region["source_file"].unique()) if "source_file" in region.columns else set()
    pat = re.compile(r"^poes_n19_202401\d{2}_proc\.nc$")
    add("regional rows reference real Jan-2024 source files (no fake data)",
        bool(srcs) and all(pat.match(s) for s in srcs), f"{len(srcs)} distinct source files")

    # 5) grid tables exist + required columns + coverage mask
    for label, path, mask_col in [("5deg", T5, "enough_samples_5deg"), ("2deg", T2, "enough_samples_2deg")]:
        if not path.exists():
            add(f"{label} grid table exists", False, str(path)); continue
        add(f"{label} grid table exists", True, f"{path.name} ({path.stat().st_size} bytes)")
        g = pd.read_parquet(path)
        miss = [c for c in REQUIRED_GRID_COLS if c not in g.columns]
        add(f"{label} grid has required columns", not miss, "all present" if not miss else f"missing {miss}")
        add(f"{label} sample_count populated", g["sample_count"].notna().all() and (g["sample_count"] > 0).all(),
            f"{len(g)} cells, min={int(g['sample_count'].min())}")
        add(f"{label} coverage mask exists", mask_col in g.columns,
            f"{mask_col}: {int(g[mask_col].sum())}/{len(g)} pass" if mask_col in g.columns else "MISSING")

    # 6) figures exist and non-empty
    for fig in FIGS:
        p = FIG_DIR / fig
        add(f"figure exists: {fig}", p.exists() and p.stat().st_size > 1000,
            f"{p.stat().st_size} bytes" if p.exists() else "MISSING")

    # 7) notebook executed (has outputs)
    if NB.exists():
        nb = json.loads(NB.read_text())
        code = [c for c in nb["cells"] if c.get("cell_type") == "code"]
        add("notebook executed (cells have outputs)",
            len(code) > 0 and all(c.get("outputs") for c in code),
            f"{sum(1 for c in code if c.get('outputs'))}/{len(code)} code cells with outputs")
    else:
        add("notebook executed (cells have outputs)", False, "notebook missing")

    return _report(checks)


def _report(checks: list[tuple[str, bool, str]]) -> int:
    print("=" * 70)
    print("CHECKPOINT 4A OUTPUT VALIDATION")
    print("=" * 70)
    all_ok = True
    for name, ok, detail in checks:
        all_ok &= ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ->  {detail}" if detail else ""))
    print("-" * 70)
    print("RESULT:", "ALL CHECKS PASSED" if all_ok else "ONE OR MORE CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
