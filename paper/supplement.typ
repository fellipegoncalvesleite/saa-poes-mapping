#import "template.typ": paper, val, csvtable

#show: paper.with(
  title: "Supplement to: Analysis choices and orbital sampling shape a particle-defined South Atlantic Anomaly footprint",
  subtitle: "Extended methods, full configuration results, data accounting, quality-rule evidence and descriptive magnetic material",
  author: "Fellipe Gonçalves Leite",
  short-title: "Supplement",
)
#set heading(numbering: (..n) => "S" + n.pos().map(str).join("."))
#let sq = sym.degree

This supplement documents every result family in full. Machine-readable versions of all tables are in `paper/tables/`. Bulky rows are linked, not printed: bootstrap draws (`outputs/channel_assurance/block_draws.json`, `replicates.csv`, `paired_replicates.csv`), selected cells (`outputs/tables/cp4d_temporal_support_selected_cells.csv`) and distinct-day counts (`outputs/tables/cp4d_temporal_support_distinct_days.csv`). Every number printed in the text is generated from the claims register `paper/generated/claims_register.json`, which lists, for each claim, its configuration, input paths with SHA-256, formula, denominator, rounding and caveat. Rounded values are for display; comparisons use unrounded values.

= Inputs and product provenance

*Files.* 155 daily NetCDF files (five spacecraft × 31 days of January 2024) from the NCEI archive path `…/access/l1b/v01r00/2024/<satellite>/poes_<token>_202401DD_proc.nc`. `paper/tables/S1_raw_manifest.csv` lists name, size, SHA-256 and URL for each file, and the reproduction verifies every hash against the recorded Phase 1 manifest before computing. Raw files are not redistributed with the package.

*Product level and units.* The archive directory is `l1b`, but every file declares `processing_level = "Level 2, calibrated fluxes"`. The NOAA manual describes the processing as turning level-1B sensor data into physical-unit level-2 products @green2013manual. Variable metadata define `mep_omni_flux_p1..p3` as "MEPED proton differential flux at 25/50/100 MeV omnidirection telescope" in `#/cm2-s-str-MeV`. The manual's Table A-1 (p. 17) prints `#/cm2-s-str`. The OMNI algorithm description @machol2012atbd (§3.1 p. 10; Table 4 pp. 24–25) defines the outputs as fitted differential fluxes at 25, 50 and 100 MeV in ions/(cm² s sr MeV). We treat the manual's label as an incomplete unit string and report per-MeV differential flux. This reconciles documentation; it does not define a new product. The OMNI fluxes are power-law fits in energy to count rates from four overlapping omnidirectional channels (16–35, 35–250, 70–250, 140–250 MeV), so p1–p3 share inputs and a spectral model.

*Fit and IFC flags.* ATBD Table 5 (p. 25): fit −1 = no fit performed; 0 = four-region power-law fit; 1 = one-point fit with a single slope set to a default; 2 = two-point single-slope fit. `mep_IFC_on` is documented as 0 (off) / 1 (on); the value −1 that dominates the files is undocumented.

*Provider caveat.* The file title states that the data have known contamination problems and advises consulting the provider for usage. No specific contamination correction is applied here.

*Quality-evidence input.* One level-1a companion file from the same archive, `…/access/l1a/v01r00/2024/noaa15/poes_n15_20240119_raw.nc` (SHA-256 `59cd88dd551ac2a18036137124000e1e91c74dd26e29233a57821a062a95626f`, recorded in `paper/inputs/qc_evidence_hashes.json`), holds the OMNI count rates of the day of the excluded record. Its record times are identical to those of the processed file. It is read only to document that record (S7) and never enters a map.

*Historical bytes.* The 31 NOAA-19 files were cached with recorded hashes before this analysis was finalized. The other 124 were retrieved again. Regional tables rebuilt from them reproduce the saved values exactly, which is value lineage, not recovery of unrecorded historical bytes.

= Quality handling and record accounting

