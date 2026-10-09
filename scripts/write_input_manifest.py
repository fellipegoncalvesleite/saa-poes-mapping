"""Hash the January 2024 raw NetCDF inputs and compare with the recorded Phase 1 manifest.

Run from repository root: python scripts/write_input_manifest.py [--raw data/raw] [--recorded PATH]
Writes paper/tables/S1_raw_manifest.csv; exits non-zero on any missing file or hash mismatch.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import sys

TOKENS = {"noaa15": "n15", "noaa18": "n18", "noaa19": "n19", "metop01": "m01", "metop03": "m03"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--recorded", type=Path,
                    default=Path("paper/inputs/raw_manifest_recorded.csv"))
    ap.add_argument("--out", type=Path, default=Path("paper/tables/S1_raw_manifest.csv"))
    a = ap.parse_args()
    recorded = {r["file"]: r for r in csv.DictReader(a.recorded.open())}
    rows, bad = [], []
    for sat, tok in TOKENS.items():
        for day in range(1, 32):
            name = f"poes_{tok}_202401{day:02d}_proc.nc"
            p = a.raw / name
            if not p.exists():
                bad.append(f"missing {name}")
                continue
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            rec = recorded.get(name, {})
            ok = rec.get("sha256") == h
            if not ok:
                bad.append(f"hash mismatch {name}")
            rows.append({"satellite": sat, "file": name, "bytes": p.stat().st_size, "sha256": h,
                         "matches_recorded": ok,
                         "url": f"https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/2024/{sat}/{name}"})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} files hashed; {len(bad)} problems")
    if bad:
        print("\n".join(bad), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
