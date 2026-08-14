import type { ActiveCell, Configuration, Grid, LoadedData, Region } from "../data/types";
import { colorForFlux, viridisAt } from "./colors";
import { createProjection } from "./projection";

const NS = "http://www.w3.org/2000/svg";
const VIEW = { width: 940, height: 560 };
const PLOT = { left: 58, top: 24, width: 820, height: 500 };
export const DISPLAY_REGION: Region = { lat_min: -50, lat_max: 5, lon_min: -95, lon_max: 10 };
const SCALE_BAR = { distanceKm: 500, referenceLat: -25 };
let mapSequence = 0;

export interface MapRenderOptions { centroidLabel?: string }

function svg(name: string, attributes: Record<string, string | number> = {}): SVGElement {
  const element = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  return element;
}

function pathFor(lines: number[][][], x: (value: number) => number, y: (value: number) => number): string {
  return lines.map((line) => line.map((point, index) => `${index ? "L" : "M"}${x(point[0]!).toFixed(2)} ${y(point[1]!).toFixed(2)}`).join(" ")).join(" ");
}

function selectedPerimeterPath(grid: Grid, selected: Set<number>, x: (value: number) => number, y: (value: number) => number): string {
  const edges = new Map<string, [[number, number], [number, number]]>();
  const toggle = (a: [number, number], b: [number, number]) => {
    const key = [a, b].map((point) => point.join(",")).sort().join("|");
    if (edges.has(key)) edges.delete(key); else edges.set(key, [a, b]);
  };
  selected.forEach((index) => {
    const cell = grid.cells[index];
    if (!cell) return;
    const [lat, lon] = cell;
    const west = lon - grid.grid_deg / 2; const east = lon + grid.grid_deg / 2;
    const south = lat - grid.grid_deg / 2; const north = lat + grid.grid_deg / 2;
    toggle([west, north], [east, north]);
    toggle([east, north], [east, south]);
    toggle([east, south], [west, south]);
    toggle([west, south], [west, north]);
  });
  return [...edges.values()].map(([a, b]) => `M${x(a[0]).toFixed(2)} ${y(a[1]).toFixed(2)}L${x(b[0]).toFixed(2)} ${y(b[1]).toFixed(2)}`).join(" ");
}

