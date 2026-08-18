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
   top 20% to top 1%, the area-aware flux-weighted centroid shifts about **433 km** and
   selected area changes by about **17.7×** on the 5° mean grid.
3. Footprint locations are broadly consistent across the p1, p2, and p3
   fitted proton outputs: the principal top-10%, 5° mean comparison has a
   maximum pairwise centroid separation of about **210 km**. Absolute flux is not compared across channels.
4. One-day maps are coverage-limited. Day-to-month centroid drift is about
   **289 km**, concentrated mainly between one and seven days; disjoint weekly
   windows agree within about **118 km**.
5. Footprint locations are broadly consistent across NOAA-15, NOAA-18,
   NOAA-19, MetOp-01, and MetOp-03. The maximum top-10%, 5° mean pairwise
   spread is about **284 km**; NOAA-18 and NOAA-19 differ by about **13 km**.
   This spread is smaller than the within-satellite threshold effect.
6. NOAA-15 is a location outlier, about **228–284 km** from the other
   platforms, and has anomalously high uncalibrated peak flux. This is a
   descriptive observation, not a cross-calibrated physical comparison.
7. In the principal top-10%, 5° mean case, **100%** of footprint samples for
   each satellite fall below that satellite's regional `Btot_sat` first
   quartile; 90% are contained within the lowest **11.7–12.1%** of its
   regional `Btot_sat` distribution.
8. The predeclared multi-satellite magnetic-generality rubric returns
   `CONSISTENT`: 5/5 satellites pass both the low-`Btot_sat` and
   `Btot_sat`-dominance criteria. `Btot_sat` separation is **+1.573 to
   +1.596**, compared with `L_IGRF` separation of **+0.387 to +0.429**.
   MLT separation is near zero except for NOAA-15 (**+0.920**), where
   `Btot_sat` still dominates. These are operational study criteria, not
   physical SAA thresholds.

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
- Coverage masks gate every grid statistic; sparse cells and nonpositive
  display values remain missing rather than being interpolated or zero-filled.

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
