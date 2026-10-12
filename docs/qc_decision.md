# QC decision: the NOAA-15 record of 2024-01-19 09:14:30 UTC (QC-1)

Decision date 2026-10-02. Status: **adopted for the primary analysis, post hoc**. Evidence bundle:
`outputs/paper_qc/20261002_noaa15_qc/`; reproducible outputs: `outputs/qc_sensitivity/`,
`outputs/tables/qc1_omni_exclusions.csv`.

## Question

Can a transparent, reproducible, consistently applicable quality-control treatment justify excluding
this observation from the primary mapped analysis? (Not: "remove the record because it changes the
satellite result" or "because an external researcher finds it suspicious".)

## The record

`poes_n15_20240119_proc.nc` (SHA-256 `1209804e…0594`), zero-based native index 13867,
2024-01-19T09:14:30.051Z, −12.532°, −29.293°. Stored p1/p2/p3 = 36 016.4 / 4 825.2 / 646.4
cm⁻² s⁻¹ sr⁻¹ MeV⁻¹; its 20 native neighbours have median p1 11.7.

Evidence, all from NOAA files:

1. **Fit semantics (ATBD, Machol 2012, Table 5 and §3.4).** Fit 0 = regular four-region power-law
   fit. If the regular fit cannot be made (summed raw count rate < 25 s⁻¹, a negative derived
   non-overlapping count rate, |γ| > 8, a positive high-energy slope, or no convergence), the
   algorithm falls back to a two-point fit (2) or a one-point fit with γ_default = −2.9 (1). Fit 1
   is a documented mode, not an invalidity flag.
2. **Time series.** One-record discontinuity: the preceding and following records are at the prior
   level; neighbours carry fit 0, the record fit 1. Two-sided p1 ratios 3 272 / 2 869.
3. **The three channels are one number.** p1/p2 = p2/p3 = 7.464 = 2^2.9 (the default slope), so
   the "simultaneous p1/p2/p3 enhancement" is not three independent confirmations.
4. **Co-located MEPED channels.** The directional P6 proton fluxes (0° and 90°) are exactly 0 in
   this record and ≥ 6 098 on every neighbour.
5. **Level-1a count rates** (`poes_n15_20240119_raw.nc`, NCEI `l1a/v01r00`, SHA-256
   `59cd88dd…626f`, retrieved with the author's approval as evidence only): OMNI >35 MeV = 487 424 s⁻¹
   (neighbours 752–1 056; highest elsewhere that day 2 752), while >16 MeV = 904 s⁻¹ (neighbours
   752–1 000). A >35 MeV integral rate 539× the >16 MeV rate is physically impossible for one particle
   population; the derived 16–35 MeV rate is negative, which precludes the regular fit and leaves the
   one-point default-slope fit, consistent with the stored flag and slopes. All 12 directional proton
   count channels and 5 of 6 electron count channels read exactly 0 in the record. The OMNI bias-voltage
   housekeeping field reads a value seen nowhere else that day for 16 records starting one record
   earlier (coincidence reported, not interpreted).

What this does **not** establish: the instrumental or telemetry cause.

## External criteria

NOAA documentation gives flag-based QA only (ATBD §5.3; the users' manual says users should rely on
error estimates, which the processed OMNI files do not carry). Lin et al. (2019) removed "clearly
erroneous" scattered points from the same >16 MeV OMNI data **by manual processing**. No
externally grounded automatic threshold exists; QC-1 is therefore a stated post-hoc rule.

## Rule QC-1 v1.0 (`src/saa/quality.py`)

Per daily file, in native order, a record's OMNI values (p1–p3) are set missing when:

1. its fit flag is 1 or 2 (fallback);
2. its 10 preceding and 10 following records form one contiguous run (every step > 0 and ≤ 6 s) and
   all have fit 0;
3. for at least one channel, all 20 neighbour values are finite and > 0 and the value exceeds
   100 × the median of the preceding ten **and** 100 × the median of the following ten.

All three channel values of a flagged record are excluded (one fit). Unevaluable records are kept.
Identity = source SHA-256 + native index. No clipping, replacement or upper cutoff; raw files
unchanged. Applied in the loader before region selection and gridding; `qc=False` gives the
unfiltered values.

Parameter basis: regular fits never depart from both neighbourhoods by more than 3.3× (p1; 349 822
evaluable records); isolated fallbacks depart by a median 3.1–5.2× per satellite and at most 19.8×
(1 242 records), the default-slope bias; the ratio is set ~5× above that. Condition 2 restricts
the rule to count rates that support the regular fit, where a two-sided ×100 jump is not counting
noise.

## Application to the whole population

6 313 670 native records, 155 files, all channels. Excluded: **one record** (the NOAA-15 event,
all three channels; one p1 value in the analysed combinations). Every other fallback value kept.

Perturbations (35 variants, `outputs/qc_sensitivity/perturbation.csv`): 26 give exactly the same set,
including every ratio 20–2 000, 3–30 neighbours per side, step limits 3–20 s, ≥ 50–100% regular
neighbours, no fallback condition, and p1-only/any/all-channel triggers. The set changes only when
the ratio enters the fallback's own departure range (15×: 4 records; 10×: 30) or when the regular-fit
neighbour condition is dropped (32 records, 8 in region: low-flux fallback values next to near-zero
neighbours — the historical triage candidates), plus joint corners (20× with 5 neighbours: 6).
The records added at 15× were inspected: isolated one-point fits at low flux on the SAA edge with
non-zero directional channels.

QC-1 can act only where neighbourhoods are all regular fits: 32.5% of regional records.

## Acceptance criteria

| Criterion | Assessment |
|---|---|
| 1. Explainable without naming the event | Yes: rule text above names no satellite, date or value. |
| 2. Applied consistently | Yes: every record of all 155 files, all channels, in the loader. |
| 3. Does not remove gradual intense structures | Yes: two-sided condition; max regular-fit ratio 3.3; tests with intense smooth passes and ramps. |
| 4. Does not treat fit 1 as invalid | Yes: 1 241 isolated fallbacks and all other fit-1/2 values retained. |
| 5. Removed records individually explained | Yes: one record; ledger, neighbourhood, level-1a evidence. |
| 6. Robust to reasonable perturbations | Yes within the documented boundaries above. |
| 7. Can be stated honestly | Yes: paper states post hoc, rule, counts, unfiltered result, no clipping. |

## Impact (primary QC-1 vs unfiltered)

Only NOAA-15 products change: 29 derived files (NOAA-15 region/grids, satellite sensitivity and
pairwise tables, CP5C tables, CP6A, NOAA-15/satellite figures); 154 derived files are byte-identical,
including every NOAA-19 threshold, channel and time-window product. Site payload: 20 NOAA-15
configurations change, 340 unchanged.

| Quantity | QC-1 (primary) | Unfiltered (sensitivity) |
|---|---|---|
| Five-satellite max, 5° mean top 10% | 113.4 km (NOAA-15/NOAA-18) | 284.1 km (NOAA-15/MetOp-03) |
| Same, 2° mean | 98.3 km | 264.6 km |
| 5° median top 10% | 112.5 km | 112.5 km |
| 5° mean over top 20…1% | 113–157 km | 245–1 460 km |
| NOAA-15 principal centroid | −21.71°, −54.91° | −20.96°, −52.89° (225 km east) |
| Event 5° cell mean / rank | 9.31 / 51 | 77.76 / 1 |
| CP5C NOAA-15 footprint samples | 21 405 | 21 442 |

5° median maxima are identical at every threshold; the 2° top-20% median maximum differs by 0.001 km.
1 015 NOAA-15 regional records change top-10%/5° membership. CP5C B_tot separation 1.5958 → 1.5960,
capture-90% 0.1190 → 0.1186; other satellites and the retired classification unchanged.

The rule-based exclusion reproduces the earlier exact-record omission exactly (all pairwise distances
and event-cell values), and the unfiltered scenario reproduces the earlier as-is evidence; the
unfiltered omission replay (`outputs/omission_sensitivity/`) stays byte-identical to the frozen
Phase 2 hashes.

## Remaining uncertainty

Cause of the count-rate inconsistency; single-record artefacts outside regular-fit stretches and
multi-record artefacts are not screened; the provider's contamination warning stands.
