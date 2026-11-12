"""F1 in the main window (ui\\window.py's F1Anywhere): on a tagged control, Help opens at its entry, as a window of its
own that blocks nothing (as before 2026-11-11). The windows that block the others get an F1 of their own:
tests\\eq_screen\\test_help_f1.py. Also: F1 with Ctrl does nothing, the main window has one F1 (an application
shortcut, as before, that a held F1 gives once), and a hotkey box of Settings records F1 as a hotkey and does not
open Help (2026-11-12: an application event filter took each F1 before the box got it)."""


def _help():
    from ui import help_window
    return help_window._window


def test_f1_in_the_main_window(devices_window, qapp, check):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QShortcut
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QWidget
    from ui import help_window
    win = devices_window.win
    tagged = [w for w in win.findChildren(QWidget) if w.property("help_key") and w.isVisible()
              and help_window.entry_of_widget(w)]
    seen = {"tagged controls in sight": len(tagged)}
    if tagged:
        ctl = tagged[0]
        hw = _help()
        if hw is not None:
            hw.close()
        ctl.setFocus()
        QTest.keyClick(ctl, Qt.Key_F1, Qt.ControlModifier)
        qapp.processEvents()
        seen["Ctrl+F1: Help"] = _help() is not None and _help().isVisible()
        QTest.keyClick(ctl, Qt.Key_F1)
        qapp.processEvents()
        hw = _help()
        seen["F1: Help at the control's entry"] = (hw is not None and hw.isVisible()
                                                   and hw.page_now == help_window.entry_of_widget(ctl))
        seen["Help blocks nothing"] = hw is not None and hw.windowModality() == Qt.NonModal \
            and QApplication.activeModalWidget() is None
        if hw is not None:
            hw.close()
    seen["F1 shortcuts (context, auto-repeat)"] = [
        (s.context() == Qt.ApplicationShortcut, s.autoRepeat()) for s in win.findChildren(QShortcut)
        if s.key().toString() == "F1"]
    check("F1: in the main window, F1 on a tagged control opens its entry in Help, a window of its own that blocks "
          "nothing, as before; Ctrl+F1 does nothing; one F1 shortcut for the whole app, which a held F1 gives once",
          seen.get("tagged controls in sight", 0) >= 1 and seen.get("Ctrl+F1: Help") is False
          and seen.get("F1: Help at the control's entry") and seen.get("Help blocks nothing")
          and seen["F1 shortcuts (context, auto-repeat)"] == [(True, False)], seen)


def test_f1_in_the_hotkey_boxes(devices_window, qapp, check):
    # (F1 alone is a hotkey that Windows permits: ui\winsys.py. The boxes take each key before a shortcut does)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeySequence
    from PySide6.QtTest import QTest
    from helpers import qt
    win, sw = devices_window.win, devices_window.sw
    win.show_page("settings", remember=False)
    qt.pump(50)
    seen = {}
    for name, box, signal, setting in (("hotkey", win.hotkey_edit, win.hotkey_changed, "hotkey"),
                                       ("on/off hotkey", win.onoff_edit, win.onoff_hotkey_changed, "onoff_hotkey")):
        old = sw.s.get(setting)
        hw = _help()
        if hw is not None:
            hw.close()
        said, typed = [], []
        signal.connect(said.append)
        box.keySequenceChanged.connect(lambda seq, t=typed: t.append(seq.toString(QKeySequence.PortableText)))
        try:
            box.setFocus()
            QTest.keyClick(box, Qt.Key_F1)
            qt.wait_for(lambda s=said: s, 3)
            hw = _help()
            seen[name] = {"typed": typed[-1:], "said": said[-1:], "help shown": hw is not None and hw.isVisible()}
        finally:
            signal.disconnect(said.append)
            sw.set(setting, old)
            win.render_settings()
    win.show_page("devices", remember=False)
    check("F1: in each hotkey box of Settings, F1 is recorded as the hotkey (as before 2026-11-11), and Help does not "
          "open", seen == {n: {"typed": ["F1"], "said": ["F1"], "help shown": False}
                           for n in ("hotkey", "on/off hotkey")}, seen)


def test_a_minimized_help_comes_back(devices_window, qapp, check):
    # (2026-11-12: open_at showed, raised and activated Help, but a minimized Help stayed minimized: F1 and the Help
    # button seemed to do nothing. The same fault as the tracer's, eq_page_files.EqFiles.open_trace)
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QWidget
    from helpers import qt
    from ui import help_window
    win = devices_window.win
    ctl = next(w for w in win.findChildren(QWidget) if w.property("help_key") and w.isVisible()
               and help_window.entry_of_widget(w))
    seen = {}
    for way, maximized in (("F1", False), ("the Help button", False), ("F1", True), ("the Help button", True)):
        hw = help_window.open_at(None)
        hw.setWindowState(Qt.WindowMaximized if maximized else Qt.WindowNoState)
        qt.pump(50)
        hw.setWindowState(hw.windowState() | Qt.WindowMinimized)
        qt.pump(50)
        before = hw.isMinimized()
        win.activateWindow()  # (the main window in front, as when you press F1 there)
        qt.pump(50)
        if way == "F1":
            ctl.setFocus()
            QTest.keyClick(ctl, Qt.Key_F1)
        else:
            win.help_btn.click()
        qt.pump(50)
        seen[f"{way}, maximized {maximized}"] = (before, hw.isVisible(), hw.isMinimized(), hw.isMaximized())
        hw.setWindowState(Qt.WindowNoState)
        hw.close()
        qt.pump(50)
    check("Help: a minimized Help comes back with F1 and with the Help button, in view and not minimized; a maximized "
          "Help comes back maximized",
          seen == {"F1, maximized False": (True, True, False, False),
                   "the Help button, maximized False": (True, True, False, False),
                   "F1, maximized True": (True, True, False, True),
                   "the Help button, maximized True": (True, True, False, True)}, seen)
