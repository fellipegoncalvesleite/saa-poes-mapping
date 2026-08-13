# Reproducibility Checklist — SAA POES/MetOp Method-Sensitivity Study (through CP5C)

Everything here regenerates from public data + the code in this repo. Data/figure payloads are
git-ignored; provenance (with checksums) is tracked in `data/processed/PROVENANCE.md`.

## 1. Required environment
- Python **3.12** via **uv**.
- Create + install:
  ```
  uv venv --python 3.12 .venv
  uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
  .venv/bin/python -m ipykernel install --prefix .venv --name python3
  ```
- Key libs: numpy, pandas, xarray, netCDF4, pyarrow, matplotlib, nbconvert, ipykernel.

## 2. Data sources (public, unauthenticated)
- NOAA **NCEI** POES/MetOp SEM-2 L1b processed NetCDF:
  `https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/<year>/<sat>/poes_<token>_<YYYYMMDD>_proc.nc`
- Used: **January 2024**, satellites `noaa15, noaa18, noaa19, metop01, metop03` (all 31/31 days).
- The loader downloads on demand into `data/raw/` (timeout-bounded; atomic `.part`). For many files,
  parallel `curl -P 8` into `data/raw/` then let the loader read cached files.

## 3. Notebooks in execution order
Run each with:
`.venv/bin/python -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=python3 <nb>`
1. `notebooks/01_data_access_test.ipynb` — CP1 feasibility/audit
2. `notebooks/02_minimal_loader.ipynb` — CP2 loader → tidy one-day parquet
3. `notebooks/03_first_exploratory_map.ipynb` — CP3 first maps
4. `notebooks/04a_monthly_aggregation.ipynb` — CP4A monthly coverage-aware grids
5. `notebooks/04b_threshold_sensitivity.ipynb` — CP4B threshold sensitivity
6. `notebooks/04c_channel_sensitivity.ipynb` — CP4C p1/p2/p3
7. `notebooks/04d_time_window_sensitivity.ipynb` — CP4D windows
8. `notebooks/04e_satellite_pilot_comparison.ipynb` — CP4E NOAA-18 pilot (downloads NOAA-18 month)
9. `notebooks/04f_multisatellite_consistency.ipynb` — CP4F 5 satellites (downloads n15/m01/m03 months)
10. `notebooks/05a_magnetic_coordinate_audit.ipynb` — CP5A IGRF audit + flux+magnetic parquet
11. `notebooks/05b_magnetic_framing.ipynb` — CP5B quantitative magnetic framing
12. Run `.venv/bin/python scripts/generate_cp6a_summary.py`, then
    `.venv/bin/python scripts/validate_cp6a_outputs.py` — CP6A synthesis (no notebook)
13. `notebooks/05c_multisatellite_magnetic_generality.ipynb` — CP5C five-satellite magnetic generality

## 4. Validation scripts in order (each prints PASS/FAIL, exit 0 on success)
```
.venv/bin/python -m unittest discover -s tests -v          # CP5C + viewer unit/contract tests
.venv/bin/python scripts/validate_processed_sample.py      # CP2
.venv/bin/python scripts/validate_cp3_outputs.py           # CP3
.venv/bin/python scripts/validate_cp4a_outputs.py          # CP4A
.venv/bin/python scripts/validate_cp4b_outputs.py          # CP4B
.venv/bin/python scripts/validate_cp4c_outputs.py          # CP4C
.venv/bin/python scripts/validate_cp4d_outputs.py          # CP4D
.venv/bin/python scripts/validate_cp4e_outputs.py          # CP4E
.venv/bin/python scripts/validate_cp4f_outputs.py          # CP4F
.venv/bin/python scripts/validate_cp5a_outputs.py          # CP5A
.venv/bin/python scripts/validate_cp5b_outputs.py          # CP5B
.venv/bin/python scripts/validate_cp6a_outputs.py          # CP6A (synthesis)
.venv/bin/python scripts/validate_cp5c_outputs.py          # CP5C extension
.venv/bin/python scripts/export_viewer_data.py             # deterministic static viewer payload
.venv/bin/python scripts/validate_viewer_outputs.py        # all 340 map states + CP5C evidence
```

## 5. Expected key outputs
- Processed (git-ignored): `data/processed/noaa19_2024-01_mep_omni_flux_p1_region.parquet` (205,153
  rows), `..._p1_p2_p3_region.parquet`, `cp4d_*`, `cp4e_noaa18_*`, `cp4f_{sat}_*`,
  `cp5a_noaa19_2024-01_region_flux_plus_magnetic.parquet`, `cp5c_{sat}_2024-01_region_flux_plus_magnetic.parquet`.
- Tables (`outputs/tables/`, git-ignored): `cp4a_*grid_{5,2}deg`, `cp4b_threshold_sensitivity`,
  `cp4c_channel_threshold_sensitivity`, `cp4d_time_window_threshold_sensitivity`,
  `cp4e_*`, `cp4f_multisatellite_threshold_sensitivity`, `cp4f_pairwise_centroid_distances`,
  `cp5a_*`, `cp5b_*`, `cp5c_*`, `cp6a_key_results_summary`.
- Figures (`outputs/figures/`, git-ignored): `cp3_*`, `cp4a_*`, `cp4b_*`, `cp4c_*`, `cp4d_*`,
  `cp4e_*`, `cp4f_*`, `cp5a_*`, `cp5b_*`, `cp5c_*`.
- Viewer: `outputs/viewer/index.html`, `viewer.js`, and generated `viewer_data.js`. The interactive
  payload contains exactly 20 threshold, 60 channel, 160 time-window, and 100 satellite states;
  CP5C is a fixed five-row evidence table rather than another map dimension.

## 6. Known git-ignored (regenerable) outputs
`.gitignore` excludes `data/{raw,processed,samples}` payloads, `outputs/figures/*.png`,
`outputs/tables/*.{parquet,csv}`, and `.venv`. The `PROVENANCE.md` files (with sizes + sha256) are
tracked so outputs are verifiable after regeneration.

## 7. Regenerate from scratch
1. Create the venv (§1). 2. Run steps 1–11 in §3 — they download required NOAA files on demand.
3. Generate and validate CP6A at step 12. 4. Execute CP5C at step 13; it requires and hash-snapshots
the CP6A pair. 5. Run the checkpoint validators through CP5C (§4). 6. Run `scripts/export_viewer_data.py`, then
`scripts/validate_viewer_outputs.py`. 7. Open `outputs/viewer/index.html` directly or run
`bash scripts/open_viewer.sh` (macOS `open`, Linux `xdg-open`). No local HTTP server is required.

## 8. Known limitations
Single month (Jan 2024); primary channel `mep_omni_flux_p1`; geographic/sub-satellite binning; no
cross-satellite calibration (no absolute-intensity comparison); IGRF variables are NOAA model
quantities; `mep_IFC_on == -1` retained, uninterpreted; `L_IGRF == -1` excluded; NCEI can serve slowly
(loader timeout + parallel pre-download mitigate). See `docs/CLAIM_AUDIT.md` for claim boundaries.
