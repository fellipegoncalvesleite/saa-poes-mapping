"""Phase 4C: the five main paper figures and the supplementary tables.

Run from repository root: PYTHONPATH=src python scripts/make_paper_figures.py
Reads only canonical outputs (outputs/tables, outputs/channel_assurance,
outputs/qc_sensitivity, outputs/audit_replay) and site/public/data/geography.json (Natural Earth 1:110m, public
domain). Writes paper/figures/fig{1..5}.{pdf,png} and paper/tables/*.csv. Deterministic: PDF
metadata dates are suppressed.
"""
from __future__ import annotations

from pathlib import Path
import itertools
import json
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LogNorm  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from saa.threshold_analysis import cell_area_km2, haversine_km  # noqa: E402

T = Path("outputs/tables")
CA = Path("outputs/channel_assurance")
QS = Path("outputs/qc_sensitivity")
FIG = Path("paper/figures")
TAB = Path("paper/tables")

# Reference categorical palette (dataviz skill, light mode), first three slots validate all-pairs.
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
SEQ = "Blues"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.fontsize": 6.8,
    "legend.frameon": False, "lines.linewidth": 1.6, "pdf.fonttype": 42, "svg.fonttype": "none",
    "axes.spines.top": False, "axes.spines.right": False, "grid.color": GRID, "grid.linewidth": 0.6,
})
META = {"CreationDate": None, "ModDate": None, "Producer": "matplotlib", "Creator": "make_paper_figures.py"}
LAT, LON = (-70, 20), (-100, 20)
GEO = json.loads(Path("site/public/data/geography.json").read_text())


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf", metadata=META)
    fig.savefig(FIG / f"{name}.png", dpi=200, metadata={"Software": None})
    plt.close(fig)


def coast(ax):
    for layer, lw in (("coastlines", 0.6), ("borders", 0.3)):
        for line in GEO[layer]:
            a = np.asarray(line)
            ax.plot(a[:, 0], a[:, 1], color="#5c5b57", lw=lw, zorder=3)
    ax.set_xlim(*LON)
    ax.set_ylim(*LAT)
    ax.set_aspect(1.0)
    ax.set_xlabel("longitude (°)")
    ax.set_ylabel("latitude (°)")


def grid_array(table, col, step):
    nl, nn = int(round(90 / step)), int(round(120 / step))
    arr = np.full((nl, nn), np.nan)
    i = np.rint((table.lat_bin_center.to_numpy() - (LAT[0] + step / 2)) / step).astype(int)
    j = np.rint((table.lon_bin_center.to_numpy() - (LON[0] + step / 2)) / step).astype(int)
    arr[i, j] = table[col].to_numpy(float)
    return np.linspace(*LON, nn + 1), np.linspace(*LAT, nl + 1), arr


def footprint(table, stat, pct, mask):
    cov = table[table[mask].astype(bool)]
    cut = float(np.percentile(cov[stat].to_numpy(float), pct))
    return cov[cov[stat] >= cut], cut


def centroid(sel, stat, step):
    w = sel[stat].to_numpy(float) * cell_area_km2(sel.lat_bin_center.to_numpy(float), step, step)
    return float((sel.lat_bin_center * w).sum() / w.sum()), float((sel.lon_bin_center * w).sum() / w.sum())


def outline(ax, sel, step, color, lw=1.1):
    cells = set(zip(sel.lat_bin_center.round(6), sel.lon_bin_center.round(6)))
    h = step / 2
    for la, lo in cells:
        for dla, dlo, seg in ((step, 0, ((lo - h, lo + h), (la + h, la + h))),
                              (-step, 0, ((lo - h, lo + h), (la - h, la - h))),
                              (0, step, ((lo + h, lo + h), (la - h, la + h))),
                              (0, -step, ((lo - h, lo - h), (la - h, la + h)))):
            if (round(la + dla, 6), round(lo + dlo, 6)) not in cells:
                ax.plot(*seg, color=color, lw=lw, solid_capstyle="round", zorder=5)


def panel_letter(ax, s):
    ax.set_title(s, loc="left")


