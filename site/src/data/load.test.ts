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
    expect(loaded.payload.cp5c.classification).toBe("CONSISTENT");
  });

  it("rejects duplicate configuration ids", () => {
    const altered = structuredClone(payloadJson);
    altered.experiments.threshold.configurations[1]!.id = altered.experiments.threshold.configurations[0]!.id;
    expect(() => validateLoadedData(altered, geographyJson)).toThrow(/duplicate configuration id/i);
  });

  it("rejects geography with a different region", () => {
    const altered = structuredClone(geographyJson);
    altered.region.lon_min = -99;
    expect(() => validateLoadedData(payloadJson, altered)).toThrow(/geography region/i);
  });
});
