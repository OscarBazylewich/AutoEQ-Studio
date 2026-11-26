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
def _notes(cfg, **an):
    """{path: text} of the notes for these settings and the made-up analysis AN with these values over."""
    return {n["path"]: n["text"] for n in autoset.plan(settings.with_auto(cfg), dict(AN, **an))["notes"]}


def test_notes_say_which_limit_lowered_the_gain_and_q(check):
    # (the text survey, 2026-11-23: "Max gain +3 dB: largest needed is +8.0 dB" looked like a mistake; the note now
    # says that the EQ app's or the website's own limit set the value. No such words when the curves set it.)
    free = _notes({"mode": "best_fit"})
    app = _notes({"mode": "best_fit", "best_fit": {"layout": "app:moondrop_free_dsp"}})  # (gain to +3 dB, Q to 10)
    app_q = _notes({"mode": "best_fit", "best_fit": {"layout": "app:minidsp_2x4hd"}}, q_need=8)  # (Q to 6)
    site, site_ok = _notes({"mode": "site_single"}, need_boost=25, q_need=8), _notes({"mode": "site_single"})
    sweep = _notes({"mode": "site_sweep"}, need_boost=25, q_need=8)
    found = {"free": (free["best_fit.gain_max"], free["best_fit.q_max"]),
             "app": (app["best_fit.gain_max"], app["best_fit.q_max"]), "app q": app_q["best_fit.q_max"],
             "site": (site["site_single.gain_max"], site["site_single.q_max"]),
             "site ok": (site_ok["site_single.gain_max"], site_ok["site_single.q_max"]),
             "sweep": (sweep["site_sweep.gain_ranges"], sweep["site_sweep.q_max"])}
    check("automatic settings: a gain or Q note says “(app limit)” or “(website limit)” when that limit, not the "
          "curves, set its value, and not otherwise",
          found == {"free": ("Max gain +10 dB: largest needed is +8.0 dB",
                             "Max Q 4 (also tries Q 5): sharpest peak/dip is Q 3.0"),
                    "app": ("Max gain +3 dB (app limit): largest needed is +8.0 dB",
                            "Max Q 4 (also tries Q 5): sharpest peak/dip is Q 3.0"),
                    "app q": "Max Q 6 (app limit): sharpest peak/dip is ~Q 8.0",
                    "site": ("Max gain +20 dB (website limit): largest needed is +25.0 dB",
                             "Max Q 5 (website limit): sharpest peak/dip is ~Q 8.0"),
                    "site ok": ("Max gain +10 dB: largest needed is +8.0 dB", "Max Q 4: sharpest peak/dip is ~Q 3.0"),
                    "sweep": ("Max gain +20 dB (website limit): largest needed is +25.0 dB",
                              "Max Q 5 (website limit): sharpest peak/dip is ~Q 8.0")}, found)


def test_no_note_for_what_the_eq_app_cannot_take(check):
    # (the text survey, 2026-11-23: with your own filters in every filter of the EQ app, the list said "Maximum 1
    # filter" though no filter is added; and "Low shelf on" for an app with no shelves, or with no free filter)
    low = {"bass_step": -4}  # (the bass 4 dB above the target: Low shelf on)
    full9 = "\n".join(f"Filter {i}: ON PK Fc {100 * i} Hz Gain 2 dB Q 1" for i in range(1, 10))
    full10 = full9 + "\nFilter 10: ON PK Fc 5000 Hz Gain 2 dB Q 1"
    free = _notes({"mode": "best_fit"}, **low)
    no_shelves = _notes({"mode": "best_fit", "best_fit": {"layout": "app:moondrop_free_dsp"}}, **low)
    filled = _notes({"mode": "best_fit", "best_fit": {"layout": "app:moondrop_free_dsp", "start_filters": full9}}, **low)
    shelves = _notes({"mode": "best_fit", "best_fit": {"layout": "app:minidsp_2x4hd"}}, **low)
    no_room = _notes({"mode": "best_fit", "best_fit": {"layout": "app:minidsp_2x4hd", "start_filters": full10}}, **low)
    found = {"free": (free.get("best_fit.filter_counts"), free.get("best_fit.low_shelf")),
             "no shelves": (no_shelves.get("best_fit.filter_counts"), no_shelves.get("best_fit.low_shelf")),
             "filled": (filled.get("best_fit.filter_counts"), filled.get("best_fit.low_shelf")),
             "shelves": (shelves.get("best_fit.filter_counts"), shelves.get("best_fit.low_shelf")),
             "no room": (no_room.get("best_fit.filter_counts"), no_room.get("best_fit.low_shelf"))}
    shelf = "Low shelf on: bass is 4.0 dB above target"
    check("automatic settings: no “Maximum … filters” note when your filters use every filter of the EQ app, and no "
          "“Low shelf on” note when the EQ app has no shelves or no free filter (the two notes stay in other cases)",
          found == {"free": ("Maximum 32 filters: 12 peaks/dips to correct", shelf),
                    "no shelves": ("Maximum 9 filters: 12 peaks/dips to correct", None), "filled": (None, None),
                    "shelves": ("Maximum 9 filters: 12 peaks/dips to correct", shelf), "no room": (None, None)}
          and "best_fit.gain_max" in filled and "best_fit.layout" in filled, (found, sorted(filled)))


