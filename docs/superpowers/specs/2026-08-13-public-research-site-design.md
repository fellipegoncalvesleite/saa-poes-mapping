# SAA POES Mapping Public Research Site Design

Date: 2026-08-13
Status: Approved for implementation planning

## Purpose

Build a new public research website in `site/` that makes the project's central result immediately
visible: there is no method-free version of the particle-defined map. Reasonable methodological
choices materially change the candidate high-proton-flux footprint's stored selected area and
flux-weighted centroid.

The website is an explanatory research tool. It is not the paper, the legacy scientific viewer, a
general-purpose dashboard, or a hazard product. It will display only accepted January-2024 scientific
states and will preserve all restrictions in `docs/CLAIM_AUDIT.md`.

## Product Principles

1. The geographic map is the primary visual object and appears in the first desktop viewport.
2. Navigation is organized by scientific question: Threshold, Proton energy, Time, and Satellite.
3. Scientific results are displayed, never recomputed in the browser.
4. Every interactive state resolves exactly to one of the 340 canonical configurations.
5. Missing, coverage-failed, or non-positive cells remain blank and are never treated as zero or
   interpolated.
6. Copy consistently describes candidate, threshold-defined, and method-dependent footprints and
   flux-weighted centroids. It does not imply a definitive boundary, true center, causality, dose,
   health risk, spacecraft danger, or cross-calibrated absolute comparisons.
7. The visual language follows public NASA Earthdata/NOAA technical products: neutral sans-serif
   typography, white and cool-gray surfaces, a compact dark institutional header, blue/red utility
   accents, visible metadata, and Viridis reserved for the scientific map. It must not resemble a
   marketing landing page.

## Approved Visual Revision

The 2026-08-13 review replaces the original editorial hero treatment. The revision is approved by
the user and has these requirements:

- no display serif, oversized headline, slogan, catchphrase, or promotional metric card;
- the first content block identifies the project, scope, data source, date, and scientific status in
  direct language;
- a compact summary strip may report accepted counts or key comparison values with labels and units;
- the explorer begins immediately after that summary and remains the dominant page element;
- section headings are literal: `Interactive map`, `Results`, `Method`, `Magnetic-field context`,
  `Reproducibility`, and `Limitations`;
- the visual reference is the information hierarchy of NASA Earthdata and NOAA satellite technical
  pages, without copying their marks, logos, page code, or claiming affiliation.

## Approved Map-Clarity Revision

The 2026-08-13 map review replaces the per-cell white selection outlines with a clearer display-only
hierarchy while preserving canonical selected-cell membership:

- `Grid resolution` is a visible primary control with exactly `5°` and `2°`; it is not hidden in
  `Analysis settings`.
- The chosen grid resolution persists when switching among Threshold, Proton energy, Time, and
  Satellite. Other incompatible dimensions still reset to the target experiment's canonical default.
- Non-selected covered cells remain visible but are subdued. Selected cells retain full Viridis
  intensity and receive a subtle translucent emphasis.
- The selected-cell union is shown with a single high-contrast outer perimeter generated only from
  stored selected membership. Internal cell borders are not presented as the footprint boundary.
- The stored flux-weighted centroid receives a direct text label and distinct symbol.
- The legend explicitly defines color, selected perimeter, and centroid using the active statistic
  and threshold label.
- These changes are presentation geometry only. They do not add interpolation, recompute selection,
  or change scientific metrics.

## Selected Technical Approach

Use a small static frontend built with Vite, TypeScript, semantic HTML, modern CSS, and SVG. Do not
use React, Vue, Svelte, Next, a backend, map tiles, or a general map library.

The first version will load a single generated JSON payload at
`site/public/data/viewer_data.json`. The existing 2.7 MB uncompressed payload is acceptable for a
static v1 with host compression. It will be split mechanically by experiment only if measured mobile
performance demonstrates that the single payload is unacceptable.

The public site is separate from `outputs/viewer/`. Existing viewer behavior and validation remain
intact.

