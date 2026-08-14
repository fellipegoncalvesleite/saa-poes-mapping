# Focused Map Cartography Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Focus the map on all selected results, add a 500 km scale bar, and print the stored comparison displacement beside Map B's centroid.

**Architecture:** The SVG renderer owns a fixed display-only map extent and cartographic scale bar. An optional render option changes centroid label text; comparison mode passes the already validated Python comparison distance.

**Tech Stack:** TypeScript, SVG, CSS, Vitest/jsdom, Vite.

## Global Constraints

- Do not change the scientific payload region or calculate comparison distance in the browser.
- Use fixed latitude −50° to +5° and longitude −95° to +10° on every map.
- Keep all selected cells across the 340 canonical configurations visible.
- Display `500 km at 25°S` and use the stored `centroid_distance_km` for Map B.

---

### Task 1: Test the focused cartographic contract

**Files:**
- Modify: `site/src/map/map.test.ts`
- Modify: `site/src/ui/ui.test.ts`

**Interfaces:**
- Consumes: existing `renderMap` and canonical comparison payload.
- Produces: failing expectations for fixed coordinates, clipping, scale bar, and comparison annotation.

- [ ] Add map assertions for projected −95°/10°/−50°/5° boundaries, clip paths on cell/selected layers, and a `500 km at 25°S` scale bar.
- [ ] Add a rendering assertion that an explicit `→ 386 km from A` label replaces the default centroid label.
- [ ] Run `npm test -- --run src/map/map.test.ts src/ui/ui.test.ts` and confirm the new assertions fail for missing behavior.

### Task 2: Implement focused map rendering

**Files:**
- Modify: `site/src/map/render.ts`
- Modify: `site/src/main.ts`
- Modify: `site/src/styles.css`

**Interfaces:**
- Produces: `renderMap(..., options?: { centroidLabel?: string })`, fixed `DISPLAY_REGION`, clipped map layers, and scale-bar SVG layer.

- [ ] Project all visual layers through `{lat_min:-50, lat_max:5, lon_min:-95, lon_max:10}` and size cells from that extent.
- [ ] Render a 500 km bar at 25°S using `500 / (6371 × π/180 × cos(25°))` longitude degrees.
- [ ] Clip geography, guides, cells, footprint perimeter, and inspection layers to the plot rectangle.
- [ ] Pass `A centroid` to Map A and `→ ${Math.round(comparison.centroid_distance_km)} km from A` to Map B.
- [ ] Run focused tests and commit with `feat: focus maps and label centroid shifts`.

### Task 3: Verify and publish

**Files:**
- Modify only if a test-first correction is required.

**Interfaces:**
- Produces: updated local preview and draft PR branch.

- [ ] Run all 23+ frontend tests and `npm run build`.
- [ ] Visually inspect single and comparison views at desktop and 320 px, confirm no overflow or console errors.
- [ ] Run the complete Python suite and 7-check viewer validator to prove scientific outputs remain unchanged.
- [ ] Push `feat/public-research-site` to the existing draft PR.

