"""Monthly (multi-day) aggregation + coverage-aware grid tables (Checkpoint 4A).

Builds on the accepted CP2 loader (:mod:`saa.load_poes`) and CP3 grid utilities
(:mod:`saa.grid_flux`). Adds:

* :func:`load_range` — download/load every day in a date range, **tolerating missing days**
  (records them instead of failing the whole month; never fabricates data),
* :func:`build_grid_table` — a tidy long grid table (one row per populated cell) with mean / median /
  sample-count / positive-count / min / max per cell,
* :func:`add_coverage_mask` — a boolean coverage column from a minimum-sample threshold.

Scope reminder: exploratory *monthly proton-flux aggregation* and a *coverage-aware gridded product*
— a foundation for later threshold sensitivity analysis. `mep_omni_flux_p1` is a differential proton
flux (~25 MeV); it is **not** dose and **not** a health-risk quantity. No SAA boundary/center here.
"""
from __future__ import annotations

import urllib.error
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .load_poes import (
    _as_date, download_poes_file, open_poes_netcdf, extract_minimal_dataframe, DEFAULT_CHANNEL,
)
from .grid_flux import DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE

GRID_COLUMNS = [
    "lat_bin_center", "lon_bin_center", "mean_flux", "median_flux",
    "sample_count", "positive_sample_count", "min_flux", "max_flux",
]


@dataclass
class RangeLoad:
    """Result of :func:`load_range` — the concatenated frame plus provenance of loaded/missing days."""

    df: pd.DataFrame
    loaded_dates: list = field(default_factory=list)
    missing_dates: list = field(default_factory=list)
    paths: list = field(default_factory=list)

    @property
    def n_expected(self) -> int:
        return len(self.loaded_dates) + len(self.missing_dates)

    @property
    def n_loaded(self) -> int:
        return len(self.loaded_dates)

    @property
    def complete(self) -> bool:
        return len(self.missing_dates) == 0


def load_range(
    start,
    end,
    satellite: str = "noaa19",
    raw_dir: str = "data/raw",
    channel: str = DEFAULT_CHANNEL,
    on_error: str = "skip",
) -> RangeLoad:
    """Download + extract every day in ``[start, end]`` (inclusive), tolerating missing days.

    Each day is fetched with the CP2 loader (download only if missing). On a download/open error,
    the date is recorded in ``missing_dates`` and processing continues (``on_error="skip"``); pass
    ``on_error="raise"`` to fail hard. Returns a :class:`RangeLoad`. Nothing is fabricated.
    """
    dates = pd.date_range(_as_date(start), _as_date(end), freq="D")
    frames, loaded, missing, paths = [], [], [], []
    for d in dates:
        dd = d.date()
        try:
            p = download_poes_file(dd, satellite, output_dir=raw_dir)
            with open_poes_netcdf(p) as ds:
                frames.append(extract_minimal_dataframe(ds, p, satellite=satellite, channel=channel))
            loaded.append(dd)
            paths.append(p)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            if on_error == "raise":
                raise
            print(f"[load_range] WARNING: {dd} skipped ({type(exc).__name__}: {exc})")
            missing.append(dd)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return RangeLoad(df=df, loaded_dates=loaded, missing_dates=missing, paths=paths)


def build_grid_table(
    df: pd.DataFrame,
    value_col: str = DEFAULT_CHANNEL,
    lat_step: float = 5.0,
    lon_step: float = 5.0,
    lat_range: tuple[float, float] = DEFAULT_LAT_RANGE,
    lon_range: tuple[float, float] = DEFAULT_LON_RANGE,
    lat_col: str = "lat",
    lon_col: str = "lon180",
) -> pd.DataFrame:
    """Tidy long grid table: one row per **populated** cell with ``GRID_COLUMNS``.

    Empty cells are simply absent (``sample_count`` is always >= 1 in the returned table).
    """
    lat_min, lat_max = lat_range
    lon_min, lon_max = lon_range
    n_lat = int(round((lat_max - lat_min) / lat_step))
    n_lon = int(round((lon_max - lon_min) / lon_step))

    lat = df[lat_col].to_numpy(dtype="float64")
    lon = df[lon_col].to_numpy(dtype="float64")
    val = df[value_col].to_numpy(dtype="float64")

    li = np.floor((lat - lat_min) / lat_step).astype(int)
    lj = np.floor((lon - lon_min) / lon_step).astype(int)
    valid = (li >= 0) & (li < n_lat) & (lj >= 0) & (lj < n_lon) & np.isfinite(val)
    li, lj, val = li[valid], lj[valid], val[valid]

    if val.size == 0:
        return pd.DataFrame(columns=GRID_COLUMNS)

    d = pd.DataFrame({
        "lat_bin_center": lat_min + (li + 0.5) * lat_step,
        "lon_bin_center": lon_min + (lj + 0.5) * lon_step,
        "v": val,
    })
    grp = d.groupby(["lat_bin_center", "lon_bin_center"])["v"]
    table = grp.agg(
        mean_flux="mean", median_flux="median", sample_count="count",
        min_flux="min", max_flux="max",
    ).reset_index()
    pos = (
        d.assign(p=(d["v"] > 0))
        .groupby(["lat_bin_center", "lon_bin_center"])["p"].sum()
        .astype(int).rename("positive_sample_count").reset_index()
    )
    table = table.merge(pos, on=["lat_bin_center", "lon_bin_center"], how="left")
    table["positive_sample_count"] = table["positive_sample_count"].fillna(0).astype(int)
    table["sample_count"] = table["sample_count"].astype(int)
    return table[GRID_COLUMNS].sort_values(["lat_bin_center", "lon_bin_center"]).reset_index(drop=True)


def add_coverage_mask(table: pd.DataFrame, min_samples: int, col_name: str) -> pd.DataFrame:
    """Return a copy of ``table`` with a boolean coverage column ``col_name`` (sample_count >= min)."""
    out = table.copy()
    out[col_name] = out["sample_count"] >= int(min_samples)
    return out


def load_range_channels(
    start,
    end,
    satellite: str = "noaa19",
    raw_dir: str = "data/raw",
    channels=("mep_omni_flux_p1",),
    on_error: str = "skip",
) -> RangeLoad:
    """Multi-channel variant of :func:`load_range` — extracts several channels per file in one pass.

    Reuses already-downloaded daily files (downloads only if missing); tolerates missing days.
    """
    from .load_poes import extract_channels_dataframe

    dates = pd.date_range(_as_date(start), _as_date(end), freq="D")
    frames, loaded, missing, paths = [], [], [], []
    for d in dates:
        dd = d.date()
        try:
            p = download_poes_file(dd, satellite, output_dir=raw_dir)
            with open_poes_netcdf(p) as ds:
                frames.append(extract_channels_dataframe(ds, p, satellite=satellite, channels=channels))
            loaded.append(dd)
            paths.append(p)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            if on_error == "raise":
                raise
            print(f"[load_range_channels] WARNING: {dd} skipped ({type(exc).__name__}: {exc})")
            missing.append(dd)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return RangeLoad(df=df, loaded_dates=loaded, missing_dates=missing, paths=paths)
