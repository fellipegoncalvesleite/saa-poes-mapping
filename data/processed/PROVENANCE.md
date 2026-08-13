# Processed-data provenance (Checkpoint 2)

Tidy one-day table produced by `notebooks/02_minimal_loader.ipynb` via `src/saa/load_poes.py` on
2026-06-07. The payload files are git-ignored (regenerable); this file documents them.

## Source NetCDF (input)
- **Product:** NOAA/NCEI POES/MetOp SEM-2 **Level-1b processed** (NGDC `_proc.nc`)
- **Satellite:** NOAA-19 · **Date:** 2024-01-01
- **URL:** https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/2024/noaa19/poes_n19_20240101_proc.nc
- **Local copy:** `data/raw/poes_n19_20240101_proc.nc`
- **Size:** 5,800,360 bytes · **sha256:** `45b84acd431025ef0abb3c87a81735c9364f155e97fb3a264848dd9d85be8e3c`
- **Downloaded:** 2026-06-07 · NetCDF-4 / HDF5 · no authentication

## Processed table (output)
- **File:** `data/processed/noaa19_2024-01-01_mep_omni_flux_p1.parquet`
- **Format:** Parquet (pyarrow) · **Size:** 1,074,994 bytes · **sha256:** `26faa8e4f55369e6ba91eb95b9ca4ef20ca4cffe88cdd910120cc18b034a2978`
- **Rows:** 43,197 · **Columns:** `time, lat, lon, alt, satellite, source_file, mep_omni_flux_p1, mep_IFC_on, mep_omni_flux_flag_fit`
- **Diagnostic figure:** `data/processed/diagnostic_noaa19_2024-01-01.png` (sanity only; not a scientific map)

## Selected channel
- **Variable:** `mep_omni_flux_p1`
- **Quantity:** **FLUX** (not counts, not uncertain) — MEPED omnidirectional proton **differential
  flux at ~25 MeV**, per the file's `long_name`: *"MEPED proton differential flux at 25 MeV
  omnidirection telescope"*.
- **Units:** `#/cm2-s-str-MeV` · **Observed range:** 0.0 … 36.5687 · **Missing:** 0.0000 %

## Quality / calibration flags found
- **`mep_IFC_on`** (in-flight calibration): observed `{-1: 40497, 0: 2700}` this day — **no `1`
  (IFC-on) values**, so masking `== 1` removes 0 rows here. `long_name` = "MEPED IFC flag (0 off 1
  on)"; the dominant **`-1` is undocumented** (no `_FillValue` attr; treated as fill / not-applicable).
  **Downstream rule:** drop records where `mep_IFC_on == 1`; do not interpret `-1`.
- **`mep_omni_flux_flag_fit`** (omni fit quality): observed `{1: 36055, 2: 3656, 0: 3486}`; review
  before any quantitative use.

## Reproduce
```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m ipykernel install --prefix .venv --name python3
.venv/bin/python -m nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=python3 notebooks/02_minimal_loader.ipynb
.venv/bin/python scripts/validate_processed_sample.py
```

---

## Checkpoint 3 additions (figures only — no new processed table)
No new processed table was created in CP3 (the CP2 parquet above is the input). CP3 generated **map
figures** in `outputs/figures/` (git-ignored, regenerable from the parquet via
`notebooks/03_first_exploratory_map.ipynb`):
`cp3_noaa19_2024-01-01_mean_flux_5deg.png`, `..._median_flux_5deg.png`, `..._mean_flux_2deg.png`,
`..._sample_count_5deg.png`, and the optional `..._to_07_mean_flux_5deg.png`.

The optional 7-day preview downloaded six more official daily files into `data/raw/`
(`poes_n19_20240102..07_proc.nc`, ~5 MB each, same NCEI L1b URL pattern; git-ignored).

---

## Checkpoint 4A — Monthly aggregation (January 2024)

**Daily source files used:** all **31** NOAA-19 L1b files `poes_n19_20240101_proc.nc` …
`poes_n19_20240131_proc.nc` from
`https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/2024/noaa19/`
(downloaded into `data/raw/`, git-ignored, ~5 MB each). **Missing dates: none — month complete.**

