"""Quantitative magnetic-coordinate framing of the particle-defined footprint (Checkpoint 5B).

Builds on the CP5A flux+magnetic dataset
(``data/processed/cp5a_noaa19_2024-01_region_flux_plus_magnetic.parquet``) and the accepted CP4A grid
tables + CP5A footprint logic. It produces, **descriptively**:

* explicit per-variable validity rules + excluded-row accounting,
* magnetic-binned flux profiles (median / mean / p90 / p95 + footprint membership fractions),
* inside-vs-outside footprint magnetic summaries with a clearly-defined separation metric,
* simple magnetic-space concentration metrics for ``Btot_sat`` and ``L_IGRF``.

This is **descriptive magnetic-coordinate framing** — *not* a causal model, *not* a classification rule,
*not* a final SAA boundary, and the particle footprint is *not* equated with the field minimum. Magnetic
variables are NOAA-provided IGRF model quantities (no external IGRF added). ``L_IGRF == -1`` is a
documented invalid sentinel and is excluded wherever ``L_IGRF`` is used. No dose/health/danger/discovery.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

from .grid_flux import DEFAULT_CHANNEL
from .magnetic_audit import assign_cells, selected_cells_from_grid, INVALID_SENTINELS

# ---------------------------------------------------------------- validity rules
VALIDITY_COLUMNS = [
    "variable_name", "rows_total", "rows_valid", "rows_invalid", "invalid_rule",
    "valid_min", "valid_max", "note",
]

PROFILE_VARIABLES = ["Btot_sat", "L_IGRF", "mag_lat_sat", "MLT"]
SUMMARY_VARIABLES = ["Btot_sat", "L_IGRF", "mag_lat_sat", "MLT"]


def valid_mask(df: pd.DataFrame, var: str) -> np.ndarray:
    """Boolean validity mask for a magnetic variable per the documented CP5B rules."""
    v = df[var].to_numpy("float64")
    finite = np.isfinite(v)
    if var == "Btot_sat":
        return finite & (v > 0)
    if var == "L_IGRF":
        return finite & (v != INVALID_SENTINELS["L_IGRF"]) & (v > 0)
    if var == "mag_lat_sat":
        return finite & (v >= -90) & (v <= 90)
    if var == "mag_lon_sat":
        return finite & (v >= 0) & (v <= 360)
    if var == "MLT":
        return finite & (v >= 0) & (v <= 24)
    return finite


_INVALID_RULE = {
    "Btot_sat": "finite and > 0",
    "L_IGRF": "finite, != -1 sentinel, and > 0",
    "mag_lat_sat": "finite and within [-90, 90] deg",
    "mag_lon_sat": "finite and within [0, 360] deg (use circular/wrap-aware methods only)",
    "MLT": "finite and within [0, 24] h (local-time diagnostic only)",
}


def magnetic_validity_table(df: pd.DataFrame,
                            variables=("Btot_sat", "L_IGRF", "mag_lat_sat", "mag_lon_sat", "MLT")) -> pd.DataFrame:
    """Per-variable validity accounting (:data:`VALIDITY_COLUMNS`)."""
    rows = []
    n = len(df)
    for var in variables:
        m = valid_mask(df, var)
        vv = df[var].to_numpy("float64")[m]
        note = "wrap-aware handling required; naive IQR/mean across 0/360 is invalid" if var == "mag_lon_sat" \
            else ("local-time diagnostic only; non-discrimination is not physical proof" if var == "MLT"
                  else "")
        rows.append({
            "variable_name": var, "rows_total": int(n), "rows_valid": int(m.sum()),
            "rows_invalid": int(n - m.sum()), "invalid_rule": _INVALID_RULE[var],
            "valid_min": float(vv.min()) if vv.size else float("nan"),
            "valid_max": float(vv.max()) if vv.size else float("nan"), "note": note,
        })
    return pd.DataFrame(rows, columns=VALIDITY_COLUMNS)


# ---------------------------------------------------------------- footprint membership
def add_footprint_flags(df: pd.DataFrame, grid5, grid2) -> pd.DataFrame:
    """Add boolean in-footprint columns for the 4 pilot cases (5deg/2deg x top10/top5, mean_flux)."""
    out = df.copy()
    specs = [(grid5, 5.0, "enough_samples_5deg", 90, "in_top10_5deg"),
             (grid5, 5.0, "enough_samples_5deg", 95, "in_top5_5deg"),
             (grid2, 2.0, "enough_samples_2deg", 90, "in_top10_2deg"),
             (grid2, 2.0, "enough_samples_2deg", 95, "in_top5_2deg")]
    for grid, step, mask_col, pct, colname in specs:
        sel, _ = selected_cells_from_grid(grid, "mean_flux", mask_col, pct)
        binned = assign_cells(out, step)
        keys = list(zip(binned["cell_lat"].round(3), binned["cell_lon"].round(3)))
        out[colname] = np.array([k in sel for k in keys])
    return out


# ---------------------------------------------------------------- binned flux profiles
PROFILE_COLUMNS = [
    "variable", "bin_index", "bin_left", "bin_right", "bin_center", "sample_count",
    "median_flux", "mean_flux", "p90_flux", "p95_flux",
    "fraction_of_samples_in_top10_geographic_footprint",
    "fraction_of_samples_in_top5_geographic_footprint",
]

#: bin counts per variable (fixed-width over observed valid range; documented via edges in the table).
PROFILE_NBINS = {"Btot_sat": 14, "L_IGRF": 12, "mag_lat_sat": 12, "MLT": 12}


def make_bins(values: np.ndarray, nbins: int) -> np.ndarray:
    return np.linspace(float(np.min(values)), float(np.max(values)), nbins + 1)


def binned_flux_profile(df: pd.DataFrame, var: str, nbins: int | None = None,
                        flux_col: str = DEFAULT_CHANNEL,
                        in10_col: str = "in_top10_5deg", in5_col: str = "in_top5_5deg") -> pd.DataFrame:
    """Descriptive flux profile vs ``var`` (valid samples only); fractions use the 5deg footprints."""
    nbins = nbins or PROFILE_NBINS.get(var, 12)
    m = valid_mask(df, var)
    d = df.loc[m, [var, flux_col, in10_col, in5_col]].copy()
    edges = make_bins(d[var].to_numpy("float64"), nbins)
    idx = np.clip(np.digitize(d[var].to_numpy("float64"), edges) - 1, 0, nbins - 1)
    d["_b"] = idx
    rows = []
    for b in range(nbins):
        g = d[d._b == b]
        f = g[flux_col].to_numpy("float64")
        rows.append({
            "variable": var, "bin_index": b, "bin_left": float(edges[b]), "bin_right": float(edges[b + 1]),
            "bin_center": float(0.5 * (edges[b] + edges[b + 1])), "sample_count": int(len(g)),
            "median_flux": float(np.median(f)) if f.size else float("nan"),
            "mean_flux": float(f.mean()) if f.size else float("nan"),
            "p90_flux": float(np.percentile(f, 90)) if f.size else float("nan"),
            "p95_flux": float(np.percentile(f, 95)) if f.size else float("nan"),
            "fraction_of_samples_in_top10_geographic_footprint": float(g[in10_col].mean()) if len(g) else float("nan"),
            "fraction_of_samples_in_top5_geographic_footprint": float(g[in5_col].mean()) if len(g) else float("nan"),
        })
    return pd.DataFrame(rows, columns=PROFILE_COLUMNS)


def all_binned_profiles(df: pd.DataFrame, variables=PROFILE_VARIABLES) -> pd.DataFrame:
    return pd.concat([binned_flux_profile(df, v) for v in variables], ignore_index=True)


# ---------------------------------------------------------------- footprint magnetic summary
FOOTPRINT_SUMMARY_COLUMNS = [
    "comparison_case", "grid_deg", "threshold_label", "magnetic_variable",
    "inside_count", "outside_count", "median_inside", "median_outside", "iqr_inside", "iqr_outside",
    "p10_inside", "p90_inside", "p10_outside", "p90_outside",
    "separation_metric", "interpretation_note",
]

#: separation_metric := (median_outside - median_inside) / (0.5*(iqr_inside+iqr_outside))
#: a standardized median difference; positive => footprint sits LOWER than the regional background.
_SEP_DEF = "std median diff = (median_out - median_in)/(0.5*(iqr_in+iqr_out)); +ve = footprint lower"


def footprint_magnetic_summary(df: pd.DataFrame, variables=SUMMARY_VARIABLES) -> pd.DataFrame:
    """Inside/outside footprint quantiles + separation metric for the 4 pilot cases (valid samples only)."""
    cases = [("top10_5deg_mean", 5, "top10", "in_top10_5deg"),
             ("top5_5deg_mean", 5, "top5", "in_top5_5deg"),
             ("top10_2deg_mean", 2, "top10", "in_top10_2deg"),
             ("top5_2deg_mean", 2, "top5", "in_top5_2deg")]
    rows = []
    for case, gd, lbl, col in cases:
        for var in variables:
            m = valid_mask(df, var)
            sub = df.loc[m, [var, col]]
            vin = sub.loc[sub[col], var].to_numpy("float64")
            vout = sub.loc[~sub[col], var].to_numpy("float64")
            def q(a, p):
                return float(np.percentile(a, p)) if a.size else float("nan")
            iqr_in = q(vin, 75) - q(vin, 25); iqr_out = q(vout, 75) - q(vout, 25)
            med_in = q(vin, 50); med_out = q(vout, 50)
            pooled = 0.5 * (iqr_in + iqr_out)
            sep = (med_out - med_in) / pooled if pooled and np.isfinite(pooled) and pooled != 0 else float("nan")
            note = ("low-Btot concentration" if var == "Btot_sat" else
                    "low-L concentration" if var == "L_IGRF" else
                    "magnetic-latitude narrowing" if var == "mag_lat_sat" else
                    "local-time diagnostic; weak separation expected")
            rows.append({
                "comparison_case": case, "grid_deg": gd, "threshold_label": lbl, "magnetic_variable": var,
                "inside_count": int(vin.size), "outside_count": int(vout.size),
                "median_inside": med_in, "median_outside": med_out,
                "iqr_inside": iqr_in, "iqr_outside": iqr_out,
                "p10_inside": q(vin, 10), "p90_inside": q(vin, 90),
                "p10_outside": q(vout, 10), "p90_outside": q(vout, 90),
                "separation_metric": sep, "interpretation_note": f"{note}; {_SEP_DEF}",
            })
    return pd.DataFrame(rows, columns=FOOTPRINT_SUMMARY_COLUMNS)


# ---------------------------------------------------------------- concentration metrics
CONCENTRATION_COLUMNS = ["metric", "footprint", "variable", "value", "definition_note"]


def concentration_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Descriptive low-Btot / low-L concentration metrics for the top10/top5 footprints (5deg)."""
    rows = []
    # regional reference quartiles (valid samples)
    bm = valid_mask(df, "Btot_sat"); lm = valid_mask(df, "L_IGRF")
    b_all = df.loc[bm, "Btot_sat"].to_numpy("float64")
    l_all = df.loc[lm, "L_IGRF"].to_numpy("float64")
    b_q25 = float(np.percentile(b_all, 25)); l_q25 = float(np.percentile(l_all, 25))

    for fp in ("in_top10_5deg", "in_top5_5deg"):
        lbl = "top10" if "top10" in fp else "top5"
        # fraction of footprint samples below regional q25
        bf = df.loc[bm & df[fp], "Btot_sat"].to_numpy("float64")
        lf = df.loc[lm & df[fp], "L_IGRF"].to_numpy("float64")
        rows.append({"metric": "fraction_below_regional_q25", "footprint": lbl, "variable": "Btot_sat",
                     "value": float((bf < b_q25).mean()) if bf.size else float("nan"),
                     "definition_note": f"frac of {lbl} footprint samples with Btot_sat < regional q25 ({b_q25:.0f} nT)"})
        rows.append({"metric": "fraction_in_regional_lowest_quartile", "footprint": lbl, "variable": "L_IGRF",
                     "value": float((lf < l_q25).mean()) if lf.size else float("nan"),
                     "definition_note": f"frac of {lbl} footprint samples with L_IGRF < regional q25 ({l_q25:.3f})"})
        # regional fraction needed to capture X% of footprint samples when sorted by low Btot / low L
        for var, mask, allv in (("Btot_sat", bm, b_all), ("L_IGRF", lm, l_all)):
            fv = df.loc[mask & df[fp], var].to_numpy("float64")
            if fv.size:
                order = np.sort(allv)
                # regional rank fraction (<=) of each footprint sample
                ranks = np.searchsorted(order, fv, side="right") / order.size
                for pct in (50, 75, 90):
                    rows.append({"metric": f"regional_fraction_to_capture_{pct}pct", "footprint": lbl,
                                 "variable": var, "value": float(np.percentile(ranks, pct)),
                                 "definition_note": f"smallest low-{var} regional fraction containing {pct}% of {lbl} footprint samples"})
    return pd.DataFrame(rows, columns=CONCENTRATION_COLUMNS)


