# Reproducibility

The analysis regenerates from public NOAA/NCEI data and repository code.
Generated data, tables, and figures are git-ignored; tracked provenance files
record the inputs and checksums.

## Environment

Python 3.12 and `uv` are recommended:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m ipykernel install --prefix .venv --name python3
```

Install the public site separately:

```bash
cd site
npm ci
```

## Data and provenance

The loader downloads NOAA/NCEI Level 1b `v01r00` files on demand into
`data/raw/`. The January 2024 analysis uses NOAA-15, NOAA-18, NOAA-19,
MetOp-01, and MetOp-03. See
[`data/processed/PROVENANCE.md`](../data/processed/PROVENANCE.md) and
[`data/samples/PROVENANCE.md`](../data/samples/PROVENANCE.md) for checksums and
artifact lineage.

## Notebook execution order

Execute a notebook with:

```bash
.venv/bin/python -m nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=python3 <notebook>
```

Run in this order:

1. `notebooks/01_data_access_test.ipynb`
2. `notebooks/02_minimal_loader.ipynb`
3. `notebooks/03_first_exploratory_map.ipynb`
4. `notebooks/04a_monthly_aggregation.ipynb`
5. `notebooks/04b_threshold_sensitivity.ipynb`
6. `notebooks/04c_channel_sensitivity.ipynb`
7. `notebooks/04d_time_window_sensitivity.ipynb`
8. `notebooks/04e_satellite_pilot_comparison.ipynb`
9. `notebooks/04f_multisatellite_consistency.ipynb`
10. `notebooks/05a_magnetic_coordinate_audit.ipynb`
11. `notebooks/05b_magnetic_framing.ipynb`
12. `scripts/generate_cp6a_summary.py`, then `scripts/validate_cp6a_outputs.py`
13. `notebooks/05c_multisatellite_magnetic_generality.ipynb`

Later notebooks depend on artifacts from earlier steps. Network retrieval can
be slow; cached files are reused and partial downloads are written atomically.

## Validation

Run the test suite and checkpoint validators from the repository root:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_processed_sample.py
.venv/bin/python scripts/validate_cp3_outputs.py
.venv/bin/python scripts/validate_cp4a_outputs.py
.venv/bin/python scripts/validate_cp4b_outputs.py
.venv/bin/python scripts/validate_cp4c_outputs.py
.venv/bin/python scripts/validate_cp4d_outputs.py
.venv/bin/python scripts/validate_cp4e_outputs.py
.venv/bin/python scripts/validate_cp4f_outputs.py
.venv/bin/python scripts/validate_cp5a_outputs.py
.venv/bin/python scripts/validate_cp5b_outputs.py
.venv/bin/python scripts/validate_cp6a_outputs.py
.venv/bin/python scripts/validate_cp5c_outputs.py
.venv/bin/python scripts/export_site_data.py
.venv/bin/python scripts/validate_viewer_outputs.py
```

The final two commands regenerate and independently validate the public site's
340-state scientific payload and fixed five-satellite magnetic evidence.

Validate the website with:

```bash
cd site
npm test
npm run build
```

For local review, run `npm run dev` in `site/` and open the printed URL.

## Regenerable outputs

Expected ignored artifacts include processed parquet files in
`data/processed/`, tables in `outputs/tables/`, and figures in
`outputs/figures/`. The public JSON payload is generated at
`site/public/data/viewer_data.json`. Exporting twice from identical inputs must
produce byte-identical output.

## Limitations affecting reproduction

The quantitative scope is January 2024. The analysis uses geographic
sub-satellite binning, no cross-satellite absolute-flux calibration, and
NOAA-modeled IGRF quantities. `mep_IFC_on == -1` remains uninterpreted and
invalid `L_IGRF == -1` values are excluded. Sparse time windows can fail the
coverage threshold. See [claims.md](claims.md) for interpretation boundaries.
