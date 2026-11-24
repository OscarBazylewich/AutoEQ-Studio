"""The EQ part's settings (eq\\settings.py): the defaults, settings of the wrong kind or past their limits put right,
settings.json read whatever it was saved as, kept aside when broken, waited for when another program has it open;
presets written whole; settings taken out of the app leaving an older copy's settings. Moved from eq_checks.py's
module_checks and removed_settings_checks."""
import json
import os
import types

import pytest

from eq import settings
from helpers.checks import raises  # (eq_checks.py's raises, line 50: the message of a ValueError, or None)


@pytest.fixture(scope="module")
def wrong_kinds():
    """Settings of every wrong kind and past every limit, put right (eq_checks.py lines 116-119)."""
    bad = {"mode": 3, "site": "x", "site_single": {"rows": 99, "q_min": 9, "q_max": 1}, "scoring": {"band_hz": [15000, 100]},
           "best_fit": {"filter_counts": list(range(-5, 500)), "gain_max": []}, "auto": {"level": "90", "manual": "x"},
           "files": {"excluded": "abc"}, "export": {"q_decimals": 1e9}, "site_sweep": {"gain_ranges": [[1, 2, 3]]}}
    return settings.with_auto(bad)


def test_defaults_valid(check):
    d = json.loads(json.dumps(settings.DEFAULTS))
    # was eq_checks.py:112
    check("settings: the defaults are valid as they are", settings.clamp(json.loads(json.dumps(d))) == d)


def test_every_path_has_a_default(check):
    # (the old check spoke only when a path was missing; here each path says ok, under the same name)
    for p in settings.ALL_AUTO_PATHS + list(settings.LIMITS):
        # was eq_checks.py:115
        check(f"settings: {p} exists in the defaults",
              not (settings.get_path(settings.DEFAULTS, p) is None and not settings.LIMITS.get(p, {}).get("empty")))


def test_wrong_kinds_go_back(wrong_kinds, check):
    c = wrong_kinds
    # was eq_checks.py:120
    check("settings: wrong kinds go back to the defaults",
          c["mode"] == "best_fit" and isinstance(c["site"], dict) and c["files"]["excluded"] == [] and "level" not in c["auto"], c)


def test_numbers_within_limits(wrong_kinds, check):
    c = wrong_kinds
    ceil = lambda p: settings.LIMITS[p]["max"]
    # was eq_checks.py:123
    check("settings: numbers kept within their limits", c["site_single"]["rows"] == ceil("site_single.rows")
          and c["export"]["q_decimals"] == ceil("export.q_decimals")
          and max(c["best_fit"]["filter_counts"]) == ceil("best_fit.filter_counts") and min(c["best_fit"]["filter_counts"]) == 1, c)


def test_pairs_in_order(wrong_kinds, check):
    c = wrong_kinds
    # was eq_checks.py:126
    check("settings: from/to pairs in order", all(not settings.pair_wrong(c, lo, hi, s) for lo, hi, s in settings.LIMIT_PAIRS))


def test_not_settings_at_all(check):
    # was eq_checks.py:127
    check("settings: something that isn't settings at all gives the defaults",
          all(settings.with_auto(x)["mode"] == "best_fit" for x in ("text", 5, [], None)))


# ---------------------------------------------------------------- what the user sets per EQ app (best_fit.per_app)
PER_APP = {"peace": {"bands": 31, "gain": 30}, "fxsound": {"band_counts": [10]}}


def _per(value):
    """best_fit.per_app as the settings make it valid."""
    return settings.with_auto({"best_fit": {"per_app": value}})["best_fit"]["per_app"]


def test_old_settings_get_the_per_app_defaults(check):
    old = settings.with_auto({"eq_app": "peace", "best_fit": {"layout": "app:peace", "filter_counts": [3, 5]}})
    check("settings: settings from before best_fit.per_app load with Peace at 31 bands and ±30 dB and FxSound at 10 "
          "bands, and keep their other values",
          old["best_fit"]["per_app"] == PER_APP and old["best_fit"]["filter_counts"] == [3, 5]
          and old["best_fit"]["layout"] == "app:peace" and old["eq_app"] == "peace"
          and settings.with_auto({})["best_fit"]["per_app"] == PER_APP, old["best_fit"]["per_app"])
    paths = ["best_fit.per_app.peace.bands", "best_fit.per_app.peace.gain", "best_fit.per_app.fxsound.band_counts"]
    check("settings: the limits of the per-app settings come from eq_apps; only the band counts of FxSound are automatic",
          [settings.LIMITS.get(p) for p in paths] == [
              {"min": 1, "max": 31, "int": True}, {"min": 1, "max": 99, "int": True, "unit": "dB"},
              {"min": 5, "max": 31, "int": True, "list": True, "of": [5, 10, 15, 20, 31]}]
          and [p for p in settings.ALL_AUTO_PATHS if ".per_app." in p] == paths[2:]
          and paths[2] in settings.AUTO_PATHS["best_fit"] and settings.AUTO_NAMES[paths[2]] == "Band counts"
          and not [p for p in paths[:2] if p in settings.AUTO_NAMES], [settings.LIMITS.get(p) for p in paths])


