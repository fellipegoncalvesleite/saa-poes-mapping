import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import payloadJson from "../../public/data/viewer_data.json";
import geographyJson from "../../public/data/geography.json";
import { validateLoadedData } from "../data/load";
import { renderControls } from "./controls";
import { renderCp5cEvidence } from "./content";
import { renderReadout } from "./readout";
import { renderComparisonControls, renderComparisonSummary } from "./comparison";
import { comparisonOptions } from "../state/comparison";

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
    expect(root.querySelector('[data-control="grid_deg"] legend')?.textContent).toBe("Grid resolution");
    expect([...root.querySelectorAll('[data-control="grid_deg"] button')].map((node) => node.textContent)).toEqual(["5°", "2°"]);
    expect(root.querySelector('[data-control="grid_deg"]')?.closest("details")).toBeNull();
    expect(root.querySelector("details")).toBeNull();
    expect(root.querySelector('[data-control="statistic_used"]')?.textContent).toContain("Mean");
    expect(root.querySelector('[data-control="statistic_used"]')?.textContent).toContain("Median");
  });

  it("keeps every applicable method setting explicit", () => {
    const root = document.createElement("div");
    renderControls(root, payload, "time", payload.experiments.time.initial_values, () => undefined);
    expect([...root.querySelectorAll("[data-control]")].map((node) => node.getAttribute("data-control")))
      .toEqual(["window_label", "grid_deg", "statistic_used", "threshold_label"]);
    expect(root.querySelector('[data-control="threshold_label"]')?.textContent).toContain("Top 10%");
  });

  it("preserves the chosen grid resolution when switching experiment", () => {
    const root = document.createElement("div");
    let next: { experiment: string; grid: string | number | undefined } | undefined;
    renderControls(root, payload, "threshold", { ...payload.experiments.threshold.initial_values, grid_deg: 2 }, (experiment, values) => {
      next = { experiment, grid: values.grid_deg };
    });
    root.querySelector<HTMLButtonElement>("#experiment-channel-tab")!.click();
    expect(next).toEqual({ experiment: "channel", grid: 2 });
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

  it("shows the inspected cell's physical dimensions and area", () => {
    const configuration = payload.experiments.threshold.configurations[0]!;
    const root = document.createElement("div");
    renderReadout(root, configuration, {
      index: 0, lat: -20, lon: -55, value: 1, sampleCount: 40, covered: true, selected: true,
      statistic: "mean_flux", units: "units", northSouthKm: 222.4, eastWestKm: 209.0, areaKm2: 46400,
    });
    expect(root.textContent).toContain("222 km N–S × 209 km E–W");
    expect(root.textContent).toContain("46,400 km²");
  });

  it("renders controlled comparison selection and difference evidence", () => {
    const current = payload.experiments.satellite.configurations.find((item) =>
      item.id === "satellite|grid_deg=5|satellite=noaa19|statistic_used=mean_flux|threshold_label=top10")!;
    const option = comparisonOptions(payload, current)[0]!;
    const controls = document.createElement("div");
    let selected = "";
    renderComparisonControls(controls, payload, current, option.configuration.id, (id) => { selected = id ?? "off"; });
    expect(controls.textContent).toContain("Compare two maps");
    expect(controls.querySelectorAll("option")).toHaveLength(4);
    controls.querySelector<HTMLSelectElement>("select")!.value = comparisonOptions(payload, current)[1]!.configuration.id;
    controls.querySelector("select")!.dispatchEvent(new Event("change"));
    expect(selected).toContain("satellite|");

    const summary = document.createElement("div");
    renderComparisonSummary(summary, option.comparison, current, option.configuration);
    expect(summary.textContent).toContain("Centroid separation");
    expect(summary.textContent).toContain("Footprint overlap");
    expect(summary.textContent).toContain("Location and shape only");
    expect(summary.textContent).not.toContain("Flux difference");
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
