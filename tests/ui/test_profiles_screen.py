"""Profiles (the window's profiles screen, ui\\window.py; ui\\profiles_screen.py once the window is split): every
profile listed. Moved from selftest.py's qt_checks: after Set up (tests\\ui\\conftest.py's set_up_window), the two
EQ files config.txt used are the two profiles."""


def test_the_profiles_list(set_up_window, check):
    win = set_up_window.win
    win.render_all()
    names = [win.prof_table.item(r, 0).text() for r in range(win.prof_table.rowCount())]
    # was selftest.py:593
    check("window: the profiles list", win.prof_table.rowCount() == 2, names)