@pytest.mark.parametrize("name, value, want", [
    ("text", "x", PER_APP), ("nothing", None, PER_APP), ("a list", [], PER_APP), ("a switch", True, PER_APP),
    ("an app that is a number", {"peace": 3}, PER_APP),
    ("bands 0 and gain -5", {"peace": {"bands": 0, "gain": -5}}, dict(PER_APP, peace={"bands": 1, "gain": 1})),
    ("bands 500 and gain 1000", {"peace": {"bands": 500, "gain": 1000}}, dict(PER_APP, peace={"bands": 31, "gain": 99})),
    ("bands 10.6 and gain 12.5", {"peace": {"bands": 10.6, "gain": 12.5}}, dict(PER_APP, peace={"bands": 11, "gain": 13})),
    ("bands a switch and gain text", {"peace": {"bands": True, "gain": "12"}}, PER_APP),
    ("bands a list", {"peace": {"bands": [10], "gain": 12}}, dict(PER_APP, peace={"bands": 31, "gain": 12})),
    ("band counts text", {"fxsound": {"band_counts": "x"}}, PER_APP),
    ("band counts a number", {"fxsound": {"band_counts": 31}}, PER_APP),
    ("band counts 0 and 99", {"fxsound": {"band_counts": [0, 99]}}, PER_APP),
    ("band counts 12", {"fxsound": {"band_counts": [12]}}, PER_APP),
    ("band counts empty", {"fxsound": {"band_counts": []}}, PER_APP),
    ("band counts 31, 12, 5, 5 and text", {"fxsound": {"band_counts": [31, 12, 5, 5.0, "x"]}},
     dict(PER_APP, fxsound={"band_counts": [5, 31]})),
    ("valid values", {"peace": {"bands": 10, "gain": 12}, "fxsound": {"band_counts": [5, 10, 15, 20, 31]}},
     {"peace": {"bands": 10, "gain": 12}, "fxsound": {"band_counts": [5, 10, 15, 20, 31]}}),
])
def test_per_app_wrong_values_put_right(name, value, want, check):
    got = _per(value)
    check(f"settings: best_fit.per_app with {name} is put right (the default, the limit, or only the counts that "
          "the app offers)", got == want, got)


def test_per_app_keeps_an_unknown_app(check):
    got = _per({"later_app": {"bands": 7}, "peace": {"bands": 10, "later": 1}})
    check("settings: an app or a value under best_fit.per_app that this version does not know is kept",
          got == {"later_app": {"bands": 7}, "peace": {"bands": 10, "gain": 30, "later": 1}, "fxsound": {"band_counts": [10]}}, got)


def test_lists_without_of_as_before(check):
    # (the new limit flag "of" is in the one function every list setting goes through)
    c = settings.with_auto({"best_fit": {"filter_counts": [40, 3, 3, 0], "q_max": [2, 99], "gain_max": "x"},
                            "site_sweep": {"filter_rows": [2.4, 50]}})
    check("settings: lists of numbers without “of” are kept within their limits as before",
          c["best_fit"]["filter_counts"] == [1, 3, 32] and c["best_fit"]["q_max"] == [2, 27]
          and c["best_fit"]["gain_max"] == settings.DEFAULTS["best_fit"]["gain_max"]
          and c["site_sweep"]["filter_rows"] == [2, 20], (c["best_fit"]["filter_counts"], c["best_fit"]["q_max"]))


def test_old_preset_of_fxsound_loads(check):
    import textfile
    # a preset of before this setting: FxSound as the layout, the automatic settings on, no per_app
    old = {"mode": "best_fit", "eq_app": "fxsound", "best_fit": {"layout": "app:fxsound", "bands": {"gain_min": -12, "gain_max": 12, "step": 1}},
           "auto": {"enabled": True, "manual": ["best_fit.q_max", "best_fit.per_app.nope.band_counts"]}}
    os.makedirs(settings.PRESET_DIR, exist_ok=True)
    textfile.write_atomic(settings.preset_path("Selftest old fxsound"), json.dumps(old))
    try:
        p = settings.read_preset("Selftest old fxsound")
    finally:
        settings.delete_preset("Selftest old fxsound")
    check("presets: a preset of before best_fit.per_app with the layout FxSound loads: 10 bands, automatic, its own "
          "values kept",
          p["best_fit"]["layout"] == "app:fxsound" and p["eq_app"] == "fxsound"
          and p["best_fit"]["per_app"] == PER_APP and p["auto"]["manual"] == ["best_fit.q_max"]
          and p["best_fit"]["bands"]["step"] == 1, (p["best_fit"]["per_app"], p["auto"]))
    mine = settings.with_auto({"best_fit": {"per_app": {"fxsound": {"band_counts": [5, 31]}}},
                               "auto": {"enabled": True, "manual": ["best_fit.per_app.fxsound.band_counts"]}})
    check("settings: band counts that the user set stay a value of the user (auto.manual keeps the path)",
          mine["auto"]["manual"] == ["best_fit.per_app.fxsound.band_counts"]
          and mine["best_fit"]["per_app"]["fxsound"]["band_counts"] == [5, 31], mine["auto"])


