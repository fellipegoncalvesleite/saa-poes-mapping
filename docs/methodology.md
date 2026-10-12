# Methodology

## Study design and scope

The study measures how a candidate high-flux South Atlantic Anomaly footprint
changes under explicit analysis choices. January 2024 is the quantitative
scope. Threshold, proton channel, aggregation window, satellite, grid
resolution, and cell statistic are varied in controlled sensitivity families;
they are not treated as a single unrestricted Cartesian parameter space.

## Source data

The source is NOAA/NCEI POES/MetOp SEM-2 MEPED Level 1b processed NetCDF,
version `v01r00`:

```text
https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/<year>/<satellite>/poes_<token>_<YYYYMMDD>_proc.nc
```

The analysis uses all available January 2024 days for NOAA-15, NOAA-18,
NOAA-19, MetOp-01, and MetOp-03. The primary variable is
`mep_omni_flux_p1`; channel sensitivity also uses p2 and p3. NetCDF metadata
identifies these as differential omnidirectional proton flux at nominal 25,
50, and 100 MeV, in `#/cm2-s-str-MeV`.

The L1b variables are positionally aligned one-dimensional arrays whose
dimensions can have different names. The loader therefore extracts aligned
arrays directly and does not use `xarray.Dataset.to_dataframe()`.

## Cleaning and geographic selection

- Longitudes in `[0, 360)` are converted with
  `((longitude + 180) % 360) - 180`.
- The analysis region is latitude `[-70°, 20°]` and longitude
  `[-100°, 20°]`.
- Rows with `mep_IFC_on == 1` are dropped. Values of `-1` are retained and
  left uninterpreted.
- `mep_omni_flux_flag_fit` is retained as a diagnostic and is not a filter.
- Missing values are not interpolated or replaced with zero.

## Coverage-aware geographic grids

Samples are binned by sub-satellite latitude and longitude on 5° and 2°
grids. Each cell records sample count and either mean or median flux. A full
month requires at least 30 samples per cell. In the January data, 432 of 432
covered 5° cells and 2,685 of 2,700 covered 2° cells pass this criterion.

Shorter windows use a duration-scaled minimum:

```text
max(3, round((30 / 31) * number_of_days))
```

This yields minimums of 3, 3, 7, 14, and 30 samples for one-day, three-day,
seven-day, fourteen-day, and monthly windows. The three-day minimum is floor-bound
(`round((30 / 31) * 3) = 3`); the floor binds but changes nothing, and that status is
reported rather than hidden. A cell failing coverage has no grid
statistic and cannot enter a footprint.

## Candidate footprint and spatial metrics

Among coverage-passed cells, flux percentiles 80, 90, 95, 98, and 99 define
the top 20%, 10%, 5%, 2%, and 1% candidate footprints. The threshold is
relative to the selected map; it is not a physical boundary.

Cell area is computed on a sphere of radius 6,371 km from the cell's latitude
and longitude bounds. Selected area is the sum of selected cell areas.
Centroids are reported both unweighted and as coordinate-wise spatial moments of the selected flux field.
For the latter, each selected cell center is weighted by `cell flux × spherical cell area`, so the discrete sum
approximates the spatial integral on unequal-area latitude–longitude cells. Straight longitude averaging is valid
here because the study region does not cross the dateline. This is a latitude/longitude moment definition, not a
3-D spherical-vector barycenter. Distances between centroids use the haversine formula.
The peak-flux cell is the coverage-passed cell with the maximum gridded statistic
(southernmost, then westernmost, on exact ties, with the tie count recorded);
coverage-rejected cells are never eligible. For time windows, each cumulative state is
compared against the full-month reference on the same grid: area-aware centroid distance,
signed selected-area difference and area ratio, and the footprint Jaccard index
(intersection over union of the actual selected cell sets, never interpolated).
The month compared with itself is exactly distance 0, ratio 1, and Jaccard 1.

## Sensitivity families

The public map payload contains 360 supported configurations:

- threshold: 20 states;
- proton channel: 60 states;
- time window: 180 states;
- satellite: 100 states.