def test_graphic_eq_has_only_the_range_note(check):
    # (the text survey, 2026-11-23: the line "{layout}: Best fit adjusts only the gains of the bands." is gone; the
    # gray line below Best fit in Settings says it)
    notes = _notes({"mode": "best_fit", "best_fit": {"layout": "graphic_10"}})
    check("automatic settings: a graphic EQ layout has only the note of the fit range (no line that Best fit adjusts "
          "only the gains)", notes == {"scoring.band_hz.1": "Fit up to 10 kHz (default): measurements above 10 kHz "
                                                            "vary with fit"}, notes)


# ---------------------------------------------------------------- FxSound's band counts (one EQ for each, no setting)
RANGE_NOTE = "Fit up to 10 kHz (default): measurements above 10 kHz vary with fit"


def _fx(auto=True):
    return settings.with_auto({"mode": "best_fit", "auto": {"enabled": auto}, "best_fit": {"layout": "app:fxsound"}})


def test_fxsound_notes_say_bands(check):
    p = autoset.plan(_fx(), dict(AN))
    notes = {n["path"]: n["text"] for n in p["notes"]}
    check("automatic settings: FxSound gets the audible pick with its note in the words for bands, and no value of "
          "Best fit (the run fits every band count, with no setting for them)",
          p["values"].get("scoring.pick") == "audible" and p["values"].get("scoring.ear_db") == 0.25
          and notes == {"scoring.band_hz.1": RANGE_NOTE, "scoring.pick": "Fewest bands for the same sound (≤ 0.25 dB)"}
          and not [k for k in p["values"] if k.startswith("best_fit.")], (p["values"], notes))
    other = autoset.plan(settings.with_auto({"mode": "best_fit"}), dict(AN))
    g10 = autoset.plan(settings.with_auto({"mode": "best_fit", "best_fit": {"layout": "graphic_10"}}), dict(AN))
    check("automatic settings: the note of Best result in the words for filters for a parametric layout, and none "
          "for a graphic layout with one set of bands",
          {n["path"]: n["text"] for n in other["notes"]}["scoring.pick"] == "Fewest filters for the same sound (≤ 0.25 dB)"
          and "scoring.pick" not in g10["values"], sorted(g10["values"]))


def test_fxsound_texts_of_what_a_run_tries(check):
    found = {auto: (autoset.describe(_fx(auto)), autoset.describe_short(_fx(auto))) for auto in (True, False)}
    check("automatic settings: the texts of what a run tries for FxSound name its 5 EQs and band counts, with "
          "Automatic settings on and off",
          found == {a: ("FxSound: 5 EQs (5, 10, 15, 20, and 31 bands), -12 to +12 dB (1 dB steps)", "5 EQs, 5 to 31 bands")
                    for a in (True, False)}, found)
    g10 = settings.with_auto({"mode": "best_fit", "best_fit": {"layout": "graphic_10"}})
    check("automatic settings: the texts for a graphic layout without band counts are as before",
          (autoset.describe(g10), autoset.describe_short(g10)) == ("10-band graphic EQ: 10 band gains, -12 to +12 dB (0.1 dB steps)", "10 bands"),
          (autoset.describe(g10), autoset.describe_short(g10)))


