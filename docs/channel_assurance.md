# Channel assurance — January 2024 NOAA-19

Status: implemented and run on the reconciled baseline. **CONDITIONAL RESAMPLING STABILITY**, not a calibrated physical-position confidence interval. Mean remains primary; median is a deterministic robustness comparison.

## Frozen protocol and execution

`outputs/paper_integrity/20260929_phases1_3/phase3/protocol.json` was written before production replicates. Protocol 1.0 uses monthly p1/p2/p3, 5° mean, top 10%, at least 30 valid samples per cell, NumPy linear percentiles. The region remains latitude -70..20 and longitude -100..20. There are 1,000 paired replicates for each of 1, 3 and 7 consecutive UTC calendar days. PCG64 seed 20260929 is reset per block length. Uniform calendar starts are 0..31-L inclusive, replacement is allowed, blocks never wrap, and concatenation is trimmed to 31 slots. All three channels use identical draws; repeated source days retain multiplicity. Missing source days remain empty slots. All 31 real source days are present in this analysis, though within-day gaps remain.

Daily cell sums/counts accelerate the mean calculation. Nine real-data equivalence checks (three draws × three channels) compare explicitly repeated records, cell counts/means, new percentile masks and area-aware centroids at rtol/atol 1e-12. Each replicate recomputes coverage, percentile selection and centroid. All 3,000 draws / 9,000 channel results and all 9,000 pair results are defined; no redraws. Saved day slots and starts are in `block_draws.json`, with channel-specific eligibility, source-day representation and denominators in `replicates.csv`.

The 1-, 3-, and 7-day runs represent respectively 14–25, 13–27 and 9–29 unique source days across replicates. Eligible-cell ranges are 429–432, 411–432 and 431–432. Marginal quantiles do not form a joint confidence region.

## Observed displacement and paired stability

Observed principal displacements (second channel minus first) are p2−p1 (-0.890798°, +0.672582°), p3−p1 (-1.060123°, +1.684086°), and p3−p2 (-0.169324°, +1.011504°). Distances are 121.096, 210.442 and 106.070 km respectively. The table gives descriptive 2.5%, median, 97.5% quantiles; each denominator is 1,000, with zero undefined pairs.

|Block days|Pair|Latitude degrees|Longitude degrees|Distance km (secondary)|
|---:|---|---|---|---|
|1|p2−p1|-1.333, -0.990, -0.687|0.062, 0.647, 1.271|85.393, 130.489, 181.884|
|1|p3−p1|-1.513, -1.149, -0.774|0.576, 1.429, 2.171|130.682, 197.862, 262.584|
|1|p3−p2|-0.300, -0.121, 0.081|0.280, 0.947, 1.282|31.657, 99.334, 134.432|
|3|p2−p1|-1.335, -0.992, -0.778|0.023, 0.677, 1.299|101.352, 135.720, 182.286|
|3|p3−p1|-1.464, -1.179, -0.869|0.557, 1.454, 2.209|152.614, 198.751, 263.116|
|3|p3−p2|-0.302, -0.162, 0.076|0.284, 0.902, 1.274|32.122, 96.445, 131.972|
|7|p2−p1|-1.243, -0.958, -0.736|0.191, 0.618, 1.152|98.432, 123.666, 169.324|
|7|p3−p1|-1.306, -1.089, -0.816|0.800, 1.454, 2.065|151.634, 193.268, 248.681|
|7|p3−p2|-0.290, -0.162, 0.035|0.311, 0.971, 1.070|34.236, 101.627, 111.437|

The p2−p1 and p3−p1 latitude/longitude marginal ranges retain their observed signs at all three block lengths. The p3−p2 latitude ranges cross zero. Distribution widths and medians vary with block length; no length was selected for a preferred conclusion. Positive distance quantiles alone establish neither statistical nor physical significance.

## Dependence, stationarity and boundaries

Daily regional-mean lag-one correlations are about 0.132, 0.138 and 0.166 for p1/p2/p3 (full 1/3/7-day diagnostics saved). First-half vs second-half p1 regional means are 3.487 vs 3.273 in flux units. These diagnostics do not prove stationarity or quantify effective independent information. Thirty-one days are insufficient to calibrate a long-run sampling distribution. Fixed overlapping blocks retain dependence within each draw, destroy it at joins, and underrepresent boundary days for L>1. Seven-day blocks have only 25 possible starts and require five draws, the final one trimmed to three days. Repeated replicates do not create new independent observations. The nonlinear coverage/percentile centroid and shared channel fitting further limit interpretation.

[Künsch (1989)](https://doi.org/10.1214/aos/1176347265) develops resampling for stationary dependent observations. [Synowiecki (2007)](https://arxiv.org/abs/0711.4493) gives additional conditions for specific periodic/nonstationary structures and statistics. Neither reference establishes calibrated confidence for this 31-day nonlinear footprint statistic. Accordingly this package makes a conditional stability statement only.

## Common-support morphology

The coverage-passed intersection is 432 cells at 5° (108.9594 million km²) and 2,685 at 2° (108.2854 million km²). No additional cells or area are excluded by requiring all three channels. The 2° grid already excludes 15 of 2,700 nominal cells under the original monthly coverage rule. Thus original-support and common-support percentile footprints are identical here; the changes below arise from removing percentile masks, not from changing region or support.

For finite nonnegative flux F and spherical cell area A, p[c,i]=F[c,i]A[i]/ΣF[c,j]A[j]; overlap is Σmin(p[c,i],p[d,i]). Areas are km², flux is #/(cm² s sr MeV); p and overlap are dimensionless. Multiplying any channel by an independent positive scalar leaves p unchanged. Zero contributes zero; missing is excluded from common support, never zero-filled. Negative values and empty/zero-mass normalizations fail explicitly. Whole-region coordinate averages of p are field summaries, not automatically SAA centers, probability or dose distributions.

|Grid|Statistic|Pair|Continuous overlap|Continuous distance km|Percentile distance km|
|---:|---|---|---:|---:|---:|
|5°|mean_flux|p1/p2|0.947180|131.008|121.096|
|5°|mean_flux|p1/p3|0.932509|143.191|210.442|
|5°|mean_flux|p2/p3|0.972383|41.965|106.070|
|5°|median_flux|p1/p2|0.945123|134.151|121.797|
|5°|median_flux|p1/p3|0.930754|140.304|207.616|
|5°|median_flux|p2/p3|0.969489|38.689|103.332|
|2°|mean_flux|p1/p2|0.943709|131.505|136.303|
|2°|mean_flux|p1/p3|0.929218|143.019|211.675|
|2°|mean_flux|p2/p3|0.969277|41.468|84.480|
|2°|median_flux|p1/p2|0.935966|146.473|140.415|
|2°|median_flux|p1/p3|0.919383|154.864|209.406|
|2°|median_flux|p2/p3|0.952692|40.154|83.145|

Overlap remains high while centroids differ; agreement of normalized shapes does not imply absolute flux equivalence. The continuous p3−p2 latitude displacement even changes sign compared with the thresholded footprint. The choice of summary is scientifically material. Complete cell-normalization, centroid, support and pair tables and two explanatory figures are in the Phase 3 evidence directory. These assurance results introduce no explorer configurations.
