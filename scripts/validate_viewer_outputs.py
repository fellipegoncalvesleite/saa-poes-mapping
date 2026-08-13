#!/usr/bin/env python3
"""Validate the static viewer against every canonical checkpoint map configuration."""
from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.viewer_export import build_viewer_payload, write_viewer_data  # noqa: E402

RTOL = 1e-9
ATOL = 1e-12
EXPECTED_COUNTS = {"threshold": 20, "channel": 60, "time": 160, "satellite": 100}
DIMENSIONS = {
    "threshold": ["grid_deg", "statistic_used", "threshold_label"],
    "channel": ["channel", "grid_deg", "statistic_used", "threshold_label"],
    "time": ["window_label", "grid_deg", "statistic_used", "threshold_label"],
    "satellite": ["satellite", "grid_deg", "statistic_used", "threshold_label"],
}
SENSITIVITY_FILES = {
    "threshold": "cp4b_threshold_sensitivity.parquet",
    "channel": "cp4c_channel_threshold_sensitivity.parquet",
    "time": "cp4d_time_window_threshold_sensitivity.parquet",
    "satellite": "cp4f_multisatellite_threshold_sensitivity.parquet",
}
METRICS = {
    "flux_cutoff": "flux_cutoff_value",
    "covered_cells": "cells_available_after_coverage_mask",
    "selected_cells": "selected_cell_count",
    "selected_area_km2": "selected_area_km2",
    "selected_area_fraction": "selected_area_fraction_of_covered_region",
    "centroid_lat": "centroid_lat_flux_weighted",
    "centroid_lon": "centroid_lon_flux_weighted",
    "peak_flux": "peak_flux",
}


def deep_payload_matches(actual: Any, expected: Any) -> bool:
    """Compare JSON-shaped payloads: exact discrete values and fixed-tolerance floats."""
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        return type(actual) is type(expected) and actual == expected
    if isinstance(expected, int):
        return type(actual) is int and actual == expected
    if isinstance(expected, float):
        return (
            type(actual) in (int, float)
            and not isinstance(actual, bool)
            and math.isfinite(float(actual))
            and np.isclose(float(actual), expected, rtol=RTOL, atol=ATOL)
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            deep_payload_matches(a, e) for a, e in zip(actual, expected)
        )
    if isinstance(expected, dict):
        return isinstance(actual, dict) and set(actual) == set(expected) and all(
            deep_payload_matches(actual[key], value) for key, value in expected.items()
        )
    return type(actual) is type(expected) and actual == expected


def load_viewer_data(path: Path) -> dict[str, Any]:
    source = Path(path).read_text(encoding="utf-8")
    prefix = "window.SAA_VIEWER_DATA = "
    suffix = ";\n"
    if not source.startswith(prefix) or not source.endswith(suffix):
        raise ValueError("viewer_data.js is not the required classic global assignment")
    payload = json.loads(source[len(prefix):-len(suffix)])
    if not isinstance(payload, dict):
        raise TypeError("viewer payload root must be an object")
    return payload


def static_files_are_file_openable(viewer_dir: Path) -> tuple[bool, str]:
    viewer_dir = Path(viewer_dir)
    required = [viewer_dir / "index.html", viewer_dir / "viewer.js", viewer_dir / "viewer_data.js"]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        return False, f"missing static files: {missing}"
    html = required[0].read_text(encoding="utf-8")
    renderer = required[1].read_text(encoding="utf-8")
    problems = []
    data_tag = '<script src="viewer_data.js"></script>'
    render_tag = '<script src="viewer.js"></script>'
    if data_tag not in html or render_tag not in html or html.index(data_tag) > html.index(render_tag):
        problems.append("classic scripts are missing or out of order")
    if 'type="module"' in html or "type='module'" in html:
        problems.append("module scripts require a server under common file:// browser policies")
    if "fetch(" in html or "fetch(" in renderer:
        problems.append("fetch is forbidden for the file-openable viewer")
    lowered = renderer.lower()
    for forbidden in ("react", "vue", "angular", "next.js", "mapbox", "leaflet"):
        if forbidden in lowered:
            problems.append(f"unnecessary framework/map dependency found: {forbidden}")
    return not problems, "; ".join(problems) if problems else "classic local/static files; no fetch/modules/framework"