## Repository and Git Workflow

- Start from current `main` commit `56856c6` on branch `feat/public-research-site`.
- PR #4 remains open and will not be merged automatically.
- Port only PR #4's useful deterministic geography and validation ideas. Its UI is not authoritative.
- Keep scientific formulas, accepted notebooks, canonical tables, and results unchanged.
- Use coherent commits separating payload/export work, frontend behavior, public presentation, and
  validation where practical.
- After verification, push the branch and open a draft pull request to `main`. Do not merge it.

## Scientific Authority and Data Flow

The authority chain is:

```text
validated canonical Python outputs
    -> build_viewer_payload()
    -> deterministic JSON writer
    -> site/public/data/viewer_data.json
    -> TypeScript validation and exact lookup
    -> SVG/readout display
```

The JSON must be semantically identical to the object returned by `build_viewer_payload()`. The
website exporter may add serialization plumbing but may not add scientific calculations or manually
copied metrics.

The existing four experiment families remain independent:

| Experiment | Dimensions | States |
|---|---|---:|
| Threshold | grid, statistic, threshold | 20 |
| Proton energy | channel, grid, statistic, threshold | 60 |
| Time | window, grid, statistic, threshold | 160 |
| Satellite | satellite, grid, statistic, threshold | 100 |

No arbitrary satellite x time x channel Cartesian product will be introduced. CP5C remains fixed
five-satellite evidence, not a fifth map family.

## Deterministic Geography

Port the PR #4 Natural Earth 1:110m approach into a neutral site asset:

- version-pinned Natural Earth revision `v5.1.2`;
- coastline and Admin-0 land boundaries;
- WGS84 longitude/latitude coordinates;
- source URLs, theme versions, hashes, and public-domain terms retained;
- deterministic ordering and serialization;
- the same region and longitude/latitude projection relationship as the canonical grid.

Geography is visual context only. It must never affect configuration lookup, metrics, selected-cell
membership, or any other scientific state.

## Page Architecture

The page follows this order:

1. compact header with Explore, Findings, Method, Reproducibility, and GitHub links;
2. factual project summary and explorer;
3. concise findings narrative;
4. descriptive magnetic framing;
5. public-facing method pipeline and technical disclosure;
6. reproducibility;
7. limitations;
8. minimal footer with provenance and repository links.

### Header and Project Summary

The compact header identifies `SAA POES Mapping`, describes it as a public research project, and
links directly to Map, Results, Method, Data and code, and Limitations. The project summary uses the
literal title `Method sensitivity of particle-defined South Atlantic Anomaly maps`, followed by two
sentences that state the January-2024 NOAA/MetOp scope and the one-choice-at-a-time method. A visible
status line states `Candidate high-flux footprints; not a definitive SAA boundary.`

A compact metadata grid reports dataset, observation period, number of satellites, validated map
configurations, and the approximately 386 km principal threshold-centroid comparison. The explorer
begins directly below it, without a promotional hero or decorative callout.

### Explorer Composition

At desktop width, the explorer uses an approximately two-thirds map and one-third controls/readout
layout. The map is visually dominant. The rail may be locally sticky as long as it does not trap
scrolling.

Experiment tabs are proper buttons within a tablist and use visitor-facing labels:

- Threshold: `How much does the footprint depend on what counts as high flux?`
- Proton energy: `Does proton energy change the footprint?`
- Time: `How stable is the footprint as observations accumulate?`
- Satellite: `Do different satellites locate the same high-flux region?`

Switching an experiment loads that family's canonical `initial_values`; incompatible state never
carries between families.

The experiment-specific dimension is the focal control:

- Threshold: five-button segmented control for Top 20%, Top 10%, Top 5%, Top 2%, Top 1%.
- Proton energy: three-button segmented control for approximately 25, 50, and 100 MeV, with exact
  `mep_omni_flux_p1/p2/p3` identifiers in details.
