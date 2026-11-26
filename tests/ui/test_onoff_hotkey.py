"""The on/off hotkey on the window and in the tray (2026-10-26): Settings' row (the key as saved, None, Level-matched
ticked to start with and saved when changed, its words; a key Windows refused said as a warning), Devices while a
device's EQ is off for now (its line, the note with Switch it back on, no APO check meanwhile), and the app's side
(ui\\app.py, with stand-ins for its tray: what the notices say, and the tray menu's "EQ off for now, to compare"
item with the key, ticked while it's off). On the ui folder's window (tests\\ui\\conftest.py: a stand-in APO folder
and devices); the switcher's side is tests\\switcher\\test_compare_off.py."""
import types

import pytest

KEY = "Headset|EarPods"


def test_settings_row(devices_window, check):
    # (the first test of the file, on the window's new settings file: so it also holds the defaults of a new copy,
    # switcher.core.DEFAULTS. A test of DEFAULTS alone went in the test audit of 2026-11-25: a default changed fails
    # this one too. A test put before it must leave the hotkey and Level-matched as it found them)
    from PySide6.QtWidgets import QLineEdit
    from ui import help_window
    w = devices_window
    win = w.win
    win.render_settings()
    seq = win.onoff_edit.keySequence().toString()
    matched = win.chk_matched.isChecked()
    emitted = []
    win.onoff_hotkey_changed.connect(emitted.append)
    try:
        # (the box's own ✕, as a click on it does: its text box emptied; the UI audit, 2026-11-08: no Clear button)
        win.onoff_edit.findChild(QLineEdit).clear()
        win.chk_matched.setChecked(False)
        saved = w.sw.s.get("onoff_matched")
    finally:
        win.onoff_hotkey_changed.disconnect(emitted.append)
        w.sw.set("onoff_matched", True)
        win.render_settings()
    check("onoff: Settings shows the on/off hotkey as saved (Ctrl+Alt+Space to start with) and Level-matched ticked; "
          "the ✕ in its box asks for no key (once); Level-matched unticked is saved; each has its Help entry",
          seq == "Ctrl+Alt+Space" and matched and emitted == [""] and saved is False
          and help_window.entry_of_widget(win.onoff_edit) and help_window.entry_of_widget(win.chk_matched),
          (seq, matched, emitted, saved))


def test_a_refused_key_said_as_a_warning(devices_window, check):
    w = devices_window
    w.app.onoff_problem = "Windows didn't take Ctrl+Alt+Space as a hotkey: another program may use it."
    try:
        w.win.render_settings()
        said = (w.win.onoff_note.text(), w.win.onoff_note.property("role"))
    finally:
        del w.app.onoff_problem
        w.win.render_settings()
    # (the UI audit, 2026-11-08: under its box only a problem; the ⓘ after its label went with the text survey,
    # 2026-11-24: tests\ui\test_settings_screen.py checks that)
    check("onoff: a key Windows refused is said under its box in the warning colour, and goes after",
          said[0].startswith("Windows didn't take") and said[1] == "warn" and w.win.onoff_note.isHidden(), said)


