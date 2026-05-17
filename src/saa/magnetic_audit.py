"""IGRF / magnetic-coordinate audit + cautious pilot framing (Checkpoint 5A).

The NOAA/NCEI POES/MetOp L1b files already carry IGRF-derived magnetic variables (verified by
inspecting `poes_n19_20240101_proc.nc`): ``L_IGRF``, ``MLT``, ``Btot_sat`` and the B-field components,
satellite magnetic lat/lon (``mag_lat_sat``/``mag_lon_sat``) and field-line foot-point coordinates
(``mag_lat_foot``, ``aacgm_lat_foot``, ``geod_lat_foot`` …). So CP5A uses the **NOAA-provided**
variables — no external IGRF computation is added.

Scope: this is an **audit + descriptive pilot framing** step. The *particle-defined footprint* (where
measured proton flux is high) and *magnetic-coordinate / field variables* (from a geomagnetic model)
are **related but not identical** and are kept conceptually separate. Everything here is descriptive —
no causality, no "the SAA is exactly the field minimum", no final SAA boundary, no dose/health/danger/
discovery claims. ``mep_IFC_on == -1`` retained, uninterpreted.
"""
from __future__ import annotations

import re
import urllib.error

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from .load_poes import (
    _as_date, download_poes_file, open_poes_netcdf, _col, satellite_from_filename,
    DEFAULT_CHANNEL, _DIRECT_COLUMNS, _FLAG_COLUMNS,
)
from .grid_flux import (
    DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE, add_lon180, prepare_region,
)
from .threshold_analysis import coverage_passed, percentile_threshold, select_high_flux, PERCENTILES

#: regex of name fragments that flag a variable as magnetic / IGRF / coordinate / field-geometry.
_MAG_PATTERN = re.compile(
    r"(^l_igrf$|mlt|mag_lat|mag_lon|aacgm|geod_.*_foot|_foot$|btot|^b[rtpxyz]_|alpha_.*(sat|foot)|igrf)",
    re.I,
)

AUDIT_COLUMNS = [
    "variable_name", "dtype", "shape_or_dimension", "units", "long_name",
    "valid_min", "valid_max", "missing_value_or_fill",
    "example_min", "example_max", "missing_percent", "interpretation_note", "recommended_use",
]

SELECTION_COLUMNS = ["variable_name", "use_in_cp5a", "use_type", "reason", "caveat"]

DISTRIBUTION_COLUMNS = [
    "comparison_case", "grid_deg", "statistic_used", "threshold_label", "magnetic_variable",
    "count_inside", "count_outside", "median_inside", "median_outside",
    "iqr_inside", "iqr_outside", "min_inside", "max_inside", "min_outside", "max_outside",
]


# ---------------------------------------------------------------- audit
def _attr(ds, v, *names):
    for n in names:
        if n in ds[v].attrs:
            return ds[v].attrs[n]
    return "-"


