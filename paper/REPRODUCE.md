# Reproducing the paper

Everything in `paper/build/main.pdf` and `paper/build/supplement.pdf` (numbers, figures, tables)
is regenerated from the 155 raw January 2024 NOAA/NCEI SEM-2 daily files by one command.

## 1. Inputs (not redistributed)

- `data/raw/poes_{n15,n18,n19,m01,m03}_202401DD_proc.nc` — 155 files. Names, sizes, SHA-256 and
  source URLs: `paper/tables/S1_raw_manifest.csv`; recorded hashes: `paper/inputs/raw_manifest_recorded.csv`.
  Fetch missing files from `https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/2024/<satellite>/`
  and **reject any file whose hash differs** (an upstream re-release is a different input).
- `poes_n15_20240119_raw.nc` — the NCEI level-1a companion file of the QC-1 record, read only as
  evidence (never an analysis input). SHA-256 and URL: `paper/inputs/qc_evidence_hashes.json`. A copy is
  kept in `outputs/paper_qc/20261002_noaa15_qc/evidence/source_raw_counts/`.
- `baseline.tar.gz` (SHA-256 in `paper/inputs/frozen_hashes.json`): the preserved original extractor
  and tables, used only to replay the Phase 1 triage census quoted in Supplement S7.
- `site/public/data/geography.json` (tracked; Natural Earth 1:110m, public domain).

## 2. Environment

```bash
uv venv --python 3.14.7 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt
cd site && npm ci && cd ..       # Node 24 / npm 11 were used; only needed for the site checks
```

## 3. Run

```bash
.venv/bin/python scripts/reproduce_paper.py --audit-baseline /path/to/baseline.tar.gz \
    --qc-evidence /path/to/poes_n15_20240119_raw.nc
```

The steps, in order: raw-hash verification; notebooks 02–05c (all derived tables and grids);
QC-1 ledger, population envelopes, perturbation study and unfiltered sensitivity (about 10 minutes);
level-1a count-rate evidence; the NOAA-15 exact-record omission replayed on unfiltered data (must stay
byte-identical to the frozen Phase 2 evidence); replay of the frozen channel-resampling protocol
(`paper/inputs/channel_assurance_protocol.json`, seed 20260929) with a byte check of the draws;
temporal coverage/conditional diagnostics; census replay; two site-payload exports compared
byte for byte; claims register; figures and supplementary tables; PDFs; unit tests; all artifact
validators; site tests and build. It stops at the first failure and writes
`outputs/reproduction/summary.json` plus one log per step. Add `--skip-site` without Node.

Individual steps can be rerun on their own:

| Output | Command |
|---|---|
| QC-1 evidence + unfiltered sensitivity | `python scripts/run_qc_sensitivity.py` |
| level-1a count-rate evidence | `python scripts/qc_raw_count_evidence.py --l1a PATH` |
| omission replay (unfiltered, provenance) | `python scripts/run_omission_sensitivity.py` |
| Portuguese reader (personal, not for publication) | `python paper/reader/build_reader.py` (needs `paper/reader/requirements-reader.txt`) |
| channel resampling replay | `python scripts/run_channel_assurance.py --output outputs/channel_assurance --protocol paper/inputs/channel_assurance_protocol.json` |
| temporal diagnostics | `python scripts/run_temporal_support.py` |
| claims register + `values.typ` | `python scripts/build_claims_register.py` |
| figures + supplementary CSVs | `python scripts/make_paper_figures.py` |
| PDFs | `python paper/build.py` |

(Set `PYTHONPATH=src` when running these directly.)

## 4. What "reproduced" means

- Scientific CSV/Parquet/JSON outputs are compared exactly or with the tolerances the validators
  already declare. Timestamps, machine paths and notebook execution metadata are not science.
- PDFs are rebuilt with embedded fonts and a fixed timestamp. Two PDFs are compared by their
  rendered text and inputs, not by byte identity.
- A run from a hash-verified cache is a fresh *derived-output* reproduction; it does not
  independently re-fetch NOAA's historical files.
