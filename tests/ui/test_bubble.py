"""The bubbles (ui\\bubble.py) on the window: a link in a "do this first" or ⓘ bubble opens and the bubble stays;
the app-wide watch goes when the last such bubble closes (by its time or its ✕ too); Esc closes an open menu before
the bubble; a bubble does not follow its control while the window is minimized or in the tray (and does again when it
shows); a bubble whose control is scrolled out of view closes (a message goes to the window's bottom). On the ui
folder's window (tests\\ui\\conftest.py)."""
import pytest
from PySide6.QtCore import QPoint, Qt

from helpers import qt


@pytest.fixture
def win(devices_window):
    w = devices_window.win
    w.show()
    w.show_page("devices", remember=False)
    w.resize(1040, 760)
    qt.pump(10)
    yield w
    from ui import bubble
    for kind in ("tell", "info", "say"):
        b = bubble.last(kind)
        if b is not None:
            b.close_now()
    w.show_page("devices", remember=False)
    w.resize(1040, 760)
    qt.pump(5)


def _watching():
    from ui import bubble
    return bool(bubble._closer) and bubble._closer[0].watching()


def test_a_link_in_a_bubble_opens(win, check):
    # (the review of 2026-11-10: the app-wide watch saw the press first on the window's native part, not on the
    # bubble's words, so it closed the bubble and the link never opened)
    from PySide6.QtTest import QTest
    from ui import bubble
    opened = []
    b = bubble.tell(win.nav["settings"], '<a href="page">Open the page</a>', links=opened.append)
    qt.pump(3)  # (watched from the next event on)
    watched = _watching()
    QTest.mouseClick(b.text, Qt.LeftButton, Qt.NoModifier, QPoint(6, b.text.height() // 2))
    qt.pump(3)
    stays = b.isVisible()
    QTest.mouseClick(win.nav["profiles"], Qt.LeftButton, Qt.NoModifier, QPoint(4, 4))  # (a click at a different place)
    qt.pump(3)
    check("bubble: a click on a link in a \"do this first\" bubble opens the link and the bubble stays; a click at a "
          "different place closes it",
          watched and opened == ["page"] and stays and not b.isVisible() and not _watching(),
          (watched, opened, stays, b.isVisible()))


def test_a_link_in_an_info_bubble_opens(win, check):
    from PySide6.QtTest import QTest
    from ui.bubble import InfoMark
    opened = []
    mark = InfoMark('<a href="app">Your EQ app</a>', "Your EQ app", links=opened.append)
    mark.setParent(win.pages["devices"])
    mark.move(40, 40)
    mark.show()
    try:
        mark.click()
        qt.pump(3)
        from ui import bubble
        b = bubble.last("info")
        QTest.mouseClick(b.text, Qt.LeftButton, Qt.NoModifier, QPoint(6, b.text.height() // 2))
        qt.pump(3)
        got = (opened, b.isVisible())
        b.close_now()
    finally:
        qt.close(mark)
    check("bubble: a click on a link in an ⓘ bubble opens the link and the bubble stays",
          got == (["app"], True), got)


def test_the_watch_goes_with_the_last_bubble(win, check):
    # (the app-wide watch sees every event of every control: it stayed on after a bubble closed by its time or its ✕,
    # until the next press)
    from ui import bubble
    b = bubble.tell(win.nav["settings"], "Do this first.")
    qt.pump(3)
    on = _watching()
    b.close_btn.click()
    by_x = _watching()
    b = bubble.tell(win.nav["settings"], "Do this first.")
    qt.pump(3)
    b._timer.start(1)  # (as a bubble with a time: its timer closes it)
    qt.wait_for(lambda: not b.isVisible(), 2)
    by_time = _watching()
    check("bubble: the app-wide watch is on while a \"do this first\" bubble shows, and goes as it closes (by its ✕ "
          "or its time), not at the next press", on and not by_x and not by_time, (on, by_x, by_time))


def test_esc_closes_an_open_menu_first(win, check):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMenu
    from ui import bubble
    b = bubble.tell(win.nav["settings"], "Do this first.")
    qt.pump(3)
    menu = QMenu(win)
    menu.addAction("One")
    menu.popup(win.mapToGlobal(QPoint(100, 100)))
    qt.pump(3)
    try:
        opened = QApplication.activePopupWidget() is menu
        QTest.keyClick(menu, Qt.Key_Escape)
        qt.pump(3)
        first = (menu.isVisible(), b.isVisible())
    finally:
        menu.close()
        menu.deleteLater()
    qt.pump(3)
    win.activateWindow()
    QTest.keyClick(win.nav["settings"], Qt.Key_Escape)
    qt.pump(3)
    check("bubble: Esc closes an open menu first and the bubble stays; the next Esc closes the bubble",
          opened and first == (False, True) and not b.isVisible(), (opened, first, b.isVisible()))


def test_no_follow_while_the_window_does_not_show(win, check):
    # (the bubble's 150 ms timer ran while the window was minimized or in the tray, and with status(text, 0) it never
    # stopped)
    win.status("Kept until the next one.", 0)
    b = win.message.bubble
    qt.pump(3)
    shown = b._follow.isActive()
    states = {}
    for name, away, back in (("tray", win.hide, win.show), ("minimized", win.showMinimized, win.showNormal)):
        away()
        qt.wait_for(lambda: not b._follow.isActive(), 2)
        off = b._follow.isActive()
        back()
        qt.wait_for(lambda: b._follow.isActive(), 2)
        states[name] = (off, b._follow.isActive())
    win.status("")
    qt.pump(3)
    check("bubble: a message's bubble follows its control while the window shows, stops while the window is in the "
          "tray or minimized, and follows again when it shows; it stops when it closes",
          shown and states == {"tray": (False, True), "minimized": (False, True)} and not b._follow.isActive(),
          (shown, states, b._follow.isActive()))


def test_a_control_scrolled_out_of_view(win, check):
    # (a bubble whose control was scrolled out of view stayed, at the window's top over the bar)
    from ui import bubble
    win.show_page("settings", remember=False)
    win.resize(1040, 420)
    qt.pump(10)
    page = win.pages["settings"]
    bar = page.verticalScrollBar()
    bar.setValue(bar.maximum())
    qt.pump(5)
    mark = win.hotkey_info
    mark.click()
    qt.pump(3)
    b = bubble.last("info")
    out_first = not bubble.in_view(mark, win) or not b.isVisible()
    bar.setValue(0)
    qt.pump(5)
    in_view = bubble.in_view(mark, win)
    mark.click()
    qt.pump(3)
    showing = b.isVisible()
    bar.setValue(bar.maximum())
    qt.wait_for(lambda: not b.isVisible(), 2)
    closed = not b.isVisible() and not bubble.in_view(mark, win)
    # a message near the control: to the window's bottom
    bar.setValue(0)
    qt.pump(5)
    win.hotkey_edit.setFocus()
    say = win.message.bubble
    say.show_text("Saved.", win.hotkey_edit, ms=None)
    near = say.anchor is win.hotkey_edit
    bar.setValue(bar.maximum())
    qt.wait_for(lambda: say.anchor is None, 2)
    bottom = say.isVisible() and say.anchor is None and say.y() + say.height() > win.height() - 40
    say.close_now()
    check("bubble: an ⓘ bubble closes when its control is scrolled out of view (it went over the top bar); a message "
          "goes to the window's bottom", out_first and in_view and showing and closed and near and bottom,
          (out_first, in_view, showing, closed, near, bottom))
