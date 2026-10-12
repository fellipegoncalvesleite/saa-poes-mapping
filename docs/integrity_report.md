> **Superseded in part (2026-10-02).** The NOAA-15 record discussed below is now excluded from the
> primary analysis by the post-hoc quality rule QC-1; the as-is analysis is kept as the unfiltered
> sensitivity. See [qc_decision.md](qc_decision.md). The rest of this report remains a historical record of
> Phases 1–3.

# Integrity and channel assurance report

The audit was executed locally on 2026-09-29, starting from commit `67e31ac5228dc3102aa70e6899a2d4657dc3bc17`. At the time of the audit, the changes were uncommitted.

Evidence root: `outputs/paper_integrity/20260929_phases1_3/`. The original tracked tree was clean; original derived artifacts and source code are preserved in `phase1/baseline.tar.gz`, with starting hashes and patch. All 31 initially cached NOAA source hashes and all 155 analyzed source hashes are unchanged. The missing 124 January files were retrieved from NOAA without overwriting cached originals. Raw-file bytes predating this run for those 124 files were not available; all five saved regional p1 tables nevertheless matched reconstructed source values exactly before correction.

## Phase 1 executed

The NOAA-15 event is file `poes_n15_20240119_proc.nc`, SHA-256 `1209804e1f2e59b49f0e55f0d5be6246e89fef9df3c8641f76d6dbf679bb0594`, zero-based native index **13867**, UTC **2024-01-19 09:14:30.051Z**, p1 **36016.3671875**. Native float32 storage, independent NetCDF reading, xarray extraction and saved parquet agree. The coordinates are -12.5319996°, -29.2929993° after longitude conversion. Its 21-record native neighborhood and ±5-minute unfiltered context include real p1/p2/p3, gamma, fit/iteration/IFC flags and time gaps; no unavailable detector diagnostics were invented.

NOAA's [OMNI ATBD Table 5](https://www.ngdc.noaa.gov/stp/satellite/poes/docs/NGDC/MEPED_OMNI_processing%20ATBD_V1.pdf) identifies fit 1 as a simplified one-point fit with default slope. It is not an automatic invalidity rule. IFC -1 remains semantically unknown. The source itself is calibrated processed flux (metadata Level 2) in the archive's L1b/v01r00 tree, not detector telemetry. Upstream presence does not establish physical or instrumental cause.

The 5° cell (-12.5,-27.5) changes from 526 observations, sum 40903.439589, mean 77.763193 and median 9.337800 to 525 observations, sum 4887.072402, mean 9.308709 and median 9.337800 under exact-key omission. The event contributes 88.0522% of that cell sum. The mean cell falls from rank 1 to 51 and leaves top10; its prior centroid weight is 8.6209%. Median was recalculated and is unchanged in this particular cell. All 5°/2°, mean/median and five-threshold cases were recalculated; selected memberships, areas, centroids and ten satellite pairs are saved. Independent spherical-zone area, fsum centroid and vector-angle distance calculations pass without calling the production reference helpers.

Maximum top10/5°/mean pair distance: **284.090147 km**, NOAA-15/MetOp-03, as-is; **113.429840 km**, NOAA-15/NOAA-18, under omission. The documented-quality correction below leaves these principal values unchanged. In the historical NOAA-15 population, changed footprint-cell memberships affect 1,015 observations for top10/5°, 972 for top5/5°, 194 for top10/2°, and 158 for top5/2°; identities are saved, not inferred from the event's presence in an old CP5 table.

The census covers **6,313,670 unique native records**, **8,727,210 channel values**, 155 files and seven existing satellite/channel combinations. It finds 39 candidate channel values at 32 unique records; the separately labeled historical 10×file-p99.99 diagnostic finds 6 unique records. Evaluable fractions range 24.54–49.86%; missing/zero neighbors and native gaps remain unevaluable. Deterministic top-five values per combination, full candidates, flag frequencies and exclusions are saved. Starting processed artifacts contain 1,853,262 record appearances, 1,075,324 unique source records and 777,938 reused appearances; these are not counted as new observations. Candidate status is triage, never an exclusion decision. Only the named event received omission sensitivity; other candidates do not have demonstrated influence or invalidity from that trigger alone.

## Phase 2 implemented and regenerated

