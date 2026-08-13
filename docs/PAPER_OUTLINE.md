# Paper Outline — Method-Sensitivity & Reproducibility of SAA Mapping from Public POES/MetOp Data

Framing: a **methodological sensitivity and reproducibility** study, *not* a discovery paper. The
contribution is showing, on fully public data, **how much the particle-defined SAA footprint estimate
moves under analysis choices** (threshold, channel, time window, satellite) and how it can be
*descriptively* framed in geomagnetic coordinates.

## 1. Title options
**Primary:**
> *Mapping the South Atlantic Anomaly from Public POES/MetOp Proton Flux Data: A Reproducibility and
> Method-Sensitivity Study*

Alternates:
- *How Much Does the Estimated South Atlantic Anomaly Move? A Method-Sensitivity Analysis of Public
  POES/MetOp MEPED Proton Data*
- *Reproducible, Coverage-Aware Mapping of the South Atlantic Anomaly Footprint from NOAA/EUMETSAT
  Energetic-Proton Measurements*

## 2. Abstract skeleton
- Context: SAA well known; many mapping choices; public LEO particle data underused for *reproducibility*.
- Gap: how sensitive is the estimated footprint (center/area/intensity) to method choices?
- Data: NOAA/NCEI POES/MetOp SEM-2 MEPED L1b, January 2024, 5 satellites, omni proton p1 (~25 MeV).
- Methods: coverage-aware lon/lat gridding; percentile threshold footprints; spherical-area & centroid
  metrics; sensitivity across threshold/channel/window/satellite; descriptive IGRF-coordinate framing;
  predeclared five-satellite magnetic-generality rubric with an independent NOAA-19 reproduction gate.
- Key numbers: threshold centroid shift ~386 km / area ~17.7×; channel ~100–300 km; day→month ~288 km
  (weekly ~118 km); 5-satellite top10 5° mean spread ~272 km; CP5C `CONSISTENT` (5/5 low-Btot and
  5/5 Btot-dominance).
- Statement: footprint *location* is robust across satellites/windows but center/area are
  method-dependent; everything exploratory, no boundary/dose/health claims.

## 3. Introduction
- What the SAA is (brief, cited); why LEO energetic-particle data sees it.
- Prior SAA mapping approaches (model-based AP-8/AP-9; in-situ; POES/MEPED studies) — cite via mentor.
- Motivation: reproducibility + explicit method-sensitivity on public data.
- Research question (verbatim, below) and contribution list.

## 4. Data
- Archive + product (NCEI L1b v01r00 `_proc.nc`), access URL pattern, January 2024.
- Satellites: noaa15/18/19, metop01/03 (availability audited, all 31/31).
- Channel `mep_omni_flux_p1`: differential omni proton flux ~25 MeV, `#/cm2-s-str-MeV` (metadata-confirmed).
- Quality flags: `mep_omni_flux_flag_fit`; `mep_IFC_on` handling (`==1` dropped, `==-1` uninterpreted).
- NOAA-provided IGRF variables (audit of 29; `L_IGRF`, `Btot_sat`, `mag_*_sat`, `MLT`, `*_foot`).
- Region lat[-70,20]×lon[-100,20]; longitude [0,360)→[-180,180).

## 5. Methods
- Loader / record-aligned extraction (no `to_dataframe`); reproducible env (uv, Python 3.12).
- Monthly coverage-aware gridding (5°/2°, mean/median, sample-count masks ≥30); spherical cell area.
- Threshold footprints (top 20/10/5/2/1%); unweighted & flux-weighted centroids; haversine distances.
- Sensitivity protocol across threshold, channel, time window, satellite (fixed-everything-else design).
- Descriptive magnetic-coordinate framing: validity rules, binned flux profiles, inside/outside
  footprint summaries, low-Btot/low-L concentration metrics.
- CP5C generality decision: fixed principal top10, 5° mean case; within-satellite ranks only;
  operational rubric evaluated before narrative interpretation. Its cutoffs are not physical SAA
  thresholds. NOAA-19 discrete references must match exactly and floats use fixed `rtol=1e-9`,
  `atol=1e-12`.
- Validation harness (per-checkpoint scripts; source and artifact consistency checks).

## 6. Results
6.1 Footprint reference (monthly mean map). 6.2 Threshold sensitivity (~386 km / ~17.7×).
6.3 Channel sensitivity (~100–300 km). 6.4 Temporal stability (day→month ~288 km; weekly ~118 km).
6.5 Inter-satellite consistency (~272 km; < threshold effect; NOAA-15 outlier).
6.6 Magnetic-coordinate framing and five-satellite generality: `CONSISTENT` by the predeclared rubric;
all 5 satellites pass low-Btot and Btot-dominance. Report every satellite's raw metrics; note that MLT
is near zero for four satellites but separates on NOAA-15, while remaining weaker than Btot.

## 7. Discussion
- Footprint *location* is robust to satellite/window; *center/area* are method artifacts → reporting
  must state the method.
- Descriptive co-location with low IGRF field strength; explicitly not causal.
- Implications for reproducible "where is the SAA" statements from public data.

## 8. Limitations
- Single month (Jan 2024); single primary channel; geographic (sub-satellite) binning only.
- No cross-satellite calibration; absolute intensity not compared.
- IGRF variables are model quantities; sampling/local-time effects not fully separated.
- `mep_IFC_on == -1` uninterpreted; coverage-threshold choice affects sparse windows.

## 9. Reproducibility statement
- Public data + open code; deterministic notebooks in order; per-checkpoint validators; provenance
  with checksums; git-ignored regenerable payloads. (Point to `REPRODUCIBILITY_CHECKLIST.md`.)

## 10. Future work
- Multi-month / seasonal extension; foot-point vs satellite
  coordinates; circular `mag_lon_sat` statistics; separating sampling from physical structure;
  comparison against published SAA descriptions (not as validation of a "true" boundary).

---

### Research question (verbatim)
*When mapping the SAA from public low-Earth-orbit energetic-particle data, how much do the estimated
center, area, and intensity of the candidate high-flux footprint change under different methodological
choices — proton channel, flux threshold, spatial grid resolution, satellite, and time window — and
how can the footprint be described (not defined) in geomagnetic-coordinate terms?*
