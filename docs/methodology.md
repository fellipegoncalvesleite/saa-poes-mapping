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

This yields minimums of 3, 7, 14, and 30 samples for one-day, seven-day,
fourteen-day, and monthly windows. A cell failing coverage has no grid
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

## Sensitivity families

The public map payload contains 340 supported configurations:

- threshold: 20 states;
- proton channel: 60 states;
- time window: 160 states;
- satellite: 100 states.

Each family changes its named factor while holding the comparison design
fixed. This membership is canonical; unsupported parameter combinations are
not synthesized. Satellite comparisons use location and shape, not absolute
flux, because the instruments are not cross-calibrated here.

## Magnetic-coordinate description

The footprint remains particle-defined. NOAA-provided IGRF fields are used
only to describe where its samples lie in modeled magnetic coordinates.
Validity rules are:

- `Btot_sat`: finite and greater than zero;
- `L_IGRF`: finite, not the `-1` sentinel, and greater than zero;
- magnetic latitude: `[-90°, 90°]`;
- magnetic longitude: `[0°, 360°]`, analyzed with circular/wrap-aware methods;
- magnetic local time: `[0, 24]`, analyzed as a circular local-time variable.

The five-satellite generality test uses the principal top-10%, 5° mean
particle footprint and within-satellite ranks. A satellite passes the
low-`Btot_sat` criterion when its footprint-to-background `Btot_sat`
separation is positive, more than half its footprint samples fall below its
regional first quartile, and its 90% capture fraction is no more than one
half. `Btot_sat` dominance requires its separation to exceed both `L_IGRF`
separation and the absolute MLT separation.

The fixed classification is `CONSISTENT` when at least four of five satellites
pass both criteria. It is `INCONSISTENT` when at most one passes the
low-`Btot_sat` test or at least four show reversed-sign separation. All other
outcomes are `MIXED`. These cutoffs are operational reproducibility rules, not
physical thresholds.

## Interpretation

The analysis estimates method-dependent candidate footprints. It does not
measure dose, infer danger, define a true SAA boundary, or establish magnetic
causality. Current claim boundaries are maintained in
[claims.md](claims.md).
