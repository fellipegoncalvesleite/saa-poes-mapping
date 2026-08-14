# SAA POES Mapping Public Research Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a static public research website that exposes exactly the project's 340 validated method-sensitivity map states while making threshold dependence visually obvious and scientifically traceable.

**Architecture:** A thin Python export writes the existing `build_viewer_payload()` object as deterministic JSON. A framework-free Vite/TypeScript application validates that payload, resolves only exact canonical configuration IDs, and renders stored grids, selected memberships, metrics, and CP5C evidence into semantic HTML and layered SVG.

**Tech Stack:** Python 3.12, pandas/NumPy/pyarrow, Vite 8.2.1, TypeScript 7.0.2, Vitest 4.1.10, jsdom 30.0.1, Playwright 1.62.1, `@axe-core/playwright` 4.13.0, semantic HTML, modern CSS, SVG.

## Global Constraints

- Work only on `feat/public-research-site`; do not commit to `main` and do not merge a pull request.
- Keep the new application in `site/`; do not redesign or replace `outputs/viewer/`.
- Do not change scientific formulas, accepted notebooks, canonical tables, or accepted results.
- Preserve the authority chain: validated canonical Python outputs -> `build_viewer_payload()` -> deterministic JSON -> TypeScript display only.
- Export exactly 340 configurations with experiment counts 20 threshold, 60 channel, 160 time, and 100 satellite.
- Never create a satellite x time x energy x threshold x grid x statistic Cartesian product.
- CP5C remains fixed five-satellite evidence, not an interactive map dimension.
- Invalid state must fail closed; never interpolate, choose a nearest state, or calculate a replacement.
- Coverage-failed, missing, or non-positive log-display cells remain blank and are never rendered as zero.
- Use only candidate high-flux footprint, threshold-defined footprint, method-dependent footprint, selected area, flux-weighted centroid, methodological sensitivity, descriptive magnetic framing, and modeled magnetic-field wording.
- Never imply a definitive SAA boundary, true center, discovery, biological dose, health risk, spacecraft danger/safety advice, IGRF causality, absolute cross-satellite flux comparability, absolute cross-channel flux comparability, or equivalence with the magnetic minimum.
- Use deterministic local Natural Earth 1:110m geography only; no tiles, Mapbox, Google Maps, Leaflet, OpenStreetMap, or imagery.
- No React, Vue, Svelte, Next, backend, database, API route, authentication, or framework runtime.
- Test responsive behavior at 375, 768, and 1440 px and preserve keyboard, touch, focus, reduced-motion, and non-color accessibility.
- Use test-driven development for every production behavior and run verification before completion claims.

## File Structure

### Python authority and validation

- `src/saa/viewer_export.py`: retain payload construction; add deterministic neutral JSON serialization.
- `scripts/export_site_data.py`: generate `site/public/data/viewer_data.json` from canonical tables.
- `scripts/generate_site_geography.py`: generate version-pinned Natural Earth JSON.
- `scripts/validate_site_outputs.py`: independently validate JSON semantics, geography, and static-site contracts.
- `tests/test_site_export.py`: deterministic JSON writer and canonical integration contracts.
- `tests/test_site_geography.py`: geography provenance, regional geometry, and determinism contracts.
- `tests/test_validate_site_outputs.py`: validator predicate and failure-path tests.

### Frontend application

- `site/package.json`, `site/package-lock.json`: pinned frontend scripts and development dependencies.
- `site/tsconfig.json`, `site/vite.config.ts`, `site/vitest.config.ts`: strict TypeScript/Vite/Vitest setup.
- `site/index.html`: semantic page shell and fixed public research content containers.
- `site/src/data/types.ts`: payload, geography, configuration, grid, and cell interfaces.
- `site/src/data/load.ts`: fetch and structural validation for both static JSON assets.
- `site/src/state/configuration.ts`: stable IDs, indexes, exact resolution, defaults, and canonical-ID URL state.
- `site/src/map/projection.ts`: display-only geographic-to-SVG transforms.
- `site/src/map/colors.ts`: display-only Viridis/log normalization.
- `site/src/map/render.ts`: layered SVG rendering and pointer/touch/keyboard inspection.
- `site/src/ui/controls.ts`: payload-driven experiment/focal/settings controls.
- `site/src/ui/readout.ts`: canonical metrics, details, summaries, and active-cell readout.
- `site/src/ui/content.ts`: fixed CP5C visualization and explorer-return actions from findings.
- `site/src/main.ts`: startup orchestration, fail-closed state lifecycle, and coordinated rendering.
- `site/src/styles.css`: modern scientific visual system and responsive/accessibility behavior.
- `site/src/**/*.test.ts`: focused Vitest tests colocated by responsibility.

### End-to-end, deployment, and documentation

- `site/playwright.config.ts`: static preview/browser matrix.
- `site/e2e/explorer.spec.ts`: full 340-state traversal and canonical rendering checks.
- `site/e2e/responsive-accessibility.spec.ts`: 375/768/1440 overflow, keyboard, touch, reduced motion, and axe checks.
- `vercel.json`: root-level static Vercel build/output configuration.
- `.gitignore`: frontend dependencies, builds, and test artifacts.
- `README.md`: public-site development and build commands.
- `docs/REPRODUCIBILITY_CHECKLIST.md`: website export and validation steps.

