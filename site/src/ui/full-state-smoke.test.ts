import { describe, expect, it } from "vitest";
import payloadJson from "../../public/data/viewer_data.json";
import geographyJson from "../../public/data/geography.json";
import { validateLoadedData } from "../data/load";
import { renderMap } from "../map/render";
import { renderReadout } from "./readout";

const loaded = validateLoadedData(payloadJson, geographyJson);

describe("full exported-state runtime smoke test", () => {
  it("renders the map and canonical readout for all 340 configurations", () => {
    const mapHost = document.createElement("div");
    const readoutHost = document.createElement("aside");
    const configurations = Object.values(loaded.payload.experiments).flatMap((experiment) => experiment.configurations);

    expect(configurations).toHaveLength(340);
    for (const configuration of configurations) {
      renderMap(mapHost, loaded, configuration, () => undefined);
      renderReadout(readoutHost, configuration, null);

      expect(mapHost.querySelectorAll(".map-cell.is-selected")).toHaveLength(configuration.selected_cell_indices.length);
      expect(mapHost.querySelector('[data-layer="centroid"]')?.getAttribute("data-lat")).toBe(String(configuration.metrics.centroid_lat));
      expect(readoutHost.querySelector('[data-testid="selected-cells"]')?.textContent).toBe(String(configuration.metrics.selected_cells));
    }
  }, 30_000);
});
