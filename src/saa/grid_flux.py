"""Grid / region utilities for exploratory SAA proton-flux mapping (Checkpoint 3).

Pure numpy/pandas. Takes the tidy one-day table produced by :mod:`saa.load_poes` and:

* converts longitude from ``[0, 360)`` to ``[-180, 180)``,
* filters a geographic region (default: South America / South Atlantic sector),
* applies the conservative in-flight-calibration filter (drop ``mep_IFC_on == 1`` only),
* bins ``mep_omni_flux_p1`` onto a regular lat/lon grid and computes mean / median / sample-count
  per cell,
* ranks the top grid cells.

**Scientific scope:** this is exploratory pipeline validation. ``mep_omni_flux_p1`` is a *differential
proton flux* (~25 MeV, ``#/cm2-s-str-MeV``); it is **not** a dose and not a health-risk quantity.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Default region: includes South America and the South Atlantic.
DEFAULT_LAT_RANGE: tuple[float, float] = (-70.0, 20.0)
DEFAULT_LON_RANGE: tuple[float, float] = (-100.0, 20.0)
DEFAULT_CHANNEL = "mep_omni_flux_p1"
CHANNEL_UNITS = "#/cm2-s-str-MeV"


def to_180(lon):
    """Convert longitude from ``[0, 360)`` to ``[-180, 180)``. Works on scalars / arrays / Series."""
    return ((np.asarray(lon, dtype="float64") + 180.0) % 360.0) - 180.0


def add_lon180(df: pd.DataFrame, lon_col: str = "lon", out_col: str = "lon180") -> pd.DataFrame:
    """Return a copy of ``df`` with a ``[-180, 180)`` longitude column added."""
    out = df.copy()
    out[out_col] = to_180(out[lon_col].to_numpy())
    return out


def filter_region(
    df: pd.DataFrame,
    lat_range: tuple[float, float] = DEFAULT_LAT_RANGE,
    lon_range: tuple[float, float] = DEFAULT_LON_RANGE,
    lat_col: str = "lat",
    lon_col: str = "lon180",
) -> pd.DataFrame:
    """Keep rows whose (lat, lon) fall inside the inclusive bounding box."""
    lat_min, lat_max = lat_range
    lon_min, lon_max = lon_range
    m = (
        df[lat_col].between(lat_min, lat_max)
        & df[lon_col].between(lon_min, lon_max)
    )
    return df.loc[m].copy()


def filter_ifc(df: pd.DataFrame, ifc_col: str = "mep_IFC_on") -> pd.DataFrame:
    """Drop rows where the in-flight-calibration flag is on (``== 1``).

    ``-1`` (undocumented; treated as fill / not-interpreted) and ``0`` (off) are **kept**.
    """
    if ifc_col not in df.columns:
        return df.copy()
    return df.loc[df[ifc_col] != 1].copy()


def prepare_region(
    df: pd.DataFrame,
    lat_range: tuple[float, float] = DEFAULT_LAT_RANGE,
    lon_range: tuple[float, float] = DEFAULT_LON_RANGE,
    lon_col: str = "lon",
    ifc_col: str = "mep_IFC_on",
) -> tuple[pd.DataFrame, dict]:
    """Full prep: add ``lon180`` -> region filter -> IFC filter.

    Returns ``(region_df, counts)`` where ``counts`` records each step's row count for reporting.
    """
    counts: dict[str, int] = {"n_total": int(len(df))}
    d = add_lon180(df, lon_col=lon_col)
    d_geo = filter_region(d, lat_range, lon_range)
    counts["n_after_geo"] = int(len(d_geo))
    if ifc_col in d_geo.columns:
        counts["n_ifc_on_dropped"] = int((d_geo[ifc_col] == 1).sum())
        counts["n_ifc_minus1"] = int((d_geo[ifc_col] == -1).sum())
    else:
        counts["n_ifc_on_dropped"] = 0
        counts["n_ifc_minus1"] = 0
    d_final = filter_ifc(d_geo, ifc_col=ifc_col)
    counts["n_after_ifc"] = int(len(d_final))
    return d_final, counts


@dataclass
class GridResult:
    """A binned lat/lon grid of a flux statistic plus the per-cell sample count."""

    value_col: str
    units: str
    lat_step: float
    lon_step: float
    lat_range: tuple[float, float]
    lon_range: tuple[float, float]
    lat_edges: np.ndarray
    lon_edges: np.ndarray
    lat_centers: np.ndarray
    lon_centers: np.ndarray
    mean: np.ndarray
    median: np.ndarray
    count: np.ndarray

    @property
    def n_nonempty(self) -> int:
        return int((self.count > 0).sum())

    @property
    def n_cells(self) -> int:
        return int(self.count.size)


def grid_statistics(
    df: pd.DataFrame,
    value_col: str = DEFAULT_CHANNEL,
    lat_step: float = 5.0,
    lon_step: float = 5.0,
    lat_range: tuple[float, float] = DEFAULT_LAT_RANGE,
    lon_range: tuple[float, float] = DEFAULT_LON_RANGE,
    lat_col: str = "lat",
    lon_col: str = "lon180",
    units: str = CHANNEL_UNITS,
) -> GridResult:
    """Bin ``value_col`` onto a regular lat/lon grid; return mean, median and count per cell.

    Empty cells are ``NaN`` in ``mean``/``median`` and ``0`` in ``count``.
    """
    lat_min, lat_max = lat_range
    lon_min, lon_max = lon_range
    lat_edges = np.arange(lat_min, lat_max + lat_step * 0.5, lat_step)
    lon_edges = np.arange(lon_min, lon_max + lon_step * 0.5, lon_step)
    n_lat = len(lat_edges) - 1
    n_lon = len(lon_edges) - 1

    lat = df[lat_col].to_numpy(dtype="float64")
    lon = df[lon_col].to_numpy(dtype="float64")
    val = df[value_col].to_numpy(dtype="float64")

    li = np.floor((lat - lat_min) / lat_step).astype(int)
    lj = np.floor((lon - lon_min) / lon_step).astype(int)
    valid = (li >= 0) & (li < n_lat) & (lj >= 0) & (lj < n_lon) & np.isfinite(val)
    li, lj, val = li[valid], lj[valid], val[valid]

    mean = np.full((n_lat, n_lon), np.nan)
    median = np.full((n_lat, n_lon), np.nan)
    count = np.zeros((n_lat, n_lon), dtype=int)

    if len(val):
        agg = (
            pd.DataFrame({"li": li, "lj": lj, "v": val})
            .groupby(["li", "lj"])["v"]
            .agg(["mean", "median", "count"])
        )
        for (i, j), row in agg.iterrows():
            mean[i, j] = row["mean"]
            median[i, j] = row["median"]
            count[i, j] = int(row["count"])

    return GridResult(
        value_col=value_col,
        units=units,
        lat_step=lat_step,
        lon_step=lon_step,
        lat_range=lat_range,
        lon_range=lon_range,
        lat_edges=lat_edges,
        lon_edges=lon_edges,
        lat_centers=(lat_edges[:-1] + lat_edges[1:]) / 2.0,
        lon_centers=(lon_edges[:-1] + lon_edges[1:]) / 2.0,
        mean=mean,
        median=median,
        count=count,
    )


def top_cells(grid: GridResult, stat: str = "mean", n: int = 10) -> pd.DataFrame:
    """Return the top ``n`` populated grid cells ranked by ``stat`` ('mean' or 'median')."""
    arr = getattr(grid, stat)
    mask = np.isfinite(arr) & (grid.count > 0)
    rows = []
    for i, j in np.argwhere(mask):
        rows.append(
            {
                "lat_center": float(grid.lat_centers[i]),
                "lon_center": float(grid.lon_centers[j]),
                stat: float(arr[i, j]),
                "n_samples": int(grid.count[i, j]),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["lat_center", "lon_center", stat, "n_samples"])
    return (
        pd.DataFrame(rows)
        .sort_values(stat, ascending=False)
        .head(n)
        .reset_index(drop=True)
    )
