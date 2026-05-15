"""Satellite availability audit + cautious one-satellite pilot comparison (Checkpoint 4E).

Methodological question: *can the existing monthly gridding + threshold pipeline be applied to another
comparable POES/MetOp satellite for the same month/channel/region, and do the threshold-defined
footprints remain broadly similar?* This is a **pilot compatibility check**, not a full multi-satellite
study and **not** a calibrated physical comparison.

Two parts:

1. :func:`build_satellite_audit` — for each candidate satellite, verify (from the **real** NCEI
   archive) January-2024 file availability and that the file opens with the CP2 loader and carries the
   expected variables and identical ``mep_omni_flux_p1`` metadata. Nothing assumed; everything probed.
2. :func:`run_satellite_sensitivity` — run the accepted CP4B sweep for NOAA-19 and the chosen pilot and
   stack with a ``satellite`` column (2 sats x 2 grids x 2 stats x 5 thresholds = 40 rows).

Strict caveats (carried from CP4A-D): absolute flux is **not** comparable across satellites without
calibration — compare footprint *location/shape* first; differences may be instrument/orbit/coverage,
not physical. ``mep_IFC_on == -1`` retained, uninterpreted. No SAA boundary / dose / health / danger /
discovery claims.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from calendar import monthrange

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from .load_poes import (
    NCEI_L1B_BASE, SAT_FILE_TOKEN, DEFAULT_CHANNEL, build_poes_l1b_url, download_poes_file,
    open_poes_netcdf, channel_metadata,
)
from .grid_flux import DEFAULT_LAT_RANGE, DEFAULT_LON_RANGE
from .threshold_analysis import run_sensitivity, _pivot_to_2d, percentile_threshold, select_high_flux, \
    flux_weighted_centroid, add_cell_area, coverage_passed, haversine_km, PERCENTILES, SENSITIVITY_COLUMNS

#: Candidate satellites confirmed to have a 2024 directory in the NCEI L1b archive (verified by
#: directory listing on 2026-06-09); names are validated again at runtime, never assumed.
CANDIDATE_SATELLITES = ["noaa15", "noaa18", "noaa19", "metop01", "metop03"]
REFERENCE_SATELLITE = "noaa19"

AUDIT_COLUMNS = [
    "satellite", "archive_path", "expected_days", "available_days", "missing_days", "sample_file",
    "opens_with_loader", "has_time_lat_lon", "has_mep_omni_flux_p1", "has_mep_IFC_on",
    "channel_units", "channel_long_name", "compatibility_note", "recommended_for_pilot",
]

SATELLITE_SENSITIVITY_COLUMNS = (
    ["satellite"]
    + [c for c in SENSITIVITY_COLUMNS if c != "notes"]
    + ["coverage_threshold_used", "satellite_compatibility_note"]
)

#: CP4F multi-satellite sensitivity columns (adds family/platform + an explicit no-abs-flux flag).
MULTISAT_SENSITIVITY_COLUMNS = (
    ["satellite", "satellite_family_or_platform"]
    + [c for c in SENSITIVITY_COLUMNS if c != "notes"]
    + ["coverage_threshold_used", "satellite_compatibility_note", "absolute_flux_comparison_allowed"]
)

PAIRWISE_DISTANCE_COLUMNS = [
    "comparison_case", "satellite_a", "satellite_b", "distance_km",
    "centroid_a_lat", "centroid_a_lon", "centroid_b_lat", "centroid_b_lon",
]


def satellite_family(satellite: str) -> str:
    """Coarse family/platform label inferred from the satellite name (else blank)."""
    s = satellite.lower()
    if s.startswith("noaa"):
        return "NOAA-POES"
    if s.startswith("metop"):
        return "MetOp"
    return ""


# ---------------------------------------------------------------- archive audit
def list_archive_month_days(satellite: str, year: int = 2024, month: int = 1,
                            base: str = NCEI_L1B_BASE, timeout: int = 120) -> tuple[str, list[int]]:
    """List the real NCEI directory and return ``(archive_url, sorted_available_day_numbers)``.

    Parses the official HTML directory index for ``poes_<token>_<YYYYMM><DD>_proc.nc`` entries.
    """
    if satellite not in SAT_FILE_TOKEN:
        raise ValueError(f"unknown satellite {satellite!r}")
    url = f"{base}/{year}/{satellite}/"
    token = SAT_FILE_TOKEN[satellite]
    html = urllib.request.urlopen(url, timeout=timeout).read().decode("utf-8", "replace")
    pat = re.compile(rf"poes_{token}_{year}{month:02d}(\d{{2}})_proc\.nc")
    days = sorted({int(m.group(1)) for m in pat.finditer(html)})
    return url, days


def audit_satellite(satellite: str, year: int = 2024, month: int = 1, raw_dir: str = "data/raw",
                    reference_meta: dict | None = None, retries: int = 3) -> dict:
    """Audit one candidate satellite: archive availability + a real sample-file variable/metadata check.

    Downloads (cached) the first-of-month file and opens it with the CP2 loader.  Returns one row of
    :data:`AUDIT_COLUMNS`.  ``reference_meta`` is the NOAA-19 ``{units, long_name}`` for comparison.
    """
    expected = monthrange(year, month)[1]
    row = {c: None for c in AUDIT_COLUMNS}
    row["satellite"] = satellite

    # 1) archive listing (real)
    try:
        url, days = list_archive_month_days(satellite, year, month)
        row["archive_path"] = url
        row["expected_days"] = expected
        row["available_days"] = len(days)
        missing = sorted(set(range(1, expected + 1)) - set(days))
        row["missing_days"] = ",".join(f"{m:02d}" for m in missing) if missing else "none"
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        row["archive_path"] = f"{NCEI_L1B_BASE}/{year}/{satellite}/"
        row["expected_days"] = expected
        row["available_days"] = 0
        row["missing_days"] = "ALL (listing failed)"
        row["opens_with_loader"] = False
        row["compatibility_note"] = f"archive listing failed: {type(exc).__name__}"
        row["recommended_for_pilot"] = "no"
        return row

    # 2) sample file open + variable / metadata check (real)
    sample_day = days[0] if days else 1
    sample_date = f"{year}-{month:02d}-{sample_day:02d}"
    last_exc = None
    for attempt in range(retries):
        try:
            p = download_poes_file(sample_date, satellite, output_dir=raw_dir,
                                   overwrite=(attempt > 0))
            with open_poes_netcdf(p) as ds:
                v = set(ds.variables)
                cm = channel_metadata(ds, [DEFAULT_CHANNEL])[DEFAULT_CHANNEL]
                row["sample_file"] = p.split("/")[-1]
                row["opens_with_loader"] = True
                row["has_time_lat_lon"] = all(x in v for x in ("time", "lat", "lon"))
                row["has_mep_omni_flux_p1"] = DEFAULT_CHANNEL in v
                row["has_mep_IFC_on"] = "mep_IFC_on" in v
                row["channel_units"] = cm["units"]
                row["channel_long_name"] = cm["long_name"]
            last_exc = None
            break
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            last_exc = exc
    if last_exc is not None:
        row["opens_with_loader"] = False
        row["compatibility_note"] = f"sample open failed after {retries} tries: {type(last_exc).__name__}"
        row["recommended_for_pilot"] = "no"
        return row

    # 3) compatibility verdict vs reference
    notes = []
    full = row["available_days"] == expected
    notes.append("full Jan coverage" if full else f"{row['available_days']}/{expected} days")
    compatible = bool(row["has_time_lat_lon"] and row["has_mep_omni_flux_p1"] and row["has_mep_IFC_on"])
    if reference_meta is not None:
        same_units = row["channel_units"] == reference_meta.get("units")
        same_name = row["channel_long_name"] == reference_meta.get("long_name")
        notes.append("p1 units+long_name match NOAA-19" if (same_units and same_name)
                     else "p1 metadata DIFFERS from NOAA-19")
        compatible = compatible and same_units and same_name
    else:
        notes.append("reference satellite")
    row["compatibility_note"] = "; ".join(notes)
    if satellite == REFERENCE_SATELLITE:
        row["recommended_for_pilot"] = "reference"
    elif compatible and full:
        row["recommended_for_pilot"] = "eligible"
    else:
        row["recommended_for_pilot"] = "no"
    return row


def build_satellite_audit(satellites=CANDIDATE_SATELLITES, year: int = 2024, month: int = 1,
                          raw_dir: str = "data/raw") -> pd.DataFrame:
    """Audit all candidates and return a tidy :data:`AUDIT_COLUMNS` table (NOAA-19 audited first)."""
    sats = list(satellites)
    sats.sort(key=lambda s: (s != REFERENCE_SATELLITE, s))  # reference first for its metadata
    ref_meta = None
    rows = []
    for sat in sats:
        row = audit_satellite(sat, year, month, raw_dir=raw_dir, reference_meta=ref_meta)
        if sat == REFERENCE_SATELLITE and row.get("opens_with_loader"):
            ref_meta = {"units": row["channel_units"], "long_name": row["channel_long_name"]}
        rows.append(row)
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS).sort_values("satellite").reset_index(drop=True)


def choose_pilot(audit: pd.DataFrame, prefer=("noaa18", "metop03", "metop01", "noaa15")) -> str | None:
    """Pick one pilot from the audited 'eligible' satellites, preferring the closest NOAA-19 analog.

    Preference order: NOAA-18 (same POES series + SEM-2/MEPED generation as NOAA-19) > MetOp (SEM-2,
    different platform) > NOAA-15 (oldest, degradation). Returns ``None`` if none are eligible.
    """
    eligible = set(audit.loc[audit.recommended_for_pilot == "eligible", "satellite"])
    for s in prefer:
        if s in eligible:
            return s
    return None


# ---------------------------------------------------------------- satellite sensitivity sweep
def run_satellite_sensitivity(sat_specs: list[dict]) -> pd.DataFrame:
    """Run the CP4B sweep per satellite and stack with satellite/coverage/compat columns.

    Each spec: ``{satellite, note, grids:[{grid_deg, step, table, mask_col, coverage_threshold}, ...]}``.
    Returns a tidy frame with :data:`SATELLITE_SENSITIVITY_COLUMNS` (2 sats x 2 grids x 2 stats x 5
    thresholds = 40 rows).
    """
    frames = []
    for spec in sat_specs:
        grids = [(g["grid_deg"], g["step"], g["table"], g["mask_col"]) for g in spec["grids"]]
        df = run_sensitivity(grids).drop(columns=["notes"])
        df.insert(0, "satellite", spec["satellite"])
        thr = {g["grid_deg"]: g["coverage_threshold"] for g in spec["grids"]}
        df["coverage_threshold_used"] = df["grid_deg"].map(thr).astype(int)
        df["satellite_compatibility_note"] = spec["note"]
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    return out[SATELLITE_SENSITIVITY_COLUMNS]


def save_table(df: pd.DataFrame, csv_path, parquet_path) -> None:
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)


# ---------------------------------------------------------------- plotting
def plot_satellite_mean_map(table, step, mask_col, save_path, satellite, stat="mean_flux",
                            lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Single coverage-masked log10 mean-flux map for one satellite (blank = no data/masked)."""
    lon_e, lat_e, base = _pivot_to_2d(table, stat, step, lat_range, lon_range, mask_col)
    data = np.where(base > 0, base, np.nan)
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    finite = data[np.isfinite(data)]
    norm = LogNorm(vmin=finite.min(), vmax=finite.max()) if finite.size else None
    mesh = ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(data), cmap="viridis", norm=norm, shading="flat")
    fig.colorbar(mesh, ax=ax, shrink=0.9, label=f"{stat} mep_omni_flux_p1 [#/cm2-s-str-MeV] log10")
    ax.set_xlim(lon_e[0], lon_e[-1]); ax.set_ylim(lat_e[0], lat_e[-1])
    ax.set_xlabel("longitude [deg] ([-180,180))"); ax.set_ylabel("latitude [deg]")
    ax.set_title(f"{satellite} 2024-01 {stat} {int(step)}deg (p1 ~25 MeV)\n"
                 "exploratory; calibration-limited; not a final SAA boundary", fontsize=9)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_satellite_sample_count(table, step, save_path, satellite,
                                lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Single linear sample-count map for one satellite."""
    lon_e, lat_e, base = _pivot_to_2d(table, "sample_count", step, lat_range, lon_range)
    fig, ax = plt.subplots(figsize=(7.0, 6.0))
    mesh = ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(base), cmap="magma", shading="flat")
    fig.colorbar(mesh, ax=ax, shrink=0.9, label="sample_count (linear)")
    ax.set_xlim(lon_e[0], lon_e[-1]); ax.set_ylim(lat_e[0], lat_e[-1])
    ax.set_xlabel("longitude [deg]"); ax.set_ylabel("latitude [deg]")
    ax.set_title(f"{satellite} 2024-01 sample_count {int(step)}deg", fontsize=9)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


_SAT_COLORS = {"noaa19": "#1f77b4", "noaa18": "#d62728", "metop03": "#2ca02c",
               "metop01": "#ff7f0e", "noaa15": "#9467bd"}


def plot_satellite_comparison(sat_tables: list[tuple], step, mask_col, save_path, threshold_label="top10",
                              stat="mean_flux", lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Overlay the top-X% selected cells of each satellite + their flux-weighted centroids.

    ``sat_tables`` is a list of ``(satellite, table)``.  Footprint location/shape comparison only —
    absolute flux is not compared.
    """
    pct = dict((lbl, p) for p, lbl in PERCENTILES)[threshold_label]
    fig, ax = plt.subplots(figsize=(7.6, 6.3))
    for sat, table in sat_tables:
        covered = coverage_passed(add_cell_area(table, step, step), mask_col)
        cutoff = percentile_threshold(covered[stat], pct)
        sel = select_high_flux(covered, stat, cutoff)
        col = _SAT_COLORS.get(sat, "#333333")
        ax.scatter(sel["lon_bin_center"], sel["lat_bin_center"], s=70, facecolors="none",
                   edgecolors=col, linewidths=1.4, label=f"{sat} {threshold_label} (n={len(sel)})")
        wlat, wlon = flux_weighted_centroid(sel, stat)
        ax.plot(wlon, wlat, marker="x", color=col, ms=11, mew=2.6)
    ax.set_xlim(lon_range); ax.set_ylim(lat_range)
    ax.set_xlabel("longitude [deg] ([-180,180))"); ax.set_ylabel("latitude [deg]")
    ax.set_title(f"satellite footprint comparison - {threshold_label} {int(step)}deg {stat}\n"
                 "x = flux-weighted centroid; location/shape only; calibration-limited", fontsize=9)
    ax.legend(fontsize=7, loc="lower left"); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_satellite_centroid_comparison(sens_df, save_path, grid_deg=5, stat="mean_flux"):
    """Flux-weighted centroid vs threshold for each satellite (inter-satellite footprint consistency)."""
    sub = sens_df[(sens_df.grid_deg == grid_deg) & (sens_df.statistic_used == stat)]
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    for sat in sub.satellite.unique():
        s = sub[sub.satellite == sat].sort_values("percentile_cutoff")
        ax.plot(s.centroid_lon_flux_weighted, s.centroid_lat_flux_weighted, "-o", ms=5,
                color=_SAT_COLORS.get(sat, "#333333"), label=sat)
        for _, r in s.iterrows():
            ax.annotate(r.threshold_label.replace("top", ""),
                        (r.centroid_lon_flux_weighted, r.centroid_lat_flux_weighted), fontsize=6)
    ax.set_xlabel("flux-weighted centroid lon [deg]"); ax.set_ylabel("flux-weighted centroid lat [deg]")
    ax.set_title(f"flux-weighted centroid by satellite vs threshold ({grid_deg}deg {stat})\n"
                 "calibration-limited; exploratory; not a final SAA center", fontsize=9)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_satellite_area_by_threshold(sens_df, save_path, grid_deg=5, stat="mean_flux"):
    """Selected area proxy vs threshold, one line per satellite (area-shape consistency)."""
    sub = sens_df[(sens_df.grid_deg == grid_deg) & (sens_df.statistic_used == stat)]
    fig, ax = plt.subplots(figsize=(7.4, 5.4))
    order = [lbl for _, lbl in PERCENTILES]
    x = np.arange(len(order))
    for sat in sub.satellite.unique():
        s = sub[sub.satellite == sat].set_index("threshold_label").reindex(order)
        ax.plot(x, s.selected_area_km2.to_numpy() / 1e6, "-o", ms=5,
                color=_SAT_COLORS.get(sat, "#333333"), label=sat)
    ax.set_xticks(x); ax.set_xticklabels(order)
    ax.set_xlabel("threshold"); ax.set_ylabel("selected area proxy [million km2]")
    ax.set_title(f"selected-area by threshold per satellite ({grid_deg}deg {stat})\n"
                 "area proxy; calibration-limited; exploratory", fontsize=9)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- CP4F multi-satellite
def run_multisatellite_sensitivity(sat_specs: list[dict]) -> pd.DataFrame:
    """Run the CP4B sweep for several satellites and stack with family + no-abs-flux columns.

    Each spec: ``{satellite, note, grids:[{grid_deg, step, table, mask_col, coverage_threshold}, ...]}``.
    Returns a tidy frame with :data:`MULTISAT_SENSITIVITY_COLUMNS` (N sats x 2 grids x 2 stats x 5
    thresholds).  ``absolute_flux_comparison_allowed`` is hard-set ``False`` on every row.
    """
    frames = []
    for spec in sat_specs:
        grids = [(g["grid_deg"], g["step"], g["table"], g["mask_col"]) for g in spec["grids"]]
        df = run_sensitivity(grids).drop(columns=["notes"])
        df.insert(0, "satellite_family_or_platform", satellite_family(spec["satellite"]))
        df.insert(0, "satellite", spec["satellite"])
        thr = {g["grid_deg"]: g["coverage_threshold"] for g in spec["grids"]}
        df["coverage_threshold_used"] = df["grid_deg"].map(thr).astype(int)
        df["satellite_compatibility_note"] = spec["note"]
        df["absolute_flux_comparison_allowed"] = False
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    return out[MULTISAT_SENSITIVITY_COLUMNS]


def pairwise_centroid_distances(sens_df, cases) -> pd.DataFrame:
    """All-pairs flux-weighted centroid distances per comparison case.

    ``cases`` is a list of ``(comparison_case, grid_deg, statistic, threshold_label)``.  Returns a
    tidy :data:`PAIRWISE_DISTANCE_COLUMNS` frame (one row per unordered satellite pair per case).
    """
    import itertools
    rows = []
    for case, gd, stat, thr in cases:
        sub = sens_df[(sens_df.grid_deg == gd) & (sens_df.statistic_used == stat)
                      & (sens_df.threshold_label == thr)]
        cents = {r.satellite: (r.centroid_lat_flux_weighted, r.centroid_lon_flux_weighted)
                 for r in sub.itertuples()}
        for a, b in itertools.combinations(sorted(cents), 2):
            la, lo = cents[a]; lb, lob = cents[b]
            rows.append({"comparison_case": case, "satellite_a": a, "satellite_b": b,
                         "distance_km": haversine_km(la, lo, lb, lob),
                         "centroid_a_lat": la, "centroid_a_lon": lo,
                         "centroid_b_lat": lb, "centroid_b_lon": lob})
    return pd.DataFrame(rows, columns=PAIRWISE_DISTANCE_COLUMNS)


def plot_multisatellite_centroids(sens_df, save_path, thresholds=("top10", "top5"),
                                  grid_deg=5, stat="mean_flux",
                                  lat_range=DEFAULT_LAT_RANGE, lon_range=DEFAULT_LON_RANGE):
    """Flux-weighted centroid of each satellite for top10 & top5 (marker shape = threshold)."""
    markers = {"top10": "o", "top5": "^"}
    fig, ax = plt.subplots(figsize=(7.4, 6.4))
    for thr in thresholds:
        sub = sens_df[(sens_df.grid_deg == grid_deg) & (sens_df.statistic_used == stat)
                      & (sens_df.threshold_label == thr)]
        for r in sub.itertuples():
            ax.plot(r.centroid_lon_flux_weighted, r.centroid_lat_flux_weighted,
                    marker=markers.get(thr, "s"), ms=11, color=_SAT_COLORS.get(r.satellite, "#333"),
                    label=f"{r.satellite} {thr}")
            ax.annotate(f"{r.satellite}", (r.centroid_lon_flux_weighted, r.centroid_lat_flux_weighted),
                        fontsize=6.5, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("flux-weighted centroid lon [deg]"); ax.set_ylabel("flux-weighted centroid lat [deg]")
    ax.set_title(f"multi-satellite flux-weighted centroids ({grid_deg}deg {stat}; o=top10, ^=top5)\n"
                 "calibration-limited footprint-location consistency; not a final SAA center", fontsize=9)
    ax.legend(fontsize=6, ncol=2); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_pairwise_distance_heatmap(pairwise_df, comparison_case, save_path):
    """Symmetric satellite x satellite centroid-distance heatmap (km) for one comparison case."""
    sub = pairwise_df[pairwise_df.comparison_case == comparison_case]
    sats = sorted(set(sub.satellite_a) | set(sub.satellite_b))
    n = len(sats)
    idx = {s: i for i, s in enumerate(sats)}
    M = np.full((n, n), np.nan)
    for i in range(n):
        M[i, i] = 0.0
    for r in sub.itertuples():
        i, j = idx[r.satellite_a], idx[r.satellite_b]
        M[i, j] = M[j, i] = r.distance_km
    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    im = ax.imshow(M, cmap="viridis")
    fig.colorbar(im, ax=ax, shrink=0.85, label="flux-weighted centroid distance [km]")
    ax.set_xticks(range(n)); ax.set_xticklabels(sats, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n)); ax.set_yticklabels(sats, fontsize=8)
    for i in range(n):
        for j in range(n):
            if np.isfinite(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if M[i, j] < np.nanmax(M) * 0.6 else "black")
    ax.set_title(f"pairwise centroid distance (km) - {comparison_case}\n"
                 "calibration-limited; location only", fontsize=9)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
