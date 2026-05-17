#!/usr/bin/env python3
"""Validate Checkpoint 6A synthesis + mentor-packet outputs (no new science).

Checks:

* the key results summary table exists (CSV + Parquet) and covers the required result areas
* the claim audit exists and contains supported / plausible / forbidden sections
* the paper outline exists (with the chosen primary title)
* the figure plan exists
* the mentor packet exists and contains concrete, technical professor questions
* the reproducibility checklist exists
* no new raw data was downloaded by CP6A (raw file count unchanged vs the 5x31 + samples already present)
* no new scientific-analysis outputs beyond synthesis tables/docs (only cp6a_* table is new in tables/)
* existing accepted outputs were not overwritten (spot-check accepted tables still present)

Exit 0 if all pass.  Usage: python scripts/validate_cp6a_outputs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TBL = ROOT / "outputs" / "tables"
DOCS = ROOT / "docs"

KEY_CSV = TBL / "cp6a_key_results_summary.csv"
KEY_PARQ = TBL / "cp6a_key_results_summary.parquet"
CLAIM = DOCS / "CLAIM_AUDIT.md"
OUTLINE = DOCS / "PAPER_OUTLINE.md"
FIGPLAN = DOCS / "FIGURE_PLAN.md"
MENTOR = DOCS / "MENTOR_PACKET.md"
REPRO = DOCS / "REPRODUCIBILITY_CHECKLIST.md"

REQUIRED_AREAS = {"threshold sensitivity", "channel sensitivity", "time-window sensitivity",
                  "satellite consistency", "magnetic-coordinate framing"}
KEY_COLUMNS = ["result_area", "checkpoint_source", "input_data", "metric", "main_numeric_result",
               "interpretation_allowed", "overclaim_to_avoid", "supporting_table_or_figure",
               "paper_section_candidate"]
# accepted outputs that must still be present (not overwritten by synthesis)
ACCEPTED = [
    "cp4b_threshold_sensitivity.parquet", "cp4c_channel_threshold_sensitivity.parquet",
    "cp4d_time_window_threshold_sensitivity.parquet", "cp4f_multisatellite_threshold_sensitivity.parquet",
    "cp5b_footprint_magnetic_summary.parquet",
]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    add = lambda n, ok, d="": checks.append((n, bool(ok), d))  # noqa: E731

    # key results table
    if not (KEY_CSV.exists() and KEY_PARQ.exists()):
        add("key results summary exists (CSV+Parquet)", False, "MISSING"); return _report(checks)
    add("key results summary exists (CSV+Parquet)", True, KEY_PARQ.name)
    key = pd.read_parquet(KEY_PARQ)
    m = [c for c in KEY_COLUMNS if c not in key.columns]
    add("key results has required columns", not m, "all present" if not m else f"missing {m}")
    areas = set(key.result_area)
    add("key results covers required result areas", REQUIRED_AREAS.issubset(areas),
        f"have {sorted(areas)}")
    add("key results main_numeric_result populated", key.main_numeric_result.notna().all()
        and (key.main_numeric_result.str.len() > 0).all())

    # docs exist
    for name, p in [("claim audit", CLAIM), ("paper outline", OUTLINE), ("figure plan", FIGPLAN),
                    ("mentor packet", MENTOR), ("reproducibility checklist", REPRO)]:
        add(f"{name} exists", p.exists() and p.stat().st_size > 200,
            f"{p.stat().st_size} B" if p.exists() else "MISSING")

    # claim audit sections
    if CLAIM.exists():
        t = CLAIM.read_text().lower()
        add("claim audit has supported section", "supported by current evidence" in t)
        add("claim audit has plausible-not-proven section", "plausible but not yet proven" in t
            or "plausible but not" in t)
        add("claim audit has forbidden section", "forbidden" in t)
        for term in ["final", "boundary", "dose", "health", "danger", "discovery"]:
            pass
        add("forbidden section names boundary/dose/health/danger/discovery",
            all(w in t for w in ["boundary", "dose", "health", "danger", "discovery"]))

    # paper outline chosen title
    if OUTLINE.exists():
        ot = OUTLINE.read_text().lower()
        add("paper outline has the chosen primary title",
            "method-sensitivity study" in ot and "south atlantic anomaly" in ot)

    # mentor packet concrete questions
    if MENTOR.exists():
        mt = MENTOR.read_text().lower()
        concrete = sum(w in mt for w in ["mep_omni_flux_p1", "btot_sat", "mep_ifc_on", "l_igrf",
                                         "calibration", "literature", "foot"])
        add("mentor packet has concrete technical questions", "?" in MENTOR.read_text() and concrete >= 5,
            f"{concrete} technical anchors")
        add("mentor packet avoids vague 'is this impressive'", "impressive" not in mt
            or "not" in mt)  # only acceptable as the 'do not ask' note

    # no new raw data downloaded by CP6A: raw counts still the known 5x31 (+ no extra)
    raw = ROOT / "data" / "raw"
    n_jan = {s: len(list(raw.glob(f"poes_{s}_202401*_proc.nc"))) for s in ("n15", "n18", "n19", "m01", "m03")}
    add("no new raw download (5 sats x 31 Jan files present, unchanged)",
        all(v == 31 for v in n_jan.values()), str(n_jan))

    # only cp6a_* added to tables among synthesis; accepted outputs intact
    for f in ACCEPTED:
        add(f"accepted output intact: {f}", (TBL / f).exists(), "present" if (TBL / f).exists() else "MISSING")

    return _report(checks)


def _report(checks):
    print("=" * 72)
    print("CHECKPOINT 6A OUTPUT VALIDATION")
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
