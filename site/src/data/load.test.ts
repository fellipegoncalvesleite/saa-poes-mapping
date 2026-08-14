import { describe, expect, it } from "vitest";
import payloadJson from "../../public/data/viewer_data.json";
import geographyJson from "../../public/data/geography.json";
import { validateLoadedData } from "./load";

describe("scientific payload validation", () => {
  it("accepts the tracked 340-state authority and matching geography", () => {
    const loaded = validateLoadedData(payloadJson, geographyJson);
    const counts = Object.fromEntries(
      Object.entries(loaded.payload.experiments).map(([name, value]) => [name, value.configuration_count]),
    );
    expect(counts).toEqual({ channel: 60, satellite: 100, threshold: 20, time: 160 });
    expect(Object.keys(loaded.payload.grids)).toHaveLength(26);
    expect(loaded.payload.comparisons).toHaveLength(860);
    expect(loaded.payload.cp5c.classification).toBe("CONSISTENT");
  });

  it("rejects duplicate configuration ids", () => {
    const altered = structuredClone(payloadJson);
    altered.experiments.threshold.configurations[1]!.id = altered.experiments.threshold.configurations[0]!.id;
    expect(() => validateLoadedData(altered, geographyJson)).toThrow(/duplicate configuration id/i);
  });

  it("rejects extra experiments and mismatched canonical ids", () => {
    const extra = structuredClone(payloadJson) as typeof payloadJson & { experiments: Record<string, unknown> };
    extra.experiments.magnetic = extra.experiments.threshold;
    expect(() => validateLoadedData(extra, geographyJson)).toThrow(/experiment set/i);

    const mismatched = structuredClone(payloadJson);
    mismatched.experiments.threshold.configurations[0]!.id = "threshold|grid_deg=5|statistic_used=mean_flux|threshold_label=top999";
    expect(() => validateLoadedData(mismatched, geographyJson)).toThrow(/canonical id/i);
  });

  it("rejects unsupported values and malformed grid cells", () => {
    const unsupported = structuredClone(payloadJson);
    unsupported.experiments.threshold.configurations[0]!.values.grid_deg = 3;
    expect(() => validateLoadedData(unsupported, geographyJson)).toThrow(/unsupported value/i);

    const malformed = structuredClone(payloadJson);
    const gridId = malformed.experiments.threshold.configurations[0]!.grid_id;
    malformed.grids[gridId]!.cells[0]![5] = null as unknown as boolean;
    expect(() => validateLoadedData(malformed, geographyJson)).toThrow(/covered flag/i);
  });

  it("rejects malformed physical geometry and comparison evidence", () => {
    const geometry = structuredClone(payloadJson);
    const gridId = geometry.experiments.threshold.configurations[0]!.grid_id;
    geometry.grids[gridId]!.cells[0]![8] = -1;
    expect(() => validateLoadedData(geometry, geographyJson)).toThrow(/physical geometry/i);

    const comparison = structuredClone(payloadJson);
    comparison.comparisons[0]!.jaccard_overlap = 2;
    expect(() => validateLoadedData(comparison, geographyJson)).toThrow(/comparison metrics/i);

    const unknown = structuredClone(payloadJson);
    unknown.comparisons[0]!.configuration_b = "missing";
    expect(() => validateLoadedData(unknown, geographyJson)).toThrow(/comparison configuration/i);
  });

  it("rejects geography with a different region", () => {
    const altered = structuredClone(geographyJson);
    altered.region.lon_min = -99;
    expect(() => validateLoadedData(payloadJson, altered)).toThrow(/geography region/i);
  });
});
