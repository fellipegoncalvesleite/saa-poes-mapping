# Cell Scale and Controlled Comparison Design

## Objective

Make the map's geographic scale explicit and let readers compare two scientifically compatible configurations without implying that unlike measurements are directly interchangeable.

## Cell scale

Python remains the scientific authority. The export will attach approximate north–south span, east–west span at the cell-center latitude, and spherical cell area to every exported grid cell. The formulas reuse the pipeline's existing Earth radius and `cell_area_km2` implementation. The map legend states the current grid spacing and its approximate physical span near the footprint; the active-cell readout reports that cell's dimensions and area. East–west span is labeled approximate because it changes with latitude.

## Comparison scope

Comparison is constrained to two configurations in the same experiment. Grid resolution, statistic, threshold, and other background controls remain identical except for the experiment's focal dimension:

- threshold: `threshold_label`
- channel: `channel`
- time: `window_label`
- satellite: `satellite`

The current configuration is map A. Comparison mode supplies a single map-B selector containing only valid alternatives. This prevents confounded arbitrary comparisons and keeps the interaction small.

## Exported comparison evidence

Python precomputes every valid focal pair and exports deterministic records. Each record contains configuration A/B identifiers, selected-area difference and ratio, centroid separation in kilometres, intersection and union area in square kilometres, and area-weighted Jaccard overlap. Geographic overlap is calculated from cell bounds/areas, so the metric remains meaningful without relying on internal cell indexes. The browser performs exact lookup and formatting only.

No absolute-flux delta is exported or displayed for satellite or proton-channel comparisons. UI copy explicitly says those modes compare footprint location and shape only.

## Interface

A `Compare two maps` control sits beside the analysis controls. In single-map mode the existing layout remains unchanged. In comparison mode, two matched map panels appear side by side with concise A/B labels, followed by a difference summary. At narrow widths the maps stack. Each panel retains the same perimeter, centroid, legend, and geographic context as the primary map.

The URL may include a canonical `compare` configuration ID. Invalid or incompatible values fail closed by returning to single-map mode.

## Accessibility and presentation

The comparison selector has an explicit label, each map figure has a distinct accessible name, and changes are announced through the existing live status. Scientific copy is direct and descriptive; no promotional language or catchphrases are added.

## Non-goals

- No combined multi-parameter or consensus model.
- No browser-side scientific calculations.
- No unrestricted comparison between experiments.
- No flux-difference heatmap or claims of improved accuracy.
- No deployment work.

