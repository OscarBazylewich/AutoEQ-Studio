"""F1 in the windows that block the others (2026-11-11, the review's note N1): Find…, the wait for a picture over it,
Sources over Find…, Which measurement and History. F1 on a tagged control opens its entry in Help, and Help is then
usable: in front of the window (the top one of the windows that block the others), with input, and the window under
it stays open and takes input again when Help closes. Before, the main window's F1 was a QShortcut, which Qt does not
give while such a window is open: F1 did nothing there. Since 2026-11-12 such a window gets a shortcut F1 of its
own when it becomes the window with the focus (not an event filter on the application: it made each event slower),
also with no control that takes the focus; a window that blocks nothing (the tracer) gets none. Also: F1 in a
text box, a drop-down's list and a menu does not stop their other keys; Help open before Find… comes in front with
F1; the window under Help closes by itself (the wait gets a picture): Help then blocks nothing; Help hides and shows
only for a change of what it blocks (a count of its show events); a minimized Help over a window that it blocks
comes back.

The page here has no main window (helpers.eqpage): a stand-in with the main window's own F1 code (ui.window's
F1Anywhere and Window.help_here) is made on it. The main window's F1 itself: tests\\ui\\test_help_f1.py."""
import types

import pytest

from helpers import qt


@pytest.fixture(scope="module")
def f1(eq_screen):
    """The main window's F1 (ui.window.F1Anywhere, Window.help_here) on a stand-in window, as the app makes it. The
    stand-in is shown, as the main window is: Qt gives an application shortcut only from a window in sight."""
    from PySide6.QtWidgets import QMainWindow
    from ui import window
    stand_in = QMainWindow()
    stand_in.open_help = window.Window.open_help
    stand_in.help_here = types.MethodType(window.Window.help_here, stand_in)
    watch = window.F1Anywhere(stand_in)
    stand_in.resize(200, 100)
    stand_in.show()
    page_window = eq_screen.page.window()
    page_window.activateWindow()
    qt.pump(50)
    yield watch
    # (the F1 shortcuts that this stand-in's watch put on windows that stay, as Help, go with it: they call the
    # stand-in, and a later file's F1 in the main window was given to one of them, 2026-11-12)
    from PySide6.QtGui import QShortcut
    from PySide6.QtWidgets import QApplication
    for w in QApplication.topLevelWidgets():
        for s in w.findChildren(QShortcut, watch.NAME):
            s.setParent(None)
            s.deleteLater()
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


