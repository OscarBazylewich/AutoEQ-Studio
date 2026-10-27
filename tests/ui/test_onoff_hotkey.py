"""The on/off hotkey on the window and in the tray (2026-10-26): Settings' row (the key as saved, None, Level-matched
ticked to start with and saved when changed, its words; a key Windows refused said as a warning), Devices while a
device's EQ is off for now (its line, the note with Switch it back on, no APO check meanwhile), and the app's side
(ui\\app.py, with stand-ins for its tray: what the notices say, and the tray menu's "EQ off for now, to compare"
item with the key, ticked while it's off). On the ui folder's window (tests\\ui\\conftest.py: a stand-in APO folder
and devices); the switcher's side is tests\\switcher\\test_compare_off.py."""
import types

import pytest

from switcher import core

KEY = "Headset|EarPods"


def test_settings_row(devices_window, check):
    from PySide6.QtWidgets import QPushButton
    from ui import help_window
    w = devices_window
    win = w.win
    win.render_settings()
    seq = win.onoff_edit.keySequence().toString()
    matched = win.chk_matched.isChecked()
    emitted = []
    win.onoff_hotkey_changed.connect(emitted.append)
    try:
        none = next(b for b in win.pages["settings"].findChildren(QPushButton)
                    if b.accessibleName() == "No hotkey to switch the EQ off and on")
        none.click()
        win.chk_matched.setChecked(False)
        saved = w.sw.s.get("onoff_matched")
    finally:
        win.onoff_hotkey_changed.disconnect(emitted.append)
        w.sw.set("onoff_matched", True)
        win.render_settings()
    check("onoff: Settings shows the on/off hotkey as saved (Ctrl+Alt+Space to start with) and Level-matched ticked; "
          "None asks for no key; Level-matched unticked is saved; each has its Help entry",
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
    check("onoff: a key Windows refused is said in the warning colour, and the note is quiet again after",
          said[0].startswith("Windows didn't take") and said[1] == "warn" and w.win.onoff_note.property("role") == "muted",
          said)


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
    words = " ".join(lab.text() for lab in win.pages["devices"].findChildren(QLabel) if lab.isVisible())
    back = next((b for b in win.pages["devices"].findChildren(QPushButton) if b.text() == "Switch it back on"), None)
    line = win._status(KEY)[1] if hasattr(win, "_status") else ""
    no_check = win.check_label is None
    back.click()
    win.render_all()
    check("onoff: Devices says a device's EQ is off for now (its line, a note with how and the key, Switch it back on, "
          "no APO check meanwhile); Switch it back on ends it",
          "off for now" in words and "Ctrl+Alt+Space" in words and back is not None and line == "EQ off for now (comparing)"
          and no_check and w.sw.compare is None, (line, words[:300], no_check))


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
    rec = {"label": "Headset", "profiles": [], "active": None}
    sw.playing = lambda: (KEY, rec)
    sw.compare_toggle = lambda key: None
    App.on_onoff(fake)
    check("onoff: the notices say what happened: off for now level-matched (by how much), truly off, an EQ louder than "
          "none (it can't be matched) and one that can't be fully measured, back on (its name); a device with nothing "
          "to switch says how to give it one",
          "turned down 4.2 dB" in off and "Ctrl+Alt+Space switches it back on" in off and plain.startswith("EQ off for now.")
          and "can't be raised to match" in louder and "can't be measured" in louder and on == "EQ back on: Daily"
          and said and "add a profile" in said[-1][1], (off, plain, louder, on, said))


def test_the_tray_menu_item(on_device, qapp, check):
    from PySide6.QtWidgets import QMenu
    from ui.app import App
    w = on_device
    fake = types.SimpleNamespace(sw=w.sw, menu=QMenu(), win=w.win, on_onoff=lambda: w.sw.compare_toggle(KEY),
                                 end_trial=lambda keep=False: None, switch=lambda key, pid: None, quit=lambda: None)
    try:
        App.build_menu(fake)
        item = next(a for a in fake.menu.actions() if a.text().startswith("EQ off for now, to compare"))
        before = (item.text(), item.isCheckable(), item.isChecked())
        item.trigger()
        App.build_menu(fake)
        after = next(a for a in fake.menu.actions() if a.text().startswith("EQ off for now")).isChecked()
    finally:
        from PySide6.QtCore import QCoreApplication, QEvent
        w.sw.compare_end()
        fake.menu.deleteLater()  # (now: its actions' call-backs hold the stand-in, a loop the collector would find)
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    check("onoff: the tray menu has “EQ off for now, to compare” with the key beside it; chosen, the device's EQ is off "
          "for now and the item ticked",
          before == ("EQ off for now, to compare\tCtrl+Alt+Space", True, False) and after, (before, after))


def test_defaults(check):
    check("onoff: a new copy's on/off hotkey is Ctrl+Alt+Space, level-matched",
          core.DEFAULTS["onoff_hotkey"] == "Ctrl+Alt+Space" and core.DEFAULTS["onoff_matched"] is True)