- Time: grouped native select with cumulative intervals and disjoint weeks clearly separated.
- Satellite: five-button or compact wrapping segmented control for NOAA-15, NOAA-18, NOAA-19,
  MetOp-01, and MetOp-03.

Threshold remains available as a secondary control in the non-threshold experiments because it is a
validated dimension of those families. Grid and statistic, along with secondary threshold where
needed, appear in an `Analysis settings` disclosure. Grid has exactly 5 and 2 degrees; statistic has
exactly Mean and Median.

### Map

The responsive SVG uses explicit layers:

1. clipped Natural Earth country boundaries and coastlines;
2. subdued geographic guides and axes;
3. canonical grid cells colored from the stored current-grid log domain using Viridis;
4. selected-cell outlines as a separate high-contrast layer;
5. the stored flux-weighted centroid as a distinct cross/ring symbol;
6. an optional active-cell focus/inspection overlay;
7. compact textual/color legend.

Cell values are used only for display color and readout. Coverage-failed cells are transparent.
Covered non-positive cells are also blank for log display. The adjacent note states that blank means
missing, insufficiently sampled, or non-positive; it is not zero and is not interpolated.

At 2-degree resolution, ordinary grid borders are softened to keep the selected outline and
geography legible. The cells are not downsampled.

### Cell Inspection

Pointer movement, pointer activation, and touch activation identify a cell through SVG geometry and
update a single active-cell readout. The readout contains:

- cell latitude and longitude;
- current mean or median value and units;
- sample count;
- coverage state;
- selected/not selected state.

SVG cells do not enter keyboard tab order. The map container is one focusable control with concise
instructions. On focus, the active cell begins at the selected cell nearest the stored centroid;
arrow keys move one canonical cell in the corresponding direction, Home returns to the centroid-nearest
cell, and Escape clears the inspection. The same active-cell readout serves pointer, touch, and keyboard
inspection. Keyboard/touch changes update the polite active-cell status; pointer movement does not
produce noisy announcements.

### Primary Readout

The rail emphasizes:

1. selected area;
2. stored flux-weighted centroid;
3. selected cells / covered cells;
4. coverage warning when present.

A Details disclosure contains the canonical threshold cutoff, percentile, configuration ID, period,
channel identifier and units, satellite/platform metadata, coverage rule, and peak flux only where
scientifically appropriate. Satellite mode explicitly hides/promotes no absolute flux comparison and
states that absolute cross-satellite flux is not allowed.

### How to Read the Map

A compact four-part explanation defines Cell, Color, Outline, and Centroid in public language. It
does not assume knowledge of Python, Pandas, NetCDF, or repository internals.

## State Model and Failure Behavior

At startup, TypeScript performs a structural validation of schema version, experiment set,
configuration counts, unique IDs, dimensions, grid references, supported control values, selected
indices, and CP5C shape. It builds maps keyed by canonical configuration ID.

State is always represented as an experiment plus the exact dimension values declared by that
experiment. Resolution constructs the same stable ID format used by Python and performs an exact map
lookup.

If a URL or interaction requests an invalid ID/state:

1. do not compute a substitute, nearest state, or interpolated value;
2. report a development-visible error and clear any stale state;
3. reset to the active experiment's canonical initial state;
4. announce the reset once in the configuration status region.

Implement shareable URLs as `?config=<encoded canonical configuration ID>`. Startup accepts only an
exact exported ID; successful interaction replaces that query value without adding history entries.
An invalid query follows the fail-closed reset path. Do not encode an arbitrary parameter blob.

Configuration changes render directly from old to new canonical state with only restrained opacity
transitions of roughly 150 ms. No intermediate scientific states are animated. Reduced-motion users
receive immediate updates.

## Findings

The findings section avoids a wall of cards and uses varying visual weight.

### Threshold

This is dominant. It states that changing only what counts as high flux materially moves and resizes
the footprint, using canonical principal values of approximately 386 km and a 17.6533 area ratio.
Controls or deep links return the explorer to the top-20% and top-1% principal states so visitors can
see the evidence on the same map.

