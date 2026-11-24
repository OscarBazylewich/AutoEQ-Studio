"""Loading the curves and running the EQ methods (eq\\pipeline.py): the sample curves loaded, averaged and finite;
what a run refuses before it starts (more of your filters than the device holds, your filters that can't be read);
the time estimate's question "was this sweep run just now?" answered without reading the files again; and Best fit
grown one filter at a time (every count a result, the progress, the audible pick where the growing stops). Moved from
eq_checks.py's module_checks (and grow_checks, which it ran).

The curves are the sample target and device (the sample_curves fixture: those files by name). The two growing runs
start a pool of worker processes, as the app's runs do (AUTOEQSTUDIO_MAX_WORKERS caps it: 2 in the tests)."""
import time

import numpy as np
import pytest

from eq import engines, inputs, pipeline, settings
from helpers import studio
from helpers.checks import raises  # (eq_checks.py's raises, line 50: the message of a ValueError, or None)

# your own filters for Best fit to start from and the small run around them (eq_checks.py lines 455-458)
MINE = "Filter 1: ON PK Fc 1000 Hz Gain -2 dB Q 1.5\n120 3 0.8"
SMALL = {"filter_counts": [2, 4], "gain_max": [6], "q_max": [3], "random_starts": 2, "seed_with_site": False,
         "fight_penalty": [0.01],
         "low_shelf": False, "high_shelf": False, "start_filters": MINE}


def test_curves_loaded_averaged_finite(sample_curves, check):
    # (the sample target and the sample device's 10 seatings, loaded as a run loads them)
    curves, _mt, _tt = sample_curves
    meas = studio.measurement_paths()
    finite = all(map(lambda a: np.isfinite(a).all(), (curves["f"], curves["meas"], curves["target"])))
    # was eq_checks.py:228
    check("curves: loaded, averaged, finite", finite and len(curves["channels"]) == len(meas))


def test_more_of_your_filters_than_the_device_holds(sample_curves, check):
    curves = sample_curves[0]
    c7 = settings.with_auto({"mode": "best_fit", "best_fit": {"layout": "app:voicemeeter",
                                                             "start_filters": "\n".join(f"{100 * 2 ** i} 1 1" for i in range(7))}})
    try:
        pipeline.check_run("best_fit", c7, curves)
        msg7 = ""
    except ValueError as err:
        msg7 = str(err)
    # was eq_checks.py:289
    check("devices: more filters of yours than the device holds is said before the run", "but Voicemeeter (Banana, Potato) allows at most" in msg7, msg7)


def test_more_of_your_filters_than_peace_is_set_to(sample_curves, check):
    curves = sample_curves[0]
    twelve = "\n".join(f"{100 + 50 * i} 1 1" for i in range(12))
    cfg = lambda bands: settings.with_auto({"mode": "best_fit", "best_fit": {
        "layout": "app:peace", "start_filters": twelve, "per_app": {"peace": {"bands": bands}}}})
    msg = raises(pipeline.check_run, "best_fit", cfg(10), curves) or ""
    check("Peace: 12 filters of yours with Peace bands 10 is said before the run, with the number of the user",
          msg.startswith("You have 12 filters, but Peace (for Equalizer APO) allows at most 10. "), msg)
    check("Peace: 12 filters of yours with Peace bands 31 (the default) is a run",
          raises(pipeline.check_run, "best_fit", cfg(31), curves) is None)


def test_best_fit_stays_in_what_peace_is_set_to(sample_curves, check):
    # (a pool of worker processes: a small run, grown to at most 4 filters and the low shelf)
    curves, mt, tt = sample_curves
    cfg = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"pick": "lowest"}, "best_fit": {
        "layout": "app:peace", "filter_counts": [2, 4, 8], "gain_min": -12, "gain_max": [9], "q_max": [3],
        "low_shelf": True, "high_shelf": False, "fight_penalty": [0.01],
        "per_app": {"peace": {"bands": 5, "gain": 3}}}})
    rs = pipeline.run_mode("best_fit", cfg, curves, mt, tt)["results"]
    gains = [f["gain"] for r in rs for f in r["filters"]]
    # (max gain 3: the sample needs a cut of 4.4 dB, so a run that did not obey the number would go past it)
    check("Peace: a Best fit run with Peace bands 5 and max gain 3 has no result with more than 5 filters or a gain "
          "outside ±3 dB",
          rs and gains and max(r["n_filters"] for r in rs) <= 5 and max(len(r["filters"]) for r in rs) <= 5
          and -3 <= min(gains) and max(gains) <= 3 and all(r["gain_min"] == -3 and r["gain_max"] == 3 for r in rs),
          ([(r["rows"], r["n_filters"]) for r in rs], min(gains, default=None), max(gains, default=None)))
    # the same run with the default 31 bands and ±30 dB goes past both (so the check above can fail)
    wide = settings.with_auto(dict(cfg, best_fit=dict(cfg["best_fit"], per_app={"peace": {"bands": 31, "gain": 30}})))
    ws = pipeline.run_mode("best_fit", wide, curves, mt, tt)["results"]
    check("Peace: the same run with 31 bands and ±30 dB has a result with more than 5 filters and a cut below -3 dB",
          max(r["n_filters"] for r in ws) > 5 and min(f["gain"] for r in ws for f in r["filters"]) < -3,
          ([(r["rows"], r["n_filters"]) for r in ws], min(f["gain"] for r in ws for f in r["filters"])))


