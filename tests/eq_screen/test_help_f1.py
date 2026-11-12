"""F1 in the windows that block the others (2026-11-11, the review's note N1): Find…, the wait for a picture over it,
Sources over Find…, Which measurement and History. F1 on a tagged control opens its entry in Help, and Help is then
usable: in front of the window (the top one of the windows that block the others), with input, and the window under
it stays open and takes input again when Help closes. Before, the main window's F1 was a QShortcut, which Qt does not
give while such a window is open: F1 did nothing there. Also: F1 in a text box and in a drop-down's list does not
stop their other keys.

The page here has no main window (helpers.eqpage): a stand-in with the main window's own F1 code (ui.window's
F1Anywhere and Window.help_here) is made on it. The main window's F1 itself: tests\\ui\\test_help_f1.py."""
import types

import pytest

from helpers import qt


@pytest.fixture(scope="module")
def f1(eq_screen):
    """The main window's F1 (ui.window.F1Anywhere, Window.help_here) on a stand-in window, as the app installs it."""
    from PySide6.QtWidgets import QApplication, QWidget
    from ui import window
    stand_in = QWidget()
    stand_in.open_help = window.Window.open_help
    stand_in.help_here = types.MethodType(window.Window.help_here, stand_in)
    watch = window.F1Anywhere(stand_in)
    QApplication.instance().installEventFilter(watch)
    yield watch
    QApplication.instance().removeEventFilter(watch)
    qt.close(stand_in)


def _help():
    from ui import help_window
    return help_window._window


def _press_f1(widget):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    widget.setFocus()
    QTest.keyClick(widget, Qt.Key_F1)
    qt.pump(50)


