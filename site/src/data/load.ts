import type { ConfigurationValues, ExperimentName, GeographyPayload, LoadedData, ViewerPayload } from "./types";

const EXPECTED: Record<ExperimentName, number> = {
  threshold: 20,
  channel: 60,
  time: 160,
  satellite: 100,
};
const DIMENSIONS: Record<ExperimentName, string[]> = {
  threshold: ["grid_deg", "statistic_used", "threshold_label"],
  channel: ["channel", "grid_deg", "statistic_used", "threshold_label"],
  time: ["window_label", "grid_deg", "statistic_used", "threshold_label"],
  satellite: ["satellite", "grid_deg", "statistic_used", "threshold_label"],
};
const GRID_COLUMNS = ["lat", "lon", "mean_flux", "median_flux", "sample_count", "covered", "north_south_km", "east_west_km", "cell_area_km2"];
const METRICS = ["flux_cutoff", "covered_cells", "selected_cells", "selected_area_km2", "selected_area_fraction", "centroid_lat", "centroid_lon", "peak_flux", "percentile_cutoff"];
const CP5C_SATELLITES = ["metop01", "metop03", "noaa15", "noaa18", "noaa19"];

function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as Record<string, unknown>;
}

function sameRegion(a: Record<string, unknown>, b: Record<string, unknown>): boolean {
  return ["lat_min", "lat_max", "lon_min", "lon_max"].every((key) => Number(a[key]) === Number(b[key]));
}

function exactKeys(value: Record<string, unknown>, expected: string[]): boolean {
  return Object.keys(value).sort().join("|") === [...expected].sort().join("|");
}

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function primitive(value: unknown): value is string | number {
  return typeof value === "string" || finite(value);
}

function canonicalId(experiment: ExperimentName, values: ConfigurationValues): string {
  return [experiment, ...Object.keys(values).sort().map((key) => `${key}=${String(values[key])}`)].join("|");
}

function validateGrid(id: string, input: unknown): number {
  const grid = object(input, `grid ${id}`);
  if (grid.grid_deg !== 2 && grid.grid_deg !== 5) throw new Error(`Unsupported grid resolution for ${id}`);
  if (!Array.isArray(grid.columns) || grid.columns.join("|") !== GRID_COLUMNS.join("|")) throw new Error(`Invalid grid columns for ${id}`);
  const domains = object(grid.color_domains, `color domains for ${id}`);
  for (const statistic of ["mean_flux", "median_flux"]) {
    const domain = domains[statistic];
    const low = Array.isArray(domain) ? domain[0] : undefined;
    const high = Array.isArray(domain) ? domain[1] : undefined;
    if (!Array.isArray(domain) || domain.length !== 2 || !finite(low) || !finite(high) || low <= 0 || low >= high) {
      throw new Error(`Invalid ${statistic} color domain for ${id}`);
    }
  }
  if (!Array.isArray(grid.cells) || grid.cells.length === 0) throw new Error(`Grid cells missing for ${id}`);
  for (const [index, cell] of grid.cells.entries()) {
    if (!Array.isArray(cell) || cell.length !== 9 || !finite(cell[0]) || !finite(cell[1])) throw new Error(`Malformed grid cell ${id}:${index}`);
    if (![cell[2], cell[3]].every((value) => value === null || finite(value))) throw new Error(`Invalid flux value for ${id}:${index}`);
    if (!Number.isInteger(cell[4]) || cell[4] < 0) throw new Error(`Invalid sample count for ${id}:${index}`);
    if (typeof cell[5] !== "boolean") throw new Error(`Invalid covered flag for ${id}:${index}`);
    if (!cell[5] && (cell[2] !== null || cell[3] !== null)) throw new Error(`Coverage-failed flux must be blank for ${id}:${index}`);
    if (![cell[6], cell[7], cell[8]].every((value) => finite(value) && value > 0)) throw new Error(`Invalid physical geometry for ${id}:${index}`);
  }
  return grid.cells.length;
}

