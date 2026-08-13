#!/usr/bin/env python3
"""Validate Checkpoint 5C multi-satellite magnetic-generality outputs."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.magnetic_audit import selected_cells_from_grid  # noqa: E402
from saa.magnetic_framing import (  # noqa: E402
    CONCENTRATION_COLUMNS,
    FOOTPRINT_SUMMARY_COLUMNS,
    VALIDITY_COLUMNS,
    add_footprint_flags,
    concentration_metrics,
    footprint_magnetic_summary,
    magnetic_validity_table,
    valid_mask,
)

SATELLITES = ("noaa15", "noaa18", "noaa19", "metop01", "metop03")
SOURCE_TOKENS = {
    "noaa15": "n15",
    "noaa18": "n18",
    "noaa19": "n19",
    "metop01": "m01",
    "metop03": "m03",
}
REFERENCE_RTOL = 1e-9
REFERENCE_ATOL = 1e-12


def notebook_has_outputs(notebook: dict) -> bool:
    """Return True only when the notebook has code cells and every code cell has output."""
    code_cells = [cell for cell in notebook.get("cells", []) if cell.get("cell_type") == "code"]
    return bool(code_cells) and all(bool(cell.get("outputs")) for cell in code_cells)


def forbidden_cross_satellite_flux_columns(columns) -> list[str]:
    """Return forbidden flux-bearing columns, allowing only the explicit comparison guard flag."""
    allowed_flag = "absolute_flux_comparison_allowed"
    return [str(column) for column in columns if "flux" in str(column).lower() and column != allowed_flag]


def source_name_matches_satellite(source_name: str, satellite: str) -> bool:
    """Require a real Jan-2024 NOAA source filename for the claimed platform."""
    token = SOURCE_TOKENS.get(satellite)
    if token is None:
        return False
    return re.fullmatch(rf"poes_{token}_202401\d{{2}}_proc\.nc", source_name) is not None


def keyed_table_matches(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
    keys: list[str],
    exact_columns: list[str],
    float_columns: list[str],
) -> bool:
    """Compare keyed tables with exact discrete and fixed-tolerance float contracts."""
    required = keys + exact_columns + float_columns
    if any(column not in actual.columns or column not in expected.columns for column in required):
        return False

    def keyed(frame: pd.DataFrame) -> pd.DataFrame | None:
        selected = frame.loc[:, required].copy()
        for key in keys:
            selected[key] = selected[key].map(
                lambda value: "<NA>" if pd.isna(value) else str(value)
            )
        if selected.duplicated(keys).any():
            return None
        return selected.sort_values(keys).set_index(keys)

    actual_keyed = keyed(actual)
    expected_keyed = keyed(expected)
    if actual_keyed is None or expected_keyed is None:
        return False
    if not actual_keyed.index.equals(expected_keyed.index):
        return False
    if any(
        not actual_keyed[column].equals(expected_keyed[column]) for column in exact_columns
    ):
        return False
    return all(
        np.allclose(
            actual_keyed[column].to_numpy(dtype="float64"),
            expected_keyed[column].to_numpy(dtype="float64"),
            rtol=REFERENCE_RTOL,
            atol=REFERENCE_ATOL,
            equal_nan=True,
        )
        for column in float_columns
    )


def expected_fit_flag_diagnostic(flagged: pd.DataFrame, satellite: str) -> pd.DataFrame:
    """Independently derive the complete regional and principal-footprint flag distribution."""
    rows: list[dict[str, object]] = []
    for scope, subset in (
        ("regional_sample", flagged),
        ("top10_5deg_mean_footprint", flagged.loc[flagged["in_top10_5deg"]]),
    ):
        total = int(len(subset))
        counts = subset["mep_omni_flux_flag_fit"].value_counts(dropna=False).sort_index()
        for flag_value, count in counts.items():
            rows.append(
                {
                    "satellite": satellite,
                    "analysis_month": "2024-01",
                    "scope": scope,
                    "flag_value": flag_value,
                    "sample_count": int(count),
                    "scope_total": total,
                    "fraction": float(count / total) if total else float("nan"),
                }
            )
    return pd.DataFrame(rows)


def semantic_table_pair_matches(csv_path: Path, parquet_path: Path) -> bool:
    """Verify that a generated CSV/Parquet pair carries the same ordered values."""
    csv = pd.read_csv(csv_path)
    parquet = pd.read_parquet(parquet_path)
    if list(csv.columns) != list(parquet.columns) or len(csv) != len(parquet):
        return False
    for column in parquet.columns:
        if pd.api.types.is_numeric_dtype(parquet[column].dtype) and not pd.api.types.is_bool_dtype(
            parquet[column].dtype
        ):
            if not np.allclose(
                csv[column].to_numpy(dtype="float64"),
                parquet[column].to_numpy(dtype="float64"),
                rtol=REFERENCE_RTOL,
                atol=REFERENCE_ATOL,
                equal_nan=True,
            ):
                return False
        else:
            csv_values = csv[column].map(
                lambda value: "<NA>" if pd.isna(value) or value == "" else str(value)
            )
            parquet_values = parquet[column].map(
                lambda value: "<NA>" if pd.isna(value) or value == "" else str(value)
            )
            if not csv_values.equals(parquet_values):
                return False
    return True


def _single_value(table: pd.DataFrame, filters: dict[str, object], column: str) -> object:
    mask = pd.Series(True, index=table.index)
    for key, value in filters.items():
        mask &= table[key] == value
    values = table.loc[mask, column]
    if len(values) != 1:
        raise ValueError(f"expected one {column} value for {filters}, found {len(values)}")
    return values.iloc[0]


def independent_classification(summary: pd.DataFrame) -> str:
    """Recompute the frozen CP5C classification without importing production rubric code."""
    if len(summary) != 5:
        raise ValueError("CP5C classification requires exactly five rows")
    low_count = int(summary["low_btot_support"].astype(bool).sum())
    dominance_count = int(summary["btot_dominance_support"].astype(bool).sum())
    reversed_count = int((summary["btot_separation_metric"].astype(float) < 0.0).sum())
    if low_count >= 4 and dominance_count >= 4:
        return "CONSISTENT"
    if low_count <= 1 or reversed_count >= 4:
        return "INCONSISTENT"
    return "MIXED"


def circularize_mlt_hours(values: np.ndarray) -> np.ndarray:
    """Express MLT as shortest signed offsets from its pooled circular mean."""
    hours = np.asarray(values, dtype="float64")
    if hours.ndim != 1 or hours.size == 0:
        raise ValueError("MLT circularization requires a non-empty one-dimensional array")
    if not np.isfinite(hours).all() or ((hours < 0.0) | (hours > 24.0)).any():
        raise ValueError("MLT circularization requires finite hours within [0, 24]")
    angles = hours * (2.0 * np.pi / 24.0)
    mean_sine = float(np.sin(angles).mean())
    mean_cosine = float(np.cos(angles).mean())
    if np.hypot(mean_sine, mean_cosine) <= np.finfo("float64").eps:
        raise ValueError("MLT circular mean is undefined for this distribution")
    center = (
        (np.arctan2(mean_sine, mean_cosine) % (2.0 * np.pi))
        * (24.0 / (2.0 * np.pi))
    )
    return (hours - center + 12.0) % 24.0 - 12.0


def standardized_median_separation(values: np.ndarray, inside: np.ndarray) -> float:
    """Reapply the accepted CP5B median/IQR separation formula to one coordinate."""
    numeric = np.asarray(values, dtype="float64")
    membership = np.asarray(inside, dtype=bool)
    if numeric.shape != membership.shape or numeric.ndim != 1:
        raise ValueError("separation values and membership must be aligned one-dimensional arrays")
    inside_values = numeric[membership]
    outside_values = numeric[~membership]
    if not inside_values.size or not outside_values.size:
        raise ValueError("separation requires non-empty inside and outside samples")
    inside_q25, inside_median, inside_q75 = np.percentile(inside_values, [25, 50, 75])
    outside_q25, outside_median, outside_q75 = np.percentile(
        outside_values, [25, 50, 75]
    )
    pooled_iqr = 0.5 * (
        (inside_q75 - inside_q25) + (outside_q75 - outside_q25)
    )
    if not np.isfinite(pooled_iqr) or pooled_iqr <= 0.0:
        raise ValueError("separation requires a positive finite pooled IQR")
    return float((outside_median - inside_median) / pooled_iqr)


def main(root: Path = ROOT) -> int:
    """Validate all CP5C scientific, processing, reference, and artifact contracts."""
    table_dir = root / "outputs" / "tables"
    figure_dir = root / "outputs" / "figures"
    processed_dir = root / "data" / "processed"
    notebook_path = root / "notebooks" / "05c_multisatellite_magnetic_generality.ipynb"

    table_stems = (
        "cp5c_magnetic_variable_validity_by_satellite",
        "cp5c_footprint_magnetic_summary_by_satellite",
        "cp5c_magnetic_concentration_by_satellite",
        "cp5c_multisatellite_magnetic_generality_summary",
        "cp5c_omni_fit_flag_diagnostic",
    )
    figure_names = (
        "cp5c_multisatellite_magnetic_separation_top10_5deg_mean.png",
        "cp5c_multisatellite_low_btot_capture90_top10_5deg_mean.png",
    )
    accepted_paths = [
        root / "outputs" / "tables" / "cp5b_magnetic_variable_validity.csv",
        root / "outputs" / "tables" / "cp5b_footprint_magnetic_summary.parquet",
        root / "outputs" / "tables" / "cp5b_magnetic_concentration_metrics.csv",
        root / "outputs" / "tables" / "cp4a_noaa19_2024-01_grid_5deg.parquet",
        root / "outputs" / "tables" / "cp4a_noaa19_2024-01_grid_2deg.parquet",
        root / "outputs" / "tables" / "cp6a_key_results_summary.csv",
        root / "outputs" / "tables" / "cp6a_key_results_summary.parquet",
        root / "data" / "processed" / "cp5a_noaa19_2024-01_region_flux_plus_magnetic.parquet",
        root / "docs" / "CLAIM_AUDIT.md",
        root / "docs" / "PAPER_OUTLINE.md",
    ]
    accepted_paths.extend(
        table_dir / f"cp4f_{satellite}_2024-01_grid_{resolution}deg.parquet"
        for satellite in SATELLITES
        for resolution in (5, 2)
    )

    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    required_paths: list[Path] = []
    for stem in table_stems:
        required_paths.extend((table_dir / f"{stem}.csv", table_dir / f"{stem}.parquet"))
    required_paths.extend(
        processed_dir / f"cp5c_{satellite}_2024-01_region_flux_plus_magnetic.parquet"
        for satellite in SATELLITES
    )
    required_paths.extend(figure_dir / name for name in figure_names)
    required_paths.append(notebook_path)
    required_paths.extend(accepted_paths)

    missing = [str(path.relative_to(root)) for path in required_paths if not path.exists()]
    add("all required CP5C and accepted artifacts exist", not missing, "MISSING: " + ", ".join(missing) if missing else "present")
    if missing:
        print("=" * 76)
        print("CHECKPOINT 5C OUTPUT VALIDATION")
        print("=" * 76)
        for name, ok, detail in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}  ->  {detail}")
        print("RESULT: ONE OR MORE CHECKS FAILED")
        return 1

    for stem in table_stems:
        add(
            f"CSV/Parquet pair is semantically equivalent: {stem}",
            semantic_table_pair_matches(table_dir / f"{stem}.csv", table_dir / f"{stem}.parquet"),
        )

    validity = pd.read_parquet(table_dir / "cp5c_magnetic_variable_validity_by_satellite.parquet")
    summary = pd.read_parquet(table_dir / "cp5c_footprint_magnetic_summary_by_satellite.parquet")
    concentration = pd.read_parquet(table_dir / "cp5c_magnetic_concentration_by_satellite.parquet")
    generality = pd.read_parquet(table_dir / "cp5c_multisatellite_magnetic_generality_summary.parquet")
    fit_flags = pd.read_parquet(table_dir / "cp5c_omni_fit_flag_diagnostic.parquet")

    required_schemas = {
        "validity": (validity, ["satellite", "analysis_month"] + VALIDITY_COLUMNS),
        "footprint summary": (summary, ["satellite", "analysis_month"] + FOOTPRINT_SUMMARY_COLUMNS),
        "concentration": (concentration, ["satellite", "analysis_month"] + CONCENTRATION_COLUMNS),
        "generality": (
            generality,
            [
                "satellite",
                "analysis_month",
                "principal_case",
                "btot_separation_metric",
                "l_igrf_separation_metric",
                "mlt_separation_metric",
                "btot_fraction_below_regional_q25",
                "btot_regional_fraction_to_capture_50pct",
                "btot_regional_fraction_to_capture_75pct",
                "btot_regional_fraction_to_capture_90pct",
                "selected_cell_count",
                "selected_sample_count",
                "ifc_on_dropped",
                "ifc_minus1_retained",
                "low_btot_support",
                "btot_dominance_support",
                "absolute_flux_comparison_allowed",
                "cp5c_classification",
            ],
        ),
        "fit flags": (
            fit_flags,
            ["satellite", "analysis_month", "scope", "flag_value", "sample_count", "scope_total", "fraction"],
        ),
    }
    for label, (frame, columns) in required_schemas.items():
        absent = [column for column in columns if column not in frame.columns]
        add(f"{label} schema complete", not absent, "all columns" if not absent else f"missing {absent}")

    expected_satellites = set(SATELLITES)
    for label, frame in (
        ("validity", validity),
        ("footprint summary", summary),
        ("concentration", concentration),
        ("generality", generality),
        ("fit flags", fit_flags),
    ):
        add(f"{label} contains all five satellites only", set(frame["satellite"]) == expected_satellites)
        add(f"{label} is January 2024 only", set(frame["analysis_month"]) == {"2024-01"})

    add("generality has exactly one row per satellite", len(generality) == 5 and generality["satellite"].is_unique)
    add(
        "generality support columns have boolean dtype",
        all(
            pd.api.types.is_bool_dtype(generality[column].dtype)
            for column in ("low_btot_support", "btot_dominance_support")
        ),
    )
    add(
        "generality rubric inputs are finite",
        np.isfinite(
            generality[
                [
                    "btot_separation_metric",
                    "l_igrf_separation_metric",
                    "mlt_separation_metric",
                    "btot_fraction_below_regional_q25",
                    "btot_regional_fraction_to_capture_90pct",
                ]
            ].to_numpy(dtype="float64")
        ).all(),
    )
    add("no forbidden absolute-flux comparison columns", not forbidden_cross_satellite_flux_columns(generality.columns), str(forbidden_cross_satellite_flux_columns(generality.columns)))
    add("absolute flux comparison guard is False", (generality["absolute_flux_comparison_allowed"] == False).all())  # noqa: E712

    required_cases = {"top10_5deg_mean", "top5_5deg_mean", "top10_2deg_mean", "top5_2deg_mean"}
    required_variables = {"Btot_sat", "L_IGRF", "mag_lat_sat", "MLT"}
    add("footprint summary covers four accepted cases", set(summary["comparison_case"]) == required_cases)
    add("footprint summary covers accepted variables", set(summary["magnetic_variable"]) == required_variables)
    add("no naive mag_lon_sat summary", "mag_lon_sat" not in set(summary["magnetic_variable"]))

    noaa19_cell_sets: dict[str, set[tuple[float, float]]] | None = None
    recomputed_principal_rows: list[dict[str, object]] = []
    circular_mlt_separations: dict[str, float] = {}
    for satellite in SATELLITES:
        region_path = processed_dir / f"cp5c_{satellite}_2024-01_region_flux_plus_magnetic.parquet"
        region = pd.read_parquet(region_path)
        required_columns = {
            "time", "lat", "lon", "lon180", "satellite", "source_file", "mep_omni_flux_p1",
            "mep_IFC_on", "mep_omni_flux_flag_fit", "Btot_sat", "L_IGRF", "mag_lat_sat",
            "mag_lon_sat", "MLT",
        }
        add(f"{satellite} processed schema complete", required_columns.issubset(region.columns))
        times = pd.to_datetime(region["time"], utc=True)
        add(f"{satellite} processed rows January-only", (times.dt.strftime("%Y-%m") == "2024-01").all())
        add(f"{satellite} label is stable", set(region["satellite"]) == {satellite})
        sources = set(region["source_file"].astype(str))
        add(
            f"{satellite} uses 31 matching real NOAA source files",
            len(sources) == 31
            and all(source_name_matches_satellite(source, satellite) for source in sources),
            f"{len(sources)} files",
        )
        add(f"{satellite} drops mep_IFC_on == 1", not (region["mep_IFC_on"] == 1).any())

        bmask = valid_mask(region, "Btot_sat")
        lmask = valid_mask(region, "L_IGRF")
        add(f"{satellite} Btot validity respected", bool(bmask.any()) and np.isfinite(region.loc[bmask, "Btot_sat"]).all() and (region.loc[bmask, "Btot_sat"] > 0).all())
        add(f"{satellite} L_IGRF -1 excluded from valid subset", bool(lmask.any()) and not (region.loc[lmask, "L_IGRF"] == -1).any() and (region.loc[lmask, "L_IGRF"] > 0).all())

        grid5 = pd.read_parquet(table_dir / f"cp4f_{satellite}_2024-01_grid_5deg.parquet")
        grid2 = pd.read_parquet(table_dir / f"cp4f_{satellite}_2024-01_grid_2deg.parquet")
        cell_sets = {}
        for case, grid, mask_column, percentile in (
            ("top10_5deg_mean", grid5, "enough_samples_5deg", 90),
            ("top5_5deg_mean", grid5, "enough_samples_5deg", 95),
            ("top10_2deg_mean", grid2, "enough_samples_2deg", 90),
            ("top5_2deg_mean", grid2, "enough_samples_2deg", 95),
        ):
            cells, _ = selected_cells_from_grid(grid, "mean_flux", mask_column, percentile)
            cell_sets[case] = cells
            add(f"{satellite} {case} selected cells non-empty", bool(cells), f"{len(cells)} cells")
        flagged = add_footprint_flags(region, grid5, grid2)
        if satellite == "noaa19":
            noaa19_cell_sets = cell_sets

        case_columns = {
            "top10_5deg_mean": "in_top10_5deg",
            "top5_5deg_mean": "in_top5_5deg",
            "top10_2deg_mean": "in_top10_2deg",
            "top5_2deg_mean": "in_top5_2deg",
        }
        for case, footprint_column in case_columns.items():
            for variable in required_variables:
                expected_inside = int((valid_mask(flagged, variable) & flagged[footprint_column]).sum())
                expected_outside = int((valid_mask(flagged, variable) & ~flagged[footprint_column]).sum())
                row = summary.loc[
                    (summary["satellite"] == satellite)
                    & (summary["comparison_case"] == case)
                    & (summary["magnetic_variable"] == variable)
                ]
                counts_match = len(row) == 1 and int(row["inside_count"].iloc[0]) == expected_inside and int(row["outside_count"].iloc[0]) == expected_outside
                add(f"{satellite} {case} {variable} membership counts reproduce", counts_match)

        expected_validity = magnetic_validity_table(flagged)
        saved_validity = validity.loc[validity["satellite"] == satellite]
        add(
            f"{satellite} full validity metrics recompute from processed data",
            keyed_table_matches(
                saved_validity,
                expected_validity,
                ["variable_name"],
                ["rows_total", "rows_valid", "rows_invalid"],
                ["valid_min", "valid_max"],
            ),
        )

        expected_summary = footprint_magnetic_summary(flagged)
        saved_summary = summary.loc[summary["satellite"] == satellite]
        add(
            f"{satellite} full separation metrics recompute from processed data",
            keyed_table_matches(
                saved_summary,
                expected_summary,
                ["comparison_case", "magnetic_variable"],
                ["inside_count", "outside_count"],
                [
                    "median_inside",
                    "median_outside",
                    "iqr_inside",
                    "iqr_outside",
                    "p10_inside",
                    "p90_inside",
                    "p10_outside",
                    "p90_outside",
                    "separation_metric",
                ],
            ),
        )

        expected_concentration = concentration_metrics(flagged)
        saved_concentration = concentration.loc[concentration["satellite"] == satellite]
        add(
            f"{satellite} full concentration metrics recompute from processed data",
            keyed_table_matches(
                saved_concentration,
                expected_concentration,
                ["metric", "footprint", "variable"],
                [],
                ["value"],
            ),
        )

        principal = generality.loc[generality["satellite"] == satellite].iloc[0]
        add(f"{satellite} principal selected-cell count reproduces CP4F", int(principal["selected_cell_count"]) == len(cell_sets["top10_5deg_mean"]))
        add(f"{satellite} principal selected-sample count reproduces membership", int(principal["selected_sample_count"]) == int(flagged["in_top10_5deg"].sum()))
        add(f"{satellite} IFC retained counts reconcile", int(principal["ifc_minus1_retained"]) == int((region["mep_IFC_on"] == -1).sum()) and int(principal["regional_rows_after_ifc"]) == len(region))

        mlt_valid = valid_mask(flagged, "MLT")
        circular_mlt_separation = standardized_median_separation(
            circularize_mlt_hours(
                flagged.loc[mlt_valid, "MLT"].to_numpy(dtype="float64")
            ),
            flagged.loc[mlt_valid, "in_top10_5deg"].to_numpy(dtype=bool),
        )
        circular_mlt_separations[satellite] = circular_mlt_separation
        add(
            f"{satellite} Btot dominance survives wrap-aware MLT audit",
            float(principal["btot_separation_metric"]) > abs(circular_mlt_separation),
            (
                f"Btot={float(principal['btot_separation_metric']):.6f}; "
                f"circular MLT={circular_mlt_separation:.6f}"
            ),
        )

        satellite_flags = fit_flags.loc[fit_flags["satellite"] == satellite]
        expected_flags = expected_fit_flag_diagnostic(flagged, satellite)
        add(
            f"{satellite} exact per-flag diagnostic recomputes from processed data",
            keyed_table_matches(
                satellite_flags,
                expected_flags,
                ["satellite", "analysis_month", "scope", "flag_value"],
                ["sample_count", "scope_total"],
                ["fraction"],
            ),
        )

        def expected_separation(variable: str) -> float:
            return float(
                _single_value(
                    expected_summary,
                    {
                        "comparison_case": "top10_5deg_mean",
                        "magnetic_variable": variable,
                    },
                    "separation_metric",
                )
            )

        def expected_concentration_value(metric: str) -> float:
            return float(
                _single_value(
                    expected_concentration,
                    {"metric": metric, "footprint": "top10", "variable": "Btot_sat"},
                    "value",
                )
            )

        recomputed_principal_rows.append(
            {
                "satellite": satellite,
                "principal_case": "top10_5deg_mean",
                "btot_separation_metric": expected_separation("Btot_sat"),
                "l_igrf_separation_metric": expected_separation("L_IGRF"),
                "mlt_separation_metric": expected_separation("MLT"),
                "btot_fraction_below_regional_q25": expected_concentration_value(
                    "fraction_below_regional_q25"
                ),
                "btot_regional_fraction_to_capture_50pct": expected_concentration_value(
                    "regional_fraction_to_capture_50pct"
                ),
                "btot_regional_fraction_to_capture_75pct": expected_concentration_value(
                    "regional_fraction_to_capture_75pct"
                ),
                "btot_regional_fraction_to_capture_90pct": expected_concentration_value(
                    "regional_fraction_to_capture_90pct"
                ),
                "selected_cell_count": len(cell_sets["top10_5deg_mean"]),
                "selected_sample_count": int(flagged["in_top10_5deg"].sum()),
            }
        )

    recomputed_principal = pd.DataFrame(recomputed_principal_rows)
    add(
        "principal raw metrics recompute from processed data",
        keyed_table_matches(
            generality,
            recomputed_principal,
            ["satellite", "principal_case"],
            ["selected_cell_count", "selected_sample_count"],
            [
                "btot_separation_metric",
                "l_igrf_separation_metric",
                "mlt_separation_metric",
                "btot_fraction_below_regional_q25",
                "btot_regional_fraction_to_capture_50pct",
                "btot_regional_fraction_to_capture_75pct",
                "btot_regional_fraction_to_capture_90pct",
            ],
        ),
    )
    recalculated_low = (
        (recomputed_principal["btot_separation_metric"] > 0)
        & (recomputed_principal["btot_fraction_below_regional_q25"] > 0.50)
        & (recomputed_principal["btot_regional_fraction_to_capture_90pct"] <= 0.50)
    )
    recalculated_dominance = (
        (recomputed_principal["btot_separation_metric"] > recomputed_principal["l_igrf_separation_metric"])
        & (recomputed_principal["btot_separation_metric"] > recomputed_principal["mlt_separation_metric"].abs())
    )
    recomputed_principal["low_btot_support"] = recalculated_low
    recomputed_principal["btot_dominance_support"] = recalculated_dominance
    saved_support = generality.set_index("satellite")
    expected_support = recomputed_principal.set_index("satellite")
    add(
        "low-Btot support booleans recompute from processed data",
        saved_support["low_btot_support"].astype(bool).equals(
            expected_support["low_btot_support"].astype(bool)
        ),
    )
    add(
        "Btot-dominance booleans recompute from processed data",
        saved_support["btot_dominance_support"].astype(bool).equals(
            expected_support["btot_dominance_support"].astype(bool)
        ),
    )
    expected_classification = independent_classification(recomputed_principal)
    add("saved classification matches independent rubric", set(generality["cp5c_classification"]) == {expected_classification}, expected_classification)
    add("saved support counts match independent counts", (generality["low_btot_support_count"] == int(recalculated_low.sum())).all() and (generality["btot_dominance_support_count"] == int(recalculated_dominance.sum())).all())
    circular_dominance = recomputed_principal.apply(
        lambda row: float(row["btot_separation_metric"])
        > abs(circular_mlt_separations[str(row["satellite"])]),
        axis=1,
    )
    circular_audit_summary = recomputed_principal.copy()
    circular_audit_summary["btot_dominance_support"] = circular_dominance
    circular_classification = independent_classification(circular_audit_summary)
    add(
        "wrap-aware MLT audit preserves CP5C classification",
        circular_classification == expected_classification == "CONSISTENT",
        circular_classification,
    )
    largest_circular_mlt = max(
        circular_mlt_separations,
        key=lambda satellite: abs(circular_mlt_separations[satellite]),
    )
    add(
        "NOAA-15 remains the largest absolute MLT-separation case after circularization",
        largest_circular_mlt == "noaa15",
        f"largest={largest_circular_mlt}",
    )

    cp4a_grid5 = pd.read_parquet(table_dir / "cp4a_noaa19_2024-01_grid_5deg.parquet")
    cp4a_grid2 = pd.read_parquet(table_dir / "cp4a_noaa19_2024-01_grid_2deg.parquet")
    cp4a_sets = {}
    for case, grid, mask_column, percentile in (
        ("top10_5deg_mean", cp4a_grid5, "enough_samples_5deg", 90),
        ("top5_5deg_mean", cp4a_grid5, "enough_samples_5deg", 95),
        ("top10_2deg_mean", cp4a_grid2, "enough_samples_2deg", 90),
        ("top5_2deg_mean", cp4a_grid2, "enough_samples_2deg", 95),
    ):
        cp4a_sets[case] = selected_cells_from_grid(grid, "mean_flux", mask_column, percentile)[0]
    add("NOAA-19 CP4F cell sets exactly reproduce CP4A/CP5B", noaa19_cell_sets == cp4a_sets)

    cp5b_validity = pd.read_csv(table_dir / "cp5b_magnetic_variable_validity.csv").sort_values("variable_name")
    cp5c_validity = validity.loc[validity["satellite"] == "noaa19"].sort_values("variable_name")
    exact_validity = all(cp5c_validity[column].reset_index(drop=True).equals(cp5b_validity[column].reset_index(drop=True)) for column in ("variable_name", "rows_total", "rows_valid", "rows_invalid"))
    add("NOAA-19 validity names/counts exactly reproduce CP5B", exact_validity)
    float_validity = all(np.allclose(cp5c_validity[column], cp5b_validity[column], rtol=REFERENCE_RTOL, atol=REFERENCE_ATOL, equal_nan=True) for column in ("valid_min", "valid_max"))
    add("NOAA-19 validity ranges reproduce CP5B at fixed tolerance", float_validity)

    cp5b_summary = pd.read_parquet(table_dir / "cp5b_footprint_magnetic_summary.parquet").sort_values(["comparison_case", "magnetic_variable"])
    cp5c_summary = summary.loc[summary["satellite"] == "noaa19"].sort_values(["comparison_case", "magnetic_variable"])
    summary_keys = ["comparison_case", "magnetic_variable"]
    exact_summary = all(cp5c_summary[column].reset_index(drop=True).equals(cp5b_summary[column].reset_index(drop=True)) for column in summary_keys + ["inside_count", "outside_count"])
    add("NOAA-19 cases/variables/counts exactly reproduce CP5B", exact_summary)
    summary_float_columns = ["median_inside", "median_outside", "iqr_inside", "iqr_outside", "p10_inside", "p90_inside", "p10_outside", "p90_outside", "separation_metric"]
    float_summary = all(np.allclose(cp5c_summary[column], cp5b_summary[column], rtol=REFERENCE_RTOL, atol=REFERENCE_ATOL, equal_nan=True) for column in summary_float_columns)
    add("NOAA-19 footprint metrics reproduce CP5B at fixed tolerance", float_summary)

    cp5b_concentration = pd.read_csv(table_dir / "cp5b_magnetic_concentration_metrics.csv").sort_values(["metric", "footprint", "variable"])
    cp5c_concentration = concentration.loc[concentration["satellite"] == "noaa19"].sort_values(["metric", "footprint", "variable"])
    concentration_keys = ["metric", "footprint", "variable"]
    exact_concentration = all(cp5c_concentration[column].reset_index(drop=True).equals(cp5b_concentration[column].reset_index(drop=True)) for column in concentration_keys)
    add("NOAA-19 concentration metric names exactly reproduce CP5B", exact_concentration)
    add("NOAA-19 concentration values reproduce CP5B at fixed tolerance", np.allclose(cp5c_concentration["value"], cp5b_concentration["value"], rtol=REFERENCE_RTOL, atol=REFERENCE_ATOL, equal_nan=True))

    for name in figure_names:
        path = figure_dir / name
        add(f"figure exists and is non-empty: {name}", path.stat().st_size > 1000, f"{path.stat().st_size} B")

    notebook = json.loads(notebook_path.read_text())
    add("CP5C notebook executed with outputs in every code cell", notebook_has_outputs(notebook))

    print("=" * 76)
    print("CHECKPOINT 5C OUTPUT VALIDATION")
    print("=" * 76)
    all_ok = True
    for name, ok, detail in checks:
        all_ok &= ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ->  {detail}" if detail else ""))
    print("-" * 76)
    print("RESULT:", "ALL CHECKS PASSED" if all_ok else "ONE OR MORE CHECKS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
