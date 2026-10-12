"""QC-1: isolated simple-fit-fallback discontinuity in the SEM-2 OMNI proton fluxes.

The OMNI algorithm (NOAA ATBD, Machol 2012, Table 5 and Section 3.4 step 6) falls back from its
regular four-region power-law fit (fit flag 0) to a single power law built from the two lowest
channels (fit 2) or, failing that, from one anchor with the default slope -2.9 (fit 1). The
fallback is a documented fit mode, not an invalidity flag, and it is common at low count rates.

QC-1 excludes the OMNI outputs of one record only when all of the following hold:

1. the record's fit is a fallback (1 or 2);
2. its ``neighbours_per_side`` preceding and following native records exist, are contiguous in time
   (each step positive and at most ``max_step_seconds``) and all received the regular fit 0;
3. for at least one channel, every neighbour value is finite and positive and the record's value
   exceeds ``ratio`` times the median of the preceding neighbours *and* ``ratio`` times the median of
   the following neighbours.

Condition 2 restricts the rule to stretches where the counts sustained the regular fit, so a
two-sided jump of this size is not a counting fluctuation; ``ratio`` sits far above the largest
departure the documented fallback shows elsewhere in the January 2024 data (about 20x). The three
channel values of a flagged record come from one fit and are excluded together (set missing, never
clipped or replaced). Records that cannot be evaluated are kept. The rule was adopted after the
NOAA-15 2024-01-19 09:14:30 UTC record was found; it is a post-hoc rule, applied to every record.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

QC1 = {
    "id": "QC-1",
    "name": "omni_isolated_fallback_discontinuity",
    "version": "1.0",
    "neighbours_per_side": 10,
    "max_step_seconds": 6.0,
    "ratio": 100.0,
    "fallback_fits": [1, 2],
    "regular_fit": 0,
    "channels": ["mep_omni_flux_p1", "mep_omni_flux_p2", "mep_omni_flux_p3"],
    "exclusion_unit": "all OMNI channel values of the flagged record",
    "adopted": "post hoc, 2026-10-02",
}


@dataclass(frozen=True)
class QCResult:
    excluded: np.ndarray            # record flagged by the rule
    evaluable: np.ndarray           # fallback record with a full contiguous regular-fit neighbourhood
    ratio_left: dict                # channel -> value / median(preceding neighbours), NaN if not evaluable
    ratio_right: dict               # channel -> value / median(following neighbours)
    triggered: dict                 # channel -> both ratios above the threshold


def segments(time_ms, max_step_seconds: float) -> np.ndarray:
    """Segment id per record; a new segment starts at any non-positive, non-finite or long step."""
    t = np.asarray(time_ms, dtype="float64") / 1000.0
    step = np.diff(t)
    brk = ~np.isfinite(step) | (step <= 0) | (step > max_step_seconds)
    return np.r_[0, np.cumsum(brk)]


def isolated_fallback_discontinuity(
    time_ms,
    fit,
    channels: Mapping[str, np.ndarray],
    *,
    k: int = QC1["neighbours_per_side"],
    max_step_seconds: float = QC1["max_step_seconds"],
    ratio: float = QC1["ratio"],
    min_regular_fraction: float = 1.0,
    require_fallback: bool = True,
    trigger: str = "any",
) -> QCResult:
    """Apply QC-1 to one native-ordered record sequence (one daily file).

    ``channels`` maps names to values already passed through the validity rule (negative or
    fit = -1 set to NaN). The keyword arguments other than the defaults exist only for the
    parameter-perturbation study; production uses the defaults recorded in :data:`QC1`.
    """
    fit = np.asarray(fit)
    n = len(fit)
    w = 2 * k + 1
    excluded = np.zeros(n, bool)
    evaluable = np.zeros(n, bool)
    ratio_left = {c: np.full(n, np.nan) for c in channels}
    ratio_right = {c: np.full(n, np.nan) for c in channels}
    triggered = {c: np.zeros(n, bool) for c in channels}
    if n < w:
        return QCResult(excluded, evaluable, ratio_left, ratio_right, triggered)
    seg = sliding_window_view(segments(time_ms, max_step_seconds), w)
    contiguous = seg[:, 0] == seg[:, -1]
    finite_fit = np.where(np.isfinite(fit.astype("float64")), fit, -9).astype(int)
    fw = sliding_window_view(finite_fit, w)
    neighbours = np.concatenate([fw[:, :k], fw[:, k + 1:]], axis=1)
    regular = (neighbours == QC1["regular_fit"]).mean(axis=1) >= min_regular_fraction
    centre_ok = np.isin(fw[:, k], QC1["fallback_fits"]) if require_fallback else np.ones(len(fw), bool)
    ok = contiguous & regular & centre_ok
    evaluable[k:n - k] = ok
    hits = []
    for name, values in channels.items():
        vw = sliding_window_view(np.asarray(values, dtype="float64"), w)
        left, right, centre = vw[:, :k], vw[:, k + 1:], vw[:, k]
        valid = (np.all(np.isfinite(left) & (left > 0), axis=1) & np.all(np.isfinite(right) & (right > 0), axis=1)
                 & np.isfinite(centre) & ok)
        with np.errstate(invalid="ignore", divide="ignore"):
            ml, mr = np.median(left, axis=1), np.median(right, axis=1)
            hit = valid & (centre > ratio * ml) & (centre > ratio * mr)
            ratio_left[name][k:n - k] = np.where(valid, centre / ml, np.nan)
            ratio_right[name][k:n - k] = np.where(valid, centre / mr, np.nan)
        triggered[name][k:n - k] = hit
        hits.append(hit)
    if hits:
        combined = np.all(hits, axis=0) if trigger == "all" else np.any(hits, axis=0)
        excluded[k:n - k] = combined
    return QCResult(excluded, evaluable, ratio_left, ratio_right, triggered)
