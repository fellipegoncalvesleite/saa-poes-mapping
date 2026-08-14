import type { Comparison, Configuration, ViewerPayload } from "../data/types";
import { comparisonOptions } from "../state/comparison";

function format(value: number, digits = 0): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function focalLabel(payload: ViewerPayload, configuration: Configuration): string {
  const name = configuration.id.split("|")[0] as keyof ViewerPayload["experiments"];
  const experiment = payload.experiments[name];
  const focal = payload.comparisons.find((item) => item.experiment === name)?.focal_dimension;
  const control = experiment.controls.find((item) => item.key === focal);
  return control?.options.find((item) => String(item.value) === String(configuration.values[focal!]))?.label ?? String(configuration.values[focal!]);
}

export function renderComparisonControls(
  root: HTMLElement,
  payload: ViewerPayload,
  current: Configuration,
  activeComparisonId: string | null,
  onChange: (configurationId: string | null) => void,
): void {
  const options = comparisonOptions(payload, current);
  const active = activeComparisonId ? options.find((item) => item.configuration.id === activeComparisonId) : undefined;
  root.innerHTML = `<div class="comparison-control-row"><button type="button" class="comparison-toggle" aria-pressed="${Boolean(active)}">Compare two maps</button>${active ? `<label>Map B<select aria-label="Map B configuration">${options.map((item) => `<option value="${item.configuration.id}"${item.configuration.id === active.configuration.id ? " selected" : ""}>${focalLabel(payload, item.configuration)}</option>`).join("")}</select></label>` : ""}</div>`;
  root.querySelector<HTMLButtonElement>("button")!.addEventListener("click", () => onChange(active ? null : options[0]?.configuration.id ?? null));
  root.querySelector<HTMLSelectElement>("select")?.addEventListener("change", (event) => onChange((event.currentTarget as HTMLSelectElement).value));
}

export function renderComparisonSummary(root: HTMLElement, comparison: Comparison, a: Configuration, b: Configuration): void {
  const locationOnly = comparison.experiment === "satellite" || comparison.experiment === "channel";
  root.innerHTML = `<h3>Difference summary</h3><div class="comparison-metrics">
    <div><span>Centroid separation</span><strong>${format(comparison.centroid_distance_km)} km</strong></div>
    <div><span>Selected-area difference</span><strong>${format(comparison.selected_area_difference_km2 / 1e6, 2)} million km²</strong></div>
    <div><span>Area ratio</span><strong>${format(comparison.selected_area_ratio, 2)}×</strong></div>
    <div><span>Footprint overlap</span><strong>${format(comparison.jaccard_overlap * 100, 1)}%</strong><small>area-weighted intersection / union</small></div>
  </div>${locationOnly ? "<p class=\"calibration-note\"><strong>Location and shape only.</strong> Absolute flux values are not compared across these measurements.</p>" : ""}
  <details><summary>Compared configurations</summary><p><strong>Map A:</strong> <code>${a.id}</code></p><p><strong>Map B:</strong> <code>${b.id}</code></p></details>`;
}