### Time

State approximately 288 km from one day to the month, with four weekly windows within approximately
118 km. Explain that one-day coverage is orbit-track sparse and do not describe the difference as
physical SAA motion.

### Satellite

State approximately 272 km maximum pairwise principal top-10 spread and approximately 13 km between
NOAA-18 and NOAA-19. Note that threshold sensitivity can exceed inter-satellite spread. Explicitly
limit interpretation to location/shape and prohibit absolute flux comparison.

### Proton Energy

State that centers differ by approximately 100–300 km while remaining broadly similar. Give this
finding less visual weight and state that absolute fluxes at different energies are not treated as
the same physical quantity.

These narrative comparison values are accepted scientific copy sourced from the current claim audit
and canonical outputs. TypeScript does not recalculate distances or ratios.

## Magnetic Framing

The section title is `What does the magnetic field add?` and leads with:

`The particle-defined footprint is concentrated at relatively low regional modeled magnetic-field
strength, but the magnetic field does not define the footprint.`

Render the fixed CP5C five-row evidence as a restrained comparison figure/table showing Btot,
L_IGRF, and MLT separation. Include:

- classification `CONSISTENT`;
- 5/5 low-Btot support;
- 5/5 Btot-dominance support;
- 100% below each satellite's own regional Btot q25;
- about 90% captured within the lowest 11.7–12.1% of each satellite's own regional Btot distribution;
- NOAA-15's materially larger MLT separation as the stated exception.

No magnetic boundary map is produced. Text states that the comparison is within satellite,
descriptive, model-based, and non-causal.

## Method and Reproducibility

The method section presents this public-facing sequence:

```text
NOAA satellite observations
-> assign observations to geographic cells
-> calculate mean/median and sample count
-> apply coverage requirement
-> rank cells and select top percentile
-> calculate physical area and flux-weighted centroid
-> repeat while changing one methodological choice
```

The technical disclosure covers the geographic region, 5/2-degree grids, monthly and scaled shorter
coverage rules, mean/median statistics, five percentile choices, spherical cell area, flux-weighted
centroid, IFC handling, and January-2024 scope without reproducing source documentation verbatim.

Reproducibility links to the repository, claim audit, reproducibility checklist, and paper outline.
It summarizes public NOAA/NCEI processed L1b data, SEM-2 MEPED, five spacecraft, Python 3.12,
deterministic outputs, validators, provenance/checksums, and the generated frontend payload.

## Limitations

Keep the following visible and concise:

- January 2024 only;
- percentile-defined candidate footprint, not a universal boundary;
- primary analysis centered on p1;
- no calibrated absolute cross-satellite flux comparison;
- IGRF values are modeled quantities;
- sampling and local-time effects are not fully separated;
- `mep_IFC_on == -1` is retained and uninterpreted;
- external scientific review remains important.

Link to the complete claim audit.

## Responsive Design

- Desktop around 1440 px: wide explorer with map/rail split and visible experiment navigation.
- Tablet around 768 px: map first, controls/readout below, settings in a compact two-column layout.
- Phone around 375 px: single column, map full width, focal experiment control directly after the
  question, collapsed settings, compact two-column metrics where readable, and no page horizontal
  overflow.

All controls meet practical touch target sizing. Experiment navigation may scroll internally on
small screens but the page itself must not scroll horizontally.

## Accessibility

- semantic landmarks and heading order;
- real buttons, selects, fieldsets, legends, labels, and disclosures;
- visible focus and WCAG-AA-minded text/control contrast;
- selected footprints differentiated by outline as well as color;
- centroid differentiated by symbol and textual coordinates;
- textual log legend and blank-cell explanation;
- one accessible active-configuration summary and one active-cell readout;
- no thousands of SVG tab stops;
- useful, limited `aria-live` announcements;
- full keyboard control operation and touch inspection;
- `prefers-reduced-motion` support.

The main scientific conclusion remains understandable through text and readouts without interpreting
Viridis hues.

