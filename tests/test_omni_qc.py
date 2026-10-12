"""QC-1: isolated simple-fit-fallback discontinuity in the SEM-2 OMNI fluxes.

Synthetic cases pin the rule's contract; real-file cases pin its behaviour on the analysed data.
"""
import hashlib
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from saa import quality
from saa.load_poes import extract_channels_dataframe, omni_qc_ledger, open_poes_netcdf

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
EVENT_FILE = RAW / "poes_n15_20240119_proc.nc"
EVENT_SHA = "1209804e1f2e59b49f0e55f0d5be6246e89fef9df3c8641f76d6dbf679bb0594"
P = ("mep_omni_flux_p1", "mep_omni_flux_p2", "mep_omni_flux_p3")


def sequence(n=41, centre=20, value=5000.0, centre_fit=1, base=10.0, fits=None, times=None):
    """Regular-fit (fit 0) background of `base` with one centre record; p2/p3 follow a -2.9 power law."""
    t = np.arange(n, dtype="int64") * 2000 + 1705655600000 if times is None else np.asarray(times, dtype="int64")
    fit = np.zeros(n, dtype=int) if fits is None else np.asarray(fits, dtype=int)
    p1 = np.full(n, base, dtype=float)
    if centre is not None:
        p1[centre] = value
        fit[centre] = centre_fit
    chans = {P[0]: p1, P[1]: p1 / 2 ** 2.9, P[2]: p1 / 4 ** 2.9}
    return t, fit, chans


def dataset(t, fit, chans):
    data = {"time": t, "lat": np.full(len(t), -12.5), "lon": np.full(len(t), 330.7), "mep_omni_flux_flag_fit": fit,
            "mep_IFC_on": np.full(len(t), -1)}
    data.update(chans)
    return xr.Dataset({k: (k, np.asarray(v)) for k, v in data.items()})


def run(t, fit, chans, **kw):
    return quality.isolated_fallback_discontinuity(t, fit, chans, **kw)


class RuleContract(unittest.TestCase):
    def test_sharp_isolated_fallback_spike_is_excluded_on_every_channel(self):
        r = run(*sequence())
        self.assertEqual(np.flatnonzero(r.excluded).tolist(), [20])
        self.assertTrue(all(r.triggered[c][20] for c in P))
        d = extract_channels_dataframe(dataset(*sequence()), "poes_n15_20240119_proc.nc", channels=list(P))
        self.assertTrue(d.loc[20, list(P)].isna().all())
        self.assertTrue(np.isfinite(d.drop(index=20)[list(P)]).all().all())

    def test_typical_fallback_departure_is_kept(self):
        # A documented one-point fit sits a few times above its regular-fit neighbours (default-slope bias).
        for value in (40.0, 199.0, 1000.0):
            self.assertFalse(run(*sequence(value=value)).excluded.any(), value)

    def test_threshold_is_strict(self):
        for value, expected in ((1000.0, False), (1000.0001, True)):     # 100x the median is not enough
            t, fit, chans = sequence(value=value)
            self.assertEqual(bool(run(t, fit, {P[0]: chans[P[0]]}).excluded[20]), expected, value)

    def test_regular_fit_record_is_never_excluded_by_magnitude(self):
        self.assertFalse(run(*sequence(centre_fit=0)).excluded.any())

    def test_fit_one_is_not_invalid_in_fallback_dominated_sequences(self):
        t, fit, chans = sequence(fits=np.ones(41))
        self.assertFalse(run(t, fit, chans).excluded.any())
        t, fit, chans = sequence(fits=np.full(41, 2), centre_fit=1)
        self.assertFalse(run(t, fit, chans).excluded.any())

    def test_one_non_regular_neighbour_makes_the_record_unevaluable(self):
        fits = np.zeros(41, dtype=int)
        fits[13] = 2
        t, fit, chans = sequence(fits=fits)
        r = run(t, fit, chans)
        self.assertFalse(r.evaluable[20])
        self.assertFalse(r.excluded.any())

    def test_high_but_gradual_structures_are_kept(self):
        n = 61
        t = np.arange(n, dtype="int64") * 2000
        # an intense, smooth pass: x1.5 per record up to 1e4 and back down; fallback fits sprinkled through it
        p1 = 1e4 * 1.5 ** -np.abs(np.arange(n) - 30.0)
        for fallback_at in (30, 25, 36):
            fit = np.zeros(n, dtype=int)
            fit[fallback_at] = 1
            r = run(t, fit, {P[0]: p1, P[1]: p1 / 7.46, P[2]: p1 / 55.7})
            self.assertTrue(r.evaluable[fallback_at])
            self.assertFalse(r.excluded.any(), fallback_at)
        # a monotonic ramp never exceeds its upstream side
        ramp = 10 * 3.0 ** np.arange(n)
        fit = np.zeros(n, dtype=int)
        fit[30] = 1
        self.assertFalse(run(t, fit, {P[0]: ramp}).excluded.any())

    def test_gaps_missing_zero_and_edge_neighbourhoods_are_unevaluable(self):
        t, fit, chans = sequence()
        gap = t.copy()
        gap[25:] += 5000                                   # 7 s step > 3 cadences
        self.assertFalse(run(gap, fit, chans).excluded.any())
        for bad in (np.nan, 0.0, -1.0):
            c = {k: v.copy() for k, v in chans.items()}
            for v in c.values():
                v[12] = bad
            self.assertFalse(run(t, fit, c).excluded.any(), bad)
        edge = sequence(n=41, centre=5)
        self.assertFalse(run(*edge).excluded.any())
        short = sequence(n=15, centre=7)
        self.assertFalse(run(*short).excluded.any())

    def test_duplicate_or_backward_timestamps_break_the_neighbourhood(self):
        t, fit, chans = sequence()
        for k in (14, 27):
            d = t.copy()
            d[k] = d[k - 1]                                # duplicate timestamp
            self.assertFalse(run(d, fit, chans).excluded.any(), k)
            b = t.copy()
            b[k] = b[k - 1] - 2000                         # time goes backwards
            self.assertFalse(run(b, fit, chans).excluded.any(), k)

    def test_identity_is_positional_not_by_value(self):
        # The same numeric value inside a smooth high-flux stretch survives; only the isolated fallback goes.
        n = 101
        t = np.arange(n, dtype="int64") * 2000
        p1 = np.full(n, 10.0)
        fit = np.zeros(n, dtype=int)
        p1[20], fit[20] = 5000.0, 1
        p1[60:90] = 5000.0
        fit[75] = 1
        r = run(t, fit, {P[0]: p1})
        self.assertEqual(np.flatnonzero(r.excluded).tolist(), [20])
        self.assertTrue(np.isfinite(p1[75]))

    def test_deterministic_replay(self):
        a = run(*sequence())
        b = run(*sequence())
        np.testing.assert_array_equal(a.excluded, b.excluded)
        for c in P:
            np.testing.assert_array_equal(a.ratio_left[c], b.ratio_left[c])
            np.testing.assert_array_equal(a.ratio_right[c], b.ratio_right[c])

    def test_unfiltered_extraction_keeps_the_source_value(self):
        d = extract_channels_dataframe(dataset(*sequence()), "x.nc", channels=list(P), qc=False)
        self.assertEqual(d.loc[20, P[0]], 5000.0)

    def test_rule_metadata_matches_defaults(self):
        self.assertEqual(quality.QC1["neighbours_per_side"], 10)
        self.assertEqual(quality.QC1["ratio"], 100.0)
        self.assertEqual(quality.QC1["max_step_seconds"], 6.0)
        self.assertEqual(quality.QC1["fallback_fits"], [1, 2])


