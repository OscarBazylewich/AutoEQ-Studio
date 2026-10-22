"""The automatic settings (eq\\autoset.py): what their notes say (a device's limits, one value and its fact a line),
every method at every slider end valid and within the limits, the filter counts and the audible pick, Best fit's
plans at every search, the time estimate of a huge sweep, and the analysis's key. Moved from eq_checks.py's
module_checks (and grow_checks, which it ran).

The analysis of the sample curves (autoset.analyse) is made once for the file (the analysis fixture); the other
checks use made-up analyses, as the old ones did."""
import json
import time

import pytest

from eq import autoset, pipeline, settings
from helpers import qt

# a made-up analysis of a device's curves (eq_checks.py lines 296-298)
AN = {"features": 12, "no_eq_rms": 3, "band_top": 10000, "band_why": "default", "n_files": 1, "unstable_from": None,
      "need_boost": 8, "boost_at": 3000, "need_cut": -6, "cut_at": 100, "q_need": 3, "q_at": 2000, "bass_step": 0,
      "treble_step": 0, "data_top": 20000, "agree_to": None}
# the one grow_checks plans on (eq_checks.py lines 2225-2228 and 2230-2233: a fresh copy for each plan, as there)
GROW_AN = {"features": 10, "no_eq_rms": 3, "band_top": 10000, "band_why": "default", "n_files": 1,
           "unstable_from": None, "need_boost": 6, "boost_at": 3000, "need_cut": -6, "cut_at": 100,
           "q_need": 3, "q_at": 2000, "bass_step": 0, "treble_step": 0, "data_top": 20000,
           "agree_to": None}


def raises(fn, *a, **k):
    """The error message fn raises (ValueError), or None (eq_checks.py's raises, line 50)."""
    try:
        fn(*a, **k)
    except ValueError as e:
        return str(e)
    return None


@pytest.fixture(scope="module")
def analysis(sample_curves):
    """The sample curves' analysis, as the automatic settings make it (eq_checks.py line 486)."""
    curves, mt, _tt = sample_curves
    return autoset.analyse(settings.with_auto({}), curves, mt)


# ---------------------------------------------------------------- the notes
def test_device_notes_give_its_limits(check):
    # the automatic notes say the device's limits (they said 32 filters, +10 dB for a 9-filter, +3 dB device)
    notes = " ".join(n["text"] for n in autoset.plan(settings.with_auto({"mode": "best_fit", "best_fit": {
        "layout": "app:moondrop_free_dsp"}}), AN)["notes"])
    # was eq_checks.py:301
    check("automatic settings: a device's notes give its limits (9 filters, +3 dB)", "Up to 9 filters" in notes
          and "Boosts up to +3 dB" in notes, notes[:200])


def test_each_note_a_line(check):
    # each note: the value and the fact about your curves behind it, in a line (why the app works so: Help)
    busy = dict(AN, treble_step=4, bass_step=-4, unstable_from=5600, band_why="unstable", n_files=10)
    wordy = [n["text"] for n in autoset.plan(settings.with_auto({"mode": "best_fit", "auto": {"level": 100}}), busy)["notes"]
             if len(n["text"]) > 80 or "test" in n["text"]]
    # was eq_checks.py:307
    check("automatic settings: each note is a value and its fact in a line (the reasons are on the Help page)", not wordy, wordy)


# ---------------------------------------------------------------- the time estimate
def test_huge_sweep_refused_and_estimated_quickly(sample_curves, check):
    # (the limit: time_limit(1), 1 s at the usual pace; measured about 1 ms)
    curves = sample_curves[0]
    big = settings.with_auto({"site_sweep": {"freq_high": list(range(1000, 21000, 10)), "q_max": [0.5 + i / 100 for i in range(300)]}})
    t0 = time.time()
    est = autoset.estimate(big, "site_sweep")
    # was eq_checks.py:480
    check("methods: a huge sweep is refused, and its estimate stays quick",
          "at most" in (raises(pipeline.check_run, "site_sweep", big, curves) or "") and time.time() - t0 < qt.time_limit(1) and est > 3600)


