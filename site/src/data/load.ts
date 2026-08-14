import type { ExperimentName, GeographyPayload, LoadedData, ViewerPayload } from "./types";

const EXPECTED: Record<ExperimentName, number> = {
  threshold: 20,
  channel: 60,
  time: 160,
  satellite: 100,
};

function object(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as Record<string, unknown>;
}

function sameRegion(a: Record<string, unknown>, b: Record<string, unknown>): boolean {
  return ["lat_min", "lat_max", "lon_min", "lon_max"].every((key) => Number(a[key]) === Number(b[key]));
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
  const ids = new Set<string>();
  for (const [name, count] of Object.entries(EXPECTED) as Array<[ExperimentName, number]>) {
    const experiment = object(experiments[name], `${name} experiment`);
    const configurations = experiment.configurations;
    if (!Array.isArray(configurations) || configurations.length !== count || experiment.configuration_count !== count) {
      throw new Error(`${name} configuration count must be ${count}`);
    }
    if (!Array.isArray(experiment.dimensions) || !Array.isArray(experiment.controls)) {
      throw new Error(`${name} dimensions and controls are required`);
    }
    for (const item of configurations) {
      const configuration = object(item, "configuration");
      const id = configuration.id;
      if (typeof id !== "string") throw new Error("Configuration id must be a string");
      if (ids.has(id)) throw new Error(`Duplicate configuration id: ${id}`);
      ids.add(id);
      if (typeof configuration.grid_id !== "string" || !grids[configuration.grid_id]) {
        throw new Error(`Missing grid reference for ${id}`);
      }
      if (!Array.isArray(configuration.selected_cell_indices)) throw new Error(`Selected membership missing for ${id}`);
      const grid = object(grids[configuration.grid_id], "grid");
      const cells = grid.cells;
      if (!Array.isArray(cells)) throw new Error("Grid cells must be an array");
      if (configuration.selected_cell_indices.some((index) => !Number.isInteger(index) || index < 0 || index >= cells.length)) {
        throw new Error(`Selected index out of range for ${id}`);
      }
    }
  }
  const cp5c = object(payloadObject.cp5c, "CP5C");
  if (cp5c.classification !== "CONSISTENT" || !Array.isArray(cp5c.satellites) || cp5c.satellites.length !== 5) {
    throw new Error("CP5C must contain the accepted five-satellite CONSISTENT evidence");
  }
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