Each family changes its named factor while holding the comparison design
fixed. This membership is canonical; unsupported parameter combinations are
not synthesized. Satellite comparisons use location and shape, not absolute
flux, because the instruments are not cross-calibrated here.

## Temporal coverage versus conditional morphology

`src/saa/temporal_support.py` (run by `scripts/run_temporal_support.py`) compares every CP4D
window W with the January reference M at the same grid, statistic and threshold. It reports
eligible-area fractions, end-to-end area-weighted Jaccard / centroid distance / area ratio of the
original footprints, monthly-footprint observability `area(F_M ∩ C_W)/area(F_M)`, and a
conditional comparison on `S = C_W ∩ C_M` with each map's percentile recomputed over S (per pair,
never a global intersection). Undefined cases carry explicit reasons. Distinct valid UTC days per
cell are descriptive, not a filter. `week1` duplicates the cumulative 1–7 January window and is
flagged as an alias.

## Magnetic-coordinate description

The footprint remains particle-defined. NOAA-provided IGRF fields are used
only to describe where its samples lie in modeled magnetic coordinates.
Validity rules are:

- `Btot_sat`: finite and greater than zero;
- `L_IGRF`: finite, not the `-1` sentinel, and greater than zero;
- magnetic latitude: `[-90°, 90°]`;
- magnetic longitude: `[0°, 360°]`, analyzed with circular/wrap-aware methods;
- magnetic local time: `[0, 24]`; legacy linear summaries are origin-dependent
  and are excluded from active dominance/classification. No substitute circular
  magnitude is claimed comparable with Btot separation.

The five-satellite generality test uses the principal top-10%, 5° mean
particle footprint and within-satellite ranks. A satellite passes the
low-`Btot_sat` criterion when its footprint-to-background `Btot_sat`
separation is positive, more than half its footprint samples fall below its
regional first quartile, and its 90% capture fraction is no more than one
half. This is retained as descriptive within-satellite evidence.

The historical v1 implementation counted >=4 low-Btot supporters and >=4
Btot-dominance supporters **separately**; they need not be the same four.
Its old "pass both" wording was inaccurate. The legacy implementation remains
for reproduction, explicitly retired from active scientific conclusions because
its dominance comparison used origin-dependent linear MLT separation.

Integrity v2 sets negative OMNI p1/p2/p3 values and fit=-1 (no fit performed)
to NaN at extraction. The product-specific basis is NOAA's External Users Manual
V1 Table A-1 (minimum zero) and OMNI ATBD Table 5 (fit semantics). Zeros and
fits 1/2 remain valid; no upper cutoff is imposed. Geographic/IFC row accounting
is separate from channel validity. Grids count finite channel values; magnetic
framing excludes invalid p1 observations from both inside and outside groups.
The January regional exclusions are 25 NOAA-15 and 4 NOAA-18; NOAA-19 has none.

Quality rule QC-1 (adopted post hoc on 2026-10-02; [decision record](qc_decision.md),
`src/saa/quality.py`) is applied per daily file in native order, before region selection and
gridding. It sets a record's OMNI p1–p3 to NaN only when the record's fit is a fallback (1 or 2),
its 10 preceding and 10 following records are contiguous (steps > 0 and ≤ 6 s) and all have the
regular fit 0, and a channel value exceeds 100× the median of each side. In January 2024 it
excludes exactly one record (NOAA-15, 2024-01-19T09:14:30.051Z, native index 13867); every other
fit-1/2 value is retained. Exclusions are counted separately from validity v2 (`qc_excluded_dropped`)
and listed with reasons in `outputs/tables/qc1_omni_exclusions.csv`. The unfiltered analysis
(`qc=False`) is kept as a sensitivity in `outputs/qc_sensitivity/`. The earlier frozen 100×
neighbour triage, which ignores fit flags, remains a historical review census only.

See [channel assurance](channel_assurance.md) for the frozen paired-day protocol,
common-support formulas, units and inferential limits.

## Interpretation

The analysis estimates method-dependent candidate footprints. It does not
measure dose, infer danger, define a true SAA boundary, or establish magnetic
causality. Current claim boundaries are maintained in
[claims.md](claims.md).
