import type { ActiveCell, Configuration, Grid, LoadedData } from "../data/types";
import { colorForFlux, viridisAt } from "./colors";
import { createProjection } from "./projection";

const NS = "http://www.w3.org/2000/svg";
const VIEW = { width: 940, height: 660 };
const PLOT = { left: 58, top: 24, width: 780, height: 585 };

function svg(name: string, attributes: Record<string, string | number> = {}): SVGElement {
  const element = document.createElementNS(NS, name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
  return element;
}

function pathFor(lines: number[][][], x: (value: number) => number, y: (value: number) => number): string {
  return lines.map((line) => line.map((point, index) => `${index ? "L" : "M"}${x(point[0]!).toFixed(2)} ${y(point[1]!).toFixed(2)}`).join(" ")).join(" ");
}

export function renderMap(
  host: HTMLElement,
  loaded: LoadedData,
  configuration: Configuration,
  onActiveCell: (cell: ActiveCell | null, announce?: boolean) => void,
): SVGSVGElement {
  host.replaceChildren();
  const { payload, geography } = loaded;
  const grid = payload.grids[configuration.grid_id]!;
  const projection = createProjection(payload.region, PLOT);
  const selected = new Set(configuration.selected_cell_indices);
  const statistic = String(configuration.values.statistic_used);
  const valueIndex = grid.columns.indexOf(statistic as "mean_flux" | "median_flux");
  const domain = grid.color_domains[statistic]!;
  const units = String(configuration.metadata.flux_units);
  const map = svg("svg", {
    viewBox: `0 0 ${VIEW.width} ${VIEW.height}`,
    role: "img",
    tabindex: 0,
    "aria-label": "Geographic proton-flux grid. Use arrow keys to inspect cells; Home returns near the centroid; Escape clears inspection.",
  }) as SVGSVGElement;

  const definitions = svg("defs");
  const plotClip = svg("clipPath", { id: "scientific-plot-clip" });
  plotClip.append(svg("rect", { x: PLOT.left, y: PLOT.top, width: PLOT.width, height: PLOT.height }));
  definitions.append(plotClip);
  map.append(definitions);

  const geographyLayer = svg("g", { "data-layer": "geography", "aria-hidden": "true", "clip-path": "url(#scientific-plot-clip)" });
  geographyLayer.append(svg("path", { d: pathFor(geography.borders, projection.x, projection.y), class: "map-border" }));
  geographyLayer.append(svg("path", { d: pathFor(geography.coastlines, projection.x, projection.y), class: "map-coast" }));
  map.append(geographyLayer);

  const guides = svg("g", { "data-layer": "guides", "aria-hidden": "true" });
  for (let lon = payload.region.lon_min; lon <= payload.region.lon_max; lon += 20) {
    guides.append(svg("line", { x1: projection.x(lon), x2: projection.x(lon), y1: PLOT.top, y2: PLOT.top + PLOT.height, class: "map-guide" }));
  }
  for (let lat = payload.region.lat_min; lat <= payload.region.lat_max; lat += 10) {
    guides.append(svg("line", { x1: PLOT.left, x2: PLOT.left + PLOT.width, y1: projection.y(lat), y2: projection.y(lat), class: "map-guide" }));
  }
  map.append(guides);

  const cellsLayer = svg("g", { "data-layer": "cells" });
  const selectedLayer = svg("g", { "data-layer": "selected", "aria-label": "Selected footprint cells" });
  const width = (grid.grid_deg / (payload.region.lon_max - payload.region.lon_min)) * PLOT.width;
  const height = (grid.grid_deg / (payload.region.lat_max - payload.region.lat_min)) * PLOT.height;
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
    }, announce);
  };

  grid.cells.forEach((cell, index) => {
    const fill = colorForFlux(cell[valueIndex] as number | null, domain);
    const rect = svg("rect", {
      x: projection.x(cell[1] - grid.grid_deg / 2),
      y: projection.y(cell[0] + grid.grid_deg / 2),
      width,
      height,
      class: grid.grid_deg === 2 ? "map-cell map-cell-fine" : "map-cell",
      "data-cell-index": index,
      fill: fill ?? "transparent",
      "fill-opacity": fill ? 0.86 : 0,
    });
    rect.addEventListener("pointermove", () => inspect(index));
    rect.addEventListener("pointerdown", () => inspect(index, true));
    cellsLayer.append(rect);
    if (selected.has(index)) selectedLayer.append(svg("rect", {
      x: projection.x(cell[1] - grid.grid_deg / 2),
      y: projection.y(cell[0] + grid.grid_deg / 2),
      width,
      height,
      class: "selected-cell",
    }));
  });
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
  map.append(centroid);
  const inspection = svg("g", { "data-layer": "inspection" });
  inspection.append(active);
  map.append(inspection);

  const nearest = grid.cells.reduce((best, cell, index) => {
    if (!selected.has(index)) return best;
    const distance = Math.hypot(cell[0] - configuration.metrics.centroid_lat, cell[1] - configuration.metrics.centroid_lon);
    return distance < best.distance ? { index, distance } : best;
  }, { index: configuration.selected_cell_indices[0] ?? 0, distance: Number.POSITIVE_INFINITY }).index;
  map.addEventListener("focus", () => { if (activeIndex === null) inspect(nearest, true); });
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
  host.append(map, legend(grid, statistic));
  return map;
}

function legend(grid: Grid, statistic: string): HTMLElement {
  const element = document.createElement("div");
  element.className = "map-legend";
  element.setAttribute("aria-label", "Log-scaled Viridis color legend");
  const swatches = Array.from({ length: 9 }, (_, index) => `<i style="background:${viridisAt(index / 8)}"></i>`).join("");
  const domain = grid.color_domains[statistic]!;
  element.innerHTML = `<span>${statistic === "mean_flux" ? "Mean" : "Median"} flux · log scale</span><span class="legend-scale"><b>${domain[0].toPrecision(3)}</b>${swatches}<b>${domain[1].toPrecision(3)}</b></span>`;
  return element;
}
