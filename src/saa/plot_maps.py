"""Simple rectangular lon/lat heatmaps for exploratory SAA proton-flux maps (Checkpoint 3).

matplotlib only (no cartopy). Plots a :class:`saa.grid_flux.GridResult` as a ``pcolormesh`` over a
plain longitude/latitude grid. Flux statistics use a log color scale (clearly labelled); the
sample-count map uses a linear scale.

These are **exploratory, one-day** visualisations for pipeline validation — not scientific maps.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from .grid_flux import GridResult

# Light reference markers for context only (no coastlines without cartopy).
_REF_LON = 0.0   # prime meridian
_REF_LAT = 0.0   # equator


def plot_heatmap(
    grid: GridResult,
    stat: str = "mean",
    log: bool = True,
    cmap: str | None = None,
    title: str | None = None,
    save_path: str | None = None,
    ax: "plt.Axes | None" = None,
):
    """Plot one statistic ('mean' | 'median' | 'count') from a GridResult.

    For 'mean'/'median', ``log=True`` applies a log10 color scale and masks non-positive/empty
    cells. For 'count', a linear scale is used regardless of ``log``.
    """
    is_count = stat == "count"
    data = np.array(getattr(grid, stat), dtype="float64")

    created = ax is None
    if created:
        fig, ax = plt.subplots(figsize=(7.2, 6.0))
    else:
        fig = ax.figure

    if is_count:
        data = np.where(data > 0, data, np.nan)
        norm = None
        cmap = cmap or "magma"
        cbar_label = "samples per grid cell"
    else:
        cmap = cmap or "viridis"
        if log:
            data = np.where(data > 0, data, np.nan)
            finite = data[np.isfinite(data)]
            norm = LogNorm(vmin=finite.min(), vmax=finite.max()) if finite.size else None
            cbar_label = f"{stat} {grid.value_col} [{grid.units}] (log10 color scale)"
        else:
            norm = None
            cbar_label = f"{stat} {grid.value_col} [{grid.units}]"

    mesh = ax.pcolormesh(
        grid.lon_edges, grid.lat_edges, np.ma.masked_invalid(data),
        shading="flat", cmap=cmap, norm=norm,
    )
    cbar = fig.colorbar(mesh, ax=ax, shrink=0.9)
    cbar.set_label(cbar_label, fontsize=9)

    ax.axvline(_REF_LON, color="white", lw=0.5, alpha=0.4)
    ax.axhline(_REF_LAT, color="white", lw=0.5, alpha=0.4)
    ax.set_xlim(grid.lon_edges[0], grid.lon_edges[-1])
    ax.set_ylim(grid.lat_edges[0], grid.lat_edges[-1])
    ax.set_xlabel("longitude [deg]  ([-180, 180) convention)")
    ax.set_ylabel("latitude [deg]")
    res = f"{grid.lat_step:g}deg x {grid.lon_step:g}deg"
    ax.set_title(title or f"{stat} {grid.value_col} ({res}) -- exploratory, one day", fontsize=10)

    if save_path:
        fig.savefig(save_path, dpi=120, bbox_inches="tight")
    return ax