Per spacecraft (region lat −70#sq…20#sq, lon −100#sq…20#sq): regional records before the IFC rule, records dropped with `mep_IFC_on = 1`, records retained with the undocumented −1, p1 values set missing by the validity rule (negative or fit = −1), p1 values excluded by QC-1, and records remaining. The principal footprint sample counts and descriptive field-strength columns belong to S8.

#csvtable("tables/S2_S8_accounting_magnetic.csv",
  keep: ("satellite", "regional_rows_before_ifc", "ifc_on_dropped", "ifc_minus1_retained", "invalid_channel_dropped", "qc_excluded_dropped", "regional_rows_after_quality", "l_igrf_rows_invalid"),
  header-map: ("satellite": "satellite", "regional_rows_before_ifc": "regional", "ifc_on_dropped": "IFC=1 dropped", "ifc_minus1_retained": "IFC=−1 kept", "invalid_channel_dropped": "p1 invalid", "qc_excluded_dropped": "QC-1", "regional_rows_after_quality": "analysed", "l_igrf_rows_invalid": "L invalid"))

The validity rule sets a value missing only when it is negative (below the documented minimum of 0) or its fit flag is −1. Valid zeros remain in means and medians, and log colour scales cannot display them. No upper cutoff is imposed. Missing flags remain missing; a synthetic regression test covers fill, scale and separate-dimension alignment in the loader. QC-1 (main text Sect. 2.2; evidence in S7) is applied to each daily file in native record order, before region selection and gridding, so neighbours outside the region count as neighbours. Its exclusions are counted separately from the validity rule; the record-level ledger, with the reason for each exclusion, is `outputs/tables/qc1_omni_exclusions.csv`.

= Estimands, configuration universe and threshold family

*Percentile.* $c_q$ is NumPy's default linear-interpolation percentile over the eligible cells' statistic. Selection is $F_i >= c_q$, so ties at the cutoff are all selected.

*Area.* $A_i = R^2 Delta lambda (sin phi_i^+ - sin phi_i^-)$, with $R = 6371$ km and $Delta lambda$ in radians. An independent check uses $2 R^2 Delta lambda cos phi_i sin(Delta phi \/ 2)$, which is algebraically identical, and agrees to $10^(-12)$ relative.

*Centroid.* Coordinate moment with weights $F_i A_i$ (main-text Eq. 2). Longitude is averaged directly because the region spans −100#sq…20#sq. Distances are haversine and are checked against a vector-angle formula.

*Configuration universe.* The viewer payload lists #val("cfg_total") configurations. Grouping by grid content, statistic and threshold gives #val("cfg_distinct") distinct states. The NOAA-19 monthly p1 map appears as the threshold family, the p1 member of the channel family, the month member of the time family and the NOAA-19 member of the satellite family (20 states × 4 listings), and `week1` duplicates the cumulative 1–7 January window (20 × 2). `paper/generated/configuration_aliases.json` lists the alias groups. Configuration counts are therefore not counts of independent experiments.

