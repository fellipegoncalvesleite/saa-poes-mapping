import type { ActiveCell, Configuration } from "../data/types";

function number(value: number, digits = 1): string { return value.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits }); }
function coordinate(value: number, positive: string, negative: string): string { return `${Math.abs(value).toFixed(2)}°${value >= 0 ? positive : negative}`; }

export function renderReadout(root: HTMLElement, configuration: Configuration, activeCell: ActiveCell | null): void {
  const satelliteMode = configuration.id.startsWith("satellite|");
  const metrics = configuration.metrics; const metadata = configuration.metadata;
  root.innerHTML = `<div class="metric-grid" aria-label="Current canonical metrics">
    <div class="metric"><span>Selected area</span><strong>${number(metrics.selected_area_km2 / 1e6, 2)} million km²</strong></div>
    <div class="metric"><span>Flux-weighted centroid</span><strong data-testid="centroid">${coordinate(metrics.centroid_lat, "N", "S")}, ${coordinate(metrics.centroid_lon, "E", "W")}</strong></div>
    <div class="metric"><span>Selected cells / covered cells</span><strong><span data-testid="selected-cells">${metrics.selected_cells}</span> / <span data-testid="covered-cells">${metrics.covered_cells}</span></strong></div>
    <div class="metric ${metadata.coverage_warning ? "warning" : ""}"><span>Coverage</span><strong>${metadata.coverage_warning || "Coverage requirement met"}</strong></div></div>
    ${satelliteMode ? '<p class="calibration-note"><strong>Location/shape only.</strong> Absolute proton flux is not cross-calibrated between satellites.</p>' : ""}
    <details class="configuration-details"><summary>Configuration details</summary><dl>
    <div><dt>Configuration ID</dt><dd><code>${configuration.id}</code></dd></div><div><dt>Period</dt><dd>${metadata.period}</dd></div><div><dt>Satellite</dt><dd>${metadata.satellite}</dd></div>
    <div><dt>Channel</dt><dd>${metadata.channel_display} <code>${metadata.channel}</code></dd></div><div><dt>Threshold cutoff</dt><dd>${metrics.flux_cutoff.toPrecision(5)} ${metadata.flux_units}</dd></div>
    <div><dt>Percentile</dt><dd>${metrics.percentile_cutoff}th</dd></div><div><dt>Coverage rule</dt><dd>${metadata.coverage_rule}</dd></div>${satelliteMode ? "" : `<div><dt>Peak flux</dt><dd>${metrics.peak_flux.toPrecision(5)} ${metadata.flux_units}</dd></div>`}</dl></details>
    <div class="cell-readout" aria-label="Active map cell"><h4>Active cell</h4>${activeCell ? `<p><strong>${activeCell.lat.toFixed(1)}°, ${activeCell.lon.toFixed(1)}°</strong></p><dl>
    <div><dt>${activeCell.statistic === "mean_flux" ? "Mean" : "Median"} flux</dt><dd>${activeCell.value === null ? "Blank" : `${activeCell.value.toPrecision(5)} ${activeCell.units}`}</dd></div><div><dt>Samples</dt><dd>${activeCell.sampleCount}</dd></div>
    <div><dt>Coverage</dt><dd>${activeCell.covered ? "Passed" : "Failed"}</dd></div><div><dt>Footprint</dt><dd>${activeCell.selected ? "Selected" : "Not selected"}</dd></div></dl>` : "<p>Point, tap, or focus the map and use arrow keys to inspect a cell.</p>"}</div>`;
}
