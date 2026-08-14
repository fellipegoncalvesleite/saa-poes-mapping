import type { Configuration, ConfigurationValues, ExperimentName, ViewerPayload } from "../data/types";

export interface ConfigurationIndex {
  byId: Map<string, Configuration>;
}

export function stableConfigurationId(experiment: string, values: ConfigurationValues): string {
  return [experiment, ...Object.keys(values).sort().map((key) => `${key}=${String(values[key])}`)].join("|");
}

export function buildConfigurationIndex(payload: ViewerPayload): ConfigurationIndex {
  const byId = new Map<string, Configuration>();
  for (const experiment of Object.values(payload.experiments)) {
    for (const configuration of experiment.configurations) byId.set(configuration.id, configuration);
  }
  return { byId };
}

export function resolveConfiguration(index: ConfigurationIndex, id: string): Configuration | undefined {
  return index.byId.get(id);
}

export function resolveValues(
  index: ConfigurationIndex,
  payload: ViewerPayload,
  experiment: ExperimentName,
  values: ConfigurationValues,
): { ok: boolean; configuration: Configuration } {
  const direct = resolveConfiguration(index, stableConfigurationId(experiment, values));
  if (direct) return { ok: true, configuration: direct };
  const fallbackValues = payload.experiments[experiment].initial_values;
  const fallback = resolveConfiguration(index, stableConfigurationId(experiment, fallbackValues));
  if (!fallback) throw new Error(`Canonical default is missing for ${experiment}`);
  return { ok: false, configuration: fallback };
}

export function canonicalQuery(id: string): string {
  return `?config=${encodeURIComponent(id)}`;
}

export function experimentFromConfiguration(configuration: Configuration): ExperimentName {
  return configuration.id.split("|")[0] as ExperimentName;
}
