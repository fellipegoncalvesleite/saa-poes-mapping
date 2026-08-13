"""Multi-satellite descriptive magnetic generality analysis (Checkpoint 5C).

CP5C applies the accepted CP4F satellite-specific particle-footprint definitions and the accepted
CP5B magnetic validity, separation, and concentration formulas to five January-2024 satellites.
Every magnetic rank is computed within one satellite. Absolute proton flux is not compared between
satellites, and no magnetic cutoff produced here defines a physical SAA boundary.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .magnetic_framing import (
    add_footprint_flags,
    concentration_metrics,
    footprint_magnetic_summary,
    magnetic_validity_table,
)

SATELLITES: tuple[str, ...] = ("noaa15", "noaa18", "noaa19", "metop01", "metop03")
ANALYSIS_MONTH = "2024-01"
REFERENCE_RTOL = 1e-9
REFERENCE_ATOL = 1e-12


@dataclass(frozen=True)
class ReferenceBundle:
    """NOAA-19 footprint and metric artifacts compared by the CP5C hard gate."""

    cell_sets: Mapping[str, set[tuple[float, float]]]
    validity: pd.DataFrame
    footprint_summary: pd.DataFrame
    concentration: pd.DataFrame


def add_cp5c_footprint_flags(
    region: pd.DataFrame,
    grid5: pd.DataFrame,
    grid2: pd.DataFrame,
) -> pd.DataFrame:
    """Assign the four accepted CP4F/CP5B footprint flags to one satellite's samples."""
    return add_footprint_flags(region, grid5, grid2)


def validity_by_satellite(df: pd.DataFrame, satellite: str) -> pd.DataFrame:
    """Return the unchanged CP5B validity audit with satellite/month identifiers."""
    out = magnetic_validity_table(df)
    out.insert(0, "analysis_month", ANALYSIS_MONTH)
    out.insert(0, "satellite", satellite)
    return out


