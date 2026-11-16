"""Settings (the window's settings screen, ui\\window.py; ui\\settings_screen.py once the window is split): restoring
a backup (moved from selftest.py's qt_checks), and its look in Windows 11's (the restyle, 2026-10-23): it scrolls in a
small window instead of squeezing its boxes and buttons, and a problem with the hotkey is said as a warning. The APO
card's Add and Remove buttons keep the focus and the screen in place (2026-11-13: last in the file).

(review 2) Restore: nothing is saved between putting the backup back and the restart (Listen's and the tracer's save
on quit wrote the old settings over it); the devices' poll stops. The dialogs and the backup's files are stand-ins.
"""
from helpers import session, subproc

# (after tests\ui\conftest.py's THEMED_WINDOW: Settings in the window at its smallest, the banner showing)
SMALL = r'''
from PySide6.QtWidgets import QAbstractButton, QKeySequenceEdit, QLineEdit, QScrollArea
win.show_page("settings", remember=False)
qapp.processEvents()
win.resize(win.minimumSizeHint())
for _ in range(10):
    qapp.processEvents()
page = win.pages["settings"]
shown = [w for kind in (QAbstractButton, QKeySequenceEdit) for w in page.findChildren(kind) if w.isVisible()
         and not isinstance(w.parentWidget(), QLineEdit)]  # (a box's own ✕ is the box's: sized by it)
print(json.dumps({"banner": win.banner.isVisible(), "controls": len(shown),
                  "squeezed": [(w.text() if isinstance(w, QAbstractButton) else type(w).__name__, w.height(),
                                w.sizeHint().height()) for w in shown if w.height() < w.sizeHint().height()],
                  "scrolls": isinstance(page, QScrollArea) and page.verticalScrollBar().maximum() > 0,
                  "smallest": [win.minimumSizeHint().width(), win.minimumSizeHint().height()],
                  "screens": win.stack.height()}))
'''


def test_settings_scrolls_in_a_small_window(themed_window, check, fake_apo, tmp_path):
    # (Windows 11's look made the cards taller: at the window's smallest, or with the banner showing, Settings
    # squeezed the hotkey box and None to half their height and cut its last lines; the window was at least 812 px
    # tall, more than a laptop's screen at 125 %)
    out = subproc.run_python(themed_window + SMALL, session.SESSION.app, str(tmp_path))
    d = out.data or {}
    check("settings: in a small window (the banner showing) its boxes and buttons keep their size, and the screen "
          "scrolls instead", d.get("banner") is True and (d.get("controls") or 0) >= 8 and d.get("squeezed") == []
          and d.get("scrolls") is True, d or out.stderr[-300:])
    check("window: at its smallest it fits a laptop's screen (no taller than 560 px, the banner showing) and leaves "
          "the screens 360 px", 0 < (d.get("smallest") or [0, 0])[1] <= 560 and (d.get("screens") or 0) >= 360,
          d.get("smallest") and (d.get("smallest"), d.get("screens")) or out.stderr[-300:])


def test_a_hotkey_problem_said_as_a_warning(devices_window, check):
    w = devices_window
    w.app.hotkey_problem = "Windows didn't take Ctrl+Alt+E as a hotkey: another program may use it. Try another."
    try:
        w.win.render_settings()
        said = (w.win.hotkey_note.text(), w.win.hotkey_note.property("role"))
    finally:
        del w.app.hotkey_problem  # (the stand-in app's own: none)
        w.win.render_settings()
    back = w.win.hotkey_note.isHidden()
    # (the UI audit, 2026-11-08: the words about the hotkey are behind its ⓘ; under its box only a problem)
    check("settings: a problem with the hotkey is said under its box in the warning colour, and goes after; the words "
          "about the hotkey are in its ⓘ",
          said[0].startswith("Windows didn't take") and said[1] == "warn" and back
          and "next profile" in w.win.hotkey_info.toolTip(), (said, back))


def test_after_a_restore_nothing_is_saved_before_the_restart(devices_window, check, monkeypatch):
    import backup
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    w = devices_window
    sw, stub = w.sw, w.app
    seen = []
    stub.timer = QTimer()  # (the app's poll of the devices: running)
    stub.timer.start(60000)
    stub.restart = lambda: seen.append((sw.read_only, stub.timer.isActive()))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("backup.zip", "")))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(backup, "read", lambda src: {"made": "today", "files": 1, "profiles": 0})
    monkeypatch.setattr(backup, "restore", lambda src, prof: {"files": 1, "kept": "kept.zip", "skipped": []})
    try:
        w.win.load_backup()
    finally:
        monkeypatch.undo()
        sw.read_only = False
        stub.timer.stop()
        del stub.timer, stub.restart  # (the stand-in app as it was)
    # was selftest.py:625
    check("window: after a restore nothing is saved over it before the restart (settings read-only, the poll stopped)",
          seen == [(True, False)], seen)


