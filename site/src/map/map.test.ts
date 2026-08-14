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
    expect([...host.querySelectorAll("[data-layer]")].map((item) => item.getAttribute("data-layer")))
      .toEqual(["geography", "guides", "cells", "selected", "centroid", "inspection"]);
    expect(host.querySelector('[data-layer="geography"]')?.getAttribute("clip-path")).toBe("url(#scientific-plot-clip)");
    expect(host.querySelectorAll('[data-layer="selected"] rect')).toHaveLength(configuration.selected_cell_indices.length);
    expect(host.querySelector('[data-layer="centroid"]')?.getAttribute("data-lat"))
      .toBe(String(configuration.metrics.centroid_lat));
    expect(host.querySelectorAll("[data-cell-index][tabindex]")).toHaveLength(0);
  });
});
