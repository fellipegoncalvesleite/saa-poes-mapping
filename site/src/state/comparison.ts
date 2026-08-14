import type { Comparison, Configuration, ExperimentName, ViewerPayload } from "../data/types";

export interface ComparisonOption { configuration: Configuration; comparison: Comparison }

function experimentName(configuration: Configuration): ExperimentName {
  return configuration.id.split("|")[0] as ExperimentName;
}

export function comparisonOptions(payload: ViewerPayload, current: Configuration): ComparisonOption[] {
  const name = experimentName(current);
  const experiment = payload.experiments[name];
  const focal = payload.comparisons.find((item) => item.experiment === name)?.focal_dimension;
  if (!focal) return [];
  const byId = new Map(experiment.configurations.map((item) => [item.id, item]));
  const byOtherId = new Map<string, Comparison>();
  for (const comparison of payload.comparisons) {
    if (comparison.experiment !== name) continue;
    if (comparison.configuration_a === current.id) byOtherId.set(comparison.configuration_b, comparison);
    if (comparison.configuration_b === current.id) byOtherId.set(comparison.configuration_a, comparison);
  }
  const optionOrder = experiment.controls.find((control) => control.key === focal)?.options.map((item) => String(item.value)) ?? [];
  return [...byOtherId.entries()].map(([id, comparison]) => ({ configuration: byId.get(id)!, comparison }))
    .filter((item) => item.configuration)
    .sort((a, b) => optionOrder.indexOf(String(a.configuration.values[focal])) - optionOrder.indexOf(String(b.configuration.values[focal])));
}

export function resolveComparison(payload: ViewerPayload, current: Configuration, requestedId: string): ComparisonOption | undefined {
  return comparisonOptions(payload, current).find((item) => item.configuration.id === requestedId);
}