**Monthly regional processed subset (new):**
- `data/processed/noaa19_2024-01_mep_omni_flux_p1_region.parquet`
- region lat[-70,20]×lon[-100,20], lon converted to [-180,180), `mep_IFC_on==1` dropped (0 rows),
  `==-1` kept (192,334 rows, uninterpreted).
- **205,153 rows · 3,639,640 bytes · Parquet zstd · sha256** `c36caa46792a3b5c…`

**Gridded tables (new, `outputs/tables/`, git-ignored):**
- `cp4a_noaa19_2024-01_grid_5deg.parquet` — 432 cells, 19,550 B, sha256 `0c3ce3e1e4a669ae…`,
  cols `lat_bin_center, lon_bin_center, mean_flux, median_flux, sample_count, positive_sample_count,
  min_flux, max_flux, enough_samples_5deg` (mask `>=30`: 432/432 pass).
- `cp4a_noaa19_2024-01_grid_2deg.parquet` — 2,700 cells, 77,119 B, sha256 `807489ee8efa6334…`,
  same columns + `enough_samples_2deg` (mask `>=30`: 2,685/2,700 pass).

**Figures (new, `outputs/figures/`, git-ignored):**
`cp4a_noaa19_2024-01_{mean,median,sample_count}_flux_{5deg,2deg}.png` (6).

Produced by `notebooks/04a_monthly_aggregation.ipynb`; validated by `scripts/validate_cp4a_outputs.py`.

---

## Checkpoint 4B — Threshold sensitivity (derived from CP4A grid tables; no new raw/processed data)

**Source grid tables used (CP4A, unchanged):** `outputs/tables/cp4a_noaa19_2024-01_grid_5deg.parquet`,
`…_grid_2deg.parquet` (coverage-passed cells only: 432/432 and 2,685/2,700).

**Threshold sensitivity table (new, `outputs/tables/`, git-ignored):**
- `cp4b_threshold_sensitivity.csv` — 20 rows, 6,999 B, sha256 `c94b4537658c0efc…`
- `cp4b_threshold_sensitivity.parquet` — 20 rows, 14,672 B, sha256 `fea789011010f893…`
- columns: grid_deg, statistic_used, threshold_label, percentile_cutoff, flux_cutoff_value,
  cells_available_after_coverage_mask, selected_cell_count, selected_area_km2,
  selected_area_fraction_of_covered_region, centroid_lat/lon_unweighted,
  centroid_lat/lon_flux_weighted, peak_flux, mean/median_flux_within_selected,
  total_flux_area_proxy, notes.

**Figures (new, `outputs/figures/`, git-ignored):**
`cp4b_threshold_overlay_{5deg,2deg}_{mean,median}.png` (4) + `cp4b_centroid_shift_by_threshold.png` (1).

Produced by `notebooks/04b_threshold_sensitivity.ipynb`; validated by `scripts/validate_cp4b_outputs.py`.
No raw or processed data files were created in CP4B (analysis of existing CP4A tables only).

---

## Checkpoint 4C — Proton channel sensitivity (p1/p2/p3)

**Source raw files:** the same 31 NOAA-19 Jan-2024 L1b files in `data/raw/` (no re-download).
**Channels** read from NetCDF metadata: `mep_omni_flux_p1/p2/p3` = differential proton flux at
**25/50/100 MeV**, units `#/cm2-s-str-MeV`.

**Multi-channel processed subset (new):**
- `data/processed/noaa19_2024-01_mep_omni_flux_p1_p2_p3_region.parquet` — 205,153 rows, 4,504,948 B,
  zstd, sha256 `13c28321f956b5f8…` (region + IFC filtered; p1,p2,p3 columns; missing 0% each).

**Grid tables (new, `outputs/tables/`):** `cp4c_noaa19_2024-01_{p1,p2,p3}_grid_{5deg,2deg}.parquet`
(6; same columns as CP4A + coverage mask; masks identical across channels: 432/432 and 2,685/2,700).

**Threshold sensitivity (new):** `cp4c_channel_threshold_sensitivity.csv` (60 rows, 20,414 B,
sha256 `1347a47a790f23e7…`) + `.parquet` (19,107 B, sha256 `1deff1c4968010c5…`).

