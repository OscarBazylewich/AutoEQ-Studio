"""The EQ part's methods and the maths of its fits (eq\\engines.py, run as a run runs them, through eq\\pipeline.py):
a filter's own response against known values (a peak, a low and a high shelf), the website's AutoEQ (in V8), Best
fit on fixed bands, on a device's layout and with your own filters, the number of fits its progress says, the fits
counted and grown, split filters merged, the starting points, a failed fit stopping the others, a scored range
without curve points, the queue's errors, one V8 kept per thread, absurd curves, a shelf's Q and your own filters'
frequency range, and the pick and the ear error. Moved from eq_checks.py's module_checks (and grow_checks and
review2_maths_checks, which it ran); the known values added after the tests' verification.

The curves are the sample target and device (the sample_curves fixture: those files by name). Best fit's runs on a
device or with your own filters start a pool of worker processes, as the app's runs do (AUTOEQSTUDIO_MAX_WORKERS caps
it: 2 in the tests)."""
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from eq import engines, layouts, pipeline, settings
from helpers import qt
from helpers.checks import raises  # (eq_checks.py's raises, line 50: the message of a ValueError, or None)

# your own filters for Best fit to start from, the small run around them, and how they are kept (eq_checks.py lines
# 455-458 and 462)
MINE = "Filter 1: ON PK Fc 1000 Hz Gain -2 dB Q 1.5\n120 3 0.8"
SMALL = {"filter_counts": [2, 4], "gain_max": [6], "q_max": [3], "random_starts": 2, "seed_with_site": False,
         "fight_penalty": [0.01],
         "low_shelf": False, "high_shelf": False, "start_filters": MINE}
KEPT = [{"type": "PK", "enabled": True, "freq": 1000.0, "gain": -2.0, "q": 1.5},
        {"type": "PK", "enabled": True, "freq": 120.0, "gain": 3.0, "q": 0.8}]


def fit_settings():
    """Best fit's settings the fits are counted on: 2 filter counts x 2 boosts x 2 Q limits (eq_checks.py lines
    309-310)."""
    return dict(settings.with_auto({"best_fit": {"filter_counts": [4, 6], "gain_max": [6, 9], "q_max": [2, 3],
                                                 "fight_penalty": [0.01]}})["best_fit"], build="scratch")


# ---------------------------------------------------------------- a filter's own response, against known values
# (added 2026-10-22 after the tests' verification, V2: every other check compares filters with filters, so a mistake
# in the formula itself, engines.biquad, would show only by luck: every filter at half its gain failed one check of
# 311, about something else. Known values instead: a peaking filter gives exactly its gain at its own frequency, and a
# shelf its whole gain far on its side, half of it at its own frequency and nothing far on the other side.)
def one_filter(eq_cfg, ftype, at):
    """The app's own response (engines.eq_gain, at the app's sample rate) of one +6 dB filter at 1 kHz, as the app
    writes filters ("PK" with Q 1; the shelves "LSQ" and "HSQ" with AutoEq's Q 0.7), in dB at each frequency in `at`."""
    q = 1.0 if ftype == "PK" else 0.7
    got = engines.eq_gain(np.array(at, dtype=float), [{"type": ftype, "freq": 1000.0, "gain": 6.0, "q": q}],
                          eq_cfg["site"]["sample_rate"])
    return [round(float(g), 3) for g in got]


def near(got, want, within=0.05):
    return len(got) == len(want) and all(abs(g - w) <= within for g, w in zip(got, want))


def test_peak_filter_known_values(eq_cfg, check):
    got = one_filter(eq_cfg, "PK", [1000, 10])
    check("filters: a +6 dB peaking filter at 1 kHz (Q 1) gives +6.0 dB at 1 kHz and about 0 dB two decades below "
          "(10 Hz), at the app's sample rate", near(got, [6.0, 0.0]), got)


def test_low_shelf_known_values(eq_cfg, check):
    got = one_filter(eq_cfg, "LSQ", [10, 1000, 20000])
    check("filters: a +6 dB low shelf at 1 kHz (Q 0.7) gives about +6 dB far below it (10 Hz), +3 dB at 1 kHz and "
          "about 0 dB far above it (20 kHz)", near(got, [6.0, 3.0, 0.0]), got)


def test_high_shelf_known_values(eq_cfg, check):
    got = one_filter(eq_cfg, "HSQ", [10, 1000, 20000])
    check("filters: a +6 dB high shelf at 1 kHz (Q 0.7) gives about 0 dB far below it (10 Hz), +3 dB at 1 kHz and "
          "about +6 dB far above it (20 kHz)", near(got, [0.0, 3.0, 6.0]), got)