def _configuration_id(experiment: str, values: dict[str, Any]) -> str:
    return "|".join([experiment, *(f"{key}={values[key]}" for key in sorted(values))])


def _grid_path(table_dir: Path, experiment: str, row: pd.Series) -> Path:
    resolution = int(row["grid_deg"])
    if experiment == "threshold":
        name = f"cp4a_noaa19_2024-01_grid_{resolution}deg.parquet"
    elif experiment == "channel":
        suffix = str(row["channel"]).removeprefix("mep_omni_flux_")
        name = f"cp4c_noaa19_2024-01_{suffix}_grid_{resolution}deg.parquet"
    elif experiment == "time":
        name = f"cp4d_{row['window_label']}_grid_{resolution}deg.parquet"
    elif experiment == "satellite":
        name = f"cp4f_{row['satellite']}_2024-01_grid_{resolution}deg.parquet"
    else:
        raise KeyError(experiment)
    return table_dir / name


def _float_matches(actual: Any, expected: Any) -> bool:
    try:
        return bool(np.isclose(float(actual), float(expected), rtol=RTOL, atol=ATOL))
    except (TypeError, ValueError):
        return False


def _grid_matches(
    actual: dict[str, Any],
    canonical: pd.DataFrame,
    resolution: int,
) -> tuple[bool, str]:
    mask = f"enough_samples_{resolution}deg"
    expected_columns = ["lat", "lon", "mean_flux", "median_flux", "sample_count", "covered"]
    if actual.get("grid_deg") != resolution or actual.get("mask_column") != mask:
        return False, "grid resolution/mask metadata differs"
    if actual.get("columns") != expected_columns:
        return False, "grid column contract differs"
    coverage = canonical[mask]
    if coverage.isna().any():
        return False, f"{mask} contains null coverage values"
    if not pd.api.types.is_bool_dtype(coverage.dtype):
        return False, f"{mask} contains non-boolean coverage values"
    ordered = canonical.sort_values(["lat_bin_center", "lon_bin_center"]).reset_index(drop=True)
    cells = actual.get("cells", [])
    if len(cells) != len(ordered):
        return False, "grid cell count differs"
    positive = {"mean_flux": [], "median_flux": []}
    for index, row in ordered.iterrows():
        cell = cells[index]
        if len(cell) != 6:
            return False, f"grid cell width differs at index {index}"
        covered = bool(row[mask])
        if not _float_matches(cell[0], row["lat_bin_center"]):
            return False, f"latitude differs at index {index}"
        if not _float_matches(cell[1], row["lon_bin_center"]):
            return False, f"longitude differs at index {index}"
        if type(cell[4]) is not int or cell[4] != int(row["sample_count"]):
            return False, f"sample count differs at index {index}"
        if type(cell[5]) is not bool or cell[5] is not covered:
            return False, f"coverage state differs at index {index}"
        for column_index, statistic in ((2, "mean_flux"), (3, "median_flux")):
            if covered:
                if not _float_matches(cell[column_index], row[statistic]):
                    return False, f"{statistic} differs at index {index}"
                if float(row[statistic]) > 0:
                    positive[statistic].append(float(row[statistic]))
            elif cell[column_index] is not None:
                return False, f"coverage-failed {statistic} is not blank at index {index}"
    expected_domains = {
        statistic: [min(values), max(values)] for statistic, values in positive.items()
    }
    if not deep_payload_matches(actual.get("color_domains"), expected_domains):
        return False, "log-color domains differ"
    return True, "grid cells/masks/values match"


