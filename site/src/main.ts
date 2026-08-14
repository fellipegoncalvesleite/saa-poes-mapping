import "./styles.css";
import { loadScientificData } from "./data/load";
import type { ActiveCell, Configuration, ConfigurationValues, ExperimentName } from "./data/types";
import { renderMap } from "./map/render";
import { buildConfigurationIndex, canonicalQuery, experimentFromConfiguration, resolveConfiguration, resolveValues } from "./state/configuration";
import { renderControls } from "./ui/controls";
import { renderCp5cEvidence } from "./ui/content";
import { renderReadout } from "./ui/readout";

const controlsRoot = document.querySelector<HTMLElement>("#experiment-controls")!;
const mapRoot = document.querySelector<HTMLElement>("#map-root")!;
const readoutRoot = document.querySelector<HTMLElement>("#readout-root")!;
const explorerState = document.querySelector<HTMLElement>("#explorer-state")!;
const errorRoot = document.querySelector<HTMLElement>("#viewer-error")!;
const configurationStatus = document.querySelector<HTMLElement>("#configuration-status")!;
const cellStatus = document.querySelector<HTMLElement>("#cell-status")!;
function activeCellStatus(cell: ActiveCell | null): string { return cell ? `Cell ${cell.lat.toFixed(1)}, ${cell.lon.toFixed(1)}. ${cell.covered ? "Coverage passed" : "Coverage failed"}. ${cell.selected ? "Selected" : "Not selected"}.` : "Cell inspection cleared."; }

async function start(): Promise<void> {
  try {
    const loaded = await loadScientificData(); const index = buildConfigurationIndex(loaded.payload);
    const requested = new URLSearchParams(location.search).get("config");
    let current = requested ? resolveConfiguration(index, requested) : undefined;
    if (!current) { current = resolveValues(index, loaded.payload, "threshold", loaded.payload.experiments.threshold.initial_values).configuration; if (requested) errorRoot.textContent = "Unsupported configuration reset to the canonical threshold default."; }
    const change = (experiment: ExperimentName, values: ConfigurationValues) => { const result = resolveValues(index, loaded.payload, experiment, values); errorRoot.textContent = result.ok ? "" : "Unsupported state reset to the experiment default."; show(result.configuration); };
    const show = (configuration: Configuration, announce = true) => {
      current = configuration; const experiment = experimentFromConfiguration(configuration); explorerState.dataset.configId = configuration.id;
      history.replaceState(null, "", `${location.pathname}${canonicalQuery(configuration.id)}${location.hash}`);
      renderControls(controlsRoot, loaded.payload, experiment, configuration.values, change);
      renderMap(mapRoot, loaded, configuration, (cell, shouldAnnounce) => { renderReadout(readoutRoot, current!, cell); if (shouldAnnounce) cellStatus.textContent = activeCellStatus(cell); });
      renderReadout(readoutRoot, configuration, null); if (announce) configurationStatus.textContent = `Showing ${configuration.id}`;
    };
    renderCp5cEvidence(document.querySelector<HTMLElement>("#cp5c-root")!, loaded.payload.cp5c);
    document.querySelectorAll<HTMLButtonElement>("[data-show-config]").forEach((button) => button.addEventListener("click", () => { const configuration = resolveConfiguration(index, button.dataset.showConfig!); if (configuration) { show(configuration); document.querySelector("#explorer")?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" }); controlsRoot.querySelector<HTMLElement>('[role="tab"][aria-selected="true"]')?.focus(); } }));
    show(current, false);
  } catch (error) { errorRoot.textContent = `The validated scientific payload could not be loaded. ${error instanceof Error ? error.message : "Unknown error"}`; }
}
void start();