# ------------------------------------------------------------------------------------ figure 1
def fig1():
    g5 = pd.read_parquet(T / "cp4a_noaa19_2024-01_grid_5deg.parquet")
    g2 = pd.read_parquet(T / "cp4a_noaa19_2024-01_grid_2deg.parquet")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.75), layout="constrained")
    sel, cut = footprint(g5, "mean_flux", 90, "enough_samples_5deg")
    lat, lon = centroid(sel, "mean_flux", 5)
    x, y, a = grid_array(g5[g5.enough_samples_5deg], "mean_flux", 5)
    both = np.r_[g5.loc[g5.enough_samples_5deg, "mean_flux"], g2.loc[g2.enough_samples_2deg, "mean_flux"]]
    both = both[both > 0]
    norm = LogNorm(both.min(), both.max())  # shared by (a) and (c); zero would be blank (none occur)
    ax = axes[0]
    m = ax.pcolormesh(x, y, np.ma.masked_invalid(np.where(a > 0, a, np.nan)), cmap=SEQ, norm=norm, zorder=1)
    coast(ax)
    outline(ax, sel, 5, ORANGE, 1.4)
    ax.plot(lon, lat, marker="X", ms=8, color=INK, mec="white", mew=1.0, zorder=6)
    pk = g5[g5.enough_samples_5deg].sort_values("mean_flux").iloc[-1]
    ax.add_patch(Rectangle((pk.lon_bin_center - 2.5, pk.lat_bin_center - 2.5), 5, 5, fc="none", ec=INK, lw=1.2,
                           ls=(0, (2, 1)), zorder=6))
    panel_letter(ax, "a  5° mean p1 (principal)")
    cb = fig.colorbar(m, ax=ax, location="bottom", shrink=0.9, pad=0.02)
    cb.set_label("mean p1 differential flux, #/(cm² s sr MeV), log scale")
    ax.text(-98, 16, f"orange: top 10% ({len(sel)} cells, ≥{cut:.2f})\n✕ area-weighted flux centroid\ndashed square: peak cell",
            fontsize=6.2, va="top", color=INK, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))

    ax = axes[1]
    x, y, c = grid_array(g5, "sample_count", 5)
    m = ax.pcolormesh(x, y, np.ma.masked_invalid(c), cmap="Greys", vmin=0, zorder=1)
    coast(ax)
    panel_letter(ax, "b  samples per 5° cell")
    cb = fig.colorbar(m, ax=ax, location="bottom", shrink=0.9, pad=0.02)
    cb.set_label("valid samples (eligibility: ≥30)")
    ax.text(-98, 16, f"{int(g5.enough_samples_5deg.sum())}/432 cells eligible\nmin {int(g5.sample_count.min())} samples",
            fontsize=6.2, va="top", bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))

    ax = axes[2]
    elig = g2[g2.enough_samples_2deg]
    x, y, a2 = grid_array(elig, "mean_flux", 2)
    ax.pcolormesh(x, y, np.ma.masked_invalid(np.where(a2 > 0, a2, np.nan)), cmap=SEQ, norm=norm, zorder=1)
    bad = g2[~g2.enough_samples_2deg]
    observed = set(zip(g2.lat_bin_center, g2.lon_bin_center))
    allc = [(la, lo) for la in np.arange(-69, 20, 2) for lo in np.arange(-99, 20, 2)]
    missing = [c_ for c_ in allc if c_ not in observed]
    for la, lo in list(zip(bad.lat_bin_center, bad.lon_bin_center)):
        ax.add_patch(Rectangle((lo - 1, la - 1), 2, 2, fc="none", ec=RED, lw=0.9, hatch="////", zorder=4))
    for la, lo in missing:
        ax.add_patch(Rectangle((lo - 1, la - 1), 2, 2, fc=INK, ec=INK, lw=0.5, zorder=4))
    coast(ax)
    sel2, _ = footprint(g2, "mean_flux", 90, "enough_samples_2deg")
    outline(ax, sel2, 2, ORANGE, 1.1)
    la2, lo2 = centroid(sel2, "mean_flux", 2)
    ax.plot(lo2, la2, marker="X", ms=8, color=INK, mec="white", mew=1.0, zorder=6)
    panel_letter(ax, "c  2° mean p1, coverage")
    ax.text(-98, 16, f"hatched red: observed, <30 samples ({len(bad)})\nblack: no valid observation ({len(missing)})",
            fontsize=6.2, va="top", bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=SEQ), ax=ax, location="bottom", shrink=0.9, pad=0.02
                 ).set_label("same colour scale as (a)")
    save(fig, "fig1_reference")


