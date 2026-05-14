"""Threshold sensitivity analysis on the CP4A monthly coverage-masked grid tables (Checkpoint 4B).

Methodological question: *how much do the estimated center, area, and intensity of the candidate
high-flux region change when it is defined with different flux thresholds?* This operates ONLY on
the already-accepted CP4A grid tables (it does not regenerate flux from raw data) and uses ONLY
cells passing the CP4A coverage mask.

Key choices:

* **Cell area** is the spherical-cap approximation
  ``area = R^2 * dlon_rad * (sin(lat_north) - sin(lat_south))`` with ``R = 6371 km`` — never raw
  cell count (lat/lon cells are not equal-area).
* **Two centroids** are reported: unweighted (mean of selected cell centers) and flux-weighted
  (weighted by the statistic being thresholded). Longitude is averaged directly; acceptable because
  the region (lon -100..+20) is limited and far from the +/-180 wrap — documented as an assumption.

Caveat preserved from CP4A: ``mep_IFC_on == -1`` rows were retained and remain **uninterpreted**;
this analysis does not resolve them. Outputs are *method-dependent, threshold-defined footprints* and
*area proxies* — **not** a final SAA boundary/center, dose, health risk, or discovery.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from .grid_flux import DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE

R_EARTH_KM = 6371.0
#: (percentile cutoff, label) — "top 20%" == values >= 80th percentile, etc.
PERCENTILES: list[tuple[int, str]] = [(80, "top20"), (90, "top10"), (95, "top5"), (98, "top2"), (99, "top1")]
STATISTICS = ("mean_flux", "median_flux")

SENSITIVITY_COLUMNS = [
    "grid_deg", "statistic_used", "threshold_label", "percentile_cutoff", "flux_cutoff_value",
    "cells_available_after_coverage_mask", "selected_cell_count", "selected_area_km2",
    "selected_area_fraction_of_covered_region", "centroid_lat_unweighted", "centroid_lon_unweighted",
    "centroid_lat_flux_weighted", "centroid_lon_flux_weighted", "peak_flux",
    "mean_flux_within_selected", "median_flux_within_selected", "total_flux_area_proxy", "notes",
]


# ---------------------------------------------------------------- loading / coverage
def load_grid_table(path) -> pd.DataFrame:
    """Load a CP4A grid table (parquet)."""
    return pd.read_parquet(path)


def coverage_passed(table: pd.DataFrame, mask_col: str) -> pd.DataFrame:
    """Return only the cells passing the CP4A coverage mask."""
    if mask_col not in table.columns:
        raise KeyError(f"coverage mask column {mask_col!r} not in grid table")
    return table[table[mask_col].astype(bool)].copy()


# ---------------------------------------------------------------- geometry
def cell_area_km2(lat_center, lat_step: float, lon_step: float, R: float = R_EARTH_KM):
    """Spherical-cap area of lat/lon cell(s) centered at ``lat_center`` (km^2)."""
    latc = np.asarray(lat_center, dtype="float64")
    north = np.radians(latc + lat_step / 2.0)
    south = np.radians(latc - lat_step / 2.0)
    return (R ** 2) * np.radians(lon_step) * (np.sin(north) - np.sin(south))


def add_cell_area(table: pd.DataFrame, lat_step: float, lon_step: float) -> pd.DataFrame:
    out = table.copy()
    out["cell_area_km2"] = cell_area_km2(out["lat_bin_center"].to_numpy(), lat_step, lon_step)
    return out


def haversine_km(lat1, lon1, lat2, lon2, R: float = R_EARTH_KM) -> float:
    """Great-circle distance between two lat/lon points (km) — for reporting centroid shifts."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlmb = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return float(2 * R * np.arcsin(np.sqrt(a)))


# ---------------------------------------------------------------- thresholds / centroids
def percentile_threshold(values, percentile: float) -> float:
    return float(np.percentile(np.asarray(values, dtype="float64"), percentile))


def select_high_flux(covered: pd.DataFrame, stat_col: str, cutoff: float) -> pd.DataFrame:
    """Cells whose statistic is >= the cutoff."""
    return covered[covered[stat_col] >= cutoff].copy()


def unweighted_centroid(cells: pd.DataFrame) -> tuple[float, float]:
    return float(cells["lat_bin_center"].mean()), float(cells["lon_bin_center"].mean())


