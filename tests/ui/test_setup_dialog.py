"""Set up (ui\\window.py's SetUpDialog; ui\\setup_dialog.py once the window is split): config.txt's EQ files added as
profiles, the one on now becoming the playing device's EQ, and EQ Switcher's Start with Windows turned off and EQ
Switcher asked to quit (both stand-ins here: tests\\ui\\conftest.py's set_up_window, which runs the dialog once for
this file). Moved from selftest.py's qt_checks."""

KEY = "Headset|EarPods"


def test_setting_up_adds_the_eq_files(set_up_window, check):
    w = set_up_window
    sw, rec = w.sw, w.sw.record(KEY)
    # was selftest.py:394
    check("window: setting up adds config.txt's EQ files, the one on now becoming the playing device's",
          len(sw.profiles()) == 2 and [sw.profile_name(i) for i in rec["profiles"]] == ["EarPods"]
          and rec["active"] == rec["profiles"][0] and sw.apo.set_up() and not w.win.banner.isVisible(),
          (sw.profiles(), rec, w.warnings))


def test_eq_switcher_turned_off_and_quit(set_up_window, check):
    w = set_up_window
    # was selftest.py:398
    check("window: Set up offers to turn off EQ Switcher's Start with Windows and to quit it (both ticked), and does "
          "both", w.offered == (True, True) and w.done_es == ["Start with Windows off", "quit"], (w.offered, w.done_es))