---

### Revision Task: Institutional scientific-portal presentation

**Files:**
- Modify: `site/index.html`
- Modify: `site/src/styles.css`
- Modify: `site/src/ui/ui.test.ts`

**Produces:** A direct, NASA Earthdata/NOAA-inspired information hierarchy without copied branding,
page code, promotional copy, display-serif typography, or a landing-page hero.

- [ ] Replace the copy test assertions so they require the literal project title, scope status,
  dataset period, `Interactive map`, `Results`, `Method`, `Magnetic-field context`,
  `Reproducibility`, and `Limitations`, and reject the old question headline.
- [ ] Run `cd site && npm test -- --run` and verify the revised assertions fail.
- [ ] Replace the hero with a compact project summary and metadata strip; rename navigation and
  section headings literally; place the explorer immediately after the summary.
- [ ] Replace the editorial palette/type scale with system sans-serif, navy/white/cool-gray surfaces,
  blue/red utility accents, compact spacing, and technical-panel borders while preserving Viridis.
- [ ] Run `cd site && npm test -- --run && npm run build` and verify both pass.
- [ ] Render at desktop and 390×844, verify no horizontal overflow, exercise a threshold change and
  satellite calibration restriction, and confirm an empty error console.
- [ ] Commit the redesign as `feat: adopt scientific portal presentation`.

### Revision Task: Persistent grid control and readable footprint

**Files:**
- Modify: `site/src/ui/controls.ts`
- Modify: `site/src/ui/ui.test.ts`
- Modify: `site/src/map/render.ts`
- Modify: `site/src/map/map.test.ts`
- Modify: `site/src/ui/full-state-smoke.test.ts`
- Modify: `site/src/styles.css`
- Modify: `site/index.html`

**Produces:** A visible 2°/5° grid selector that persists across experiment changes and a map whose
canonical selected-cell union reads as one footprint rather than many outlined squares.

- [ ] Add failing control tests proving `Grid resolution` sits outside `Analysis settings` and that
  switching experiment with `grid_deg: 2` passes `grid_deg: 2` into the target canonical values.
- [ ] Add failing map tests proving selected base cells carry `is-selected`, the selected layer uses
  perimeter paths rather than one rectangle per cell, and the centroid has a direct text label.
- [ ] Run the focused tests and confirm they fail for the intended missing behavior.
- [ ] Update `renderControls()` so grid resolution is a primary fieldset and experiment switches copy
  only the current `grid_deg` into the target experiment's canonical initial values.
- [ ] Build the selected perimeter by canceling shared edges from stored selected cell indices; render
  a white halo plus red perimeter, dim non-selected cells, and label the stored centroid.
- [ ] Replace the compact legend with active-statistic color, active-threshold selected perimeter,
  and centroid explanations; update the public map explanation accordingly.
- [ ] Run `cd site && npm test -- --run && npm run build` and verify both pass.
- [ ] Inspect the live desktop page at 5° and 2°, switch experiments after choosing 2°, and confirm
  the grid persists, the map remains canonical, and the console is clear.
- [ ] Commit as `feat: clarify footprint map and preserve grid choice`, push the existing branch, and
  leave PR #5 open and unmerged.

### Task 1: Deterministic Website JSON Authority

**Files:**
- Modify: `src/saa/viewer_export.py`
- Create: `scripts/export_site_data.py`
- Create: `scripts/validate_site_outputs.py`
- Create: `tests/test_site_export.py`
- Create: `tests/test_validate_site_outputs.py`
- Create generated artifact: `site/public/data/viewer_data.json`

**Interfaces:**
- Consumes: `build_viewer_payload(table_dir: Path) -> dict[str, Any]` and the accepted canonical Parquet tables.
- Produces: `write_viewer_json(payload: dict[str, Any], output: Path) -> str`, `load_site_data(path: Path) -> dict[str, Any]`, and `validate_site_payload(payload, table_dir) -> tuple[bool, str]`.

- [ ] **Step 1: Restore the required local Python 3.12 environment and ignored authority inputs**