export function renderMap(
  host: HTMLElement,
  loaded: LoadedData,
  configuration: Configuration,
  onActiveCell: (cell: ActiveCell | null, announce?: boolean) => void,
  options: MapRenderOptions = {},
): SVGSVGElement {
  host.replaceChildren();
  const { payload, geography } = loaded;
  const grid = payload.grids[configuration.grid_id]!;
  const projection = createProjection(DISPLAY_REGION, PLOT);
  const selected = new Set(configuration.selected_cell_indices);
  const statistic = String(configuration.values.statistic_used);
  const valueIndex = grid.columns.indexOf(statistic as "mean_flux" | "median_flux");
  const domain = grid.color_domains[statistic]!;
  const units = String(configuration.metadata.flux_units);
  const map = svg("svg", {
    viewBox: `0 0 ${VIEW.width} ${VIEW.height}`,
    role: "img",
    tabindex: 0,
    "data-display-region": "-50,5,-95,10",
    "aria-label": "Geographic proton-flux grid. Use arrow keys to inspect cells; Home returns near the centroid; Escape clears inspection.",
  }) as SVGSVGElement;
  const clipId = `scientific-plot-clip-${++mapSequence}`;

  const definitions = svg("defs");
  const plotClip = svg("clipPath", { id: clipId });
  plotClip.append(svg("rect", { x: PLOT.left, y: PLOT.top, width: PLOT.width, height: PLOT.height }));
  definitions.append(plotClip);
  map.append(definitions);

  const geographyLayer = svg("g", { "data-layer": "geography", "aria-hidden": "true", "clip-path": `url(#${clipId})` });
  geographyLayer.append(svg("path", { d: pathFor(geography.borders, projection.x, projection.y), class: "map-border" }));
  geographyLayer.append(svg("path", { d: pathFor(geography.coastlines, projection.x, projection.y), class: "map-coast" }));
  map.append(geographyLayer);

  const guides = svg("g", { "data-layer": "guides", "aria-hidden": "true", "clip-path": `url(#${clipId})` });
  for (let lon = -80; lon <= DISPLAY_REGION.lon_max; lon += 20) {
    guides.append(svg("line", { x1: projection.x(lon), x2: projection.x(lon), y1: PLOT.top, y2: PLOT.top + PLOT.height, class: "map-guide" }));
  }
  for (let lat = DISPLAY_REGION.lat_min; lat <= DISPLAY_REGION.lat_max; lat += 10) {
    guides.append(svg("line", { x1: PLOT.left, x2: PLOT.left + PLOT.width, y1: projection.y(lat), y2: projection.y(lat), class: "map-guide" }));
  }
  map.append(guides);

  const cellsLayer = svg("g", { "data-layer": "cells", "clip-path": `url(#${clipId})` });
  const selectedLayer = svg("g", { "data-layer": "selected", "aria-label": "Selected footprint cells", "clip-path": `url(#${clipId})` });
  const width = (grid.grid_deg / (DISPLAY_REGION.lon_max - DISPLAY_REGION.lon_min)) * PLOT.width;
  const height = (grid.grid_deg / (DISPLAY_REGION.lat_max - DISPLAY_REGION.lat_min)) * PLOT.height;
  const active = svg("rect", { class: "active-cell", visibility: "hidden", "pointer-events": "none" });
  let activeIndex: number | null = null;

  const inspect = (index: number, announce = false) => {
    const cell = grid.cells[index];
    if (!cell) return;
    activeIndex = index;
    active.setAttribute("x", String(projection.x(cell[1] - grid.grid_deg / 2)));
    active.setAttribute("y", String(projection.y(cell[0] + grid.grid_deg / 2)));
    active.setAttribute("width", String(width));
    active.setAttribute("height", String(height));
    active.setAttribute("visibility", "visible");
    onActiveCell({
      index,
      lat: cell[0],
      lon: cell[1],
      value: cell[valueIndex] as number | null,
      sampleCount: cell[4],
      covered: cell[5],
      selected: selected.has(index),
      statistic,
      units,
      northSouthKm: cell[6],
      eastWestKm: cell[7],
      areaKm2: cell[8],
    }, announce);
  };

  grid.cells.forEach((cell, index) => {
    const fill = colorForFlux(cell[valueIndex] as number | null, domain);
    const isSelected = selected.has(index);
    const rect = svg("rect", {
      x: projection.x(cell[1] - grid.grid_deg / 2),
      y: projection.y(cell[0] + grid.grid_deg / 2),
      width,
      height,
      class: `map-cell ${grid.grid_deg === 2 ? "map-cell-fine " : ""}${isSelected ? "is-selected" : "is-context"}`,
      "data-cell-index": index,
      fill: fill ?? "transparent",
      "fill-opacity": fill ? 0.86 : 0,
    });
    rect.addEventListener("pointermove", () => inspect(index));
    rect.addEventListener("pointerdown", () => inspect(index, true));
    cellsLayer.append(rect);
  });
  const perimeter = selectedPerimeterPath(grid, selected, projection.x, projection.y);
  selectedLayer.setAttribute("data-selected-cells", String(selected.size));
  selectedLayer.append(
    svg("path", { d: perimeter, class: "selected-footprint-halo" }),
    svg("path", { d: perimeter, class: "selected-footprint-boundary" }),
  );
  map.append(cellsLayer, selectedLayer);

  const centroid = svg("g", {
    "data-layer": "centroid",
    "data-lat": configuration.metrics.centroid_lat,
    "data-lon": configuration.metrics.centroid_lon,
    "aria-label": "Stored flux-weighted centroid",
  });
  const cx = projection.x(configuration.metrics.centroid_lon);
  const cy = projection.y(configuration.metrics.centroid_lat);
  centroid.append(svg("circle", { cx, cy, r: 8, class: "centroid-ring" }));
  centroid.append(svg("path", { d: `M${cx - 7} ${cy - 7}L${cx + 7} ${cy + 7}M${cx - 7} ${cy + 7}L${cx + 7} ${cy - 7}`, class: "centroid-cross" }));
  centroid.append(svg("line", { x1: cx + 8, y1: cy - 8, x2: cx + 22, y2: cy - 25, class: "centroid-leader" }));
  centroid.append(svg("rect", { x: cx + 18, y: cy - 52, width: 242, height: 38, rx: 3, class: "centroid-label-bg" }));
  const centroidLabel = svg("text", { x: cx + 30, y: cy - 26, class: "centroid-label" });
  centroidLabel.textContent = options.centroidLabel ?? "Flux-weighted centroid";
  centroid.append(centroidLabel);
  map.append(centroid);

  const kmPerLongitudeDegree = 6371 * Math.PI / 180 * Math.cos(Math.abs(SCALE_BAR.referenceLat) * Math.PI / 180);
  const scaleLongitudeDegrees = SCALE_BAR.distanceKm / kmPerLongitudeDegree;
  const scaleWidth = scaleLongitudeDegrees / (DISPLAY_REGION.lon_max - DISPLAY_REGION.lon_min) * PLOT.width;
  const scaleX = PLOT.left + 24; const scaleY = PLOT.top + PLOT.height - 22;
  const scaleBar = svg("g", { "data-layer": "scale-bar", "data-distance-km": SCALE_BAR.distanceKm, "aria-label": "500 kilometre map scale at 25 degrees south" });
  scaleBar.append(
    svg("line", { x1: scaleX, y1: scaleY, x2: scaleX + scaleWidth, y2: scaleY, class: "scale-bar-line" }),
    svg("line", { x1: scaleX, y1: scaleY - 6, x2: scaleX, y2: scaleY + 6, class: "scale-bar-line" }),
    svg("line", { x1: scaleX + scaleWidth, y1: scaleY - 6, x2: scaleX + scaleWidth, y2: scaleY + 6, class: "scale-bar-line" }),
  );
  const scaleLabel = svg("text", { x: scaleX, y: scaleY - 11, class: "scale-bar-label" });
  scaleLabel.textContent = "500 km at 25°S"; scaleBar.append(scaleLabel); map.append(scaleBar);

  const inspection = svg("g", { "data-layer": "inspection", "clip-path": `url(#${clipId})` });
  inspection.append(active);
  map.append(inspection);

  const nearest = grid.cells.reduce((best, cell, index) => {
    if (!selected.has(index)) return best;
    const distance = Math.hypot(cell[0] - configuration.metrics.centroid_lat, cell[1] - configuration.metrics.centroid_lon);
    return distance < best.distance ? { index, distance } : best;
  }, { index: configuration.selected_cell_indices[0] ?? 0, distance: Number.POSITIVE_INFINITY }).index;
  map.addEventListener("focus", () => { if (activeIndex === null) inspect(nearest, true); });
  map.addEventListener("pointerleave", (event) => {
    if (event.pointerType && event.pointerType !== "mouse") return;
    activeIndex = null;
    active.setAttribute("visibility", "hidden");
    onActiveCell(null);
  });
  map.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      activeIndex = null;
      active.setAttribute("visibility", "hidden");
      onActiveCell(null, true);
      return;
    }
    if (event.key === "Home") { event.preventDefault(); inspect(nearest, true); return; }
    const delta = { ArrowLeft: [0, -grid.grid_deg], ArrowRight: [0, grid.grid_deg], ArrowUp: [grid.grid_deg, 0], ArrowDown: [-grid.grid_deg, 0] }[event.key];
    if (!delta) return;
    event.preventDefault();
    const current = grid.cells[activeIndex ?? nearest]!;
    const target = grid.cells.findIndex((cell) => Math.abs(cell[0] - (current[0] + delta[0]!)) < 0.01 && Math.abs(cell[1] - (current[1] + delta[1]!)) < 0.01);
    if (target >= 0) inspect(target, true);
  });
  host.append(map, legend(grid, statistic, configuration));
  return map;
}

