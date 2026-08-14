import { describe, expect, it } from "vitest";
import payloadJson from "../../public/data/viewer_data.json";
import geographyJson from "../../public/data/geography.json";
import { validateLoadedData } from "../data/load";
import {
  buildConfigurationIndex,
  canonicalQuery,
  resolveConfiguration,
  resolveValues,
  stableConfigurationId,
} from "./configuration";

const { payload } = validateLoadedData(payloadJson, geographyJson);

describe("canonical configuration state", () => {
  it("resolves all 340 canonical ids exactly once", () => {
    const index = buildConfigurationIndex(payload);
    const configurations = Object.values(payload.experiments).flatMap((item) => item.configurations);
    expect(configurations).toHaveLength(340);
    for (const configuration of configurations) {
      expect(resolveConfiguration(index, configuration.id)).toBe(configuration);
      expect(stableConfigurationId(configuration.id.split("|")[0]!, configuration.values)).toBe(configuration.id);
    }
  });

  it("fails closed to the active experiment default", () => {
    const index = buildConfigurationIndex(payload);
    const result = resolveValues(index, payload, "threshold", {
      grid_deg: 3,
      statistic_used: "mean_flux",
      threshold_label: "top10",
    });
    expect(result.ok).toBe(false);
    expect(result.configuration.values).toEqual(payload.experiments.threshold.initial_values);
  });

  it("encodes only the stable canonical id in the query", () => {
    const id = payload.experiments.threshold.configurations[0]!.id;
    expect(canonicalQuery(id)).toBe(`?config=${encodeURIComponent(id)}`);
  });
});
