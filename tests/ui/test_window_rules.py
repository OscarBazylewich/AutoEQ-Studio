"""The window's screens by the UI rules (2026-10-27; the rules are .claude\\notes\\UI-RULES.md, on the developer's
PC): the tray menu's order (Open first, Quit last, a trial's words as its bar's), a profile taken off a device with
Undo (back in its place, on only if it was), Online / Offline one width either way, the banner's website asked for
while offline said in the window's line, Settings' hotkeys lined up as a form, and deleting a profile asked with No
the default. On the ui folder's window (tests\\ui\\conftest.py's devices_window: a stand-in APO folder and
devices)."""
import os
import time
import types

from helpers import qt

KEY = "Headset|EarPods"


def _profile(w, name):
    path = os.path.join(w.top, name + ".txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("Preamp: -3 dB\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n")
    return w.sw.import_profile(path, name)


def test_the_tray_menu_open_first_quit_last(devices_window, check):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QMenu
    from ui.app import App
    w = devices_window
    fake = types.SimpleNamespace(sw=w.sw, menu=QMenu(), win=w.win, on_onoff=lambda: None,
                                 end_trial=lambda keep=False: None, switch=lambda key, pid: None, quit=lambda: None)
    try:
        App.build_menu(fake)
        items = [a.text() for a in fake.menu.actions() if not a.isSeparator()]
        default = fake.menu.defaultAction().text() if fake.menu.defaultAction() else None
        w.sw.trial = {"key": KEY, "name": "Bright", "until": time.time() + 200}
        App.build_menu(fake)
        trial = [a.text() for a in fake.menu.actions() if not a.isSeparator()]
    finally:
        w.sw.trial = None
        fake.menu.deleteLater()  # (now: its actions' call-backs hold the stand-in, a loop the collector would find)
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    check("tray: Open AutoEQ Studio first and in bold (the icon's own click, as Windows' tray menus), Quit alone at the "
          "end; a trial's items say Keep it and Stop now, as its bar does",
          items[:1] == ["Open AutoEQ Studio"] and default == "Open AutoEQ Studio" and items[-1:] == ["Quit"]
          and "Keep it" in trial and "Stop now" in trial and "Stop trying" not in trial, (items, default, trial))


def test_a_profile_taken_off_a_device_comes_back_with_undo(devices_window, qapp, check):
    from PySide6.QtWidgets import QToolButton
    w = devices_window
    win, sw = w.win, w.sw
    first, second = _profile(w, "First"), _profile(w, "Second")
    sw.add_to_device(KEY, first, switch_on=False)
    sw.add_to_device(KEY, second, switch_on=False)
    sw.set_active(KEY, None)
    before = list(sw.record(KEY)["profiles"])
    try:
        win.show_page("devices", remember=False)
        win.render_all()
        qapp.processEvents()

        def cross(name):
            return next((b for b in win.dev_panel.findChildren(QToolButton)
                         if b.accessibleName() == f"Remove {name} from this device"), None)
        cross("First").click()
        off = (first in sw.record(KEY)["profiles"], win.message.text.text(), win.message.undo_btn.isVisibleTo(win))
        win.message.undo_btn.click()
        back = (sw.record(KEY)["profiles"] == before, sw.record(KEY)["active"], win.message.text.text())
        # (a profile deleted in Profiles meanwhile: Undo says so, and puts nothing back)
        win.render_all()
        qapp.processEvents()
        cross("Second").click()
        sw.remove_profile(second)
        win.message.undo_btn.click()
        gone = win.message.text.text()
    finally:
        for pid in (first, second):
            sw.remove_profile(pid)
        win.render_all()
    check("devices: a profile's ✕ removes it from the device and says so with Undo in the window's line; Undo puts it "
          "back in its place, the device's EQ as it was (Off stays off); deleted meanwhile, Undo says so",
          off == (False, "Removed “First” from this device.", True) and back == (True, None, "")
          and "deleted meanwhile" in gone, (off, back, before, gone))


def test_online_offline_one_width(devices_window, online, check):
    import net
    win = devices_window.win
    qt.pump(30)
    on = win.online_btn.geometry()
    win.online_btn.click()
    qt.pump(30)
    off = (win.online_btn.geometry(), net.offline())
    win.online_btn.click()
    qt.pump(30)
    check("window: Online / Offline is as wide either way, its words whole (the buttons beside it stay put as it's "
          "switched)", off == (on, True) and win.online_btn.width() >= win.online_btn.sizeHint().width(), (on, off))


def test_the_banners_website_offline_said_in_the_line(devices_window, monkeypatch, check):
    import net
    from PySide6.QtGui import QDesktopServices
    from switcher.apo import Apo
    win = devices_window.win
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url)))
    monkeypatch.setattr(Apo, "found", property(lambda self: False))
    win.show_page("devices", remember=False)
    win.render_banner()
    b = win.banner_btn
    look = (b.text(), b.isEnabled(), b.icon().isNull(), b.property("primary"))
    b.click()
    said = win.message.text.text()
    monkeypatch.undo()
    win.render_all()
    check("window: the banner's Get Equalizer APO is plain, with its symbol (a notice's action), and stays on while "
          "offline: clicked, it says so in the window's line, nothing opened",
          net.offline() and look == ("Get Equalizer APO", True, False, None) and opened == []
          and said == "Offline: switch to Online (top right) to open websites.", (look, said, opened))


