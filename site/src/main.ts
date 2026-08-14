import "./styles.css";
import { loadScientificData } from "./data/load";
import type { ActiveCell, Configuration, ConfigurationValues, ExperimentName } from "./data/types";
import { renderMap } from "./map/render";
import { buildConfigurationIndex, canonicalQuery, experimentFromConfiguration, resolveConfiguration, resolveValues } from "./state/configuration";
import { renderControls } from "./ui/controls";
import { renderCp5cEvidence } from "./ui/content";
import { renderReadout } from "./ui/readout";
import { resolveComparison } from "./state/comparison";
import { renderComparisonControls, renderComparisonSummary } from "./ui/comparison";

const controlsRoot = document.querySelector<HTMLElement>("#experiment-controls")!;
const mapRoot = document.querySelector<HTMLElement>("#map-root")!;
const readoutRoot = document.querySelector<HTMLElement>("#readout-root")!;
const explorerState = document.querySelector<HTMLElement>("#explorer-state")!;
const errorRoot = document.querySelector<HTMLElement>("#viewer-error")!;
const configurationStatus = document.querySelector<HTMLElement>("#configuration-status")!;
const cellStatus = document.querySelector<HTMLElement>("#cell-status")!;
const comparisonControls = document.querySelector<HTMLElement>("#comparison-controls")!;
const comparisonState = document.querySelector<HTMLElement>("#comparison-state")!;
const comparisonMapA = document.querySelector<HTMLElement>("#comparison-map-a")!;
const comparisonMapB = document.querySelector<HTMLElement>("#comparison-map-b")!;
const comparisonSummary = document.querySelector<HTMLElement>("#comparison-summary")!;
function activeCellStatus(cell: ActiveCell | null): string { return cell ? `Cell ${cell.lat.toFixed(1)}, ${cell.lon.toFixed(1)}. ${cell.covered ? "Coverage passed" : "Coverage failed"}. ${cell.selected ? "Selected" : "Not selected"}.` : "Cell inspection cleared."; }

async function start(): Promise<void> {
  try {
    const loaded = await loadScientificData(); const index = buildConfigurationIndex(loaded.payload);
    const requested = new URLSearchParams(location.search).get("config");
    const requestedComparison = new URLSearchParams(location.search).get("compare");
    let current = requested ? resolveConfiguration(index, requested) : undefined;
    let compared: Configuration | null = null;
    if (!current) { current = resolveValues(index, loaded.payload, "threshold", loaded.payload.experiments.threshold.initial_values).configuration; if (requested) errorRoot.textContent = "Unsupported configuration reset to the canonical threshold default."; }
    const change = (experiment: ExperimentName, values: ConfigurationValues) => { const result = resolveValues(index, loaded.payload, experiment, values); errorRoot.textContent = result.ok ? "" : "Unsupported state reset to the experiment default."; show(result.configuration); };
    const show = (configuration: Configuration, announce = true) => {
      current = configuration; const experiment = experimentFromConfiguration(configuration); explorerState.dataset.configId = configuration.id;
      explorerState.setAttribute("aria-labelledby", `experiment-${experiment}-tab`);
      if (compared && !resolveComparison(loaded.payload, configuration, compared.id)) compared = null;
      const params = new URLSearchParams(canonicalQuery(configuration.id).slice(1)); if (compared) params.set("compare", compared.id);
      history.replaceState(null, "", `${location.pathname}?${params.toString()}${location.hash}`);
      renderControls(controlsRoot, loaded.payload, experiment, configuration.values, change);
      renderComparisonControls(comparisonControls, loaded.payload, configuration, compared?.id ?? null, (id) => {
        compared = id ? resolveComparison(loaded.payload, current!, id)?.configuration ?? null : null; show(current!);
      });
      explorerState.hidden = Boolean(compared); comparisonState.hidden = !compared;
      if (compared) {
        const option = resolveComparison(loaded.payload, configuration, compared.id)!;
        const mapA = renderMap(comparisonMapA, loaded, configuration, (cell, shouldAnnounce) => { if (shouldAnnounce) cellStatus.textContent = `Map A. ${activeCellStatus(cell)}`; });
        const mapB = renderMap(comparisonMapB, loaded, compared, (cell, shouldAnnounce) => { if (shouldAnnounce) cellStatus.textContent = `Map B. ${activeCellStatus(cell)}`; });
        mapA.setAttribute("aria-label", `Map A. ${mapA.getAttribute("aria-label")}`); mapB.setAttribute("aria-label", `Map B. ${mapB.getAttribute("aria-label")}`);
        document.querySelector("#comparison-a-label")!.textContent = `Map A · ${String(configuration.values[option.comparison.focal_dimension])}`;
        document.querySelector("#comparison-b-label")!.textContent = `Map B · ${String(compared.values[option.comparison.focal_dimension])}`;
        renderComparisonSummary(comparisonSummary, option.comparison, configuration, compared);
      } else {
        renderMap(mapRoot, loaded, configuration, (cell, shouldAnnounce) => { renderReadout(readoutRoot, current!, cell); if (shouldAnnounce) cellStatus.textContent = activeCellStatus(cell); });
        renderReadout(readoutRoot, configuration, null);
      }
      if (announce) configurationStatus.textContent = compared ? `Comparing ${configuration.id} with ${compared.id}` : `Showing ${configuration.id}`;
    };
    renderCp5cEvidence(document.querySelector<HTMLElement>("#cp5c-root")!, loaded.payload.cp5c);
    document.querySelectorAll<HTMLButtonElement>("[data-show-config]").forEach((button) => button.addEventListener("click", () => { const configuration = resolveConfiguration(index, button.dataset.showConfig!); if (configuration) { show(configuration); document.querySelector("#explorer")?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); controlsRoot.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')?.focus(); } }));
    if (requestedComparison) compared = resolveComparison(loaded.payload, current, requestedComparison)?.configuration ?? null;
    if (requestedComparison && !compared) errorRoot.textContent = "Unsupported comparison ignored.";
    show(current, false);
  } catch (error) { errorRoot.textContent = `The validated scientific payload could not be loaded. ${error instanceof Error ? error.message : "Unknown error"}`; }
}
void start();