def _f1_on(control, dialog, close_first=True):
    """F1 on `control` of `dialog` (the top window that blocks the others): what Help shows and whether it is usable,
    then Help closed and the window under it as it is then. close_first=False: a Help that is open stays open."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    from ui import help_window
    hw = _help()
    if hw is not None and close_first:
        hw.close()
    want = help_window.entry_of_widget(control)
    _press_f1(control)
    hw = _help()
    seen = {"entry": want, "help shown": hw is not None and hw.isVisible(),
            "at the entry": getattr(hw, "page_now", None) == want,
            "help on top (takes input)": QApplication.activeModalWidget() is hw,
            "window under it open": dialog.isVisible()}
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
    from PySide6.QtGui import QShortcut
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
            # (2026-11-12: only a window that blocks the others gets an F1 of its own; the main window's F1 works in
            # the tracer. A check of the window with the focus in place of the one that blocks passed every test)
            tw.activateWindow()
            tagged[0].setFocus()
            qt.pump(50)
            seen["the tracer has no F1 of its own"] = tw.findChild(QShortcut, f1.NAME) is None
    finally:
        tw.close()
    check("F1: in the tracer (a window of its own), F1 on a tagged control opens its entry in Help, which blocks "
          "nothing, as before; the tracer gets no F1 shortcut of its own",
          seen.get("tagged controls in sight", 0) >= 1 and seen.get("at the entry")
          and seen.get("blocks nothing") and seen.get("the tracer has no F1 of its own"), seen)


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
    check("F1: F1 in Help, opened over Find…, keeps Help shown and the top window (with input); closed, Find… is the "
          "top window again", seen == (True, True, True), seen)


def test_f1_of_a_window_that_blocks(eq_screen, f1, check):
    # (Find…'s own F1, made when the focus goes into it: one, an application shortcut as the main window's (so it also
    # works from a drop-down's list or a menu of Find…), which a held F1 gives once)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QShortcut
    from ui.picker import Picker

    def steps(pk):
        pk.q.setFocus()
        qt.pump(50)
        return [(s.context() == Qt.ApplicationShortcut, s.autoRepeat()) for s in pk.findChildren(QShortcut)
                if s.key().toString() == "F1"]
    seen = _during(Picker(eq_screen.page, "measurement"), steps)
    check("F1: Find… gets one F1 of its own, an application shortcut, which a held F1 gives once",
          seen == [(True, False)], seen)


def test_help_open_before_find(eq_screen, f1, check):
    # (Help open as a window of its own, then Find… opens and blocks it: F1 in Find… brings Help in front, with input)
    from PySide6.QtCore import Qt
    from ui import help_window
    from ui.picker import Picker
    hw = help_window.open_at(None)
    qt.pump(50)
    before = hw.isVisible() and hw.windowModality() == Qt.NonModal
    seen = _during(Picker(eq_screen.page, "measurement"), lambda pk: _f1_on(pk.f_sure, pk, close_first=False))
    seen["Help open before Find…, it blocks nothing"] = before
    check("F1: with Help open before Find… opens, F1 in Find… opens the entry in Help, in front and with input; "
          "Find… stays open", seen.get("ok") and before, seen)


def test_one_help_for_each_f1(eq_screen, f1, monkeypatch, check):
    # (Help opened over Find… has an F1 of its own. Open again as a window of its own, its F1 and the main window's
    # are two shortcuts for one key, which Qt gives as "ambiguous": F1 must still open Help, one time)
    from PySide6.QtGui import QShortcut
    from PySide6.QtWidgets import QWidget
    from ui import help_window
    from ui.picker import Picker
    _during(Picker(eq_screen.page, "measurement"), lambda pk: _f1_on(pk.f_sure, pk))
    hw = _help()
    seen = {"Help has its own F1": hw.findChild(QShortcut, f1.NAME) is not None}
    real, calls = help_window.open_at, []
    monkeypatch.setattr(help_window, "open_at", lambda entry=None: (calls.append(entry), real(entry))[1])
    real(None)
    qt.pump(50)
    _press_f1(hw.q)
    seen["F1 in Help (a window of its own)"] = len(calls)
    calls.clear()
    ctl = next(w for w in eq_screen.page.findChildren(QWidget) if w.property("help_key") and w.isVisible()
               and help_window.entry_of_widget(w))
    ctl.window().activateWindow()  # (the page in front, Help open behind it)
    qt.pump(50)
    _press_f1(ctl)
    seen["F1 in the page, Help open"] = calls == [help_window.entry_of_widget(ctl)]
    monkeypatch.undo()
    hw.close()
    qt.pump(50)
    check("F1: with Help open as a window of its own after it blocked Find…, F1 in Help and F1 in the page each open "
          "Help one time", seen == {"Help has its own F1": True, "F1 in Help (a window of its own)": 1,
                                   "F1 in the page, Help open": True}, seen)


@pytest.mark.parametrize("f1_in_help", [False, True], ids=["F1 in the wait", "then F1 in Help too"])
def test_help_when_the_wait_ends(eq_screen, f1, f1_in_help, check):
    # (Help over the wait for a picture; the wait gets a picture and closes by itself, then Find… under it closes, as
    # the page does then: Help stays open and blocks nothing, so each window takes input again. Before 2026-11-12, Help
    # blocked the others until it closed: the tracer then got no input)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from ui.picker import Picker
    from ui.picture_wait import PictureWait
    out = {}

    def steps(pk):
        wait = PictureWait(pk, {"name": "Truthear Gate", "site": "Hangout.Audio 5128"})
        wait.open()
        qt.pump(50)
        try:
            _press_f1(wait.paste_btn)
            hw = _help()
            if f1_in_help:  # (F1 in Help itself: Help stays over the same window)
                _press_f1(hw.q)
            out["Help over the wait"] = QApplication.activeModalWidget() is hw
            wait.accept()
            qt.pump(100)
            out["wait closed: Help shown, over Find…"] = hw.isVisible() and QApplication.activeModalWidget() is hw
        finally:
            qt.close(wait)
        pk.reject()
        qt.pump(100)
        out["Find… closed: Help shown"] = hw.isVisible()
        out["Find… closed: no window blocks the others"] = QApplication.activeModalWidget() is None \
            and hw.windowModality() == Qt.NonModal
        hw.close()
        qt.pump(50)
    _during(Picker(eq_screen.page, "measurement"), steps)
    check("F1: Help opened over the wait for a picture stays open when the wait and then Find… close by themselves, "
          "and then blocks nothing (each window takes input again)",
          out == {"Help over the wait": True, "wait closed: Help shown, over Find…": True,
                  "Find… closed: Help shown": True, "Find… closed: no window blocks the others": True}, out)


def test_f1_of_a_window_with_no_control_that_takes_the_focus(eq_screen, f1, check):
    # (2026-11-12: F1Anywhere was told of each change of the focus control and of the focus window, and a test with
    # only one of the two passed. Measured: a window that blocks and has no control that takes the focus gets its F1
    # only from the change of the focus window; the change of the focus control is not connected now)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QShortcut
    from PySide6.QtWidgets import QApplication, QDialog, QLabel, QLineEdit, QVBoxLayout

    def f1s(w):
        return len(w.findChildren(QShortcut, f1.NAME, Qt.FindDirectChildrenOnly))
    seen = {}
    # (the same start whatever test ran before: the page's window has the focus and no control in it has the focus.
    # Measured 2026-11-12: with a control that has the focus first, the dialog takes the focus from it, and a watch
    # of the change of the focus control (focusChanged) also puts the F1; a test from that start passed with that
    # watch in place of the watch of the focus window. From this start only the change of the focus window occurs)
    page_window = eq_screen.page.window()
    page_window.activateWindow()
    qt.pump(50)
    if QApplication.focusWidget() is not None:
        QApplication.focusWidget().clearFocus()
        qt.pump(50)
    seen["the page's window first, no control with the focus"] = (QApplication.activeWindow() is page_window
                                                                  and QApplication.focusWidget() is None)
    first = QDialog(eq_screen.page)
    QVBoxLayout(first).addWidget(QLabel("Words only"))
    first.setWindowModality(Qt.ApplicationModal)
    first.show()
    qt.pump(50)
    second = None
    try:
        seen["no control with the focus"] = QApplication.focusWidget() is None
        seen["its F1"] = f1s(first)
        second = QDialog(first)
        boxes = (QLineEdit(), QLineEdit())
        lay = QVBoxLayout(second)
        for b in boxes:
            lay.addWidget(b)
        second.setWindowModality(Qt.ApplicationModal)
        second.show()
        qt.pump(50)
        seen["second over it: its F1"] = f1s(second)
        boxes[1].setFocus()
        qt.pump(50)
        boxes[0].setFocus()
        qt.pump(50)
        seen["the focus moves in the second: its F1"] = f1s(second)
    finally:
        if second is not None:
            qt.close(second)
        qt.close(first)
    check("F1: a window that blocks the others and has no control that takes the focus gets its F1; a second one over "
          "it gets its F1; the focus that moves in a window keeps one F1 there",
          seen == {"the page's window first, no control with the focus": True, "no control with the focus": True,
                   "its F1": 1, "second over it: its F1": 1, "the focus moves in the second: its F1": 1}, seen)


def _show_count(w):
    """A count of w's show events, from now (a hide and a show again flashes the window on a real desktop)."""
    from PySide6.QtCore import QEvent, QObject

    class Count(QObject):
        shows = 0

        def eventFilter(self, obj, e):
            if obj is w and e.type() == QEvent.Show:
                self.shows += 1
            return False
    c = Count(w)
    w.installEventFilter(c)
    return c


