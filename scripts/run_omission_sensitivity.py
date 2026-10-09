"""NOAA-15 exact-record omission, replayed on the unfiltered data (provenance of the Phase 2 evidence).

Run from repository root after scripts/run_qc_sensitivity.py:
PYTHONPATH=src python scripts/run_omission_sensitivity.py [--output DIR]
Default output: outputs/omission_sensitivity/. Reuses the Phase 1 audit functions
(`event_dossier`, `influence`) unchanged. Regions are extracted from data/raw with the integrity-v2
validity rule but *without* QC-1 (``qc=False``): "as_is" is the unfiltered data and
"omit_exact_record" removes the one record by source SHA-256 and native index. Since QC-1 became
primary, the as-is grids are reconciled against the unfiltered grids written by
run_qc_sensitivity.py (the canonical cp4f grids now carry QC-1), and the outputs must remain
byte-identical to the recorded Phase 2 evidence.
"""
from pathlib import Path
import argparse
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import run_integrity_audit as audit  # noqa: E402
from saa.grid_flux import prepare_region  # noqa: E402
from saa.load_poes import SAT_FILE_TOKEN, extract_channels_dataframe, file_sha256, open_poes_netcdf  # noqa: E402


def regions_from_raw(raw: Path) -> dict:
    regions = {}
    for sat in audit.SAT:
        frames = []
        paths = sorted(raw.glob(f"poes_{SAT_FILE_TOKEN[sat]}_202401*_proc.nc"))
        if len(paths) != 31:
            raise RuntimeError(f"{sat}: {len(paths)}/31 January files present")
        for p in paths:
            with open_poes_netcdf(str(p)) as ds:
                d = extract_channels_dataframe(ds, str(p), channels=[audit.P1], qc=False)
            d["source_sha256"] = file_sha256(str(p))
            d["native_index"] = np.arange(len(d))
            frames.append(d)
        region, _ = prepare_region(pd.concat(frames, ignore_index=True))
        regions[sat] = region
        print(sat, "region rows", len(region), flush=True)
    return regions


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path("outputs/omission_sensitivity"))
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--unfiltered-grids", type=Path, default=Path("outputs/qc_sensitivity/unfiltered_grids"))
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    audit.R = a.output
    audit.T = a.unfiltered_grids
    audit.event_dossier()
    audit.influence(regions_from_raw(a.raw))
    grid = pd.read_csv(a.output / "grid_reconciliation.csv")
    if not grid.exact_grid_match.all():
        raise SystemExit("as-is reconstructed grids differ from the unfiltered cp4f-equivalent grids")


if __name__ == "__main__":
    main()
