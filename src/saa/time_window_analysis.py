"""Time-window sensitivity analysis (Checkpoint 4D).

Methodological question: *how stable is the threshold-defined candidate high-flux footprint as the
aggregation time window changes* (one day -> 7 days -> 14 days -> full month, plus four disjoint
weekly windows), with **satellite, channel, region, grid logic and threshold machinery fixed**?

This reuses the accepted CP4A gridding (:mod:`saa.aggregate`) and CP4B threshold machinery
(:mod:`saa.threshold_analysis`). The only genuinely new ingredient is a **per-window, per-grid
coverage threshold**: a one-day map is orbit-track sparse, so blindly reusing the CP4A monthly
``>=30`` cut would be wrong. Instead the minimum-sample threshold is scaled with exposure, anchored
to CP4A (``>=30`` samples over 31 days ~ 1 sample/day/cell):

    ``min_samples = max(COVERAGE_FLOOR, round((30/31) * day_count))``

so a full month reproduces CP4A's ``>=30`` while shorter windows relax proportionally. A
``coverage_warning`` flags one-day sparsity, low regional coverage, and few-selected-cell footprints
so coverage effects are never silently confused with physical/temporal variability.

Caveat preserved from CP4A/B/C: ``mep_IFC_on == -1`` rows are retained and remain **uninterpreted**.
Outputs are *time-window-dependent, threshold-defined footprints* and *area proxies* — **not** a final
SAA boundary/center, dose, health risk, or discovery.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from .grid_flux import DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE, DEFAULT_CHANNEL, prepare_region
from .aggregate import build_grid_table, add_coverage_mask, load_range
from .threshold_analysis import run_sensitivity, _pivot_to_2d, PERCENTILES

# ------------------------------------------------------------------ window definitions
#: Named aggregation windows.  ``day_count`` is filled by :func:`window_day_count`.
TIME_WINDOWS: list[dict] = [
    {"window_label": "day_2024-01-01",        "start_date": "2024-01-01", "end_date": "2024-01-01"},
    {"window_label": "days_2024-01-01_to_07", "start_date": "2024-01-01", "end_date": "2024-01-07"},
    {"window_label": "days_2024-01-01_to_14", "start_date": "2024-01-01", "end_date": "2024-01-14"},
    {"window_label": "month_2024-01",         "start_date": "2024-01-01", "end_date": "2024-01-31"},
    {"window_label": "week1",                 "start_date": "2024-01-01", "end_date": "2024-01-07"},
    {"window_label": "week2",                 "start_date": "2024-01-08", "end_date": "2024-01-14"},
    {"window_label": "week3",                 "start_date": "2024-01-15", "end_date": "2024-01-21"},
    {"window_label": "week4",                 "start_date": "2024-01-22", "end_date": "2024-01-28"},
]

#: The four cumulative windows that get saved regional Parquets + mean maps.
CUMULATIVE_LABELS = ["day_2024-01-01", "days_2024-01-01_to_07", "days_2024-01-01_to_14", "month_2024-01"]
WEEK_LABELS = ["week1", "week2", "week3", "week4"]

# coverage threshold anchored to CP4A (>=30 over 31 days ~ 1 sample/day/cell)
COVERAGE_RATE = 30.0 / 31.0
COVERAGE_FLOOR = 3

TIME_WINDOW_SENSITIVITY_COLUMNS = [
    "window_label", "start_date", "end_date", "day_count", "files_expected", "files_loaded",
    "grid_deg", "statistic_used", "threshold_label", "percentile_cutoff", "flux_cutoff_value",
    "cells_available_after_coverage_mask", "selected_cell_count", "selected_area_km2",
    "selected_area_fraction_of_covered_region", "centroid_lat_unweighted", "centroid_lon_unweighted",
    "centroid_lat_flux_weighted", "centroid_lon_flux_weighted", "peak_flux",
    "mean_flux_within_selected", "median_flux_within_selected", "total_flux_area_proxy",
    "coverage_threshold_used", "coverage_warning",
]


def window_day_count(start, end) -> int:
    return int((pd.Timestamp(end).normalize() - pd.Timestamp(start).normalize()).days) + 1


def region_cell_count(grid_deg: float, lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE) -> int:
    """Maximum number of grid cells covering the analysis region at ``grid_deg`` resolution."""
    n_lat = int(round((lat_range[1] - lat_range[0]) / grid_deg))
    n_lon = int(round((lon_range[1] - lon_range[0]) / grid_deg))
    return n_lat * n_lon


def choose_coverage_threshold(day_count: int) -> int:
    """Per-window minimum-sample coverage threshold (same for 5 deg and 2 deg, as in CP4A).

    Scaled with exposure and anchored to CP4A: ``max(COVERAGE_FLOOR, round((30/31)*day_count))``.
    """
    return int(max(COVERAGE_FLOOR, round(COVERAGE_RATE * day_count)))


# ------------------------------------------------------------------ loading / slicing
def add_obs_date(df: pd.DataFrame, time_col: str = "time") -> pd.DataFrame:
    """Add an ``obs_date`` column (UTC midnight of each record's day) for window slicing."""
    out = df.copy()
    out["obs_date"] = pd.to_datetime(out[time_col], utc=True).dt.normalize()
    return out


def slice_window(df: pd.DataFrame, start, end, date_col: str = "obs_date") -> pd.DataFrame:
    """Inclusive [start, end] day slice of a region frame carrying an ``obs_date`` column."""
    s = pd.Timestamp(start, tz="UTC").normalize()
    e = pd.Timestamp(end, tz="UTC").normalize()
    return df[(df[date_col] >= s) & (df[date_col] <= e)].copy()


def load_month_region(start="2024-01-01", end="2024-01-31", satellite="noaa19",
                      raw_dir="data/raw", channel=DEFAULT_CHANNEL):
    """Load the whole month once (real files), region+IFC filter, add ``obs_date``.

    Returns ``(region_df, loaded_dates)`` so each daily file is read exactly once and every window is
    a cheap in-memory slice. Missing days propagate from :func:`load_range`.
    """
    rl = load_range(start, end, satellite=satellite, raw_dir=raw_dir, channel=channel)
    region, _ = prepare_region(rl.df)
    region = add_obs_date(region)
    return region, rl.loaded_dates


# ------------------------------------------------------------------ per-window grids
def build_window_grids(region_df: pd.DataFrame, day_count: int, value_col: str = DEFAULT_CHANNEL):
    """Build 5 deg and 2 deg grid tables for a window's region frame, with the per-window mask.

    Returns ``(grids, threshold)`` where ``grids`` is a list of dicts with ``grid_deg, step, table,
    mask_col, coverage_threshold`` ready for :func:`run_time_window_sensitivity`.
    """
    threshold = choose_coverage_threshold(day_count)
    grids = []
    for grid_deg in (5.0, 2.0):
        mask_col = f"enough_samples_{int(grid_deg)}deg"
        table = build_grid_table(region_df, value_col=value_col, lat_step=grid_deg, lon_step=grid_deg)
        table = add_coverage_mask(table, threshold, mask_col)
        grids.append({"grid_deg": int(grid_deg), "step": grid_deg, "table": table,
                      "mask_col": mask_col, "coverage_threshold": threshold})
    return grids, threshold


def sample_count_distribution(table: pd.DataFrame) -> dict:
    """Summary of the per-cell ``sample_count`` distribution (for reporting before masking)."""
    sc = table["sample_count"].to_numpy()
    if sc.size == 0:
        return {"n_cells": 0}
    return {
        "n_cells": int(sc.size), "min": int(sc.min()), "max": int(sc.max()),
        "median": float(np.median(sc)),
        "p10": float(np.percentile(sc, 10)), "p90": float(np.percentile(sc, 90)),
    }


# ------------------------------------------------------------------ coverage warning
def coverage_warning(grid_deg: int, cells_available: int, selected_cell_count: int,
                     day_count: int, low_coverage_frac: float = 0.5) -> str:
    """Honest per-row flag separating coverage/sampling effects from physical variability."""
    parts = []
    if day_count == 1:
        parts.append("one-day orbit-track sparse")
    max_cells = region_cell_count(grid_deg)
    frac = cells_available / max_cells if max_cells else 0.0
    if frac < low_coverage_frac:
        parts.append(f"low_coverage:{cells_available}/{max_cells} cells ({frac:.0%})")
    if selected_cell_count < 3:
        parts.append(f"few_selected_cells(n={selected_cell_count})")
    return "; ".join(parts)


# ------------------------------------------------------------------ sensitivity sweep
def run_time_window_sensitivity(window_specs: list[dict]) -> pd.DataFrame:
    """Run the CP4B sweep per window and stack with window/coverage columns.

    Each spec: ``{window_label, start_date, end_date, day_count, files_expected, files_loaded,
    grids:[{grid_deg, step, table, mask_col, coverage_threshold}, ...]}``.  Returns a tidy frame with
    :data:`TIME_WINDOW_SENSITIVITY_COLUMNS` (8 windows x 2 grids x 2 stats x 5 thresholds = 160 rows).
    """
    frames = []
    for spec in window_specs:
        grids = [(g["grid_deg"], g["step"], g["table"], g["mask_col"]) for g in spec["grids"]]
        df = run_sensitivity(grids).drop(columns=["notes"])
        df.insert(0, "files_loaded", spec["files_loaded"])
        df.insert(0, "files_expected", spec["files_expected"])
        df.insert(0, "day_count", spec["day_count"])
        df.insert(0, "end_date", spec["end_date"])
        df.insert(0, "start_date", spec["start_date"])
        df.insert(0, "window_label", spec["window_label"])
        thr = {g["grid_deg"]: g["coverage_threshold"] for g in spec["grids"]}
        df["coverage_threshold_used"] = df["grid_deg"].map(thr).astype(int)
        df["coverage_warning"] = [
            coverage_warning(int(r.grid_deg), int(r.cells_available_after_coverage_mask),
                             int(r.selected_cell_count), int(spec["day_count"]))
            for r in df.itertuples()
        ]
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    return out[TIME_WINDOW_SENSITIVITY_COLUMNS]


def save_sensitivity(df: pd.DataFrame, csv_path, parquet_path) -> None:
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)


