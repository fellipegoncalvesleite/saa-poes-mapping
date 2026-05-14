#!/usr/bin/env python3
"""Validate Checkpoint 4C proton-channel-sensitivity outputs.

Checks (against real data; nothing fabricated):

* the 31 NOAA-19 Jan-2024 raw daily files exist (or report missing)
* the multi-channel regional processed Parquet exists and contains p1, p2, p3
* missing-value rate is computed per channel
* grid tables exist for all 3 channels x 2 resolutions, with required columns + coverage mask
* the channel threshold sensitivity table (CSV + Parquet) exists with required columns and 60 rows
* selected_cell_count > 0 for every row
* both centroids are inside the analysis region
* the seven required figures exist and are non-empty
* the notebook was executed
* no fake data: per-grid available-cell counts match the real CP4A coverage (432 / 2685)

Exit 0 if all pass.  Usage: python scripts/validate_cp4c_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.aggregate import GRID_COLUMNS  # noqa: E402
from saa.threshold_analysis import CHANNEL_SENSITIVITY_COLUMNS  # noqa: E402

RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
NB = ROOT / "notebooks" / "04c_channel_sensitivity.ipynb"

REGION = PROC / "noaa19_2024-01_mep_omni_flux_p1_p2_p3_region.parquet"
CHANNELS = ["mep_omni_flux_p1", "mep_omni_flux_p2", "mep_omni_flux_p3"]
SHORT = {c: c.split("_")[-1] for c in CHANNELS}
SENS_CSV = TBL / "cp4c_channel_threshold_sensitivity.csv"
SENS_PARQ = TBL / "cp4c_channel_threshold_sensitivity.parquet"
FIGS = (
    [f"cp4c_noaa19_2024-01_{SHORT[c]}_mean_flux_5deg.png" for c in CHANNELS]
    + ["cp4c_channel_comparison_top10_5deg_mean.png", "cp4c_channel_comparison_top10_2deg_mean.png",
       "cp4c_channel_centroid_comparison.png", "cp4c_channel_area_by_threshold.png"]
)
LAT_RANGE, LON_RANGE = (-70, 20), (-100, 20)
EXPECTED_RAW = [f"poes_n19_202401{d:02d}_proc.nc" for d in range(1, 32)]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    add = lambda n, ok, d="": checks.append((n, bool(ok), d))  # noqa: E731

    # 1) raw daily files
    present = sum((RAW / f).exists() for f in EXPECTED_RAW)
    missing = [f for f in EXPECTED_RAW if not (RAW / f).exists()]
    add("31 NOAA-19 Jan-2024 raw files present", present == 31,
        f"{present}/31" + ("" if not missing else f"; missing {missing}"))

    # 2) regional parquet + 3 channels
    if not REGION.exists():
        add("multi-channel regional parquet exists", False, str(REGION)); return _report(checks)
    add("multi-channel regional parquet exists", True, f"{REGION.name} ({REGION.stat().st_size} B)")
    region = pd.read_parquet(REGION)
    add("p1/p2/p3 present in processed data", all(c in region.columns for c in CHANNELS),
        f"cols: {[c for c in CHANNELS if c in region.columns]}")

    # 3) missing-value rate per channel (computed)
    miss_rates = {SHORT[c]: round(float(region[c].isna().mean() * 100), 4) for c in CHANNELS if c in region.columns}
    add("missing-value rate computed per channel", len(miss_rates) == 3, str(miss_rates))

    # 4) grid tables x3 channels x2 res
    for c in CHANNELS:
        for res, mask_col in [("5deg", "enough_samples_5deg"), ("2deg", "enough_samples_2deg")]:
            p = TBL / f"cp4c_noaa19_2024-01_{SHORT[c]}_grid_{res}.parquet"
            if not p.exists():
                add(f"grid table exists: {SHORT[c]} {res}", False, "MISSING"); continue
            g = pd.read_parquet(p)
            miss = [col for col in GRID_COLUMNS if col not in g.columns]
            ok = (not miss) and (mask_col in g.columns)
            add(f"grid table ok: {SHORT[c]} {res}", ok,
                "cols ok + mask" if ok else f"missing {miss or mask_col}")

    # 5) sensitivity table
    add("sensitivity CSV exists", SENS_CSV.exists(), SENS_CSV.name)
    if not SENS_PARQ.exists():
        add("sensitivity Parquet exists", False, "MISSING"); return _report(checks)
    add("sensitivity Parquet exists", True, SENS_PARQ.name)
    sens = pd.read_parquet(SENS_PARQ)
    miss = [c for c in CHANNEL_SENSITIVITY_COLUMNS if c not in sens.columns]
    add("sensitivity has required columns", not miss, "all present" if not miss else f"missing {miss}")
    add("sensitivity has 60 rows", len(sens) == 60, f"{len(sens)} rows")
    add("3 channels present in table", set(sens["channel"].unique()) == set(CHANNELS),
        str(sorted(set(sens["channel"].unique()))))
    add("selected_cell_count > 0 for all", (sens["selected_cell_count"] > 0).all(),
        f"min={int(sens['selected_cell_count'].min())}")
    inside = (sens["centroid_lat_unweighted"].between(*LAT_RANGE).all()
              and sens["centroid_lon_unweighted"].between(*LON_RANGE).all()
              and sens["centroid_lat_flux_weighted"].between(*LAT_RANGE).all()
              and sens["centroid_lon_flux_weighted"].between(*LON_RANGE).all())
    add("centroids inside analysis region", inside)

    # 6) no fake data: available counts match real CP4A coverage
    av5 = set(sens.loc[sens.grid_deg == 5, "cells_available_after_coverage_mask"].unique())
    av2 = set(sens.loc[sens.grid_deg == 2, "cells_available_after_coverage_mask"].unique())
    add("available counts match real coverage (no fake data)", av5 == {432} and av2 == {2685},
        f"5deg {av5}, 2deg {av2}")

    # 7) figures
    for fig in FIGS:
        p = FIG / fig
        add(f"figure exists: {fig}", p.exists() and p.stat().st_size > 1000,
            f"{p.stat().st_size} B" if p.exists() else "MISSING")

    # 8) notebook executed
    if NB.exists():
        nb = json.loads(NB.read_text())
        codecells = [c for c in nb["cells"] if c.get("cell_type") == "code"]
        add("notebook executed (cells have outputs)",
            bool(codecells) and all(c.get("outputs") for c in codecells),
            f"{sum(1 for c in codecells if c.get('outputs'))}/{len(codecells)} with outputs")
    else:
        add("notebook executed (cells have outputs)", False, "missing")

    return _report(checks)


def _report(checks: list[tuple[str, bool, str]]) -> int:
    print("=" * 72)
    print("CHECKPOINT 4C OUTPUT VALIDATION")
    print("=" * 72)
    all_ok = True
    for name, ok, detail in checks:
        all_ok &= ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ->  {detail}" if detail else ""))
    print("-" * 72)
    print("RESULT:", "ALL CHECKS PASSED" if all_ok else "ONE OR MORE CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
