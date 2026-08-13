"""Deterministic export of validated checkpoint outputs for the static viewer.

Scientific calculations remain in the Python pipeline.  The viewer consumes exported
validated values for display.  This module reads the
accepted grid and sensitivity Parquets, checks that their discrete contracts agree, computes the
selected-cell membership in Python from each canonical stored cutoff, and writes ordinary
JavaScript data that works through both ``file://`` and static hosting.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

REGION = {"lat_min": -70.0, "lat_max": 20.0, "lon_min": -100.0, "lon_max": 20.0}

EXPERIMENT_DIMENSIONS = {
    "threshold": ["grid_deg", "statistic_used", "threshold_label"],
    "channel": ["channel", "grid_deg", "statistic_used", "threshold_label"],
    "time": ["window_label", "grid_deg", "statistic_used", "threshold_label"],
    "satellite": ["satellite", "grid_deg", "statistic_used", "threshold_label"],
}

EXPECTED_CONFIGURATION_COUNTS = {
    "threshold": 20,
    "channel": 60,
    "time": 160,
    "satellite": 100,
}

CONTROL_OPTIONS = {
    "grid_deg": [(5, "5 deg"), (2, "2 deg")],
    "statistic_used": [("mean_flux", "mean"), ("median_flux", "median")],
    "threshold_label": [
        ("top20", "top 20%"),
        ("top10", "top 10%"),
        ("top5", "top 5%"),
        ("top2", "top 2%"),
        ("top1", "top 1%"),
    ],
    "channel": [
        ("mep_omni_flux_p1", "p1 (~25 MeV)"),
        ("mep_omni_flux_p2", "p2 (~50 MeV)"),
        ("mep_omni_flux_p3", "p3 (~100 MeV)"),
    ],
    "window_label": [
        ("day_2024-01-01", "2024-01-01 (1 day)"),
        ("days_2024-01-01_to_07", "2024-01-01..07"),
        ("days_2024-01-01_to_14", "2024-01-01..14"),
        ("month_2024-01", "2024-01 (month)"),
        ("week1", "week 1 (Jan 01..07)"),
        ("week2", "week 2 (Jan 08..14)"),
        ("week3", "week 3 (Jan 15..21)"),
        ("week4", "week 4 (Jan 22..28)"),
    ],
    "satellite": [
        ("noaa15", "NOAA-15"),
        ("noaa18", "NOAA-18"),
        ("noaa19", "NOAA-19"),
        ("metop01", "MetOp-01"),
        ("metop03", "MetOp-03"),
    ],
}

CONTROL_LABELS = {
    "grid_deg": "grid",
    "statistic_used": "statistic",
    "threshold_label": "threshold",
    "channel": "channel",
    "window_label": "time window",
    "satellite": "satellite",
}

CHANNEL_DISPLAY = {
    "mep_omni_flux_p1": "p1 (~25 MeV)",
    "mep_omni_flux_p2": "p2 (~50 MeV)",
    "mep_omni_flux_p3": "p3 (~100 MeV)",
}

EXPERIMENT_METADATA = {
    "threshold": {
        "label": "threshold sensitivity",
        "question": "How does the candidate footprint change as the percentile threshold changes?",
        "initial_values": {
            "grid_deg": 5,
            "statistic_used": "mean_flux",
            "threshold_label": "top10",
        },
    },
    "channel": {
        "label": "proton channel sensitivity",
        "question": "How does the threshold-defined footprint change across validated proton channels?",
        "initial_values": {
            "channel": "mep_omni_flux_p1",
            "grid_deg": 5,
            "statistic_used": "mean_flux",
            "threshold_label": "top10",
        },
    },
    "time": {
        "label": "time-window sensitivity",
        "question": "How does the threshold-defined footprint change with the validated aggregation window?",
        "initial_values": {
            "window_label": "month_2024-01",
            "grid_deg": 5,
            "statistic_used": "mean_flux",
            "threshold_label": "top10",
        },
    },
    "satellite": {
        "label": "satellite sensitivity",
        "question": "How consistent is footprint location/shape across the five validated spacecraft?",
        "initial_values": {
            "satellite": "noaa19",
            "grid_deg": 5,
            "statistic_used": "mean_flux",
            "threshold_label": "top10",
        },
    },
}

METRIC_COLUMNS = {
    "flux_cutoff": "flux_cutoff_value",
    "covered_cells": "cells_available_after_coverage_mask",
    "selected_cells": "selected_cell_count",
    "selected_area_km2": "selected_area_km2",
    "selected_area_fraction": "selected_area_fraction_of_covered_region",
    "centroid_lat": "centroid_lat_flux_weighted",
    "centroid_lon": "centroid_lon_flux_weighted",
    "peak_flux": "peak_flux",
}


def _finite_float(value: Any, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_grid(table: pd.DataFrame, grid_deg: int, mask_col: str) -> dict[str, Any]:
    """Return one sorted, compact grid with failed-coverage flux values explicitly blanked."""
    required = {
        "lat_bin_center",
        "lon_bin_center",
        "mean_flux",
        "median_flux",
        "sample_count",
        mask_col,
    }
    missing = sorted(required - set(table.columns))
    if missing:
        raise KeyError(f"grid is missing required columns: {missing}")
    if table.duplicated(["lat_bin_center", "lon_bin_center"]).any():
        raise ValueError("grid contains duplicate cell centers")
    coverage = table[mask_col]
    if coverage.isna().any():
        raise TypeError(f"{mask_col} must not contain null coverage values")
    if not pd.api.types.is_bool_dtype(coverage.dtype):
        raise TypeError(f"{mask_col} must contain boolean coverage values")

    ordered = table.sort_values(["lat_bin_center", "lon_bin_center"]).reset_index(drop=True)
    cells: list[list[Any]] = []
    covered_values = {"mean_flux": [], "median_flux": []}
    for row in ordered.itertuples(index=False):
        lat = _finite_float(getattr(row, "lat_bin_center"), "lat_bin_center")
        lon = _finite_float(getattr(row, "lon_bin_center"), "lon_bin_center")
        count = int(getattr(row, "sample_count"))
        covered = bool(getattr(row, mask_col))
        exported_flux: list[float | None] = []
        for statistic in ("mean_flux", "median_flux"):
            value = getattr(row, statistic)
            if covered:
                numeric = _finite_float(value, statistic)
                if numeric > 0:
                    covered_values[statistic].append(numeric)
                exported_flux.append(numeric)
            else:
                exported_flux.append(None)
        cells.append([lat, lon, *exported_flux, count, covered])

    domains: dict[str, list[float]] = {}
    for statistic, values in covered_values.items():
        if not values:
            raise ValueError(f"grid has no positive coverage-passed {statistic} values")
        domains[statistic] = [min(values), max(values)]

    return {
        "grid_deg": int(grid_deg),
        "mask_column": mask_col,
        "columns": ["lat", "lon", "mean_flux", "median_flux", "sample_count", "covered"],
        "cells": cells,
        "color_domains": domains,
    }


def selected_cell_indices(grid: dict[str, Any], statistic: str, cutoff: float) -> list[int]:
    """Return coverage-passed cell indices at or above one canonical stored cutoff."""
    try:
        value_index = grid["columns"].index(statistic)
        covered_index = grid["columns"].index("covered")
    except ValueError as exc:
        raise KeyError(f"grid does not carry required selection field: {exc}") from exc
    threshold = _finite_float(cutoff, "flux_cutoff_value")
    selected: list[int] = []
    for index, cell in enumerate(grid["cells"]):
        covered = cell[covered_index]
        if type(covered) is not bool:
            raise TypeError(f"covered must be boolean at cell index {index}")
        if covered and cell[value_index] is not None and float(cell[value_index]) >= threshold:
            selected.append(index)
    return selected


def stable_configuration_id(experiment: str, values: dict[str, Any]) -> str:
    """Build a deterministic, experiment-scoped identifier from discrete method choices."""
    parts = [experiment]
    parts.extend(f"{key}={values[key]}" for key in sorted(values))
    return "|".join(parts)


def _controls_for(experiment: str) -> list[dict[str, Any]]:
    return [
        {
            "key": dimension,
            "label": CONTROL_LABELS[dimension],
            "options": [
                {"value": value, "label": label}
                for value, label in CONTROL_OPTIONS[dimension]
            ],
        }
        for dimension in EXPERIMENT_DIMENSIONS[experiment]
    ]


def _grid_path(table_dir: Path, experiment: str, row: pd.Series) -> Path:
    grid = int(row["grid_deg"])
    if experiment == "threshold":
        name = f"cp4a_noaa19_2024-01_grid_{grid}deg.parquet"
    elif experiment == "channel":
        channel_suffix = str(row["channel"]).removeprefix("mep_omni_flux_")
        name = f"cp4c_noaa19_2024-01_{channel_suffix}_grid_{grid}deg.parquet"
    elif experiment == "time":
        name = f"cp4d_{row['window_label']}_grid_{grid}deg.parquet"
    elif experiment == "satellite":
        name = f"cp4f_{row['satellite']}_2024-01_grid_{grid}deg.parquet"
    else:
        raise KeyError(f"unknown experiment {experiment!r}")
    return table_dir / name


def _configuration_metadata(experiment: str, row: pd.Series) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "period": "2024-01",
        "satellite": "noaa19",
        "channel": "mep_omni_flux_p1",
        "channel_display": CHANNEL_DISPLAY["mep_omni_flux_p1"],
        "flux_units": "#/cm2-s-str-MeV",
        "coverage_rule": "sample_count >= 30",
    }
    if experiment == "channel":
        channel = str(row["channel"])
        metadata["channel"] = channel
        metadata["channel_display"] = CHANNEL_DISPLAY[channel]
        metadata["channel_note"] = str(row["channel_metadata_note"])
    elif experiment == "time":
        metadata.update(
            {
                "period": f"{row['start_date']}..{row['end_date']}",
                "window_label": str(row["window_label"]),
                "day_count": int(row["day_count"]),
                "files_loaded": int(row["files_loaded"]),
                "files_expected": int(row["files_expected"]),
                "coverage_rule": f"sample_count >= {int(row['coverage_threshold_used'])}",
                "coverage_warning": str(row["coverage_warning"]),
            }
        )
    elif experiment == "satellite":
        if bool(row["absolute_flux_comparison_allowed"]):
            raise ValueError("satellite output unexpectedly permits absolute-flux comparison")
        metadata.update(
            {
                "satellite": str(row["satellite"]),
                "satellite_family_or_platform": str(row["satellite_family_or_platform"]),
                "coverage_rule": f"sample_count >= {int(row['coverage_threshold_used'])}",
                "absolute_flux_comparison_allowed": False,
                "satellite_note": str(row["satellite_compatibility_note"]),
            }
        )
    return metadata


def _configuration(
    experiment: str,
    row: pd.Series,
    grid_id: str,
    grid: dict[str, Any],
) -> dict[str, Any]:
    values = {
        dimension: int(row[dimension]) if dimension == "grid_deg" else str(row[dimension])
        for dimension in EXPERIMENT_DIMENSIONS[experiment]
    }
    cutoff = _finite_float(row["flux_cutoff_value"], "flux_cutoff_value")
    selected = selected_cell_indices(grid, str(row["statistic_used"]), cutoff)
    selected_count = int(row["selected_cell_count"])
    covered_count = int(row["cells_available_after_coverage_mask"])
    if len(selected) != selected_count:
        raise ValueError(
            f"{stable_configuration_id(experiment, values)} selected-cell mismatch: "
            f"grid/cutoff={len(selected)}, canonical={selected_count}"
        )
    actual_covered = sum(bool(cell[-1]) for cell in grid["cells"])
    if actual_covered != covered_count:
        raise ValueError(
            f"{stable_configuration_id(experiment, values)} covered-cell mismatch: "
            f"grid={actual_covered}, canonical={covered_count}"
        )

    metrics = {
        output: (
            int(row[source])
            if source in {"cells_available_after_coverage_mask", "selected_cell_count"}
            else _finite_float(row[source], source)
        )
        for output, source in METRIC_COLUMNS.items()
    }
    metrics["percentile_cutoff"] = int(row["percentile_cutoff"])
    return {
        "id": stable_configuration_id(experiment, values),
        "grid_id": grid_id,
        "values": values,
        "metadata": _configuration_metadata(experiment, row),
        "metrics": metrics,
        "selected_cell_indices": selected,
    }


def _cp5c_payload(summary: pd.DataFrame) -> dict[str, Any]:
    expected_satellites = {"noaa15", "noaa18", "noaa19", "metop01", "metop03"}
    if set(summary["satellite"]) != expected_satellites or len(summary) != 5:
        raise ValueError("CP5C summary must contain exactly the five accepted satellites")
    classifications = set(summary["cp5c_classification"].astype(str))
    if len(classifications) != 1:
        raise ValueError("CP5C classification must be identical on all satellite rows")

    count_fields = [
        "low_btot_support_count",
        "btot_dominance_support_count",
        "reversed_btot_sign_count",
    ]
    common_counts: dict[str, int] = {}
    for field in count_fields:
        values = set(summary[field].astype(int))
        if len(values) != 1:
            raise ValueError(f"CP5C global count differs across rows: {field}")
        common_counts[field] = int(next(iter(values)))

    rows = []
    for row in summary.sort_values("satellite").itertuples(index=False):
        rows.append(
            {
                "satellite": str(row.satellite),
                "btot_separation": _finite_float(row.btot_separation_metric, "btot_separation"),
                "l_igrf_separation": _finite_float(row.l_igrf_separation_metric, "l_igrf_separation"),
                "mlt_separation": _finite_float(row.mlt_separation_metric, "mlt_separation"),
                "fraction_below_btot_q25": _finite_float(
                    row.btot_fraction_below_regional_q25, "fraction_below_btot_q25"
                ),
                "regional_fraction_to_capture_90pct": _finite_float(
                    row.btot_regional_fraction_to_capture_90pct,
                    "regional_fraction_to_capture_90pct",
                ),
                "selected_cells": int(row.selected_cell_count),
                "selected_samples": int(row.selected_sample_count),
                "low_btot_support": bool(row.low_btot_support),
                "btot_dominance_support": bool(row.btot_dominance_support),
            }
        )

    return {
        "principal_case": "top10_5deg_mean",
        "classification": next(iter(classifications)),
        **common_counts,
        "criteria_note": "predeclared operational criteria for CP5C; not physical thresholds defining the SAA",
        "classification_rule": (
            "CONSISTENT requires >=4/5 low-Btot supporters and >=4/5 Btot-dominance supporters; "
            "INCONSISTENT applies at 0-1 low-Btot supporters or broadly reversed sign; otherwise MIXED."
        ),
        "interpretation": (
            "Across all five satellites, the low-Btot framing generalizes. NOAA-15 has a substantially "
            "larger MLT separation than the other spacecraft, so MLT is not described as universally irrelevant."
        ),
        "satellites": rows,
    }


def _require_unique_rows(table: pd.DataFrame, experiment: str) -> None:
    dimensions = EXPERIMENT_DIMENSIONS[experiment]
    if table.duplicated(dimensions).any():
        raise ValueError(f"{experiment} sensitivity table contains duplicate configuration keys")
    expected = EXPECTED_CONFIGURATION_COUNTS[experiment]
    if len(table) != expected:
        raise ValueError(f"{experiment} requires {expected} rows; found {len(table)}")


def build_viewer_payload(table_dir: Path) -> dict[str, Any]:
    """Build the complete static-viewer payload from validated canonical Parquet outputs."""
    table_dir = Path(table_dir)
    sensitivity_paths = {
        "threshold": table_dir / "cp4b_threshold_sensitivity.parquet",
        "channel": table_dir / "cp4c_channel_threshold_sensitivity.parquet",
        "time": table_dir / "cp4d_time_window_threshold_sensitivity.parquet",
        "satellite": table_dir / "cp4f_multisatellite_threshold_sensitivity.parquet",
    }
    cp5c_path = table_dir / "cp5c_multisatellite_magnetic_generality_summary.parquet"
    required = [*sensitivity_paths.values(), cp5c_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"viewer authority inputs are missing: {missing}")

    source_paths: set[Path] = set(required)
    grids: dict[str, dict[str, Any]] = {}
    grid_ids_by_digest: dict[str, str] = {}
    grid_ids_by_path: dict[Path, str] = {}
    experiments: dict[str, dict[str, Any]] = {}

    for experiment, sensitivity_path in sensitivity_paths.items():
        sensitivity = pd.read_parquet(sensitivity_path)
        _require_unique_rows(sensitivity, experiment)
        configurations = []
        dimensions = EXPERIMENT_DIMENSIONS[experiment]
        ordered = sensitivity.sort_values(dimensions).reset_index(drop=True)
        for _, row in ordered.iterrows():
            path = _grid_path(table_dir, experiment, row)
            if not path.is_file():
                raise FileNotFoundError(f"canonical grid is missing: {path}")
            source_paths.add(path)
            if path not in grid_ids_by_path:
                grid_deg = int(row["grid_deg"])
                exported = export_grid(
                    pd.read_parquet(path),
                    grid_deg=grid_deg,
                    mask_col=f"enough_samples_{grid_deg}deg",
                )
                semantic = json.dumps(
                    exported, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode("utf-8")
                digest = hashlib.sha256(semantic).hexdigest()
                grid_id = grid_ids_by_digest.get(digest)
                if grid_id is None:
                    grid_id = f"grid-{digest[:16]}"
                    grid_ids_by_digest[digest] = grid_id
                    grids[grid_id] = {**exported, "sources": [path.name]}
                else:
                    grids[grid_id]["sources"].append(path.name)
                    grids[grid_id]["sources"].sort()
                grid_ids_by_path[path] = grid_id
            grid_id = grid_ids_by_path[path]
            configurations.append(_configuration(experiment, row, grid_id, grids[grid_id]))

        ids = [configuration["id"] for configuration in configurations]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{experiment} produced duplicate configuration ids")
        experiments[experiment] = {
            **EXPERIMENT_METADATA[experiment],
            "dimensions": dimensions,
            "controls": _controls_for(experiment),
            "configuration_count": len(configurations),
            "configurations": sorted(configurations, key=lambda item: item["id"]),
        }

    authority_sources = [
        {"path": path.name, "sha256": _sha256(path), "size_bytes": path.stat().st_size}
        for path in sorted(source_paths, key=lambda item: item.name)
    ]
    cp5c = _cp5c_payload(pd.read_parquet(cp5c_path))
    return {
        "schema_version": 1,
        "export_contract": "validated Python outputs -> deterministic static data; browser display only",
        "region": REGION,
        "flux_color_scale": "viridis/log10",
        "experiments": experiments,
        "grids": dict(sorted(grids.items())),
        "cp5c": cp5c,
        "authority_sources": authority_sources,
        "global_caveats": [
            "candidate threshold-defined footprint; not a final SAA boundary",
            "not dose; not health risk; not a discovery claim",
            "coverage-failed or missing cells are blank, never zero-filled or interpolated",
            "cross-satellite absolute flux is not compared; compare footprint location/shape only",
            "mep_IFC_on == -1 is retained and remains uninterpreted",
        ],
    }


def write_viewer_data(payload: dict[str, Any], output: Path) -> str:
    """Write deterministic classic JavaScript and return its SHA-256 digest."""
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    source = f"window.SAA_VIEWER_DATA = {encoded};\n"
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding="utf-8", newline="\n")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