def test_preset_needs_settings(check):
    # was eq_checks.py:129
    check("settings: a preset needs settings to save", raises(settings.save_preset, "x", "text") is not None)


@pytest.mark.parametrize("enc", ["utf-16", "utf-8-sig", "cp1252"])
def test_read_whatever_it_was_saved_as(enc, tmp_path, check):
    sp = os.path.join(tmp_path, "test settings.json")
    with open(sp, "w", encoding=enc) as fh:
        json.dump({"mode": "site_single"}, fh)
    # was eq_checks.py:134
    check(f"settings: settings.json read when saved as {enc}", settings.load(sp)["mode"] == "site_single")


def test_autoeq_method_becomes_best_fit(check):
    old = settings.with_auto({"mode": "autoeq", "autoeq": {"preset": "QUDELIX_5K"}})
    # was eq_checks.py:138
    check("settings: the AutoEq method's settings (taken out) become Best fit's", old["mode"] == "best_fit" and "autoeq" not in old)


def test_broken_file_kept_aside(tmp_path, check):
    import textfile
    sp = os.path.join(tmp_path, "test settings.json")
    with open(sp, "w", encoding="utf-8") as fh:
        fh.write('{"mode": "autoeq",')
    try:
        # was eq_checks.py:139
        check("settings: a broken settings.json gives the defaults and is kept as .bad",
              settings.load(sp)["mode"] == "best_fit" and os.path.exists(sp + ".bad"))
    finally:
        textfile.take_set_aside()  # (the notice it set aside for the window: no other test should see it)


def test_send_to_apo_settings_dropped(check):
    old = settings.with_auto({"export": {"apo_folder": "C:\\x", "apo_on_save": True, "apo_enable": True, "poweramp": True}})
    # was eq_checks.py:628
    check("settings: Send to Equalizer APO's old settings are dropped (the rest kept)",
          not any(k.startswith("apo_") for k in old["export"]) and old["export"]["poweramp"] is True, old["export"])


def test_locked_file_said_and_kept(tmp_path, monkeypatch, check):
    import textfile
    sp = os.path.join(tmp_path, "locked settings.json")
    settings.save(settings.with_auto({"scoring": {"ear_db": 0.3}}), sp)
    msg = ""
    with monkeypatch.context() as m:
        # (the file in use: its reading refused; settings' waits made instant. Only settings' own time is stood in
        # for, not every thread's, as the old check did with time.sleep)
        m.setattr(textfile, "read", lambda p: (_ for _ in ()).throw(PermissionError(13, "The file is in use")))
        m.setattr(settings, "time", types.SimpleNamespace(sleep=lambda s: None, time=settings.time.time,
                                                          monotonic=settings.time.monotonic))
        try:
            settings.load(sp)
        except OSError as err:
            msg = str(err)
    # was eq_checks.py:761
    check("settings: a locked settings.json says so and stays (not moved to .bad for the defaults)",
          "a different program has it open" in msg and os.path.exists(sp) and not os.path.exists(sp + ".bad")
          and settings.load(sp)["scoring"]["ear_db"] == 0.3, msg)


def test_presets_written_in_one_step(monkeypatch, check):
    import textfile
    writes, real_write = [], textfile.write_atomic
    monkeypatch.setattr(textfile, "write_atomic", lambda p, text, **k: (writes.append(p), real_write(p, text, **k)))
    settings.save_preset("Selftest atomic", settings.DEFAULTS)
    monkeypatch.undo()
    try:
        # was eq_checks.py:772
        check("presets: written in one step (never a cut-off preset)", writes == [settings.preset_path("Selftest atomic")],
              writes)
    finally:
        settings.delete_preset("Selftest atomic")


def test_preset_name_that_cleans_to_nothing(check):
    # was eq_checks.py:774
    check("presets: a name that cleans down to nothing is refused (was saved over \"preset\")",
          raises(settings.preset_path, "..") == "Give the preset a name." and raises(settings.preset_path, " . ") is not None)


def test_removed_settings_leave_older_copies(check):
    old = settings.with_auto({"app": {"browser": "auto", "window": "tab"},
                              "best_fit": {"build": "scratch", "random_starts": 5, "seed_with_site": True},
                              "scoring": {"pick": "simplest", "tolerance_db": 0.2}})
    kept = settings.with_auto({"best_fit": {"gain_penalty": 0.001, "high_shelf": True},
                               "scoring": {"priority": ["max_q", "n_filters", "max_boost"]}})
    gone = ["app" in old, *(k in old["best_fit"] for k in ("build", "random_starts", "seed_with_site")),
            "tolerance_db" in old["scoring"]]
    # was eq_checks.py:2173
    check("settings: the removed ones leave an older copy's settings (the old pick becomes the audible one); the hidden "
          "ones still work",
          not any(gone) and old["scoring"]["pick"] == "audible" and kept["best_fit"]["gain_penalty"] == 0.001
          and kept["best_fit"]["high_shelf"] is True and kept["scoring"]["priority"][0] == "max_q", (gone, old["scoring"]))
