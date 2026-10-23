"""Settings (the window's settings screen, ui\\window.py; ui\\settings_screen.py once the window is split): restoring
a backup (moved from selftest.py's qt_checks), and its look in Windows 11's (the restyle, 2026-10-23): it scrolls in a
small window instead of squeezing its boxes and buttons, and a problem with the hotkey is said as a warning.

(review 2) Restore: nothing is saved between putting the backup back and the restart (Listen's and the tracer's save
on quit wrote the old settings over it); the devices' poll stops. The dialogs and the backup's files are stand-ins.
"""
from helpers import session, subproc

# (after tests\ui\conftest.py's THEMED_WINDOW: Settings in the window at its smallest, the banner showing)
SMALL = r'''
from PySide6.QtWidgets import QAbstractButton, QKeySequenceEdit, QScrollArea
win.show_page("settings", remember=False)
qapp.processEvents()
win.resize(win.minimumSizeHint())
for _ in range(10):
    qapp.processEvents()
page = win.pages["settings"]
shown = [w for kind in (QAbstractButton, QKeySequenceEdit) for w in page.findChildren(kind) if w.isVisible()]
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
    back = w.win.hotkey_note.property("role")
    check("settings: a problem with the hotkey is said in the warning colour, and the note is quiet again after",
          said[0].startswith("Windows didn't take") and said[1] == "warn" and back == "muted", (said, back))


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
        w.win.restore_backup()
    finally:
        monkeypatch.undo()
        sw.read_only = False
        stub.timer.stop()
        del stub.timer, stub.restart  # (the stand-in app as it was)
    # was selftest.py:625
    check("window: after a restore nothing is saved over it before the restart (settings read-only, the poll stopped)",
          seen == [(True, False)], seen)
