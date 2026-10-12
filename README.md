# SAA POES Mapping

This repository holds the analysis, data provenance and manuscript for *Analysis choices and
orbital sampling shape a particle-defined South Atlantic Anomaly footprint*, a single-month
methodological case study of January 2024 NOAA/NCEI POES/MetOp SEM-2 MEPED omnidirectional
proton fluxes from NOAA-15, NOAA-18, NOAA-19, MetOp-01 and MetOp-03. A candidate high-flux SAA
footprint is defined as the cells above a percentile of a coverage-gated latitude–longitude grid
and summarized by spherical area and a flux-and-area-weighted centroid. The paper measures how
that location and extent change with threshold, cell statistic and grid, proton channel,
accumulation window and spacecraft; separates end-to-end differences from differences on shared
eligible support; and traces a large inter-satellite difference to a single artefactual NOAA-15
record, excluded by a stated post-hoc quality rule (QC-1) with the unfiltered result reported
alongside. Every number in the paper comes from a claims register tied to hashed outputs. It is a
methods study: it does not define a true SAA boundary or centre, estimate dose or risk, infer
magnetic causality, or compare uncalibrated absolute flux across satellites.

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
See [channel assurance](docs/channel_assurance.md), [integrity handoff](docs/integrity_handoff.md)
and the [QC-1 decision record](docs/qc_decision.md).

See [claims](docs/claims.md) for accepted wording and limitations.

## Paper

The Typst sources are in [`paper/`](paper/): `main.typ` (manuscript), `supplement.typ`,
`template.typ` and `refs.bib`. Every number in them is read from
`paper/generated/claims_register.json` via `paper/generated/values.typ`.

The PDFs are built to `paper/build/main.pdf` and `paper/build/supplement.pdf` (git-ignored):

```bash
.venv/bin/python paper/build.py
```

## Reproducing the paper

One command regenerates every derived table, the resampling, the diagnostics, the figures, the
claims register and both PDFs from the hash-verified raw files:

```bash
python scripts/reproduce_paper.py --audit-baseline /path/to/baseline.tar.gz \
    --qc-evidence /path/to/poes_n15_20240119_raw.nc
```

The two arguments are required: the preserved audit baseline (used only to replay the historical
triage census) and the NCEI level-1a file read as evidence for the QC-1 record. Add `--skip-site`
without Node. Inputs, environment (`requirements-lock.txt`), step order and what counts as
"reproduced" are documented in [`paper/REPRODUCE.md`](paper/REPRODUCE.md).

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
paper/          manuscript, supplement, claims register and paper build
data/           ignored data products with tracked provenance records
outputs/        ignored scientific tables and figures
```

## Citation

If you use this work, cite the paper and this repository; citation metadata are in
[`CITATION.cff`](CITATION.cff) (GitHub's "Cite this repository" button reads it). Until an
archival DOI is issued, reference the repository and the exact Git commit or release tag used.
Please also cite the NOAA/NCEI POES Space Environment Monitor (SEM-2) data product.

## License

Software is released under the [MIT License](LICENSE). NOAA data retain their source terms and
attribution.