def test_help_hides_and_shows_only_when_it_must(eq_screen, f1, check):
    # (2026-11-12, the review's H7: Help's watch of an older window under it, not removed, hid and showed Help again
    # when that older window closed while Help was over a different one)
    from PySide6.QtWidgets import QApplication
    from ui.picker import Picker
    from ui.sources_window import Sources
    out = {}

    def steps(pk):
        _press_f1(pk.f_sure)  # (Help over Find…: it watches Find…)
        hw = _help()
        hw.close()
        qt.pump(50)

        def over_sources(src):
            _press_f1(src.folders)  # (Help over Sources, which is over Find…: it watches Sources only)
            out["Help over Sources"] = QApplication.activeModalWidget() is hw
            count = _show_count(hw)
            pk.hide()  # (Find… closes while Sources and Help stay open)
            qt.pump(100)
            out["show events of Help"] = count.shows
            out["Help still over Sources"] = hw.isVisible() and QApplication.activeModalWidget() is hw
            hw.removeEventFilter(count)
            hw.close()
            qt.pump(50)
        _during(Sources(eq_screen.page), over_sources)
    _during(Picker(eq_screen.page, "measurement"), steps)
    check("F1: Help over Sources does not hide and show again when Find… (the window that Help was over before) "
          "closes", out == {"Help over Sources": True, "show events of Help": 0, "Help still over Sources": True}, out)