def test_a_hotkey_box_keeps_the_key_while_you_type(devices_window, monkeypatch, check):
    # (the review of 2026-11-10: Qt empties the box at the first key press of a new hotkey, and that empty value was
    # said as "no hotkey": the app saved it and took the hotkey off, so a key that Windows then refused could not put
    # the old key back)
    import types
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QLineEdit, QToolButton
    from helpers import qt
    from ui import app as app_module
    w = devices_window
    win, sw = w.win, w.sw
    box = win.hotkey_edit
    old = sw.s.get("hotkey")
    sw.set("hotkey", "Ctrl+Alt+E")
    win.render_settings()
    said = []
    refuse = {"Ctrl+Alt+J"}

    class Hotkey:  # (Windows' side: a key it refuses)
        @staticmethod
        def set(text):
            return text not in refuse
    fake = types.SimpleNamespace(sw=sw, win=win, hotkey=Hotkey())

    def changed(text):  # (the app's own way: ui\app.py)
        said.append(text)
        app_module.App._set_key(fake, "hotkey", fake.hotkey, text, True)
    win.hotkey_changed.connect(changed)
    try:
        box.setFocus()
        QTest.keyPress(box, Qt.Key_Control, Qt.ControlModifier)
        QTest.keyRelease(box, Qt.Key_Control, Qt.NoModifier)
        qt.wait_for(lambda: box.keySequence().toString() == "Ctrl+Alt+E", 3)
        ctrl_only = (list(said), sw.s.get("hotkey"), box.keySequence().toString())
        QTest.keyClick(box, Qt.Key_K, Qt.ControlModifier | Qt.AltModifier)
        qt.pump(5)
        complete = (list(said), sw.s.get("hotkey"))
        QTest.keyClick(box, Qt.Key_J, Qt.ControlModifier | Qt.AltModifier)
        qt.pump(5)
        refused = (list(said), sw.s.get("hotkey"), box.keySequence().toString(), bool(fake.hotkey_problem))
        x = box.findChild(QLineEdit).findChildren(QToolButton)  # (the box's ✕)
        QTest.mouseClick(x[0], Qt.LeftButton)
        qt.pump(5)
        cleared = (list(said), sw.s.get("hotkey"))
    finally:
        win.hotkey_changed.disconnect(changed)
        sw.set("hotkey", old)
        win.setFocus()
        win.render_settings()
    check("settings: in a hotkey box, Ctrl only (typing not complete) says no change and the key before stays; a "
          "complete key is said once; a key that Windows refuses puts the key before back (saved and in the box); "
          "the box's ✕ says no hotkey",
          ctrl_only == ([], "Ctrl+Alt+E", "Ctrl+Alt+E") and complete == (["Ctrl+Alt+K"], "Ctrl+Alt+K")
          and refused == (["Ctrl+Alt+K", "Ctrl+Alt+J"], "Ctrl+Alt+K", "Ctrl+Alt+K", True)
          and cleared == (["Ctrl+Alt+K", "Ctrl+Alt+J", ""], ""), (ctrl_only, complete, refused, cleared))


# ---------------------------------------------------------------- the APO card's buttons and the focus
# ("Add AutoEQ Studio to APO…" and "Remove AutoEQ Studio from APO…" take the place of each other. A click gives the
# button the focus; hidden with it, the button gave the focus to the next control in the window's order (Your files'
# Open the folder) and the screen scrolled to it: 63 px, measured 2026-11-13, as Calculate took Make an EQ to its top.
# Now the button that comes takes the focus. The screen stays where it is, or moves only as far as that button needs
# to stay in sight: the banner over the screens shows or goes with the change, and takes or gives room (46 px
# unthemed, 71 px in the app's theme). These tests use set_up_window, and so come last in the file)

def _apo_name(w):
    return None if w is None else f"{type(w).__name__} {w.text() if hasattr(w, 'text') else ''!r}"


def _apo_in_sight(area, w):
    from PySide6.QtCore import QPoint, QRect
    vp = area.viewport()
    return w.isVisible() and vp.rect().contains(QRect(w.mapTo(vp, QPoint(0, 0)), w.size()))


def _apo_settings_at(win, button):
    """Settings shown in a small window (it scrolls), the button in sight, the window active. Settings' scroll area."""
    from helpers import qt
    win.resize(1040, 560)
    win.show_page("settings", remember=False)
    win.render_settings()
    win.activateWindow()
    qt.pump(150)
    area = win.pages["settings"]
    for _ in range(10):  # (until the screen is laid out at this size: the theme, if a test before applied it, makes
        area.ensureWidgetVisible(button, 0, 60)  # the cards taller)
        qt.pump(60)
        if _apo_in_sight(area, button):
            break
    return area


def _apo_after(area, before, at, came):
    """What the change did: how far the screen moved, how much room it lost (the banner), and whether the button that
    came is in sight."""
    lost = max(0, before - area.viewport().height())
    return {"moved": abs(area.verticalScrollBar().value() - at), "room lost": lost,
            "came in sight": _apo_in_sight(area, came)}


