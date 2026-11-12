"""F1 in the main window (ui\\window.py's F1Anywhere): on a tagged control, Help opens at its entry, as a window of its
own that blocks nothing (as before 2026-11-11, when F1 became a watch on the application's key presses so that it
also works in the windows that block the others: tests\\eq_screen\\test_help_f1.py). Also: F1 with Ctrl does nothing,
and the window's watch is the only one (no QShortcut F1 left beside it)."""


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
    seen["F1 shortcuts left"] = [s.key().toString() for s in win.findChildren(QShortcut) if s.key().toString() == "F1"]
    check("F1: in the main window, F1 on a tagged control opens its entry in Help, a window of its own that blocks "
          "nothing, as before; Ctrl+F1 does nothing; no QShortcut F1 beside the watch",
          seen.get("tagged controls in sight", 0) >= 1 and seen.get("Ctrl+F1: Help") is False
          and seen.get("F1: Help at the control's entry") and seen.get("Help blocks nothing")
          and seen["F1 shortcuts left"] == [], seen)
