"""Make an EQ's Presets (ui\\eq_page.py: save_preset, fill_presets, load_preset, delete_preset, use_initial_settings):
the settings saved under a name (not your files), listed, loaded (Undo puts the ones before back), deleted; Reset
all settings with its Undo. Moved from eq_checks.py's preset_checks (lines 2120-2159), on a page opened as the old
checks opened it (the eq_screen fixture). Delete and Reset ask first: answered Yes by the tests' dialogs
(helpers.dialogs), as the old checks' message boxes were."""
import json
import os


def test_presets(eq_screen, monkeypatch, check):
    from PySide6.QtWidgets import QMenu
    from ui import window_parts
    from eq import paths as eq_paths
    page = eq_screen.page
    S = page.S
    was_all = json.loads(json.dumps(S))
    was_mode, was_files = S["mode"], json.dumps(S["files"])
    with monkeypatch.context() as m:  # (the name asked for: "Check preset")
        m.setattr(window_parts, "ask_text", lambda *a, **k: ("Check preset", True))
        page.save_preset()
    saved = os.path.exists(os.path.join(eq_paths.PRESET_DIR, "Check preset.json"))
    menu = QMenu()
    page.fill_presets(menu)
    listed = [a.text() for a in menu.actions()]
    page.S["mode"] = "site_single" if was_mode != "site_single" else "best_fit"
    page.changed()
    page.load_preset("Check preset")
    loaded = (page.S["mode"], json.dumps(page.S["files"]), page.mode_combo.currentData())
    eq_screen.undo()  # (the message line's Undo)
    undone = page.S["mode"]
    page.load_preset("Check preset")
    page.delete_preset("Check preset")
    gone = not os.path.exists(os.path.join(eq_paths.PRESET_DIR, "Check preset.json"))
    page.S["best_fit"]["q_min"] = 0.7
    page.use_initial_settings()
    reset = page.S["best_fit"]["q_min"] != 0.7 and json.dumps(page.S["files"]) == was_files
    eq_screen.undo()  # (the message line's Undo)
    reset_undone = page.S["best_fit"]["q_min"] == 0.7
    # was eq_checks.py:2152
    check("presets: Presets ▾ saves the settings (not the files) under a name, lists it, loads it (Undo puts the ones "
          "before back), deletes it; Reset all settings, with its Undo",
          saved and "Check preset" in listed and "Save as a preset…" in listed
          and loaded == (was_mode, was_files, was_mode) and undone != was_mode and gone and reset and reset_undone,
          (saved, listed, loaded, undone, gone, reset, reset_undone))
    page.S = was_all  # (the settings as they were)
    page.changed(curves=True)
    eq_screen.wait_for(lambda: page.curves is not None, 30)


def test_presets_menu_changes_no_file(eq_screen, check):
    # (2026-11-10, a code review: to find the preset in use, the menu loaded each preset the way a click does, and a
    # load saves the preset as settings.json: each opening of Presets left the last preset there, while the page kept
    # its own settings)
    from PySide6.QtWidgets import QMenu
    from eq import settings as eq_settings
    from helpers import qt
    page = eq_screen.page
    other = json.loads(json.dumps(page.S))
    other["mode"] = "site_single" if page.S["mode"] != "site_single" else "best_fit"
    eq_settings.save_preset("Check in use", page.S)
    eq_settings.save_preset("Check zz other", other)  # (last in the list: what settings.json became)
    eq_settings.save(page.S)
    menu = QMenu(page)
    try:
        with open(eq_settings.PATH, "rb") as f:
            before = f.read()
        page.fill_presets(menu)
        with open(eq_settings.PATH, "rb") as f:
            after = f.read()
        marks = {a.text(): a.isChecked() for a in menu.actions() if a.text().startswith("Check ")}
    finally:
        qt.close(menu)
        eq_settings.delete_preset("Check in use")
        eq_settings.delete_preset("Check zz other")
    check("presets: opening the Presets menu leaves settings.json as it was, byte for byte (it saved each preset "
          "there in turn), and the mark is still at the preset with the settings in use",
          after == before and marks == {"Check in use": True, "Check zz other": False},
          (after == before, marks, len(before), len(after)))
