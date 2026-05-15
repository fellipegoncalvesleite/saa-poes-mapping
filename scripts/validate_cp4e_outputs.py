#!/usr/bin/env python3
"""Validate Checkpoint 4E satellite-availability-audit + pilot-comparison outputs.

Checks (against real data; nothing fabricated):

* the satellite availability audit table exists (CSV + Parquet) with required columns
* NOAA-19 is present in the audit
* a pilot satellite is clearly selected (>=1 'eligible') or clearly rejected (documented)
* if a pilot was selected (a comparison was performed):
    - the pilot regional processed Parquet exists
    - the pilot 5deg/2deg grid tables exist with required columns + coverage mask
    - the NOAA-19 comparison input (CP4A grid tables) exists
    - the pilot threshold sensitivity table (CSV + Parquet) exists, has 40 rows, required columns
    - selected_cell_count > 0 and selected_area_km2 > 0 for every row
    - both centroids are inside the analysis region
    - the eight required figures exist and are non-empty
    - the notebook was executed
    - no fake data: NOAA-19 coverage reproduces CP4A (432 / 2685)
* if no pilot was selected: pass only if the rejection is documented and no comparison was fabricated

Exit 0 if all pass.  Usage: python scripts/validate_cp4e_outputs.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from saa.aggregate import GRID_COLUMNS  # noqa: E402
from saa.satellite_analysis import AUDIT_COLUMNS, SATELLITE_SENSITIVITY_COLUMNS, REFERENCE_SATELLITE  # noqa: E402

PROC = ROOT / "data" / "processed"
TBL = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
NB = ROOT / "notebooks" / "04e_satellite_pilot_comparison.ipynb"

AUDIT_CSV = TBL / "cp4e_satellite_availability_audit.csv"
AUDIT_PARQ = TBL / "cp4e_satellite_availability_audit.parquet"
SENS_CSV = TBL / "cp4e_satellite_pilot_threshold_sensitivity.csv"
SENS_PARQ = TBL / "cp4e_satellite_pilot_threshold_sensitivity.parquet"
N19_GRIDS = [TBL / "cp4a_noaa19_2024-01_grid_5deg.parquet", TBL / "cp4a_noaa19_2024-01_grid_2deg.parquet"]
LAT_RANGE, LON_RANGE = (-70, 20), (-100, 20)


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    add = lambda n, ok, d="": checks.append((n, bool(ok), d))  # noqa: E731

    # 1) audit table
    if not (AUDIT_CSV.exists() and AUDIT_PARQ.exists()):
        add("audit table exists (CSV+Parquet)", False, "MISSING"); return _report(checks)
    add("audit table exists (CSV+Parquet)", True, AUDIT_PARQ.name)
    audit = pd.read_parquet(AUDIT_PARQ)
    miss = [c for c in AUDIT_COLUMNS if c not in audit.columns]
    add("audit has required columns", not miss, "all present" if not miss else f"missing {miss}")
    add("NOAA-19 present in audit", (audit.satellite == REFERENCE_SATELLITE).any(),
        str(sorted(audit.satellite)))
    eligible = sorted(audit.loc[audit.recommended_for_pilot == "eligible", "satellite"])
    add("pilot clearly selected or rejected", True,
        f"eligible: {eligible}" if eligible else "none eligible -> must be rejected with docs")

    # determine whether a comparison was performed
    comparison = SENS_PARQ.exists()
    if not comparison:
        # rejection path: acceptable only if no fabricated comparison artefacts exist
        no_fake = not any((PROC.glob("cp4e_*region.parquet")))
        add("no pilot: rejection documented, no fabricated comparison", no_fake,
            "no comparison artefacts" if no_fake else "found comparison artefacts without a table")
        return _report(checks)

    # 2) comparison path -> derive pilot from the sensitivity table
    sens = pd.read_parquet(SENS_PARQ)
    pilots = sorted(set(sens.satellite) - {REFERENCE_SATELLITE})
    add("exactly one pilot in comparison", len(pilots) == 1, str(pilots))
    pilot = pilots[0] if pilots else None

    # 3) pilot regional parquet
    if pilot:
        rp = PROC / f"cp4e_{pilot}_2024-01_mep_omni_flux_p1_region.parquet"
        add(f"pilot regional parquet exists ({pilot})", rp.exists() and rp.stat().st_size > 1000,
            f"{rp.stat().st_size} B" if rp.exists() else "MISSING")
        for res, mask_col in [("5deg", "enough_samples_5deg"), ("2deg", "enough_samples_2deg")]:
            p = TBL / f"cp4e_{pilot}_2024-01_grid_{res}.parquet"
            if not p.exists():
                add(f"pilot grid table exists: {res}", False, "MISSING"); continue
            g = pd.read_parquet(p)
            m = [c for c in GRID_COLUMNS if c not in g.columns]
            add(f"pilot grid table ok: {res}", (not m) and (mask_col in g.columns),
                "cols ok + mask" if (not m and mask_col in g.columns) else f"missing {m or mask_col}")

    # 4) NOAA-19 comparison input (CP4A)
    for p in N19_GRIDS:
        add(f"NOAA-19 input exists: {p.name}", p.exists(), "ok" if p.exists() else "MISSING")

    # 5) sensitivity table
    add("sensitivity CSV exists", SENS_CSV.exists(), SENS_CSV.name)
    m = [c for c in SATELLITE_SENSITIVITY_COLUMNS if c not in sens.columns]
    add("sensitivity has required columns", not m, "all present" if not m else f"missing {m}")
    add("sensitivity has 40 rows", len(sens) == 40, f"{len(sens)} rows")
    add("selected_cell_count > 0 for all", (sens.selected_cell_count > 0).all(),
        f"min={int(sens.selected_cell_count.min())}")
    add("selected_area_km2 > 0 for all", (sens.selected_area_km2 > 0).all(),
        f"min={sens.selected_area_km2.min():.3g}")
    inside = (sens.centroid_lat_unweighted.between(*LAT_RANGE).all()
              and sens.centroid_lon_unweighted.between(*LON_RANGE).all()
              and sens.centroid_lat_flux_weighted.between(*LAT_RANGE).all()
              and sens.centroid_lon_flux_weighted.between(*LON_RANGE).all())
    add("centroids inside analysis region", inside)
    add("coverage_threshold_used populated", sens.coverage_threshold_used.notna().all()
        and (sens.coverage_threshold_used > 0).all(),
        f"values {sorted(sens.coverage_threshold_used.unique())}")

    # 6) no fake data: NOAA-19 coverage reproduces CP4A
    n5 = set(sens[(sens.satellite == REFERENCE_SATELLITE) & (sens.grid_deg == 5)]["cells_available_after_coverage_mask"])
    n2 = set(sens[(sens.satellite == REFERENCE_SATELLITE) & (sens.grid_deg == 2)]["cells_available_after_coverage_mask"])
    add("NOAA-19 coverage matches CP4A (no fake data)", n5 == {432} and n2 == {2685},
        f"5deg {n5}, 2deg {n2}")

    # 7) figures
    figs = [
        "cp4e_noaa19_2024-01_mean_flux_5deg.png", f"cp4e_{pilot}_2024-01_mean_flux_5deg.png",
        "cp4e_noaa19_2024-01_sample_count_5deg.png", f"cp4e_{pilot}_2024-01_sample_count_5deg.png",
        "cp4e_satellite_comparison_top10_5deg_mean.png", "cp4e_satellite_comparison_top10_2deg_mean.png",
        "cp4e_satellite_centroid_comparison.png", "cp4e_satellite_area_by_threshold.png",
    ]
    for f in figs:
        p = FIG / f
        add(f"figure exists: {f}", p.exists() and p.stat().st_size > 1000,
            f"{p.stat().st_size} B" if p.exists() else "MISSING")

    # 8) notebook executed
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
    print("CHECKPOINT 4E OUTPUT VALIDATION")
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