## Frontend Module Boundaries

Keep modules small and purpose-specific:

- `data/types.ts`: payload and state interfaces;
- `data/load.ts`: fetch, structural validation, and indexes;
- `state/configuration.ts`: canonical ID construction, experiment defaults, exact resolution, and
  canonical-ID URL handling;
- `map/projection.ts`: longitude/latitude-to-SVG display transforms only;
- `map/colors.ts`: display-only Viridis interpolation and log-domain normalization;
- `map/render.ts`: SVG layer creation/update and inspection events;
- `ui/controls.ts`: experiment and method controls generated from payload options;
- `ui/readout.ts`: primary metrics, details, configuration summary, and cell inspection;
- `ui/content.ts`: fixed explanatory sections and CP5C presentation;
- `main.ts`: startup orchestration and rendering lifecycle.

Exact filenames may adapt during implementation if the boundaries remain clear.

## Testing and Validation

### Python payload contract

Add a deterministic JSON writer and validator covering:

- exactly 340 configurations and counts 20/60/160/100;
- exact experiment dimensions and unique stable IDs;
- no unsupported states;
- exact grid cells, coverage states, and selected-cell indices;
- canonical discrete metrics and fixed-tolerance floats;
- coverage-failed flux serialized as null;
- exact five-satellite CP5C rows/classification;
- satellite comparison fields keep `absolute_flux_comparison_allowed` false;
- the website JSON deeply matches a fresh `build_viewer_payload()` result;
- the existing viewer validator continues to pass.

### TypeScript unit tests

Test structural validation, every valid configuration lookup, control-option support, canonical
default resets, invalid state/ID failure, display formatting, projection coordinates, color blanking,
and cell inspection data.

### Browser tests

Use Playwright to traverse all 340 canonical IDs and assert:

- exactly one configuration resolves;
- controls match its values;
- selected rendered outline count equals canonical selected-cell count;
- centroid uses stored coordinates;
- readout matches canonical metrics;
- no unsupported state or console error occurs.

Representative visual/behavior cases cover both grids, both statistics, all thresholds, all
channels, all windows, and all satellites. Tests verify blank cells remain transparent and geography
does not change data state.

Run responsive checks at approximately 375, 768, and 1440 px with horizontal-overflow assertions.
Run automated accessibility checks if the small dependency remains practical, plus manual keyboard,
focus, touch, and reduced-motion checks.

### Regression and completion verification

Before declaring completion:

- run the Python unit/contract suite in the required Python 3.12 environment;
- run all available checkpoint validators without regenerating or changing scientific results;
- run existing viewer export/validation;
- run frontend unit tests and the 340-state browser smoke test;
- run the production build and static preview;
- inspect rendered desktop, tablet, and phone layouts;
- review public copy against `docs/CLAIM_AUDIT.md` and forbidden wording;
- inspect the final diff for accidental scientific changes;
- answer the final product-test questions against the rendered site.

The current system Python lacks NumPy and Pandas, so the repository's Python 3.12 virtual environment
must be created before full baseline or final scientific validation.

## Performance

V1 uses one static JSON payload with host gzip/Brotli and no remote basemap. The frontend avoids SVG
filters and updates only the map/readout required by a canonical state. Measure production asset size,
load time, and interaction responsiveness on a mobile-sized viewport.

Only if measurement shows the single payload is unacceptable, split it deterministically into the
four existing experiment families plus CP5C metadata. Such a split must preserve exact semantic
content and remain generated from the same Python authority.

## Acceptance Standard

The implementation is acceptable when a visitor can understand the research question and caveat in
about 15 seconds, the geographic map is unquestionably the central object, threshold changes visibly
demonstrate the principal result, every state is one of the 340 accepted configurations, scientific
restrictions are consistently respected, and methodology/reproducibility remain easy to reach.

The final impression must be unmistakable: the candidate high-proton-flux footprint changes when
reasonable mapping choices change, and the website shows that dependence using only validated
scientific states.