def test_settings_hotkeys_lined_up_as_a_form(devices_window, check):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QPushButton
    win = devices_window.win
    win.show_page("settings", remember=False)
    qt.pump(30)
    try:
        boxes = [e.mapTo(win, QPoint(0, 0)).x() for e in (win.hotkey_edit, win.onoff_edit, win.chk_matched)]
        clears = sorted(b.accessibleName() for b in win.pages["settings"].findChildren(QPushButton)
                        if b.text() == "Clear")
    finally:
        win.show_page("devices", remember=False)
    check("settings: the two hotkeys as a form, their boxes lined up in one column (Level-matched under them), each "
          "with a Clear named for its hotkey",
          len(set(boxes)) == 1 and clears == ["Clear the hotkey to switch the EQ off and on",
                                              "Clear the hotkey to switch the playing device's EQ"], (boxes, clears))


def test_deleting_a_profile_asks_with_no_the_default(devices_window, monkeypatch, check):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox
    w = devices_window
    win = w.win
    pid = _profile(w, "Delete me")
    asked = []
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: asked.append(a) or QMessageBox.No))
    try:
        win.render_all()
        t = win.prof_table
        t.selectRow(next(r for r in range(t.rowCount()) if t.item(r, 0).data(Qt.UserRole) == pid))
        next(b for b in win.prof_needs_one if b.text() == "Delete…").click()
        kept = pid in w.sw.profiles()
    finally:
        w.sw.remove_profile(pid)
        win.render_all()
    a = asked[0] if asked else (None,) * 5
    check("profiles: Delete… asks first, the question titled by its command and No its default (the file goes for "
          "good); No keeps the profile",
          len(asked) == 1 and a[1] == "Delete" and "Its file goes" in a[2] and a[4] == QMessageBox.No and kept,
          (a[1:], kept))


def test_dialogs_ask_with_windows_11s_band(devices_window, monkeypatch, check):
    # (2026-10-27, the rules' review: the name boxes (Rename…, Save as…) were Qt's own, OK and Cancel at their right,
    # while Paste filters and Set up had Windows 11's band; Set up's words were 18 px from its edges, the others' 24)
    from PySide6.QtWidgets import QDialog, QFrame, QPushButton, QWidget
    from ui import window_parts
    from ui.setup_dialog import SetUpDialog
    seen = {}

    def look(dlg, *a, **k):
        band = dlg.findChild(QFrame, "dialogFooter")
        btns = band.findChildren(QPushButton) if band is not None else []
        body = next(w for w in dlg.findChildren(QWidget) if w.parentWidget() is dlg and w is not band)
        m = body.layout().contentsMargins()
        seen[dlg.windowTitle()] = ([b.text() for b in btns], btns[0].property("primary") if btns else None,
                                   (m.left(), m.top(), m.right()))
        return QDialog.Rejected
    monkeypatch.setattr(QDialog, "exec", look)
    w = devices_window
    w.win.rename_device(KEY)
    window_parts.ask_text(w.win, "Save as a preset", "Name of the preset", "My settings", "Save")
    d = SetUpDialog(w.sw, w.win)
    m = next(x for x in d.findChildren(QWidget) if x.parentWidget() is d and x.objectName() != "dialogFooter")
    setup = (m.layout().contentsMargins().left(), m.layout().contentsMargins().top())
    d.deleteLater()
    check("dialogs: a name asked for (Rename the device, Save as a preset) ends with Windows 11's band, its verb first "
          "in the accent, then Cancel, its words 24 px from the edges, as Paste filters' and Set up's",
          seen.get("Rename the device") == (["Rename", "Cancel"], "true", (24, 24, 24))
          and seen.get("Save as a preset") == (["Save", "Cancel"], "true", (24, 24, 24)) and setup == (24, 24),
          (seen, setup))