Run:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-dev.txt
```

Copy only the required accepted `outputs/tables/*.parquet` files from the existing local research checkout into this clone's ignored `outputs/tables/`, then verify the fresh `build_viewer_payload()` deeply matches the tracked `outputs/viewer/viewer_data.js` using `scripts/validate_viewer_outputs.py`. Do not commit the ignored Parquets.

Expected: existing viewer validation reports all checks passed before site-export code changes.

- [ ] **Step 2: Write failing JSON serialization and validation tests**

Create `tests/test_site_export.py` with contracts equivalent to:

```python
class SiteJsonSerializationTests(unittest.TestCase):
    def test_writer_is_deterministic_neutral_json(self) -> None:
        payload = {"schema_version": 1, "nested": {"b": 2, "a": 1}}
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.json"
            second = Path(tmp) / "second.json"
            one = write_viewer_json(payload, first)
            two = write_viewer_json(payload, second)
            self.assertEqual(one, two)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(json.loads(first.read_text()), payload)
            self.assertFalse(first.read_text().startswith("window."))

    def test_site_payload_matches_fresh_canonical_export(self) -> None:
        expected = build_viewer_payload(ROOT / "outputs" / "tables")
        actual = json.loads((ROOT / "site/public/data/viewer_data.json").read_text())
        self.assertTrue(deep_payload_matches(actual, expected))
        self.assertEqual(sum(x["configuration_count"] for x in actual["experiments"].values()), 340)
```

Create `tests/test_validate_site_outputs.py` with a corruption test that changes one selected index and expects `validate_site_payload()` to fail.

- [ ] **Step 3: Run the new tests and verify they fail**

Run:

```bash
.venv/bin/python -m unittest tests.test_site_export tests.test_validate_site_outputs -v
```

Expected: FAIL because `write_viewer_json`, `scripts/export_site_data.py`, and the site validator do not exist.

- [ ] **Step 4: Implement neutral deterministic JSON writing and independent validation**

Add to `src/saa/viewer_export.py`:

```python
def write_viewer_json(payload: dict[str, Any], output: Path) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ) + "\n"
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8", newline="\n")
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
```

Implement `scripts/export_site_data.py` to call `build_viewer_payload(ROOT / "outputs/tables")`, write `site/public/data/viewer_data.json`, and print counts, grid count, digest, and CP5C classification.

Implement `scripts/validate_site_outputs.py` by reusing fixed `RTOL=1e-9`, `ATOL=1e-12` comparison semantics while independently checking:

```python
EXPECTED_COUNTS = {"threshold": 20, "channel": 60, "time": 160, "satellite": 100}

def load_site_data(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("site payload root must be an object")
    return payload

def validate_site_payload(payload: dict[str, Any], table_dir: Path) -> tuple[bool, str]:
    authority_ok, authority_detail = independent_authority_matches(payload, table_dir)
    cp5c_ok, cp5c_detail = independent_cp5c_matches(payload, table_dir)
    if not authority_ok:
        return False, authority_detail
    if not cp5c_ok:
        return False, cp5c_detail
    fresh = build_viewer_payload(table_dir)
    if not deep_payload_matches(payload, fresh):
        return False, "website JSON differs from fresh build_viewer_payload authority"
    return True, "340 configurations and CP5C match canonical authority"
```

Import independent comparison predicates from `scripts.validate_viewer_outputs` rather than weakening or replacing the existing viewer validator.

- [ ] **Step 5: Generate and validate the website JSON**

Run:

```bash
.venv/bin/python scripts/export_site_data.py
.venv/bin/python -m unittest tests.test_site_export tests.test_validate_site_outputs -v
.venv/bin/python scripts/validate_site_outputs.py
.venv/bin/python scripts/validate_viewer_outputs.py
```

Expected: website JSON equals fresh canonical export; 340 configurations resolve; existing viewer validation still passes.

- [ ] **Step 6: Commit the website authority layer**

```bash
git add src/saa/viewer_export.py scripts/export_site_data.py scripts/validate_site_outputs.py \
  tests/test_site_export.py tests/test_validate_site_outputs.py site/public/data/viewer_data.json
git commit -m "feat: export canonical data for public site"
```

### Task 2: Deterministic Natural Earth Geography

**Files:**
- Create: `scripts/generate_site_geography.py`
- Create: `tests/test_site_geography.py`
- Create generated artifact: `site/public/data/geography.json`

**Interfaces:**
- Consumes: Natural Earth GeoJSON at revision `v5.1.2` and fixed region lat -70..20, lon -100..20.
- Produces: `build_payload() -> dict[str, Any]` and deterministic `site/public/data/geography.json` with `coastlines`, `borders`, source metadata, and hashes.

- [ ] **Step 1: Write failing geography provenance and geometry tests**

Create `tests/test_site_geography.py` using PR #4's validated predicates, adapted to neutral JSON:

```python
def load_geography() -> dict:
    return json.loads((ROOT / "site/public/data/geography.json").read_text())

def test_asset_is_versioned_and_matches_the_scientific_region(self) -> None:
    self.assertEqual(self.geography["schema_version"], 1)
    self.assertEqual(self.geography["region"], REGION)
    self.assertEqual(self.geography["projection"], "WGS84 geographic longitude/latitude")
    self.assertEqual({s["layer"] for s in self.geography["sources"]}, {"coastlines", "borders"})
    self.assertTrue(all(s["revision"] == "v5.1.2" for s in self.geography["sources"]))

def test_context_contains_south_america(self) -> None:
    coast = [point for line in self.geography["coastlines"] for point in line]
    borders = [point for line in self.geography["borders"] for point in line]
    self.assertTrue(any(-55 < lon < -30 and -35 < lat < 10 for lon, lat in coast))
    self.assertTrue(any(-75 < lon < -45 and -35 < lat < 10 for lon, lat in borders))
```

- [ ] **Step 2: Run the geography test and verify it fails**

Run: `.venv/bin/python -m unittest tests.test_site_geography -v`

Expected: FAIL because the generator and JSON asset do not exist.

- [ ] **Step 3: Port the deterministic PR #4 generator into neutral JSON**

Implement `scripts/generate_site_geography.py` with the same version-pinned URLs, `_geometry_lines`, `_intersects_region`, `_regional_lines`, source SHA-256 fields, deterministic sorting, and public-domain metadata used by PR #4. Write plain sorted compact JSON plus newline to `site/public/data/geography.json`, not a global JavaScript assignment.

- [ ] **Step 4: Generate twice and prove byte determinism**

Run:

```bash
.venv/bin/python scripts/generate_site_geography.py
shasum -a 256 site/public/data/geography.json
.venv/bin/python scripts/generate_site_geography.py
shasum -a 256 site/public/data/geography.json
.venv/bin/python -m unittest tests.test_site_geography -v
```

Expected: both hashes match and all provenance/geometry tests pass.

- [ ] **Step 5: Commit deterministic geography**

```bash
git add scripts/generate_site_geography.py tests/test_site_geography.py site/public/data/geography.json
git commit -m "feat: add deterministic site geography"
```

### Task 3: Vite Foundation, Typed Payload Validation, and Exact State Lookup

**Files:**
- Create: `site/package.json`
- Create: `site/package-lock.json`
- Create: `site/tsconfig.json`
- Create: `site/vite.config.ts`
- Create: `site/vitest.config.ts`
- Create: `site/index.html`
- Create: `site/src/data/types.ts`
- Create: `site/src/data/load.ts`
- Create: `site/src/data/load.test.ts`
- Create: `site/src/state/configuration.ts`
- Create: `site/src/state/configuration.test.ts`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `/data/viewer_data.json`, `/data/geography.json`.
- Produces: `loadScientificData(fetcher?: typeof fetch): Promise<LoadedData>`, `validatePayload(input: unknown): ViewerPayload`, `buildConfigurationIndex(payload): ConfigurationIndex`, `resolveConfiguration(index, id): Configuration | undefined`, and canonical URL helpers.

- [ ] **Step 1: Scaffold the dependency-minimal frontend and strict compiler configuration**

Create `site/package.json` with:

```json
{
  "name": "saa-poes-mapping-public-site",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview --host 127.0.0.1",
    "test": "vitest run",
    "test:e2e": "playwright test"
  },
  "devDependencies": {
    "@axe-core/playwright": "4.13.0",
    "@playwright/test": "1.62.1",
    "jsdom": "30.0.1",
    "typescript": "7.0.2",
    "vite": "8.2.1",
    "vitest": "4.1.10"
  }
}
```

Use strict TypeScript with DOM/ES2023 libraries and Vite module resolution. Configure Vitest for jsdom and `site/src/**/*.test.ts`. Add `site/node_modules/`, `site/dist/`, `site/playwright-report/`, `site/test-results/`, and `.venv/` to `.gitignore`. Run `npm install` in `site/` to create the lockfile.

- [ ] **Step 2: Write failing structural validation and exact-lookup tests**

In `site/src/data/load.test.ts`, load the tracked JSON and assert exact schema/experiment counts, grid references, and CP5C five-row shape. In `site/src/state/configuration.test.ts`, add:

```ts
it("resolves every canonical configuration id exactly once", () => {
  const index = buildConfigurationIndex(payload);
  const configurations = Object.values(payload.experiments).flatMap((x) => x.configurations);
  expect(configurations).toHaveLength(340);
  for (const configuration of configurations) {
    expect(resolveConfiguration(index, configuration.id)).toBe(configuration);
  }
});