# ---------------------------------------------------------------- the methods on the sample curves
def test_site_single_lowers_the_error(sample_curves, eq_cfg, check):
    curves, mt, tt = sample_curves
    cfg = eq_cfg
    no_eq = engines.rms_error(curves["f"], curves["meas"], curves["target"], cfg["scoring"]["band_hz"])
    out = pipeline.run_mode("site_single", cfg, curves, mt, tt)
    # was eq_checks.py:231
    check("methods: site_single lowers the error", out["pick"]["rms"] < no_eq and out["pick"]["filters"], (out["pick"]["rms"], no_eq))


@pytest.mark.parametrize("lay", ["graphic_10", "spotify", "bands"])
def test_fixed_bands(lay, sample_curves, check):
    # Best fit's layouts (layouts.py): fixed bands (gains only, in the sliders' steps and range)
    curves, mt, tt = sample_curves
    cg = settings.with_auto({"mode": "best_fit", "best_fit": {"layout": lay, "bands": {
        "freqs": [100, 1000, 5000], "q": 1, "step": 0.5, "gain_min": -6, "gain_max": 6}}})
    fl = pipeline.run_mode("best_fit", cg, curves, mt, tt)["pick"]["filters"]
    want, q = layouts.bands(cg["best_fit"])
    # was eq_checks.py:239
    check(f"methods: Best fit, fixed bands ({lay}): its bands, only the gains, in 0.5 dB steps within ±6 dB",
          [f["freq"] for f in fl] == want and all(f["q"] == q and f["type"] == "PK" and -6 <= f["gain"] <= 6
                                                  and abs(f["gain"] * 2 - round(f["gain"] * 2)) < 1e-9 for f in fl), fl)


def test_device_layout_kept(sample_curves, check):
    # (a pool of worker processes)
    curves, mt, tt = sample_curves
    cd = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"pick": "lowest"}, "best_fit": {
        "layout": "app:moondrop_free_dsp", "filter_counts": [4, 12], "gain_max": [6, 9], "q_max": [8], "random_starts": 1,
        "seed_with_site": False, "low_shelf": True, "high_shelf": False, "start_filters": ""}})
    rs = pipeline.run_mode("best_fit", cd, curves, mt, tt)["results"]
    # was eq_checks.py:246
    check("methods: Best fit, a device layout keeps to it (Moondrop Free DSP: 9 peaking filters, -12..+3 dB, Q 8 of its 10, 40 Hz up)",
          all(len(r["filters"]) <= 9 and all(f["type"] == "PK" and -12 <= f["gain"] <= 3 and f["q"] <= 8 and f["freq"] >= 40
                                              for f in r["filters"]) for r in rs) and max(r["rows"] for r in rs) == 9,
          [(r["rows"], r["filters"]) for r in rs])


def test_progress_counts_the_fits(sample_curves, check):
    # the fits' count shown is the real one (your own filters' fit is one more); a pool of worker processes
    curves, mt, tt = sample_curves
    said = []
    cm = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "best_fit": {
        "filter_counts": [2, 3], "gain_max": [6], "q_max": [2], "random_starts": 1, "seed_with_site": False,
        "start_filters": "1000 2 1", "start_keep": False, "fight_penalty": [0.01]}})
    rs = pipeline.run_mode("best_fit", cm, curves, mt, tt, progress=lambda d, t, m="": said.append((t, m)))["results"]
    totals = {t for t, m in said if m.startswith(("Fits", "Starting"))}
    # was eq_checks.py:262
    check("progress: the number of fits said is the number made", totals == {len(rs)} and len(rs) == 3, (totals, len(rs)))


# ---------------------------------------------------------------- the fits counted
def test_fits_counted_with_your_filters(check):
    bfc = fit_settings()
    counts = (engines.fit_count(bfc), engines.fit_count(bfc, 3), engines.fit_count(dict(bfc, start_keep=False), 3),
              engines.fit_count(dict(bfc, start_add=False), 3))
    # was eq_checks.py:313
    check("fits: counted with your own filters (kept: one more; adjusted: one per limit; nothing added: yours only)",
          counts == (8, 9, 12, 1), counts)


