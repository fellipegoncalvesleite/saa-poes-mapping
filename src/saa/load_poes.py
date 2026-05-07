"""Minimal, reproducible loader for NOAA/NCEI POES/MetOp SEM-2 **L1b processed** NetCDF files.

Checkpoint-2 deliverable. It builds the official NCEI URL for one daily file, downloads it
(only if missing), opens it with xarray, and extracts a tidy one-day :class:`pandas.DataFrame`
suitable for South-Atlantic-Anomaly mapping.

Official archive (verified in Checkpoint 1)::

    https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00/
        <YYYY>/<satellite>/poes_<token>_<YYYYMMDD>_proc.nc

Real-file facts confirmed by inspecting ``poes_n19_20240101_proc.nc`` (2026-06-07), which drive
the design choices below:

* **No shared record dimension.** Every variable is a 1-D array of length N *along its own
  dimension* (e.g. ``lat`` has dims ``('lat',)``). The variables are positionally aligned by
  record index. We therefore read each variable's ``.values`` and build the DataFrame by hand;
  ``xarray.Dataset.to_dataframe()`` must **not** be used (it would attempt an N-dimensional
  cartesian product).
* **time** is ``uint64`` = *milliseconds since 1970-01-01 UTC* (the CF ``units`` attribute is
  non-standard; the truth is in ``long_name``). We decode it ourselves with
  ``pd.to_datetime(values, unit="ms", utc=True)``.
* **lon** uses the ``[0, 360)`` East convention; ``lat`` in degrees; ``alt`` in km.
* **mep_omni_flux_p1** is the MEPED omnidirectional proton **differential flux at ~25 MeV**,
  units ``#/cm2-s-str-MeV`` -- i.e. a *flux*, not counts and not an integral channel. p2/p3 are
  the ~50/100 MeV channels.
* **mep_IFC_on** (in-flight-calibration flag) holds values ``{-1, 0}`` in this file; ``long_name``
  says ``0=off / 1=on``, so ``-1`` is a fill/no-data marker. We carry the raw flag through
  unchanged; downstream analysis should drop records where it equals ``1``.

This module fabricates nothing: every value comes from the official file.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import urllib.request
from datetime import date as _date, datetime

import numpy as np
import pandas as pd
import xarray as xr

NCEI_L1B_BASE = (
    "https://www.ncei.noaa.gov/data/poes-metop-space-environment-monitor/access/l1b/v01r00"
)

#: satellite name -> short token used inside the NCEI filenames (``poes_<token>_<date>_proc.nc``)
SAT_FILE_TOKEN: dict[str, str] = {
    "noaa15": "n15", "noaa16": "n16", "noaa17": "n17", "noaa18": "n18", "noaa19": "n19",
    "metop01": "m01", "metop02": "m02", "metop03": "m03",
}
_TOKEN_TO_SAT = {tok: name for name, tok in SAT_FILE_TOKEN.items()}

DEFAULT_CHANNEL = "mep_omni_flux_p1"

#: nominal description + units for the omni proton channels (read authoritatively from the file
#: at runtime; this table is just convenient documentation).
CHANNEL_INFO: dict[str, tuple[str, str]] = {
    "mep_omni_flux_p1": ("MEPED omni proton differential flux @ ~25 MeV", "#/cm2-s-str-MeV"),
    "mep_omni_flux_p2": ("MEPED omni proton differential flux @ ~50 MeV", "#/cm2-s-str-MeV"),
    "mep_omni_flux_p3": ("MEPED omni proton differential flux @ ~100 MeV", "#/cm2-s-str-MeV"),
}

# Columns that always come straight from a same-named NetCDF variable.
_DIRECT_COLUMNS = ("lat", "lon", "alt")
# Quality/calibration flags carried through (not applied) when present.
_FLAG_COLUMNS = ("mep_IFC_on", "mep_omni_flux_flag_fit")


def _as_date(d) -> _date:
    """Accept a ``datetime.date``/``datetime`` or an ISO ``'YYYY-MM-DD'`` string."""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, _date):
        return d
    return datetime.strptime(str(d), "%Y-%m-%d").date()


def satellite_from_filename(filename: str) -> str | None:
    """Return the satellite name ('noaa19', ...) parsed from a ``poes_<token>_...`` filename."""
    parts = os.path.basename(filename).split("_")
    if len(parts) >= 2 and parts[1] in _TOKEN_TO_SAT:
        return _TOKEN_TO_SAT[parts[1]]
    return None


def build_poes_l1b_url(date, satellite: str = "noaa19") -> str:
    """Build the official NCEI L1b processed-NetCDF URL for one day / satellite.

    >>> build_poes_l1b_url("2024-01-01", "noaa19")  # doctest: +ELLIPSIS
    '.../access/l1b/v01r00/2024/noaa19/poes_n19_20240101_proc.nc'
    """
    d = _as_date(date)
    sat = satellite.lower()
    if sat not in SAT_FILE_TOKEN:
        raise ValueError(f"unknown satellite {satellite!r}; known: {sorted(SAT_FILE_TOKEN)}")
    fname = f"poes_{SAT_FILE_TOKEN[sat]}_{d:%Y%m%d}_proc.nc"
    return f"{NCEI_L1B_BASE}/{d:%Y}/{sat}/{fname}"


def download_poes_file(
    date, satellite: str = "noaa19", output_dir: str = "data/raw", overwrite: bool = False,
    timeout: float = 120.0,
) -> str:
    """Download one daily L1b file from NCEI into ``output_dir``; skip if already present.

    Returns the local path. Downloads via a ``.part`` temp file then atomically renames, so an
    interrupted download never looks like a complete one. ``timeout`` (seconds) bounds the socket so a
    stalled NCEI connection raises instead of hanging forever (``urlretrieve`` has no timeout).
    """
    url = build_poes_l1b_url(date, satellite)
    os.makedirs(output_dir, exist_ok=True)
    dest = os.path.join(output_dir, os.path.basename(url))
    if os.path.exists(dest) and not overwrite:
        return dest
    tmp = dest + ".part"
    with urllib.request.urlopen(url, timeout=timeout) as resp, open(tmp, "wb") as fh:
        shutil.copyfileobj(resp, fh)
    os.replace(tmp, dest)
    return dest


def open_poes_netcdf(path: str) -> xr.Dataset:
    """Open a POES L1b NetCDF file.

    ``decode_times=False`` because the ``time`` variable's CF ``units`` is non-standard (we decode
    epoch-milliseconds ourselves in :func:`extract_minimal_dataframe`). ``mask_and_scale=True``
    applies any ``_FillValue``/scale attributes so genuinely-missing values become ``NaN``.
    """
    return xr.open_dataset(path, engine="netcdf4", decode_times=False, mask_and_scale=True)


def describe_dataset(ds: xr.Dataset, n_preview: int = 12) -> dict:
    """Return a small, printable summary of an open POES dataset (dims, var count, key attrs)."""
    variables = list(ds.variables)
    n_records = int(ds.sizes[variables[0]]) if variables else 0
    key_vars = ["time", "lat", "lon", "alt", "satID", DEFAULT_CHANNEL,
                "mep_omni_flux_flag_fit", "mep_IFC_on"]
    key_attrs = {}
    for v in key_vars:
        if v in ds.variables:
            a = ds[v].attrs
            key_attrs[v] = {
                "dtype": str(ds[v].dtype),
                "units": a.get("units", "-"),
                "long_name": a.get("long_name", "-"),
            }
    return {
        "n_records": n_records,
        "n_variables": len(variables),
        "variables_preview": variables[:n_preview],
        "key_var_attrs": key_attrs,
        "global_title": ds.attrs.get("title", "-"),
        "time_coverage_resolution": ds.attrs.get("time_coverage_resolution", "-"),
        "geospatial_lon_units": ds.attrs.get("geospatial_lon_units", "-"),
    }


def _col(ds: xr.Dataset, name: str) -> np.ndarray:
    return np.asarray(ds[name].values).ravel()


def extract_minimal_dataframe(
    dataset: xr.Dataset,
    source_file: str,
    satellite: str | None = None,
    channel: str = DEFAULT_CHANNEL,
) -> pd.DataFrame:
    """Extract the tidy minimal table for SAA mapping from an open POES dataset.

    Columns: ``time, lat, lon, alt, satellite, source_file, <channel>`` plus, when present, the
    quality flags ``mep_IFC_on`` and ``mep_omni_flux_flag_fit`` (carried through unchanged).

    Parameters
    ----------
    dataset : open :class:`xarray.Dataset` from :func:`open_poes_netcdf`.
    source_file : path of the NetCDF file (its basename is stored in ``source_file`` and used to
        infer the satellite if ``satellite`` is not given).
    satellite : optional override for the ``satellite`` label; if ``None`` it is parsed from
        ``source_file`` (falling back to ``"unknown"``).
    channel : proton channel variable name to extract (default ``mep_omni_flux_p1``).
    """
    ds = dataset
    required = ["time", "lat", "lon", channel]
    missing = [v for v in required if v not in ds.variables]
    if missing:
        raise KeyError(f"required variables missing from {os.path.basename(source_file)}: {missing}")

    sat_label = satellite or satellite_from_filename(source_file) or "unknown"

    time_ms = _col(ds, "time").astype("uint64")
    time = pd.to_datetime(time_ms, unit="ms", utc=True)
    n = len(time)

    data: dict[str, np.ndarray] = {"time": time}
    for col in _DIRECT_COLUMNS:
        data[col] = _col(ds, col).astype("float64") if col in ds.variables else np.full(n, np.nan)
    data["satellite"] = np.repeat(sat_label, n)
    data["source_file"] = np.repeat(os.path.basename(source_file), n)
    data[channel] = _col(ds, channel).astype("float64")
    for flag in _FLAG_COLUMNS:
        if flag in ds.variables:
            data[flag] = _col(ds, flag).astype("int16")

    lengths = {k: len(v) for k, v in data.items()}
    if len(set(lengths.values())) != 1:
        raise ValueError(f"variable length mismatch (file not record-aligned): {lengths}")

    df = pd.DataFrame(data)
    ordered = ["time", "lat", "lon", "alt", "satellite", "source_file", channel]
    ordered += [f for f in _FLAG_COLUMNS if f in df.columns]
    return df[ordered]


def load_minimal_day(
    date,
    satellite: str = "noaa19",
    raw_dir: str = "data/raw",
    channel: str = DEFAULT_CHANNEL,
) -> tuple[pd.DataFrame, str]:
    """Convenience: download (if needed) -> open -> extract. Returns ``(dataframe, netcdf_path)``."""
    path = download_poes_file(date, satellite, output_dir=raw_dir)
    with open_poes_netcdf(path) as ds:
        df = extract_minimal_dataframe(ds, path, satellite=satellite, channel=channel)
    return df, path


def file_sha256(path: str, chunk: int = 1 << 20) -> str:
    """Streaming SHA-256 of a file (for provenance)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load_date_range(
    start,
    end,
    satellite: str = "noaa19",
    raw_dir: str = "data/raw",
    channel: str = DEFAULT_CHANNEL,
) -> tuple[pd.DataFrame, list[str]]:
    """Download + extract every day in ``[start, end]`` (inclusive) and concatenate.

    Minimal multi-day helper (Checkpoint 3 preview / Checkpoint 4 building block). Returns
    ``(dataframe, paths)``. Each day is a separate ~5 MB official file; nothing is fabricated.
    """
    dates = pd.date_range(_as_date(start), _as_date(end), freq="D")
    frames, paths = [], []
    for d in dates:
        path = download_poes_file(d.date(), satellite, output_dir=raw_dir)
        with open_poes_netcdf(path) as ds:
            frames.append(extract_minimal_dataframe(ds, path, satellite=satellite, channel=channel))
        paths.append(path)
    return pd.concat(frames, ignore_index=True), paths