it("fails closed for unsupported ids and state", () => {
  const index = buildConfigurationIndex(payload);
  expect(resolveConfiguration(index, "threshold|grid_deg=3|statistic_used=mean_flux|threshold_label=top10"))
    .toBeUndefined();
  expect(resolveValues(index, "threshold", {grid_deg: 5, statistic_used: "mean_flux", threshold_label: "top7"}))
    .toEqual({ok: false, fallback: payload.experiments.threshold.initial_values});
});
```

Add URL tests proving only an exact encoded `?config=` ID is accepted and invalid IDs reset to the experiment default.

- [ ] **Step 3: Run Vitest and verify the tests fail**

Run: `cd site && npm test`

Expected: FAIL because typed loaders and configuration functions do not exist.

- [ ] **Step 4: Define the payload types and runtime validation**

Define exact interfaces for `ViewerPayload`, `Experiment`, `Configuration`, `Grid`, `CellTuple`, `Cp5cPayload`, `GeographyPayload`, and `LoadedData`. Implement runtime guards that reject wrong schema, missing experiment names, wrong counts, duplicate IDs, undeclared control values, missing grid references, out-of-range selected indices, CP5C row/count errors, and region mismatch between geography and data.

The loader must use:

```ts
export async function loadScientificData(fetcher: typeof fetch = fetch): Promise<LoadedData> {
  const [payloadResponse, geographyResponse] = await Promise.all([
    fetcher("/data/viewer_data.json"),
    fetcher("/data/geography.json"),
  ]);
  if (!payloadResponse.ok || !geographyResponse.ok) throw new Error("Scientific assets failed to load");
  return validateLoadedData(await payloadResponse.json(), await geographyResponse.json());
}
```

- [ ] **Step 5: Implement stable IDs, exact indexes, defaults, and URL handling**

Use the Python ordering contract:

```ts
export function stableConfigurationId(experiment: ExperimentName, values: ConfigurationValues): string {
  return [experiment, ...Object.keys(values).sort().map((key) => `${key}=${String(values[key])}`)].join("|");
}
```

Build one global ID map and per-experiment maps. `resolveValues` returns a discriminated union with the exact configuration on success or that experiment's canonical default configuration on failure. URL writes use `history.replaceState` with a single encoded canonical ID.

- [ ] **Step 6: Run unit tests and production type/build checks**

Run:

```bash
cd site
npm test
npm run build
```

Expected: all payload/state tests pass and Vite produces static `site/dist/`.

- [ ] **Step 7: Commit the typed foundation**

```bash
git add .gitignore site/package.json site/package-lock.json site/tsconfig.json \
  site/vite.config.ts site/vitest.config.ts site/index.html site/src/data site/src/state