# ------------------------------------------------------------------------------------ figure 2
def fig2():
    b = pd.read_parquet(T / "cp4b_threshold_sensitivity.parquet")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), layout="constrained", width_ratios=[1.15, 1])
    ax = axes[0]
    style = {(5, "mean_flux"): (BLUE, "-", "o"), (5, "median_flux"): (BLUE, "--", "s"),
             (2, "mean_flux"): (ORANGE, "-", "o"), (2, "median_flux"): (ORANGE, "--", "s")}
    for (g, stat), (col, ls, mk) in style.items():
        s = b[(b.grid_deg == g) & (b.statistic_used == stat)].sort_values("percentile_cutoff")
        ax.plot(s.centroid_lon_flux_weighted, s.centroid_lat_flux_weighted, ls=ls, marker=mk, ms=4.5, color=col,
                mfc="white" if ls == "--" else col, label=f"{g}° {stat.split('_')[0]}")
        if (g, stat) == (5, "mean_flux"):
            for r in s.itertuples():
                ax.annotate(r.threshold_label.replace("top", "top ") + "%", (r.centroid_lon_flux_weighted,
                            r.centroid_lat_flux_weighted), xytext=(6, -2), textcoords="offset points", fontsize=6.3,
                            color=INK2)
    ax.set_xlabel("centroid longitude (°)")
    ax.set_ylabel("centroid latitude (°)")
    ax.grid(True)
    ax.legend(loc="upper left", title="grid, cell statistic", title_fontsize=6.5)
    panel_letter(ax, "a  area-weighted flux centroid, top 20% → top 1%")
    ax.set_aspect(1.0, adjustable="datalim")

    ax = axes[1]
    frac = np.array([0.20, 0.10, 0.05, 0.02, 0.01])
    for (g, stat), (col, ls, mk) in style.items():
        s = b[(b.grid_deg == g) & (b.statistic_used == stat)].sort_values("percentile_cutoff")
        total = s.selected_area_km2 / s.selected_area_fraction_of_covered_region
        ax.plot(frac, s.selected_area_km2 / 1e6, ls="none", marker=mk, ms=5, color=col,
                mfc="white" if ls == "--" else col, label=f"{g}° {stat.split('_')[0]}")
    tot5 = float((b[b.grid_deg == 5].selected_area_km2 / b[b.grid_deg == 5].selected_area_fraction_of_covered_region).iloc[0])
    xs = np.array([0.008, 0.25])
    ax.plot(xs, xs * tot5 / 1e6, color=MUTED, lw=1.0, ls=":", label="prescribed: fraction × eligible area")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(frac, ["20%", "10%", "5%", "2%", "1%"])
    ax.minorticks_off()
    ax.invert_xaxis()
    ax.set_xlabel("nominal selected fraction of eligible cells")
    ax.set_ylabel("selected area (10⁶ km²)")
    ax.grid(True)
    ax.legend(loc="lower left", fontsize=6.3)
    panel_letter(ax, "b  selected area follows the percentile rule")
    save(fig, "fig2_threshold")