def save_table(df, csv_path, parquet_path=None):
    df.to_csv(csv_path, index=False)
    if parquet_path is not None:
        df.to_parquet(parquet_path, index=False)


# ---------------------------------------------------------------- plots
def plot_flux_profile(profile_df, var, save_path):
    """Median + p90 flux vs magnetic-variable bin center (descriptive profile)."""
    p = profile_df[profile_df.variable == var]
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.plot(p.bin_center, p.median_flux, "-o", ms=5, color="#1f77b4", label="median flux")
    ax.plot(p.bin_center, p.p90_flux, "-^", ms=4, color="#d62728", label="p90 flux")
    ax.set_xlabel(var); ax.set_ylabel(f"{DEFAULT_CHANNEL} [#/cm2-s-str-MeV]")
    ax2 = ax.twinx()
    ax2.bar(p.bin_center, p.sample_count, width=(p.bin_right - p.bin_left) * 0.9, alpha=0.12,
            color="#555555", label="sample_count")
    ax2.set_ylabel("sample_count (bars)")
    ax.set_title(f"DESCRIPTIVE magnetic-binned flux profile vs {var}\n"
                 "NOAA-19 Jan-2024 (valid samples); not a boundary, not causal", fontsize=9)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_inside_outside(df, var, save_path, in_col="in_top10_5deg"):
    """Overlaid inside/outside histograms of a magnetic variable (valid samples; descriptive)."""
    m = valid_mask(df, var)
    vin = df.loc[m & df[in_col], var].to_numpy("float64")
    vout = df.loc[m & ~df[in_col], var].to_numpy("float64")
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    lo = min(vin.min(), vout.min()); hi = max(vin.max(), vout.max())
    bins = np.linspace(lo, hi, 50)
    ax.hist(vout, bins=bins, density=True, alpha=0.5, color="#999999", label="outside footprint")
    ax.hist(vin, bins=bins, density=True, alpha=0.6, color="#d62728", label="inside top10 footprint")
    ax.set_xlabel(var); ax.set_ylabel("density")
    ax.set_title(f"DESCRIPTIVE inside-vs-outside footprint distribution: {var}\n"
                 "NOAA-19 Jan-2024 (top10 5deg mean); not a boundary, not causal", fontsize=9)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_btot_vs_l(df, save_path, flux_col=DEFAULT_CHANNEL, sample=60000):
    """Btot_sat vs L_IGRF scatter colored by log flux (valid samples; descriptive)."""
    m = valid_mask(df, "Btot_sat") & valid_mask(df, "L_IGRF")
    d = df.loc[m, ["Btot_sat", "L_IGRF", flux_col]].copy()
    d = d[d[flux_col] > 0]
    if len(d) > sample:
        d = d.sample(sample, random_state=0)
    fig, ax = plt.subplots(figsize=(7.4, 5.8))
    sc = ax.scatter(d["L_IGRF"], d["Btot_sat"], c=d[flux_col], s=4, alpha=0.3,
                    norm=LogNorm(vmin=max(d[flux_col].min(), 1e-3), vmax=d[flux_col].max()), cmap="viridis")
    fig.colorbar(sc, ax=ax, label=f"{flux_col} [#/cm2-s-str-MeV] (log)")
    ax.set_xlabel("L_IGRF"); ax.set_ylabel("Btot_sat [nT]")
    ax.set_title("DESCRIPTIVE: Btot_sat vs L_IGRF colored by proton flux\n"
                 "NOAA-19 Jan-2024 (valid samples); not a boundary, not causal", fontsize=9)
    ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_high_flux_btot_vs_l(df, save_path, in_col="in_top10_5deg", sample=60000):
    """Btot_sat vs L_IGRF: inside-footprint samples vs the rest (valid samples; descriptive)."""
    m = valid_mask(df, "Btot_sat") & valid_mask(df, "L_IGRF")
    d = df.loc[m, ["Btot_sat", "L_IGRF", in_col]].copy()
    out = d[~d[in_col]]; ins = d[d[in_col]]
    if len(out) > sample:
        out = out.sample(sample, random_state=0)
    fig, ax = plt.subplots(figsize=(7.4, 5.8))
    ax.scatter(out["L_IGRF"], out["Btot_sat"], s=4, alpha=0.12, color="#999999", label="outside footprint")
    ax.scatter(ins["L_IGRF"], ins["Btot_sat"], s=5, alpha=0.30, color="#d62728", label="inside top10 footprint")
    ax.set_xlabel("L_IGRF"); ax.set_ylabel("Btot_sat [nT]")
    ax.set_title("DESCRIPTIVE: high-flux footprint in Btot_sat vs L_IGRF space\n"
                 "NOAA-19 Jan-2024; particle footprint vs magnetic coords are related, not identical", fontsize=9)
    ax.legend(fontsize=8, markerscale=3); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_mag_lat_lon_wrapaware(df, save_path, in_col="in_top10_5deg", sample=60000):
    """mag_lat_sat vs mag_lon_sat scatter (wrap-aware: x axis is the natural [0,360), no IQR/mean drawn)."""
    m = valid_mask(df, "mag_lat_sat") & valid_mask(df, "mag_lon_sat")
    d = df.loc[m, ["mag_lat_sat", "mag_lon_sat", in_col]].copy()
    out = d[~d[in_col]]; ins = d[d[in_col]]
    if len(out) > sample:
        out = out.sample(sample, random_state=0)
    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    ax.scatter(out["mag_lon_sat"], out["mag_lat_sat"], s=4, alpha=0.12, color="#999999", label="outside footprint")
    ax.scatter(ins["mag_lon_sat"], ins["mag_lat_sat"], s=5, alpha=0.30, color="#d62728", label="inside top10 footprint")
    ax.set_xlim(0, 360); ax.set_xticks(range(0, 361, 60))
    ax.set_xlabel("mag_lon_sat [deg] (wrap-aware axis [0,360); no naive IQR/mean computed)")
    ax.set_ylabel("mag_lat_sat [deg]")
    ax.set_title("DESCRIPTIVE: footprint samples in magnetic lat/lon (wrap-aware)\n"
                 "NOAA-19 Jan-2024; not a boundary, not causal", fontsize=9)
    ax.legend(fontsize=8, markerscale=3); ax.grid(alpha=0.3)
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
