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
from helpers.checks import raises  # (eq_checks.py's raises, line 50: the message of a ValueError, or None)

# a made-up analysis of a device's curves (eq_checks.py lines 296-298)
AN = {"features": 12, "no_eq_rms": 3, "band_top": 10000, "band_why": "default", "n_files": 1, "unstable_from": None,
      "need_boost": 8, "boost_at": 3000, "need_cut": -6, "cut_at": 100, "q_need": 3, "q_at": 2000, "bass_step": 0,
      "treble_step": 0, "data_top": 20000, "agree_to": None}
# the one grow_checks plans on (eq_checks.py lines 2225-2228 and 2230-2233: a fresh copy for each plan, as there)
GROW_AN = {"features": 10, "no_eq_rms": 3, "band_top": 10000, "band_why": "default", "n_files": 1,
           "unstable_from": None, "need_boost": 6, "boost_at": 3000, "need_cut": -6, "cut_at": 100,
           "q_need": 3, "q_at": 2000, "bass_step": 0, "treble_step": 0, "data_top": 20000,
           "agree_to": None}


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
    check("automatic settings: a device's notes give its limits (9 filters, +3 dB)", "Maximum 9 filters" in notes
          and "Maximum gain +3 dB" in notes, notes[:200])


def test_q_note_says_the_second_limit_is_tried_too(check):
    # (2026-11-08: the STE rewrite made it "Maximum Q 3 and Q 6", which did not say that Q 6 is a second limit that
    # the app also tries; Best fit tries two Q limits, a single run one)
    def q_note(cfg):
        return next(n["text"] for n in autoset.plan(settings.with_auto(cfg), dict(AN))["notes"]
                    if n["text"].startswith("Maximum Q"))
    two, one = q_note({"mode": "best_fit"}), q_note({"mode": "site_single"})
    check("automatic settings: the Q note says the app also tries the second Q limit (and is a line)",
          "(the app also tries Q " in two and len(two) <= 80 and "also tries" not in one and "approximately" in one,
          (two, one))


def test_each_note_a_line(check):
    # each note: the value and the fact about your curves behind it, in a line (why the app works so: Help)
    busy = dict(AN, treble_step=4, bass_step=-4, unstable_from=5600, band_why="unstable", n_files=10)
    wordy = [n["text"] for n in autoset.plan(settings.with_auto({"mode": "best_fit", "auto": {"level": 100}}), busy)["notes"]
             if len(n["text"]) > 80 or "test" in n["text"]]
    # was eq_checks.py:307
    check("automatic settings: each note is a value and its fact in a line (the reasons are on the Help page)", not wordy, wordy)


# ---------------------------------------------------------------- the time estimate
def test_huge_sweep_refused_and_estimated_quickly(sample_curves, check):
    # (the limit: 1 s, fixed, exactly as the old check had it: it takes about 1 ms, so even a busy PC stays far below
    # it; a time limit stretched by the time factor would let a slowdown to 2 or 4 s pass)
    curves = sample_curves[0]
    big = settings.with_auto({"site_sweep": {"freq_high": list(range(1000, 21000, 10)), "q_max": [0.5 + i / 100 for i in range(300)]}})
    t0 = time.time()
    est = autoset.estimate(big, "site_sweep")
    # was eq_checks.py:480
    check("methods: a huge sweep is refused, and its estimate stays quick",
          "The maximum is" in (raises(pipeline.check_run, "site_sweep", big, curves) or "") and time.time() - t0 < 1 and est > 3600)


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


# ---------------------------------------------------------------- the short text of what a run tries (2026-11-10)
def _short_cfg(**bf):
    """Best fit with one boost limit, one Q limit and one penalty (one growing EQ per limit), these settings over."""
    cfg = settings.with_auto({"mode": "best_fit"})
    cfg["best_fit"].update({"gain_max": [6], "q_max": [2], "fight_penalty": [0.01], **bf})
    return cfg


MINE = "Filter 1: ON PK Fc 100 Hz Gain 2 dB Q 1"


def test_short_text_counts_your_filters_kept(check):
    # (a code review: with your own filters kept as they are, a growing run makes one EQ more, theirs alone, as
    # engines.fit_count counts it; the short text said one too few)
    from eq import engines
    cfg = _short_cfg(filter_counts=[2, 3], start_filters=MINE, start_keep=True)
    bf = autoset.device_settings(cfg["best_fit"])
    short, real = autoset.describe_short(cfg), engines.fit_count(bf, 1)
    check("automatic settings: the short text of a run counts the EQ of your own filters kept as they are (one too "
          "few before)", engines.grows(bf, 1) and real == 2 and short == "2 EQs, 1 to 3 filters", (short, real))


def test_short_text_says_one_without_s(check):
    def scratch(counts):  # (each count fitted on its own: the benchmarks' way, so one EQ for one count and limit)
        cfg = _short_cfg(filter_counts=counts)
        cfg["best_fit"]["build"] = "scratch"
        return cfg
    found = {"one row": autoset.describe_short(settings.with_auto({"mode": "site_single", "site_single": {"rows": 1}})),
             "one growing EQ": autoset.describe_short(_short_cfg(filter_counts=[4])),
             "one EQ of 4": autoset.describe_short(scratch([4])),
             "one EQ of 1": autoset.describe_short(scratch([1])),
             "your one filter": autoset.describe_short(_short_cfg(start_filters=MINE, start_add=False))}
    check("automatic settings: the short text says “1 EQ”, “1 filter”, “1 filter row”, “your 1 filter” (it said "
          "“1 EQs”, “1 filter rows”, “your 1 filters”)",
          found == {"one row": "1 website EQ, 1 filter row", "one growing EQ": "1 EQ, 1 to 4 filters",
                    "one EQ of 4": "1 EQ, 4 filters", "one EQ of 1": "1 EQ, 1 filter",
                    "your one filter": "your 1 filter"}, found)


def test_short_text_with_no_filter_counts(check):
    # (settings.with_auto puts the default counts back for an empty list, so /api/auto never sends one; settings not
    # checked that way made min() and max() stop with a ValueError)
    cfg = _short_cfg()
    cfg["best_fit"]["filter_counts"] = []
    found = raises(autoset.describe_short, cfg), settings.with_auto({"best_fit": {"filter_counts": []}})["best_fit"]["filter_counts"]
    check("automatic settings: the short text of Best fit with no filter counts gives words, not an error (and checked "
          "settings put the default counts back)", found[0] is None and found[1] == list(range(1, 11)), found)