# ------------------------------------------------------------------------------------ figure 3
def fig3():
    q = pd.read_csv(CA / "paired_quantiles.csv")
    m = pd.read_csv(CA / "morphology_pairs.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.9), layout="constrained", width_ratios=[1.1, 1.1, 1])
    pairs = [("mep_omni_flux_p1", "mep_omni_flux_p2", BLUE, "p2 − p1"),
             ("mep_omni_flux_p1", "mep_omni_flux_p3", ORANGE, "p3 − p1"),
             ("mep_omni_flux_p2", "mep_omni_flux_p3", AQUA, "p3 − p2")]
    for ax, metric, lab in ((axes[0], "delta_lat", "Δ latitude (°)"), (axes[1], "delta_lon", "Δ longitude (°)")):
        for k, (a, b_, col, name) in enumerate(pairs):
            obs = m[(m.grid_deg == 5) & (m.statistic == "mean_flux") & (m.channel_a == a) & (m.channel_b == b_)
                    & (m["mode"] == "original_percentile")][metric].iloc[0]
            for j, L in enumerate((1, 3, 7)):
                r = q[(q.block_length == L) & (q.channel_a == a) & (q.channel_b == b_) & (q.metric == metric)].iloc[0]
                xpos = k + (j - 1) * 0.22
                ax.plot([xpos, xpos], [r.q025, r.q975], color=col, lw=2.0, solid_capstyle="round")
                ax.plot(xpos, r.q50, marker="o", ms=4, color=col, mec="white", mew=0.8)
            ax.plot([k - 0.35, k + 0.35], [obs, obs], color=INK, lw=1.1)
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_xticks(range(3), [p[3] for p in pairs])
        ax.set_ylabel(lab)
        ax.grid(True, axis="y")
    panel_letter(axes[0], "a  Δ latitude, 5° mean top 10%")
    panel_letter(axes[1], "b  Δ longitude, 5° mean top 10%")
    ax = axes[2]
    combos = [(5, "mean_flux"), (5, "median_flux"), (2, "mean_flux"), (2, "median_flux")]
    for k, (a, b_, col, name) in enumerate(pairs):
        for j, (g, st) in enumerate(combos):
            sub = m[(m.grid_deg == g) & (m.statistic == st) & (m.channel_a == a) & (m.channel_b == b_)].set_index("mode")
            y = k + (j - 1.5) * 0.17
            p_, c_ = sub.loc["original_percentile", "distance_km"], sub.loc["common_continuous", "distance_km"]
            ax.plot([p_, c_], [y, y], color=GRID, lw=1.4, zorder=1)
            ax.plot(p_, y, marker="o", ms=4.5, color=col, zorder=2)
            ax.plot(c_, y, marker="s", ms=4.5, mfc="white", mec=col, mew=1.2, zorder=2)
    ax.set_yticks(range(3), ["p1/p2", "p1/p3", "p2/p3"])
    ax.invert_yaxis()
    ax.set_xlabel("centroid distance (km)")
    ax.grid(True, axis="x")
    ax.plot([], [], marker="o", ls="none", color=INK2, label="top-10% footprint")
    ax.plot([], [], marker="s", ls="none", mfc="white", mec=INK2, label="whole-field normalized")
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.2), fontsize=6, ncol=1)
    panel_letter(ax, "c  distance by summary")
    save(fig, "fig3_channel")


# ------------------------------------------------------------------------------------ figure 4
WIN = [("day_2024-01-01", "1 d"), ("days_2024-01-01_to_03", "3 d"), ("days_2024-01-01_to_07", "7 d\n(=wk1)"),
       ("days_2024-01-01_to_14", "14 d"), ("week2", "wk 2"), ("week3", "wk 3"), ("week4", "wk 4")]


def fig4():
    ts = pd.read_parquet(T / "cp4d_temporal_support.parquet")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8), layout="constrained")
    x = np.arange(len(WIN))
    for g, col in ((5, BLUE), (2, ORANGE)):
        s = ts[(ts.grid_deg == g) & (ts.statistic_used == "mean_flux") & (ts.threshold_label == "top10")].set_index("window_label")
        s = s.loc[[w for w, _ in WIN]]
        axes[0].plot(x, s.window_coverage_passed_area_fraction, marker="o", ms=4, color=col, label=f"{g}° eligible")
        axes[0].plot(x, s.window_valid_observed_area_fraction, marker="o", ms=3.5, ls=":", mfc="white", color=col,
                     label=f"{g}° any valid obs.")
        axes[1].plot(x, s.area_jaccard_original, marker="o", ms=4, color=col, label=f"{g}° end-to-end")
        axes[1].plot(x, s.area_jaccard_common, marker="s", ms=4, ls="--", mfc="white", color=col,
                     label=f"{g}° shared support")
        axes[2].plot(x, s.centroid_distance_km_original, marker="o", ms=4, color=col, label=f"{g}° end-to-end")
        axes[2].plot(x, s.centroid_distance_km_common, marker="s", ms=4, ls="--", mfc="white", color=col,
                     label=f"{g}° shared support")
    for ax in axes:
        ax.set_xticks(x, [l for _, l in WIN], fontsize=6.3)
        ax.axvline(3.5, color=GRID, lw=1.0)
        ax.grid(True, axis="y")
    axes[0].set_ylabel("fraction of regional area")
    axes[0].set_ylim(0, 1.05)
    axes[0].legend(loc="lower right", fontsize=5.9, frameon=True, facecolor="white", edgecolor="none", framealpha=0.9)
    panel_letter(axes[0], "a  window coverage")
    axes[1].set_ylabel("area-weighted Jaccard vs January")
    axes[1].set_ylim(0, 1.05)
    axes[1].legend(loc="lower right", fontsize=5.9, frameon=True, facecolor="white", edgecolor="none", framealpha=0.9)
    panel_letter(axes[1], "b  top-10% footprint agreement")
    axes[2].set_ylabel("centroid distance to January (km)")
    axes[2].legend(loc="upper right", fontsize=5.9, frameon=True, facecolor="white", edgecolor="none", framealpha=0.9)
    panel_letter(axes[2], "c  centroid distance")
    save(fig, "fig4_temporal")