git commit -m "feat: add exact canonical site state"
```

### Task 4: SVG Map, Viridis Display, and Accessible Cell Inspection

**Files:**
- Create: `site/src/map/projection.ts`
- Create: `site/src/map/projection.test.ts`
- Create: `site/src/map/colors.ts`
- Create: `site/src/map/colors.test.ts`
- Create: `site/src/map/render.ts`
- Create: `site/src/map/render.test.ts`

**Interfaces:**
- Consumes: `ViewerPayload`, `GeographyPayload`, and one exact `Configuration`.
- Produces: `createProjection(region, plot)`, `colorForFlux(value, domain)`, `renderMap(container, context): MapController`, and `MapController.setConfiguration(configuration)`/`destroy()`.

- [ ] **Step 1: Write failing projection, blank-color, layer-order, and inspection tests**

Add tests proving:

```ts
expect(projection.x(-100)).toBe(PLOT.left);
expect(projection.x(20)).toBe(PLOT.left + PLOT.width);
expect(projection.y(20)).toBe(PLOT.top);
expect(projection.y(-70)).toBe(PLOT.top + PLOT.height);
expect(colorForFlux(null, [1, 100])).toBeNull();
expect(colorForFlux(0, [1, 100])).toBeNull();
```

Render a representative configuration into jsdom and assert ordered groups with `data-layer="geography"`, `guides`, `cells`, `selected`, `centroid`, and `inspection`; selected outline count equals `selected_cell_indices.length`; centroid transform uses stored coordinates; coverage-failed rects have no fill; cells have `tabindex` absent.

Simulate pointer activation and ArrowRight/Home/Escape on the single focusable map container and assert the active-cell callback receives the expected canonical tuple.

- [ ] **Step 2: Run map tests and verify they fail**

Run: `cd site && npm test -- src/map`

Expected: FAIL because map modules do not exist.

- [ ] **Step 3: Implement display-only projection and Viridis interpolation**

Keep scientific calculations out of these modules. Projection maps the fixed WGS84 region linearly into the SVG plot. Color uses the current grid's exported positive domain and `Math.log10` only for display normalization. Return `null` for null, non-finite, non-positive, or invalid-domain values.

- [ ] **Step 4: Implement layered SVG rendering**

Build one SVG with a stable viewBox and clipped geography paths. Cells use canonical centers and `grid_deg` to draw exact geographic rectangles. Ordinary cell strokes are subdued; 2-degree strokes are softer. Selected outlines are separate high-contrast rects. The centroid is a cross plus ring with a text alternative. Do not calculate selected membership or centroid.

Update only changed layers when switching configurations that share a grid; replace cell geometry only when the `grid_id` changes.

- [ ] **Step 5: Implement unified pointer/touch/keyboard inspection**

The SVG/map wrapper is the sole focusable map element. Hit-test pointer coordinates through the display projection to the exact canonical cell index. On keyboard focus choose the selected cell nearest the stored centroid using display distance only; Arrow keys move by one row/column in the canonical grid, Home returns to that initial cell, and Escape clears. Invoke one `onActiveCell(cell | null)` callback. Never add per-cell tab stops or pointer-driven live announcements.

- [ ] **Step 6: Run map tests and commit**

```bash
cd site && npm test -- src/map
cd ..
git add site/src/map
git commit -m "feat: render canonical scientific map"
```

### Task 5: Explorer Controls, Fail-Closed Lifecycle, and Canonical Readouts

**Files:**
- Create: `site/src/ui/controls.ts`
- Create: `site/src/ui/controls.test.ts`
- Create: `site/src/ui/readout.ts`
- Create: `site/src/ui/readout.test.ts`
- Create: `site/src/main.ts`
- Create: `site/src/main.test.ts`
- Modify: `site/index.html`

**Interfaces:**
- Consumes: `LoadedData`, `ConfigurationIndex`, `MapController`.
- Produces: `renderControls(root, model): ControlsController`, `renderReadout(root, configuration, activeCell)`, `startApplication(document, fetcher): Promise<AppController>`.

- [ ] **Step 1: Write failing experiment/reset/control/readout tests**

Test that four question-oriented tabs exist; threshold buttons are exactly Top 20/10/5/2/1; channel/satellite controls expose only exported states; time is grouped into cumulative/separate-week optgroups; settings contains exact 5/2 degree and Mean/Median choices.

Test that switching experiments resets to each canonical `initial_values`, valid changes resolve exactly one configuration, and an injected invalid value produces an alert plus reset without rendering stale metrics.

Test prominent readout labels and values: Selected area, Flux-weighted centroid, Selected cells / covered cells, and Coverage warning. Satellite mode must omit peak flux and show `Location/shape only; absolute proton flux is not cross-calibrated between satellites.`

- [ ] **Step 2: Run UI tests and verify they fail**

Run: `cd site && npm test -- src/ui src/main.test.ts`

Expected: FAIL because UI/application modules do not exist.

- [ ] **Step 3: Implement payload-driven controls**

Render real buttons, fieldsets, legends, labels, select, and details elements. Use visitor-facing experiment labels/questions while taking every supported option from the active experiment's payload. The tested dimension is outside `Analysis settings`; threshold/grid/statistic secondary controls are inside. Controls dispatch complete dimension values, never partial arbitrary blobs.

- [ ] **Step 4: Implement canonical and active-cell readouts**

Format area in million km2 with full accessible value, centroid as signed latitude/longitude degrees, and counts as `selected / covered`. Details include cutoff, percentile, ID, period, exact channel, units, coverage rule, and permitted metadata. Active-cell output includes lat/lon, selected statistic/units, sample count, coverage state, and selected state.

Add one polite configuration status and one polite committed active-cell status. Pointer hover updates visible text but not the live region.

- [ ] **Step 5: Implement fail-closed application orchestration and canonical URL state**

`startApplication` loads/validates data, builds indexes, accepts only an exact query ID, initializes the map/controls/readout, and coordinates changes. Any resolution failure clears stale map/readout, surfaces a development-visible `role="alert"`, resets to the active experiment default, and replaces the URL with that canonical ID. Successful interactions replace the query without adding browser history entries.

- [ ] **Step 6: Run UI/application tests and build**

```bash
cd site
npm test
npm run build
```

Expected: exact state/reset/readout tests pass; no TypeScript errors.

- [ ] **Step 7: Commit the functional explorer**

```bash
git add site/index.html site/src/ui site/src/main.ts site/src/main.test.ts
git commit -m "feat: add fail-closed public explorer"
```

### Task 6: Public Research Narrative, Magnetic Evidence, and Responsive Visual Design

**Files:**
- Create: `site/src/ui/content.ts`
- Create: `site/src/ui/content.test.ts`
- Create: `site/src/styles.css`
- Modify: `site/index.html`
- Modify: `site/src/main.ts`

**Interfaces:**
- Consumes: fixed approved public copy, CP5C payload, and `AppController.showConfiguration(id)`.
- Produces: `renderCp5cEvidence(root, cp5c)`, `bindFindingActions(root, app)`, and complete responsive page presentation.

- [ ] **Step 1: Write failing public-copy, CP5C, and findings-action tests**

Assert exact presence of the eyebrow, headline, immediate caveat, 386 km threshold result, blank-cell explanation, four findings, magnetic lead, method pipeline, reproducibility links, and eight limitations.

Test CP5C output includes `CONSISTENT`, 5/5 low-Btot, 5/5 Btot dominance, five satellites, per-satellite Btot/L/MLT separations, 100% below q25, 11.7–12.1% capture range, and NOAA-15 MLT nuance.

Test threshold finding actions call `showConfiguration` with the canonical top20 and top1 principal IDs and return focus to the explorer.

- [ ] **Step 2: Run content tests and verify they fail**

Run: `cd site && npm test -- src/ui/content.test.ts`

Expected: FAIL because the narrative and CP5C renderer are incomplete.

- [ ] **Step 3: Complete semantic page content in the required order**

Use header/nav, main, named sections, figures/figcaptions, headings, paragraphs, lists, details, and footer. Copy the approved numerical claims from the current canonical record; do not calculate them in TypeScript. Link GitHub and repository-relative documents through GitHub blob URLs so deployed links resolve.

The method pipeline is a semantic ordered list with visible connectors. Reproducibility and limitations stay concise. The hero and explorer share one composition so the map begins in the first desktop viewport.

- [ ] **Step 4: Render fixed CP5C evidence without a magnetic map**

Create an accessible compact grouped bar/SVG or semantic table in which Btot is visually dominant but exact Btot/L/MLT values remain readable. Add the five within-satellite low-Btot capture values. State modeled/descriptive/non-causal framing beside the figure.

- [ ] **Step 5: Implement the modern scientific design system**

Use CSS custom properties for warm off-white background, near-white explorer, near-black text, subdued borders/support text, and one restrained interface accent. Use a readable system sans stack and monospace only for IDs/variables. Keep radii 6–10 px, minimal shadows, no gradients/glass/neon/globe/stock imagery.

Desktop: explorer map/rail approximately 2:1 within a maximum 1280 px content width. Tablet: map first and settings/readout below. Phone: one column, focal control immediately after the question, collapsed settings, compact metric grid, no horizontal page overflow. Add visible focus, practical touch targets, `scroll-margin`, and a reduced-motion media query that removes transitions.

- [ ] **Step 6: Run tests/build and perform initial rendered inspection**

```bash
cd site
npm test
npm run build
npm run preview
```

Inspect the local preview at 1440, 768, and 375 px. Confirm the map is the main object, caveat is immediately visible, and no unsupported/forbidden claims appear.

- [ ] **Step 7: Commit public content and design**

```bash
git add site/index.html site/src/ui/content.ts site/src/ui/content.test.ts site/src/styles.css site/src/main.ts
git commit -m "feat: present public research narrative"
```

### Task 7: Full-State Browser, Responsive, and Accessibility Tests

**Files:**
- Create: `site/playwright.config.ts`
- Create: `site/e2e/explorer.spec.ts`
- Create: `site/e2e/responsive-accessibility.spec.ts`
- Modify: `site/package.json`
- Modify: `site/package-lock.json`

**Interfaces:**
- Consumes: production Vite preview and tracked scientific JSON.
- Produces: browser proof that all 340 states render without console errors and the page remains operable/accessibility-minded at required widths.

- [ ] **Step 1: Write the failing 340-state browser traversal**

Load `/data/viewer_data.json` in the test, then for every configuration navigate to `/?config=<id>`. Assert:

```ts
await expect(page.locator("[data-config-id]")).toHaveAttribute("data-config-id", configuration.id);
await expect(page.locator('[data-layer="selected"] rect')).toHaveCount(configuration.selected_cell_indices.length);
await expect(page.getByTestId("selected-cells")).toContainText(String(configuration.metrics.selected_cells));
await expect(page.getByTestId("covered-cells")).toContainText(String(configuration.metrics.covered_cells));
await expect(page.getByTestId("centroid")).toContainText(configuration.metrics.centroid_lat.toFixed(2));
```

Collect `pageerror` and console error events and require zero. Add representative assertions spanning both grids, both statistics, all thresholds, all channels, all windows, and all satellites.

- [ ] **Step 2: Write failing responsive/accessibility browser tests**

For 375, 768, and 1440 widths assert `document.documentElement.scrollWidth <= innerWidth`, map and focal controls are visible, and controls work. Use Playwright touchscreen context to tap a cell and assert active readout updates. Focus the map and exercise ArrowRight/Home/Escape. Emulate reduced motion and assert transition duration is zero.

Run axe and fail on serious/critical violations:

```ts
const results = await new AxeBuilder({page}).analyze();
expect(results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""))).toEqual([]);
```

- [ ] **Step 3: Run Playwright and verify tests expose remaining gaps**

Run:

```bash
cd site
npx playwright install chromium
npm run test:e2e
```

Expected: initial failures identify any missing selectors, state synchronization, overflow, touch, keyboard, or accessibility behavior.

- [ ] **Step 4: Make the minimal production corrections required by the browser tests**

Add these stable hooks: `data-config-id` on the explorer root; `data-testid="selected-cells"`,
`covered-cells`, and `centroid` on the corresponding readout values; and the existing `data-layer`
attributes on SVG groups. Correct rendering/state synchronization, tighten responsive CSS, and fix
semantic names, contrast, and focus behavior. Do not weaken canonical assertions or accessibility
rules to make tests pass.

- [ ] **Step 5: Run the complete frontend verification suite**

```bash
cd site
npm test
npm run build
npm run test:e2e
```

Expected: unit tests, production build, all 340 states, responsive widths, touch/keyboard, reduced-motion, and axe checks pass.

- [ ] **Step 6: Commit browser verification**

```bash
git add site/playwright.config.ts site/e2e site/package.json site/package-lock.json site/src site/index.html
git commit -m "test: verify all public explorer states"
```

### Task 8: Deployment, Documentation, Copy Audit, and Complete Regression Verification

**Files:**
- Create: `vercel.json`
- Modify: `README.md`
- Modify: `docs/REPRODUCIBILITY_CHECKLIST.md`
- Modify: `scripts/validate_site_outputs.py`
- Modify: `tests/test_validate_site_outputs.py`

**Interfaces:**
- Consumes: completed static site and all existing validators.
- Produces: generic/Vercel static build instructions, broken-link/static-copy checks, and a complete evidence-backed release checklist.

- [ ] **Step 1: Add failing static-contract and forbidden-copy tests**

Extend site validation tests to require semantic landmarks/section IDs, local data paths, no remote map/runtime dependencies, and production links. Add a case-insensitive forbidden-copy scan for definitive boundary/true center/discovery/dose/health risk/danger zone/safety recommendation/causal proof/equal-to-field-minimum wording, with an explicit allowlist only for visible negated caveats such as `not a definitive SAA boundary`.

Add a test that every local fragment link resolves to an element ID and every configured repository/document URL has a non-empty HTTPS href.

- [ ] **Step 2: Run validator tests and verify they fail**

Run: `.venv/bin/python -m unittest tests.test_validate_site_outputs -v`

Expected: FAIL until deployment/static-copy contracts and document links are complete.

- [ ] **Step 3: Add static deployment configuration and public-site documentation**

Create root `vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "npm --prefix site ci && npm --prefix site run build",
  "outputDirectory": "site/dist",
  "framework": "vite"
}
```

Update README with `npm --prefix site ci`, `npm --prefix site run dev`, `npm --prefix site run build`, and site export/validation commands. Update reproducibility checklist after the existing viewer steps, explicitly retaining viewer validation and documenting the 340-state Playwright run.

- [ ] **Step 4: Complete site static/copy validation**

Make `scripts/validate_site_outputs.py` check JSON authority, geography schema/region, required site files, no forbidden frameworks/map providers, expected scientific caveats, local fragment links, and the exact 340-state total. Keep scientific float/discrete validation delegated to the independent canonical checks built in Task 1.

- [ ] **Step 5: Run the full Python and checkpoint validation suite**

Run:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/validate_processed_sample.py
.venv/bin/python scripts/validate_cp3_outputs.py
.venv/bin/python scripts/validate_cp4a_outputs.py
.venv/bin/python scripts/validate_cp4b_outputs.py
.venv/bin/python scripts/validate_cp4c_outputs.py
.venv/bin/python scripts/validate_cp4d_outputs.py
.venv/bin/python scripts/validate_cp4e_outputs.py
.venv/bin/python scripts/validate_cp4f_outputs.py
.venv/bin/python scripts/validate_cp5a_outputs.py
.venv/bin/python scripts/validate_cp5b_outputs.py
.venv/bin/python scripts/validate_cp6a_outputs.py
.venv/bin/python scripts/validate_cp5c_outputs.py
.venv/bin/python scripts/validate_viewer_outputs.py
.venv/bin/python scripts/validate_site_outputs.py
```