def independent_authority_matches(payload: dict[str, Any], table_dir: Path) -> tuple[bool, str]:
    """Walk all 340 configurations directly against canonical rows and grid Parquets."""
    experiments = payload.get("experiments", {})
    if set(experiments) != set(EXPECTED_COUNTS):
        return False, "experiment set differs"
    grids = payload.get("grids", {})
    validated_grid_pairs: set[tuple[str, str]] = set()
    for experiment, expected_count in EXPECTED_COUNTS.items():
        sensitivity_path = table_dir / SENSITIVITY_FILES[experiment]
        if not sensitivity_path.is_file():
            return False, f"missing {sensitivity_path.name}"
        canonical_rows = pd.read_parquet(sensitivity_path)
        dimensions = DIMENSIONS[experiment]
        if len(canonical_rows) != expected_count or canonical_rows.duplicated(dimensions).any():
            return False, f"canonical {experiment} row/key count differs"
        configurations = experiments[experiment].get("configurations", [])
        if len(configurations) != expected_count:
            return False, f"exported {experiment} configuration count differs"
        by_id = {item.get("id"): item for item in configurations}
        if len(by_id) != expected_count:
            return False, f"exported {experiment} ids are not unique"
        expected_ids: set[str] = set()
        for _, row in canonical_rows.iterrows():
            values = {
                key: int(row[key]) if key == "grid_deg" else str(row[key])
                for key in dimensions
            }
            config_id = _configuration_id(experiment, values)
            expected_ids.add(config_id)
            actual = by_id.get(config_id)
            if actual is None or actual.get("values") != values:
                return False, f"missing or altered configuration: {config_id}"
            grid_id = actual.get("grid_id")
            grid = grids.get(grid_id)
            if grid is None:
                return False, f"missing referenced grid: {grid_id}"
            path = _grid_path(table_dir, experiment, row)
            if not path.is_file():
                return False, f"missing canonical grid: {path.name}"
            pair = (str(path), str(grid_id))
            canonical_grid = pd.read_parquet(path)
            if pair not in validated_grid_pairs:
                ok, detail = _grid_matches(grid, canonical_grid, int(row["grid_deg"]))
                if not ok:
                    return False, f"{path.name}: {detail}"
                validated_grid_pairs.add(pair)
            ordered = canonical_grid.sort_values(
                ["lat_bin_center", "lon_bin_center"]
            ).reset_index(drop=True)
            mask = f"enough_samples_{int(row['grid_deg'])}deg"
            statistic = str(row["statistic_used"])
            cutoff = float(row["flux_cutoff_value"])
            selected = [
                index for index, cell in ordered.iterrows()
                if bool(cell[mask]) and float(cell[statistic]) >= cutoff
            ]
            if actual.get("selected_cell_indices") != selected:
                return False, f"selected membership differs: {config_id}"
            metrics = actual.get("metrics", {})
            for output, column in METRICS.items():
                if column in {"cells_available_after_coverage_mask", "selected_cell_count"}:
                    if type(metrics.get(output)) is not int or metrics[output] != int(row[column]):
                        return False, f"discrete metric differs: {config_id} {output}"
                elif not _float_matches(metrics.get(output), row[column]):
                    return False, f"float metric differs: {config_id} {output}"
            if type(metrics.get("percentile_cutoff")) is not int or metrics["percentile_cutoff"] != int(row["percentile_cutoff"]):
                return False, f"percentile cutoff differs: {config_id}"
            if len(selected) != int(row["selected_cell_count"]):
                return False, f"canonical selected count does not reconcile: {config_id}"
        if set(by_id) != expected_ids:
            return False, f"unsupported extra {experiment} configuration exported"
    return True, f"all {sum(EXPECTED_COUNTS.values())} configurations independently match canonical rows/grids"