# ------------------------------------------------------------------------------------ figure 5
SATS = [("noaa15", "NOAA-15"), ("noaa18", "NOAA-18"), ("noaa19", "NOAA-19"), ("metop01", "MetOp-01"),
        ("metop03", "MetOp-03")]


def fig5():
    sens = pd.read_csv(QS / "sensitivity.csv")
    pw = pd.read_csv(QS / "pairwise.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), layout="constrained", width_ratios=[1.05, 1])
    ax = axes[0]
    p = sens[(sens.grid_deg == 5) & (sens.statistic_used == "mean_flux") & (sens.threshold_label == "top10")]
    offsets = {"noaa15": (6, -11), "noaa18": (-16, 8), "noaa19": (6, 5), "metop01": (-30, -13), "metop03": (7, -3)}
    for sat, name in SATS:
        r = p[(p.scenario == "qc_primary") & (p.satellite == sat)].iloc[0]
        ax.plot(r.centroid_lon_flux_weighted, r.centroid_lat_flux_weighted, marker="o", ms=6, color=BLUE,
                mec="white", mew=0.8, zorder=3)
        ax.annotate(name, (r.centroid_lon_flux_weighted, r.centroid_lat_flux_weighted), xytext=offsets[sat],
                    textcoords="offset points", fontsize=6.5, color=INK)
    a = p[(p.scenario == "qc_primary") & (p.satellite == "noaa15")].iloc[0]
    o = p[(p.scenario == "unfiltered") & (p.satellite == "noaa15")].iloc[0]
    ax.annotate("", xy=(o.centroid_lon_flux_weighted, o.centroid_lat_flux_weighted),
                xytext=(a.centroid_lon_flux_weighted, a.centroid_lat_flux_weighted),
                arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.4))
    ax.plot(o.centroid_lon_flux_weighted, o.centroid_lat_flux_weighted, marker="o", ms=6, mfc="white", mec=ORANGE,
            mew=1.4, zorder=4)
    ax.annotate("NOAA-15 unfiltered\n(sensitivity)", (o.centroid_lon_flux_weighted, o.centroid_lat_flux_weighted),
                xytext=(-6, 9), textcoords="offset points", fontsize=6.2, color=ORANGE, ha="right")
    ax.set_xlabel("centroid longitude (°)")
    ax.set_ylabel("centroid latitude (°)")
    ax.set_aspect(1.0, adjustable="datalim")
    ax.grid(True)
    panel_letter(ax, "a  principal centroids, 5° mean, top 10%")

    ax = axes[1]
    thr = ["top20", "top10", "top5", "top2", "top1"]
    for scen, stat, col, ls, mk, lab in (("qc_primary", "mean_flux", BLUE, "-", "o", "mean, QC-1 (primary)"),
                                         ("unfiltered", "mean_flux", ORANGE, "--", "o", "mean, unfiltered"),
                                         ("qc_primary", "median_flux", AQUA, "-", "s", "median, QC-1 (primary)")):
        y = [pw[(pw.scenario == scen) & (pw.grid_deg == 5) & (pw.statistic == stat) & (pw.threshold == t)].distance_km.max()
             for t in thr]
        ax.plot(range(5), y, ls=ls, marker=mk, ms=4.5, color=col, mfc="white" if ls == "--" else col, label=lab)
    ax.set_xticks(range(5), ["top 20%", "top 10%", "top 5%", "top 2%", "top 1%"])
    ax.set_yscale("log")
    ax.set_ylabel("max pairwise centroid distance (km, log)")
    ax.grid(True, axis="y")
    ax.legend(loc="upper left")
    panel_letter(ax, "b  five-satellite spread, 5° grid")
    save(fig, "fig5_satellite")