def test_estimate_and_learn_with_band_counts(fresh_studio, check):
    g10 = settings.with_auto({"mode": "best_fit", "best_fit": {"layout": "graphic_10"}})
    e5, eg = autoset.estimate(_fx(), "best_fit"), autoset.estimate(g10, "best_fit")
    check("automatic settings: the time estimate of FxSound's 5 band counts is 0.25 s more than one graphic fit "
          "(0.6 s) and stays under 2 s",
          eg == 0.6 and abs((e5 - eg) - 0.25) < 1e-9 and e5 < 2, (eg, e5))
    before = autoset.estimate(settings.with_auto({"mode": "best_fit"}), "best_fit")
    said = raises(autoset.learn, _fx(), "best_fit", 0.3)
    check("automatic settings: a run of several band counts is learned from without an error and changes no estimate "
          "of a parametric run (it has no fitting work to compare)",
          said is None and autoset.estimate(settings.with_auto({"mode": "best_fit"}), "best_fit") == before, said)


def test_range_note_gives_its_cause(check):
    found = [_notes({"mode": "site_single"}, **an)["scoring.band_hz.1"] for an in (
        {"band_why": "agree", "band_top": 16000, "n_files": 4}, {"band_why": "data", "band_top": 8000, "data_top": 8500},
        {"band_why": "unstable", "band_top": 8000, "unstable_from": 8600, "n_files": 3})]
    check("automatic settings: the note of the fit range gives its cause (the files agree, no data, the files diverge)",
          found == ["Fit up to 16 kHz: your 4 files stay consistent until here",
                    "Fit up to 8 kHz: no measurement data above 8.5 kHz",
                    "Fit up to 8 kHz: your 3 files diverge above 8.6 kHz"], found)


def test_moved_value_note_names_the_setting_and_the_values(check):
    # (the text survey, 2026-11-23: the note said only "Set above your “from” value (12000)."; it now names the
    # setting as Settings does (settings.AUTO_NAMES) and gives the new value and yours with their unit)
    def last(cfg):
        return [(n["path"], n["text"]) for n in autoset.plan(settings.with_auto(cfg), dict(AN))["notes"]][-1]
    up = last({"mode": "best_fit", "scoring": {"band_hz": [12000, 20000]}, "auto": {"manual": ["scoring.band_hz.0"]}})
    down = last({"mode": "site_single", "site_single": {"gain_max": -10}, "auto": {"manual": ["site_single.gain_max"]}})
    check("automatic settings: the note of a value moved past your own “from” or “to” value names the setting and "
          "gives the new value and your value with their unit",
          up == ("scoring.band_hz.1", "Auto-adjusted Fit up to: 15 kHz (your minimum is 12 kHz)")
          and down == ("site_single.gain_min", "Auto-adjusted Gain from: -11 dB (your maximum is -10 dB)")
          and settings.AUTO_NAMES["scoring.band_hz.1"] == "Fit up to"
          and settings.AUTO_NAMES["site_single.gain_min"] == "Gain from", (up, down))


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
          "(max 20,000). Reduce" in (raises(pipeline.check_run, "site_sweep", big, curves) or "") and time.time() - t0 < 1 and est > 3600)


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


def test_whole_text_says_one_without_s(check):
    # (a code review, 2026-11-10: describe() said "1 filter rows", "1 gain limits × 1 Q limits", "your 1 filters";
    # it now counts with _many, as describe_short does)
    def scratch(counts):
        cfg = _short_cfg(filter_counts=counts)
        cfg["best_fit"]["build"] = "scratch"
        return cfg
    found = {"one row": autoset.describe(settings.with_auto({"mode": "site_single", "site_single": {"rows": 1}})),
             "one growing EQ": autoset.describe(_short_cfg(filter_counts=[4])),
             "one EQ of 1": autoset.describe(scratch([1])),
             "your one filter": autoset.describe(_short_cfg(start_filters=MINE, start_add=False)),
             # (2026-11-24: the layout "any" has the name "Parametric filters": the text said "filters filters")
             "your one, adjusted, any": autoset.describe(_short_cfg(start_filters=MINE, start_add=False,
                                                                    start_keep=False))}
    found["up to one"] = autoset.describe(_short_cfg(filter_counts=[1]))
    found["your one, adjusted"] = autoset.describe(_short_cfg(start_filters=MINE, start_add=False, start_keep=False,
                                                              layout="app:moondrop_free_dsp"))
    # (the words of the text survey, 2026-11-23: "1 gain × 1 Q" has no word to count any more)
    wrong = [w for w in ("1 filters", "1 filter rows", "1 filter counts", "1 EQs", "1 random starts", "they use")
             if any(w in t for t in found.values())]
    check("automatic settings: the whole text says “1 filter row”, “1 filter count”, “1 EQ”, “up to 1 filter”, "
          "“your 1 filter” and “it uses” (it said “1 filter rows”, “your 1 filters”)",
          not wrong and found["one row"] == "1 website EQ with 1 filter row"
          and found["one growing EQ"] == "1 EQ (1 gain × 1 Q): adds up to 4 filters one by one, stopping once it "
                                         "matches the target"
          and found["up to one"].startswith("1 EQ (1 gain × 1 Q): adds up to 1 filter one by one")
          and found["one EQ of 1"].startswith("1 EQ (1 filter count × 1 gain × 1 Q), ")
          and found["your one filter"] == "Evaluates the error of your 1 filter"
          # (2026-11-24: no period at the end: the tooltip of Settings to try showed "filters. · Est. time: ~3 s")
          and found["your one, adjusted"] == "Your 1 filter, adjusted once per limit set (1 gain × 1 Q); it uses all "
                                             "Moondrop Free DSP filters"
          and found["your one, adjusted, any"].endswith("; it uses all Parametric filters"), (wrong, found))


