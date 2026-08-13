# Claim Audit — SAA POES/MetOp Method-Sensitivity Study (as of CP5C extension after CP6A)

Scope note: this project is a **methodological reproducibility and sensitivity study** of how a
*particle-defined candidate high-flux footprint* behaves under analysis choices, using public
NOAA/NCEI POES/MetOp SEM-2 MEPED data (January 2024). It is **not** a discovery study and **not** a
radiation-hazard product. Every claim below is bounded by that scope.

---

## A. Claims supported by current evidence (cautious wording)

These follow directly from accepted, validated outputs (CP4B–CP5C) and may be stated, with the
hedging shown:

1. **A persistent candidate high-flux sector exists over the South America / South Atlantic region**
   in the January-2024 NOAA-19 `mep_omni_flux_p1` (~25 MeV omnidirectional proton) data — an
   *exploratory, threshold-defined footprint*, not a boundary. (CP3, CP4A)
2. **The estimated footprint center and area are strongly method-dependent on the flux threshold:**
   the flux-weighted centroid shifts by ~**386 km** from top-20% to top-1% and the selected area
   changes by ~**17.7×** (5° mean). (CP4B)
3. **The footprint location is broadly consistent across proton channels** p1/p2/p3 (25/50/100 MeV):
   max pairwise centroid differences ~**100–300 km**; absolute flux is *not* compared across channels.
   (CP4C)
4. **One-day maps are coverage-limited; the footprint stabilizes with aggregation:** day→month centroid
   drift ~**288 km** (most of it in the day→7-day step), while disjoint weekly windows agree to within
   ~**118 km**. (CP4D)
5. **The footprint location is broadly consistent across five satellites** (noaa15/18/19, metop01/03):
   max pairwise centroid spread ~**272 km** (top10, 5° mean), with NOAA-18≈NOAA-19 (~13 km). This
   inter-satellite spread is **smaller than the within-satellite threshold effect** (~386 km). (CP4F)
6. **NOAA-15 is a footprint-location outlier** (~217–272 km from the others) with anomalously high
   *uncalibrated* peak flux — consistent with it being the oldest platform; reported descriptively,
   not as physical truth. (CP4F)
7. **The particle-defined footprint occupies a low, narrow IGRF field-strength band across the five
   satellites:** in the principal top10, 5° mean case, **100%** of each satellite's footprint samples
   fall below its own regional `Btot_sat` q25, and 90% are contained within the lowest **11.7–12.1%**
   of its regional `Btot_sat` distribution. (CP5C; within-satellite ranks only)
8. **The predeclared CP5C rubric classifies multi-satellite magnetic generality as `CONSISTENT`:**
   5/5 satellites satisfy all low-Btot criteria and 5/5 satisfy Btot-dominance. `Btot_sat`
   separation is **+1.573 to +1.596**, versus `L_IGRF` **+0.387 to +0.429**. MLT separation is near
   zero for four satellites but **+0.920 for NOAA-15**; Btot still dominates there. These cutoffs are
   operational criteria for CP5C, not physical thresholds defining the SAA. (CP5C)

---

## B. Claims that are plausible but NOT yet proven (require more work)

State these only as hypotheses / future work, never as findings:

1. **Multi-month / seasonal generality** — all quantitative results are January 2024 only; the
   footprint's stability across months/seasons is untested.
2. **A causal relation between low geomagnetic field strength and the proton-flux footprint** — CP5B
   shows *descriptive co-location* with low `Btot_sat`, not causation.
3. **Long-term SAA drift / secular change** — not addressed; would need multi-year data.
4. **A robust, cross-calibrated absolute-intensity comparison across satellites** — only footprint
   *location/shape* is compared; absolute flux is explicitly not cross-calibrated.
5. **That the low-`Btot_sat` concentration is physical rather than partly an orbital/local-time
   sampling effect** — not separated yet.
6. **Foot-of-field-line vs satellite-coordinate framing equivalence** — only satellite-altitude
   magnetic coordinates were used in the pilot.

---

## C. Claims explicitly FORBIDDEN (must never appear in any output)

These are out of scope and unsupported; do not state them in any form, hedged or not:

- A **final or definitive SAA boundary**.
- A **true SAA center** (only method-dependent candidate centroids exist).
- Any **biological dose** estimate.
- Any **health risk** statement.
- Any **"danger zone"** / spacecraft-hazard claim.
- **Discovery** of the SAA (it is long known; this is a methods study).
- **Replacing or competing with professional radiation-belt / radiation-transport models** (AP-8/AP-9,
  IRBEM-based products, etc.).
- **Physical causality inferred from IGRF variables alone** (`Btot_sat`/`L_IGRF` are model quantities;
  co-location ≠ cause).
- **Absolute proton-flux comparison across satellites** without cross-calibration.
- **Absolute flux comparison across energy channels** as if the same quantity.
- Any claim that the **particle footprint equals the magnetic-field minimum**.

---

## Standing data caveats (carry into every write-up)

- `mep_omni_flux_p1` is a **differential** omnidirectional proton flux at ~25 MeV
  (`#/cm2-s-str-MeV`), confirmed from NetCDF metadata (CP1's integral-channel guess was corrected in
  CP2).
- `mep_IFC_on == 1` rows are dropped; `mep_IFC_on == -1` is **retained and uninterpreted** (its
  meaning is undocumented; do not resolve by guessing).
- `L_IGRF == -1` is a documented **invalid sentinel**, excluded from L-based analysis (3,914 rows).
- IGRF/magnetic variables are **model** quantities provided by NOAA, not measurements.
- Coverage masks (≥30 samples/cell) gate every grid statistic; one-day coverage is sparse.