@pytest.mark.parametrize("pick", ["audible", "lowest"])
def test_fxsound_band_counts_one_run(pick, sample_curves, check):
    curves, mt, tt = sample_curves
    cfg = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"pick": pick}, "best_fit": {
        "layout": "app:fxsound", "per_app": {"fxsound": {"band_counts": [5, 10, 15, 20, 31]}}}})
    said = []
    out = pipeline.run_mode("best_fit", cfg, curves, mt, tt, progress=lambda d, t, m="": said.append((d, t, m)))
    rs = out["results"]
    check(f"FxSound: a run with its 5 band counts gives 5 results in the order of the counts ({pick})",
          [(r["id"], r["rows"], r["mode"], r["engine"]) for r in rs]
          == [(i, n, "best_fit", "graphic") for i, n in enumerate((5, 10, 15, 20, 31))], [(r["id"], r["rows"]) for r in rs])
    chosen, best, case = engines.pick(rs, cfg["scoring"], curves, cfg["scoring"]["band_hz"])
    check(f"FxSound: the result of the run is the one that Best result selects among the 5, by the rule of every "
          f"layout ({pick})",
          out["pick"] is chosen and out["best"] is best and out["pick_case"] == case
          and best["rms"] == min(r["rms"] for r in rs) and (pick != "lowest" or out["pick"] is best)
          and (pick != "audible" or case in ("target", "best")), (out["pick"]["rows"], out["best"]["rows"], case))
    msg = "Best fit: adjusting band gains (FxSound)"
    check(f"FxSound: the progress counts the band counts, with the message of every graphic EQ ({pick})",
          said == [(i, 5, msg) for i in range(6)], said)


def test_sweep_cached_reads_no_files_again(fresh_studio, eq_cfg, monkeypatch, check):
    # whether a sweep is cached: the texts the curves were loaded from, not every file read again. (The files in use
    # are the studio's as new, the sample target and device: sweep_cached asks inputs.selected for them, as the old
    # check's load did.)
    cfg = eq_cfg
    t, meas = inputs.selected(cfg)
    reads, real_read_text = [], inputs.read_text
    monkeypatch.setitem(pipeline._SWEEPS, "dummy", [])
    monkeypatch.setattr(inputs, "read_text", lambda p: (reads.append(p), real_read_text(p))[1])
    pipeline.load(cfg, t, meas)
    n_load = len(reads)
    [pipeline.sweep_cached(cfg) for _ in range(4)]
    monkeypatch.undo()  # (the real reading back and the dummy sweep gone, as the old check's finally did)
    # was eq_checks.py:444
    check("estimates: asking whether a sweep is cached reads no files again", len(reads) == n_load, (n_load, len(reads)))


def test_unreadable_filters_named_before_the_run(sample_curves, check):
    curves, mt, tt = sample_curves
    cb = settings.with_auto({"mode": "best_fit", "best_fit": dict(SMALL, start_filters="Filter 1: ON PK Fc 100 Hz Gain 3 dB\nhello")})
    # was eq_checks.py:475
    check("methods: your filters that can't be read are named before the run",
          (raises(pipeline.run_mode, "best_fit", cb, curves, mt, tt) or "").startswith("Your filters, line 1"))


