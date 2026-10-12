"""Count-rate evidence for records excluded by QC-1 (evidence only; never an analysis input).

Run from repository root:

    PYTHONPATH=src python scripts/qc_raw_count_evidence.py --l1a PATH/poes_n15_20240119_raw.nc [--output DIR]

The NOAA/NCEI level-1a companion file of the event day carries the OMNI count rates
(``mep_omni_cps_p6..p9``: >16, >35, >70, >140 MeV) from which the processed fluxes are fitted. Its
SHA-256 must match ``paper/inputs/qc_evidence_hashes.json``. Writes ``event_raw_counts.csv``
(+-12 records around each QC-1 record in that file) and ``event_raw_counts_summary.json``.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json

import netCDF4
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ["mep_omni_cps_p6", "mep_omni_cps_p7", "mep_omni_cps_p8", "mep_omni_cps_p9", "mep_omni_biase_V",
          "mep_pro_tel0_cps_p6", "mep_pro_tel90_cps_p6", "mep_IFC_on"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--l1a", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=Path("outputs/qc_sensitivity"))
    ap.add_argument("--ledger", type=Path, default=Path("outputs/tables/qc1_omni_exclusions.csv"))
    a = ap.parse_args()
    recorded = json.loads((ROOT / "paper/inputs/qc_evidence_hashes.json").read_text())
    sha = hashlib.sha256(a.l1a.read_bytes()).hexdigest()
    if recorded.get(a.l1a.name) != sha:
        raise SystemExit(f"{a.l1a.name}: SHA-256 {sha} does not match the recorded evidence hash")
    proc_name = a.l1a.name.replace("_raw.nc", "_proc.nc")
    led = pd.read_csv(a.ledger)
    led = led[led.source_file == proc_name]
    if led.empty:
        raise SystemExit(f"no QC-1 record in {proc_name}")
    with netCDF4.Dataset(a.l1a) as r, netCDF4.Dataset(ROOT / "data/raw" / proc_name) as p:
        r.set_auto_maskandscale(False)
        p.set_auto_maskandscale(False)
        tr, tp = np.asarray(r["time"][:]).astype("int64"), np.asarray(p["time"][:]).astype("int64")
        if not np.array_equal(tr, tp):
            raise SystemExit("level-1a and processed record times are not identical")
        v = {c: np.asarray(r[c][:]) for c in COUNTS}
        p6, p7 = v["mep_omni_cps_p6"].astype(float), v["mep_omni_cps_p7"].astype(float)
        both = (p6 > 0) & (p7 > 0)
        ratio = np.where(both, p7 / np.where(both, p6, 1), np.nan)
        rows, summary = [], {"l1a_file": a.l1a.name, "l1a_sha256": sha, "records": int(len(tr)),
                             "times_identical_to_processed": True, "events": []}
        for i in led.native_index.astype(int):
            sl = slice(max(0, i - 12), min(len(tr), i + 13))
            d = pd.DataFrame({c: v[c][sl] for c in COUNTS})
            d.insert(0, "offset", np.arange(sl.start, sl.stop) - i)
            d.insert(0, "native_index", np.arange(sl.start, sl.stop))
            d.insert(0, "source_file", a.l1a.name)
            d["utc"] = pd.to_datetime(tr[sl], unit="ms", utc=True).strftime("%H:%M:%S.%f").str[:-3]
            d["proc_p1"] = np.asarray(p["mep_omni_flux_p1"][sl])
            d["proc_fit"] = np.asarray(p["mep_omni_flux_flag_fit"][sl])
            rows.append(d)
            nb = np.r_[np.arange(i - 10, i), np.arange(i + 1, i + 11)]
            zero = sorted(k for k, var in r.variables.items()
                          if var.ndim == 1 and len(var) == len(tr) and np.issubdtype(var.dtype, np.number)
                          and float(np.asarray(var[i])) == 0.0 and np.all(np.asarray(var[nb]) != 0))
            bias = v["mep_omni_biase_V"]
            unusual = np.flatnonzero(~np.isin(bias, [0.0, np.float32(685.41)]))
            others = np.delete(p7, i)
            summary["events"].append({
                "native_index": int(i),
                "p6_cps": float(p6[i]), "p7_cps": float(p7[i]), "p9_cps": float(v["mep_omni_cps_p9"][i]),
                "p8_cps": float(v["mep_omni_cps_p8"][i]),
                "p6_neighbours_min": float(p6[nb].min()), "p6_neighbours_max": float(p6[nb].max()),
                "p7_neighbours_min": float(p7[nb].min()), "p7_neighbours_max": float(p7[nb].max()),
                "p7_over_p6_event": float(ratio[i]),
                "p7_over_p6_day_median": float(np.nanmedian(ratio)),
                "p7_over_p6_day_max_other": float(np.nanmax(np.delete(ratio, i))),
                "p7_day_second_highest_cps": float(others.max()),
                "directional_p6_cps_event": [float(v["mep_pro_tel0_cps_p6"][i]), float(v["mep_pro_tel90_cps_p6"][i])],
                "directional_p6_cps_neighbours_min": float(np.minimum(v["mep_pro_tel0_cps_p6"][nb], v["mep_pro_tel90_cps_p6"][nb]).min()),
                "variables_zero_at_event_nonzero_in_all_20_neighbours": zero,
                **{f"directional_{kind}_count_channels_{what}": (
                    len(names) if what == "total" else sum(float(np.asarray(r[k][i])) == 0.0 for k in names))
                   for kind, names in (("proton", [k for k in r.variables if k.startswith("mep_pro_tel") and "_cps_" in k]),
                                       ("electron", [k for k in r.variables if k.startswith("mep_ele_tel") and "_cps_" in k]))
                   for what in ("total", "zero_at_event")},
                "bias_V_values_in_day": sorted(map(float, np.unique(bias))),
                "bias_V_unusual_record_span": [int(unusual.min()), int(unusual.max())] if len(unusual) else None,
            })
    a.output.mkdir(parents=True, exist_ok=True)
    pd.concat(rows, ignore_index=True).to_csv(a.output / "event_raw_counts.csv", index=False)
    (a.output / "event_raw_counts_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
