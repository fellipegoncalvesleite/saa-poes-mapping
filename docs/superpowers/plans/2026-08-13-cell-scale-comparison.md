# Cell Scale and Controlled Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit physical cell dimensions and a same-experiment, one-factor, side-by-side comparison mode backed entirely by Python-computed values.

**Architecture:** Extend the deterministic viewer payload with per-cell physical geometry and canonical pairwise comparison records. Strict TypeScript validation accepts only the exact expanded contract; focused state helpers resolve compatible alternatives, while reusable map rendering displays A and B without calculating science.

**Tech Stack:** Python 3.12, pandas/Parquet, pytest, TypeScript, Vite, Vitest/jsdom, SVG, CSS.

## Global Constraints

- Python is the scientific authority; the browser performs lookup and display only.
- Compare only configurations from one experiment whose non-focal settings match.
- Do not compare absolute flux across satellites or proton-energy channels.
- Keep all 340 canonical configurations and deterministic exports.
- Do not add dependencies or deployment work.

---

### Task 1: Export physical cell geometry

**Files:**
- Modify: `src/saa/viewer_export.py`
- Modify: `tests/test_viewer_export.py`
- Regenerate: `outputs/viewer/viewer_data.js`
- Regenerate: `site/public/data/viewer_data.json`

**Interfaces:**
- Produces: each grid cell tuple gains `north_south_km`, `east_west_km`, and `cell_area_km2`; grid `columns` declares those fields.

- [ ] Add failing tests asserting 2°/5° geometry is finite, positive, latitude-sensitive, and equal to the established spherical formula.
- [ ] Run `.venv/bin/pytest tests/test_viewer_export.py -q` and confirm failure from the missing geometry fields.
- [ ] Reuse `R_EARTH_KM` and `cell_area_km2` in `export_grid` to emit the three values.
- [ ] Run the focused test and confirm it passes.
- [ ] Commit with `feat: export physical grid-cell scale`.

### Task 2: Export canonical one-factor comparisons

**Files:**
- Modify: `src/saa/viewer_export.py`
- Modify: `tests/test_viewer_export.py`
- Regenerate: `outputs/viewer/viewer_data.js`
- Regenerate: `site/public/data/viewer_data.json`

**Interfaces:**
- Produces: top-level `comparisons` records with `id`, `experiment`, `focal_dimension`, `configuration_a`, `configuration_b`, `centroid_distance_km`, `selected_area_difference_km2`, `selected_area_ratio`, `intersection_area_km2`, `union_area_km2`, and `jaccard_overlap`.

- [ ] Add failing tests for deterministic IDs, focal-only pairing, exact pair counts, haversine centroid distance, area-weighted overlap, and absence of flux deltas.
- [ ] Run the focused pytest tests and confirm they fail because `comparisons` is absent.
- [ ] Implement pair grouping by all non-focal dimensions and compute metrics from exported configurations/grids.
- [ ] Run the focused tests and full Python suite.
- [ ] Regenerate both public data artifacts and confirm byte-stable repeat exports.
- [ ] Commit with `feat: export controlled map comparisons`.

### Task 3: Validate and resolve comparison data

**Files:**
- Modify: `site/src/data/types.ts`
- Modify: `site/src/data/load.ts`
- Create: `site/src/state/comparison.ts`
- Modify: `site/src/data/load.test.ts`
- Create: `site/src/state/comparison.test.ts`

**Interfaces:**
- Produces: `Comparison`, expanded `ActiveCell`, `comparisonOptions(payload, current)`, and `resolveComparison(payload, current, requestedId)`.

- [ ] Add failing validator tests for malformed cell geometry, unknown comparison IDs, incompatible settings, invalid metric ranges, and forbidden extra metric keys.
- [ ] Add failing state tests showing only same-experiment focal alternatives are returned and invalid requests fail closed.
- [ ] Run `npm test -- --run src/data/load.test.ts src/state/comparison.test.ts` in `site/` and confirm expected failures.
- [ ] Add the exact types, runtime validation, indexes, and resolvers.
- [ ] Run the focused frontend tests and confirm they pass.
- [ ] Commit with `feat: validate controlled comparison states`.

### Task 4: Display physical scale and two-map comparison

**Files:**
- Modify: `site/index.html`
- Modify: `site/src/main.ts`
- Modify: `site/src/map/render.ts`
- Modify: `site/src/ui/readout.ts`
- Create: `site/src/ui/comparison.ts`
- Modify: `site/src/styles.css`
- Modify: `site/src/map/map.test.ts`
- Modify: `site/src/ui/ui.test.ts`
- Modify: `site/src/full-state-smoke.test.ts`

**Interfaces:**
- Consumes: validated geometry and `Comparison` records from Tasks 1–3.
- Produces: single/compare toggle, compatible B selector, two labeled maps, physical cell readout, and comparison metric summary.

- [ ] Add failing UI tests for physical dimensions, compare controls, side-by-side A/B labels, difference metrics, satellite/channel caution, invalid URL fallback, and rendering every valid comparison.
- [ ] Run the focused Vitest files and confirm failures are caused by missing UI.
- [ ] Extend map active-cell data and legend formatting, add comparison markup/rendering, and preserve current single-map behavior.
- [ ] Add responsive two-column/stacked CSS and clear focus/selected states.
- [ ] Run focused and full frontend tests plus `npm run build`.
- [ ] Commit with `feat: add scientific map comparison mode`.

### Task 5: Verify the complete local site

**Files:**
- Modify if needed: files above only for defects found during verification.

**Interfaces:**
- Produces: verified local experience and updated draft PR branch.

- [ ] Run `.venv/bin/pytest -q`, viewer validation scripts, `npm test -- --run`, and `npm run build`.
- [ ] Inspect single-map 2° and 5° states and a comparison from each experiment at desktop and narrow viewport widths.
- [ ] Confirm comparison URLs round-trip, physical sizes vary correctly with latitude, no browser console errors appear, and no overflow obscures controls or maps.
- [ ] Commit any test-first defect corrections, push `feat/public-research-site`, and update the existing draft PR.