def test_whole_text_of_each_kind_of_run(check):
    # (the words of the text survey, 2026-11-23, with each part that shows only in some condition)
    two = MINE + "\n" + MINE.replace("100 Hz", "200 Hz")
    grown = _short_cfg(filter_counts=[2, 3], start_filters=two, layout="app:moondrop_free_dsp",
                       fight_penalty=[0.003, 0.01])
    lowest = dict(grown, scoring=dict(grown["scoring"], pick="lowest"))
    alone = _short_cfg(filter_counts=[2, 3], start_filters=two, start_keep=False, layout="app:moondrop_free_dsp")
    alone["best_fit"]["build"] = "scratch"
    fixed = _short_cfg(layout="graphic_10")
    found = {"grown": autoset.describe(grown), "lowest": autoset.describe(lowest), "alone": autoset.describe(alone),
             "fixed": autoset.describe(fixed)}
    from eq import engines, layouts
    lo, hi, step = layouts.sliders(fixed["best_fit"])
    check("automatic settings: the whole text of a run: EQs that add filters one by one (with 2 penalties, your "
          "filters and the limits of an EQ app; with and without the stop at the target), EQs from random starts, "
          "and the band gains of a graphic EQ",
          found == {"grown": "2 EQs (1 gain × 1 Q × 2 opposite-filter penalties): adds up to 3 filters one by one, "
                             "stopping once it matches the target, on top of your 2 filters, within Moondrop Free "
                             "DSP limits",
                    "lowest": "2 EQs (1 gain × 1 Q × 2 opposite-filter penalties): adds up to 3 filters one by one, "
                              "on top of your 2 filters, within Moondrop Free DSP limits",
                    "alone": f"{engines.fit_count(autoset.device_settings(alone['best_fit']), 2)} EQs (2 filter counts "
                             f"× 1 gain × 1 Q), {engines.RANDOM_STARTS} random starts each, on top of your 2 filters "
                             "(Best fit can adjust them), within Moondrop Free DSP limits",
                    "fixed": f"10-band graphic EQ: 10 band gains, {lo:g} to +{hi:g} dB ({step:g} dB steps)"}, found)


def test_time_is_short(check):
    found = [autoset.fmt_time(s) for s in (0.4, 20, 120, 7200)]
    check("automatic settings: the time of a run is “~1 s”, “~20 s”, “~2.0 min”, “~2.0 h”",
          found == ["~1 s", "~20 s", "~2.0 min", "~2.0 h"], found)


def test_limits_line_of_an_eq_app(check):
    from eq import layouts
    found = [layouts.summary(k) for k in ("app:roon", "app:hiby", "app:moondrop_free_dsp", "app:minidsp_il_dsp")]
    check("layouts: the line of an EQ app's limits in About these settings (no limit, filters of the two kinds, "
          "peaking filters, with shelves; gain, Q and frequency)",
          found == ["Roon (MUSE parametric EQ) limits: unlimited filters, gain -24 to +24 dB",
                    "HiBy Music (and HiBy devices) limits: up to 10 peaking/shelf filters, gain -12 to +12 dB, Q 0.2 "
                    "to 20, frequency 20 Hz to 20 kHz",
                    "Moondrop Free DSP limits: up to 9 peaking filters, gain -12 to +3 dB, Q 0.2 to 10, frequency "
                    "40 Hz to 10 kHz",
                    "miniDSP IL-DSP limits: up to 8 peaking filters + low/high shelves, gain -16 to +16 dB, Q 0.5 "
                    "to 6"], found)