function validateCp5c(input: unknown): void {
  const cp5c = object(input, "CP5C");
  if (cp5c.classification !== "CONSISTENT" || cp5c.low_btot_support_count !== 5 || cp5c.btot_dominance_support_count !== 5) {
    throw new Error("CP5C must contain the accepted CONSISTENT 5/5 evidence");
  }
  if (!Array.isArray(cp5c.satellites) || cp5c.satellites.length !== 5) throw new Error("CP5C must contain five satellite rows");
  const names: string[] = [];
  for (const inputRow of cp5c.satellites) {
    const row = object(inputRow, "CP5C satellite row");
    if (typeof row.satellite !== "string") throw new Error("CP5C satellite name is invalid");
    names.push(row.satellite);
    for (const key of ["btot_separation", "l_igrf_separation", "mlt_separation", "fraction_below_btot_q25", "regional_fraction_to_capture_90pct", "selected_cells", "selected_samples"]) {
      if (!finite(row[key])) throw new Error(`CP5C ${key} is invalid`);
    }
    if (row.low_btot_support !== true || row.btot_dominance_support !== true) throw new Error("CP5C support flags must be true");
  }
  if (names.sort().join("|") !== CP5C_SATELLITES.join("|")) throw new Error("CP5C satellite set is invalid");
}