def extract_channels_dataframe(
    dataset: xr.Dataset,
    source_file: str,
    satellite: str | None = None,
    channels=(DEFAULT_CHANNEL,),
) -> pd.DataFrame:
    """Like :func:`extract_minimal_dataframe` but extracts several channel columns at once.

    Columns: ``time, lat, lon, alt, satellite, source_file, <each channel>`` + the quality flags
    (`mep_IFC_on`, `mep_omni_flux_flag_fit`) when present. All channels are positionally aligned.
    """
    ds = dataset
    chans = list(channels)
    missing = [v for v in (["time", "lat", "lon"] + chans) if v not in ds.variables]
    if missing:
        raise KeyError(f"missing variables in {os.path.basename(source_file)}: {missing}")

    sat_label = satellite or satellite_from_filename(source_file) or "unknown"
    time = pd.to_datetime(_col(ds, "time").astype("uint64"), unit="ms", utc=True)
    n = len(time)

    data: dict[str, np.ndarray] = {"time": time}
    for col in _DIRECT_COLUMNS:
        data[col] = _col(ds, col).astype("float64") if col in ds.variables else np.full(n, np.nan)
    data["satellite"] = np.repeat(sat_label, n)
    data["source_file"] = np.repeat(os.path.basename(source_file), n)
    for c in chans:
        data[c] = _col(ds, c).astype("float64")
    for flag in _FLAG_COLUMNS:
        if flag in ds.variables:
            data[flag] = _col(ds, flag).astype("int16")

    if len({len(v) for v in data.values()}) != 1:
        raise ValueError("variable length mismatch (file not record-aligned)")

    df = pd.DataFrame(data)
    ordered = ["time", "lat", "lon", "alt", "satellite", "source_file"] + chans
    ordered += [f for f in _FLAG_COLUMNS if f in df.columns]
    return df[ordered]


def channel_metadata(dataset: xr.Dataset, channels) -> dict:
    """Return ``{channel: {long_name, units, dtype}}`` straight from the NetCDF attributes."""
    out = {}
    for c in channels:
        if c in dataset.variables:
            a = dataset[c].attrs
            out[c] = {"long_name": a.get("long_name", "-"), "units": a.get("units", "-"),
                      "dtype": str(dataset[c].dtype)}
        else:
            out[c] = {"long_name": "MISSING", "units": "-", "dtype": "-"}
    return out
