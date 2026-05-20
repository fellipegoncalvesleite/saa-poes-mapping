# Mentor / Professor Review Packet — SAA POES/MetOp Method-Sensitivity Study

*Prepared for a physics professor / mentor. The goal is technical feedback on correctness, framing, and
literature — not validation that the project is "impressive".*

## 1. Project summary (one paragraph)
I built a reproducible pipeline that maps a *candidate high-flux footprint* of the South Atlantic
Anomaly (SAA) from public NOAA/NCEI POES/MetOp SEM-2 MEPED energetic-proton data (January 2024), and I
quantified **how much the estimated footprint center, area, and intensity change under different
analysis choices** (flux threshold, proton channel, time window, satellite). I then *descriptively*
related the particle-defined footprint to NOAA-provided IGRF magnetic variables (`Btot_sat`, `L_IGRF`,
`MLT`). The project is deliberately framed as a **methodological reproducibility / sensitivity study**,
not a discovery, and it makes no dose/health/boundary claims.

## 2. Exact research question
*When mapping the SAA from public LEO energetic-particle data, how much do the estimated center, area,
and intensity of the candidate high-flux footprint change under different methodological choices —
proton channel, flux threshold, spatial grid resolution, satellite, and time window — and how can the
footprint be described (not defined) in geomagnetic-coordinate terms?*

## 3. Data used
- NOAA/NCEI POES/MetOp SEM-2 **L1b processed** NetCDF (`v01r00`, `poes_<sat>_<YYYYMMDD>_proc.nc`),
  January 2024, satellites noaa15/18/19 + metop01/03 (all 31/31 days available).
- Primary channel `mep_omni_flux_p1` = differential omnidirectional proton flux at ~25 MeV
  (`#/cm2-s-str-MeV`, confirmed from `long_name`); also p2/p3 (50/100 MeV) for channel sensitivity.
- NOAA-provided IGRF variables (`L_IGRF`, `Btot_sat`, `mag_lat_sat`, `mag_lon_sat`, `MLT`, foot-point
  coordinates). Region lat[-70,20]×lon[-100,20].

## 4. Methods used
Coverage-aware lon/lat gridding (5°/2°, mean & median, ≥30-sample masks, spherical cell area);
percentile threshold footprints (top 20/10/5/2/1%); unweighted and flux-weighted centroids; haversine
distances; one-axis-at-a-time sensitivity (threshold, channel, window, satellite); descriptive
magnetic-coordinate framing (validity rules, binned flux profiles, inside/outside footprint summaries,
low-Btot/low-L concentration metrics). Reproducible env (uv + Python 3.12), per-checkpoint validators.

## 5. Key preliminary results
- Threshold: flux-weighted centroid shifts ~**386 km** (top20→top1, 5° mean); selected area ~**17.7×**.
- Channel: footprint location consistent across p1/p2/p3 (max centroid diff ~**100–300 km**).
- Time window: day→month centroid drift ~**288 km** (mostly day→7-day); weekly windows agree ~**118 km**.
- Satellite: 5-satellite max centroid spread ~**272 km** (top10, 5°), **smaller than the threshold
  effect**; NOAA-18≈NOAA-19 (~13 km); NOAA-15 a location outlier with high *uncalibrated* flux.
- Magnetic: footprint sits at low IGRF field strength (~**100%** of top10/top5 below regional `Btot_sat`
  q25; 90% within lowest ~12%); `Btot_sat` separates the footprint more sharply than `L_IGRF`; `MLT`
  does not discriminate.

## 6. Limitations (self-identified)
Single month; single primary channel; geographic/sub-satellite binning only; no cross-satellite
calibration (absolute intensity not compared); IGRF variables are model quantities; sampling/local-time
effects not fully separated; `mep_IFC_on == -1` retained but uninterpreted.

## 7. Specific questions for the professor (technical)
1. Is **`mep_omni_flux_p1` (~25 MeV omni proton)** an appropriate *first* channel for an SAA footprint
   framing, or would a directional telescope (`mep_pro_tel0/90`) or a different energy be more standard?
2. Are the **magnetic-coordinate variables interpreted cautiously enough**? Specifically, is it
   defensible to use **satellite-altitude** `mag_lat_sat`/`Btot_sat` rather than **foot-of-field-line**
   quantities for this descriptive framing?
3. Is **`Btot_sat` a defensible descriptive framing variable** for "where the footprint is", or is
   `L_IGRF` (or B/B0, or invariant latitude) the more conventional choice?
4. Are we **overstating the relationship** between the particle-defined footprint and the geomagnetic
   field by reporting the low-`Btot_sat` concentration, even with explicit "co-location, not causation"
   language?
5. What **literature** should we cite on (a) SAA mapping methodology, (b) POES/MEPED proton data
   characteristics and known artifacts, and (c) IGRF / magnetic-coordinate conventions (L-shell, MLT,
   AACGM)?
6. Should **`mep_IFC_on == -1`** be handled differently? We currently keep those rows and treat the
   value as undocumented/uninterpreted — is there a known meaning we should apply?
7. Are there **known NOAA/MEPED calibration caveats** (proton contamination, detector degradation,
   inter-satellite calibration, the `mep_omni_flux_flag_fit` quality flag) we must state before any
   cross-satellite or absolute-flux discussion?
8. Is the **coverage-threshold choice (≥30 samples/cell)** and our spherical-area + flux-weighted
   centroid methodology statistically sound for this kind of footprint metric?

## 8. What I am *not* claiming (so feedback can focus)
No final SAA boundary/center, no dose/health/danger, no discovery, no replacement for AP-8/AP-9 or
radiation-transport models, no causal claim from IGRF variables, no absolute cross-satellite flux
comparison. See `docs/CLAIM_AUDIT.md`.