export function validateLoadedData(payloadInput: unknown, geographyInput: unknown): LoadedData {
  const payloadObject = object(payloadInput, "scientific payload");
  const geographyObject = object(geographyInput, "geography");
  if (payloadObject.schema_version !== 1) throw new Error("Unsupported scientific payload schema");
  if (geographyObject.schema_version !== 1) throw new Error("Unsupported geography schema");
  if (!sameRegion(object(payloadObject.region, "scientific region"), object(geographyObject.region, "geography region"))) {
    throw new Error("Geography region differs from scientific payload region");
  }
  const experiments = object(payloadObject.experiments, "experiments");
  const grids = object(payloadObject.grids, "grids");
  if (!exactKeys(experiments, Object.keys(EXPECTED))) throw new Error("Scientific experiment set is invalid");
  const gridLengths = new Map<string, number>();
  for (const [id, grid] of Object.entries(grids)) gridLengths.set(id, validateGrid(id, grid));
  const ids = new Set<string>();
  const configurationsById = new Map<string, { experiment: ExperimentName; values: Record<string, unknown> }>();
  for (const [name, count] of Object.entries(EXPECTED) as Array<[ExperimentName, number]>) {
    const experiment = object(experiments[name], `${name} experiment`);
    const configurations = experiment.configurations;
    if (!Array.isArray(configurations) || configurations.length !== count || experiment.configuration_count !== count) {
      throw new Error(`${name} configuration count must be ${count}`);
    }
    if (!Array.isArray(experiment.dimensions) || experiment.dimensions.join("|") !== DIMENSIONS[name].join("|") || !Array.isArray(experiment.controls)) {
      throw new Error(`${name} dimensions and controls are required`);
    }
    const supported = new Map<string, Set<string>>();
    for (const inputControl of experiment.controls) {
      const control = object(inputControl, `${name} control`);
      if (typeof control.key !== "string" || !DIMENSIONS[name].includes(control.key) || !Array.isArray(control.options) || control.options.length === 0) {
        throw new Error(`${name} control is invalid`);
      }
      const values = new Set<string>();
      for (const inputOption of control.options) {
        const option = object(inputOption, `${name} option`);
        if (!primitive(option.value) || typeof option.label !== "string") throw new Error(`${name} option is invalid`);
        values.add(String(option.value));
      }
      if (values.size !== control.options.length) throw new Error(`${name} control contains duplicate values`);
      supported.set(control.key, values);
    }
    if ([...supported.keys()].sort().join("|") !== [...DIMENSIONS[name]].sort().join("|")) throw new Error(`${name} control set is invalid`);
    const initial = object(experiment.initial_values, `${name} initial values`);
    if (!exactKeys(initial, DIMENSIONS[name]) || DIMENSIONS[name].some((key) => !supported.get(key)!.has(String(initial[key])))) {
      throw new Error(`${name} initial values are unsupported`);
    }
    for (const item of configurations) {
      const configuration = object(item, "configuration");
      const id = configuration.id;
      if (typeof id !== "string") throw new Error("Configuration id must be a string");
      if (ids.has(id)) throw new Error(`Duplicate configuration id: ${id}`);
      ids.add(id);
      const values = object(configuration.values, `values for ${id}`);
      if (!exactKeys(values, DIMENSIONS[name])) throw new Error(`Configuration dimensions are invalid for ${id}`);
      for (const key of DIMENSIONS[name]) {
        if (!primitive(values[key]) || !supported.get(key)!.has(String(values[key]))) throw new Error(`Unsupported value for ${name}.${key}`);
      }
      if (id !== canonicalId(name, values as ConfigurationValues)) throw new Error(`Canonical id does not match values for ${id}`);
      if (typeof configuration.grid_id !== "string" || !gridLengths.has(configuration.grid_id)) {
        throw new Error(`Missing grid reference for ${id}`);
      }
      if (!Array.isArray(configuration.selected_cell_indices)) throw new Error(`Selected membership missing for ${id}`);
      const cellCount = gridLengths.get(configuration.grid_id)!;
      if (new Set(configuration.selected_cell_indices).size !== configuration.selected_cell_indices.length || configuration.selected_cell_indices.some((index) => !Number.isInteger(index) || index < 0 || index >= cellCount)) {
        throw new Error(`Selected index out of range for ${id}`);
      }
      const metrics = object(configuration.metrics, `metrics for ${id}`);
      if (!exactKeys(metrics, METRICS) || METRICS.some((key) => !finite(metrics[key]))) throw new Error(`Canonical metrics are malformed for ${id}`);
      if (Number(metrics.selected_cells) !== configuration.selected_cell_indices.length || Number(metrics.covered_cells) < Number(metrics.selected_cells)) throw new Error(`Canonical counts are inconsistent for ${id}`);
      object(configuration.metadata, `metadata for ${id}`);
      configurationsById.set(id, { experiment: name, values });
    }
  }
  if (!Array.isArray(payloadObject.comparisons) || payloadObject.comparisons.length !== 860) throw new Error("Scientific payload must contain 860 comparisons");
  const comparisonKeys = ["id", "experiment", "focal_dimension", "configuration_a", "configuration_b", "centroid_distance_km", "selected_area_difference_km2", "selected_area_ratio", "intersection_area_km2", "union_area_km2", "jaccard_overlap"];
  const focal: Record<ExperimentName, string> = { threshold: "threshold_label", channel: "channel", time: "window_label", satellite: "satellite" };
  const comparisonIds = new Set<string>();
  for (const input of payloadObject.comparisons) {
    const comparison = object(input, "comparison");
    if (!exactKeys(comparison, comparisonKeys) || typeof comparison.id !== "string" || comparisonIds.has(comparison.id)) throw new Error("Comparison record keys or id are invalid");
    comparisonIds.add(comparison.id);
    if (typeof comparison.configuration_a !== "string" || typeof comparison.configuration_b !== "string") throw new Error("Comparison configuration ids are invalid");
    const a = configurationsById.get(comparison.configuration_a); const b = configurationsById.get(comparison.configuration_b);
    if (!a || !b) throw new Error("Comparison configuration is unknown");
    if (comparison.experiment !== a.experiment || comparison.experiment !== b.experiment || comparison.focal_dimension !== focal[a.experiment]) throw new Error("Comparison configuration scope is invalid");
    const changed = Object.keys(a.values).filter((key) => a.values[key] !== b.values[key]);
    if (changed.length !== 1 || changed[0] !== focal[a.experiment]) throw new Error("Comparison configuration background settings differ");
    const metricValues = [comparison.centroid_distance_km, comparison.selected_area_difference_km2, comparison.selected_area_ratio, comparison.intersection_area_km2, comparison.union_area_km2, comparison.jaccard_overlap];
    if (!metricValues.every(finite) || Number(comparison.centroid_distance_km) < 0 || Number(comparison.selected_area_difference_km2) < 0 || Number(comparison.selected_area_ratio) < 1 || Number(comparison.intersection_area_km2) < 0 || Number(comparison.union_area_km2) <= 0 || Number(comparison.jaccard_overlap) < 0 || Number(comparison.jaccard_overlap) > 1) throw new Error("Comparison metrics are invalid");
  }
  validateCp5c(payloadObject.cp5c);
  if (!Array.isArray(geographyObject.coastlines) || !Array.isArray(geographyObject.borders)) {
    throw new Error("Geography linework is missing");
  }
  return { payload: payloadInput as ViewerPayload, geography: geographyInput as GeographyPayload };
}

export async function loadScientificData(fetcher: typeof fetch = fetch): Promise<LoadedData> {
  const [payloadResponse, geographyResponse] = await Promise.all([
    fetcher("/data/viewer_data.json"),
    fetcher("/data/geography.json"),
  ]);
  if (!payloadResponse.ok || !geographyResponse.ok) throw new Error("Scientific assets failed to load");
  return validateLoadedData(await payloadResponse.json(), await geographyResponse.json());
}
