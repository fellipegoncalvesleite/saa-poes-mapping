import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import payloadJson from "../../public/data/viewer_data.json";
import geographyJson from "../../public/data/geography.json";
import { validateLoadedData } from "../data/load";
import { renderControls } from "./controls";
import { renderCp5cEvidence } from "./content";
import { renderReadout } from "./readout";

const { payload } = validateLoadedData(payloadJson, geographyJson);

describe("public explorer UI", () => {
  it("renders four question-oriented experiments and exact threshold states", () => {
    const root = document.createElement("div");
    renderControls(root, payload, "threshold", payload.experiments.threshold.initial_values, () => undefined);
    expect([...root.querySelectorAll('[role="tab"]')].map((node) => node.textContent)).toEqual([
      "Threshold", "Proton energy", "Time", "Satellite",
    ]);
    expect([...root.querySelectorAll<HTMLElement>('[role="tab"]')].map((node) => node.tabIndex)).toEqual([0, -1, -1, -1]);
    expect(root.querySelector('[role="tab"]')?.getAttribute("aria-controls")).toBe("explorer-state");
    expect([...root.querySelectorAll('[data-control="threshold_label"] button')].map((node) => node.textContent))
      .toEqual(["Top 20%", "Top 10%", "Top 5%", "Top 2%", "Top 1%"]);
    expect(root.querySelector("details")?.textContent).toContain("Analysis settings");
  });

  it("keeps satellite readout location-only and hides peak flux", () => {
    const configuration = payload.experiments.satellite.configurations.find((item) =>
      item.id === "satellite|grid_deg=5|satellite=noaa19|statistic_used=mean_flux|threshold_label=top10")!;
    const root = document.createElement("div");
    renderReadout(root, configuration, null);
    expect(root.textContent).toContain("Selected area");
    expect(root.textContent).toContain("Flux-weighted centroid");
    expect(root.textContent).toContain("Location/shape only");
    expect(root.textContent).not.toContain("Peak flux");
  });

  it("renders the fixed five-satellite CP5C evidence", () => {
    const root = document.createElement("div");
    renderCp5cEvidence(root, payload.cp5c);
    expect(root.textContent).toContain("CONSISTENT");
    expect(root.textContent).toContain("5/5 low-Btot");
    expect(root.querySelectorAll("tbody tr")).toHaveLength(5);
    expect(root.textContent).toContain("NOAA-15");
  });
});

describe("public research copy", () => {
  it("contains the required framing, method, reproducibility, and limitations", () => {
    const path = resolve(process.cwd(), "index.html");
    const html = readFileSync(path, "utf8");
    for (const phrase of [
      "Method sensitivity of particle-defined South Atlantic Anomaly maps",
      "Candidate high-flux footprints; not a definitive SAA boundary.",
      "January 2024",
      "340 validated configurations",
      "Interactive map",
      "Results",
      "How to read this map",
      "Magnetic-field context",
      "NOAA satellite observations",
      "Reproducibility",
      "Limitations",
    ]) expect(html).toContain(phrase);
    expect(html).not.toContain("How much does the mapped South Atlantic Anomaly change when the method changes?");
  });
});