- Retained the influential but unresolved NOAA-15 event in the primary mean baseline. Its exact-key omission remains separate from the export.
- Corrected a different validity defect: 298 negative analyzed native channel values, representing 252 records, include 29 regional p1 values (-999, fit=-1): 25 NOAA-15 and 4 NOAA-18. The [NOAA user manual Table A-1](https://www.ngdc.noaa.gov/stp/satellite/poes/docs/NGDC/External_Users_Manual_POES_MetOp_SEM-2_processing_V1.pdf) gives a zero minimum for OMNI channels; the ATBD defines fit=-1 as no fit. Extraction now converts negative OMNI or no-fit channel values to NaN consistently. Valid zero and fit 1/2 are retained. No upper cutoff or automatic despiking is used. Magnetic framing excludes these invalid p1 observations before recomputing memberships and summaries.
- Fixed missing-flag integer casting in all three loaders. A synthetic fill/scale/separate-dimension NetCDF regression verifies missingness and positional alignment. Actual January flags contain no NaN, so this safety fix has no additional baseline numerical effect.
- **MLT: reproduced.** Real summary separation for the wrapping probe is 0.066946 vs 5.000 after a 12-hour shift. The nonwrapping control remains 5; 0/24 handling is probed. Actual January separations also change, although the legacy five-satellite classification happens not to flip under this shift. Active MLT dominance and combined classification are retired. Legacy numeric tables/functions are explicitly labeled; descriptive Btot/L remain. No replacement circular separation is promoted.
- **Classifier: reproduced documentation mismatch.** A/B/C/D low supporters and A/B/C/E dominance supporters yield historical CONSISTENT despite only three joint supporters. Separate-count v1 is retained and documented, with aligned-four/all-five controls. This wording mismatch alone did not change January's all-five outcome.
- **Exporter: reproduced.** A one-degree stored-centroid perturbation in an otherwise internally valid temporary bundle was silently replaced. Export now rejects inconsistent centroids, cutoffs, selected/covered counts, selected area/fraction and peak flux. Current pre-intervention centroid tables had already matched their grids. Active magnetic narrative derives the low-Btot count and labels the combined rubric retired; MLT/dominance fields are null and the site contract handles them explicitly.

Rebuilt notebooks 02 through 05c in dependency order, with CP6 synthesis before/after CP5C as required by the existing chain. Regenerated extracted/processed products, CP4 grids and all existing 360 configurations (20 threshold, 60 channel, 180 time including CP4D.1, 100 satellite), CP5 memberships and magnetic summaries, synthesis, figures and payload. `phase2/baseline_to_current.csv` records actual changed metrics. Some NOAA-15/18 lower-threshold/fine-grid metrics changed; no NOAA-19 CP4B/C/D metric changed. Maximum absolute affected centroid-coordinate change in the impact table is about 0.125°; principal five-satellite spread is unchanged. Raw source files remain untouched.

## Phase 3 implemented and run

Frozen protocol 1.0, paired 1/3/7-day blocks ×1,000, same recorded seed and day draws across channels, calendar missingness and repeat multiplicity preserved. Rebuilt coverage, percentiles, selected cells and centroids in every replicate. No undefined pairs or silent redraws. Full draws, 9,000 channel rows, 9,000 pair rows, quantiles, eligibility and dependence diagnostics are saved.

Observed p1–p3 displacement is -1.060123° latitude, +1.684086° longitude, **210.441666 km**. Its directional conditional quantiles retain their signs at all three block lengths; p3–p2 latitude quantiles cross zero. These are **CONDITIONAL RESAMPLING STABILITY** findings, not calibrated physical-position confidence or physical significance. The 31-day sample, stationarity/dependence uncertainty, edge underweighting and few long blocks are documented.

Common coverage support is identical between channels: 432 cells at 5°, 2,685 at 2°, with zero extra exclusions. Continuous normalized p1–p3 field overlap is **0.932509**, with whole-field distance **143.191378 km** at 5° mean. All 5°/2° mean/median checks ran; pairwise overlaps span 0.919383–0.972383. Whole-region field averages do not automatically identify the SAA center. See `docs/channel_assurance.md` / `phase3/FINDINGS.md` for signed intervals and all comparisons.

## Verification and review

See final `VERIFICATION.md` and logs for exact final test/validator counts, deterministic replay, site build and visual inspection. Scientific CSVs and figures are compared separately from timestamps and operational logs. Earlier failed runs remain in the evidence with their repaired causes; they are not claimed as passing.

Additional verification covered all Phase 3 input hashes, group counts, paired quantiles, normalized masses and original-support agreement with CP4C. A P3 protocol-label guard was implemented with a failing regression and fail-fast fixed-protocol validation. These checks do not constitute external domain peer review.

**Author review: pending.** Fellipe has not been represented as having reviewed the critical code. No executable phase is blocked. Unresolved scientific limitations remain the NOAA-15 event cause, IFC -1 semantics, absent historical raw hashes for formerly uncached satellites, single-month scope, instrument/channel dependence and uncalibrated statistical inference. Stop after Phase 3; ready for Phase 4 consolidation, not a finished paper or Phase 6 clean-room reproduction.

## Critical-code walkthrough for Fellipe (pending author review)

1. `src/saa/load_poes.py`: `_flux_col` applies the narrow documented lower-bound/no-fit rule; `_flag_col` preserves missing flags. Observe that fit 1 and zero survive.
2. `src/saa/integrity.py`: `omit_record` requires one source hash/native-index match. `review_trigger` respects consecutive native neighbors and gap boundaries. Reference area/centroid/distance formulas do not call production helpers.
3. `src/saa/magnetic_audit.py`: invalid p1 observations are excluded before CP5 summaries; counts distinguish geographic, IFC and channel-quality stages.
4. `src/saa/magnetic_generality.py`: separate-count legacy rubric remains reproducible and marked retired. Active export no longer exposes its dominance as evidence.
5. `src/saa/viewer_export.py`: grid/mask-derived values validate canonical authority; disagreement raises instead of silently replacing values. Examine the temporary-bundle regression.
6. `src/saa/channel_assurance.py`: `draw_days`, `combine_days`, `replicate_metrics`, `normalized_fields`, `validate_protocol`. The test with repeated/missing days protects multiplicity and weighted means. Read `scripts/run_channel_assurance.py` together with saved protocol and equivalence tables.
7. `site/src/data/{types,load}.ts` and `site/src/ui/content.ts`: explicit null retired fields and low-Btot descriptive display; no new explorer computation or configuration.

## Main changed paths

`src/saa/{load_poes,magnetic_audit,magnetic_framing,magnetic_generality,viewer_export,integrity,channel_assurance}.py`; new audit/regeneration/assurance scripts; affected tests; notebooks 02–05c; `docs/`, `README.md`, processed provenance; regenerated `data/processed`, `outputs/tables`, `outputs/figures`; `site/index.html`, types/validation/content/styles and `site/public/data/viewer_data.json`. Final patch, content manifest and code archive provide identity beyond unchanged HEAD.
