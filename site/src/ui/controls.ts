import type { ConfigurationValues, ExperimentName, ViewerPayload } from "../data/types";

const LABELS: Record<ExperimentName, string> = { threshold: "Threshold", channel: "Proton energy", time: "Time", satellite: "Satellite" };
const QUESTIONS: Record<ExperimentName, string> = {
  threshold: "How much does the footprint depend on what counts as high flux?",
  channel: "Does proton energy change the footprint?",
  time: "How stable is the footprint as observations accumulate?",
  satellite: "Do different satellites locate the same high-flux region?",
};
const FOCAL: Record<ExperimentName, string> = { threshold: "threshold_label", channel: "channel", time: "window_label", satellite: "satellite" };

function display(key: string, label: string): string {
  if (key === "threshold_label") return label.replace(/^top /i, "Top ");
  if (key === "channel") return label.replace(/^p\d \(/, "").replace(/\)$/, "");
  if (key === "grid_deg") return label.replace(" deg", "°");
  if (key === "statistic_used") return label[0]!.toUpperCase() + label.slice(1);
  return label;
}

function segmented(key: string, options: Array<{value: string | number; label: string}>, value: string | number | undefined, update: (value: string | number) => void): HTMLElement {
  const group = document.createElement("div");
  group.className = "segmented";
  options.forEach((option) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = display(key, option.label);
    button.setAttribute("aria-pressed", String(String(value) === String(option.value)));
    button.addEventListener("click", () => update(option.value));
    group.append(button);
  });
  return group;
}

export function renderControls(root: HTMLElement, payload: ViewerPayload, activeExperiment: ExperimentName, values: ConfigurationValues, onChange: (experiment: ExperimentName, values: ConfigurationValues) => void): void {
  root.replaceChildren();
  const tabs = document.createElement("div");
  tabs.className = "experiment-tabs";
  tabs.setAttribute("role", "tablist");
  tabs.setAttribute("aria-label", "Scientific question");
  const names = Object.keys(LABELS) as ExperimentName[];
  const currentGrid = values.grid_deg ?? payload.experiments[activeExperiment].initial_values.grid_deg ?? 5;
  names.forEach((name, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.role = "tab";
    button.id = `experiment-${name}-tab`;
    button.textContent = LABELS[name];
    button.setAttribute("aria-selected", String(name === activeExperiment));
    button.setAttribute("aria-controls", "explorer-state");
    button.tabIndex = name === activeExperiment ? 0 : -1;
    button.addEventListener("click", () => onChange(name, { ...payload.experiments[name].initial_values, grid_deg: currentGrid }));
    button.addEventListener("keydown", (event) => {
      const destination = event.key === "Home" ? 0 : event.key === "End" ? names.length - 1
        : event.key === "ArrowRight" ? (index + 1) % names.length
          : event.key === "ArrowLeft" ? (index - 1 + names.length) % names.length : -1;
      if (destination < 0) return;
      event.preventDefault();
      const next = names[destination]!;
      onChange(next, { ...payload.experiments[next].initial_values, grid_deg: currentGrid });
      queueMicrotask(() => document.querySelector<HTMLElement>(`#experiment-${next}-tab`)?.focus());
    });
    tabs.append(button);
  });
  root.append(tabs);
  const question = document.createElement("h3");
  question.className = "experiment-question";
  question.textContent = QUESTIONS[activeExperiment];
  root.append(question);
  const specification = payload.experiments[activeExperiment];
  const focalKey = FOCAL[activeExperiment];
  const focal = specification.controls.find((control) => control.key === focalKey)!;
  const focalFieldset = document.createElement("fieldset");
  focalFieldset.className = "focal-control";
  focalFieldset.dataset.control = focal.key;
  const legend = document.createElement("legend");
  legend.textContent = focal.label === "channel" ? "Proton energy" : focal.label[0]!.toUpperCase() + focal.label.slice(1);
  focalFieldset.append(legend);
  if (focal.key === "window_label") {
    const select = document.createElement("select");
    select.setAttribute("aria-label", "Time window");
    const cumulative = document.createElement("optgroup"); cumulative.label = "Cumulative observations";
    const weeks = document.createElement("optgroup"); weeks.label = "Separate weekly windows";
    focal.options.forEach((option) => {
      const item = document.createElement("option"); item.value = String(option.value); item.textContent = option.label; item.selected = String(values[focal.key]) === String(option.value);
      (String(option.value).startsWith("week") ? weeks : cumulative).append(item);
    });
    select.append(cumulative, weeks);
    select.addEventListener("change", () => onChange(activeExperiment, { ...values, [focal.key]: select.value }));
    focalFieldset.append(select);
  } else {
    focalFieldset.append(segmented(focal.key, focal.options, values[focal.key], (value) => onChange(activeExperiment, { ...values, [focal.key]: value })));
  }
  root.append(focalFieldset);
  const gridControl = specification.controls.find((control) => control.key === "grid_deg")!;
  const gridFieldset = document.createElement("fieldset");
  gridFieldset.className = "persistent-control";
  gridFieldset.dataset.control = gridControl.key;
  const gridLegend = document.createElement("legend");
  gridLegend.textContent = "Grid resolution";
  gridFieldset.append(gridLegend, segmented(gridControl.key, gridControl.options, currentGrid, (value) => onChange(activeExperiment, { ...values, grid_deg: value })));
  root.append(gridFieldset);
  const details = document.createElement("div"); details.className = "analysis-settings";
  const settings = document.createElement("div"); settings.className = "settings-grid";
  specification.controls.filter((control) => control.key !== focalKey && control.key !== "grid_deg").forEach((control) => {
    const fieldset = document.createElement("fieldset"); fieldset.dataset.control = control.key;
    const fieldLegend = document.createElement("legend"); fieldLegend.textContent = control.label[0]!.toUpperCase() + control.label.slice(1); fieldset.append(fieldLegend);
    fieldset.append(segmented(control.key, control.options, values[control.key], (value) => onChange(activeExperiment, { ...values, [control.key]: value })));
    settings.append(fieldset);
  });
  details.append(settings); root.append(details);
}
