# SAA POES Mapping

> **⚠️ Work in progress.** This is an active research project — methods and
> numbers below are preliminary and still being validated; expect changes.

Reproducible **mapping and methodological sensitivity analysis of the South Atlantic Anomaly
(SAA)** using public NOAA/EUMETSAT **POES/MetOp SEM-2 MEPED** energetic-particle data.

**Research question (long-term):** When mapping the SAA from public low-Earth-orbit energetic
particle data, how much do the estimated **center, area, and intensity** change under different
methodological choices — proton channel, flux threshold, spatial grid resolution, satellite, and
time window?

**This project does _not_:** discover the SAA · compute biological dose · replace
radiation-transport models · do generic Monte-Carlo. The contribution is *methodological*:
reproducibility + sensitivity analysis on public data.

## Current status (CP5C — validated magnetic-generality extension after CP6A)
- **What works:** a reproducible, validated pipeline through CP6A, plus the validated CP5C extension,
  that maps a candidate high-flux footprint from real NOAA/NCEI POES/MetOp data and quantifies its
  sensitivity to flux threshold,
  proton channel, time window, and satellite, plus a descriptive IGRF magnetic-coordinate framing.
- **Current scientific question:** *how much does the estimated SAA footprint (center/area/intensity)
  move under method choices, and how can it be described — not defined — in geomagnetic coordinates?*
- **Headline numbers:** threshold centroid shift ~386 km / area ~17.7×; channel ~100–300 km; day→month
  ~288 km (weekly ~118 km); 5-satellite maximum pairwise spread ~272 km for top10 5° mean (top5:
  ~437 km); all 5 satellites pass CP5C's predeclared low-`Btot_sat` and Btot-dominance criteria.
- **Synthesis docs:** `docs/{CLAIM_AUDIT,PAPER_OUTLINE,FIGURE_PLAN,MENTOR_PACKET,REPRODUCIBILITY_CHECKLIST}.md`.
- **Open the viewer:** `bash scripts/open_cp3_viewer.sh` (or `xdg-open outputs/viewer/index.html`).
- **Run validations:** `.venv/bin/python scripts/validate_cp5c_outputs.py` (plus the prerequisite
  validators listed in `docs/REPRODUCIBILITY_CHECKLIST.md`).
- **Do NOT claim:** final SAA boundary/center · dose · health risk · danger zone · discovery ·
  causality from IGRF variables · cross-satellite absolute-flux comparison. See `docs/CLAIM_AUDIT.md`.

## Status
- **CP1 — Data access & feasibility audit: ✅** See [`docs/research_notes.md`](docs/research_notes.md).
- **CP2 — Minimal reproducible loader: ✅** Real NOAA-19 L1b NetCDF → validated tidy one-day parquet.
- **CP3 — First exploratory map: ✅** One-day lon/lat proton-flux maps + bare local HTML viewer.
- **CP4A — Monthly aggregation & coverage-aware grids: ✅** Jan 2024 (31/31 days) → regional subset,
  5°/2° coverage-masked grid tables, monthly figures.
- **CP4B — Threshold sensitivity analysis: ✅** Top 20/10/5/2/1% footprints on the coverage-masked
  grids → 20-row sensitivity table + overlay/centroid-shift figures (method-dependent centers).
- **CP4C — Proton channel sensitivity (p1/p2/p3): ✅** 60-row channel sensitivity table + comparison
  figures; footprints overlap strongly (centers within ~100–300 km).
- **CP4D — Time-window sensitivity: ✅** 8 windows (1/7/14/31 days + 4 weeks), per-window coverage
  thresholds → 160-row sensitivity table; footprint stabilises once coverage fills in (day→month
  centroid drift ~290 km, but day→7-day is the bulk; weekly windows within ~120 km).
- **CP4E — Satellite audit + NOAA-18 pilot: ✅** Real NCEI audit (5 satellites, full Jan-2024
  coverage, identical p1 metadata) → 40-row pilot table; NOAA-18 vs NOAA-19 footprints broadly overlap
  (top10 centroid 13 km, areas identical); absolute flux not cross-calibrated.
- **CP4F — Multi-satellite footprint consistency: ✅** All 5 satellites → 100-row table + pairwise
  centroid distances; footprints broadly overlap (max top10 spread 272 km < CP4B threshold effect
  386 km); NOAA-15 the location outlier; absolute flux explicitly not compared.
- **CP5A — IGRF / magnetic-coordinate audit + pilot framing: ✅** 29 NOAA-provided IGRF variables
  audited; descriptive inside/outside-footprint distributions show the high-flux footprint sits in a
  narrow low-`Btot_sat`/low-`L_IGRF` band (IQR ~7–11× narrower); MLT does not discriminate. No causal
  claim; particle footprint kept distinct from field model.