function legend(grid: Grid, statistic: string, configuration: Configuration): HTMLElement {
  const element = document.createElement("div");
  element.className = "map-legend";
  element.setAttribute("aria-label", "Log-scaled Viridis color legend");
  const swatches = Array.from({ length: 9 }, (_, index) => `<i style="background:${viridisAt(index / 8)}"></i>`).join("");
  const domain = grid.color_domains[statistic]!;
  const threshold = String(configuration.values.threshold_label).replace(/^top(\d+)$/, "top $1%");
  const representative = grid.cells[configuration.selected_cell_indices.reduce((best, index) => {
    const cell = grid.cells[index]!; const current = grid.cells[best]!;
    const distance = Math.hypot(cell[0] - configuration.metrics.centroid_lat, cell[1] - configuration.metrics.centroid_lon);
    const bestDistance = Math.hypot(current[0] - configuration.metrics.centroid_lat, current[1] - configuration.metrics.centroid_lon);
    return distance < bestDistance ? index : best;
  }, configuration.selected_cell_indices[0] ?? 0)]!;
  element.innerHTML = `<div class="legend-title"><strong>What the map shows</strong><span>${statistic === "mean_flux" ? "Mean" : "Median"} proton flux · logarithmic scale</span></div>
    <div class="legend-row"><span class="legend-label">Lower flux</span><span class="legend-scale"><b>${domain[0].toPrecision(3)}</b>${swatches}<b>${domain[1].toPrecision(3)}</b></span><span class="legend-label">Higher flux</span></div>
    <div class="legend-keys"><span class="legend-key"><i class="legend-footprint"></i><span><strong>Selected ${threshold} footprint</strong><small>Red perimeter; cells outside are dimmed context</small></span></span><span class="legend-key"><i class="legend-centroid">×</i><span><strong>Flux-weighted centroid</strong><small>Stored center of the selected cells</small></span></span><span class="legend-key legend-cell-scale"><i class="legend-cell"></i><span><strong>${grid.grid_deg}° cell near footprint</strong><small>Approx. ${Math.round(representative[6])} km N–S × ${Math.round(representative[7])} km E–W; width changes with latitude</small></span></span></div>`;
  return element;
}
