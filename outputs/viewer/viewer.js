(function () {
  "use strict";

  const DATA = window.SAA_VIEWER_DATA;
  const EXPERIMENT_ORDER = ["threshold", "channel", "time", "satellite"];
  const SVG_NS = "http://www.w3.org/2000/svg";
  const SVG_WIDTH = 900;
  const SVG_HEIGHT = 690;
  const PLOT = { left: 70, top: 30, width: 720, height: 540 };
  const VIRIDIS = [
    [0.00, "#440154"],
    [0.25, "#3b528b"],
    [0.50, "#21918c"],
    [0.75, "#5ec962"],
    [1.00, "#fde725"],
  ];

  const state = { experiment: "threshold", values: {} };

  function svgElement(name, attributes, text) {
    const element = document.createElementNS(SVG_NS, name);
    Object.entries(attributes || {}).forEach(([key, value]) => {
      element.setAttribute(key, String(value));
    });
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function htmlElement(name, text) {
    const element = document.createElement(name);
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function labelFor(control, value) {
    const option = control.options.find((item) => String(item.value) === String(value));
    return option ? option.label : String(value);
  }

  function formatNumber(value, digits) {
    if (!Number.isFinite(Number(value))) return "n/a";
    return Number(value).toLocaleString("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function formatFlux(value) {
    if (!Number.isFinite(Number(value))) return "n/a";
    const numeric = Number(value);
    if (numeric !== 0 && (Math.abs(numeric) >= 10000 || Math.abs(numeric) < 0.01)) {
      return numeric.toExponential(4);
    }
    return formatNumber(numeric, 4);
  }

  function xPosition(lon) {
    const region = DATA.region;
    return PLOT.left + ((lon - region.lon_min) / (region.lon_max - region.lon_min)) * PLOT.width;
  }

  function yPosition(lat) {
    const region = DATA.region;
    return PLOT.top + ((region.lat_max - lat) / (region.lat_max - region.lat_min)) * PLOT.height;
  }

  function hexToRgb(hex) {
    return [
      parseInt(hex.slice(1, 3), 16),
      parseInt(hex.slice(3, 5), 16),
      parseInt(hex.slice(5, 7), 16),
    ];
  }

  function interpolateColor(value) {
    const t = Math.max(0, Math.min(1, value));
    let left = VIRIDIS[0];
    let right = VIRIDIS[VIRIDIS.length - 1];
    for (let index = 1; index < VIRIDIS.length; index += 1) {
      if (t <= VIRIDIS[index][0]) {
        left = VIRIDIS[index - 1];
        right = VIRIDIS[index];
        break;
      }
    }
    const span = right[0] - left[0] || 1;
    const local = (t - left[0]) / span;
    const a = hexToRgb(left[1]);
    const b = hexToRgb(right[1]);
    const channels = a.map((channel, index) => Math.round(channel + (b[index] - channel) * local));
    return `rgb(${channels[0]},${channels[1]},${channels[2]})`;
  }

  function logColor(value, domain) {
    if (!(value > 0) || !(domain[0] > 0) || !(domain[1] > 0)) return "#ffffff";
    const low = Math.log10(domain[0]);
    const high = Math.log10(domain[1]);
    const normalized = high === low ? 0.5 : (Math.log10(value) - low) / (high - low);
    return interpolateColor(normalized);
  }

  function currentSpecification() {
    return DATA.experiments[state.experiment];
  }

  function currentConfiguration() {
    const specification = currentSpecification();
    return specification.configurations.find((configuration) =>
      specification.dimensions.every(
        (dimension) => String(configuration.values[dimension]) === String(state.values[dimension])
      )
    );
  }

  function appendAxes(svg) {
    const region = DATA.region;
    const gridGroup = svgElement("g", { "aria-hidden": "true" });
    for (let lon = region.lon_min; lon <= region.lon_max; lon += 20) {
      const x = xPosition(lon);
      gridGroup.appendChild(svgElement("line", {
        x1: x, y1: PLOT.top, x2: x, y2: PLOT.top + PLOT.height,
        stroke: lon === 0 ? "#777" : "#ddd", "stroke-width": lon === 0 ? 0.8 : 0.5,
      }));
      gridGroup.appendChild(svgElement("text", {
        x, y: PLOT.top + PLOT.height + 20, "text-anchor": "middle", "font-size": 12,
      }, String(lon)));
    }
    for (let lat = region.lat_min; lat <= region.lat_max; lat += 10) {
      const y = yPosition(lat);
      gridGroup.appendChild(svgElement("line", {
        x1: PLOT.left, y1: y, x2: PLOT.left + PLOT.width, y2: y,
        stroke: lat === 0 ? "#777" : "#ddd", "stroke-width": lat === 0 ? 0.8 : 0.5,
      }));
      gridGroup.appendChild(svgElement("text", {
        x: PLOT.left - 9, y: y + 4, "text-anchor": "end", "font-size": 12,
      }, String(lat)));
    }
    gridGroup.appendChild(svgElement("rect", {
      x: PLOT.left, y: PLOT.top, width: PLOT.width, height: PLOT.height,
      fill: "none", stroke: "#000", "stroke-width": 1,
    }));
    gridGroup.appendChild(svgElement("text", {
      x: PLOT.left + PLOT.width / 2, y: PLOT.top + PLOT.height + 48,
      "text-anchor": "middle", "font-size": 13,
    }, "longitude [deg]  ([-180,180) convention)"));
    const latitudeLabel = svgElement("text", {
      x: 18, y: PLOT.top + PLOT.height / 2, "text-anchor": "middle", "font-size": 13,
      transform: `rotate(-90 18 ${PLOT.top + PLOT.height / 2})`,
    }, "latitude [deg]");
    gridGroup.appendChild(latitudeLabel);
    svg.appendChild(gridGroup);
  }

  function appendColorLegend(svg, statistic, domain, units) {
    const x = 820;
    const y = 80;
    const height = 360;
    const swatches = 12;
    const group = svgElement("g", { "aria-label": "log10 flux color legend" });
    for (let index = 0; index < swatches; index += 1) {
      const t = index / (swatches - 1);
      group.appendChild(svgElement("rect", {
        x, y: y + height - ((index + 1) * height) / swatches,
        width: 24, height: height / swatches + 0.5,
        fill: interpolateColor(t), stroke: "none",
      }));
    }
    group.appendChild(svgElement("rect", {
      x, y, width: 24, height, fill: "none", stroke: "#000", "stroke-width": 1,
    }));
    group.appendChild(svgElement("text", { x: x + 31, y: y + 5, "font-size": 11 }, formatFlux(domain[1])));
    group.appendChild(svgElement("text", { x: x + 31, y: y + height, "font-size": 11 }, formatFlux(domain[0])));
    const label = svgElement("text", {
      x: x + 75, y: y + height / 2, "text-anchor": "middle", "font-size": 11,
      transform: `rotate(-90 ${x + 75} ${y + height / 2})`,
    }, `${statistic} [${units}] log10`);
    group.appendChild(label);
    svg.appendChild(group);
  }

  function renderMap(configuration) {
    const svg = document.getElementById("flux-map");
    svg.replaceChildren();
    svg.setAttribute("viewBox", `0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`);
    const grid = DATA.grids[configuration.grid_id];
    const statistic = configuration.values.statistic_used;
    const valueIndex = grid.columns.indexOf(statistic);
    const sampleIndex = grid.columns.indexOf("sample_count");
    const coveredIndex = grid.columns.indexOf("covered");
    const selected = new Set(configuration.selected_cell_indices);
    const cellWidth = (grid.grid_deg / (DATA.region.lon_max - DATA.region.lon_min)) * PLOT.width;
    const cellHeight = (grid.grid_deg / (DATA.region.lat_max - DATA.region.lat_min)) * PLOT.height;

    appendAxes(svg);
    const cells = svgElement("g", { "aria-label": "canonical geographic grid cells" });
    grid.cells.forEach((cell, index) => {
      const lat = cell[0];
      const lon = cell[1];
      const value = cell[valueIndex];
      const covered = Boolean(cell[coveredIndex]);
      const isSelected = selected.has(index);
      const rect = svgElement("rect", {
        x: xPosition(lon - grid.grid_deg / 2),
        y: yPosition(lat + grid.grid_deg / 2),
        width: cellWidth,
        height: cellHeight,
        fill: covered && value > 0 ? logColor(value, grid.color_domains[statistic]) : "#ffffff",
        stroke: isSelected ? "#000000" : "#aaaaaa",
        "stroke-width": isSelected ? 2.0 : 0.35,
        "vector-effect": "non-scaling-stroke",
      });
      const status = covered ? (value > 0 ? "coverage passed" : "non-positive on log scale") : "coverage failed";
      rect.appendChild(svgElement("title", {},
        `lat ${lat}, lon ${lon}; ${statistic}=${value === null ? "blank" : value}; samples=${cell[sampleIndex]}; ${status}${isSelected ? "; selected footprint" : ""}`
      ));
      cells.appendChild(rect);
    });
    svg.appendChild(cells);

    const centroidX = xPosition(configuration.metrics.centroid_lon);
    const centroidY = yPosition(configuration.metrics.centroid_lat);
    const marker = svgElement("g", { "aria-label": "stored flux-weighted centroid" });
    marker.appendChild(svgElement("line", {
      x1: centroidX - 9, y1: centroidY - 9, x2: centroidX + 9, y2: centroidY + 9,
      stroke: "#000", "stroke-width": 3,
    }));
    marker.appendChild(svgElement("line", {
      x1: centroidX - 9, y1: centroidY + 9, x2: centroidX + 9, y2: centroidY - 9,
      stroke: "#000", "stroke-width": 3,
    }));
    marker.appendChild(svgElement("title", {},
      `stored flux-weighted centroid: ${configuration.metrics.centroid_lat}, ${configuration.metrics.centroid_lon}`
    ));
    svg.appendChild(marker);

    appendColorLegend(svg, statistic, grid.color_domains[statistic], configuration.metadata.flux_units);
    svg.appendChild(svgElement("text", {
      x: PLOT.left, y: SVG_HEIGHT - 16, "font-size": 11,
    }, "black cell outline = selected threshold footprint; X = stored flux-weighted centroid"));
  }

  function addReadoutRow(body, label, value) {
    const row = htmlElement("tr");
    const heading = htmlElement("th", label);
    heading.scope = "row";
    row.appendChild(heading);
    row.appendChild(htmlElement("td", String(value)));
    body.appendChild(row);
  }

  function renderReadout(configuration) {
    const body = document.getElementById("configuration-readout");
    body.replaceChildren();
    const specification = currentSpecification();
    const controls = Object.fromEntries(specification.controls.map((control) => [control.key, control]));
    const values = configuration.values;
    const metadata = configuration.metadata;
    const metrics = configuration.metrics;
    const rows = [
      ["experiment", specification.label],
      ["configuration id", configuration.id],
      ["satellite", metadata.satellite],
      ["period", metadata.period],
      ["channel", metadata.channel_display],
      ["grid", labelFor(controls.grid_deg, values.grid_deg)],
      ["statistic", labelFor(controls.statistic_used, values.statistic_used)],
      ["threshold", labelFor(controls.threshold_label, values.threshold_label)],
      ["covered cells", metrics.covered_cells],
      ["selected cells", metrics.selected_cells],
      ["selected area", `${formatNumber(metrics.selected_area_km2, 0)} km²`],
      ["area fraction of covered region", formatNumber(metrics.selected_area_fraction, 6)],
      ["centroid lat", `${formatNumber(metrics.centroid_lat, 6)} deg`],
      ["centroid lon", `${formatNumber(metrics.centroid_lon, 6)} deg`],
      ["flux cutoff", `${formatFlux(metrics.flux_cutoff)} ${metadata.flux_units}`],
      ["coverage rule", metadata.coverage_rule],
    ];
    rows.splice(rows.length - 1, 0, ["color normalization", "within the current grid only"]);
    if (state.experiment === "threshold" || state.experiment === "time") {
      rows.splice(rows.length - 1, 0, ["peak flux", `${formatFlux(metrics.peak_flux)} ${metadata.flux_units}`]);
    }
    if (metadata.window_label) rows.splice(3, 0, ["time window", metadata.window_label]);
    if (metadata.coverage_warning) rows.push(["coverage warning", metadata.coverage_warning]);
    if (metadata.absolute_flux_comparison_allowed === false) {
      rows.push(["absolute flux comparison", "NOT ALLOWED"]);
    }
    rows.forEach(([label, value]) => addReadoutRow(body, label, value));
  }

  function renderConfiguration() {
    const configuration = currentConfiguration();
    const error = document.getElementById("viewer-error");
    if (!configuration) {
      error.textContent = "ERROR: no validated configuration matches these controls.";
      document.getElementById("flux-map").replaceChildren();
      document.getElementById("configuration-readout").replaceChildren();
      return;
    }
    error.textContent = "";
    document.getElementById("experiment-question").textContent = currentSpecification().question;
    renderMap(configuration);
    renderReadout(configuration);
  }

  function buildMethodControls() {
    const container = document.getElementById("method-controls");
    const specification = currentSpecification();
    container.replaceChildren();
    state.values = { ...specification.initial_values };
    specification.controls.forEach((control) => {
      const label = htmlElement("label", `${control.label}: `);
      const select = htmlElement("select");
      select.name = control.key;
      select.setAttribute("aria-label", control.label);
      control.options.forEach((item) => {
        const option = htmlElement("option", item.label);
        option.value = String(item.value);
        option.selected = String(item.value) === String(state.values[control.key]);
        select.appendChild(option);
      });
      select.addEventListener("change", () => {
        const declared = control.options.find((item) => String(item.value) === select.value);
        state.values[control.key] = declared ? declared.value : select.value;
        renderConfiguration();
      });
      label.appendChild(select);
      container.appendChild(label);
    });
    renderConfiguration();
  }

  function renderCp5c() {
    const target = document.getElementById("cp5c-result");
    const result = DATA.cp5c;
    target.replaceChildren();
    target.appendChild(htmlElement("p", `RUBRIC RESULT: ${result.classification}`));
    target.appendChild(htmlElement("p",
      `votes: low-Btot ${result.low_btot_support_count}/5; Btot dominance ${result.btot_dominance_support_count}/5; reversed Btot sign ${result.reversed_btot_sign_count}/5`
    ));
    target.appendChild(htmlElement("p", `rule: ${result.classification_rule}`));
    target.appendChild(htmlElement("p", `criteria status: ${result.criteria_note}`));

    const table = htmlElement("table");
    const head = htmlElement("thead");
    const headingRow = htmlElement("tr");
    ["satellite", "Btot sep", "L_IGRF sep", "MLT sep", "below Btot q25", "fraction for 90%", "low-Btot", "Btot dominance"]
      .forEach((heading) => headingRow.appendChild(htmlElement("th", heading)));
    head.appendChild(headingRow);
    table.appendChild(head);
    const body = htmlElement("tbody");
    result.satellites.forEach((satellite) => {
      const row = htmlElement("tr");
      [
        satellite.satellite,
        formatNumber(satellite.btot_separation, 6),
        formatNumber(satellite.l_igrf_separation, 6),
        formatNumber(satellite.mlt_separation, 6),
        formatNumber(satellite.fraction_below_btot_q25, 6),
        formatNumber(satellite.regional_fraction_to_capture_90pct, 6),
        String(satellite.low_btot_support),
        String(satellite.btot_dominance_support),
      ].forEach((value) => row.appendChild(htmlElement("td", value)));
      body.appendChild(row);
    });
    table.appendChild(body);
    target.appendChild(table);
    target.appendChild(htmlElement("p", `NARRATIVE INTERPRETATION (after rubric): ${result.interpretation}`));
  }

  function initialize() {
    if (!DATA || DATA.schema_version !== 1) {
      document.getElementById("viewer-error").textContent =
        "ERROR: viewer_data.js is missing or has an unsupported schema.";
      return;
    }
    const experimentSelect = document.getElementById("experiment-control");
    EXPERIMENT_ORDER.forEach((name) => {
      const option = htmlElement("option", DATA.experiments[name].label);
      option.value = name;
      experimentSelect.appendChild(option);
    });
    experimentSelect.value = state.experiment;
    experimentSelect.addEventListener("change", () => {
      state.experiment = experimentSelect.value;
      buildMethodControls();
    });
    buildMethodControls();
    renderCp5c();
  }

  initialize();
}());
