# SAA POES Mapping

Reproducible mapping and methodological sensitivity analysis of a candidate
high-flux South Atlantic Anomaly footprint using public NOAA/NCEI POES/MetOp
SEM-2 MEPED proton data.

The study asks how reported footprint centroid and selected area change with flux
threshold, proton channel, spatial grid, observation window, and satellite.
It also describes the particle-defined footprint in NOAA-provided IGRF
coordinates. The quantitative scope is January 2024.

This is a methods study. It does not define a true SAA boundary or center,
estimate dose or health risk, claim discovery, infer magnetic causality, or
compare uncalibrated absolute flux across satellites.

## Results

- Tightening the footprint from the top 20% to top 1% shifts its
  area-aware flux-weighted centroid by about 433 km (351–433 km across grids and statistics).
  Area changes by about 17.7×, but the percentile rule itself prescribes a nominal 20× change
  in selected cells, so the contraction is not independent evidence.
- The principal three-channel comparison has a maximum pairwise centroid separation of about 210 km.
- One day to one month differs by about 289 km; the 3-day state is 138 km from the
  month end to end (area-weighted Jaccard 0.540), but on the cells eligible in both maps the
  recomputed footprints are 14 km apart (Jaccard 0.829); the 7-day state is 39 km end to end.
  The month contains every window, so this is descriptive January 2024 NOAA-19 sampling,
  not a universal timescale. Weekly centroids lie within 16–118 km of one another.
- The five-satellite top-10%, 5° mean footprint spread is about 113 km (112.5 km with cell
  medians); NOAA-18 and NOAA-19 differ by about 13 km. This applies quality rule QC-1, adopted
  post hoc, which excludes one NOAA-15 record whose >35 MeV count rate is inconsistent with its own
  >16 MeV rate ([decision record](docs/qc_decision.md)). Unfiltered, the spread is about 284 km;
  that result is kept as a sensitivity.
- All five satellites satisfy the descriptive low-`Btot_sat` criteria. The MLT-based
  dominance interpretation and combined classification are retired because linear
  clock-label separation depends on the arbitrary hour origin.

Phase 3 ran 1,000 paired calendar-block replicates for each of 1, 3 and 7 days.
The p1–p3 displacement persists conditionally; 5° mean continuous-field overlap is
0.933. These are descriptive stability findings, not calibrated physical confidence.
See [channel assurance](docs/channel_assurance.md), [integrity report](docs/integrity_report.md)
and the [QC-1 decision record](docs/qc_decision.md).

See [claims](docs/claims.md) for accepted wording and limitations.

## Paper

The manuscript and supplement are in [`paper/`](paper/) (Typst sources; PDFs in `paper/build/`).
Every number in them is generated from `paper/generated/claims_register.json`. The
single reproduction command is
`python scripts/reproduce_paper.py --audit-baseline <baseline.tar.gz> --qc-evidence <poes_n15_20240119_raw.nc>`;
see [`paper/REPRODUCE.md`](paper/REPRODUCE.md). This version is a local, uncommitted working
tree pending author review; it is not on the remote main branch and has no DOI.

## Public research site

The TypeScript/SVG site in `site/` displays 360 validated configurations. Its
JSON is exported from canonical Python results; the browser does not calculate
thresholds, coverage, area, centroids, or unsupported parameter combinations.

```bash
python scripts/export_site_data.py
python scripts/generate_site_geography.py
cd site
npm ci
npm run dev
```

Run `npm test` and `npm run build` from `site/` to validate and build the
static site. Build output is written to `site/dist/`.

## Analysis environment

Python 3.12 and `uv` are recommended:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m ipykernel install --prefix .venv --name python3
.venv/bin/python -m unittest discover -s tests -v
```

The notebooks are the ordered scientific workflow. Generated data, tables,
and figures are git-ignored and reproducible from public inputs. Full notebook
order, validation commands, expected outputs, and provenance links are in
[reproducibility](docs/reproducibility.md).

## Data and method

Source data are NOAA/NCEI POES/MetOp SEM-2 MEPED Level 1b processed NetCDF
(`v01r00`) files for NOAA-15, NOAA-18, NOAA-19, MetOp-01, and MetOp-03. The
analysis uses coverage-aware 5° and 2° geographic grids, mean and median cell
statistics, percentile-defined footprints, spherical cell areas, and
area-aware flux-weighted centroids.

- [Methodology](docs/methodology.md)
- [Claims and interpretation boundaries](docs/claims.md)
- [Reproducibility](docs/reproducibility.md)
- [Processed-data provenance](data/processed/PROVENANCE.md)
- [Sample-data provenance](data/samples/PROVENANCE.md)
- [Paper outline](docs/paper_outline.md)
- [Figure plan](docs/figure_plan.md)

## Repository structure

```text
src/saa/        analysis, plotting, and deterministic export modules
notebooks/      ordered executable scientific workflow
scripts/        artifact generation and independent validators
tests/          scientific, export, and website contract tests
site/           public research website
docs/           method, claims, reproduction, and manuscript planning
data/           ignored data products with tracked provenance records
outputs/        ignored scientific tables and figures
```

## Citation and license

When citing the analysis, reference this repository and the exact Git commit
used, and cite the NOAA/NCEI POES Space Environment Monitor data product.
Software is released under the [MIT License](LICENSE). NOAA data retain their
source terms and attribution.