Expected: every available unit/contract/checkpoint/viewer/site validator passes without regenerating or altering accepted science. If ignored raw/processed artifacts required by a checkpoint validator are absent, stage the accepted local artifacts or report that validator separately; do not fabricate or silently skip it.

- [ ] **Step 6: Run final frontend, performance, and rendered product checks**

Run:

```bash
npm --prefix site test
npm --prefix site run build
npm --prefix site run test:e2e
du -h site/public/data/viewer_data.json site/public/data/geography.json
du -sh site/dist
git diff --check
```

Use the production preview and inspect actual rendered screenshots at 1440, 768, and 375 px. Answer every final product-test question from the specification. Verify threshold top20/top1 visibly differ, blank cells stay transparent, satellite mode avoids intensity comparison, CP5C is descriptive, and professor-facing method/reproducibility links are quickly reachable.

- [ ] **Step 7: Inspect the final diff and commit deployment/documentation**

Run `git diff main...HEAD --stat`, `git diff main...HEAD -- src/saa notebooks outputs/tables`, and `git status --short`. Confirm no notebook, scientific formula, or canonical output changed.

```bash
git add vercel.json README.md docs/REPRODUCIBILITY_CHECKLIST.md \
  scripts/validate_site_outputs.py tests/test_validate_site_outputs.py
git commit -m "docs: document public site reproduction"
```

