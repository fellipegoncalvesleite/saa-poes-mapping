# SAA POES Mapping

Reproducible mapping and methodological sensitivity analysis of a candidate
high-flux South Atlantic Anomaly footprint using public NOAA/NCEI POES/MetOp
SEM-2 MEPED proton data.

The study asks how estimated footprint center and area change with flux
threshold, proton channel, spatial grid, observation window, and satellite.
It also describes the particle-defined footprint in NOAA-provided IGRF
coordinates. The quantitative scope is January 2024.

This is a methods study. It does not define a true SAA boundary or center,
estimate dose or health risk, claim discovery, infer magnetic causality, or
compare uncalibrated absolute flux across satellites.

## Results

- Tightening the footprint from the top 20% to top 1% shifts its
  flux-weighted centroid by about 386 km and changes area by about 17.7×.
- Proton-channel centroid differences are approximately 100–300 km.
- One day to one month differs by about 288 km; four weekly windows agree
  within about 118 km.
- The five-satellite top-10%, 5° mean footprint spread is about 272 km;
  NOAA-18 and NOAA-19 differ by about 13 km.
- All five satellites satisfy the predeclared low-`Btot_sat` and
  `Btot_sat`-dominance criteria. This is descriptive co-location with low
  modeled field strength, not causation.

See [claims](docs/claims.md) for accepted wording and limitations.

## Public research site

The TypeScript/SVG site in `site/` displays 340 validated configurations. Its
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
flux-weighted centroids.

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