*Threshold family, full results* (NOAA-19 p1, January; flux cutoff and peak in cm#super[−2] s#super[−1] sr#super[−1] MeV#super[−1]; area in 10#super[6] km²):

#csvtable("tables/S3_threshold.csv")

Successive 5#sq mean centroid steps are #val("thr_step_top20_top10"), #val("thr_step_top10_top5"), #val("thr_step_top5_top2") and #val("thr_step_top2_top1") km. The selected-cell ratios top 20% / top 1% are #val("thr_count_ratio_5_mean") (5#sq mean), #val("thr_count_ratio_5_median") (5#sq median), #val("thr_count_ratio_2_mean") (2#sq mean) and #val("thr_count_ratio_2_median") (2#sq median); the nominal ratio is 20.

= Channel family

Footprint results for p1, p2 and p3 across all 20 settings (channel absolute values differ by construction and are not compared):

#csvtable("tables/S4_channel.csv")

Pairwise morphology for the four grid/statistic settings. Modes: `original_percentile` (each channel's own eligible support), `common_percentile` (top 10% recomputed on the three-channel common support; identical here because the supports coincide), and `common_continuous` (whole-field normalized moments; "overlap" is Eq. 4 of the main text; "jaccard" is the area-weighted Jaccard of the selected sets, trivially 1 for the whole field). Signed differences are second channel minus first:

#csvtable("tables/S4b_channel_morphology.csv")

= Paired calendar-block resampling

*Protocol (frozen before production replicates; `outputs/channel_assurance/protocol.json`, version 1.0).* Monthly p1/p2/p3, 5#sq mean, top 10%, ≥ 30 samples per cell, NumPy linear percentile. For each block length $L in {1, 3, 7}$, 1,000 replicates. Starts are uniform on $0..31-L$, drawn with replacement, without wrap; draws are concatenated and trimmed to 31 day-slots. The generator is PCG64 with seed 20260929, reset per block length. The same day draws are used for all three channels, and repeated days keep their multiplicity. Missing days would keep empty slots; none occurred, although within-day gaps remain. Each replicate recomputes coverage, percentile, footprint and centroid from daily cell sums and counts. Nine real-data checks confirm that the sufficient-statistic path reproduces explicitly repeated records (cell means, masks, centroids) to $10^(-12)$. All 3,000 draws and 9,000 channel-level results were defined; none was redrawn.

*Quantiles* (pandas linear; signed second − first; degrees or km; denominator 1,000 defined replicates each):

#csvtable("tables/S5_paired_quantiles.csv", keep: ("block_length", "pair", "metric", "defined", "q025", "q50", "q975"))

*Dependence diagnostics* (daily regional-mean p1–p3; descriptive only):

#csvtable("tables/S5b_dependence.csv")

*Caveats.* Thirty-one days cannot establish stationarity or a long-run dependence structure @kunsch1989block @synowiecki2007mbb. Seven-day blocks have only 25 possible starts and need five draws, the last trimmed to three days. Dates near the month's ends are selected less often when $L > 1$. Joins between blocks break dependence, and 1-day blocks remove cross-day dependence altogether. The thresholded centroid is nonlinear and coverage-dependent. The channels are fitted outputs of shared counts. The quantiles are marginal (they do not form a joint region), are conditional on the month observed, and are not calibrated confidence intervals for a physical position. A positive distance quantile is not significance.

= Temporal coverage versus conditional morphology

*Definitions* (main text §2.6). For each window $W$ and the January reference $M$ at the same grid, statistic and threshold: $C_W$, $C_M$ are the eligible cells with a finite statistic; $F_W$, $F_M$ the original footprints; "J_end" $= J(F_W, F_M)$ (area-weighted); "O_M" $= A(F_M inter C_W) \/ A(F_M)$; "S" $= |C_W inter C_M|$; "J_shared" and "D_shared" compare footprints recomputed with each map's own percentile over $C_W inter C_M$; "R" is the selected-area ratio window/month. Undefined cases would be reported with reasons; there were #val("tw_undefined") among #val("tw_rows") rows. Recomputed original footprints match the stored time-window table exactly (cell counts, areas, cutoffs, centroid distances), and three rows were recomputed independently with hand-coded percentiles, zone-formula areas and vector-angle distances. `wk 1*` is the same date range as `7 d`, and its rows are identical.

*Window coverage* (eligible = cells passing the window's sample minimum):

#csvtable("tables/S6b_window_coverage.csv")

*Full diagnostics* (all windows except the reference; 2 grids × 2 statistics × 5 thresholds):

#csvtable("tables/S6_temporal_support.csv", size: 6.6pt)

= Quality rule QC-1 and the excluded NOAA-15 record

*Rule (version 1.0, adopted post hoc).* For each daily file in native order, a record's OMNI values (p1–p3) are set missing when: its fit flag is 1 or 2; its #val("qc_k") preceding and #val("qc_k") following records lie in one contiguous run (every time step positive and ≤ #val("qc_step") s) and all have fit flag 0; and, for at least one channel, every neighbour value is finite and positive and the record's value exceeds #val("qc_ratio") × the median of the preceding ten *and* #val("qc_ratio") × the median of the following ten (strict inequality). Records that cannot be evaluated are kept. Identity is the source SHA-256 and the zero-based native index; numerically equal values elsewhere are unaffected. Code: `src/saa/quality.py`; tests: `tests/test_omni_qc.py` (event exclusion, a real isolated one-point fit that is kept, gradual intense passes, gaps, missing/zero neighbours, duplicate and backward timestamps, positional identity, strict threshold, deterministic replay).

*Population envelopes* (all 155 files; "regular": two-sided ratio min(left, right) of fit-0 records whose 20 neighbours are all fit 0; "fallback": the same for isolated fit-1/2 records; "excluded ratio": smallest ratio among excluded values):

#csvtable("tables/S7f_qc_population.csv", size: 6.6pt)

*Parameter perturbations* (one at a time around the adopted rule, plus joint ratio × neighbour changes; "same set" compares the full list of excluded records, not only its size):

#csvtable("tables/S7g_qc_perturbation.csv", size: 6.6pt)

The excluded set is unchanged in #val("qc_pert_same") of #val("qc_pert_n") variants. It grows when the ratio falls to 15× or 10× (#val("qc_ratio_15_n") and #val("qc_ratio_10_n") records). The three records added at 15× are isolated one-point default-slope fits at low flux on the edge of the SAA, beside lower regular-fit neighbours, and their co-located directional channels are not zero: departures of the kind the documented fallback produces elsewhere, which the ratio is set to leave alone. It also grows to #val("qc_nonb_n") records (#val("qc_nonb_region") in the study region) when the regular-fit neighbour condition is dropped; these are mostly low-flux fallback values beside near-zero neighbours, the cases that condition is designed to leave alone.

*Excluded record.* Zero-based native index #val("ev_index") of the NOAA-15 file for 19 January, #val("ev_utc") (`poes_n15_20240119_proc.nc`, SHA-256 #raw(val("ev_sha"))). Stored values (float32): p1 = #val("ev_p1"), p2 = #val("ev_p2"), p3 = #val("ev_p3"). Two-sided p1 ratios: #val("ev_p1_ratio_left") (preceding) and #val("ev_p1_ratio_right") (following); p3 ratios #val("ev_p3_ratio_left") and #val("ev_p3_ratio_right"). Its p1/p2 and p2/p3 ratios are #val("ev_spectral_ratio") and #val("ev_spectral_ratio_p2p3"), equal to $2^(2.9) = $ #val("gamma_default_ratio"): the three channels are one value extended with the default slope. It is the only record QC-1 excludes in the 155 files; it is also one of the candidates of the historical triage described at the end of this section.

*Native neighbourhood* (±10 records; flux in cm#super[−2] s#super[−1] sr#super[−1] MeV#super[−1]; γ1 is the fitted slope at p1; P6 0#sq/90#sq are the co-located directional MEPED proton fluxes, cm#super[−2] s#super[−1] sr#super[−1]):

#csvtable("tables/S7a_event_neighbours.csv", size: 6.6pt)

*Level-1a count rates* (±5 records; counts s#super[−1]; ">16 MeV" … ">140 MeV" are the OMNI channels P6–P9, and P8/P9 share a telemetry word and are read out on alternate records, shown as "–"; P6 0#sq/90#sq are directional; "bias V" is the OMNI bias-voltage housekeeping field):

#csvtable("tables/S7e_event_counts.csv", size: 6.6pt)

In this record the >35 MeV rate is #val("rc_p7") s#super[−1] while the >16 MeV rate is #val("rc_p6") s#super[−1], a ratio of #val("rc_p7p6"). Elsewhere that day the >35/>16 MeV ratio never exceeds #val("rc_p7p6_other"), and the second-highest >35 MeV rate is #val("rc_p7_second") s#super[−1]. In this record #val("rc_dir_proton_zero") of the #val("rc_dir_proton_n") directional MEPED proton count channels and #val("rc_dir_electron_zero") of the #val("rc_dir_electron_n") electron count channels read exactly zero; #val("rc_zero_n") level-1a variables in all are zero here and non-zero in all 20 neighbours. The bias-voltage field reads a value that occurs nowhere else that day for #val("rc_bias_span") records starting one record before the event; we report this coincidence without interpreting it. None of this identifies the cause.

*Cell and footprint influence.* The record lies in 5#sq cell (−12.5#sq, −27.5#sq) and 2#sq cell (−13#sq, −29#sq). Per scenario and setting ("QC-1 primary" excludes it; "unfiltered" keeps it):

#csvtable("tables/S7c_event_cell.csv", size: 6.8pt)

Between the two analyses, top-10%/5#sq footprint membership differs for #val("ev_members_top10_5") NOAA-15 regional records (`outputs/qc_sensitivity/cp5_changed_memberships.csv`), and #val("fp_settings_changed") of the 100 satellite settings change their selected cells, all of them NOAA-15. Rule-based exclusion reproduces the earlier exact-record omission exactly: every pairwise distance and every event-cell value of the QC-1 scenario equals the recorded omission evidence, and every unfiltered value equals the recorded as-is evidence (checked when the claims register is built).

*Five-satellite footprints by scenario* (area 10#super[6] km²):

#csvtable("tables/S7_satellite.csv", size: 6.6pt)

*Maximum pairwise centroid distance* per scenario, grid, statistic and threshold:

#csvtable("tables/S7b_max_pairwise.csv", size: 6.8pt)

*Historical triage census.* Before QC-1 existed, a frozen two-sided screen flagged a positive value exceeding 100 times the median of each of its ten preceding and ten following native records, regardless of fit flags, where all 20 neighbours were finite and positive and no gap exceeded three cadences. Run with the original extractor over #val("census_records") native records (#val("census_values") channel values) and replayed exactly here, it flagged #val("census_candidates") values at #val("census_candidate_records") records, with #val("census_eval_min")–#val("census_eval_max")% evaluable per satellite/channel. All its candidates carry fit flag 1 or 2, and most are low-flux fallback values beside near-zero neighbours, outside the SAA. It removed nothing; QC-1 adds the regular-fit neighbour condition that separates those cases.

#csvtable("tables/S7d_triage_census.csv")

= Descriptive magnetic context

NOAA-supplied IGRF-based quantities in the files (`Btot_sat`, `L_IGRF`) are model values, used here only to describe where footprint samples lie. The NOAA manual (2013) describes IGRF evaluation during processing @green2013manual; the IGRF generation used for these 2024 files is not stated in the file metadata we inspected. For the principal footprint (5#sq mean, top 10%) of each spacecraft, #val("mag_q25_min")% of footprint samples fall below that spacecraft's regional first quartile of `Btot_sat`, and 90% of footprint samples lie within the lowest #val("mag_cap90_min")–#val("mag_cap90_max")% of its regional `Btot_sat` distribution. The column "separation" is a standardized median difference, $(m_"out" - m_"in") \/ (0.5 ("IQR"_"in" + "IQR"_"out"))$, where $m$ and IQR are the median and interquartile range of `Btot_sat` for regional samples inside and outside the footprint; positive values mean lower field strength inside. It ranges from #val("mag_sep_min") to #val("mag_sep_max").

#csvtable("tables/S2_S8_accounting_magnetic.csv",
  keep: ("satellite", "selected_sample_count", "btot_fraction_below_regional_q25", "btot_regional_fraction_to_capture_90pct", "btot_separation_metric"),
  header-map: ("selected_sample_count": "footprint samples", "btot_fraction_below_regional_q25": "frac < Q1(Btot)", "btot_regional_fraction_to_capture_90pct": "Btot fraction for 90%", "btot_separation_metric": "separation"))

This is co-location with low modelled field strength, consistent with these particle-defined footprints lying in the region of weak field. It is a description of these footprints, not a test of any boundary, and it does not establish causation.

*Retired material.* An earlier combined classification (legacy "v1") counted low-Btot and Btot-dominance supporters separately and compared Btot against a linear magnetic-local-time separation. That MLT summary depends on the clock origin (a 12-hour shift changes a wrapping test case from #val("mlt_probe_wrap_0") to #val("mlt_probe_wrap_12")), and "separate counts" differs from the documented "both criteria" wording. The legacy output and its dominance results are retired: they are kept in the audit archive for provenance and are not current findings. No replacement circular statistic is claimed comparable to Btot.

= Reproduction and verification summary

The package's `REPRODUCE.md` gives the single entry command (`python scripts/reproduce_paper.py`), the environment files and the order of steps: input hash verification; regeneration of processed tables, grids and all sensitivity families from raw files (QC-1 applied); the QC-1 ledger, population envelopes, perturbation study and unfiltered sensitivity; the level-1a count-rate evidence (hash-checked); the exact-record omission replayed on unfiltered data as provenance; the Phase 3 protocol replay; the Phase 4 temporal diagnostics; the audit census replay; the claims register; figures; the viewer payload (exported twice and compared byte for byte); tests and validators; and these documents. The final verification report lists exact commands and pass/fail counts. Author review of the critical code and of this text is pending.

#bibliography("refs.bib", title: "References", style: "american-geophysical-union")