### Task 9: Final Review, Push, and Draft Pull Request

**Files:**
- Review only: all branch changes relative to `main`.
- External result: draft pull request to `main`.

**Interfaces:**
- Consumes: verified clean branch and recorded command results.
- Produces: pushed `feat/public-research-site` and a draft PR that is not merged.

- [ ] **Step 1: Invoke verification-before-completion and requesting-code-review workflows**

Re-run the decisive commands fresh: Python tests, existing viewer validation, site validation, frontend tests, production build, and 340-state browser test. Review the diff against the specification and fix any P1/P2 findings before continuing.

- [ ] **Step 2: Confirm branch scope and commit history**

Run:

```bash
git status --short --branch
git log --oneline main..HEAD
git diff --check main...HEAD
git diff --stat main...HEAD
```

Expected: clean feature branch, coherent commits, no whitespace errors.

- [ ] **Step 3: Invoke the GitHub publish workflow and push the feature branch**

Push `feat/public-research-site` without force. Do not merge PR #4 or alter it.

- [ ] **Step 4: Open a draft pull request to `main`**

The PR body must explicitly include:

- new `site/` Vite/TypeScript/static SVG architecture;
- `build_viewer_payload()` as the unchanged scientific authority;
- exactly 340 configurations and 20/60/160/100 experiment counts;
- fail-closed exact configuration lookup and canonical-ID URLs;
- responsive/accessibility/touch/keyboard work;
- Python, frontend, build, Playwright, and validation commands executed;
- Natural Earth/guidance ported from PR #4 while its UI and branch were not merged;
- confirmation that scientific formulas, notebooks, canonical results, and legacy viewer were not altered.

- [ ] **Step 5: Report the draft PR and non-merged status**

Return the PR URL, branch name, decisive verification results, any unavailable checkpoint validators with exact reasons, and the explicit statement that the PR remains draft/unmerged.
