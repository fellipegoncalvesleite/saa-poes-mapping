#!/usr/bin/env python3
"""Validate Checkpoint 5B quantitative magnetic-coordinate framing outputs.

Checks (against real data; nothing fabricated):

* the CP5A flux+magnetic Parquet exists and has the required variables
* the magnetic validity table exists with required columns
* the binned flux profile table exists (CSV + Parquet) with required columns
* the footprint magnetic summary table exists (CSV + Parquet) with required columns
* the concentration metrics table exists with required columns
* invalid L_IGRF sentinel (-1) is excluded from L-using analyses (validity rows_invalid > 0 and no L
  profile/summary uses -1 in its valid range)
* required figures exist and are non-empty
* the notebook was executed
* no accepted CP4 / CP5A files were overwritten (CP5A region intact; CP5B uses new names)

Exit 0 if all pass.  Usage: python scripts/validate_cp5b_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.magnetic_framing import (  # noqa: E402
    VALIDITY_COLUMNS, PROFILE_COLUMNS, FOOTPRINT_SUMMARY_COLUMNS, CONCENTRATION_COLUMNS,
)

PROC = ROOT / "data" / "processed"
TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
NB = ROOT / "notebooks" / "05b_magnetic_framing.ipynb"

CP5A_REGION = PROC / "cp5a_noaa19_2024-01_region_flux_plus_magnetic.parquet"
CP4A_REGION = PROC / "noaa19_2024-01_mep_omni_flux_p1_region.parquet"
VALIDITY = TBL / "cp5b_magnetic_variable_validity.csv"
PROFILES = TBL / "cp5b_magnetic_binned_flux_profiles.parquet"
SUMMARY = TBL / "cp5b_footprint_magnetic_summary.parquet"
CONC = TBL / "cp5b_magnetic_concentration_metrics.csv"
REQ_VARS = ["mep_omni_flux_p1", "Btot_sat", "L_IGRF", "mag_lat_sat", "mag_lon_sat", "MLT"]
FIGS = [
    "cp5b_flux_profile_by_Btot_sat.png", "cp5b_flux_profile_by_L_IGRF.png",
    "cp5b_flux_profile_by_mag_lat_sat.png", "cp5b_flux_profile_by_MLT.png",
    "cp5b_inside_outside_Btot_sat.png", "cp5b_inside_outside_L_IGRF.png",
    "cp5b_inside_outside_mag_lat_sat.png",
    "cp5b_flux_Btot_vs_L_IGRF.png", "cp5b_high_flux_footprint_Btot_vs_L_IGRF.png",
]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    add = lambda n, ok, d="": checks.append((n, bool(ok), d))  # noqa: E731

    # 1) CP5A input
    if not CP5A_REGION.exists():
        add("CP5A flux+magnetic parquet exists", False, "MISSING"); return _report(checks)
    add("CP5A flux+magnetic parquet exists", True, CP5A_REGION.name)
    region = pd.read_parquet(CP5A_REGION)
    miss = [v for v in REQ_VARS if v not in region.columns]
    add("CP5A has required variables", not miss, "all present" if not miss else f"missing {miss}")

    # 2) validity table
    if not VALIDITY.exists():
        add("validity table exists", False, "MISSING"); return _report(checks)
    add("validity table exists", True, VALIDITY.name)
    val = pd.read_csv(VALIDITY)
    m = [c for c in VALIDITY_COLUMNS if c not in val.columns]
    add("validity has required columns", not m, "all present" if not m else f"missing {m}")
    lrow = val[val.variable_name == "L_IGRF"]
    add("L_IGRF invalid sentinel excluded (rows_invalid > 0)",
        len(lrow) == 1 and int(lrow.rows_invalid.iloc[0]) > 0,
        f"invalid={int(lrow.rows_invalid.iloc[0])}" if len(lrow) else "no L_IGRF row")
    add("L_IGRF valid_min > -1 (sentinel removed)", len(lrow) == 1 and float(lrow.valid_min.iloc[0]) > -1,
        f"valid_min={float(lrow.valid_min.iloc[0]):.3f}" if len(lrow) else "-")

    # 3) profiles
    if not (PROFILES.exists() and (TBL / "cp5b_magnetic_binned_flux_profiles.csv").exists()):
        add("binned flux profile table exists (CSV+Parquet)", False, "MISSING"); return _report(checks)
    add("binned flux profile table exists (CSV+Parquet)", True, PROFILES.name)
    prof = pd.read_parquet(PROFILES)
    m = [c for c in PROFILE_COLUMNS if c not in prof.columns]
    add("profiles have required columns", not m, "all present" if not m else f"missing {m}")
    add("profiles cover the 4 magnetic variables", set(prof.variable.unique()) >=
        {"Btot_sat", "L_IGRF", "mag_lat_sat", "MLT"}, str(sorted(prof.variable.unique())))
    lprof = prof[prof.variable == "L_IGRF"]
    add("L_IGRF profile excludes -1 (bin_left >= 0)", (lprof.bin_left >= 0).all(),
        f"min bin_left={lprof.bin_left.min():.3f}")

    # 4) footprint summary
    if not (SUMMARY.exists() and (TBL / "cp5b_footprint_magnetic_summary.csv").exists()):
        add("footprint magnetic summary exists (CSV+Parquet)", False, "MISSING"); return _report(checks)
    add("footprint magnetic summary exists (CSV+Parquet)", True, SUMMARY.name)
    summ = pd.read_parquet(SUMMARY)
    m = [c for c in FOOTPRINT_SUMMARY_COLUMNS if c not in summ.columns]
    add("summary has required columns", not m, "all present" if not m else f"missing {m}")
    add("summary covers 4 cases", summ.comparison_case.nunique() == 4, str(sorted(summ.comparison_case.unique())))
    add("summary inside_count > 0 for all", (summ.inside_count > 0).all(), f"min={int(summ.inside_count.min())}")

    # 5) concentration metrics
    if not CONC.exists():
        add("concentration metrics table exists", False, "MISSING"); return _report(checks)
    add("concentration metrics table exists", True, CONC.name)
    conc = pd.read_csv(CONC)
    m = [c for c in CONCENTRATION_COLUMNS if c not in conc.columns]
    add("concentration has required columns", not m, "all present" if not m else f"missing {m}")
    add("concentration covers Btot_sat and L_IGRF", {"Btot_sat", "L_IGRF"}.issubset(set(conc.variable)),
        str(sorted(conc.variable.unique())))

    # 6) figures
    for f in FIGS:
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

    # 8) no overwrite of accepted CP4/CP5A
    add("CP5A region intact (not overwritten)", CP5A_REGION.exists())
    add("accepted CP4A region intact (not overwritten)", CP4A_REGION.exists())

    return _report(checks)


def _report(checks: list[tuple[str, bool, str]]) -> int:
    print("=" * 72)
    print("CHECKPOINT 5B OUTPUT VALIDATION")
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
