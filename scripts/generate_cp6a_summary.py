#!/usr/bin/env python3
"""Regenerate the git-ignored CP6A synthesis table from accepted checkpoint tables."""
from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from saa.threshold_analysis import haversine_km  # noqa: E402
from saa.viewer_export import build_viewer_payload  # noqa: E402

TABLES = ROOT / "outputs" / "tables"


def _case(table: pd.DataFrame, **filters: object) -> pd.Series:
    mask = pd.Series(True, index=table.index)
    for column, value in filters.items():
        mask &= table[column] == value
    rows = table.loc[mask]
    if len(rows) != 1:
        raise ValueError(f"expected one row for {filters}, found {len(rows)}")
    return rows.iloc[0]


def _viewer_case(payload: dict, experiment: str, **filters: object) -> dict:
    rows = [
        row
        for row in payload["experiments"][experiment]["configurations"]
        if all(row["values"].get(key) == value for key, value in filters.items())
    ]
    if len(rows) != 1:
        raise ValueError(f"expected one viewer row for {experiment} {filters}, found {len(rows)}")
    return rows[0]


def _max_viewer_pairwise_km(rows: list[dict]) -> float:
    distances = [
        haversine_km(
            left["metrics"]["centroid_lat"],
            left["metrics"]["centroid_lon"],
            right["metrics"]["centroid_lat"],
            right["metrics"]["centroid_lon"],
        )
        for left, right in combinations(rows, 2)
    ]
    return max(distances)

def build_summary(table_dir: Path = TABLES) -> pd.DataFrame:
    """Build the five-row CP6A synthesis from validated CP4B–CP5B artifacts."""
    viewer = build_viewer_payload(table_dir)
    cp5b_summary = pd.read_parquet(table_dir / "cp5b_footprint_magnetic_summary.parquet")
    cp5b_concentration = pd.read_csv(table_dir / "cp5b_magnetic_concentration_metrics.csv")

    top20 = _viewer_case(
        viewer, "threshold", grid_deg=5, statistic_used="mean_flux", threshold_label="top20"
    )
    top1 = _viewer_case(
        viewer, "threshold", grid_deg=5, statistic_used="mean_flux", threshold_label="top1"
    )
    threshold_shift = haversine_km(
        top20["metrics"]["centroid_lat"],
        top20["metrics"]["centroid_lon"],
        top1["metrics"]["centroid_lat"],
        top1["metrics"]["centroid_lon"],
    )
    area_ratio = top20["metrics"]["selected_area_km2"] / top1["metrics"]["selected_area_km2"]

    channel_rows = [
        _viewer_case(
            viewer, "channel", channel=channel, grid_deg=5,
            statistic_used="mean_flux", threshold_label="top10",
        )
        for channel in ("mep_omni_flux_p1", "mep_omni_flux_p2", "mep_omni_flux_p3")
    ]
    channel_spread = _max_viewer_pairwise_km(channel_rows)

    day = _viewer_case(
        viewer, "time", window_label="day_2024-01-01", grid_deg=5,
        statistic_used="mean_flux", threshold_label="top10",
    )
    month = _viewer_case(
        viewer, "time", window_label="month_2024-01", grid_deg=5,
        statistic_used="mean_flux", threshold_label="top10",
    )
    day_month = haversine_km(
        day["metrics"]["centroid_lat"], day["metrics"]["centroid_lon"],
        month["metrics"]["centroid_lat"], month["metrics"]["centroid_lon"],
    )
    weekly_rows = [
        _viewer_case(
            viewer, "time", window_label=window, grid_deg=5,
            statistic_used="mean_flux", threshold_label="top10",
        )
        for window in ("week1", "week2", "week3", "week4")
    ]
    weekly_spread = _max_viewer_pairwise_km(weekly_rows)

    satellite_rows = [
        _viewer_case(
            viewer, "satellite", satellite=satellite, grid_deg=5,
            statistic_used="mean_flux", threshold_label="top10",
        )
        for satellite in ("noaa15", "noaa18", "noaa19", "metop01", "metop03")
    ]
    satellite_spread = _max_viewer_pairwise_km(satellite_rows)

    def separation(variable: str) -> float:
        return float(
            _case(
                cp5b_summary,
                comparison_case="top10_5deg_mean",
                magnetic_variable=variable,
            ).separation_metric
        )

    capture90 = float(
        _case(
            cp5b_concentration,
            metric="regional_fraction_to_capture_90pct",
            footprint="top10",
            variable="Btot_sat",
        ).value
    )

    columns = [
        "result_area",
        "checkpoint_source",
        "input_data",
        "metric",
        "main_numeric_result",
        "interpretation_allowed",
        "overclaim_to_avoid",
        "supporting_table_or_figure",
        "paper_section_candidate",
    ]
    rows = [
        [
            "threshold sensitivity",
            "CP4B",
            "NOAA-19 Jan-2024 p1",
            "top20-to-top1 centroid shift and area ratio (5deg mean)",
            f"{threshold_shift:.0f} km; {area_ratio:.1f}x",
            "footprint centroid and selected area are threshold-dependent",
            "a final SAA boundary or true center",
            "cp4b_threshold_sensitivity.parquet",
            "6.2",
        ],
        [
            "channel sensitivity",
            "CP4C",
            "NOAA-19 Jan-2024 p1/p2/p3",
            "maximum top10 5deg mean pairwise centroid distance",
            f"{channel_spread:.0f} km",
            "footprint locations broadly agree across the tested channels",
            "absolute flux equivalence across energy channels",
            "cp4c_channel_threshold_sensitivity.parquet",
            "6.3",
        ],
        [
            "time-window sensitivity",
            "CP4D",
            "NOAA-19 Jan-2024 p1",
            "day-to-month drift and weekly maximum spread (top10 5deg mean)",
            f"{day_month:.0f} km; weekly {weekly_spread:.0f} km",
            "coverage filling explains much of the early-window movement",
            "seasonal or long-term stability",
            "cp4d_time_window_threshold_sensitivity.parquet",
            "6.4",
        ],
        [
            "satellite consistency",
            "CP4F",
            "five satellites, Jan-2024 p1",
            "maximum pairwise centroid distance (top10 5deg mean)",
            f"{satellite_spread:.0f} km",
            "within-satellite percentile footprints broadly overlap",
            "cross-satellite absolute-flux comparison",
            "cp4f_pairwise_centroid_distances.parquet",
            "6.5",
        ],
        [
            "magnetic-coordinate framing",
            "CP5B",
            "NOAA-19 Jan-2024 p1",
            "Btot/L/MLT separation and Btot regional fraction capturing 90%",
            (
                f"Btot {separation('Btot_sat'):.2f}; L {separation('L_IGRF'):.2f}; "
                f"MLT {separation('MLT'):.2f}; capture90 {capture90:.2f}"
            ),
            "descriptive co-location with low NOAA-provided IGRF field strength",
            "causality or a physical SAA threshold",
            "cp5b_footprint_magnetic_summary.parquet",
            "6.6",
        ],
    ]
    return pd.DataFrame(rows, columns=columns)


def main() -> None:
    summary = build_summary()
    TABLES.mkdir(parents=True, exist_ok=True)
    summary.to_csv(TABLES / "cp6a_key_results_summary.csv", index=False)
    summary.to_parquet(TABLES / "cp6a_key_results_summary.parquet", index=False)
    print(f"wrote CP6A synthesis rows: {len(summary)}")


if __name__ == "__main__":
    main()