def test_help_shows_once_when_its_window_goes(eq_screen, f1, check):
    # (2026-11-12, the review's H8: the second of two late calls, after Help blocked nothing already, hid and showed
    # it again. The wait closes, Help is opened again over Find…, then Find… closes: two calls come after that)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from ui import help_window
    from ui.picker import Picker
    from ui.picture_wait import PictureWait
    out = {}

    def steps(pk):
        wait = PictureWait(pk, {"name": "Truthear Gate", "site": "Hangout.Audio 5128"})
        wait.open()
        qt.pump(50)
        try:
            _press_f1(wait.paste_btn)  # (Help over the wait)
            hw = _help()
            count = _show_count(hw)
            wait.accept()  # (the wait gets a picture; then, before the next turn of the event loop:)
            hw.close()
            help_window.open_at(None)  # (Help opened again, over Find…)
            pk.reject()  # (and Find… closes, as the page does)
            shows_before = count.shows
            qt.pump(150)
            out["show events after"] = count.shows - shows_before
            out["Help shown, blocks nothing"] = hw.isVisible() and hw.windowModality() == Qt.NonModal \
                and QApplication.activeModalWidget() is None
            hw.removeEventFilter(count)
            hw.close()
            qt.pump(50)
        finally:
            qt.close(wait)
    _during(Picker(eq_screen.page, "measurement"), steps)
    check("F1: when the windows under Help close, Help hides and shows one time (to block nothing), not two",
          out == {"show events after": 1, "Help shown, blocks nothing": True}, out)


@pytest.mark.parametrize("over", [True, False], ids=["over a window that it blocks", "a window of its own"])
def test_a_minimized_help_when_its_window_goes(eq_screen, f1, over, check):
    # (2026-11-12: a minimized Help that blocks the others makes the window under it take no input; when the window
    # that it was over closes and it blocks a different one, it comes back; as a window of its own, it stays minimized)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from ui.picker import Picker
    from ui.picture_wait import PictureWait
    out = {}

    def steps(pk):
        wait = PictureWait(pk, {"name": "Truthear Gate", "site": "Hangout.Audio 5128"}) if over else None
        if wait is not None:
            wait.open()
            qt.pump(50)
        try:
            _press_f1(wait.paste_btn if wait is not None else pk.f_sure)
            hw = _help()
            hw.setWindowState(hw.windowState() | Qt.WindowMinimized)
            qt.pump(50)
            out["minimized"] = hw.isMinimized()
            if wait is not None:
                wait.accept()
            else:
                pk.reject()
            qt.pump(150)
            out["after: minimized"] = hw.isMinimized()
            out["after: blocks"] = QApplication.activeModalWidget() is hw
            hw.setWindowState(Qt.WindowNoState)
            hw.close()
            qt.pump(50)
        finally:
            if wait is not None:
                qt.close(wait)
    _during(Picker(eq_screen.page, "measurement"), steps)
    want = {"minimized": True, "after: minimized": not over, "after: blocks": over}
    check("F1: a minimized Help over the wait comes back when the wait closes (it then blocks Find…); a minimized Help "
          "over Find… stays minimized when Find… closes (it then blocks nothing)", out == want, out)
