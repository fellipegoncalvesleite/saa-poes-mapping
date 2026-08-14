export type ExperimentName = "threshold" | "channel" | "time" | "satellite";
export type Primitive = string | number;
export type ConfigurationValues = Record<string, Primitive>;
export type CellTuple = [number, number, number | null, number | null, number, boolean];

export interface Region {
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
}

export interface ControlOption { value: Primitive; label: string }
export interface Control { key: string; label: string; options: ControlOption[] }
export interface Metrics {
  flux_cutoff: number;
  covered_cells: number;
  selected_cells: number;
  selected_area_km2: number;
  selected_area_fraction: number;
  centroid_lat: number;
  centroid_lon: number;
  peak_flux: number;
  percentile_cutoff: number;
}
export interface Configuration {
  id: string;
  grid_id: string;
  values: ConfigurationValues;
  metadata: Record<string, string | number | boolean>;
  metrics: Metrics;
  selected_cell_indices: number[];
}
export interface Experiment {
  label: string;
  question: string;
  initial_values: ConfigurationValues;
  dimensions: string[];
  controls: Control[];
  configuration_count: number;
  configurations: Configuration[];
}
export interface Grid {
  grid_deg: number;
  mask_column: string;
  columns: ["lat", "lon", "mean_flux", "median_flux", "sample_count", "covered"];
  cells: CellTuple[];
  color_domains: Record<string, [number, number]>;
  sources: string[];
}
export interface Cp5cSatellite {
  satellite: string;
  btot_separation: number;
  l_igrf_separation: number;
  mlt_separation: number;
  fraction_below_btot_q25: number;
  regional_fraction_to_capture_90pct: number;
  selected_cells: number;
  selected_samples: number;
  low_btot_support: boolean;
  btot_dominance_support: boolean;
}
export interface Cp5cPayload {
  classification: string;
  low_btot_support_count: number;
  btot_dominance_support_count: number;
  reversed_btot_sign_count: number;
  principal_case: string;
  criteria_note: string;
  interpretation: string;
  satellites: Cp5cSatellite[];
}
export interface ViewerPayload {
  schema_version: number;
  region: Region;
  experiments: Record<ExperimentName, Experiment>;
  grids: Record<string, Grid>;
  cp5c: Cp5cPayload;
  global_caveats: string[];
}
export interface GeographyPayload {
  schema_version: number;
  region: Region;
  projection: string;
  coastlines: number[][][];
  borders: number[][][];
  sources: Array<Record<string, string>>;
  license: string;
  terms_url: string;
}
export interface LoadedData { payload: ViewerPayload; geography: GeographyPayload }
export interface ActiveCell {
  index: number;
  lat: number;
  lon: number;
  value: number | null;
  sampleCount: number;
  covered: boolean;
  selected: boolean;
  statistic: string;
  units: string;
}