# ------------------------------------------------------------------------------------ tables
def r(x, n):
    return x.round(n)


def _short(df):
    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object or str(out[c].dtype).startswith("str"):
            out[c] = out[c].replace({"mean_flux": "mean", "median_flux": "median"})
    return out


def tables():
    TAB.mkdir(parents=True, exist_ok=True)
    # every supplementary CSV gets short statistic labels; the original writer is restored at the end
    _to_csv = pd.DataFrame.to_csv
    pd.DataFrame.to_csv = lambda self, *a, **k: _to_csv(_short(self), *a, **k)
    b = pd.read_parquet(T / "cp4b_threshold_sensitivity.parquet")
    t = b[["grid_deg", "statistic_used", "threshold_label", "flux_cutoff_value", "cells_available_after_coverage_mask",
           "selected_cell_count", "selected_area_km2", "centroid_lat_flux_weighted", "centroid_lon_flux_weighted",
           "peak_flux"]].copy()
    t["selected_area_km2"] = r(t.selected_area_km2 / 1e6, 3)
    for c in ("flux_cutoff_value", "centroid_lat_flux_weighted", "centroid_lon_flux_weighted", "peak_flux"):
        t[c] = r(t[c], 3)
    t.columns = ["grid", "statistic", "threshold", "cutoff", "eligible", "selected", "area_Mkm2", "lat", "lon", "peak"]
    t.to_csv(TAB / "S3_threshold.csv", index=False)

    c = pd.read_parquet(T / "cp4c_channel_threshold_sensitivity.parquet")
    t = c[["channel", "grid_deg", "statistic_used", "threshold_label", "flux_cutoff_value", "selected_cell_count",
           "selected_area_km2", "centroid_lat_flux_weighted", "centroid_lon_flux_weighted"]].copy()
    t["channel"] = t.channel.str[-2:]
    t["selected_area_km2"] = r(t.selected_area_km2 / 1e6, 3)
    for k in ("flux_cutoff_value", "centroid_lat_flux_weighted", "centroid_lon_flux_weighted"):
        t[k] = r(t[k], 3)
    t.columns = ["ch", "grid", "statistic", "threshold", "cutoff", "selected", "area_Mkm2", "lat", "lon"]
    t.to_csv(TAB / "S4_channel.csv", index=False)

    m = pd.read_csv(CA / "morphology_pairs.csv")
    m = m.assign(pair=m.channel_a.str[-2:] + "/" + m.channel_b.str[-2:])
    t = m[["grid_deg", "statistic", "pair", "mode", "delta_lat", "delta_lon", "distance_km", "continuous_overlap",
           "area_jaccard"]].copy()
    for k in ("delta_lat", "delta_lon", "distance_km", "continuous_overlap", "area_jaccard"):
        t[k] = r(t[k], 3)
    t.columns = ["grid", "statistic", "pair", "mode", "dlat", "dlon", "km", "overlap", "jaccard"]
    t.to_csv(TAB / "S4b_channel_morphology.csv", index=False)

    q = pd.read_csv(CA / "paired_quantiles.csv")
    q = q.assign(pair=q.channel_b.str[-2:] + "−" + q.channel_a.str[-2:])
    t = q[["block_length", "pair", "metric", "defined", "q025", "q50", "q975"]].copy()
    for k in ("q025", "q50", "q975"):
        t[k] = r(t[k], 3)
    t.to_csv(TAB / "S5_paired_quantiles.csv", index=False)

    ts = pd.read_parquet(T / "cp4d_temporal_support.parquet")
    t = ts[["window_label", "grid_deg", "statistic_used", "threshold_label", "window_coverage_passed_cells",
            "window_coverage_passed_area_fraction", "area_jaccard_original", "monthly_footprint_observability",
            "common_support_cells", "area_jaccard_common", "centroid_distance_km_original",
            "centroid_distance_km_common", "selected_area_ratio_original", "selected_area_ratio_common"]].copy()
    t = t[t.window_label != "month_2024-01"]
    short = dict(WIN)
    short.update({"week1": "wk 1*"})
    t["window_label"] = t.window_label.map(lambda s: short.get(s, s).replace("\n(=wk1)", ""))
    for k in t.columns[5:]:
        if k != "common_support_cells":
            t[k] = r(t[k], 3)
    t.columns = ["window", "grid", "stat", "thr", "C_W", "C_W area", "J_end", "O_M", "S", "J_sh",
                 "D_end km", "D_sh km", "R_end", "R_sh"]
    t.to_csv(TAB / "S6_temporal_support.csv", index=False)
    tw = pd.read_parquet(T / "cp4d_time_window_threshold_sensitivity.parquet")
    t = tw[["window_label", "grid_deg", "day_count", "coverage_threshold_used", "nominal_region_cells",
            "cells_with_observation", "cells_available_after_coverage_mask", "coverage_pass_fraction"]].drop_duplicates()
    t["coverage_pass_fraction"] = r(t.coverage_pass_fraction, 3)
    t.columns = ["window", "grid", "days", "min_samples", "nominal", "observed", "eligible", "eligible_frac"]
    t.to_csv(TAB / "S6b_window_coverage.csv", index=False)

    SCN = {"qc_primary": "QC-1 primary", "unfiltered": "unfiltered"}
    s = pd.read_csv(QS / "sensitivity.csv")
    t = s[["scenario", "satellite", "grid_deg", "statistic_used", "threshold_label", "selected_cell_count",
           "selected_area_km2", "centroid_lat_flux_weighted", "centroid_lon_flux_weighted"]].copy()
    t["selected_area_km2"] = r(t.selected_area_km2 / 1e6, 3)
    for k in ("centroid_lat_flux_weighted", "centroid_lon_flux_weighted"):
        t[k] = r(t[k], 3)
    t["scenario"] = t.scenario.map(SCN)
    t.columns = ["scenario", "satellite", "grid", "statistic", "threshold", "selected", "area_Mkm2", "lat", "lon"]
    t.to_csv(TAB / "S7_satellite.csv", index=False)
    pw = pd.read_csv(QS / "pairwise.csv")
    mx = pw.loc[pw.groupby(["scenario", "grid_deg", "statistic", "threshold"], sort=False).distance_km.idxmax()].copy()
    mx["distance_km"] = r(mx.distance_km, 2)
    mx["scenario"] = mx.scenario.map(SCN)
    mx.to_csv(TAB / "S7b_max_pairwise.csv", index=False)
    ac = pd.read_csv(QS / "event_cell.csv")
    t = ac[["scenario", "grid_deg", "statistic", "threshold", "lat", "lon", "count", "mean", "median",
            "descending_rank", "selected", "cell_centroid_weight"]].copy()
    t.columns = ["scenario", "grid", "stat", "thr", "lat", "lon", "n", "cell mean", "cell median", "rank", "selected",
                 "centroid weight"]
    for k in ("cell mean", "cell median", "centroid weight"):
        t[k] = r(t[k], 4)
    t["scenario"] = t.scenario.map(SCN)
    t.to_csv(TAB / "S7c_event_cell.csv", index=False)

    ctx = pd.read_csv(QS / "event_context.csv")
    nb = ctx[ctx.offset.abs() <= 10]
    t = nb[["native_index", "utc", "lat", "lon180", "mep_IFC_on", "mep_omni_flux_flag_fit", "mep_omni_flux_p1",
            "mep_omni_flux_p2", "mep_omni_flux_p3", "mep_omni_gamma_p1", "mep_pro_tel0_flux_p6",
            "mep_pro_tel90_flux_p6", "gap_s"]].copy()
    t["utc"] = t.utc.str[11:23]
    for k in ("lat", "lon180"):
        t[k] = r(t[k], 3)
    for k in ("mep_omni_flux_p1", "mep_omni_flux_p2", "mep_omni_flux_p3", "mep_pro_tel0_flux_p6",
              "mep_pro_tel90_flux_p6"):
        t[k] = t[k].map(lambda x: f"{x:.4g}")
    t["gap_s"] = r(t.gap_s, 3)
    t.columns = ["index", "UTC", "lat", "lon", "IFC", "fit", "p1", "p2", "p3", "γ1", "P6 0°", "P6 90°", "gap_s"]
    t.to_csv(TAB / "S7a_event_neighbours.csv", index=False)
    rc = pd.read_csv(QS / "event_raw_counts.csv")
    t = rc[rc.offset.abs() <= 5][["native_index", "utc", "mep_omni_cps_p6", "mep_omni_cps_p7", "mep_omni_cps_p8",
                                   "mep_omni_cps_p9", "mep_pro_tel0_cps_p6", "mep_pro_tel90_cps_p6", "mep_omni_biase_V",
                                   "proc_fit", "proc_p1"]].copy()
    for k in ("mep_omni_cps_p8", "mep_omni_cps_p9"):
        t[k] = t[k].map(lambda x: "–" if x < 0 else f"{x:.6g}")
    t["proc_p1"] = t.proc_p1.map(lambda x: f"{x:.4g}")
    t.columns = ["index", "UTC", ">16 MeV", ">35 MeV", ">70 MeV", ">140 MeV", "P6 0°", "P6 90°", "bias V", "fit", "p1"]
    t.to_csv(TAB / "S7e_event_counts.csv", index=False)
    po = pd.read_csv(QS / "population.csv")
    t = po[["satellite", "channel", "records", "regular_evaluable", "regular_max", "isolated_fallback",
            "fallback_ratio_median", "fallback_ratio_max_kept", "isolated_fallback_flagged", "flagged_ratio_min"]].copy()
    t["channel"] = t.channel.str[-2:]
    for k in ("regular_max", "fallback_ratio_median", "fallback_ratio_max_kept", "flagged_ratio_min"):
        t[k] = r(t[k], 2)
    t.columns = ["satellite", "ch", "records", "regular n", "regular max", "fallback n", "fallback median",
                 "fallback max kept", "excluded", "excluded ratio"]
    t.to_csv(TAB / "S7f_qc_population.csv", index=False)
    pt = pd.read_csv(QS / "perturbation.csv")
    t = pt[["variant", "excluded_global", "excluded_in_region", "same_set_as_adopted"]].copy()
    t.columns = ["variant", "excluded (all)", "excluded (region)", "same set"]
    t.to_csv(TAB / "S7g_qc_perturbation.csv", index=False)
    dd = pd.read_csv(CA / "dependence_diagnostics.csv")
    t = dd[dd.variable == "regional_mean"][["channel", "lag_days", "lag_correlation", "first_half_mean", "second_half_mean"]].copy()
    t["channel"] = t.channel.str[-2:]
    for k in ("lag_correlation", "first_half_mean", "second_half_mean"):
        t[k] = r(t[k], 3)
    t.to_csv(TAB / "S5b_dependence.csv", index=False)
    cen = pd.read_csv(Path("outputs/audit_replay/census.csv"))
    t = cen[["satellite", "channel", "source_records", "negative", "zero", "evaluable_fraction", "candidates"]].copy()
    t["channel"] = t.channel.str[-2:]
    t["evaluable_fraction"] = r(t.evaluable_fraction, 3)
    t.to_csv(TAB / "S7d_triage_census.csv", index=False)
    q5 = pd.read_parquet(T / "cp5c_multisatellite_magnetic_generality_summary.parquet")
    t = q5[["satellite", "regional_rows_before_ifc", "ifc_on_dropped", "ifc_minus1_retained", "invalid_channel_dropped",
            "qc_excluded_dropped", "regional_rows_after_quality", "selected_sample_count", "btot_fraction_below_regional_q25",
            "btot_regional_fraction_to_capture_90pct", "btot_separation_metric", "l_igrf_rows_invalid"]].copy()
    for k in ("btot_fraction_below_regional_q25", "btot_regional_fraction_to_capture_90pct", "btot_separation_metric"):
        t[k] = r(t[k], 4)
    t.to_csv(TAB / "S2_S8_accounting_magnetic.csv", index=False)
    pd.DataFrame.to_csv = _to_csv


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    tables()
    print("figures:", sorted(p.name for p in FIG.glob("*.pdf")))
