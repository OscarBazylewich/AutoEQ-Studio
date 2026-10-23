"""Settings (the window's settings screen, ui\\window.py; ui\\settings_screen.py once the window is split): restoring
a backup. Moved from selftest.py's qt_checks.

(review 2) Restore: nothing is saved between putting the backup back and the restart (Listen's and the tracer's save
on quit wrote the old settings over it); the devices' poll stops. The dialogs and the backup's files are stand-ins.
"""


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