def flux_weighted_centroid(cells: pd.DataFrame, stat_col: str) -> tuple[float, float]:
    w = cells[stat_col].to_numpy(dtype="float64")
    lat = cells["lat_bin_center"].to_numpy(dtype="float64")
    lon = cells["lon_bin_center"].to_numpy(dtype="float64")
    sw = w.sum()
    if not np.isfinite(sw) or sw <= 0:
        return float("nan"), float("nan")
    return float((lat * w).sum() / sw), float((lon * w).sum() / sw)


# ---------------------------------------------------------------- per-threshold record
def analyze_threshold(covered: pd.DataFrame, stat_col: str, percentile: int, label: str,
                      grid_deg: float, total_covered_area: float) -> dict:
    cutoff = percentile_threshold(covered[stat_col], percentile)
    sel = select_high_flux(covered, stat_col, cutoff)
    area = float(sel["cell_area_km2"].sum())
    ulat, ulon = unweighted_centroid(sel)
    wlat, wlon = flux_weighted_centroid(sel, stat_col)
    proxy = float((sel[stat_col].to_numpy("float64") * sel["cell_area_km2"].to_numpy("float64")).sum())
    return {
        "grid_deg": grid_deg, "statistic_used": stat_col, "threshold_label": label,
        "percentile_cutoff": percentile, "flux_cutoff_value": cutoff,
        "cells_available_after_coverage_mask": int(len(covered)),
        "selected_cell_count": int(len(sel)),
        "selected_area_km2": area,
        "selected_area_fraction_of_covered_region": area / total_covered_area if total_covered_area > 0 else float("nan"),
        "centroid_lat_unweighted": ulat, "centroid_lon_unweighted": ulon,
        "centroid_lat_flux_weighted": wlat, "centroid_lon_flux_weighted": wlon,
        "peak_flux": float(sel[stat_col].max()),
        "mean_flux_within_selected": float(sel[stat_col].mean()),
        "median_flux_within_selected": float(sel[stat_col].median()),
        "total_flux_area_proxy": proxy,
        "notes": "coverage-masked; spherical-cap area; lon avg ok for limited region; mep_IFC_on==-1 uninterpreted",
    }


def run_sensitivity(grids: list[tuple]) -> pd.DataFrame:
    """Run the full grid x statistic x percentile sweep.

    ``grids`` is a list of ``(grid_deg, step, table, mask_col)``. Returns a tidy DataFrame with
    :data:`SENSITIVITY_COLUMNS` (2 grids x 2 statistics x 5 thresholds = 20 rows for the CP4B set).
    """
    rows = []
    for grid_deg, step, table, mask_col in grids:
        t = add_cell_area(table, step, step)
        covered = coverage_passed(t, mask_col)
        total_area = float(covered["cell_area_km2"].sum())
        for stat in STATISTICS:
            for pct, label in PERCENTILES:
                rows.append(analyze_threshold(covered, stat, pct, label, grid_deg, total_area))
    return pd.DataFrame(rows, columns=SENSITIVITY_COLUMNS)


def save_sensitivity(df: pd.DataFrame, csv_path, parquet_path) -> None:
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)


# ---------------------------------------------------------------- plotting
def _pivot_to_2d(table, value_col, step, lat_range, lon_range, mask_col=None):
    lat_min, lat_max = lat_range
    lon_min, lon_max = lon_range
    n_lat = int(round((lat_max - lat_min) / step))
    n_lon = int(round((lon_max - lon_min) / step))
    arr = np.full((n_lat, n_lon), np.nan)
    for _, r in table.iterrows():
        if mask_col is not None and not bool(r[mask_col]):
            continue
        i = int(round((r["lat_bin_center"] - (lat_min + step / 2)) / step))
        j = int(round((r["lon_bin_center"] - (lon_min + step / 2)) / step))
        if 0 <= i < n_lat and 0 <= j < n_lon:
            arr[i, j] = r[value_col]
    lat_edges = np.linspace(lat_min, lat_max, n_lat + 1)
    lon_edges = np.linspace(lon_min, lon_max, n_lon + 1)
    return lon_edges, lat_edges, arr


_LEVEL_COLORS = {"top20": "#1f77b4", "top10": "#2ca02c", "top5": "#ff7f0e", "top2": "#d62728", "top1": "#9467bd"}
_LEVEL_SIZES = {"top20": 150, "top10": 95, "top5": 58, "top2": 33, "top1": 15}


