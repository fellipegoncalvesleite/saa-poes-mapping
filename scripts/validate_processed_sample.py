#!/usr/bin/env python3
"""Validate a processed one-day POES table (Checkpoint 2).

Checks the saved parquet/CSV produced by ``notebooks/02_minimal_loader.ipynb``:

* file exists
* required columns exist
* row count > 0
* latitude within [-90, 90]
* longitude convention is valid and reported ([-180, 180] or [0, 360])
* the time column parses as datetimes
* the selected proton channel column exists
* at least some non-null particle values exist

Exit code 0 if every check passes, 1 otherwise.

Usage::

    python scripts/validate_processed_sample.py [path-to-processed-file] [--channel NAME]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STEM = ROOT / "data" / "processed" / "noaa19_2024-01-01_mep_omni_flux_p1"
REQUIRED_BASE_COLUMNS = ["time", "lat", "lon", "satellite", "source_file"]


def _resolve_path(arg: str | None) -> Path | None:
    """Pick the file to validate: explicit arg, else .parquet, else .csv."""
    if arg:
        p = Path(arg)
        return p if p.exists() else None
    for ext in (".parquet", ".csv"):
        cand = DEFAULT_STEM.with_suffix(ext)
        if cand.exists():
            return cand
    return None


def _load(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, parse_dates=["time"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", default=None, help="processed parquet/CSV (auto-detected if omitted)")
    ap.add_argument("--channel", default="mep_omni_flux_p1", help="selected proton channel column")
    args = ap.parse_args()

    path = _resolve_path(args.path)
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    # 1) file exists
    if path is None:
        check("processed file exists", False,
              f"none of {DEFAULT_STEM}.parquet/.csv (or given path) found")
        _report(checks)
        return 1
    check("processed file exists", True, str(path))

    df = _load(path)

    # 2) required columns (+ selected channel)
    required = REQUIRED_BASE_COLUMNS + [args.channel]
    missing = [c for c in required if c not in df.columns]
    check("required columns present", not missing,
          "all present" if not missing else f"missing: {missing}")

    # 3) row count > 0
    n = len(df)
    check("row count > 0", n > 0, f"{n} rows")

    if n > 0 and "lat" in df.columns:
        lat_min, lat_max = float(df["lat"].min()), float(df["lat"].max())
        check("latitude within [-90, 90]", lat_min >= -90 and lat_max <= 90,
              f"min={lat_min:.3f} max={lat_max:.3f}")

    if n > 0 and "lon" in df.columns:
        lon_min, lon_max = float(df["lon"].min()), float(df["lon"].max())
        if lon_min >= -180 and lon_max <= 180:
            conv = "[-180, 180]"
            ok = True
        elif lon_min >= 0 and lon_max <= 360:
            conv = "[0, 360]"
            ok = True
        else:
            conv = "INVALID"
            ok = False
        check("longitude convention valid", ok, f"detected {conv} (min={lon_min:.3f} max={lon_max:.3f})")

    # 6) time parses
    time_ok = pd.api.types.is_datetime64_any_dtype(df["time"]) if "time" in df.columns else False
    if not time_ok and "time" in df.columns:
        try:
            pd.to_datetime(df["time"])
            time_ok = True
        except Exception:
            time_ok = False
    detail = ""
    if time_ok and n > 0:
        detail = f"{df['time'].min()} .. {df['time'].max()}"
    check("time column parses", time_ok, detail)

    # 7) selected channel exists
    has_channel = args.channel in df.columns
    check(f"channel '{args.channel}' exists", has_channel)

    # 8) some non-null particle values
    if has_channel:
        nn = int(df[args.channel].notna().sum())
        pos = int((df[args.channel] > 0).sum())
        check("non-null particle values exist", nn > 0,
              f"{nn}/{n} non-null ({nn/n*100:.1f}%), {pos} strictly > 0")

    return _report(checks)


def _report(checks: list[tuple[str, bool, str]]) -> int:
    print("=" * 64)
    print("PROCESSED-SAMPLE VALIDATION")
    print("=" * 64)
    all_ok = True
    for name, ok, detail in checks:
        all_ok &= ok
        tag = "PASS" if ok else "FAIL"
        line = f"[{tag}] {name}"
        if detail:
            line += f"  ->  {detail}"
        print(line)
    print("-" * 64)
    print("RESULT:", "ALL CHECKS PASSED" if all_ok else "ONE OR MORE CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