@pytest.fixture
def on_device(devices_window):
    """A profile switched on for the playing stand-in device (the window's own switcher), taken off after."""
    import os
    w = devices_window
    path = os.path.join(w.top, "Compare me.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("Preamp: -3 dB\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n")
    pid = w.sw.import_profile(path, "Compare me")
    w.sw.add_to_device(KEY, pid, switch_on=True)
    yield w
    w.sw.compare_end()
    w.sw.remove_profile(pid)


def test_devices_while_off_for_now(on_device, qapp, check):
    from PySide6.QtWidgets import QLabel, QPushButton
    w = on_device
    win = w.win
    win.show_page("devices", remember=False)
    win.selected = KEY
    w.sw.compare_toggle(KEY)
    win.render_all()
    qapp.processEvents()  # (the panel made again: shown once Qt has laid it out)
    # (2026-10-27, UI-RULES 23: a bar at the window's top, as a trial's, says it; a card inside Devices' EQ card did)
    words = f"{win.compare_title.text()}: {win.compare_text.text()}" if win.compare_holder.isVisibleTo(win) else ""
    back = next((b for b in win.compare_bar.findChildren(QPushButton) if b.text() == "Enable it again"), None)
    card_gone = not any(lab.text().startswith("Its EQ is off for now") for lab in
                        win.pages["devices"].findChildren(QLabel) if lab.isVisibleTo(win))  # (the old card's words)
    line = win._device_state(KEY)[1] if hasattr(win, "_device_state") else ""
    no_check = win.check_label is None
    # (with no on/off hotkey, the line ends after how the EQ is off: no sentence about a key)
    hotkey = w.sw.s.get("onoff_hotkey")
    w.sw.s["onoff_hotkey"] = ""
    try:
        win.render_compare()
        no_key = win.compare_text.text()
    finally:
        w.sw.s["onoff_hotkey"] = hotkey
        win.render_compare()
    back.click()
    win.render_all()
    check("onoff: a bar at the window's top says a device's EQ is off for now (how, the key, Switch it back on), as a "
          "trial's does, and Devices its line, with no APO check meanwhile; Switch it back on ends it",
          words.startswith("EQ off, to compare: Headset (EarPods): ")
          and words.endswith(". Press Ctrl+Alt+Space to turn EQ back on.") and back is not None
          and no_key and words == f"EQ off, to compare: {no_key} Press Ctrl+Alt+Space to turn EQ back on."
          and line == "Compare: EQ off"
          and no_check and card_gone and w.sw.compare is None and not win.compare_holder.isVisibleTo(win),
          (line, words[:300], no_key, no_check, card_gone))


def test_the_apps_notices(check):
    from ui.app import App
    said = []
    sw = types.SimpleNamespace(s={"onoff_hotkey": "Ctrl+Alt+Space", "notify": True}, compare=None)
    fake = types.SimpleNamespace(sw=sw, tray_message=lambda title, text: said.append((title, text)))
    fake.compare_text = lambda got: App.compare_text(fake, got)
    off = App.compare_text(fake, ("off", {"matched": True, "db": -4.2, "louder": False, "complete": True}))
    plain = App.compare_text(fake, ("off", {"matched": False, "db": None, "louder": False, "complete": True}))
    louder = App.compare_text(fake, ("off", {"matched": True, "db": 0.0, "louder": True, "complete": False}))
    on = App.compare_text(fake, ("on", "Daily"))
    on_none = App.compare_text(fake, ("on", None))
    sw.s["onoff_hotkey"] = ""
    no_key = App.compare_text(fake, ("off", {"matched": False, "db": None, "louder": False, "complete": True}))
    sw.s["onoff_hotkey"] = "Ctrl+Alt+Space"
    rec = {"label": "Headset", "profiles": [], "active": None}
    sw.playing = lambda: (KEY, rec)
    sw.compare_toggle = lambda key: None
    App.on_onoff(fake)
    App.on_hotkey(fake)  # (the other hotkey on the same device: the same words)
    check("onoff: the notices say what happened: off for now level-matched (by how much), truly off, an EQ louder than "
          "none (it can't be matched) and one that can't be fully measured, back on (its name); a device with nothing "
          "to switch says how to give it one",
          off == "EQ off to compare (4.2 dB lower). Press Ctrl+Alt+Space to turn back on."
          and plain == "EQ off to compare. Press Ctrl+Alt+Space to turn back on."
          and louder == ("EQ off to compare. Press Ctrl+Alt+Space to turn back on. Level match skipped to avoid "
                         "clipping. (Approximate level match: some filters couldn't be measured.)")
          and no_key == "EQ off to compare. Press the on/off hotkey to turn back on."
          and on == "EQ on: Daily" and on_none == "EQ on"
          and [text for _, text in said] == ["No profiles for this device. Open Devices to add one."] * 2,
          (off, plain, louder, no_key, on, on_none, said))


def test_no_number_when_the_level_match_is_skipped(check):
    # (the owner, 2026-11-25: an EQ louder than none isn't level-matched, so the notice has no "(… dB lower)"; one
    # quieter than none keeps its number, also 0.0 dB)
    from ui.app import App
    fake = types.SimpleNamespace(sw=types.SimpleNamespace(s={"onoff_hotkey": "Ctrl+Alt+Space"}))
    skipped = App.compare_text(fake, ("off", {"matched": True, "db": 0.0, "louder": True, "complete": True}))
    matched = App.compare_text(fake, ("off", {"matched": True, "db": -2.0, "louder": False, "complete": True}))
    same = App.compare_text(fake, ("off", {"matched": True, "db": 0.0, "louder": False, "complete": True}))
    check("onoff: the notice of an EQ louder than none has no “dB lower” (its level match skipped); a matched one "
          "says by how much",
          skipped == "EQ off to compare. Press Ctrl+Alt+Space to turn back on. Level match skipped to avoid clipping."
          and matched == "EQ off to compare (2.0 dB lower). Press Ctrl+Alt+Space to turn back on."
          and same == "EQ off to compare (0.0 dB lower). Press Ctrl+Alt+Space to turn back on.",
          (skipped, matched, same))


def test_the_tray_menu_item(on_device, qapp, check):
    from PySide6.QtWidgets import QMenu
    from ui.app import App
    w = on_device
    fake = types.SimpleNamespace(sw=w.sw, menu=QMenu(), win=w.win, on_onoff=lambda: w.sw.compare_toggle(KEY),
                                 end_trial=lambda keep=False: None, switch=lambda key, pid: None, quit=lambda: None)
    try:
        App.build_menu(fake)
        item = next(a for a in fake.menu.actions() if a.text().startswith("EQ off, to compare"))
        before = (item.text(), item.isCheckable(), item.isChecked())
        item.trigger()
        App.build_menu(fake)
        after = next(a for a in fake.menu.actions() if a.text().startswith("EQ off, to compare")).isChecked()
    finally:
        from PySide6.QtCore import QCoreApplication, QEvent
        w.sw.compare_end()
        fake.menu.deleteLater()  # (now: its actions' call-backs hold the stand-in, a loop the collector would find)
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    check("onoff: the tray menu has “EQ off for now, to compare” with the key beside it; chosen, the device's EQ is off "
          "for now and the item ticked",
          before == ("EQ off, to compare\tCtrl+Alt+Space", True, False) and after, (before, after))