# ---------------------------------------------------------------- every method and slider end
@pytest.mark.parametrize("lv", [0, 50, 100])
@pytest.mark.parametrize("mode", list(settings.MODES))
def test_every_method_and_level_valid(mode, lv, analysis, check):
    # automatic settings: every method and slider end within the limits, pairs in order
    c2 = settings.with_auto({"mode": mode, "auto": {"level": lv}})
    p = autoset.plan(c2, analysis)
    autoset.apply(c2, p["values"])
    ok = settings.clamp(json.loads(json.dumps(c2))) == c2
    # was eq_checks.py:493
    check(f"auto settings: {mode} at {lv} valid, with reasons", ok and p["notes"], p["values"])


def test_counts_reach_their_ceiling(analysis, check):
    # no cap below where fits stop improving: the counts reach their ceiling, the audible pick at 0.25 dB
    v = {mode: autoset.plan(settings.with_auto({"mode": mode}), analysis)["values"] for mode in ("best_fit", "site_sweep")}
    reach = (max(v["best_fit"]["best_fit.filter_counts"]), max(v["site_sweep"]["site_sweep.filter_rows"]),
             v["best_fit"]["scoring.pick"], v["best_fit"]["scoring.ear_db"])
    # was eq_checks.py:498
    check("auto settings: filter counts reach their ceiling, the audible pick (0.25 dB)",
          reach == (settings.LIMITS["best_fit.filter_counts"]["max"], settings.LIMITS["site_sweep.filter_rows"]["max"],
                    "audible", 0.25), reach)


# ---------------------------------------------------------------- the analysis's key
def test_analysis_key_follows_the_curves(sample_curves, eq_cfg, check):
    # a run uses the page's analysis only for the curves it was made from
    _cs, mts, tts = sample_curves
    cfg = eq_cfg
    key = autoset.analysis_key(cfg, mts, tts)
    moved = json.loads(json.dumps(cfg)); moved["scoring"]["band_hz"][1] = 12000  # (the automatic "to" changing: same key)
    # was eq_checks.py:687
    check("runs: the analysis key follows the curves, not the automatic scored range",
          key == autoset.analysis_key(moved, mts, tts) and key != autoset.analysis_key(cfg, mts[:1], tts))


# ---------------------------------------------------------------- Best fit's plans (grown one filter at a time)
def test_your_filters_adjusted_counts_stay_sparse(check):
    adjusted = autoset.plan(settings.with_auto({"mode": "best_fit", "auto": {"level": 0}, "best_fit": {
        "start_filters": "1000 2 1", "start_keep": False}}), dict(GROW_AN))["values"]["best_fit.filter_counts"]
    # was eq_checks.py:2234
    check("Best fit: your own filters adjusted (each count on its own): Quick's counts stay sparse",
          len(adjusted) < 32, adjusted)


def test_grows_by_default_every_count_at_every_search(check):
    d = settings.DEFAULTS["best_fit"]
    plans = [autoset.plan(settings.with_auto({"mode": "best_fit", "auto": {"level": lv}}), dict(GROW_AN))["values"]
             for lv in (0, 50, 100)]
    # was eq_checks.py:2236
    check("Best fit: grows by default, no website seeding; the automatic settings: every filter count, the audible pick "
          "(0.25 dB), no seeding, at every search",
          "build" not in d and "seed_with_site" not in d and settings.DEFAULTS["scoring"]["pick"] == "audible"
          and all("best_fit.seed_with_site" not in v and v["scoring.pick"] == "audible" and v["scoring.ear_db"] == 0.25
                  and v["best_fit.filter_counts"] == list(range(1, 33)) for v in plans),
          [(v["scoring.pick"], len(v["best_fit.filter_counts"])) for v in plans])