**Figures (new, `outputs/figures/`):** `cp4c_noaa19_2024-01_{p1,p2,p3}_mean_flux_5deg.png` (3),
`cp4c_channel_comparison_top10_{5deg,2deg}_mean.png` (2), `cp4c_channel_centroid_comparison.png`,
`cp4c_channel_area_by_threshold.png`.

Produced by `notebooks/04c_channel_sensitivity.ipynb`; validated by `scripts/validate_cp4c_outputs.py`.

---

## Checkpoint 4D — Time-window sensitivity (NOAA-19, Jan 2024, mep_omni_flux_p1)

**Source raw files:** the same 31 NOAA-19 Jan-2024 L1b files in `data/raw/` (no re-download); all 31
loaded, no missing days. The month is read once and each window is an in-memory date slice.

**Processed regional subsets (new, cumulative windows):**
- `cp4d_noaa19_2024-01-01_mep_omni_flux_p1_region.parquet` — 7,244 rows, 255,416 B
- `cp4d_noaa19_2024-01-01_to_07_mep_omni_flux_p1_region.parquet` — 43,524 rows, 1,395,523 B
- `cp4d_noaa19_2024-01-01_to_14_mep_omni_flux_p1_region.parquet` — 88,277 rows, 2,583,567 B
- `cp4d_noaa19_2024-01_full_month_mep_omni_flux_p1_region.parquet` — 205,153 rows, 4,949,364 B,
  sha256 `5ada9229275b0d75…` (identical content to the CP4A monthly region subset).
Weekly windows are sliced in-memory (no separate parquet) and documented in `research_notes.md`.

**Grid tables (new, `outputs/tables/`, 16):** `cp4d_{window}_grid_{5deg,2deg}.parquet` for windows
`day_2024-01-01, days_2024-01-01_to_07, days_2024-01-01_to_14, month_2024-01, week1..week4`. Same
columns as CP4A + per-window coverage mask `enough_samples_{5,2}deg`. Coverage threshold per window:
`max(3, round((30/31)*day_count))` → day 3, 7-day/weekly 7, 14-day 14, month 30 (month reproduces
CP4A 432/2685).

**Threshold sensitivity (new):** `cp4d_time_window_threshold_sensitivity.csv` (160 rows, 46,085 B,
sha256 `9209a7a40302398d…`) + `.parquet` (29,052 B, sha256 `f07e65a4e58c9bcf…`). Columns add
`window_label, start_date, end_date, day_count, files_expected, files_loaded, coverage_threshold_used,
coverage_warning` to the CP4B set.

**Figures (new, `outputs/figures/`, 11):** `cp4d_mean_flux_5deg_{day_2024-01-01,days_2024-01-01_to_07,
days_2024-01-01_to_14,month_2024-01}.png`, `cp4d_sample_count_{5deg,2deg}_time_windows.png`,
`cp4d_centroid_by_time_window_{top10,top5}.png`, `cp4d_area_by_time_window.png`,
`cp4d_weekly_centroid_comparison.png`, `cp4d_weekly_mean_flux_5deg_comparison.png`.

Produced by `notebooks/04d_time_window_sensitivity.ipynb`; validated by `scripts/validate_cp4d_outputs.py`.

---

## Checkpoint 4E — Satellite availability audit + NOAA-18 pilot comparison

**Audit (real NCEI archive listing + sample-file open):** five satellites with complete 31/31 Jan-2024
L1b coverage — noaa15, noaa18, noaa19, metop01, metop03 — all loader-compatible with identical
`mep_omni_flux_p1` units/long_name. Table `outputs/tables/cp4e_satellite_availability_audit.csv`
(1,738 B, sha256 `134737b913d07c57…`) + `.parquet` (9,705 B, sha256 `9ce1fd8a208dc8b1…`).

**Pilot raw files used (new):** 31 NOAA-18 L1b files `poes_n18_20240101…20240131_proc.nc` from
`https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/2024/noaa18/`
(downloaded into `data/raw/`, git-ignored, ~5–7 MB each). **Missing dates: none.** Plus one sample
file per other candidate (`poes_{n15,m01,m03}_20240101_proc.nc`) for the audit.

