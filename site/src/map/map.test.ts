import { describe, expect, it } from "vitest";
import payloadJson from "../../public/data/viewer_data.json";
import geographyJson from "../../public/data/geography.json";
import { validateLoadedData } from "../data/load";
import { colorForFlux } from "./colors";
import { createProjection } from "./projection";
import { renderMap } from "./render";

const loaded = validateLoadedData(payloadJson, geographyJson);

describe("display-only map rendering", () => {
  it("projects the exact region edges", () => {
    const projection = createProjection(loaded.payload.region, { left: 40, top: 20, width: 720, height: 540 });
    expect(projection.x(-100)).toBe(40);
    expect(projection.x(20)).toBe(760);
    expect(projection.y(20)).toBe(20);
    expect(projection.y(-70)).toBe(560);
  });

  it("keeps missing and non-positive values blank", () => {
    expect(colorForFlux(null, [1, 100])).toBeNull();
    expect(colorForFlux(0, [1, 100])).toBeNull();
    expect(colorForFlux(10, [1, 100])).toMatch(/^rgb\(/);
  });

  it("uses ordered layers, stored selected membership, and stored centroid", () => {
    const configuration = loaded.payload.experiments.threshold.configurations.find(
      (item) => item.id === "threshold|grid_deg=5|statistic_used=mean_flux|threshold_label=top10",
    )!;
    const host = document.createElement("div");
    renderMap(host, loaded, configuration, () => undefined);
    expect(host.querySelector("svg")?.getAttribute("data-display-region")).toBe("-50,5,-95,10");
    expect([...host.querySelectorAll("[data-layer]")].map((item) => item.getAttribute("data-layer")))
      .toEqual(["geography", "guides", "cells", "selected", "centroid", "scale-bar", "inspection"]);
    expect(host.querySelector('[data-layer="geography"]')?.getAttribute("clip-path")).toMatch(/^url\(#scientific-plot-clip-/);
    expect(host.querySelector('[data-layer="cells"]')?.getAttribute("clip-path")).toMatch(/^url\(#scientific-plot-clip-/);
    expect(host.querySelector('[data-layer="selected"]')?.getAttribute("clip-path")).toMatch(/^url\(#scientific-plot-clip-/);
    expect(host.querySelectorAll(".map-cell.is-selected")).toHaveLength(configuration.selected_cell_indices.length);
    expect(host.querySelectorAll('[data-layer="selected"] path')).toHaveLength(2);
    expect(host.querySelector('[data-layer="selected"] rect')).toBeNull();
    expect(host.querySelector('[data-layer="centroid"]')?.getAttribute("data-lat"))
      .toBe(String(configuration.metrics.centroid_lat));
    expect(host.querySelector('[data-layer="centroid"] text')?.textContent).toBe("Flux-weighted centroid");
    expect(host.querySelector(".map-legend")?.textContent).toContain("Selected top 10% footprint");
    expect(host.querySelector(".map-legend")?.textContent).toContain("5° cell");
    expect(host.querySelector(".map-legend")?.textContent).toContain("km N–S");
    expect(host.querySelectorAll("[data-cell-index][tabindex]")).toHaveLength(0);
    expect(host.querySelector('[data-layer="scale-bar"]')?.textContent).toContain("500 km at 25°S");
  });

  it("prints a supplied stored shift next to the centroid", () => {
    const configuration = loaded.payload.experiments.threshold.configurations[0]!;
    const host = document.createElement("div");
    renderMap(host, loaded, configuration, () => undefined, { centroidLabel: "→ 386 km from A" });
    expect(host.querySelector('[data-layer="centroid"] text')?.textContent).toBe("→ 386 km from A");
  });

  it("uses distinct SVG clip identifiers for side-by-side maps", () => {
    const configuration = loaded.payload.experiments.threshold.configurations[0]!;
    const first = document.createElement("div"); const second = document.createElement("div");
    renderMap(first, loaded, configuration, () => undefined);
    renderMap(second, loaded, configuration, () => undefined);
    expect(first.querySelector("clipPath")?.id).not.toBe(second.querySelector("clipPath")?.id);
  });
});