@unittest.skipUnless(EVENT_FILE.exists(), "raw NOAA files not present")
class RealFiles(unittest.TestCase):
    def test_noaa15_event_is_excluded_and_its_source_bytes_are_untouched(self):
        before = hashlib.sha256(EVENT_FILE.read_bytes()).hexdigest()
        self.assertEqual(before, EVENT_SHA)
        with open_poes_netcdf(str(EVENT_FILE)) as ds:
            qc = extract_channels_dataframe(ds, str(EVENT_FILE), channels=list(P))
            raw = extract_channels_dataframe(ds, str(EVENT_FILE), channels=list(P), qc=False)
            ledger = omni_qc_ledger(ds, str(EVENT_FILE), before)
        self.assertTrue(qc.loc[13867, list(P)].isna().all())
        self.assertAlmostEqual(raw.loc[13867, P[0]], 36016.3671875)
        self.assertEqual(ledger.native_index.tolist(), [13867])
        row = ledger.iloc[0]
        self.assertEqual((row.source_sha256, int(row.fit)), (EVENT_SHA, 1))
        self.assertIn("fallback fit 1", row.reason)
        self.assertGreater(row.p1_ratio_min, 1000)
        diff = (qc[list(P)].fillna(-1) != raw[list(P)].fillna(-1)).any(axis=1)
        self.assertEqual(np.flatnonzero(diff).tolist(), [13867])
        self.assertEqual(hashlib.sha256(EVENT_FILE.read_bytes()).hexdigest(), before)

    def test_magnetic_chain_counts_qc_separately_from_validity(self):
        from saa.magnetic_audit import load_region_with_magnetic
        region, counts, _ = load_region_with_magnetic("2024-01-19", "2024-01-19", "noaa15", raw_dir=str(RAW))
        self.assertEqual(counts["n_qc_excluded"], 1)
        self.assertNotIn("omni_qc_excluded", region.columns)
        self.assertFalse(((region.time == pd.Timestamp("2024-01-19T09:14:30.051Z"))).any())
        with open_poes_netcdf(str(EVENT_FILE)) as ds:
            d = extract_channels_dataframe(ds, str(EVENT_FILE), qc=False)
        d["lon180"] = (d.lon + 180) % 360 - 180
        inside = d[(d.lat >= -70) & (d.lat <= 20) & (d.lon180 >= -100) & (d.lon180 <= 20) & (d.mep_IFC_on != 1)]
        self.assertEqual(counts["n_invalid_channel_dropped"], int(inside[P[0]].isna().sum()))
        self.assertEqual(counts["n_after_flux_validity"], len(inside) - counts["n_invalid_channel_dropped"] - 1)

    def test_normal_isolated_fit_one_records_are_kept(self):
        # Real isolated one-point fits inside regular-fit stretches: NOAA-19 with zeroed directional
        # channels (p1 ~1.8x its neighbours) and the NOAA-15 record on the same day 2 h earlier.
        for name, index in (("poes_n19_20240125_proc.nc", 16503), ("poes_n15_20240119_proc.nc", 10992)):
            with open_poes_netcdf(str(RAW / name)) as ds:
                d = extract_channels_dataframe(ds, name, channels=list(P))
                fit = int(ds["mep_omni_flux_flag_fit"].values[index])
            self.assertEqual(fit, 1, name)
            self.assertTrue(np.isfinite(d.loc[index, P[0]]), name)


if __name__ == "__main__":
    unittest.main()
