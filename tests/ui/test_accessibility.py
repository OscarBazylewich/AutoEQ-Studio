"""Accessibility on the window's screens (Devices, Profiles, Settings): every control has a name a screen reader
reads, and Tab reaches it (app\\tools\\a11y.py). Moved from selftest.py's qt_checks.

The window as the old check saw it: after Set up, with one profile on the device, switched off
(tests\\ui\\conftest.py's set_up_window, then Off). Unthemed, as there: the theme names a symbol button by its tooltip
for a screen reader once it has been applied in a process, which would let this check pass more easily; so no test
in this folder applies the theme in this process (the theme's tests do it in a Python of their own).
"""
import pytest

from helpers import paths

COVERS = ("a11y",)  # (app\tools\a11y.py, imported by its name through helpers.paths.import_tool)


def test_every_control_named_and_reachable(set_up_window, check, qapp):
    if qapp.styleSheet():
        pytest.fail("The app's theme was applied in this test process before the accessibility check: the theme's "
                    "automatic names would make the check laxer than the old one. Apply it in a Python of its own.")
    a11y = paths.import_tool("a11y")
    w = set_up_window
    win, sw = w.win, w.sw
    sw.set_active(w.key, None)  # (the device's EQ off: its one profile still on it)
    qapp.processEvents()
    gaps = {}
    try:
        for page_key in ("devices", "profiles", "settings"):
            win.show_page(page_key, remember=False)
            qapp.processEvents()
            u, r = a11y.unnamed(win), a11y.unreachable(win)
            if u or r:
                gaps[page_key] = ([f"{x[0]}:{x[1] or x[2][:16]}" for x in u], [f"{x[0]}:{x[1]}" for x in r])
    finally:
        win.show_page("devices", remember=False)
    # was selftest.py:588
    check("access: on Devices, Profiles and Settings every control has a name a screen reader reads, and Tab "
          "reaches it", not gaps, gaps)
