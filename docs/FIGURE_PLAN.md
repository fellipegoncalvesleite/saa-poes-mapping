# Figure Plan — core figures for the paper (CP6A)

Only the strongest figures are selected. All file paths are git-ignored but regenerable from the
executed notebooks. Every caption must keep the exploratory / descriptive framing.

Legend: **M** = main paper, **S** = supplement.

---

## F1 — Monthly footprint reference (M)
- Source: CP5A (built on CP4A grids). Path: `outputs/figures/cp5a_particle_footprint_geographic_reference.png`
  (alt: `outputs/figures/cp4a_noaa19_2024-01_mean_flux_5deg.png`).
- Why it matters: orients the reader — the candidate high-flux sector + top10/top5 selected cells.
- Caption draft: "Exploratory monthly mean omnidirectional proton flux (NOAA-19, Jan 2024, ~25 MeV,
  5° coverage-masked) with top-10%/top-5% threshold-defined footprints (× = flux-weighted centroid).
  Not a final SAA boundary."
- Supports: existence of a persistent candidate high-flux sector (Claim A1).
- Must NOT claim: a definitive boundary/center.

## F2 — Threshold overlay (M)
- Source: CP4B. Path: `outputs/figures/cp4b_threshold_overlay_5deg_mean.png`.
- Why: shows nested footprints shrinking/moving as the threshold tightens.
- Caption draft: "Threshold-defined footprints (top 20→1%) on the coverage-masked 5° mean grid;
  centers and areas are method-dependent."
- Supports: threshold method-dependence (Claim A2).
- Must NOT claim: that any one threshold is 'the' SAA.

## F3 — Centroid shift vs threshold (M)
- Source: CP4B. Path: `outputs/figures/cp4b_centroid_shift_by_threshold.png`.
- Why: quantifies the ~386 km centroid travel and area ~17.7× change.
- Caption draft: "Flux-weighted centroid path as the flux threshold tightens (labels = top-X%);
  ~386 km total shift (5° mean). Method-dependent, exploratory."
- Supports: A2. Must NOT claim: physical motion of the SAA.

## F4 — Time-window stabilization (M)
- Source: CP4D. Path: `outputs/figures/cp4d_centroid_by_time_window_top10.png`
  (supplement: `cp4d_sample_count_5deg_time_windows.png`).
- Why: shows the day→7-day jump then stabilization (~288 km day→month; ~118 km weekly).
- Caption draft: "Flux-weighted centroid by aggregation window (top10, 5° mean); one-day maps are
  coverage-limited, stabilizing by ~7 days."
- Supports: A4. Must NOT claim: a one-day footprint as final.

## F5 — Multi-satellite centroid comparison (M)
- Source: CP4F. Path: `outputs/figures/cp4f_multisatellite_centroid_comparison_top10_top5.png`
  (supplement: `cp4f_pairwise_centroid_distance_top10_5deg_mean.png`).
- Why: footprint location agrees across 5 satellites (~272 km), NOAA-15 outlier; < threshold effect.
- Caption draft: "Flux-weighted footprint centroids across five POES/MetOp satellites (top10/top5,
  5° mean); broad location agreement (calibration-limited; absolute flux not compared)."
- Supports: A5, A6. Must NOT claim: absolute-intensity satellite comparison.

## F6 — Magnetic-coordinate framing (M)
- Source: CP5B. Path: `outputs/figures/cp5b_inside_outside_Btot_sat.png`
  (alt: `cp5b_flux_profile_by_Btot_sat.png`).
- Why: inside-footprint samples sit in a low, narrow `Btot_sat` band vs the regional background.
- Caption draft: "Descriptive inside-vs-outside footprint distribution of IGRF total field `Btot_sat`
  (top10, 5° mean); the footprint concentrates at low field strength. Co-location, not causation."
- Supports: A7, A8. Must NOT claim: causality or footprint = field minimum.

---

## Supplement (S)
- S1 channel sensitivity: `cp4c_channel_centroid_comparison.png` (Claim A3).
- S2 channel maps p1/p2/p3: `cp4c_noaa19_2024-01_{p1,p2,p3}_mean_flux_5deg.png`.
- S3 time-window sample-count panels: `cp4d_sample_count_{5deg,2deg}_time_windows.png`.
- S4 multi-satellite per-sat maps + overlays: `cp4f_{sat}_mean_flux_5deg.png`,
  `cp4f_multisatellite_top10_5deg_mean_overlay.png`.
- S5 Btot–L diagnostic: `cp5b_flux_Btot_vs_L_IGRF.png`, `cp5b_high_flux_footprint_Btot_vs_L_IGRF.png`.
- S6 flux-vs-L / flux-vs-MLT profiles: `cp5b_flux_profile_by_{L_IGRF,MLT}.png` (shows MLT non-discrimination).

## Excluded from the paper
- Debug viewer screenshots; redundant median-vs-mean duplicates; 2° duplicates where the 5°
  figure carries the message; per-satellite sample-count maps (kept only as data-quality backup).