def test_fits_counted_growing(check):
    bfc = fit_settings()
    bfg = dict(bfc, build="grow")
    grown = (engines.fit_count(bfg), engines.fit_count(dict(bfg, start_filters="1000 2 1"), 1),
             engines.grows(bfg), engines.grows(dict(bfg, start_filters="1000 2 1", start_keep=False)),
             engines.grows(dict(bfg, start_add=False)))
    both = engines.fit_count(dict(bfc, fight_penalty=[0.003, 0.01]))
    # was eq_checks.py:320
    check("fits: growing, one per limit (your filters kept: one more); adjusted or nothing added: each count on its "
          "own; two penalties, twice the fits",
          grown == (4, 5, True, False, False) and both == 16, (grown, both))


# ---------------------------------------------------------------- inside a fit
def test_split_filters_merged_within_the_gain_limit(check):
    # two filters at one spot are merged only while the sum keeps within the gain limits (a +3 dB device got +6)
    two = np.array([np.log10(3000), 3.0, np.log(2.0), np.log10(3010), 3.0, np.log(2.02)])
    lb, ub = np.array([1, -12, -3] * 2, float), np.array([5, 3, 3] * 2, float)
    kept_two, merged = engines._tidy(("PK", "PK"), two, lb, ub), engines._tidy(("PK", "PK"), two, lb, ub + [0, 6, 0] * 2)
    # was eq_checks.py:379
    check("fits: split filters merged only within the gain limit (two +3 dB stay two at a +3 dB limit)",
          [f["gain"] for f in kept_two] == [3.0, 3.0] and [f["gain"] for f in merged] == [6.0], (kept_two, merged))


def test_starting_points_spread(sample_curves, monkeypatch, check):
    # starting points: a short website seed is padded across the range (was 32, 64, 128 kHz: piled at the top), and
    # random starts spread even when the filter range starts above 12 kHz (were all at its bottom)
    curves = sample_curves[0]
    task = {"n": 8, "q_min": 0.5, "q_max": 2, "gain_max": 6, "gain_min": -12, "freq_low": 20, "freq_high": 16000,
            "starts": 2, "shelves": {"low": False, "high": False},
            "seeds": [{"filters": [(100.0, 2.0, 1.0), (1000.0, -3.0, 2.0)], "rms": 1.0}]}
    # (a worker's fitting data, for AutoEq's start: put back as it was after the test)
    monkeypatch.setattr(engines, "_bf", {"fb": curves["f"], "fs": 48000, "tb": curves["target"], "mb": curves["meas"]})
    pad = [f for f, g, q in engines._starting_points(task)[0][2:]]
    hi_starts = engines._starting_points(dict(task, freq_low=13000, freq_high=20000, seeds=[]))[-2:]
    # was eq_checks.py:390
    check("fits: padded seeds spread within 20 Hz-12 kHz; random starts spread above 12 kHz too",
          len(pad) == 6 and len(set(pad)) == 6 and all(20 < f < 12000 for f in pad)
          and all(len({round(f) for f, g, q in s}) > 4 and all(13000 <= f <= 20000 for f, g, q in s) for s in hi_starts),
          (pad, [[round(f) for f, g, q in s] for s in hi_starts]))


def test_failed_fit_stops_the_others(monkeypatch, check):
    # a task that fails stops the rest (they ran to the end before the error showed). Each of the others sleeps
    # time_limit(1), 1 s at the usual pace, and the limit is time_limit(2.5): on a busy PC both get longer together,
    # so all four left running to the end (4 naps) still go past the limit, as in the old check.
    monkeypatch.setitem(engines._stopping, "on", False)  # (the stop below sets it: put back as it was after the test)
    nap = qt.time_limit(1)

    def task_fn(i):
        if i == 0:
            raise RuntimeError("broken fit")
        time.sleep(nap)
    t0 = time.time()
    try:
        with ThreadPoolExecutor(1) as pool:
            engines.run_tasks(pool, task_fn, [0, 1, 2, 3, 4])
    except RuntimeError:
        pass
    # was eq_checks.py:407
    check("runs: one failed fit stops the others (the error shows at once)", time.time() - t0 < qt.time_limit(2.5),
          round(time.time() - t0, 1))


def test_empty_scored_range_said(sample_curves, check):
    # an empty scored range is said, not scored as NaN
    curves = sample_curves[0]
    # was eq_checks.py:409
    check("scoring: a scored range without curve points is said (was NaN)",
          "has no curve points" in (raises(engines.rms_error, curves["f"], curves["meas"], curves["target"], [19900, 20000]) or ""))