# ---------------------------------------------------------------- Best fit grown one filter at a time
def test_growing_every_count_a_result(sample_curves, check):
    # every count a result, closer with more filters; the progress counts the filters added (a pool)
    curves, mt, tt = sample_curves
    said = []
    cg = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "scoring": {"pick": "lowest"}, "best_fit": {
        "filter_counts": list(range(1, 7)), "gain_max": [6], "q_max": [3], "low_shelf": False, "high_shelf": False,
        "fight_penalty": [0.01]}})
    out = pipeline.run_mode("best_fit", cg, curves, mt, tt, progress=lambda dn, t, m="": said.append((dn, t, m)))
    rs = sorted(out["results"], key=lambda r: r["rows"])
    grew = [m for _d, _t, m in said if m.startswith("Best fit (adding filters): ")]
    # was eq_checks.py:2250
    check("Best fit, growing: every count is a result, each closer than the first; the progress counts the filters added",
          [r["rows"] for r in rs] == [1, 2, 3, 4, 5, 6] and all(len(r["filters"]) <= r["rows"] for r in rs)
          and rs[-1]["rms"] < rs[0]["rms"] and grew and said[-1][:2] == (6, 6),
          ([(r["rows"], round(r["rms"], 3)) for r in rs], said[-1:]))


@pytest.mark.slow  # (a pool growing 4 fits to up to 32 filters: about 2.5 s with the tests' 2 workers)
def test_audible_pick_where_growing_stops(sample_curves, check):
    # the audible pick: the fewest filters that sound the same as the target; the growing stops there (a pool)
    curves, mt, tt = sample_curves
    ca = settings.with_auto({"mode": "best_fit", "auto": {"enabled": False}, "best_fit": {
        "filter_counts": list(range(1, 33)), "gain_max": [6, 9], "q_max": [3, 5]}})
    t0 = time.time()
    out = pipeline.run_mode("best_fit", ca, curves, mt, tt)
    p, lim = out["pick"], ca["scoring"]["ear_db"]
    fewer = [r for r in out["results"] if r["ear"] <= lim and (r["n_filters"], r["rows"]) < (p["n_filters"], p["rows"])]
    # was eq_checks.py:2261
    check("pick: the fewest filters that sound the same as the target (ear error within 0.25 dB); growing stops there",
          out["pick_case"] == "target" and p["ear"] <= lim and not fewer
          and max(r["rows"] for r in out["results"]) < 32 and p.get("ear_at"),
          (out["pick_case"], p["n_filters"], round(p["ear"], 3), round(time.time() - t0, 1), fewer[:1]))


NO_DATA = "Frequency range ({}–{} Hz) has no curve data (curves cover 20 Hz–20 kHz). Adjust the range."
NARROW = "Frequency range ({}–{} Hz) is too narrow and needs at least 2 curve points. Widen the range."


def test_scored_range_message_fits_its_cause(sample_curves, check):
    # (2026-11-24: a range between two points of the curves, inside 20 Hz-20 kHz, said "has no curve data (curves
    # cover 20 Hz-20 kHz)": that hint does not explain it. And the score took a range with 1 point, while the check
    # before a run refused it.) The curves have points at 19,897 and 20,186 Hz and none between.
    curves = sample_curves[0]
    f = curves["f"]
    one = [float(f[100]) - 0.01, float(f[100]) + 0.01]  # (1 point of the curves)

    def score(band):
        return raises(engines.rms_error, f, curves["meas"], curves["target"], band)
    said = {name: (pipeline.band_problem(curves, band), score(band))
            for name, band in (("between", [19900, 19950]), ("one", one), ("above", [30000, 40000]), ("below", [5, 10]),
                               ("good", [20, 10000]))}
    check("scoring: a range inside the curves with no point or 1 point is too narrow, to the check before a run and "
          "to the score alike",
          said["between"] == (NARROW.format(19900, 19950),) * 2
          and said["one"] == (NARROW.format(f"{one[0]:g}", f"{one[1]:g}"),) * 2, (said["between"], said["one"]))
    check("scoring: a range outside the curves has no curve data, to the check before a run and to the score alike",
          said["above"] == (NO_DATA.format(30000, 40000),) * 2 and said["below"] == (NO_DATA.format(5, 10),) * 2,
          (said["above"], said["below"]))
    check("scoring: a range with 2 or more points of the curves is accepted", said["good"] == (None, None), said["good"])


def test_fit_range_in_the_wrong_order_said_first(sample_curves, check):
    # (2026-11-24: Fit from 10005 with Fit up to 10000 gave the message of a range with no curve points: that check
    # ran before the one of minimum and maximum)
    cfg = settings.with_auto({"mode": "site_single"})
    cfg["scoring"]["band_hz"] = [10005, 10000]
    said = raises(pipeline.check_run, "site_single", cfg, sample_curves[0])
    check("runs: Fit from larger than Fit up to gives the message of minimum and maximum, not one of the curve points",
          said == "Fit range: minimum (10005) must be less than maximum (10000)", said)