**Pilot processed regional subset (new):**
- `cp4e_noaa18_2024-01_mep_omni_flux_p1_region.parquet` — 208,722 rows, 5,046,977 B,
  sha256 `180e8611d7f0cf5b…` (region + lon[-180,180) + `mep_IFC_on==1` dropped; `==-1` kept).

**Pilot grid tables (new, `outputs/tables/`):** `cp4e_noaa18_2024-01_grid_5deg.parquet`
(19,817 B, sha256 `ba2a3d9a42d436ce…`, 432/432 pass ≥30) and `…_grid_2deg.parquet`
(78,771 B, sha256 `fcb3cf7bd41daf38…`, 2571/2699 pass ≥30). Same columns as CP4A + coverage mask.
NOAA-19 grids reused unchanged from CP4A (no regeneration).

**Threshold sensitivity (new):** `cp4e_satellite_pilot_threshold_sensitivity.csv` (40 rows, 16,949 B,
sha256 `4cccd5061f17832e…`) + `.parquet` (18,010 B, sha256 `f2aad0ef46233e81…`). Columns add
`satellite`, `coverage_threshold_used` (30), `satellite_compatibility_note`.

**Figures (new, `outputs/figures/`, 8):** `cp4e_{noaa19,noaa18}_2024-01_mean_flux_5deg.png`,
`cp4e_{noaa19,noaa18}_2024-01_sample_count_5deg.png`,
`cp4e_satellite_comparison_top10_{5deg,2deg}_mean.png`, `cp4e_satellite_centroid_comparison.png`,
`cp4e_satellite_area_by_threshold.png`.

Produced by `notebooks/04e_satellite_pilot_comparison.ipynb`; validated by `scripts/validate_cp4e_outputs.py`.

---

## Checkpoint 4F — Multi-satellite footprint consistency (noaa15/18/19, metop01/03)

**Raw source files used:** 31 NOAA-19 + 31 NOAA-18 (from CP4A/CP4E) + **new** 31 NOAA-15, 31 MetOp-01,
31 MetOp-03 daily L1b files from
`https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/2024/<sat>/`
(downloaded into `data/raw/`, git-ignored, ~5–7 MB each). **Missing dates: none** for any satellite.

**Compatibility table (new):** `outputs/tables/cp4f_satellite_compatibility.{csv,parquet}`
(parquet 10,803 B, sha256 `9e0feb85f73bef0d…`) — all five satellites `cp4f_included=True`, none excluded.

**Processed regional subsets (new, 5):**
- `cp4f_noaa15_2024-01_…region.parquet` — 207,232 rows, 5,006,914 B, sha256 `0f546391e267…`
- `cp4f_noaa18_2024-01_…region.parquet` — 208,722 rows, 5,046,977 B, sha256 `180e8611d7f0…`
- `cp4f_noaa19_2024-01_…region.parquet` — 205,153 rows, 4,947,631 B, sha256 `c6bf2292f2e9…`
- `cp4f_metop01_2024-01_…region.parquet` — 227,572 rows, 5,286,736 B, sha256 `14c358c27c8e…`
- `cp4f_metop03_2024-01_…region.parquet` — 226,645 rows, 5,297,169 B, sha256 `ab573214ccc0…`

**Grid tables (new, `outputs/tables/`, 10):** `cp4f_{sat}_2024-01_grid_{5deg,2deg}.parquet` for all
five satellites (CP4A columns + `enough_samples_{5,2}deg` coverage mask at ≥30).

**Threshold sensitivity (new):** `cp4f_multisatellite_threshold_sensitivity.csv` (100 rows, 41,214 B,
sha256 `4f164ef752d68d7a…`) + `.parquet` (24,330 B, sha256 `c2d56ae1fa126f61…`); every row has
`absolute_flux_comparison_allowed=False`.

**Pairwise centroid distances (new):** `cp4f_pairwise_centroid_distances.csv` (40 rows, 5,144 B,
sha256 `0871435f5b772204…`) + `.parquet` (6,401 B, sha256 `4a9d90df07e00b5f…`).