def test_queue_errors_hidden_only_while_stopping(monkeypatch, check):
    # the queue errors hidden only while workers are being stopped
    seen_err = []
    monkeypatch.setattr(engines, "_feeder_error", lambda e, obj: seen_err.append(e))
    monkeypatch.setitem(engines._stopping, "on", False)
    engines._quiet_feeder_error(OSError("pipe"), None)
    monkeypatch.setitem(engines._stopping, "on", True)
    engines._quiet_feeder_error(OSError("pipe"), None)
    monkeypatch.undo()  # (the real one and "not stopping" back, as the old check's finally did)
    # was eq_checks.py:421
    check("runs: a queue's error goes to the log unless workers are being stopped", len(seen_err) == 1, seen_err)


def test_points_and_graphic_eq_one_v8_per_thread(sample_curves, eq_cfg, monkeypatch, check):
    # counting points and the GraphicEQ text: one V8 per thread, not one per call
    mt = sample_curves[1]
    made, real_racer = [], engines._racer
    monkeypatch.setattr(engines, "_racer", lambda: (made.append(1), real_racer())[1])
    engines._kept.__dict__.pop("ctxs", None)  # (this thread's V8s: none yet, so each one started is counted)
    counts = [engines.count_points(mt[0]) for _ in range(5)]
    texts = [engines.graphic_eq_text(eq_cfg, [{"type": "PK", "freq": 1000, "gain": 2, "q": 1}]) for _ in range(3)]
    monkeypatch.undo()
    # was eq_checks.py:431
    check("files: points counted and GraphicEQ written with one V8 each per thread", len(made) == 2 and len(set(counts)) == 1
          and counts[0] >= 32 and len(set(texts)) == 1 and texts[0].startswith("GraphicEQ"), (len(made), counts[:1], texts[0][:20]))


# ---------------------------------------------------------------- Best fit: the scored range's top and your own filters
def test_falloff_at_20k_followed(sample_curves, eq_cfg, check):
    # scored to 20 kHz, a measurement falling off at the top: the grid's point past 20 kHz (no data) isn't guarded, so
    # the EQ isn't pulled back to 0 dB there (a filter was spent cutting at 20 kHz: 0.35 dB left, now 0.05); a pool
    curves, mt, tt = sample_curves
    fall = dict(curves, meas=curves["target"] - np.clip((curves["f"] - 16000) / 400, 0, 10))
    ce = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"band_hz": [20, 20000]},
                             "best_fit": {"filter_counts": [4], "gain_max": [12], "q_max": [4], "random_starts": 2,
                                          "seed_with_site": False, "freq_range": [20, 20000]}})
    r = pipeline.run_mode("best_fit", ce, fall, mt, tt)["best"]
    # was eq_checks.py:452
    check("methods: Best fit scored to 20 kHz follows a fall-off there (the grid's point past 20 kHz isn't guarded)",
          r["rms"] < 0.15 and not any(f["freq"] > 19500 and f["gain"] < 0 for f in r["filters"]), (r["rms"], r["filters"]))


def test_your_filters_kept_and_added_to(sample_curves, check):
    # Best fit from your own filters: kept exactly, filters added, and yours alone among the results; a pool
    curves, mt, tt = sample_curves
    cb = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"pick": "lowest"},
                             "best_fit": dict(SMALL, start_keep=True)})
    out = pipeline.run_mode("best_fit", cb, curves, mt, tt)
    rows = sorted(r["rows"] for r in out["results"])
    # was eq_checks.py:464
    check("methods: Best fit keeps your filters exactly and adds to them (and scores yours alone)",
          rows == [0, 2, 4] and all(r["filters"][:2] == KEPT and len(r["filters"]) >= 2 + (r["rows"] > 0) for r in out["results"])
          and min(r["rms"] for r in out["results"] if r["rows"]) < min(r["rms"] for r in out["results"] if not r["rows"]),
          [(r["rows"], r["rms"], r["filters"][:3]) for r in out["results"]])


def test_your_filters_adjusted_when_asked(sample_curves, eq_cfg, check):
    # a pool of worker processes
    curves, mt, tt = sample_curves
    cfg = eq_cfg
    cb = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "best_fit": dict(SMALL, start_keep=False)})
    out = pipeline.run_mode("best_fit", cb, curves, mt, tt)
    alone = [r for r in out["results"] if not r["rows"]]
    # was eq_checks.py:471
    check("methods: Best fit may adjust your filters when asked (yours alone, adjusted, score better than as typed)",
          alone and alone[0]["filters"] != KEPT and alone[0]["rms"] < engines.finish({"filters": KEPT}, curves, cfg["scoring"]["band_hz"], cfg["site"]["sample_rate"])["rms"],
          [(r["rows"], r["rms"]) for r in out["results"]])