# ------------------------------------------------------------------ plotting
def plot_window_mean_map(table, step, mask_col, save_path, title,
                         lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Single coverage-masked log10 mean-flux heatmap for one time window (blank = no data/masked)."""
    lon_e, lat_e, base = _pivot_to_2d(table, "mean_flux", step, lat_range, lon_range, mask_col)
    data = np.where(base > 0, base, np.nan)
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    finite = data[np.isfinite(data)]
    norm = LogNorm(vmin=finite.min(), vmax=finite.max()) if finite.size else None
    mesh = ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(data), cmap="viridis", norm=norm, shading="flat")
    cbar = fig.colorbar(mesh, ax=ax, shrink=0.9)
    cbar.set_label("mean mep_omni_flux_p1 [#/cm2-s-str-MeV] log10", fontsize=8)
    ax.set_xlim(lon_e[0], lon_e[-1]); ax.set_ylim(lat_e[0], lat_e[-1])
    ax.set_xlabel("longitude [deg] ([-180,180))"); ax.set_ylabel("latitude [deg]")
    ax.set_title(title, fontsize=9)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_sample_count_panels(labelled_tables, step, save_path, title,
                             lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Side-by-side linear sample_count heatmaps for several windows (coverage growth visualisation).

    ``labelled_tables`` is a list of ``(label, table)``.
    """
    n = len(labelled_tables)
    fig, axes = plt.subplots(1, n, figsize=(4.0 * n, 5.0), squeeze=False)
    vmax = max((t["sample_count"].max() for _, t in labelled_tables if len(t)), default=1)
    for ax, (label, table) in zip(axes[0], labelled_tables):
        lon_e, lat_e, base = _pivot_to_2d(table, "sample_count", step, lat_range, lon_range)
        mesh = ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(base), cmap="magma",
                             vmin=0, vmax=vmax, shading="flat")
        ax.set_title(label, fontsize=8)
        ax.set_xlabel("lon"); ax.set_ylabel("lat")
    fig.colorbar(mesh, ax=axes[0].tolist(), shrink=0.8, label="sample_count (linear)")
    fig.suptitle(title, fontsize=10)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_mean_map_panels(labelled_tables, step, mask_col, save_path, title,
                         lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Side-by-side coverage-masked log10 mean-flux heatmaps for several windows (shared color scale).

    ``labelled_tables`` is a list of ``(label, table)``; ``mask_col`` is each table's coverage column.
    """
    n = len(labelled_tables)
    fig, axes = plt.subplots(1, n, figsize=(4.0 * n, 5.0), squeeze=False)
    panels = []
    vmin, vmax = np.inf, -np.inf
    for label, table in labelled_tables:
        lon_e, lat_e, base = _pivot_to_2d(table, "mean_flux", step, lat_range, lon_range, mask_col)
        data = np.where(base > 0, base, np.nan)
        finite = data[np.isfinite(data)]
        if finite.size:
            vmin = min(vmin, finite.min()); vmax = max(vmax, finite.max())
        panels.append((label, lon_e, lat_e, data))
    norm = LogNorm(vmin=vmin, vmax=vmax) if np.isfinite(vmin) and np.isfinite(vmax) else None
    for ax, (label, lon_e, lat_e, data) in zip(axes[0], panels):
        mesh = ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(data), cmap="viridis", norm=norm, shading="flat")
        ax.set_title(label, fontsize=8); ax.set_xlabel("lon"); ax.set_ylabel("lat")
    fig.colorbar(mesh, ax=axes[0].tolist(), shrink=0.8, label="mean mep_omni_flux_p1 log10")
    fig.suptitle(title, fontsize=10)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_centroid_by_window(sens_df, threshold_label, save_path, grid_deg=5, statistic="mean_flux",
                            labels=None):
    """Flux-weighted centroid of one threshold across windows (centroid stability across windows)."""
    sub = sens_df[(sens_df.grid_deg == grid_deg) & (sens_df.statistic_used == statistic)
                  & (sens_df.threshold_label == threshold_label)]
    if labels is not None:
        sub = sub[sub.window_label.isin(labels)]
        sub = sub.set_index("window_label").loc[[l for l in labels if l in set(sub.window_label)]].reset_index()
    fig, ax = plt.subplots(figsize=(7.0, 6.2))
    ax.plot(sub.centroid_lon_flux_weighted, sub.centroid_lat_flux_weighted, "-o", ms=6, color="#333333")
    for _, r in sub.iterrows():
        ax.annotate(r.window_label, (r.centroid_lon_flux_weighted, r.centroid_lat_flux_weighted),
                    fontsize=6.5, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("flux-weighted centroid lon [deg]"); ax.set_ylabel("flux-weighted centroid lat [deg]")
    ax.set_title(f"centroid stability across time windows ({threshold_label}, {grid_deg}deg {statistic})\n"
                 "time-window-dependent / exploratory; not a final SAA center", fontsize=9)
    ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_area_by_window(sens_df, save_path, grid_deg=5, statistic="mean_flux", labels=None):
    """Selected area proxy vs time window, one line per threshold (area stability across windows)."""
    sub = sens_df[(sens_df.grid_deg == grid_deg) & (sens_df.statistic_used == statistic)]
    if labels is None:
        labels = CUMULATIVE_LABELS
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    x = np.arange(len(labels))
    for _, lbl in PERCENTILES:
        ys = []
        for w in labels:
            row = sub[(sub.window_label == w) & (sub.threshold_label == lbl)]
            ys.append(float(row.selected_area_km2.iloc[0]) if len(row) else np.nan)
        ax.plot(x, np.array(ys) / 1e6, "-o", ms=5, label=lbl)
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("selected area proxy [million km2]")
    ax.set_title(f"selected-area stability across time windows ({grid_deg}deg {statistic})\n"
                 "area proxy; exploratory; not a physical boundary", fontsize=9)
    ax.legend(fontsize=7, title="threshold"); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_weekly_centroids(sens_df, save_path, threshold_label="top10", grid_deg=5, statistic="mean_flux"):
    """Flux-weighted centroids of the four disjoint weekly windows (weekly stability)."""
    sub = sens_df[(sens_df.grid_deg == grid_deg) & (sens_df.statistic_used == statistic)
                  & (sens_df.threshold_label == threshold_label)
                  & (sens_df.window_label.isin(WEEK_LABELS))]
    fig, ax = plt.subplots(figsize=(7.0, 6.2))
    for _, r in sub.iterrows():
        ax.plot(r.centroid_lon_flux_weighted, r.centroid_lat_flux_weighted, "o", ms=9)
        ax.annotate(r.window_label, (r.centroid_lon_flux_weighted, r.centroid_lat_flux_weighted),
                    fontsize=8, xytext=(5, 5), textcoords="offset points")
    ax.set_xlabel("flux-weighted centroid lon [deg]"); ax.set_ylabel("flux-weighted centroid lat [deg]")
    ax.set_title(f"weekly window centroids ({threshold_label}, {grid_deg}deg {statistic})\n"
                 "disjoint weeks; exploratory; not a final SAA center", fontsize=9)
    ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