- **CP5B — Quantitative magnetic-coordinate framing: ✅** Validity rules + binned flux profiles +
  footprint summaries + concentration metrics; `Btot_sat` frames the footprint far more sharply than
  `L_IGRF` (~100% of footprint below regional Btot q25; 90% within lowest ~12% of regional Btot); MLT
  non-discriminating. Descriptive, no boundary/causal claim.
- **CP6A — Results synthesis, claim audit & mentor packet: ✅** Key-results table + claim audit + paper
  outline + figure plan + mentor packet + reproducibility checklist (no new analysis).
- **CP5C — Multi-satellite magnetic generality: ✅** January-2024 fixed-scope replication across all
  five CP4F satellites. Rubric result: **CONSISTENT** (5/5 low-Btot; 5/5 Btot dominance); NOAA-19
  exactly reproduces discrete CP5B references and matches floats at `rtol=1e-9`, `atol=1e-12`.
- **Next — mentor review, then multi-month/seasonal extension:** ⬜

All exploratory: no SAA boundary/center, dose, health, or discovery claims.

## Data source
NOAA **NCEI** POES/MetOp Space Environment Monitor (SEM-2), unauthenticated HTTPS:
<https://www.ncei.noaa.gov/products/poes-space-environment-monitor>
Primary product: L1b processed NetCDF-4 (`…/access/l1b/v01r00/<year>/<sat>/poes_<sat>_<YYYYMMDD>_proc.nc`).

## Layout
```
docs/research_notes.md                    audit + CP2..CP4A results (sources, vars, caveats)
src/saa/load_poes.py                      load: URL / download / open / extract / multi-day
src/saa/grid_flux.py                      lon convert / region & IFC filter / binning / top cells
src/saa/plot_maps.py                      matplotlib lon-lat heatmaps
src/saa/aggregate.py                      CP4A: month load (tolerant) / grid tables / coverage mask
src/saa/threshold_analysis.py             CP4B: percentile thresholds / spherical area / centroids
src/saa/time_window_analysis.py           CP4D: per-window coverage thresholds / window sweep / plots
src/saa/satellite_analysis.py             CP4E/4F: archive audit / pilot / multi-satellite sweep / plots
src/saa/magnetic_audit.py                 CP5A: IGRF variable audit / flux+magnetic / distributions / plots
src/saa/magnetic_framing.py               CP5B: validity rules / binned profiles / footprint summary / concentration
src/saa/magnetic_generality.py            CP5C: frozen rubric / NOAA-19 hard gate / multi-satellite summaries
notebooks/01..03_*.ipynb                  CP1..CP3 (feasibility / loader / first maps)
notebooks/04a_monthly_aggregation.ipynb   CP4A: executed monthly aggregation (real outputs)
notebooks/04b_threshold_sensitivity.ipynb CP4B: executed threshold sensitivity (real outputs)
notebooks/04c_channel_sensitivity.ipynb   CP4C: executed proton-channel sensitivity (real outputs)
notebooks/04d_time_window_sensitivity.ipynb CP4D: executed time-window sensitivity (real outputs)
notebooks/04e_satellite_pilot_comparison.ipynb CP4E: executed satellite audit + pilot (real outputs)
notebooks/04f_multisatellite_consistency.ipynb CP4F: executed 5-satellite consistency (real outputs)
notebooks/05a_magnetic_coordinate_audit.ipynb CP5A: executed IGRF/magnetic audit + pilot (real outputs)
notebooks/05b_magnetic_framing.ipynb      CP5B: executed quantitative magnetic framing (real outputs)
notebooks/05c_multisatellite_magnetic_generality.ipynb CP5C: executed five-satellite generality test
scripts/validate_*.py                     per-checkpoint validation
outputs/figures/  outputs/tables/         CP3/CP4A figures & grid tables (git-ignored)
outputs/viewer/index.html                 bare local HTML viewer of figures
data/{raw,processed,samples}/             data payloads (git-ignored) + PROVENANCE.md files
requirements*.txt                         runtime / notebook-execution dependencies
```

## Quick start (Python 3.12 via uv)
```
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m ipykernel install --prefix .venv --name python3
.venv/bin/python -m nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=python3 notebooks/04a_monthly_aggregation.ipynb
.venv/bin/python scripts/validate_cp4a_outputs.py
```

## View the maps (local HTML)
```
bash scripts/open_cp3_viewer.sh        # or: xdg-open outputs/viewer/index.html
```
Bare static viewer of the existing CP3 + CP4A figures (no server/framework) — exploratory only.
