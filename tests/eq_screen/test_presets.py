"""Make an EQ's Presets ▾ (ui\\eq_page.py: save_preset, fill_presets, load_preset, delete_preset, reset_settings):
the settings saved under a name (not your files), listed, loaded (Undo puts the ones before back), deleted; Reset
all settings with its Undo. Moved from eq_checks.py's preset_checks (lines 2120-2159), on a page opened as the old
checks opened it (the eq_screen fixture). Delete and Reset ask first: answered Yes by the tests' dialogs
(helpers.dialogs), as the old checks' message boxes were."""
import json
import os

import pytest

from helpers import qt


@pytest.fixture(scope="module", autouse=True)
def settled(eq_screen):
    """After the file's last test, the page's background work finished before the eq_screen fixture closes it: each
    load that ends starts the next in the background (the curves, their analysis, the automatic settings), and one
    still on its way once the page is deleted answers a page that's gone (an error inside a Qt call-back, "Internal
    C++ object already deleted"). Quiet for half a second: nothing running, nothing new started."""
    yield
    from PySide6.QtCore import QThreadPool
    idle = {"n": 0}

    def quiet():
        idle["n"] = idle["n"] + 1 if QThreadPool.globalInstance().activeThreadCount() == 0 else 0
        return idle["n"] >= 25
    qt.wait_for(quiet, 30)


def test_presets(eq_screen, monkeypatch, check):
    from PySide6.QtWidgets import QInputDialog, QMenu
    from eq import paths as eq_paths
    page = eq_screen.page
    S = page.S
    was_all = json.loads(json.dumps(S))
    was_mode, was_files = S["mode"], json.dumps(S["files"])
    with monkeypatch.context() as m:  # (the name asked for: "Check preset")
        m.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Check preset", True)))
        page.save_preset()
    saved = os.path.exists(os.path.join(eq_paths.PRESET_DIR, "Check preset.json"))
    menu = QMenu()
    page.fill_presets(menu)
    listed = [a.text() for a in menu.actions()]
    page.S["mode"] = "site_single" if was_mode != "site_single" else "best_fit"
    page.changed()
    page.load_preset("Check preset")
    loaded = (page.S["mode"], json.dumps(page.S["files"]), page.mode_combo.currentData())
    page.notice_undo.click()
    undone = page.S["mode"]
    page.load_preset("Check preset")
    page.delete_preset("Check preset")
    gone = not os.path.exists(os.path.join(eq_paths.PRESET_DIR, "Check preset.json"))
    page.S["best_fit"]["q_min"] = 0.7
    page.reset_settings()
    reset = page.S["best_fit"]["q_min"] != 0.7 and json.dumps(page.S["files"]) == was_files
    page.notice_undo.click()
    reset_undone = page.S["best_fit"]["q_min"] == 0.7
    # was eq_checks.py:2152
    check("presets: Presets ▾ saves the settings (not the files) under a name, lists it, loads it (Undo puts the ones "
          "before back), deletes it; Reset all settings, with its Undo",
          saved and "Check preset" in listed and "Save current settings as…" in listed
          and loaded == (was_mode, was_files, was_mode) and undone != was_mode and gone and reset and reset_undone,
          (saved, listed, loaded, undone, gone, reset, reset_undone))
    page.S = was_all  # (the settings as they were)
    page.changed(curves=True)
    eq_screen.wait_for(lambda: page.curves is not None, 30)
