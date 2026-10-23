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

from eq import inputs, pipeline, settings
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
    check("devices: more filters of yours than the device holds is said before the run", "more than Voicemeeter" in msg7, msg7)


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
    grew = [m for _d, _t, m in said if m.startswith("Adding filters one at a time")]
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