def summaries_by_satellite(
    df: pd.DataFrame,
    satellite: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return unchanged CP5B footprint and concentration metrics with satellite/month identifiers."""
    summary = footprint_magnetic_summary(df)
    concentration = concentration_metrics(df)
    for table in (summary, concentration):
        table.insert(0, "analysis_month", ANALYSIS_MONTH)
        table.insert(0, "satellite", satellite)
    return summary, concentration


def ifc_counts(
    filtered_region: pd.DataFrame,
    preparation_counts: Mapping[str, int],
) -> dict[str, int]:
    """Normalize accepted IFC preparation counts and retained-value counts for one satellite."""
    flags = filtered_region["mep_IFC_on"]
    minus1 = int((flags == -1).sum())
    zero = int((flags == 0).sum())
    other = int((~flags.isin([-1, 0])).sum())
    result = {
        "regional_rows_before_ifc": int(preparation_counts["n_after_geo"]),
        "regional_rows_after_ifc": int(preparation_counts["n_after_ifc"]),
        "ifc_on_dropped": int(preparation_counts["n_ifc_on_dropped"]),
        "ifc_minus1_retained": minus1,
        "ifc_zero_retained": zero,
        "ifc_other_retained": other,
    }
    if result["regional_rows_after_ifc"] != len(filtered_region):
        raise ValueError("IFC row accounting does not match the filtered regional frame")
    if minus1 != int(preparation_counts["n_ifc_minus1"]):
        raise ValueError("retained mep_IFC_on == -1 count does not match preparation accounting")
    if minus1 + zero + other != len(filtered_region):
        raise ValueError("retained IFC value counts do not reconcile with the filtered frame")
    return result


def omni_fit_flag_diagnostic(
    df: pd.DataFrame,
    satellite: str,
    footprint_col: str = "in_top10_5deg",
) -> pd.DataFrame:
    """Count every observed omni-fit flag regionally and inside the principal footprint.

    The function is diagnostic only: it subsets for counting but never returns filtered science data.
    """
    if "mep_omni_flux_flag_fit" not in df.columns:
        raise KeyError("required mep_omni_flux_flag_fit column is missing")
    if footprint_col not in df.columns:
        raise KeyError(f"required footprint column is missing: {footprint_col}")

    rows: list[dict[str, object]] = []
    scopes = (
        ("regional_sample", df),
        ("top10_5deg_mean_footprint", df.loc[df[footprint_col].astype(bool)]),
    )
    for scope, subset in scopes:
        total = int(len(subset))
        counts = subset["mep_omni_flux_flag_fit"].value_counts(dropna=False).sort_index()
        for flag_value, count in counts.items():
            rows.append(
                {
                    "satellite": satellite,
                    "analysis_month": ANALYSIS_MONTH,
                    "scope": scope,
                    "flag_value": flag_value,
                    "sample_count": int(count),
                    "scope_total": total,
                    "fraction": float(count / total) if total else float("nan"),
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "satellite",
            "analysis_month",
            "scope",
            "flag_value",
            "sample_count",
            "scope_total",
            "fraction",
        ],
    )


def evaluate_satellite_support(row: Mapping[str, object]) -> tuple[bool, bool]:
    """Apply the predeclared CP5C per-satellite criteria to one principal-case row."""
    btot = float(row["btot_separation_metric"])
    low_btot = (
        btot > 0.0
        and float(row["btot_fraction_below_regional_q25"]) > 0.50
        and float(row["btot_regional_fraction_to_capture_90pct"]) <= 0.50
    )
    dominance = (
        btot > float(row["l_igrf_separation_metric"])
        and btot > abs(float(row["mlt_separation_metric"]))
    )
    return bool(low_btot), bool(dominance)


def classify_generality(summary: pd.DataFrame) -> str:
    """Classify the five-satellite principal case with the frozen CP5C rubric."""
    if len(summary) != len(SATELLITES):
        raise ValueError(f"CP5C classification requires exactly {len(SATELLITES)} satellite rows")
    low_count = int(summary["low_btot_support"].astype(bool).sum())
    dominance_count = int(summary["btot_dominance_support"].astype(bool).sum())
    reversed_count = int((summary["btot_separation_metric"].astype(float) < 0.0).sum())
    if low_count >= 4 and dominance_count >= 4:
        return "CONSISTENT"
    if low_count <= 1 or reversed_count >= 4:
        return "INCONSISTENT"
    return "MIXED"


def assert_cross_satellite_schema_safe(columns: Iterable[str]) -> None:
    """Reject absolute/cross-satellite flux fields from a CP5C comparison schema."""
    allowed_flag = "absolute_flux_comparison_allowed"
    forbidden = [str(c) for c in columns if "flux" in str(c).lower() and str(c) != allowed_flag]
    if forbidden:
        raise ValueError(f"absolute cross-satellite flux fields are forbidden: {forbidden}")


def _keyed(table: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Return a deterministically keyed copy used only by the reference comparator."""
    return table.sort_values(keys).set_index(keys)


def _assert_exact_columns(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
    keys: list[str],
    columns: list[str],
) -> None:
    actual_keyed = _keyed(actual, keys)
    expected_keyed = _keyed(expected, keys)
    if not actual_keyed.index.equals(expected_keyed.index):
        raise AssertionError(f"reference keys differ for {keys}")
    for column in columns:
        if not actual_keyed[column].equals(expected_keyed[column]):
            raise AssertionError(f"reference exact column differs: {column}")


def _assert_float_columns(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
    keys: list[str],
    columns: list[str],
) -> None:
    actual_keyed = _keyed(actual, keys)
    expected_keyed = _keyed(expected, keys)
    if not actual_keyed.index.equals(expected_keyed.index):
        raise AssertionError(f"reference keys differ for {keys}")
    for column in columns:
        np.testing.assert_allclose(
            actual_keyed[column].to_numpy(dtype="float64"),
            expected_keyed[column].to_numpy(dtype="float64"),
            rtol=REFERENCE_RTOL,
            atol=REFERENCE_ATOL,
            equal_nan=True,
            err_msg=f"NOAA-19 floating reference differs: {column}",
        )


def compare_noaa19_reference(actual: ReferenceBundle, expected: ReferenceBundle) -> None:
    """Enforce the predeclared NOAA-19 exact and fixed-tolerance comparisons."""
    if set(actual.cell_sets) != set(expected.cell_sets):
        raise AssertionError("NOAA-19 footprint case names differ")
    for case in expected.cell_sets:
        if actual.cell_sets[case] != expected.cell_sets[case]:
            raise AssertionError(f"NOAA-19 selected cell coordinates differ: {case}")

    _assert_exact_columns(
        actual.validity,
        expected.validity,
        ["variable_name"],
        ["rows_total", "rows_valid", "rows_invalid"],
    )
    _assert_float_columns(
        actual.validity,
        expected.validity,
        ["variable_name"],
        ["valid_min", "valid_max"],
    )

    summary_keys = ["comparison_case", "magnetic_variable"]
    _assert_exact_columns(
        actual.footprint_summary,
        expected.footprint_summary,
        summary_keys,
        ["inside_count", "outside_count"],
    )
    _assert_float_columns(
        actual.footprint_summary,
        expected.footprint_summary,
        summary_keys,
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
    )

    concentration_keys = ["metric", "footprint", "variable"]
    actual_concentration = _keyed(actual.concentration, concentration_keys)
    expected_concentration = _keyed(expected.concentration, concentration_keys)
    if not actual_concentration.index.equals(expected_concentration.index):
        raise AssertionError("NOAA-19 concentration metric names differ")
    np.testing.assert_allclose(
        actual_concentration["value"].to_numpy(dtype="float64"),
        expected_concentration["value"].to_numpy(dtype="float64"),
        rtol=REFERENCE_RTOL,
        atol=REFERENCE_ATOL,
        equal_nan=True,
        err_msg="NOAA-19 concentration values differ",
    )
