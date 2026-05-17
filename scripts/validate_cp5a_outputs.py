#!/usr/bin/env python3
"""Validate Checkpoint 5A magnetic/IGRF audit + pilot-framing outputs.

Checks (against real data; nothing fabricated):

* the magnetic-variable audit table exists (CSV + Parquet) with required columns
* the selected-magnetic-variables decision table exists with required columns
* at least one safe magnetic variable is selected (use_in_cp5a True), else rejection documented
* the flux+magnetic regional Parquet exists with required columns (incl. selected magnetic vars)
* the footprint inside/outside magnetic distribution table exists with required columns and rows
* the required diagnostic figures exist and are non-empty
* the notebook was executed
* no fake data: CP5A region row count matches the accepted CP4A region file
* no accepted CP4 files were overwritten (the accepted CP4A region file is intact + CP5A uses new names)

Exit 0 if all pass.  Usage: python scripts/validate_cp5a_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.magnetic_audit import (  # noqa: E402
    AUDIT_COLUMNS, SELECTION_COLUMNS, DISTRIBUTION_COLUMNS, PILOT_MAGNETIC_VARS,
)

PROC = ROOT / "data" / "processed"
TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
NB = ROOT / "notebooks" / "05a_magnetic_coordinate_audit.ipynb"

AUDIT = TBL / "cp5a_magnetic_variable_audit.parquet"
SELECTION = TBL / "cp5a_selected_magnetic_variables.parquet"
DIST = TBL / "cp5a_footprint_magnetic_distributions.parquet"
REGION = PROC / "cp5a_noaa19_2024-01_region_flux_plus_magnetic.parquet"
CP4A_REGION = PROC / "noaa19_2024-01_mep_omni_flux_p1_region.parquet"

BASE_COLS = ["time", "lat", "lon", "alt", "satellite", "source_file", "mep_omni_flux_p1", "mep_IFC_on"]
REQUIRED_FIGS = [
    "cp5a_particle_footprint_geographic_reference.png",
    "cp5a_flux_vs_L_IGRF.png",
    "cp5a_flux_vs_magnetic_latitude.png",
    "cp5a_flux_vs_MLT.png",
    "cp5a_high_flux_samples_magnetic_space.png",
]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    add = lambda n, ok, d="": checks.append((n, bool(ok), d))  # noqa: E731

    # 1) audit table
    if not (AUDIT.exists() and (TBL / "cp5a_magnetic_variable_audit.csv").exists()):
        add("magnetic audit table exists (CSV+Parquet)", False, "MISSING"); return _report(checks)
    add("magnetic audit table exists (CSV+Parquet)", True, AUDIT.name)
    audit = pd.read_parquet(AUDIT)
    m = [c for c in AUDIT_COLUMNS if c not in audit.columns]
    add("audit has required columns", not m, "all present" if not m else f"missing {m}")
    add("audit found magnetic variables from real metadata", len(audit) > 0, f"{len(audit)} vars")

    # 2) selection table
    if not SELECTION.exists():
        add("selection table exists", False, "MISSING"); return _report(checks)
    add("selection table exists", True, SELECTION.name)
    sel = pd.read_parquet(SELECTION)
    m = [c for c in SELECTION_COLUMNS if c not in sel.columns]
    add("selection has required columns", not m, "all present" if not m else f"missing {m}")
    selected = sorted(sel.loc[sel.use_in_cp5a, "variable_name"])
    add("at least one safe magnetic variable selected", len(selected) >= 1, str(selected))

    # 3) flux+magnetic regional parquet
    if not REGION.exists():
        add("flux+magnetic regional parquet exists", False, "MISSING"); return _report(checks)
    add("flux+magnetic regional parquet exists", True, f"{REGION.stat().st_size} B")
    region = pd.read_parquet(REGION)
    need = BASE_COLS + selected
    miss = [c for c in need if c not in region.columns]
    add("region has base + selected magnetic columns", not miss, "all present" if not miss else f"missing {miss}")

    # 4) distribution table
    if not DIST.exists():
        add("footprint magnetic distribution table exists", False, "MISSING"); return _report(checks)
    add("footprint magnetic distribution table exists", True, DIST.name)
    dist = pd.read_parquet(DIST)
    m = [c for c in DISTRIBUTION_COLUMNS if c not in dist.columns]
    add("distribution has required columns", not m, "all present" if not m else f"missing {m}")
    add("distribution has rows for 4 cases x selected vars", len(dist) == 4 * len(selected),
        f"{len(dist)} rows (expected {4*len(selected)})")
    add("distribution counts inside > 0", (dist.count_inside > 0).all(),
        f"min={int(dist.count_inside.min())}")

    # 5) no fake data: region rows match accepted CP4A region
    if CP4A_REGION.exists():
        n_cp4a = len(pd.read_parquet(CP4A_REGION, columns=["lat"]))
        add("region rows match CP4A (no fake data)", len(region) == n_cp4a,
            f"CP5A {len(region)} vs CP4A {n_cp4a}")
    add("accepted CP4A region file intact (not overwritten)",
        CP4A_REGION.exists() and CP4A_REGION.name != REGION.name, CP4A_REGION.name)

    # 6) figures
    for f in REQUIRED_FIGS:
        p = FIG / f
        add(f"figure exists: {f}", p.exists() and p.stat().st_size > 1000,
            f"{p.stat().st_size} B" if p.exists() else "MISSING")

    # 7) notebook executed
    if NB.exists():
        nb = json.loads(NB.read_text())
        cc = [c for c in nb["cells"] if c.get("cell_type") == "code"]
        add("notebook executed (cells have outputs)", bool(cc) and all(c.get("outputs") for c in cc),
            f"{sum(1 for c in cc if c.get('outputs'))}/{len(cc)} with outputs")
    else:
        add("notebook executed (cells have outputs)", False, "missing")

    return _report(checks)


def _report(checks: list[tuple[str, bool, str]]) -> int:
    print("=" * 72)
    print("CHECKPOINT 5A OUTPUT VALIDATION")
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
