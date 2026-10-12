# Claims and interpretation boundaries

This project is a methodological sensitivity and reproducibility study of a
particle-defined candidate high-flux footprint derived from public NOAA/NCEI
POES/MetOp SEM-2 MEPED data. All quantitative results cover January 2024.
The footprint is an analysis construct, not a definitive South Atlantic
Anomaly boundary or center.

## Supported findings

For the accepted, validated analysis:

1. A persistent candidate high-flux sector appears over South America and the
   South Atlantic in January 2024 NOAA-19 `mep_omni_flux_p1` data.
2. The reported footprint centroid and selected area depend strongly on the flux threshold. From
   top 20% to top 1%, the area-aware flux-weighted centroid shifts about **433 km** on the 5° mean
   grid (351–433 km across grids/statistics). Selected area changes by about **17.7×**, but the
   percentile rule prescribes a nominal 20× change in selected cells (realized 87→5 cells), so the
   area contraction is a property of the definition, not independent evidence.
3. Footprint locations are broadly consistent across the p1, p2, and p3
   fitted proton outputs: the principal top-10%, 5° mean comparison has a
   maximum pairwise centroid separation of about **210 km**; for the top-10% footprint across both
   grids and statistics the range is 83–212 km (not the maximum across all thresholds). Absolute
   flux is not compared across channels, and the study does not separate physical energy structure
   from the shared fit and detector response.
4. One-day maps are coverage-limited. Day-to-month centroid drift is about
   **289 km**; disjoint weekly centroids lie within **16–118 km** of one another. The three-day
   cumulative state is about **138 km** from the monthly centroid end to end (area-weighted
   Jaccard **0.540**; 74.5% of the regional area eligible; only 61.5% of the monthly footprint's
   area is eligible in the window). Restricted to cells eligible in both maps, with each map's
   percentile recomputed there, the footprints are **14 km** apart (Jaccard **0.829**). For one day
   the conditional difference remains large (174 km, Jaccard 0.823). The seven-day state is about
   **39 km** end to end (Jaccard **0.887**). The month contains every window, so agreement is
   descriptive, not independent validation; the study compares end-to-end maps and maps recomputed
   on shared eligible support, and does not causally attribute differences to coverage. These are
   January 2024 NOAA-19 sampling observations, not a universal timescale.
5. Footprint locations are broadly consistent across NOAA-15, NOAA-18,
   NOAA-19, MetOp-01, and MetOp-03. With the post-hoc quality rule QC-1 applied (primary), the
   maximum top-10%, 5° mean pairwise spread is **113.430 km** (NOAA-15/NOAA-18; 112.5 km with cell
   medians; 113–157 km over the five thresholds); NOAA-18 and NOAA-19 differ by about **13 km**.
   Families are not ranked against each other: their setting ranges are not commensurate.
6. QC-1 ([qc_decision.md](qc_decision.md)) excludes exactly one record in the 155 files: NOAA-15
   record 13867 of `poes_n15_20240119_proc.nc` (2024-01-19T09:14:30.051Z), a one-point
   default-slope fit whose >35 MeV OMNI count rate (487 424 s⁻¹) is 539 times its simultaneous
   >16 MeV rate. Unfiltered (sensitivity), the spread is **284.090 km** (NOAA-15/MetOp-03) and grows
   to 1 460 km at top 1%. The rule was adopted post hoc; its excluded set is unchanged in 26 of 35
   parameter variants. The cause of the count-rate inconsistency is not established.
7. In the principal top-10%, 5° mean case, **100%** of footprint samples for
   each satellite fall below that satellite's regional `Btot_sat` first
   quartile; 90% are contained within the lowest **11.7–12.1%** of its
   regional `Btot_sat` distribution.
8. All five meet the descriptive low-Btot criterion; Btot separation is about
   +1.573 to +1.596. The legacy MLT-based dominance interpretation and combined
   classification are **retired**. Linear separation changes with clock origin;
   a replacement circular magnitude is not assumed comparable to Btot.
9. NOAA-19 channel assurance completed 3,000 paired temporal-block replicates.
   p2 and p3 lie south/east of p1 in the observed principal case, with the same
   signs throughout the reported marginal 2.5–97.5% conditional quantiles for
   1-, 3- and 7-day blocks. p3–p2 latitude quantiles cross zero. These are
   resampling stability summaries, not calibrated physical significance.
10. Common coverage support is identical across channels: 432 cells at 5° and
    2,685 at 2°. Support restriction adds no exclusions. On 5° mean continuous
    fields, p1–p3 overlap is 0.9325 and centroid distance is 143.191 km, compared
    with 210.442 km for percentile footprints. Across all four deterministic
    grid/statistic checks, pairwise field overlaps are 0.9194–0.9724. Whole-region
    normalized field centroids are not automatically SAA centers.

## Findings that require qualification

- The analysis does not establish multi-month, seasonal, or long-term
  generality.
- Magnetic results show descriptive co-location with low modeled field
  strength; they do not establish causation.
- Cross-satellite comparisons concern footprint location and shape only.
  Absolute proton intensities are not cross-calibrated.
- Orbital sampling, local time, detector degradation, and intercalibration
  can contribute to observed differences.
- `mep_omni_flux_p1`, p2, and p3 are differential omnidirectional proton-flux
  channels at nominal 25, 50, and 100 MeV. They are not interchangeable
  measurements of one absolute quantity.
- NOAA-provided IGRF quantities are modeled, not measured.
- `mep_IFC_on == 1` samples are removed. Values of `-1` are retained and left
  uninterpreted because their meaning is undocumented.
- OMNI negative flux and fit -1 (no fit) are missing channel values; valid zero
  remains in numerical statistics. Log-color displays cannot show zero.
- QC-1 is a post-hoc rule. It can act only where both 10-record neighbourhoods received regular
  fits (32.5% of regional records); it does not screen low-count stretches, gaps or multi-record
  artefacts, and the data are not certified free of other artefacts. Fit 1/2 values are otherwise
  retained.
- Coverage masks gate every grid statistic; missing cells are never interpolated
  or zero-filled. Missing IFC semantics remain unresolved.

## Unsupported claims

The project does not claim:

- a final or true SAA boundary or center;
- biological dose, health risk, or a danger zone;
- discovery of the SAA;
- replacement of professional radiation-belt or transport models;
- magnetic causality from IGRF variables;
- calibrated absolute flux comparisons across satellites or energy channels;
- equivalence between the particle footprint and the magnetic-field minimum.

See [methodology.md](methodology.md) for definitions and
[reproducibility.md](reproducibility.md) for regeneration and validation.