def test_absurd_db_values_said(sample_curves, eq_cfg, check):
    tt = sample_curves[2]
    huge = "".join(f"{20 * 1.1 ** i:.2f}\t{900000 if i == 40 else 80}\n" for i in range(80))
    # was eq_checks.py:483
    check("curves: absurd dB values give a clear message", "values the app can't use" in (raises(engines.load_curves, eq_cfg, [huge], tt) or ""))


def test_previews_one_v8_per_thread(sample_curves, eq_cfg, monkeypatch, check):
    # previews and comparisons: one V8 per thread, not one per curve
    mts = sample_curves[1]
    made, real_racer = [], engines._racer
    monkeypatch.setattr(engines, "_racer", lambda: (made.append(1), real_racer())[1])
    engines._kept.__dict__.pop("ctxs", None)  # (this thread's V8s: none yet, so each one started is counted)
    prev = [engines.preview_curve(eq_cfg, mts[:2]) for _ in range(3)]
    monkeypatch.undo()
    # was eq_checks.py:1031
    check("previews: one V8 per thread for the same settings", len(made) == 1 and prev[0] == prev[2], len(made))


# ---------------------------------------------------------------- review 2's fixes in Best fit's maths
def test_shelf_q_within_the_apps(check):
    # was eq_checks.py:2182
    check("best fit: a shelf's Q stays within the EQ app's (0.5-6 took shelves at 0.44), AutoEq's 0.4-0.7 otherwise",
          engines.shelf_q({"q_min": 0.5, "q_max": 6}) == (0.5, 0.7) and engines.shelf_q({"q_min": 0.18, "q_max": 6})
          == (0.4, 0.7) and engines.shelf_q({"q_min": 1.0, "q_max": 6})[0] == 1.0)


def test_your_filters_adjusted_within_the_apps_range(check):
    lo, hi, _s = engines._mine_bounds([{"type": "PK", "freq": 8000.0, "gain": 3.0, "q": 1.0}],
                                      {"q_min": 0.5, "q_max": 6, "gain_min": -12, "gain_max": 12, "freq_low": 40,
                                       "freq_high": 10000})
    # was eq_checks.py:2188
    check("best fit: your own filters, when adjusted, stay within the EQ app's frequency range", 10 ** hi[0] <= 10000.01,
          10 ** hi[0])


# ---------------------------------------------------------------- the pick and the ear error
def test_pick_target_first(check):
    # pick() itself: the target first; out of reach: the simplest that sounds the same as the closest
    f = np.geomspace(20, 20000, 400)
    bump = lambda db, at: db * np.exp(-0.5 * (np.log2(f / at) / 0.5) ** 2)
    cv, band = {"f": f, "meas": np.zeros_like(f), "target": np.zeros_like(f)}, [20, 10000]

    def res(i, n, eq):
        r = {"id": i, "rows": n, "n_filters": n, "max_q": 1, "max_boost": 1, "eq": eq,
             "rms": engines.rms_error(f, eq, cv["target"], band)}
        r["ear"], r["ear_at"] = engines.ear_error(f, eq, band)
        return r
    sc = {"pick": "audible", "ear_db": 0.25, "tolerance_db": 0.1, "priority": ["n_filters", "max_q", "max_boost"]}
    near = [res(0, 3, bump(0.6, 1000)), res(1, 5, bump(0.1, 1000) + 0.4), res(2, 8, np.zeros_like(f))]
    far = [res(0, 3, bump(1.0, 5000)), res(1, 5, bump(0.95, 1000)), res(2, 8, bump(0.8, 1000))]
    (a, _, a_case), (b, _, b_case) = engines.pick(near, sc, cv, band), engines.pick(far, sc, cv, band)
    high = engines.ear_error(f, np.where(f > 10000, 3.0, 0.0), band)[0]  # (only above the scored range)
    # was eq_checks.py:2280
    check("pick: the target first (a level offset isn't a difference); out of reach, the simplest close to the closest; "
          "the ear error only within the scored range",
          (a["id"], a_case, b["id"], b_case) == (1, "target", 1, "best") and high < 0.05 and "pick_case" not in a,
          (a["id"], a_case, b["id"], b_case, round(high, 3)))