def audit_magnetic_variables(ds, sample_cap: int = 200_000) -> pd.DataFrame:
    """Audit every magnetic/IGRF/coordinate-related variable in an open dataset (real metadata+values).

    ``example_min/max`` and ``missing_percent`` are computed from the file's actual values (capped for
    speed). Returns a tidy :data:`AUDIT_COLUMNS` frame; ``interpretation_note``/``recommended_use`` are
    left blank here and filled by the curated :func:`default_interpretation`.
    """
    rows = []
    for v in ds.variables:
        if not _MAG_PATTERN.search(v):
            continue
        vals = np.asarray(ds[v].values).ravel().astype("float64")
        n = vals.size
        if n > sample_cap:
            vals = vals[:: max(1, n // sample_cap)]
        finite = vals[np.isfinite(vals)]
        miss = 100.0 * (1.0 - finite.size / vals.size) if vals.size else 100.0
        note, use = default_interpretation(v)
        rows.append({
            "variable_name": v, "dtype": str(ds[v].dtype),
            "shape_or_dimension": str(tuple(ds[v].dims)),
            "units": _attr(ds, v, "units"), "long_name": _attr(ds, v, "long_name"),
            "valid_min": _attr(ds, v, "valid_min"), "valid_max": _attr(ds, v, "valid_max"),
            "missing_value_or_fill": _attr(ds, v, "_FillValue", "missing_value"),
            "example_min": float(finite.min()) if finite.size else float("nan"),
            "example_max": float(finite.max()) if finite.size else float("nan"),
            "missing_percent": round(float(miss), 4),
            "interpretation_note": note, "recommended_use": use,
        })
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS).sort_values("variable_name").reset_index(drop=True)


def default_interpretation(v: str) -> tuple[str, str]:
    """Curated (note, recommended_use) for a magnetic variable name — conservative, not over-claiming."""
    table = {
        "L_IGRF": ("McIlwain L-shell from IGRF field; dimensionless", "grouping/descriptive"),
        "MLT": ("magnetic local time (hours); orbit/local-time sampling dependent", "caution/descriptive"),
        "Btot_sat": ("total IGRF field strength at the satellite (nT); SAA ~ field minimum", "descriptive"),
        "mag_lat_sat": ("magnetic latitude at the satellite (deg)", "descriptive"),
        "mag_lon_sat": ("magnetic longitude at the satellite (deg)", "descriptive"),
        "Btot_foot": ("total IGRF field at field-line foot (nT)", "caution/descriptive"),
        "mag_lat_foot": ("magnetic latitude at field-line foot (deg)", "caution/descriptive"),
        "mag_lon_foot": ("magnetic longitude at field-line foot (deg)", "caution/descriptive"),
        "aacgm_lat_foot": ("AACGM latitude at foot (deg)", "caution/descriptive"),
        "aacgm_lon_foot": ("AACGM longitude at foot (deg)", "caution/descriptive"),
        "geod_lat_foot": ("geodetic latitude at foot (deg)", "excluded/redundant-with-geographic"),
        "geod_lon_foot": ("geodetic longitude at foot (deg)", "excluded/redundant-with-geographic"),
    }
    if v in table:
        return table[v]
    if v.startswith(("Br_", "Bt_", "Bp_", "Bx_", "By_", "Bz_")):
        return ("IGRF field component (nT)", "caution/component-not-core")
    if v.startswith(("meped_alpha", "ted_alpha")):
        return ("telescope pitch angle (deg); detector-geometry, not a coordinate", "excluded/geometry")
    return ("magnetic/coordinate-related; review before use", "caution/descriptive")


#: pilot selection — small, well-documented, populated set (justified in the selection table).
PILOT_MAGNETIC_VARS = ["L_IGRF", "Btot_sat", "mag_lat_sat", "mag_lon_sat", "MLT"]

#: documented invalid/sentinel values to exclude *in analysis* (raw parquet keeps the values faithful).
INVALID_SENTINELS = {"L_IGRF": -1.0}


def _drop_sentinel(values: np.ndarray, var: str) -> np.ndarray:
    """Return finite values with any documented invalid sentinel for ``var`` removed."""
    v = values[np.isfinite(values)]
    s = INVALID_SENTINELS.get(var)
    return v[v != s] if s is not None else v


def build_selection_table(audit: pd.DataFrame, selected=PILOT_MAGNETIC_VARS) -> pd.DataFrame:
    """Decision table over audited variables (which to use in CP5A and how)."""
    reasons = {
        "L_IGRF": ("descriptive", "well-documented IGRF L-shell, 0% missing; natural magnetic grouping",
                   "L alone does not define the SAA boundary"),
        "Btot_sat": ("descriptive", "IGRF total field at satellite; physically the SAA is the field-strength minimum",
                     "model field, not a measurement; do not equate low B with the particle footprint"),
        "mag_lat_sat": ("descriptive", "magnetic latitude at satellite; documented, populated",
                        "satellite-altitude coordinate, not the foot of the field line"),
        "mag_lon_sat": ("descriptive", "magnetic longitude at satellite; documented, populated",
                        "satellite-altitude coordinate"),
        "MLT": ("caution_only", "documented magnetic local time; useful context",
                "depends on local-time / orbital sampling; not a spatial SAA coordinate"),
    }
    rows = []
    for v in audit["variable_name"]:
        use = v in selected
        ut, reason, caveat = reasons.get(v, ("excluded", "not needed for the cautious CP5A pilot", "-"))
        if not use and v not in reasons:
            # excluded by default
            note = audit.loc[audit.variable_name == v, "recommended_use"].iloc[0]
            ut = "excluded" if "exclud" in note else "caution_only"
        rows.append({"variable_name": v, "use_in_cp5a": use, "use_type": ut if use else "excluded",
                     "reason": reason if use else "not selected for the small pilot set",
                     "caveat": caveat if use else "-"})
    return pd.DataFrame(rows, columns=SELECTION_COLUMNS)


# ---------------------------------------------------------------- flux + magnetic extraction
def extract_flux_plus_magnetic(ds, source_file, satellite=None, channel=DEFAULT_CHANNEL,
                               magnetic_vars=PILOT_MAGNETIC_VARS) -> pd.DataFrame:
    """Tidy table: time/lat/lon/alt/satellite/source_file/<channel>/flags + selected magnetic vars.

    All variables are 1-D, positionally aligned (same record structure as the CP2 loader).
    """
    import os
    required = ["time", "lat", "lon", channel] + list(magnetic_vars)
    missing = [v for v in required if v not in ds.variables]
    if missing:
        raise KeyError(f"missing variables in {os.path.basename(source_file)}: {missing}")
    sat_label = satellite or satellite_from_filename(source_file) or "unknown"
    time = pd.to_datetime(_col(ds, "time").astype("uint64"), unit="ms", utc=True)
    n = len(time)
    data = {"time": time}
    for col in _DIRECT_COLUMNS:
        data[col] = _col(ds, col).astype("float64") if col in ds.variables else np.full(n, np.nan)
    data["satellite"] = np.repeat(sat_label, n)
    data["source_file"] = np.repeat(os.path.basename(source_file), n)
    data[channel] = _col(ds, channel).astype("float64")
    for flag in _FLAG_COLUMNS:
        if flag in ds.variables:
            data[flag] = _col(ds, flag).astype("int16")
    for mv in magnetic_vars:
        data[mv] = _col(ds, mv).astype("float64")
    if len({len(x) for x in data.values()}) != 1:
        raise ValueError("variable length mismatch (file not record-aligned)")
    return pd.DataFrame(data)


def load_region_with_magnetic(start, end, satellite="noaa19", raw_dir="data/raw",
                              channel=DEFAULT_CHANNEL, magnetic_vars=PILOT_MAGNETIC_VARS):
    """Load a date range extracting flux + magnetic vars, then region + IFC filter (CP4A rules).

    Returns ``(region_df, counts, paths)``.  Reuses cached daily files (downloads only if missing).
    """
    dates = pd.date_range(_as_date(start), _as_date(end), freq="D")
    frames, paths = [], []
    for d in dates:
        for attempt in range(4):
            try:
                p = download_poes_file(d.date(), satellite, output_dir=raw_dir)
                break
            except (urllib.error.URLError, urllib.error.HTTPError, OSError):
                if attempt == 3:
                    raise
        with open_poes_netcdf(p) as ds:
            frames.append(extract_flux_plus_magnetic(ds, p, satellite=satellite, channel=channel,
                                                     magnetic_vars=magnetic_vars))
        paths.append(p)
    df = pd.concat(frames, ignore_index=True)
    region, counts = prepare_region(df)
    return region, counts, paths


# ---------------------------------------------------------------- inside/outside footprint
def assign_cells(region_df, step, lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Add ``cell_lat``/``cell_lon`` (bin centers) to a region frame, matching build_grid_table binning."""
    lat_min, lat_max = lat_range
    lon_min, lon_max = lon_range
    out = region_df.copy()
    lat = out["lat"].to_numpy("float64")
    lon = out["lon180"].to_numpy("float64")
    li = np.floor((lat - lat_min) / step)
    lj = np.floor((lon - lon_min) / step)
    out["cell_lat"] = lat_min + (li + 0.5) * step
    out["cell_lon"] = lon_min + (lj + 0.5) * step
    return out


def selected_cells_from_grid(grid_table, stat_col, mask_col, percentile):
    """Recompute the top-(100-percentile)% coverage-passed cells from a CP4A grid table.

    Returns a set of ``(cell_lat, cell_lon)`` tuples (rounded) for the selected high-flux cells.
    """
    covered = coverage_passed(grid_table, mask_col)
    cutoff = percentile_threshold(covered[stat_col], percentile)
    sel = select_high_flux(covered, stat_col, cutoff)
    return {(round(float(r.lat_bin_center), 3), round(float(r.lon_bin_center), 3))
            for r in sel.itertuples()}, cutoff


def footprint_magnetic_distributions(region_df, grid_table, step, stat_col, mask_col, percentile,
                                     threshold_label, magnetic_vars=PILOT_MAGNETIC_VARS,
                                     grid_deg=None) -> pd.DataFrame:
    """Inside-vs-outside footprint distribution stats for each magnetic variable (descriptive).

    Samples are assigned to grid cells; "inside" = sample's cell is among the selected high-flux cells.
    Returns rows with :data:`DISTRIBUTION_COLUMNS`.
    """
    grid_deg = grid_deg if grid_deg is not None else int(step)
    sel_cells, _ = selected_cells_from_grid(grid_table, stat_col, mask_col, percentile)
    df = assign_cells(region_df, step)
    keys = list(zip(df["cell_lat"].round(3), df["cell_lon"].round(3)))
    inside_mask = np.array([k in sel_cells for k in keys])
    case = f"{threshold_label}_{grid_deg}deg_{stat_col.replace('_flux','')}"
    rows = []
    for mv in magnetic_vars:
        vin = _drop_sentinel(df.loc[inside_mask, mv].to_numpy("float64"), mv)
        vout = _drop_sentinel(df.loc[~inside_mask, mv].to_numpy("float64"), mv)
        def iqr(a):
            return float(np.percentile(a, 75) - np.percentile(a, 25)) if a.size else float("nan")
        rows.append({
            "comparison_case": case, "grid_deg": grid_deg, "statistic_used": stat_col,
            "threshold_label": threshold_label, "magnetic_variable": mv,
            "count_inside": int(vin.size), "count_outside": int(vout.size),
            "median_inside": float(np.median(vin)) if vin.size else float("nan"),
            "median_outside": float(np.median(vout)) if vout.size else float("nan"),
            "iqr_inside": iqr(vin), "iqr_outside": iqr(vout),
            "min_inside": float(vin.min()) if vin.size else float("nan"),
            "max_inside": float(vin.max()) if vin.size else float("nan"),
            "min_outside": float(vout.min()) if vout.size else float("nan"),
            "max_outside": float(vout.max()) if vout.size else float("nan"),
        })
    return pd.DataFrame(rows, columns=DISTRIBUTION_COLUMNS), inside_mask, df


def save_table(df, csv_path, parquet_path):
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)


# ---------------------------------------------------------------- plots
def plot_flux_vs_variable(df, xvar, save_path, flux_col=DEFAULT_CHANNEL, logy=True, xlabel=None,
                          sample=60000):
    """Descriptive scatter of proton flux vs a magnetic variable (sub-sampled for legibility)."""
    d = df[[xvar, flux_col]].dropna()
    s = INVALID_SENTINELS.get(xvar)
    if s is not None:
        d = d[d[xvar] != s]
    d = d[d[flux_col] > 0] if logy else d
    if len(d) > sample:
        d = d.sample(sample, random_state=0)
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    ax.scatter(d[xvar], d[flux_col], s=3, alpha=0.15, color="#1f77b4", edgecolors="none")
    if logy:
        ax.set_yscale("log")
    ax.set_xlabel(xlabel or xvar); ax.set_ylabel(f"{flux_col} [#/cm2-s-str-MeV]" + (" (log)" if logy else ""))
    ax.set_title(f"DESCRIPTIVE DIAGNOSTIC: {flux_col} vs {xvar}\n"
                 "NOAA-19 Jan-2024 region; not a fit, not causal, not a final boundary", fontsize=9)
    ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_high_flux_in_magnetic_space(df, inside_mask, save_path, xvar="mag_lon_sat", yvar="mag_lat_sat",
                                     sample=60000):
    """High-flux footprint samples vs the rest in a magnetic-coordinate plane (descriptive)."""
    d = df.copy(); d["_inside"] = inside_mask
    out = d[~d._inside][[xvar, yvar]].dropna()
    ins = d[d._inside][[xvar, yvar]].dropna()
    if len(out) > sample:
        out = out.sample(sample, random_state=0)
    fig, ax = plt.subplots(figsize=(7.2, 6.0))
    ax.scatter(out[xvar], out[yvar], s=3, alpha=0.12, color="#999999", edgecolors="none", label="outside footprint")
    ax.scatter(ins[xvar], ins[yvar], s=4, alpha=0.25, color="#d62728", edgecolors="none", label="inside footprint")
    ax.set_xlabel(xvar); ax.set_ylabel(yvar)
    ax.set_title("DESCRIPTIVE DIAGNOSTIC: high-flux footprint samples in magnetic-coordinate space\n"
                 "particle-defined footprint vs magnetic coords are related, not identical", fontsize=9)
    ax.legend(fontsize=8, markerscale=3); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_geographic_variable_map(df, var, save_path, step=5.0, lat_range=DEFAULT_LAT_RANGE,
                                 lon_range=DEFAULT_LON_RANGE, agg="median"):
    """Geographic map of a magnetic variable, cell-aggregated (descriptive context, not a measurement)."""
    d = assign_cells(df, step)
    g = d.groupby(["cell_lat", "cell_lon"])[var].agg(agg).reset_index()
    lat_min, lat_max = lat_range; lon_min, lon_max = lon_range
    n_lat = int(round((lat_max - lat_min) / step)); n_lon = int(round((lon_max - lon_min) / step))
    arr = np.full((n_lat, n_lon), np.nan)
    for r in g.itertuples():
        i = int(round((r.cell_lat - (lat_min + step / 2)) / step))
        j = int(round((r.cell_lon - (lon_min + step / 2)) / step))
        if 0 <= i < n_lat and 0 <= j < n_lon:
            arr[i, j] = getattr(r, var)
    lon_e = np.linspace(lon_min, lon_max, n_lon + 1); lat_e = np.linspace(lat_min, lat_max, n_lat + 1)
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    mesh = ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(arr), cmap="plasma", shading="flat")
    fig.colorbar(mesh, ax=ax, shrink=0.9, label=f"{agg} {var}")
    ax.set_xlabel("longitude [deg]"); ax.set_ylabel("latitude [deg]")
    ax.set_title(f"DESCRIPTIVE DIAGNOSTIC: geographic {agg} {var} (NOAA-19 Jan-2024)\n"
                 "model magnetic variable; not the particle footprint, not a final boundary", fontsize=9)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_particle_footprint_reference(grid_table_5, save_path, stat_col="mean_flux",
                                      mask_col="enough_samples_5deg",
                                      lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Geographic flux map (grey log10) + top10 & top5 selected-cell markers (particle reference)."""
    from .threshold_analysis import _pivot_to_2d, add_cell_area, flux_weighted_centroid
    lon_e, lat_e, base = _pivot_to_2d(grid_table_5, stat_col, 5.0, lat_range, lon_range, mask_col)
    data = np.where(base > 0, base, np.nan)
    covered = coverage_passed(add_cell_area(grid_table_5, 5.0, 5.0), mask_col)
    fig, ax = plt.subplots(figsize=(7.4, 6.2))
    finite = data[np.isfinite(data)]
    norm = LogNorm(vmin=finite.min(), vmax=finite.max()) if finite.size else None
    ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(data), cmap="Greys", norm=norm, shading="flat")
    for pct, lbl, col in [(90, "top10", "#2ca02c"), (95, "top5", "#d62728")]:
        cutoff = percentile_threshold(covered[stat_col], pct)
        sel = select_high_flux(covered, stat_col, cutoff)
        ax.scatter(sel["lon_bin_center"], sel["lat_bin_center"], s={90: 110, 95: 45}[pct],
                   facecolors="none", edgecolors=col, linewidths=1.4, label=f"{lbl} (n={len(sel)})")
        wlat, wlon = flux_weighted_centroid(sel, stat_col)
        ax.plot(wlon, wlat, "x", color=col, ms=10, mew=2.4)
    ax.set_xlim(lon_e[0], lon_e[-1]); ax.set_ylim(lat_e[0], lat_e[-1])
    ax.set_xlabel("longitude [deg] ([-180,180))"); ax.set_ylabel("latitude [deg]")
    ax.set_title("particle-defined high-flux footprint reference (NOAA-19 Jan-2024, 5deg mean)\n"
                 "x = flux-weighted centroid; exploratory; not a final SAA boundary", fontsize=9)
    ax.legend(fontsize=8, loc="lower left")
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
