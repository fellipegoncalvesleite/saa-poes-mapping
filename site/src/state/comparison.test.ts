import { describe, expect, it } from "vitest";
import payloadJson from "../../public/data/viewer_data.json";
import geographyJson from "../../public/data/geography.json";
import { validateLoadedData } from "../data/load";
import { comparisonOptions, resolveComparison } from "./comparison";

const { payload } = validateLoadedData(payloadJson, geographyJson);
const current = payload.experiments.threshold.configurations.find((item) =>
  item.id === "threshold|grid_deg=2|statistic_used=mean_flux|threshold_label=top10")!;

describe("controlled comparison state", () => {
  it("returns only focal alternatives with background settings held constant", () => {
    const options = comparisonOptions(payload, current);
    expect(options).toHaveLength(4);
    expect(options.every((item) => item.configuration.values.grid_deg === 2)).toBe(true);
    expect(options.every((item) => item.configuration.values.statistic_used === "mean_flux")).toBe(true);
    expect(options.map((item) => item.configuration.values.threshold_label)).toEqual(["top20", "top5", "top2", "top1"]);
  });

  it("resolves either orientation and fails closed for incompatible ids", () => {
    const valid = comparisonOptions(payload, current)[0]!.configuration.id;
    expect(resolveComparison(payload, current, valid)?.configuration.id).toBe(valid);
    expect(resolveComparison(payload, current, payload.experiments.channel.configurations[0]!.id)).toBeUndefined();
    expect(resolveComparison(payload, current, "missing")).toBeUndefined();
  });
});