def independent_cp5c_matches(payload: dict[str, Any], table_dir: Path) -> tuple[bool, str]:
    path = table_dir / "cp5c_multisatellite_magnetic_generality_summary.parquet"
    if not path.is_file():
        return False, f"missing {path.name}"
    canonical = pd.read_parquet(path)
    cp5c = payload.get("cp5c", {})
    rows = cp5c.get("satellites", [])
    by_satellite = {row.get("satellite"): row for row in rows}
    if len(canonical) != 5 or len(by_satellite) != 5:
        return False, "CP5C must contain five satellite rows"
    expected_classifications = set(canonical["cp5c_classification"].astype(str))
    if expected_classifications != {cp5c.get("classification")}:
        return False, "CP5C classification differs"
    for field in (
        "low_btot_support_count",
        "btot_dominance_support_count",
        "reversed_btot_sign_count",
    ):
        expected = set(canonical[field].astype(int))
        if len(expected) != 1 or type(cp5c.get(field)) is not int or cp5c[field] != next(iter(expected)):
            return False, f"CP5C global count differs: {field}"
    mappings = {
        "btot_separation": "btot_separation_metric",
        "l_igrf_separation": "l_igrf_separation_metric",
        "mlt_separation": "mlt_separation_metric",
        "fraction_below_btot_q25": "btot_fraction_below_regional_q25",
        "regional_fraction_to_capture_90pct": "btot_regional_fraction_to_capture_90pct",
    }
    for _, row in canonical.iterrows():
        actual = by_satellite.get(str(row["satellite"]))
        if actual is None:
            return False, f"CP5C satellite missing: {row['satellite']}"
        for output, column in mappings.items():
            if not _float_matches(actual.get(output), row[column]):
                return False, f"CP5C float differs: {row['satellite']} {output}"
        discrete = {
            "selected_cells": int(row["selected_cell_count"]),
            "selected_samples": int(row["selected_sample_count"]),
            "low_btot_support": bool(row["low_btot_support"]),
            "btot_dominance_support": bool(row["btot_dominance_support"]),
        }
        for field, expected in discrete.items():
            if type(actual.get(field)) is not type(expected) or actual[field] != expected:
                return False, f"CP5C discrete value differs: {row['satellite']} {field}"
    return True, "five raw CP5C rows/classification match canonical summary"


def main(
    table_dir: Path = ROOT / "outputs" / "tables",
    viewer_dir: Path = ROOT / "outputs" / "viewer",
) -> int:
    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append((name, bool(ok), detail))

    viewer_data = Path(viewer_dir) / "viewer_data.js"
    ok, detail = static_files_are_file_openable(viewer_dir)
    add("file-openable static contract", ok, detail)
    try:
        payload = load_viewer_data(viewer_data)
        add("viewer data parses", True, f"schema={payload.get('schema_version')}")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        add("viewer data parses", False, str(exc))
        payload = None

    if payload is not None:
        add("schema version", payload.get("schema_version") == 1, str(payload.get("schema_version")))
        authority_ok, authority_detail = independent_authority_matches(payload, Path(table_dir))
        add("independent map authority", authority_ok, authority_detail)
        cp5c_ok, cp5c_detail = independent_cp5c_matches(payload, Path(table_dir))
        add("independent CP5C evidence", cp5c_ok, cp5c_detail)
        try:
            regenerated = build_viewer_payload(Path(table_dir))
            add(
                "fresh deterministic payload",
                deep_payload_matches(payload, regenerated),
                "generated payload equals fresh authority export",
            )
            with tempfile.TemporaryDirectory() as tmp:
                fresh_path = Path(tmp) / "viewer_data.js"
                write_viewer_data(regenerated, fresh_path)
                byte_exact = fresh_path.read_bytes() == viewer_data.read_bytes()
            add("byte-deterministic artifact", byte_exact, "fresh bytes equal checked artifact")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            add("fresh deterministic payload", False, str(exc))
            add("byte-deterministic artifact", False, "fresh export failed")

    for name, passed, message in checks:
        print(f"{'PASS' if passed else 'FAIL'} | {name} | {message}")
    passed_count = sum(passed for _, passed, _ in checks)
    print(f"\n{passed_count}/{len(checks)} checks passed")
    if checks and all(passed for _, passed, _ in checks):
        print("ALL CHECKS PASSED")
        return 0
    print("VALIDATION FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
