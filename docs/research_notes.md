# Research Notes — Checkpoint 1: Data Access & Feasibility Audit

**Project:** Methodological mapping & sensitivity analysis of the South Atlantic Anomaly (SAA)
from public NOAA/EUMETSAT POES/MetOp SEM‑2 MEPED particle data.
**Audit date:** 2026‑06‑07
**Scope of this checkpoint:** Determine whether official NOAA data can support the MVP
(load real satellite data with *time, latitude, longitude, satellite ID, and at least one
proton channel*). **No maps and no scientific conclusions are produced in this checkpoint.**

> Framing reminder (carried from the project brief): we are **not** discovering the SAA,
> **not** computing biological dose, **not** replacing radiation‑transport models, and
> **not** doing generic Monte‑Carlo. The contribution is *methodological*: reproducible
> mapping + sensitivity analysis on public data.

---

## 1. Verdict

**FEASIBLE — confirmed against real files, not just documentation.**
Official NOAA NCEI archives provide browsable, unauthenticated, directly downloadable
POES/MetOp SEM‑2 files that contain every MVP‑required field. Two independent products were
downloaded and verified in this environment:

- a **NetCDF‑4** processed file (`poes_n19_20240101_proc.nc`, 5.5 MB) — confirmed valid HDF5,
  variable names confirmed by scanning the file's metadata;
- an **ASCII** Level‑2 file (`poes_n19_20140102.txt`, 2.2 MB) — confirmed self‑describing
  (header row) and fully readable with the Python standard library alone.

Latitude, longitude, time, satellite ID, and multiple proton channels are **all present** in both.

---

## 2. Official sources found

| Source | Role | URL |
|---|---|---|
| **NOAA NCEI** (National Centers for Environmental Information; *formerly NGDC*) | Authoritative archive + product landing page | https://www.ncei.noaa.gov/products/poes-space-environment-monitor |
| NCEI data archive root (SEM) | Browsable file tree (`access/l0b|l1a|l1b|l2/v01r00/…`) | https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/ |
| **External Users Manual — POES/MetOp SEM‑2 Processing** (Janet Green, NGDC, v1.0, Mar 2013) | Authoritative variable list (Table A‑1) & directory layout | https://www.ngdc.noaa.gov/stp/satellite/poes/docs/NGDC/External_Users_Manual_POES_MetOp_SEM-2_processing_V1.pdf |
| SEM‑2 instrument doc (2006) | Instrument description | https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/doc/sem2_docs/2006/SEM2v2.0.pdf |
| MEPED telescope ATBD / MEPED omni ATBD / TED ATBD | Algorithm + energy bands + contamination detail | linked from the product page (`/doc/` tree) |

**Migration note (verified):** the legacy host `satdat.ngdc.noaa.gov` (cited inside the 2013
manual) now **refuses connections**, and `www.ngdc.noaa.gov/stp/satellite/poes/dataaccess.html`
issues a **301 redirect** to the NCEI product page above. Use the **`www.ncei.noaa.gov/data/…`**
paths; do not rely on the legacy NGDC host.

---

## 3. Data products & directory map

Archive root: `https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/`