**Figures (new, `outputs/figures/`, 16):** `cp4f_{sat}_mean_flux_5deg.png` (5),
`cp4f_{sat}_sample_count_5deg.png` (5), `cp4f_multisatellite_{top10,top5}_{5deg,2deg}_mean_overlay.png`
(4), `cp4f_multisatellite_centroid_comparison_top10_top5.png`,
`cp4f_pairwise_centroid_distance_top10_5deg_mean.png`.

Produced by `notebooks/04f_multisatellite_consistency.ipynb`; validated by `scripts/validate_cp4f_outputs.py`.

---

## Checkpoint 5A — IGRF / magnetic-coordinate audit + pilot framing (NOAA-19, Jan 2024)

**Raw files inspected:** the 31 NOAA-19 Jan-2024 L1b files in `data/raw/` (audit metadata read from
`poes_n19_20240101_proc.nc`; full month re-read to extract magnetic variables). No re-download; no
external IGRF package added (NOAA files already carry IGRF products).

**Magnetic variables used (from real NetCDF):** selected `L_IGRF`, `Btot_sat`, `mag_lat_sat`,
`mag_lon_sat`, `MLT` (of 29 magnetic/coord variables audited). `L_IGRF == -1` is a documented invalid
sentinel, excluded in analysis.

**Audit + selection tables (new, `outputs/tables/`):**
- `cp5a_magnetic_variable_audit.csv` (5,548 B, sha256 `653a2c52b3b103ff…`) + `.parquet`
  (10,064 B, sha256 `db75d91fc19e33fd…`) — 29 variables, 14 audit columns.
- `cp5a_selected_magnetic_variables.{csv,parquet}` (csv 2,377 B, sha256 `c9d9dd76091c6788…`).

**Processed flux+magnetic regional file (new):**
- `cp5a_noaa19_2024-01_region_flux_plus_magnetic.parquet` — 205,153 rows, 7,486,038 B,
  sha256 `05729c85989960f2…` (matches CP4A region row count; **accepted CP4 files untouched**).

**Footprint magnetic distribution table (new):** `cp5a_footprint_magnetic_distributions.csv`
(20 rows, 3,929 B, sha256 `07fdf3cd54813b2c…`) + `.parquet` (10,513 B, sha256 `a39a9b70e3547575…`).

**Figures (new, `outputs/figures/`, 7):** `cp5a_particle_footprint_geographic_reference.png`,
`cp5a_flux_vs_{L_IGRF,magnetic_latitude,MLT,Btot_sat}.png`,
`cp5a_high_flux_samples_magnetic_space.png`, `cp5a_geographic_Btot_sat_map.png`.

Produced by `notebooks/05a_magnetic_coordinate_audit.ipynb`; validated by `scripts/validate_cp5a_outputs.py`.

---

## Checkpoint 5B — Quantitative magnetic-coordinate framing (NOAA-19, Jan 2024)

**Input (reused, not modified):** `data/processed/cp5a_noaa19_2024-01_region_flux_plus_magnetic.parquet`
+ accepted CP4A grid tables `cp4a_noaa19_2024-01_grid_{5,2}deg.parquet`. No raw re-read, no new processed
data file, no external IGRF added. Accepted CP4/CP5A files untouched.

**Output tables (new, `outputs/tables/`):**
- `cp5b_magnetic_variable_validity.csv` (721 B, sha256 `00e40ac45965e561…`) — 5 variables; L_IGRF -1
  sentinel: 3,914 rows excluded.
- `cp5b_magnetic_binned_flux_profiles.csv` (8,022 B, sha256 `ce94980954d1318a…`) + `.parquet`
  (11,318 B, sha256 `887c7aede07c70d9…`) — 50 rows (Btot 14 bins + L/mag_lat/MLT 12 each).
- `cp5b_footprint_magnetic_summary.csv` (5,336 B, sha256 `a28a9c3d847c9afb…`) + `.parquet`
  (11,883 B, sha256 `d2803f8e2a45c013…`) — 16 rows (4 cases × 4 vars); separation metric defined.
