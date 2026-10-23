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
          "another program has it open" in msg and os.path.exists(sp) and not os.path.exists(sp + ".bad")
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