def plot_threshold_overlay(table, stat_col, step, mask_col, save_path, title,
                           lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Base coverage-masked flux map (grey, log10) + nested open-circle overlays for each top-X% set
    and an 'x' at each set's flux-weighted centroid."""
    covered = coverage_passed(add_cell_area(table, step, step), mask_col)
    lon_e, lat_e, base = _pivot_to_2d(table, stat_col, step, lat_range, lon_range, mask_col)
    data = np.where(base > 0, base, np.nan)

    fig, ax = plt.subplots(figsize=(7.6, 6.3))
    finite = data[np.isfinite(data)]
    norm = LogNorm(vmin=finite.min(), vmax=finite.max()) if finite.size else None
    mesh = ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(data), cmap="Greys", norm=norm, shading="flat")
    cbar = fig.colorbar(mesh, ax=ax, shrink=0.9)
    cbar.set_label(f"{stat_col} [#/cm2-s-str-MeV] log10 (coverage-masked base)", fontsize=8)

    for pct, label in PERCENTILES:
        cutoff = percentile_threshold(covered[stat_col], pct)
        sel = select_high_flux(covered, stat_col, cutoff)
        ax.scatter(sel["lon_bin_center"], sel["lat_bin_center"], s=_LEVEL_SIZES[label],
                   facecolors="none", edgecolors=_LEVEL_COLORS[label], linewidths=1.3,
                   label=f"{label} (>= {cutoff:.1f}, n={len(sel)})")
        wlat, wlon = flux_weighted_centroid(sel, stat_col)
        ax.plot(wlon, wlat, marker="x", color=_LEVEL_COLORS[label], ms=9, mew=2.2)

    ax.set_xlim(lon_e[0], lon_e[-1]); ax.set_ylim(lat_e[0], lat_e[-1])
    ax.set_xlabel("longitude [deg]  ([-180,180))"); ax.set_ylabel("latitude [deg]")
    ax.set_title(title, fontsize=9)
    ax.legend(fontsize=6.5, loc="lower left", framealpha=0.9, title="x = flux-weighted centroid")
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    return ax


def plot_centroid_shift(sens_df, save_path):
    """Flux-weighted centroid path as threshold tightens (top20 -> top1) for each grid x statistic."""
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    for grid_deg in (5, 2):
        for stat in STATISTICS:
            sub = sens_df[(sens_df.grid_deg == grid_deg) & (sens_df.statistic_used == stat)] \
                .sort_values("percentile_cutoff")
            ax.plot(sub.centroid_lon_flux_weighted, sub.centroid_lat_flux_weighted,
                    marker="o", ms=5, label=f"{grid_deg}deg {stat}")
            for _, r in sub.iterrows():
                ax.annotate(r.threshold_label.replace("top", ""),
                            (r.centroid_lon_flux_weighted, r.centroid_lat_flux_weighted), fontsize=6)
    ax.set_xlabel("flux-weighted centroid lon [deg]"); ax.set_ylabel("flux-weighted centroid lat [deg]")
    ax.set_title("flux-weighted centroid shift vs threshold (labels = top X%)\n"
                 "method-dependent / threshold-defined, exploratory", fontsize=9)
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    return ax


# ---------------------------------------------------------------- channel sensitivity (CP4C)
CHANNEL_SENSITIVITY_COLUMNS = (
    ["channel"] + [c for c in SENSITIVITY_COLUMNS if c != "notes"]
    + ["channel_units", "channel_metadata_note"]
)


def run_channel_sensitivity(channel_specs: list[dict]) -> pd.DataFrame:
    """Run :func:`run_sensitivity` per channel and stack with channel/units/metadata columns.

    ``channel_specs`` is a list of ``{"channel", "units", "note", "grids"}`` where ``grids`` is the
    ``[(grid_deg, step, table, mask_col), ...]`` list expected by :func:`run_sensitivity` (each
    table's ``mean_flux``/``median_flux`` are that channel's statistics). Returns a tidy DataFrame
    with :data:`CHANNEL_SENSITIVITY_COLUMNS` (3 channels x 2 grids x 2 stats x 5 thresholds = 60 rows).
    """
    frames = []
    for spec in channel_specs:
        df = run_sensitivity(spec["grids"]).drop(columns=["notes"])
        df.insert(0, "channel", spec["channel"])
        df["channel_units"] = spec["units"]
        df["channel_metadata_note"] = spec["note"]
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    return out[CHANNEL_SENSITIVITY_COLUMNS]
