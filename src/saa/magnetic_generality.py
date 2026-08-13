"""Multi-satellite descriptive magnetic generality analysis (Checkpoint 5C).

CP5C applies the accepted CP4F satellite-specific particle-footprint definitions and the accepted
CP5B magnetic validity, separation, and concentration formulas to five January-2024 satellites.
Every magnetic rank is computed within one satellite. Absolute proton flux is not compared between
satellites, and no magnetic cutoff produced here defines a physical SAA boundary.
"""
from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .magnetic_framing import (
    add_footprint_flags,
    concentration_metrics,
    footprint_magnetic_summary,
    magnetic_validity_table,
)

SATELLITES: tuple[str, ...] = ("noaa15", "noaa18", "noaa19", "metop01", "metop03")
ANALYSIS_MONTH = "2024-01"


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