- `cp5b_magnetic_concentration_metrics.csv` (2,338 B, sha256 `279e5be07e4ec9fb…`) — 16 rows
  (Btot_sat & L_IGRF, top10/top5).

**Figures (new, `outputs/figures/`, 10):** `cp5b_flux_profile_by_{Btot_sat,L_IGRF,mag_lat_sat,MLT}.png`,
`cp5b_inside_outside_{Btot_sat,L_IGRF,mag_lat_sat}.png`, `cp5b_flux_Btot_vs_L_IGRF.png`,
`cp5b_high_flux_footprint_Btot_vs_L_IGRF.png`, `cp5b_mag_lat_vs_mag_lon_wrapaware.png`.

Produced by `notebooks/05b_magnetic_framing.ipynb`; validated by `scripts/validate_cp5b_outputs.py`.

---

## Checkpoint 5C — Multi-satellite magnetic generality (five satellites, Jan 2024)

**Inputs:** 31 real NOAA/NCEI L1b `_proc.nc` files for each of `noaa15`, `noaa18`, `noaa19`,
`metop01`, and `metop03` (155 source files total), plus the accepted CP4F footprint tables and CP5B
NOAA-19 reference tables. Fixed scope: `mep_omni_flux_p1`, regional lat[-70,20]×lon[-100,20],
top10/top5 × 5°/2° mean cases. No cross-satellite absolute-flux comparison.

**Regional flux+magnetic Parquets (regenerable):**
- `cp5c_noaa15_2024-01_region_flux_plus_magnetic.parquet` — 207,232 rows, 7,569,199 B, sha256 `aa6435e78ca4b485…`.
- `cp5c_noaa18_2024-01_region_flux_plus_magnetic.parquet` — 208,722 rows, 7,617,613 B, sha256 `585f08f1ea6da56a…`.
- `cp5c_noaa19_2024-01_region_flux_plus_magnetic.parquet` — 205,153 rows, 7,486,038 B, sha256 `760bc9a47a0935d1…`.
- `cp5c_metop01_2024-01_region_flux_plus_magnetic.parquet` — 227,572 rows, 8,055,136 B, sha256 `37546c3bc0ba47ec…`.
- `cp5c_metop03_2024-01_region_flux_plus_magnetic.parquet` — 226,645 rows, 8,070,350 B, sha256 `70edd3372eb92ec6…`.

**Output tables (`outputs/tables/`, each CSV + Parquet):**
- `cp5c_magnetic_variable_validity_by_satellite` — 25 rows; CSV 3,555 B, sha256 `df96f854cb656b6d…`.
- `cp5c_footprint_magnetic_summary_by_satellite` — 80 rows; CSV 27,311 B, sha256 `a62e9e8ae879593c…`.
- `cp5c_magnetic_concentration_by_satellite` — 80 rows; CSV 12,771 B, sha256 `97d8efdd7932ca84…`.
- `cp5c_multisatellite_magnetic_generality_summary` — 5 rows; CSV 2,330 B, sha256 `d52d6e2f91cc81fb…`.
- `cp5c_omni_fit_flag_diagnostic` — 26 rows; CSV 1,856 B, sha256 `73017888c7a3e1dc…`.

**Figures (`outputs/figures/`):**
- `cp5c_multisatellite_magnetic_separation_top10_5deg_mean.png` — 35,004 B, sha256 `7968935fd42c78cc…`.
- `cp5c_multisatellite_low_btot_capture90_top10_5deg_mean.png` — 36,434 B, sha256 `378cb36dbf9fc502…`.

**Frozen decision result:** `CONSISTENT` (5/5 low-Btot, 5/5 Btot dominance, zero reversed Btot signs).
The cutoffs are predeclared operational CP5C criteria, not physical SAA thresholds. NOAA-19 hard
gate passed exact deterministic comparisons and floats at `rtol=1e-9`, `atol=1e-12`,
`equal_nan=True`. Accepted CP4A/CP4F/CP5A/CP5B/CP6A artifacts were hash-checked before and after
execution and were unchanged.

Produced by `notebooks/05c_multisatellite_magnetic_generality.ipynb`; validated by
`scripts/validate_cp5c_outputs.py` (all checks passed).