def _f1_on(control, dialog):
    """F1 on `control` of `dialog` (the top window that blocks the others): what Help shows and whether it is usable,
    then Help closed and the window under it as it is then."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from ui import help_window
    hw = _help()
    if hw is not None:
        hw.close()
    want = help_window.entry_of_widget(control)
    _press_f1(control)
    hw = _help()
    seen = {"entry": want, "help shown": hw is not None and hw.isVisible(),
            "at the entry": getattr(hw, "page_now", None) == want,
            "help on top (takes input)": QApplication.activeModalWidget() is hw, "window under it open": dialog.isVisible()}
    if hw is not None and hw.isVisible():
        hw.q.setFocus()
        QTest.keyClicks(hw.q, "rig")
        seen["typed in Help's search"] = hw.q.text()
        hw.q.clear()
        hw.close()
        qt.pump(50)
    seen["after Help closes: the window on top again"] = QApplication.activeModalWidget() is dialog
    seen["ok"] = (bool(want) and seen["help shown"] and seen["at the entry"] and seen["help on top (takes input)"]
                  and seen["window under it open"] and seen.get("typed in Help's search") == "rig"
                  and seen["after Help closes: the window on top again"])
    assert Qt.Key_F1  # (Qt loaded)
    return seen


def _during(dialog, steps):
    """steps(dialog) run while `dialog` is open as exec() opens it (application modal, shown: it blocks the others;
    the tests answer exec() at once, helpers.dialogs), then the dialog closed. Returns what steps returned."""
    from PySide6.QtCore import Qt
    dialog.setWindowModality(Qt.ApplicationModal)
    dialog.show()
    qt.pump(50)
    try:
        return steps(dialog)
    finally:
        dialog.reject()
        qt.close(dialog)


def test_f1_in_find(eq_screen, f1, check):
    from ui.picker import Picker
    seen = _during(Picker(eq_screen.page, "measurement"), lambda pk: _f1_on(pk.f_sure, pk))
    check("F1: in Find… (it blocks the other windows), F1 on Known rig opens its entry in Help; Help is in front and "
          "takes input, Find… stays open and is the top window again when Help closes", seen.get("ok"), seen)


def test_f1_in_the_wait_window(eq_screen, f1, check):
    # (the wait for a picture from a website: made and shown over Find…, as the page shows it, window modal)
    from ui.picker import Picker
    from ui.picture_wait import PictureWait

    def steps(pk):
        wait = PictureWait(pk, {"name": "Truthear Gate", "site": "Hangout.Audio 5128"})
        wait.open()
        qt.pump(50)
        try:
            return _f1_on(wait.paste_btn, wait)
        finally:
            wait.reject()
            qt.close(wait)
    seen = _during(Picker(eq_screen.page, "measurement"), steps)
    check("F1: in the wait for a picture (over Find…), F1 on Paste the picture opens its entry in Help, which is in "
          "front and takes input; the wait stays open", seen.get("ok"), seen)


def test_f1_in_sources_over_find(eq_screen, f1, check):
    from ui.picker import Picker
    from ui.sources_window import Sources

    def steps(pk):
        return _during(Sources(eq_screen.page), lambda src: _f1_on(src.folders, src))
    seen = _during(Picker(eq_screen.page, "measurement"), steps)
    check("F1: in Sources (over Find…: two windows that block the others), F1 on the folders opens their entry in "
          "Help, in front and with input; Sources stays open", seen.get("ok"), seen)


def test_f1_in_which_measurement(eq_screen, f1, monkeypatch, check):
    from ui import compare_window
    monkeypatch.setattr(compare_window.CompareWindow, "search_measurements", lambda self, auto=False: None)
    seen = _during(compare_window.CompareWindow(eq_screen.page), lambda cw: _f1_on(cw.q, cw))
    check("F1: in Which measurement, F1 on the model's box opens its entry in Help, in front and with input; the "
          "window stays open", seen.get("ok"), seen)


def test_f1_in_history(eq_screen, f1, check):
    from ui.history_window import HistoryWindow
    seen = _during(HistoryWindow(eq_screen.page, False), lambda hw: _f1_on(hw.only, hw))
    check("F1: in History, F1 on Only this IEM opens its entry in Help, in front and with input; History stays open",
          seen.get("ok"), seen)


def test_other_keys_go_on(eq_screen, f1, check):
    # (F1 is the only key that the watch keeps: after F1, a text box, a drop-down's list and a menu get all their other
    # keys as before)
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMenu
    from ui.picker import Picker

    def close_help():
        hw = _help()
        shown = hw is not None and hw.isVisible()
        if shown:
            hw.close()
            qt.pump(50)
        return shown

    def steps(pk):
        out = {}
        _press_f1(pk.q)  # (the search box has no entry: Help at its start)
        out["F1 in the search box: Help"] = close_help()
        pk.q.setFocus()
        QTest.keyClicks(pk.q, "gate")
        QTest.keyClick(pk.q, Qt.Key_Backspace)
        out["typed after F1"] = pk.q.text()
        box = pk.f_form  # (a drop-down's own list: Types has few choices, no search box)
        box.setCurrentIndex(0)
        box.showPopup()
        qt.pump(50)
        view = box.view()
        QTest.keyClick(view, Qt.Key_F1)
        qt.pump(50)
        out["F1 in a drop-down's list: Help"] = close_help()
        if not view.isVisible():
            box.showPopup()
            qt.pump(50)
        start = view.currentIndex().row()
        QTest.keyClick(view, Qt.Key_Down)
        out["the list's Down after F1"] = view.currentIndex().row() == start + 1
        QTest.keyClick(view, Qt.Key_Escape)
        qt.pump(50)
        out["the list closes with Esc"] = not view.isVisible()
        menu = QMenu(pk)
        acts = [menu.addAction(t) for t in ("One", "Two")]
        menu.popup(pk.mapToGlobal(QPoint(20, 20)))
        qt.pump(50)
        menu.setActiveAction(acts[0])
        QTest.keyClick(menu, Qt.Key_F1)
        qt.pump(50)
        out["F1 in a menu: Help"] = close_help()
        if not menu.isVisible():
            menu.popup(pk.mapToGlobal(QPoint(20, 20)))
            qt.pump(50)
            menu.setActiveAction(acts[0])
        QTest.keyClick(menu, Qt.Key_Down)
        out["the menu's Down after F1"] = menu.activeAction() is acts[1]
        qt.close(menu)
        return out
    seen = _during(Picker(eq_screen.page, "measurement"), steps)
    check("F1: in Find…, F1 opens Help from the search box, a drop-down's list and a menu, and after it each takes its "
          "other keys as before (typing, Backspace, Down, Esc)",
          seen == {"F1 in the search box: Help": True, "typed after F1": "gat", "F1 in a drop-down's list: Help": True,
                   "the list's Down after F1": True, "the list closes with Esc": True, "F1 in a menu: Help": True,
                   "the menu's Down after F1": True}, seen)


def test_f1_in_the_tracer_as_before(eq_screen, f1, check):
    # (the tracer is a window of its own that blocks nothing: Help opens there as before, a window that blocks nothing)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QWidget
    from ui import help_window
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    seen = {}
    try:
        qt.pump(100)
        tagged = [w for w in tw.findChildren(QWidget) if w.property("help_key") and w.isVisible()
                  and help_window.entry_of_widget(w)]
        seen["tagged controls in sight"] = len(tagged)
        if tagged:
            _press_f1(tagged[0])
            hw = _help()
            seen["at the entry"] = hw is not None and hw.isVisible() and hw.page_now == help_window.entry_of_widget(
                tagged[0])
            seen["blocks nothing"] = hw is not None and hw.windowModality() == Qt.NonModal \
                and QApplication.activeModalWidget() is None
            if hw is not None:
                hw.close()
    finally:
        tw.close()
    check("F1: in the tracer (a window of its own), F1 on a tagged control opens its entry in Help, which blocks "
          "nothing, as before", seen.get("tagged controls in sight", 0) >= 1 and seen.get("at the entry")
          and seen.get("blocks nothing"), seen)


def test_pointer_over_a_blocked_window(eq_screen, f1, monkeypatch, check):
    # (F1 opens the entry of the setting under the pointer first: with Find… open, the pointer over Make an EQ behind
    # it gave that setting's entry, not the one of Find…'s control with the focus)
    from PySide6.QtWidgets import QApplication, QWidget
    from ui import help_window
    from ui.picker import Picker
    page = eq_screen.page
    behind = next(w for w in page.findChildren(QWidget) if w.property("help_key") and help_window.entry_of_widget(w)
                  and help_window.entry_of_widget(w) != "set-pk-f-sure")
    monkeypatch.setattr(QApplication, "widgetAt", staticmethod(lambda *a: behind))

    def steps(pk):
        _press_f1(pk.f_sure)
        hw = _help()
        out = (hw.page_now if hw is not None else None, help_window.entry_of_widget(behind))
        if hw is not None:
            hw.close()
            qt.pump(50)
        return out
    seen = _during(Picker(page, "measurement"), steps)
    check("F1: with Find… open and the pointer over Make an EQ behind it, F1 opens the entry of Find…'s control with "
          "the focus, not the one of the setting behind", seen[0] == "set-pk-f-sure", seen)


def test_f1_in_help_over_find(eq_screen, f1, check):
    # (F1 in Help itself, while Help blocks the others over Find…: Help stays the top window, with input)
    from PySide6.QtWidgets import QApplication
    from ui.picker import Picker

    def steps(pk):
        _press_f1(pk.f_sure)
        hw = _help()
        _press_f1(hw.q)
        out = (hw.isVisible(), QApplication.activeModalWidget() is hw)
        hw.close()
        qt.pump(50)
        return out + (QApplication.activeModalWidget() is pk,)
    seen = _during(Picker(eq_screen.page, "measurement"), steps)
    check("F1: F1 in Help, opened over Find…, keeps Help shown and the top window (with input); closed, Find… is the top "
          "window again", seen == (True, True, True), seen)