| NCEI level | Format | Coverage | Path pattern | Content (what's inside) |
|---|---|---|---|---|
| `l0b/v01r00` | binary `.bin` | 1978–2014 | … | Raw Level‑0b telemetry |
| `l1a/v01r00` | NetCDF `.nc` | 2012–present | `…/l1a/v01r00/<year>/<sat>/` | Calibrated **counts/s** (`*_cps_*`) + geolocation, no fitted flux |
| **`l1b/v01r00`** ⭐ | **NetCDF‑4 `.nc`** | **2012–present** | `…/l1b/v01r00/<year>/<sat>/poes_<sat>_<YYYYMMDD>_proc.nc` | **Processed: calibrated differential/integral FLUX + errors + full magnetic ephemeris + flags.** This is the science‑ready product (the manual's `…_proc.nc`). |
| **`l2/v01r00/txt`** | **ASCII `.txt`** | 1998–2014 | `…/l2/v01r00/txt/<year>/<sat>/poes_<sat>_<YYYYMMDD>.txt` | Legacy SWPC 16‑s‑averaged archive, **count rates**, self‑describing header. Zero‑dependency. |
| `l2/v01r00/cdf` | NASA CDF `.cdf` | 1998–2014 | `…/l2/v01r00/cdf/<year>/<sat>/` | Same legacy product in NASA CDF |
| (indices) | `.txt` | 2013–present | … | Radiation‑belt indices |

`<sat>` ∈ {`noaa15, noaa16, noaa17, noaa18, noaa19, metop01 (MetOp‑B), metop02 (MetOp‑A),
metop03 (MetOp‑C)`}. In 2024 the L1b tree contains `metop01, metop03, noaa15, noaa18, noaa19`
(NOAA‑16/17 and MetOp‑A retired). `<sat>` token in filenames uses `n15…n19` / `m01…m03`.

> **Product discontinuity to remember:** modern NetCDF (`l1a/l1b`) starts in **2012**; the ASCII/CDF
> legacy product (`l2`) ends in **2014**. Any pre‑2012 window *must* use `l2`; any post‑2014 window
> *must* use `l1b`. The two products use different processing/units → a multi‑year span crosses a
> **processing boundary** (relevant to the project's "time window" sensitivity axis).

---

## 4. Access method

- **Protocol:** plain **HTTPS GET** over an Apache auto‑index (human‑browsable directories).
- **Authentication:** **none** (public‑domain U.S. Government data). Verified: anonymous `curl` returned `200 OK`.
- **Headers (verified):** `content-type: application/x-netcdf` (`.nc`) / `text/plain` (`.txt`);
  `accept-ranges: bytes` (supports HTTP range requests → cheap header peeks and resumable/bulk pulls).
- **Bulk download:** feasible via `wget -r -np -A '*.nc'` or a small Python loop over dated filenames.
  For the MVP, **manual/scripted per‑file download is easier and sufficient** (filenames are fully
  predictable: `poes_n19_YYYYMMDD_proc.nc`).
- **File sizes (observed):** L1b NOAA‑19 2024 ≈ **4–6 MB/day**; L2 txt ≈ **2.2 MB/day**.

### Python readers
| Format | Library | Install | Notes |
|---|---|---|---|
| `.nc` (NetCDF‑4/HDF5) | `xarray` (`xr.open_dataset`) or `netCDF4` | `pip install xarray netCDF4` | Confirmed valid HDF5 (magic bytes `\x89HDF`). |
| `.txt` (ASCII) | stdlib `csv` / `str.split`, or `pandas.read_csv(delim_whitespace=True)` | none (stdlib) / `pip install pandas` | Has a header row; **verified readable with stdlib only**. |
| `.cdf` (NASA CDF) | `cdflib` or `spacepy.pycdf` | `pip install cdflib` | Only needed if using the CDF flavor of L2. |

---

## 5. Variables available (confirmed)

### 5.1 Geolocation, time, identity — present in **every** file
| Variable (NetCDF) | ASCII column | Meaning | Units / range |
|---|---|---|---|
| `time`, `year`, `day`, `msec` | `year mo dy hr mi second`, `dayofyear` | timestamp | UTC; `msec` 0–86 400 000 |
| `lat` / `latitude` | `sslat` | sub‑satellite geographic latitude | −90…90° (observed −81…81°, = 98.7° inclination) |
| `lon` / `longitude` | `sslon` | sub‑satellite geographic longitude | 0…360° |
| `alt` | (—) | satellite altitude | km (~800–850) |
| `satID` | (filename) | satellite identifier | integer ID |
| `sat_direction` | (—) | ascending/descending flag | 0/1 |

### 5.2 MEPED proton channels — the SAA tracers (present)
- **Telescope, 0° look (≈ zenith):** `mep_pro_tel0_flux_p1 … p6` (+ `_err`) — ASCII `mep0p1…mep0p6`
- **Telescope, 90° look (≈ horizon):** `mep_pro_tel90_flux_p1 … p6` (+ `_err`) — ASCII `mep90p1…mep90p6`
- **Omnidirectional (dome) integral:** `mep_omni_flux_p1, p2, p3` (+ `mep_omni_gamma_p1..p3`) — ASCII raw dome `mepomp6, mepomp7, mepomp8, mepomp9`
- **Units:** NetCDF telescope flux = `#/cm²·s·sr·keV` (differential); NetCDF omni flux = `#/cm²·s·sr` (integral);
  ASCII columns = **count rates (counts/s)** from the legacy SWPC archive (uncorrected; loosely called "fluxes").

**Approximate energy bands** *(per published SEM‑2 documentation — Evans & Greer 2004 / ATBDs;
treat as nominal and verify exact thresholds in the MEPED telescope & omni ATBDs before any
quantitative use):*

| Channel | Nominal energy | Channel | Nominal energy |
|---|---|---|---|
| P1 | 30–80 keV | P5 | 2500–6900 keV |
| P2 | 80–240 keV | P6 | > 6900 keV (⚠ electron‑contaminated) |
| P3 | 240–800 keV | omni P1 | > ~16 MeV |
| P4 | 800–2500 keV | omni P2 / P3 | > ~36 / > ~70 MeV |

### 5.3 Electron channels (present)
`mep_ele_tel0_flux_e1…e4`, `mep_ele_tel90_flux_e1…e4` (+ `_err`); ASCII `mep0e1..e3`, `mep90e1..e3`.
Nominal integral E1 > ~30 keV, E2 > ~100 keV, E3 > ~300 keV (E4 in newer processing — verify in ATBD).

### 5.4 Detector orientation / pitch angle (present)
`meped_alpha_0_foot`, `meped_alpha_90_foot` (and `…_sat`), `ted_alpha_0/30_*`; ASCII `pas0`, `pas90`.
→ The 0°/90° telescopes sample **different pitch angles**, so they are *not* interchangeable.

### 5.5 Magnetic / orbital ephemeris (present in NetCDF; bonus for SAA work)
`L_IGRF` (McIlwain L), `MLT`, `mag_lat_sat`/`mag_lon_sat`, foot‑of‑field‑line
(`geod_lat_foot`/`geod_lon_foot`, `mag_lat_foot`, `aacgm_lat_foot/lon_foot`), field components
`Br_foot/Bt_foot/Bp_foot/Btot_foot`. ASCII: `folat`, `folon`, `lval`, `mlt`.

### 5.6 Quality information (present)
- **Per‑value error bars:** every physical variable has a paired `*_err` (Poisson + calibration).
  The manual states users should rely on these **rather than quality flags**.
- **Omni fit flags:** `mep_omni_flux_flag_fit`, `mep_omni_flux_flag_iter_lim`.
- **In‑flight calibration flag:** `mep_IFC_on` / `ted_IFC_on` — **must be filtered**: when the
  calibration source is on, the detector is *not* viewing space.

---

## 6. Real‑file verification evidence (reproducible)

**NetCDF integrity & format** (`poes_n19_20240101_proc.nc`):
```
content-length: 5800360 ; content-type: application/x-netcdf ; accept-ranges: bytes
downloaded 5800360 bytes (== content-length)
first 8 bytes: \x89HDF\r\n\x1a\n  -> NetCDF-4 (HDF5)  -> readable by xarray/netCDF4
sha256: 45b84acd431025ef0abb3c87a81735c9364f155e97fb3a264848dd9d85be8e3c
```
**Variable names found by scanning the file's (uncompressed) HDF5 metadata** — confirmed present:
`time, year, day, msec, lat, latitude, lon, longitude, alt, satID, sat_direction,`
`mep_pro_tel0_flux_p1..p6 (+_err), mep_pro_tel90_flux_p1..p6 (+_err),`
`mep_omni_flux_p1..p3, mep_omni_flux_flag_fit, mep_omni_flux_flag_iter_lim,`
`mep_ele_tel0/90_flux_e1..e4, L_IGRF, MLT, mag_lat_sat, *_foot, meped_alpha_0/90_foot, mep_IFC_on.`
(`mep_pro_tel0_cps_p1` absent → processed file carries *flux*, not counts.)

**ASCII stdlib read** (`poes_n19_20140102.txt`, no third‑party libraries):
```
columns (41): year mo dy hr mi second dayofyear sslat sslon folat folon lval mlt pas0 pas90
              mep0e1..e3 mep0p1..p6 mep90e1..e3 mep90p1..p6 mepomp6..p9 ted echar pchar econtr
data rows: 5400            (16-s cadence x 1 day)
sslat range: -81.12 .. 81.12 deg   sslon range: 0.11 .. 359.98 deg
mep0p6 (counts/s): 0.0 .. 303.5     mepomp6 (counts/s): 0.0 .. 2239.8
sha256: e31a1b78560b16dc5eac9b2fceb64039713616d39c3c1565577c15c12278875d
```

---

## 7. Recommended MVP dataset

**Primary target (science‑ready):**
- **Satellite:** **NOAA‑19** (`n19`) — operational, recent, stable, present in the L1b tree.
- **Product:** **L1b processed NetCDF**, `poes_n19_YYYYMMDD_proc.nc`.
- **Time window:** start with **a single day (2024‑01‑01)** to validate loading, then **one
  calendar month (Jan 2024 ≈ 30 files, ~150 MB)** for the first map — enough orbits (~14/day)
  for usable longitude coverage without a multi‑decade pull.
- **Proton channel:** **`mep_omni_flux_p1`** (integral omnidirectional high‑energy protons,
  > ~16 MeV) — best single channel for a first SAA footprint (omnidirectional ⇒ no
  look‑direction ambiguity; high‑energy trapped protons). Cross‑check: `mep_pro_tel0_flux_p6`.

**Lowest‑friction alternative (zero install — recommended if NetCDF tooling is a blocker):**
- **L2 ASCII** `poes_n19_20140102.txt`: map `sslon` × `sslat` colored by **`mepomp6`** (or `mep0p6`).
  Readable with the standard library alone (already verified here). Trade‑off: count rates
  (uncorrected), no error bars, coverage ends 2014.

**Why this is easiest / least risky:** one satellite, one predictable filename pattern, no auth,
small files; the omnidirectional proton channel removes pitch‑angle complications; and a single
product/window avoids the 2014↔2012 processing boundary. The ASCII fallback removes the only real
technical dependency (the NetCDF stack).

---

## 8. Scientific caveats (must be remembered before interpreting anything)

1. **Detector degradation.** MEPED proton telescopes degrade over a satellite's lifetime; absolute
   sensitivity drifts. Long‑duration single‑satellite trends need degradation correction. *(Stated by NOAA, §3.2.2.)*
2. **Cross‑species contamination.** The P6 telescope channel (and others) is contaminated by
   relativistic **electrons**; high‑energy electrons leak into "proton" channels and vice‑versa.
   Prefer omni channels / documented clean channels for proton mapping. *(NOAA §3.2.2.)*
3. **Counts vs. flux.** ASCII/L2 = uncorrected **count rates**; NetCDF/L1b = **calibrated flux** with
   `*_err`. Do not compare the two as if they were the same quantity.
4. **Satellite‑to‑satellite intercalibration.** Different satellites are **not** absolutely
   cross‑calibrated. Multi‑satellite comparison needs intercalibration before quantitative claims. *(NOAA §3.2.2.)*
5. **Long‑term quantitative comparison needs correction** (degradation + intercalibration + the
   2014/2012 product boundary). A **single‑satellite, single‑product, exploratory first map is fine**;
   multi‑decade/multi‑satellite intensity comparisons are **not** valid without correction.
6. **In‑flight calibration intervals** (`mep_IFC_on`) must be filtered out.
7. **Look direction / pitch angle.** `tel0` and `tel90` sample different pitch angles; the omni dome
   is direction‑integrated. Mixing them changes the map.
8. **Coordinate choice matters.** Sub‑satellite geographic (`lat/lon`) vs field‑line foot
   (`folat/folon`) vs magnetic (`L`, `MLT`) give different SAA "shapes" — itself one of the project's
   methodological axes.
9. **First map = exploratory visualization only.** Acceptable and intended for the MVP; **not** a
   calibrated dosimetric or absolute‑intensity product.

---

## 9. Stored samples

See `../data/samples/PROVENANCE.md`. Two real, checksummed files are kept locally for offline
notebook runs (and git‑ignored by default — re‑downloadable from the documented URLs):
`poes_n19_20240101_proc.nc` (NetCDF‑4, 5.5 MB) and `poes_n19_20140102.txt` (ASCII, 2.2 MB).

## 10. Authoring‑environment limitations (for honesty/reproducibility)

This audit ran on Python **3.14.4** with **no `pip`**, **no** numpy/pandas/xarray/netCDF4, and **no
Jupyter**. Consequences: the NetCDF path could not be opened with xarray *here* (variable names were
instead confirmed by scanning the file's HDF5 metadata); the ASCII path **was** executed with the
standard library; and `notebooks/01_data_access_test.ipynb` is **authored but not executed in this
environment** (it carries no fabricated outputs). To run it, create a venv elsewhere and
`pip install xarray netCDF4` (Path B) — Path A needs only the standard library.

## 11. Recommended next checkpoint (Checkpoint 2)

**"First exploratory SAA map + minimal reproducible loader."**
1. Set up a clean Python env (`xarray, netCDF4, numpy, pandas, matplotlib`; add `cartopy` later).
2. Implement a loader returning a tidy table `[time, lat, lon, alt, sat, channel_value]` for one
   NOAA‑19 L1b day, then a month.
3. Bin onto a lon×lat grid (e.g., 5°×5° and 2°×2°) and plot mean/median `mep_omni_flux_p1` as a
   first SAA footprint (exploratory only; filter `mep_IFC_on`).
4. Stub the **sensitivity axes** as parameters: proton channel, flux threshold, grid resolution,
   satellite, time window — the eventual study varies exactly these.
5. Keep the ASCII path as a no‑dependency sanity check.

---

# Checkpoint 2 — Minimal Loader Results

**Date:** 2026-06-07 · **Status:** ✅ complete & validated (loader runs on real data; all checks pass).

## Environment (this resolved the CP1 blocker)
CP1 noted the box had Python 3.14 with no `pip`/sci-libs/Jupyter. **`uv` (0.11.9) turned out to be
installed**, so a clean **Python 3.12.13** venv was created and the real scientific stack installed
and import-verified: `numpy 2.4.6, pandas 3.0.3, xarray 2026.4.0, netCDF4 1.7.4, pyarrow 24.0.0,
matplotlib 3.10.9` (+ `nbconvert 7.17.1, ipykernel 7.2.0` to execute the notebook). See
`requirements.txt` / `requirements-dev.txt`. Reproduce:
```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
```

## Does the NetCDF loader work?
**Yes.** `src/saa/load_poes.py` builds the official URL, downloads the file (only if missing), opens
it with xarray/netCDF4, and extracts a tidy table. `notebooks/02_minimal_loader.ipynb` was
**executed end-to-end** (7/7 code cells produced real outputs + an embedded diagnostic figure), and
`scripts/validate_processed_sample.py` reports **ALL CHECKS PASSED**.

## Real-file structure (confirmed by opening the file with xarray)
- **Records:** 43,197 (2-second cadence, one UTC day). The file's own global `title` warns:
  *"POES/MetOp: Particle Precipitation (These data have known contamination problems...)"*.
- **Layout quirk:** there is **no shared record dimension** — every variable is a 1-D array along a
  dimension of *its own name*, positionally aligned by index. The loader reads each variable's
  `.values` and assembles the DataFrame manually; `xarray.Dataset.to_dataframe()` must NOT be used.

## Exact variable names used and mapping
| tidy column | NetCDF variable | dtype in file | transform | units |
|---|---|---|---|---|
| `time` | `time` | uint64 | `pd.to_datetime(v, unit="ms", utc=True)` (epoch **ms since 1970**) | UTC |
| `lat` | `lat` | float32 | -> float64 | degrees |
| `lon` | `lon` | float32 | -> float64 (kept **[0,360) East**) | degrees |
| `alt` | `alt` | float32 | -> float64 | km |
| `satellite` | (filename token `n19`) | - | constant `"noaa19"` | - |
| `source_file` | (filename) | - | basename | - |
| `mep_omni_flux_p1` | `mep_omni_flux_p1` | float32 | -> float64 | `#/cm2-s-str-MeV` |
| `mep_IFC_on` | `mep_IFC_on` | int8 | carried through (int16) | flag |
| `mep_omni_flux_flag_fit` | `mep_omni_flux_flag_fit` | int8 | carried through (int16) | flag |

The internal `satID` variable is a constant **8** for NOAA-19 (an internal code, not "19"), so the
`satellite` column is labelled from the filename/URL instead; `satID=8` is recorded here for traceability.

## Extracted table — sanity numbers (real)
- **Rows:** 43,197 · **Columns:** the 9 above.
- **Selected-channel missing values:** **0.0000 %** (43,197/43,197 non-null; 40,815 strictly > 0; 2,382 exactly 0).
- **Latitude:** -80.974 ... 80.974° · **Longitude:** 0.007 ... 359.997° (**[0, 360)** convention).
- **Altitude:** 842.30 ... 886.60 km.
- **`mep_omni_flux_p1` range:** 0.0 ... 36.5687 `#/cm2-s-str-MeV`.
- **Timestamp range:** 2024-01-01 00:00:00.977Z ... 2024-01-01 23:59:56.975Z.
- **Saved:** `data/processed/noaa19_2024-01-01_mep_omni_flux_p1.parquet` (1,074,994 B, sha256 `26faa8e4...2978`).

## `mep_IFC_on` — exists, and how to handle it later
Present (int8). **Observed values this day: `{-1: 40497, 0: 2700}`** — there are **no `1` values**, so
masking `mep_IFC_on == 1` (IFC active) drops 0 rows here, but the column is preserved for days that
*do* contain IFC intervals. `long_name` says `0=off / 1=on`; the dominant **`-1` is undocumented**
(no `_FillValue` attribute; treat as fill / not-applicable). **Downstream rule:** exclude records
where `mep_IFC_on == 1`; do **not** interpret `-1`. The omni fit-quality flag
`mep_omni_flux_flag_fit` is distributed `{1: 36055, 2: 3656, 0: 3486}` and should be reviewed too.

## Caveats discovered from the real data
1. **CP1 energy-band correction.** The L1b omni channels are **differential fluxes at nominal
   25 / 50 / 100 MeV** (`mep_omni_flux_p1/p2/p3`, units `#/cm2-s-str-MeV`) — **not** integral
   ">16/36/70 MeV" as guessed in CP1 §5/§7. `mep_omni_flux_p1`'s `long_name` is literally *"MEPED
   proton differential flux at 25 MeV omnidirection telescope"*. The selected values are therefore
   **flux** (not counts), differential at ~25 MeV. *(CP1 §7's energy figures are superseded by this.)*
2. **Contamination is flagged by the data itself** (global `title`), consistent with CP1 caveat #2 —
   keep any single-channel result exploratory.
3. **`satID` is an internal code (8), not the satellite number** — always label from the file/URL.
4. **Longitude is [0, 360)** — CP3 mapping will likely convert to [-180, 180] to centre on the
   Atlantic (the SAA sits near lon ≈ -40° ≡ 320°). Documented; the validator accepts [0,360].
5. **No shared record dimension** — re-implementations must avoid `to_dataframe()`.

## Validation
`python scripts/validate_processed_sample.py` -> **ALL CHECKS PASSED**: file exists; required
columns present; 43,197 rows > 0; latitude in [-90, 90]; longitude convention [0, 360] reported;
time parses; channel present; 100 % non-null particle values.

## Next checkpoint (Checkpoint 3)
First **exploratory** lon×lat SAA footprint of `mep_omni_flux_p1`: extend the loader to several
days / one month, mask `mep_IFC_on == 1`, bin on 5°×5° and 2°×2° grids, plot mean/median. Keep it
exploratory — no scientific, dose, or discovery claims. Start stubbing the five sensitivity axes
(channel, threshold, grid resolution, satellite, time window).

---

# Checkpoint 3 — First Exploratory Map Results

**Date:** 2026-06-07 · **Status:** ✅ complete & validated (real one-day maps generated; all checks pass).
**Scope:** *exploratory one-day proton-flux maps for pipeline validation* — **not** the final SAA
shape, **not** dose, **not** health risk, **not** a discovery, and **not** stable from a single day.

## Inputs
- **Input file:** `data/processed/noaa19_2024-01-01_mep_omni_flux_p1.parquet` (43,197 rows; from CP2,
  derived from the real NCEI `poes_n19_20240101_proc.nc`).
- **Channel:** `mep_omni_flux_p1` — MEPED omnidirectional proton **differential flux at ~25 MeV**.
- **Flux units (as currently understood):** `#/cm2-s-str-MeV` (a particle flux; explicitly **not** a
  dose or health-risk quantity).

## Longitude conversion
`[0, 360) -> [-180, 180)` via `((lon + 180) % 360) - 180`, applied **before** filtering
(`src/saa/grid_flux.py:to_180`). In-region `lon180` spans -99.99 … 19.99°.

## Geographic filter & calibration filter
- **Region:** lat **-70 … +20**, lon **-100 … +20** (inclusive) — South America + South Atlantic.
- **Calibration:** dropped `mep_IFC_on == 1` (none this day); kept `== -1` (6,791 rows; undocumented,
  **not interpreted**) and `== 0`.

## Row counts
| stage | rows |
|---|---|
| total (one day) | 43,197 |
| after geographic filter | 7,244 |
| after `mep_IFC_on` filter | 7,244 |

In-region channel: min 0.0, max 36.5687, mean 3.356 (7,056 > 0; 188 zeros).

## Grid resolutions tested
- **5° × 5°:** 432 cells, **206 non-empty**.
- **2° × 2°:** 2,700 cells, **548 non-empty** (sparser per cell — visible in the sample-count map).

## Figures (`outputs/figures/`)
- `cp3_noaa19_2024-01-01_mean_flux_5deg.png` — 5° mean (log10 color scale)
- `cp3_noaa19_2024-01-01_median_flux_5deg.png` — 5° median (log10)
- `cp3_noaa19_2024-01-01_mean_flux_2deg.png` — 2° mean (log10)
- `cp3_noaa19_2024-01-01_sample_count_5deg.png` — samples per cell (linear)
- `cp3_noaa19_2024-01-01_to_07_mean_flux_5deg.png` — optional 7-day preview (exploratory)

## Does a high-flux region appear in the expected sector?
**Yes (exploratory).** A **candidate high-flux region** appears in the **South Atlantic / South
America sector**: the top 5° cells by mean and median cluster near **lat -12.5° to -27.5°,
lon -52.5° to -57.5°** (top cell lat -22.5°, lon -52.5°: mean ≈ 33.1, median ≈ 34.5, n=41). This is
consistent with the sector where the SAA is expected, but is offered only as a *first visualization
for pipeline validation* — not a measurement of the anomaly's shape.

| lat | lon | mean | median | n |
|---|---|---|---|---|
| -22.5 | -52.5 | 33.14 | 34.48 | 41 |
| -22.5 | -57.5 | 30.54 | 30.86 | 45 |
| -17.5 | -52.5 | 30.19 | 30.42 | 43 |
| -27.5 | -57.5 | 27.63 | 27.92 | 86 |
| -12.5 | -52.5 | 23.58 | 23.34 | 43 |

## Optional multi-day preview (2024-01-01 … 07)
`load_date_range` downloaded 7 daily files: **258,692 total rows -> 43,524 in-region**; 5° non-empty
cells rose to **429/432** (vs 206 one day) — better coverage, as expected. Full multi-day mapping and
the sensitivity study are deferred to **Checkpoint 4**.

## Validation
`python scripts/validate_cp3_outputs.py` -> **ALL CHECKS PASSED**: parquet present; real source file
(no fake data); 4 figures exist; region rows > 0; longitude converted & within box; 5°/2° grids
non-empty; sample-count populated; top cells computable.

## Caveats
1. **One day only** — sparse coverage (especially 2°); the footprint is **not stable** and must not
   be read as the SAA's shape.
2. **Differential ~25 MeV flux**, single channel, exploratory — not integral, not dose.
3. **`mep_IFC_on == -1`** kept and not interpreted; revisit once its meaning is confirmed.
4. **Sub-satellite geographic binning only**; magnetic coords (`L_IGRF`, `MLT`), other channels and
   satellites are sensitivity axes for later checkpoints.
5. **No absolute calibration / intercalibration / degradation correction** applied.

## Next checkpoint (Checkpoint 4)
Aggregate a longer window (week -> month), implement the five **sensitivity axes** (proton channel,
flux threshold, grid resolution, satellite, time window), and begin quantifying the estimated
**center, area, and intensity** and their variation.

---

# Checkpoint 4A — Monthly Aggregation and Coverage-Aware Grids

**Date:** 2026-06-07 · **Status:** ✅ complete & validated (19/19 checks pass).
**Scope:** *monthly exploratory proton-flux aggregation* + a *coverage-aware gridded product* — a
**foundation for later threshold sensitivity analysis**. **Not** a final SAA shape/center, **not**
dose, **not** health risk, **not** a discovery, **not** a satellite-danger estimate.

## Inputs
- **Date range:** 2024-01-01 … 2024-01-31 · **Satellite:** NOAA-19 · **Channel:** `mep_omni_flux_p1`
  (differential proton flux ~25 MeV, `#/cm2-s-str-MeV`).
- **Files loaded:** **31 / 31** (one official NCEI L1b `poes_n19_YYYYMMDD_proc.nc` per day).
  **Missing dates: none — the month is complete.** (`load_range` tolerates per-day failures and
  records them; none occurred.)
- **Region:** lat **-70…+20**, lon **-100…+20**. **Longitude:** `[0,360) → [-180,180)` before filtering.

## Row counts
| stage | rows |
|---|---|
| total (all 31 days) | 1,206,770 |
| after geographic filter | 205,153 |
| after `mep_IFC_on` filter | 205,153 |

- **Calibration filter:** dropped `mep_IFC_on == 1` (**0 rows** this month); kept `== -1`
  (**192,334 rows**, uninterpreted) and `== 0`.
- In-region flux: min 0.0, max **147.56**, mean 3.37 (200,274 > 0; 4,879 zeros).
- **Saved regional subset:** `data/processed/noaa19_2024-01_mep_omni_flux_p1_region.parquet`
  (205,153 rows, **3,639,640 B**, zstd, sha256 `c36caa46…`).

## Grid resolutions & products
Tidy grid tables (one row per populated cell; columns `lat_bin_center, lon_bin_center, mean_flux,
median_flux, sample_count, positive_sample_count, min_flux, max_flux` + coverage mask):
- `outputs/tables/cp4a_noaa19_2024-01_grid_5deg.parquet` (432 cells, 19,550 B, sha256 `0c3ce3e1…`)
- `outputs/tables/cp4a_noaa19_2024-01_grid_2deg.parquet` (2,700 cells, 77,119 B, sha256 `807489ee…`)

## Sample-count distribution (reported before choosing thresholds)
- **5° (432 populated cells, full region):** min **276**, q10 400, median **477**, q90 542, max 599.
- **2° (2,700 populated cells, full region):** min **16**, q10 51, median **76**, q90 99, max 127.

## Chosen coverage thresholds & justification
- **5°: `enough_samples_5deg = sample_count >= 30` → 432/432 (100%) pass.** Even the least-sampled 5°
  cell has 276 samples, far above any reasonable floor, so monthly 5° coverage is **complete and
  robust**; the mask flags nothing this month but guards future under-sampled cases.
- **2°: `enough_samples_2deg = sample_count >= 30` → 2,685/2,700 (99.4%) pass** (15 sparse
  region-edge cells flagged). 30 is a per-cell statistical-stability floor (enough for a stable
  per-cell median) and sits **below the 10th percentile (51)**, so it discards only the sparsest
  tail, not typical cells. Monthly 2° coverage is **dense, not sparse** (min 16, median 76).
- The masks exist as columns in the saved grid tables so later center/area/intensity estimates can
  exclude low-sample cells.

## Figures (`outputs/figures/`)
`cp4a_noaa19_2024-01_{mean,median,sample_count}_flux_{5deg,2deg}.png` (6 total). Flux maps use a
**log10 color scale**; on mean/median maps **blank cells = no data OR below the coverage threshold
(insufficient samples)** — values are never interpolated or smoothed. Sample-count maps are linear.

## Candidate high-flux sector (exploratory)
Top coverage-passing cells cluster in the **South America / South Atlantic sector**:
- **5° (mean):** lat -22.5°, lon -52.5° (mean 31.46, median 30.86, n=431); -22.5°/-57.5° (31.41);
  -22.5°/-62.5° (29.72) — i.e. lat ≈ -22.5°/-27.5°, lon ≈ -47.5°…-62.5°.
- **2° (mean):** lat -21°…-25°, lon -51°…-59° (mean ≈ 32). Offered only as a *candidate high-flux
  sector*, not a measured anomaly center/shape.

## Validation
`python scripts/validate_cp4a_outputs.py` → **ALL CHECKS PASSED**: regional parquet present;
31/31 daily files; monthly region rows (205,153) > one-day (7,244); grid tables + required columns;
sample-count populated; coverage masks present; 6 figures present; notebook executed; real source
files (no fake data).

## Caveats
1. **Exploratory monthly aggregation**, single channel/satellite — not a final SAA boundary/center.
2. **Differential ~25 MeV flux**, not integral, not dose/health.
3. **`mep_IFC_on == -1`** retained and uninterpreted (192k rows); revisit when its meaning is confirmed.
4. **Sub-satellite geographic binning only**; no IGRF/magnetic coordinates yet; no degradation or
   inter-satellite calibration applied.
5. Mean is pulled above the median in high-flux cells (right-skewed per-cell distributions) — both
   are provided so later analysis can choose.

## Next checkpoint (Checkpoint 4B)
Threshold sensitivity: vary flux threshold / channel / grid resolution / satellite / time window on
the coverage-masked grids and quantify how the candidate **center, area, and intensity** change.

---

# Checkpoint 4B — Threshold Sensitivity Results

**Date:** 2026-06-08 · **Status:** ✅ complete & validated (18/18 checks pass).
**Scope:** methodological sensitivity test of *candidate high-flux regions* / *threshold-defined
footprints* with *method-dependent centers* and *area proxies* — exploratory. **Not** a true SAA
boundary/center, dose, health risk, or discovery.

## Inputs used
The accepted CP4A monthly grid tables only (no regeneration from raw data): NOAA-19, Jan 2024,
`mep_omni_flux_p1`, region lat[-70,20]×lon[-100,20], 5° and 2°, statistics `mean_flux` & `median_flux`.

## Coverage mask used
Only cells passing the CP4A masks: **5° → 432/432** cells, **2° → 2,685/2,700** cells. Coverage-failed
cells are excluded from all thresholding and left blank in figures.

## Threshold definitions
Percentile cutoffs among coverage-passed cells: **80/90/95/98/99th** = **top 20/10/5/2/1 %**, for each
of {5° mean, 5° median, 2° mean, 2° median} → **20 rows** (`outputs/tables/cp4b_threshold_sensitivity.{csv,parquet}`).

## Cell-area method
Spherical-cap approximation per cell: `area = R² · Δlon_rad · (sin(lat_N) − sin(lat_S))`, **R = 6371 km**
(never raw cell count). Two centroids per selection: **unweighted** (mean of cell centers) and
**flux-weighted** (weighted by the thresholded statistic). Longitude is averaged directly — acceptable
because the region (lon -100..+20) is limited and far from the ±180 wrap (documented assumption).

## Summary of centroid shifts (flux-weighted, top 20% → top 1%)
| grid · statistic | top20 center | top1 center | shift |
|---|---|---|---|
| 5° mean   | (-20.2, -55.3) | (-23.5, -56.5) | **386 km** |
| 5° median | (-20.2, -55.0) | (-23.5, -55.6) | 371 km |
| 2° mean   | (-20.2, -55.1) | (-23.0, -56.4) | 343 km |
| 2° median | (-20.1, -55.2) | (-22.8, -55.9) | 307 km |

As the threshold tightens, the center migrates **south/south-west** (toward ≈ lat -23°, lon -56°).
**Largest observed shift: ~386 km** (5° mean, top20→top1).

## Summary of area changes
Selected area shrinks from **≈25.0 M km² (≈22.9 % of the covered region) at top 20%** to
**≈1.2–1.5 M km² (≈1.1–1.3 %) at top 1%** — a ~17–20× reduction. `selected_cell_count`: 5° 87→5, 2° 537→27.

## Comparison: 5° vs 2°
Flux-weighted centers agree closely (e.g. **top10 mean: ~32 km apart**); the 2° footprint is just a
finer-resolution version of the same candidate sector — resolution does not move the center much.

## Comparison: mean vs median
Nearly identical centers (**top10: ~4 km apart at 5°, ~11 km at 2°**); the choice of mean vs median has
little effect on the threshold-defined center at these thresholds.

## Figures (`outputs/figures/`)
`cp4b_threshold_overlay_{5deg,2deg}_{mean,median}.png` (grey log10 base map + nested top-X% markers +
flux-weighted centroid `x`; blank = no data / coverage-failed; no smoothing/interpolation) and
`cp4b_centroid_shift_by_threshold.png` (flux-weighted centroid path vs threshold for all four combos).

## Validation
`python scripts/validate_cp4b_outputs.py` → **ALL CHECKS PASSED**: CP4A tables present; sensitivity
CSV+Parquet; required columns; **20 rows**; selected_cell_count>0 & selected_area_km2>0 for all;
both centroids inside region; finite cutoffs; 5 figures; notebook executed; available counts match the
real CP4A coverage (432/2,685 — no fake data).

## Caveats
1. **Threshold-defined footprints are methodological objects**, not physical boundaries; the center
   depends on the chosen threshold (a few hundred km of movement across top20→top1).
2. Single channel/satellite/month; `mep_omni_flux_p1` is differential ~25 MeV; **not** dose/health.
3. **`mep_IFC_on == -1`** retained and **uninterpreted** (carried from CP4A); not resolved here.
4. `total_flux_area_proxy` = Σ(statistic × cell_area) is a **proxy**, not a physically integrated flux.
5. Geographic (sub-satellite) framing only; no IGRF/magnetic coordinates yet.

## Next checkpoint
Extend the sensitivity sweep to the remaining axes (proton channel, satellite, time window), then —
only afterwards — consider a magnetic-coordinate (IGRF) framing of the candidate sector.

---

# Checkpoint 4C — Proton Channel Sensitivity Results

**Date:** 2026-06-08 · **Status:** ✅ complete & validated (27/27 checks pass).
**Scope:** *channel-dependent footprints* / *method-dependent high-flux regions*. **Not** a true SAA
boundary, danger zone, dose, health risk, or discovery. **Absolute flux is NOT comparable across
channels** (different energies) — footprint **location/shape** is compared, not absolute intensity.

## Channels tested & metadata (read from the NetCDF, not guessed)
| channel | `long_name` (energy) | `units` | dtype |
|---|---|---|---|
| `mep_omni_flux_p1` | MEPED proton differential flux at **25 MeV** omnidirection telescope | `#/cm2-s-str-MeV` | float32 |
| `mep_omni_flux_p2` | MEPED proton differential flux at **50 MeV** omnidirection telescope | `#/cm2-s-str-MeV` | float32 |
| `mep_omni_flux_p3` | MEPED proton differential flux at **100 MeV** omnidirection telescope | `#/cm2-s-str-MeV` | float32 |

## Inputs / filters
NOAA-19, Jan 2024 (**31/31 days**), region lat[-70,20]×lon[-100,20], lon → [-180,180), drop
`mep_IFC_on==1` (0 rows), keep `==-1` (uninterpreted). Multi-channel regional subset:
`data/processed/noaa19_2024-01_mep_omni_flux_p1_p2_p3_region.parquet` (205,153 rows, 4,504,948 B,
zstd, sha256 `13c28321…`).

## Missing-value rate per channel
**p1 0.0000 %, p2 0.0000 %, p3 0.0000 %** (no missing). Per-cell means are all positive for every
channel at both resolutions, so percentile thresholding is well-defined (no degenerate cutoffs).

## Coverage thresholds
`sample_count` is sampling-based (same orbital coverage), so the coverage masks are **identical across
channels** — the CP4A `>=30` threshold remains valid (5°: 432/432; 2°: 2,685/2,700). No change needed.

## Grids & sensitivity table
6 grid tables `outputs/tables/cp4c_noaa19_2024-01_{p1,p2,p3}_grid_{5deg,2deg}.parquet`; sensitivity
`outputs/tables/cp4c_channel_threshold_sensitivity.{csv,parquet}` — **60 rows** (3 channels × 2 grids
× 2 statistics × 5 thresholds; columns include `channel`, `channel_units`, `channel_metadata_note`),
sha256 csv `1347a47a…` / parquet `1deff1c4…`.

## Centroid differences across channels (flux-weighted, 5° mean)
Footprints **overlap strongly** — centers within ~100–300 km:
- **top10:** p1↔p2 122 km, p1↔p3 **209 km**, p2↔p3 104 km. **top5:** max 200 km. **top1:** max 299 km.
- positions (top10): p1 (-21.2°, -55.6°), p2 (-22.0°, -55.0°), p3 (-22.2°, -54.0°). The p3 (100 MeV)
  center sits slightly **south & east** of p1 (25 MeV).

## Area differences across channels
At a fixed percentile the footprint size is **essentially channel-independent**: selected area at
top10 (5° mean) = p1 **12.61**, p2 **12.54**, p3 **12.53 M km²** (same cell count, similar latitudes).

## 5° vs 2°
Agree qualitatively — the same candidate high-flux sector and channel ordering; finer grid does not
move the centers materially (consistent with CP4B's ~32 km 5°-vs-2° agreement).

## Intensity (reported, NOT compared as the same quantity)
peak per-cell mean: p1 31.5, p2 21.5, p3 13.7 `#/cm2-s-str-MeV` — decreasing with energy as
physically expected, but these are **different energies**; absolute values are not equated.

## Figures (`outputs/figures/`)
`cp4c_noaa19_2024-01_{p1,p2,p3}_mean_flux_5deg.png` (3), `cp4c_channel_comparison_top10_{5deg,2deg}_mean.png`
(2), `cp4c_channel_centroid_comparison.png`, `cp4c_channel_area_by_threshold.png`.

## Caveats
1. **Channel-dependent, method-dependent footprints** — not physical boundaries.
2. **Absolute flux not comparable across energies**; only location/shape compared; no "more dangerous" channel.
3. `mep_IFC_on == -1` retained and **uninterpreted**.
4. Geographic (sub-satellite) binning only; no IGRF/magnetic coordinates; single satellite/month.

## Next checkpoint
Satellite sensitivity (other POES/MetOp satellites), then time-window sensitivity; only afterwards an
IGRF/magnetic-coordinate framing.

---

# Checkpoint 4D — Time-Window Sensitivity Results

**Question:** how stable is the threshold-defined candidate high-flux footprint as the *aggregation
time window* changes, with satellite (NOAA-19), channel (`mep_omni_flux_p1`, ~25 MeV), region, grid
logic and threshold machinery all fixed? Time-window sensitivity only — **not** a final SAA boundary.

## Windows tested (8)
`day_2024-01-01` (1 d) · `days_2024-01-01_to_07` (7 d) · `days_2024-01-01_to_14` (14 d) ·
`month_2024-01` (31 d) · four disjoint weeks `week1` 01-01..07 · `week2` 01-08..14 ·
`week3` 01-15..21 · `week4` 01-22..28 (7 d each).

## Files loaded / missing
All 31 NOAA-19 Jan-2024 daily L1b files loaded; **no missing days**. The month is read once (31 file
opens) and each window is an in-memory date slice, so `files_loaded == files_expected == day_count`
for every window.

## Row counts (region, IFC-filtered)
day 7,244 · 7-day/week1 43,524 · 14-day 88,277 · month 205,153 · week2 44,753 · week3 47,570 ·
week4 48,180.

## Coverage thresholds by window/grid (the key methodological choice)
Coverage masks are **not** a blind reuse of CP4A's `>=30`. The minimum-sample threshold scales with
exposure, anchored to CP4A (`>=30` over 31 days ~ 1 sample/day/cell):
`min_samples = max(3, round((30/31) * day_count))` — **same for 5deg and 2deg** (as in CP4A).
Result: day=3, 7-day/weekly=7, 14-day=14, month=30. Cells passing coverage:

| window | 5deg pass / 432 | 2deg pass / 2700 |
|---|---|---|
| day_2024-01-01 | 201 (47%) | 517 (19%) |
| 7-day / week1 | 429 | 2097 |
| 14-day | 432 | 2405 |
| month | **432** | **2685** |
| week2 / week3 / week4 | 428 / 432 / 427 | 2136 / 2214 / 2236 |

The **full-month row reproduces CP4A coverage exactly** (432/432, 2685/2700), confirming consistency
with the accepted product. The one-day window is the only one flagged `one-day orbit-track sparse`
(47% / 19% regional coverage).

## Centroid stability summary (flux-weighted, 5deg mean)
- **top10:** day (−18.90, −54.29) → 7-day (−20.85, −55.79) **+267 km** → 14-day (−21.13, −55.60)
  **+37 km** → month (−21.15, −55.64) **+5 km**. Day→month total **288 km**.
- **top5:** day→7-day **+138 km** → +63 km → +61 km; day→month total **204 km**.
The footprint center moves most going from the sparse 1-day map to 7 days, then **stabilises**
(<40 km thereafter) once coverage fills in.

## Area stability summary
Selected top-10% area proxy (5deg mean): day 6.11 M km² (sparse) → 7-day 12.34 → 14-day 12.61 →
month 12.61 M km². Once coverage is adequate (≥7 days) the area proxy is stable to ~2%.

## Weekly comparison summary
The four disjoint weeks (equal 7-day exposure) cluster tightly: top10 5deg-mean flux-weighted
centroids span a **max pairwise distance of 118 km**, with comparable areas (~12.2–12.6 M km²). So
the residual day→month drift is dominated by coverage filling in, not large week-to-week physical
swings.

## Resolution / statistic agreement
- 5deg vs 2deg (month, top10, mean) flux-weighted centroid: **32 km** apart.
- mean vs median (month, top10, 5deg): **4 km** apart.
Qualitative agreement across both axes.

## Caveats
1. Coverage (orbital sampling) is the dominant inter-window difference and is measured/flagged, not
   silently mixed with physical/temporal variability. The 1-day window (esp. 2deg, tight thresholds)
   is too sparse to treat as final — reported but flagged.
2. Threshold-defined, time-window-dependent, coverage-limited footprints / area proxies — **not** a
   true SAA boundary, center, dose, health risk, danger zone, or discovery.
3. `mep_IFC_on == -1` retained and uninterpreted. Single satellite/channel/month; sub-satellite
   geographic binning only; no IGRF.

## Outputs
160-row table `outputs/tables/cp4d_time_window_threshold_sensitivity.{csv,parquet}`; 16 grid tables
`cp4d_{window}_grid_{5,2}deg.parquet`; 4 cumulative regional parquets; 11 figures `cp4d_*.png`.
Produced by `notebooks/04d_time_window_sensitivity.ipynb`; validated by
`scripts/validate_cp4d_outputs.py` (ALL CHECKS PASSED).

## Next checkpoint
Satellite sensitivity (other POES/MetOp satellites) — kept last among the data axes because
inter-satellite calibration / instrument differences are more involved — then an IGRF /
magnetic-coordinate framing.

---

# Checkpoint 4E — Satellite Availability Audit and Pilot Comparison

**Question:** can the accepted monthly gridding + threshold pipeline be applied to another comparable
POES/MetOp satellite for the same month/channel/region, and do the threshold-defined footprints remain
broadly similar? **Pilot compatibility check only** — not a full multi-satellite study, not a
calibrated physical comparison.

## Satellites found (real NCEI archive, 2024 listing)
Five satellites have a 2024 L1b directory and **complete 31/31 January 2024** daily files:
`noaa15, noaa18, noaa19, metop01, metop03`. Archive pattern (verified):
`https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/2024/<sat>/poes_<token>_<YYYYMMDD>_proc.nc`.
All five open with the CP2 loader and carry `time/lat/lon/alt`, `mep_omni_flux_p1`, `mep_IFC_on`, with
**identical** channel units (`#/cm2-s-str-MeV`) and long_name (*"MEPED proton differential flux at 25
MeV omnidirection telescope"*) to NOAA-19. No missing days for any candidate.
Audit table: `outputs/tables/cp4e_satellite_availability_audit.{csv,parquet}` (14 columns).

## Pilot chosen: NOAA-18
All four non-reference satellites were `eligible`; **NOAA-18** selected as the closest NOAA-19 analog —
same POES series and SEM-2/MEPED instrument generation (MetOp = different EUMETSAT platform; NOAA-15 =
oldest, most degraded). Simplest, most defensible first cautious comparison. One pilot only.

## Files expected/loaded/missing (pilot)
NOAA-18: **31/31** daily files loaded, **no missing days**. Region (lat[-70,20]×lon[-100,20], lon
[-180,180), `mep_IFC_on==1` dropped=0, `==-1` kept=195,680 uninterpreted): **208,722 region rows**
(NOAA-19 CP4A: 205,153). Processed: `data/processed/cp4e_noaa18_2024-01_mep_omni_flux_p1_region.parquet`.

## Metadata compatibility
Variable names, dtype, channel units and long_name **identical** to NOAA-19. The only difference is
absolute flux magnitude (see below), which is **not cross-calibrated**.

## Row counts & coverage comparison (coverage threshold ≥30, same as CP4A for both — fair constant)
| grid | NOAA-19 cells pass | NOAA-18 cells pass | sample_count median (N19 / N18) |
|---|---|---|---|
| 5° | 432/432 | 432/432 | 477 / 487 |
| 2° | 2685/2700 | 2571/2699 | 76 / 78 |
NOAA-18 has slightly lower 2° coverage (2571 vs 2685) but comparable sampling; ≥30 kept for both and
reported so the difference is visible, not hidden.

## Threshold sensitivity table
`outputs/tables/cp4e_satellite_pilot_threshold_sensitivity.{csv,parquet}` — **40 rows** (2 sats × 2
grids × 2 stats × 5 thresholds), columns add `satellite`, `coverage_threshold_used`,
`satellite_compatibility_note`. selected_cell_count min = 5 (>0).

## Centroid differences vs NOAA-19 (flux-weighted, 5° mean)
- **top10:** NOAA-19 (−21.15, −55.64) vs NOAA-18 (−21.18, −55.76) → **13 km**.
- **top5:** (−21.57, −55.76) vs (−21.58, −55.95) → **20 km**.
Footprints **broadly overlap** in location.

## Area differences vs NOAA-19
top10 and top5 selected area proxies are **identical to 0.0%** (12.61 / 6.31 M km²): at 5° both
satellites have full coverage and the same percentile selects the same cells, so the area-proxy and
shape match. Inter-satellite **footprint consistency** in location and area.

## Caveats
1. **Absolute flux is NOT cross-calibrated.** NOAA-18 peak (36.2) > NOAA-19 (31.5) in the top cell; this
   may reflect instrument response/degradation, orbit/local-time sampling, or coverage — **not**
   necessarily a physical difference. Only footprint location/shape is compared.
2. Pilot compatibility check, single additional satellite, single month/channel; not a multi-satellite
   study. Threshold-defined, calibration-limited footprints — not a true SAA boundary/center, dose,
   health risk, danger zone, or discovery. `mep_IFC_on==-1` retained, uninterpreted; no IGRF.
3. Loader hardening: `download_poes_file` now takes a `timeout` (default 120 s) — a stalled NCEI
   connection raises instead of hanging forever (the previous `urlretrieve` had no timeout).

## Outputs
Audit table; pilot regional parquet; pilot 5°/2° grid tables; 40-row sensitivity table; 8 figures
`cp4e_*.png`. Produced by `notebooks/04e_satellite_pilot_comparison.ipynb`; validated by
`scripts/validate_cp4e_outputs.py` (ALL CHECKS PASSED).

## Next checkpoint
With the pilot showing strong footprint consistency, a fuller multi-satellite comparison (add MetOp +
NOAA-15) is feasible — but only with explicit calibration caveats. Alternatively, move to an IGRF /
magnetic-coordinate framing (deferred since CP1).

---

# Checkpoint 4F — Multi-Satellite Footprint Consistency (calibration-cautious)

**Question:** do independently measured, threshold-defined high-flux footprints appear in broadly the
same location across the available POES/MetOp satellites for January 2024? **Footprint-location/shape
consistency only** — NOT an absolute-intensity comparison, NOT a claim any satellite is more correct.
`absolute_flux_comparison_allowed = False` on every sensitivity row.

## Satellites included / excluded
Reusing + re-confirming the CP4E audit: **all five** satellites included, **none excluded** —
`noaa15, noaa18, noaa19` (NOAA-POES) + `metop01, metop03` (MetOp). Each: full 31/31 Jan-2024 coverage,
opens with the loader, has `time/lat/lon/alt`, `mep_omni_flux_p1`, `mep_IFC_on`, **identical** p1 units
(`#/cm2-s-str-MeV`) and long_name (25 MeV). Compatibility table:
`outputs/tables/cp4f_satellite_compatibility.{csv,parquet}`.

## File availability & metadata compatibility
No missing days for any satellite. Channel metadata identical across all five (only the *absolute*
flux magnitude differs — not cross-calibrated).

## Row counts & coverage (coverage threshold ≥30 applied consistently)
| satellite | region rows | 5° cells pass | 2° cells pass | sc5 med | sc2 med |
|---|---|---|---|---|---|
| metop01 | 227,572 | 432/432 | 2700/2700 | 528 | 85 |
| metop03 | 226,645 | 432/432 | 2700/2700 | 526 | 82 |
| noaa15 | 207,232 | 432/432 | 2665/2700 | 485 | 78 |
| noaa18 | 208,722 | 432/432 | 2571/2700 | 487 | 78 |
| noaa19 | 205,153 | 432/432 | 2685/2700 | 477 | 76 |
MetOp has the densest sampling; all five have full 5° coverage; 2° coverage is comparable
(2571–2700). NOAA-19 reproduces CP4A coverage exactly (432 / 2685).

## Threshold sensitivity table
`outputs/tables/cp4f_multisatellite_threshold_sensitivity.{csv,parquet}` — **100 rows**
(5 sats × 2 grids × 2 stats × 5 thresholds) + `satellite_family_or_platform`,
`coverage_threshold_used`, `satellite_compatibility_note`, `absolute_flux_comparison_allowed=False`.
selected_cell_count min = 5.

## Pairwise flux-weighted centroid distances (`cp4f_pairwise_centroid_distances.{csv,parquet}`, 40 rows)
Max pairwise centroid spread across satellites:
| case | max spread | median |
|---|---|---|
| top10 5° mean | **272 km** | 105 km |
| top5 5° mean | **437 km** | 125 km |
| top10 2° mean | 254 km | 83 km |
| top5 2° mean | 372 km | 84 km |
**NOAA-18 and NOAA-19 cluster within ~13 km**; MetOp-01/03 sit within ~50–80 km of them. **NOAA-15 is
the consistent outlier** — its top10/5° centroid is 217–272 km from the others (centroid lon ≈ −53.1°
vs ≈ −55.6° for the rest) and its uncalibrated peak flux is anomalously high (77.8 vs 26–36). This is
consistent with NOAA-15 being the oldest platform (instrument aging / detector response / sampling) —
**reported, not claimed as physical truth; its absolute flux is not compared.**

## Comparison to CP4B threshold sensitivity magnitude
Inter-satellite footprint spread (top10, 5° mean) = **272 km**, vs CP4B **intra-satellite** centroid
shift top20→top1 (5° mean) = **386 km**. So choosing a different satellite moves the candidate
footprint center *less* than choosing a different flux threshold does — the footprint is **more
sensitive to method (threshold) than to which satellite is used**, even including the NOAA-15 outlier.

## Caveats
1. **Absolute flux NOT compared** (`absolute_flux_comparison_allowed=False`). Differences may be
   calibration, instrument aging, detector response, orbital/local-time sampling, or platform — not
   physical. Only footprint location/shape compared.
2. NOAA-15 outlier flagged, not excluded; not interpreted as "wrong". Single month/channel.
3. Threshold-defined, calibration-limited footprints — not a true SAA boundary/center, dose, health
   risk, danger zone, or discovery. `mep_IFC_on==-1` retained, uninterpreted; no IGRF.

## Outputs
Compatibility table; 5 regional parquets; 10 grid tables; 100-row sensitivity table; 40-row pairwise
table; 16 figures `cp4f_*.png`. Produced by `notebooks/04f_multisatellite_consistency.ipynb`;
validated by `scripts/validate_cp4f_outputs.py` (ALL CHECKS PASSED).

## Next checkpoint
With footprint location shown to be robust across satellites and methods, the natural next step is the
long-deferred **IGRF / magnetic-coordinate framing** (re-express the footprint in B/L or magnetic
lat/lon), and/or a temporal/seasonal extension beyond January 2024.

---

# Checkpoint 5A — IGRF / Magnetic-Coordinate Audit and Pilot Framing

**Question:** what magnetic/IGRF information is in the NOAA POES/MetOp files, and can the Jan-2024
particle-defined high-flux footprint be *described* in magnetic-coordinate terms without overclaiming?
**Audit + descriptive pilot only.** Particle-defined footprint (high measured flux) and magnetic/IGRF
model variables are kept **conceptually separate** — related, not identical. No causality, no "SAA =
field minimum", no boundary/dose/health/danger/discovery.

## Variables found (real NetCDF metadata, NOAA-19 2024-01-01)
**29 magnetic/IGRF/coordinate-related variables, all 0% missing**: IGRF field components
`B{r,t,p,x,y,z}_{sat,foot}`, totals `Btot_sat`/`Btot_foot`; `L_IGRF`; `MLT`; satellite magnetic
lat/lon `mag_lat_sat`/`mag_lon_sat`; field-line foot coordinates `mag_lat_foot`/`mag_lon_foot`,
`aacgm_lat_foot`/`aacgm_lon_foot`, `geod_lat_foot`/`geod_lon_foot`; pitch angles
`meped_alpha_{0,90}_{sat,foot}`, `ted_alpha_{0,30}_{sat,foot}`. **The files already provide IGRF
products → no external IGRF package was added.** Audit table:
`outputs/tables/cp5a_magnetic_variable_audit.{csv,parquet}`.

## Variables selected / excluded
Selected for the pilot (`cp5a_selected_magnetic_variables.{csv,parquet}`): **`Btot_sat`** (descriptive —
IGRF total field at satellite), **`L_IGRF`** (descriptive — IGRF L-shell; **-1 = documented invalid
sentinel**, excluded in analysis), **`mag_lat_sat`** + **`mag_lon_sat`** (descriptive — satellite
magnetic coords), **`MLT`** (caution-only — local time, sampling-dependent). Excluded for a first
pilot: field components (`B*_sat/foot`), foot-point coordinates, pitch angles (detector geometry),
`Btot_foot`, `geod_*_foot` (redundant with geographic).

## Processed dataset
`data/processed/cp5a_noaa19_2024-01_region_flux_plus_magnetic.parquet` — **205,153 rows** (matches the
accepted CP4A region exactly; CP4 files **not** overwritten), columns = CP2 base + `mep_IFC_on` +
`L_IGRF, Btot_sat, mag_lat_sat, mag_lon_sat, MLT` + `lon180`.

## Inside-vs-outside footprint magnetic distributions (4 pilot cases, descriptive)
`cp5a_footprint_magnetic_distributions.{csv,parquet}` (20 rows). High-flux footprint samples occupy a
**markedly narrower magnetic range** than the full region (top10 5° mean shown; consistent across
top5 / 2°):
| variable | median inside | median outside | IQR inside | IQR outside |
|---|---|---|---|---|
| Btot_sat (nT) | 16,621 | 20,242 | **593** | 3,978 |
| L_IGRF | 1.29 | 1.55 | **0.13** | 1.13 |
| mag_lat_sat (deg) | −9.6 | −20.8 | **10.5** | 49.4 |
| MLT (hours) | 8.9 | 9.6 | 12.0 | 12.2 |
- **Btot_sat** and **L_IGRF** discriminate strongly: the footprint sits at **low, narrow field
  strength / low L** (IQR ~7–11× narrower). Descriptive only — the SAA is conventionally the
  field-strength minimum, but this is **not asserted as causal** and the footprint is **not** equated
  with the field minimum.
- **MLT** does **not** discriminate (expected — local time, not a spatial SAA coordinate).
- **mag_lon_sat** wraps [0,360); its IQR is not a clean spread (documented caveat).

## Diagnostic figures
`cp5a_particle_footprint_geographic_reference.png` (top10/top5 footprint), `cp5a_flux_vs_L_IGRF.png`,
`cp5a_flux_vs_magnetic_latitude.png`, `cp5a_flux_vs_MLT.png`, `cp5a_flux_vs_Btot_sat.png`,
`cp5a_high_flux_samples_magnetic_space.png`, `cp5a_geographic_Btot_sat_map.png` — all labelled
"DESCRIPTIVE DIAGNOSTIC".

## What CP5A can / cannot say
**Can:** the NOAA files carry usable IGRF variables; the particle-defined footprint occupies a confined
low-`Btot`/low-`L` magnetic band, much narrower than the regional background (descriptive). **Cannot:**
anything causal; footprint ≠ field minimum; no SAA boundary; foot-point vs satellite-coordinate choice
unresolved; single satellite/month/channel.

## Recommended CP5B
Promote `Btot_sat` and `L_IGRF` (+ `mag_lat_sat`) to a quantitative magnetic-coordinate framing:
flux vs L/B binning, wrap-aware magnetic-longitude handling, and a foot-point vs satellite-coordinate
comparison — still descriptive, with calibration/sampling caveats.

## Outputs
3 tables (audit, selection, distributions) + 1 processed parquet + 7 figures. Produced by
`notebooks/05a_magnetic_coordinate_audit.ipynb`; validated by `scripts/validate_cp5a_outputs.py`
(ALL CHECKS PASSED).

---

# Checkpoint 5B — Quantitative Magnetic-Coordinate Framing

**Question:** how can the particle-defined high-flux footprint be *described* in magnetic-coordinate
terms, and which NOAA-provided magnetic variables best separate high-flux samples from the regional
background? **Still descriptive** — no causality, footprint ≠ field minimum, no boundary, no
dose/health/danger/discovery. Input: `cp5a_noaa19_2024-01_region_flux_plus_magnetic.parquet` (CP4/CP5A
files untouched).

## Validity rules + excluded counts (`cp5b_magnetic_variable_validity.csv`)
| variable | rule | rows valid | rows invalid | valid range |
|---|---|---|---|---|
| Btot_sat | finite & >0 | 205,153 | 0 | 16,015–32,434 nT |
| L_IGRF | finite, ≠ −1 sentinel, >0 | 201,239 | **3,914** | 1.10–6.48 |
| mag_lat_sat | finite & [−90,90] | 205,153 | 0 | −66.6…31.6° |
| mag_lon_sat | finite & [0,360], **wrap-aware only** | 205,153 | 0 | 0–360° (no naive IQR/mean) |
| MLT | finite & [0,24], local-time diagnostic only | 205,153 | 0 | 5.08–23.72 h |

## Magnetic-binned flux profiles (`cp5b_magnetic_binned_flux_profiles.{csv,parquet}`, 50 rows)
Fixed-width bins over each variable's valid range (14 Btot, 12 each L/mag_lat/MLT; bin edges in the
table). Per bin: sample_count, median/mean/p90/p95 flux, and fraction of bin samples in the top10/top5
geographic footprint. The top10-footprint fraction rises sharply toward the **lowest Btot_sat** bins —
a descriptive concentration, **not** a boundary.

## Footprint magnetic summary (`cp5b_footprint_magnetic_summary.{csv,parquet}`, 16 rows)
`separation_metric := (median_out − median_in)/(0.5·(iqr_in+iqr_out))`; +ve ⇒ footprint lower.
Top10 5° mean:
| variable | median in | median out | IQR in | IQR out | separation |
|---|---|---|---|---|---|
| Btot_sat | 16,621 | 20,242 | 593 | 3,978 | **+1.58** |
| L_IGRF | 1.29 | 1.55 | 0.13 | 1.13 | +0.41 |
| mag_lat_sat | −9.6 | −20.8 | 10.5 | 49.4 | −0.38 |
| MLT | 8.9 | 9.6 | 12.0 | 12.2 | +0.06 |
`Btot_sat` separates by far the most; `MLT` essentially not. (Consistent across top5 and 2° cases.)

## Concentration metrics (`cp5b_magnetic_concentration_metrics.csv`, 16 rows; descriptive)
- **~100% of top10 AND top5 footprint samples lie below the regional Btot_sat 25th percentile**
  (18,258 nT).
- 50% / 75% / 90% of the **top10** footprint is captured within only the lowest **5.1% / 8.4% / 12.0%**
  of regional `Btot_sat` (top5: **2.6% / 4.5% / 6.6%**) — a tight low-field concentration.
- `L_IGRF` concentrates **more weakly**: only **8.6%** of the top10 footprint (0.03% of top5) is in the
  regional lowest-L quartile; 50% of the top10 footprint needs the lowest **36.8%** of regional L.
  → Among NOAA-provided variables, **`Btot_sat` frames the footprint far more sharply than `L_IGRF`.**

## Diagnostic figures (10)
4 flux profiles (`cp5b_flux_profile_by_{Btot_sat,L_IGRF,mag_lat_sat,MLT}.png`), 3 inside/outside
(`cp5b_inside_outside_{Btot_sat,L_IGRF,mag_lat_sat}.png`), 2 Btot-vs-L
(`cp5b_flux_Btot_vs_L_IGRF.png`, `cp5b_high_flux_footprint_Btot_vs_L_IGRF.png`), 1 wrap-aware
mag-lat/lon (`cp5b_mag_lat_vs_mag_lon_wrapaware.png`) — all labelled "DESCRIPTIVE", no boundary lines.

## Key caveats
Descriptive only — no causality, footprint not equated with the field minimum, no SAA boundary. Low-Btot
concentration could be partly orbital-sampling; magnetic variables are IGRF **model** quantities;
`mag_lon_sat` summarized only via wrap-aware plotting (not IQR/mean); single satellite/month/channel;
`L_IGRF −1` excluded. `mep_IFC_on==-1` uninterpreted.

## Recommended CP5C
Test generality of the low-`Btot_sat` framing across the CP4F satellites and/or other months (still
descriptive); optionally a foot-point vs satellite-coordinate comparison and wrap-aware circular
statistics for `mag_lon_sat`.

## Outputs
4 tables (validity, profiles, footprint summary, concentration) + 10 figures. Produced by
`notebooks/05b_magnetic_framing.ipynb`; validated by `scripts/validate_cp5b_outputs.py`
(ALL CHECKS PASSED).

---

# Checkpoint 6A — Results Synthesis and Mentor Packet

**Synthesis only — no new scientific axis, no new raw data, no new analysis.** Turns the accepted
CP4B–CP5B results into a coherent article plan + a professor/mentor review packet.

## Synthesis files created
- `outputs/tables/cp6a_key_results_summary.{csv,parquet}` — 5 rows (one per result area) with exact
  numbers pulled from the accepted tables; columns: result_area, checkpoint_source, input_data, metric,
  main_numeric_result, interpretation_allowed, overclaim_to_avoid, supporting_table_or_figure,
  paper_section_candidate.
- `docs/CLAIM_AUDIT.md` — A) supported claims, B) plausible-not-proven, C) forbidden claims + standing
  data caveats.
- `docs/PAPER_OUTLINE.md` — 10-part outline; primary title *"Mapping the South Atlantic Anomaly from
  Public POES/MetOp Proton Flux Data: A Reproducibility and Method-Sensitivity Study"* (+2 alternates);
  verbatim research question.
- `docs/FIGURE_PLAN.md` — 6 core (main) figures + supplement set, with captions and what-each-must-not-claim.
- `docs/MENTOR_PACKET.md` — summary, question, data, methods, results, limits, 8 concrete technical
  questions for a physics professor (channel choice, sat- vs foot-coordinate, Btot defensibility,
  over-interpretation, literature, `mep_IFC_on==-1`, MEPED calibration caveats, statistics).
- `docs/REPRODUCIBILITY_CHECKLIST.md` — env, data sources, notebook order, validator order, expected
  outputs, regenerate-from-scratch, limitations.
- `scripts/validate_cp6a_outputs.py` — checks all of the above (ALL CHECKS PASSED).

## Core results (now the headline set)
threshold centroid shift ~386 km / area ~17.7×; channel ~100–300 km; day→month ~288 km (weekly
~118 km); 5-satellite spread ~272 km (< threshold effect; NOAA-15 outlier); footprint concentrated at
low `Btot_sat` (~100% below regional q25; Btot > L > MLT as framing variables).

## Claims that remain forbidden
final SAA boundary/center; dose; health risk; danger zone; discovery; replacing professional radiation
models; physical causality from IGRF variables alone; cross-satellite absolute-flux comparison.

## Recommended next step
Send `docs/MENTOR_PACKET.md` to a physics mentor; incorporate feedback (esp. channel choice,
coordinate convention, calibration caveats, citations) before any CP5C multi-month/multi-satellite
magnetic generality work or drafting.

---

# Checkpoint 5C — Multi-Satellite Magnetic Generality (January 2024)

**Fixed scope:** `noaa15`, `noaa18`, `noaa19`, `metop01`, and `metop03`; January 2024;
`mep_omni_flux_p1`; the accepted CP4F footprint definitions; and the principal top10, 5° mean case.
Every magnetic comparison is within satellite. Cross-satellite absolute flux comparison remains
forbidden.

## Predeclared operational rubric and result

A satellite supports the low-`Btot_sat` relationship only when (1) Btot separation is > 0, (2) >50%
of footprint samples lie below its regional Btot q25, and (3) the lowest 50% or less of its regional
Btot distribution contains 90% of its footprint. It supports Btot dominance only when Btot separation
exceeds both L separation and absolute MLT separation. The checkpoint is `CONSISTENT` when at least
4/5 satellites pass each group; `INCONSISTENT` when 0–1 pass the low-Btot group or the Btot sign is
broadly reversed; otherwise it is `MIXED`.

**Rubric result: `CONSISTENT` — 5/5 low-Btot support, 5/5 Btot-dominance support, 0/5 reversed Btot
signs.** These are predeclared operational criteria for CP5C, not physical thresholds defining the
SAA. NOAA-19 separately passed the hard reproduction gate: deterministic memberships/counts matched
exactly, and floating metrics matched with `rtol=1e-9`, `atol=1e-12`, `equal_nan=True`.

## Principal raw satellite-level metrics

| satellite | Btot sep | L sep | MLT sep | footprint below regional Btot q25 | regional Btot fraction capturing 90% | low-Btot | Btot dominance |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| noaa15 | 1.596147 | 0.387097 | 0.919967 | 1.000000 | 0.118963 | yes | yes |
| noaa18 | 1.572744 | 0.428571 | 0.048053 | 1.000000 | 0.120877 | yes | yes |
| noaa19 | 1.584260 | 0.412698 | 0.056082 | 1.000000 | 0.120371 | yes | yes |
| metop01 | 1.572559 | 0.393701 | −0.034783 | 1.000000 | 0.117669 | yes | yes |
| metop03 | 1.583358 | 0.396825 | −0.040630 | 1.000000 | 0.116626 | yes | yes |

## Narrative interpretation (after rubric evaluation)

The NOAA-19 low-Btot description generalizes cleanly across the five January-2024 platforms under
the frozen particle-footprint definitions: each footprint is concentrated in the lowest roughly 12%
of its own regional Btot distribution, and Btot separates inside from outside more sharply than L or
absolute MLT. The MLT result is not uniform: four satellites are close to zero, while NOAA-15 has
substantial positive MLT separation (+0.920); it still remains below NOAA-15's Btot separation
(+1.596). This is descriptive co-location with NOAA-provided IGRF model quantities, not causality and
not a magnetic definition of the SAA.

The fit-flag diagnostic is consistent across satellites rather than identifying one anomalous
platform: 99.76–100% of principal-footprint samples have `mep_omni_flux_flag_fit == 0`. It is reported
as a diagnostic only; no new fit-flag filtering was introduced. `mep_IFC_on == 1` removed one NOAA-15
regional row and none for the other satellites; `-1` remains retained and uninterpreted.

## Outputs and validation

Five regenerable regional Parquets, five tables in CSV+Parquet form, and two figures were produced by
`notebooks/05c_multisatellite_magnetic_generality.ipynb`. Independent validation is in
`scripts/validate_cp5c_outputs.py`; all checks passed on the real 31-files-per-satellite inputs.