def test_remove_from_apo_gives_the_focus_to_add(set_up_window, check):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from helpers import qt
    win = set_up_window.win
    area = _apo_settings_at(win, win.btn_unset)
    bar = area.verticalScrollBar()
    at, there, before = bar.value(), _apo_in_sight(area, win.btn_unset), area.viewport().height()
    QTest.mouseClick(win.btn_unset, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))  # (its question answered Yes)
    qt.pump(150)
    focus = QApplication.focusWidget()
    did = _apo_after(area, before, at, win.btn_setup)
    check("settings: Remove AutoEQ Studio from APO… gives the focus to Add AutoEQ Studio to APO…, in sight; the screen "
          "moves no farther than the room that the banner takes (it scrolled to Your files' Open the folder)",
          there and bar.maximum() > 0 and not win.btn_unset.isVisible() and focus is win.btn_setup
          and did["came in sight"] and did["moved"] <= did["room lost"], (there, at, _apo_name(focus), did))


def test_add_to_apo_gives_the_focus_to_remove(set_up_window, check, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMessageBox
    from helpers import qt
    from ui import winsys
    from ui.window import SetUpDialog
    w = set_up_window
    win = w.win
    if win.btn_unset.isVisible():  # (this test alone: APO not set up first)
        w.sw.remove_from_apo()
        win.render_settings()
    area = _apo_settings_at(win, win.btn_setup)
    bar = area.verticalScrollBar()
    win.btn_setup.setFocus(Qt.MouseFocusReason)  # (the click that opened Set up…; its window closed, the focus back)
    at, there, before = bar.value(), _apo_in_sight(area, win.btn_setup), area.viewport().height()
    # (Set up's OK, with EQ Switcher's side stood in, as tests\ui\conftest.py's set_up_window does it)
    monkeypatch.setattr(winsys, "eq_switcher_autostart", lambda: False)
    monkeypatch.setattr(winsys, "eq_switcher_running", lambda: False)
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: QMessageBox.Ok))
    SetUpDialog(w.sw, win)._add_to_apo()
    qt.pump(150)
    focus = QApplication.focusWidget()
    did = _apo_after(area, before, at, win.btn_unset)
    check("settings: Add AutoEQ Studio to APO… (its window's OK) gives the focus to Remove AutoEQ Studio from APO…, in "
          "sight; the screen moves no farther than the room that the banner takes",
          there and not win.btn_setup.isVisible() and focus is win.btn_unset and did["came in sight"]
          and did["moved"] <= did["room lost"], (there, at, _apo_name(focus), did))


# (after tests\ui\conftest.py's THEMED_WINDOW: APO set up for AutoEQ Studio, Settings in a small window, Remove
# AutoEQ Studio from APO… at the bottom of the screen with the focus, then clicked, its question answered Yes)
REMOVE_THEMED = r'''
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
sw.add_to_apo()
win.resize(1040, 560)
win.show_page("settings", remember=False)
win.render_settings()
win.activateWindow()
for _ in range(10):
    qapp.processEvents()
area = win.pages["settings"]
bar, vp = area.verticalScrollBar(), area.viewport()


def in_sight(w):
    return w.isVisible() and vp.rect().contains(QRect(w.mapTo(vp, QPoint(0, 0)), w.size()))


b = win.btn_unset
bar.setValue(b.mapTo(area.widget(), QPoint(0, 0)).y() + b.height() - vp.height() + 2)
for _ in range(5):
    qapp.processEvents()
b.setFocus(Qt.MouseFocusReason)
there, banner, before = in_sight(b) and win.focusWidget() is b, win.banner_holder.isVisible(), vp.height()
QTest.mouseClick(b, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
for _ in range(10):
    qapp.processEvents()
print(json.dumps({"Remove in sight with the focus": there, "banner before": banner,
                  "banner after": win.banner_holder.isVisible(), "room lost": before - vp.height(),
                  "focus on Add": win.focusWidget() is win.btn_setup, "Add in sight": in_sight(win.btn_setup)}))
'''


def test_remove_from_apo_keeps_add_in_sight_in_the_theme(themed_window, check, fake_apo, tmp_path):
    # (2026-11-15, the verifier: in the app's theme the banner that comes takes 71 px, and the button with the focus
    # went under the screen's bottom when the screen kept its place: the screen moves as far as that button needs)
    out = subproc.run_python(themed_window + REMOVE_THEMED, session.SESSION.app, str(tmp_path))
    d = out.data or {}
    check("settings, in the app's theme: Remove AutoEQ Studio from APO… at the bottom of a small screen gives the "
          "focus to Add AutoEQ Studio to APO…, in sight, when the banner comes and takes room",
          d.get("Remove in sight with the focus") is True and d.get("banner before") is False
          and d.get("banner after") is True and (d.get("room lost") or 0) > 0 and d.get("focus on Add") is True
          and d.get("Add in sight") is True, d or out.stderr[-400:])
