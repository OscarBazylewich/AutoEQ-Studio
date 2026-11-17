"""The focus frame on Make an EQ and in its windows (ui\\focus_frame.py; the user's decision, 2026-11-16), with real
keys and clicks (QTest, on the window's native part, as Windows sends them) and what shows read from the pixels of the
window's picture: Tab shows the frame on Calculate; Space on Calculate starts the job and the frame shows on Cancel,
which the page gives the focus (UI-RULES 30), then on Calculate again when the job is done; after a click on Calculate
none of that shows; a notch of the mouse wheel on the Target list gives the list the focus and no frame, and one on
the page leaves the frame; a ✕ button and a drop-down list in the first row of the filter table have a whole frame
(the table's view has no room above that row); a click outside the menu of Use on device takes the frame off; the
filter editor's sliders keep their own ring; the graph that floats over the page is above the frame; the Guide shows
no frame on the page under it, and the frame is back at its end when a key ended it; in each window of the page
(Find…, Sources, History, Queue, All results, Compare, Which measurement, the wait for a picture, the tracer, a
question) each control that gets the frame has it, whole, with the keyboard in use; one move of the focus takes less
than 1 ms. One page for the file (the eq_screen fixture)."""
import statistics
import time

import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QSlider, QToolButton, QWidget

from helpers import eqpage, qt

COVERS = ("ui.focus_frame",)


def _frame_module():
    """ui.focus_frame, or None on the code before the focus frame (each check then fails with what was seen)."""
    try:
        from ui import focus_frame
    except ImportError:
        return None
    return focus_frame


def _colours():
    from ui import theme
    t = theme.tokens()
    return t.get("focus_outer", t["ink"]), t.get("focus_inner", "#ffffff" if not theme.dark() else "#000000")


def _mouse_up(win):
    """No mouse button down for Qt (a test before this file that pressed one without a release would leave Qt with a
    button down, and every move of the focus would then be the mouse's)."""
    for b in (Qt.LeftButton, Qt.RightButton, Qt.MiddleButton):
        if QGuiApplication.mouseButtons() & b:
            QTest.mouseRelease(win.windowHandle(), b, Qt.NoModifier, QPoint(1, 1))


def _click(w, at=None):
    """A click of the mouse on w, sent to its window's native part."""
    win = w.window()
    QTest.mouseClick(win.windowHandle(), Qt.LeftButton, Qt.NoModifier, w.mapTo(win, at or QPoint(10, 10)))
    qt.pump(30)


def _mouse_in_use(page):
    """A click on the page where no control is (the corner of its view): the mouse is in use."""
    _click(page.page_area.viewport(), QPoint(2, 2))


def _round(page, w, by=4):
    """The window's picture round w (by px on each side: the frame's room and one more)."""
    return qt.picture(page).copy(_box(w).adjusted(-by, -by, by, by))


def _key(win, k, mod=Qt.NoModifier):
    QTest.keyClick(win.windowHandle(), k, mod)
    qt.pump(30)


def _tab_stop(c, win):
    return c.isVisibleTo(win) and c.isEnabled() and bool(c.focusPolicy() & Qt.TabFocus) and c.focusProxy() is None


def _tab_to(w):
    """The focus on w by a real Tab key, pressed on the control before it in the Tab order. Whether it got there."""
    win = w.window()
    win.activateWindow()
    qt.pump(30)
    prev = w.previousInFocusChain()
    for _ in range(5000):
        if prev is w or _tab_stop(prev, win):
            break
        prev = prev.previousInFocusChain()
    prev.setFocus(Qt.OtherFocusReason)
    QApplication.processEvents()
    for _ in range(30):
        _key(win, Qt.Key_Tab)
        if QApplication.focusWidget() is w:
            return True
    return False


def _backtab_to(w):
    """The focus on w by a real Shift+Tab, pressed on the control after it in the Tab order. Whether it got there."""
    win = w.window()
    win.activateWindow()
    qt.pump(30)
    nxt = w.nextInFocusChain()
    for _ in range(5000):
        if nxt is w or _tab_stop(nxt, win):
            break
        nxt = nxt.nextInFocusChain()
    nxt.setFocus(Qt.OtherFocusReason)
    QApplication.processEvents()
    _key(win, Qt.Key_Tab, Qt.ShiftModifier)
    return QApplication.focusWidget() is w


def _box(w):
    return QRect(w.mapTo(w.window(), QPoint(0, 0)), w.size())


def _rings(win):
    return [r for r in win.findChildren(QWidget, "focusFrame") if r.isVisible() and r.window() is win]


def _frame_on(w):
    """Is the frame on w, whole, in the window's picture? One frame in w's window, round w (at most 3 px from each of
    its sides), with the outer colour at the middle of its four edges and the inner colour inside the left one."""
    QApplication.processEvents()
    win = w.window()
    rings = _rings(win)
    if len(rings) != 1:
        return False
    outer, inner = _colours()
    g, b = QRect(rings[0].mapTo(win, QPoint(0, 0)), rings[0].size()), _box(w)
    near = (g.contains(b) and b.left() - g.left() <= 3 and b.top() - g.top() <= 3 and g.right() - b.right() <= 3
            and g.bottom() - b.bottom() <= 3)
    img = qt.picture(win)
    cx, cy = g.center().x(), g.center().y()
    seen = [img.pixelColor(x, y).name() for x, y in ((g.left(), cy), (g.right(), cy), (cx, g.top()), (cx, g.bottom()),
                                                     (g.left() + 1, cy), (g.left() + 2, cy))]
    return near and seen == [outer] * 5 + [inner]


def _no_frame(win):
    QApplication.processEvents()
    return not _rings(win)


def _quick(page):
    page.choose_app("apo")
    page.S["auto"]["enabled"] = False
    page.S["best_fit"].update(filter_counts=[3, 5], random_starts=0, gain_max=[6], q_max=[2], seed_with_site=False)
    page.set_way("auto", remember=False)


def _calculate_in_sight(page):
    page.resize(1000, 900)
    qt.pump(150)
    page.activateWindow()
    page.page_area.ensureWidgetVisible(page.run_btn, 0, 250)
    qt.pump(60)
    _mouse_up(page)


def _a_job(eq_screen, start):
    """A job started by start(), held while it runs (the page does not read its end), then let finish. What had the
    focus and the frame while it ran and when it was done."""
    page = eq_screen.page
    start()
    page._poll.stop()
    qt.pump(80)
    during = {"focus on Cancel": QApplication.focusWidget() is page.cancel_btn,
              "frame on Cancel": _frame_on(page.cancel_btn), "no frame": _no_frame(page)}
    page._poll.start()
    done = eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180)
    qt.pump(250)
    after = {"done": done, "focus on Calculate": QApplication.focusWidget() is page.run_btn,
             "frame on Calculate": _frame_on(page.run_btn), "no frame": _no_frame(page)}
    return during, after


def test_tab_shows_it_on_calculate_and_space_on_cancel(eq_screen, qapp, check):
    page = eq_screen.page
    _quick(page)
    seen = {}
    try:
        for look in ("light", "dark"):
            (qt.dark if look == "dark" else qt.light)(qapp)
            qt.pump(150)
            _calculate_in_sight(page)
            find = next(b for b in page.target_box.findChildren(QPushButton) if b.text() == "Find…")
            _mouse_in_use(page)
            page.run_btn.setFocus(Qt.OtherFocusReason)
            qt.pump(60)
            plain = _round(page, page.run_btn)
            d = {"no frame before a key": _no_frame(page), "Tab got to Calculate": _tab_to(page.run_btn),
                 "frame on Calculate": _frame_on(page.run_btn)}
            page.page_area.ensureWidgetVisible(page.run_btn, 0, 250)
            qt.pump(60)
            during, after = _a_job(eq_screen, lambda: _key(page, Qt.Key_Space))
            d["Space on Calculate, the job runs"] = during
            d["the job done"] = after
            page.page_area.ensureWidgetVisible(page.run_btn, 0, 250)
            qt.pump(60)
            _click(page.run_btn)
            page._poll.stop()
            qt.pump(80)
            by_mouse = {"focus on Cancel": QApplication.focusWidget() is page.cancel_btn, "no frame": _no_frame(page)}
            page._poll.start()
            by_mouse["done"] = eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180)
            qt.pump(250)
            by_mouse["focus on Calculate after"] = QApplication.focusWidget() is page.run_btn
            by_mouse["no frame after"] = _no_frame(page)
            d["a click on Calculate"] = by_mouse
            d["Tab got to Find…"] = _tab_to(find)
            page.page_area.ensureWidgetVisible(find, 0, 100)
            qt.pump(60)
            d["frame on Find…"] = _frame_on(find)
            seen[look] = d
            # (the page's picture with the mouse in use again is the one before the keyboard was used: Calculate
            # in sight at the same place, the focus on it by the code)
            _calculate_in_sight(page)
            _mouse_in_use(page)
            page.run_btn.setFocus(Qt.OtherFocusReason)
            qt.pump(60)
            now = _round(page, page.run_btn)
            seen[look]["pixels round Calculate different from before the keyboard"] = (
                sum(plain.pixel(x, y) != now.pixel(x, y) for x in range(now.width()) for y in range(now.height()))
                if plain.size() == now.size() else "another size")
    finally:
        qt.light(qapp)
        qt.pump(150)
    want = {"no frame before a key": True, "Tab got to Calculate": True, "frame on Calculate": True,
            "Space on Calculate, the job runs": {"focus on Cancel": True, "frame on Cancel": True, "no frame": False},
            "the job done": {"done": True, "focus on Calculate": True, "frame on Calculate": True, "no frame": False},
            "a click on Calculate": {"focus on Cancel": True, "no frame": True, "done": True,
                                     "focus on Calculate after": True, "no frame after": True},
            "Tab got to Find…": True, "frame on Find…": True,
            "pixels round Calculate different from before the keyboard": 0}
    check("eq page: Tab shows the focus frame on Calculate (the accent button) and on Find… (a push button); Space "
          "on Calculate starts the job, and the frame shows on Cancel, which has the focus while the job runs, then "
          "on Calculate again when the job is done; after a click on Calculate, Cancel and then Calculate have the "
          "focus with no frame; and with the mouse in use again, the pixels round Calculate are those from before "
          "the keyboard was used: light and dark", seen == {"light": want, "dark": want}, seen)


def _wheel(w, at=None, notch=-120):
    """One notch of the mouse wheel (towards the person: -120), the pointer on w, sent to its window's native part."""
    win = w.window()
    QTest.wheelEvent(win.windowHandle(), QPointF(w.mapTo(win, at or w.rect().center())), QPoint(0, notch))
    qt.pump(30)


def test_the_mouse_wheel_on_the_target_list(eq_screen, monkeypatch, check):
    # (the wheel gives a drop-down list the focus with no mouse button down: with the frame on Find…, the frame went
    # to the Target list; found by a verifier, 2026-11-16)
    page = eq_screen.page
    _calculate_in_sight(page)
    area, bar = page.page_area, page.page_area.verticalScrollBar()
    find = next(b for b in page.target_box.findChildren(QPushButton) if b.text() == "Find…")
    lst = page.target_combo
    was, chosen = lst.currentIndex(), []
    # (the notch also chooses the next target of the list: the page is kept from saving that and loading its curves)
    monkeypatch.setattr(page, "_file_chosen", chosen.append)
    mod = _frame_module()
    try:
        got = _tab_to(find)
        area.ensureWidgetVisible(find, 0, 100)
        qt.pump(60)
        seen = {"Tab to Find… of Target": {"Tab got there": got, "frame on Find…": _frame_on(find)}}
        _wheel(lst)
        seen["a notch on the Target list"] = {"the list has the focus": QApplication.focusWidget() is lst,
                                              "no frame": _no_frame(page),
                                              "the keyboard is not in use": mod is not None
                                              and not mod.keyboard_in_use()}
        _key(page, Qt.Key_Tab)
        f = QApplication.focusWidget()
        seen["Tab after it"] = {"the focus went on": f is not None and f is not lst,
                                "frame on the control with the focus": f is not None and _frame_on(f)}
        got = _tab_to(page.run_btn)
        top, view = bar.value(), area.viewport()
        d = {"frame on Calculate before": got and _frame_on(page.run_btn)}
        # (the pointer in the corner of the page's view, where no control is; the notch that takes Calculate towards
        # the middle of the view, so that it stays whole in it)
        low = page.run_btn.mapTo(view, QPoint(0, 0)).y() > view.height() // 2
        _wheel(view, QPoint(2, 2), -120 if low else 120)
        d.update({"the page moved": bar.value() != top, "Calculate keeps the focus":
                  QApplication.focusWidget() is page.run_btn, "frame on Calculate": _frame_on(page.run_btn)})
        seen["a notch on the page"] = d
    finally:
        lst.setCurrentIndex(was)
        _mouse_in_use(page)
    want = {"Tab to Find… of Target": {"Tab got there": True, "frame on Find…": True},
            "a notch on the Target list": {"the list has the focus": True, "no frame": True,
                                           "the keyboard is not in use": True},
            "Tab after it": {"the focus went on": True, "frame on the control with the focus": True},
            "a notch on the page": {"frame on Calculate before": True, "the page moved": True,
                                    "Calculate keeps the focus": True, "frame on Calculate": True}}
    check("eq page: with the focus frame on Find… of Target, a notch of the mouse wheel on the Target list gives the "
          "list the focus and no frame (the wheel moves the focus with no mouse button down: the frame went to the "
          "list), and Tab then shows the frame on the next control; a notch on the page, where no control is, moves "
          "the page and the frame stays on Calculate", seen == want,
          {k: v for k, v in seen.items() if v != want.get(k)})


def test_the_first_row_of_the_filter_table(eq_screen, check):
    from ui.search_combo import SearchCombo
    page = eq_screen.page
    _quick(page)
    if not page.current()[1]:
        eqpage.quick_run(eq_screen)
    page.set_view("table", remember=False)
    page.resize(1000, 900)
    qt.pump(150)
    page.activateWindow()
    _mouse_up(page)
    crosses = [b for b in page.editor.findChildren(QToolButton) if b.text() == "✕" and b.isVisible()]
    types = [c for c in page.editor.findChildren(SearchCombo) if c.isVisible()]
    seen = {}
    # (Tab reaches the ✕; from there Tab goes on in the table's next row, so the type's list of the first row is
    # reached with Shift+Tab from the frequency box after it)
    for name, w, reach in (("the ✕ of the first row", crosses[0] if crosses else None, _tab_to),
                           ("the type of the first row", types[0] if types else None, _backtab_to)):
        if w is None:
            seen[name] = "not there"
            continue
        got = reach(w)
        page.page_area.ensureWidgetVisible(w, 0, 120)
        qt.pump(60)
        ring = _rings(page)
        view = w.parentWidget()
        seen[name] = {"a key got there": got, "frame, whole": _frame_on(w),
                      "no room above it in the table's view": w.mapTo(view, QPoint(0, 0)).y() < 3,
                      "the frame is in the table's view": bool(ring) and ring[0].parentWidget() is view}
    want = {"a key got there": True, "frame, whole": True, "no room above it in the table's view": True,
            "the frame is in the table's view": True}
    check("eq page: the ✕ button (Tab) and the type's drop-down list (Shift+Tab) in the first row of the filter "
          "table get the focus frame, whole on its four sides, in the table's view (the view has no room above its "
          "first row: the frame's top line comes in to the view's edge)",
          seen == {"the ✕ of the first row": want, "the type of the first row": want}, seen)


def test_a_click_outside_a_menu_takes_it_off(eq_screen, check):
    # (a menu takes the clicks itself and moves no focus: the frame of its button stayed after a click in the menu,
    # found with a made-up window, 2026-11-16; here the page's own Use on device, with the theme's own filter)
    page = eq_screen.page
    _quick(page)
    if not page.current()[1]:
        eqpage.quick_run(eq_screen)
    page.resize(1000, 900)
    qt.pump(150)
    page.activateWindow()
    _mouse_up(page)
    btn, menu = page.use_btn, page.use_menu
    seen = {}
    for case in ("a click outside the menu", "Esc in the menu"):
        got = _tab_to(btn)
        page.page_area.ensureWidgetVisible(btn, 0, 150)
        qt.pump(60)
        d = {"frame on Use on device before": got and _frame_on(btn)}
        acted = []

        def act(n=0, case=case, acted=acted):
            if menu.isVisible():
                if case.startswith("a click"):
                    QTest.mouseClick(menu.windowHandle(), Qt.LeftButton, Qt.NoModifier, QPoint(-30, -30))
                else:
                    QTest.keyClick(menu.windowHandle(), Qt.Key_Escape)
                acted.append(True)
            elif n < 200:
                QTimer.singleShot(20, lambda: act(n + 1))
            else:
                acted.append(False)
        QTimer.singleShot(20, act)
        QTimer.singleShot(int(qt.time_limit(8) * 1000), menu.close)  # (never left open: Qt stays in an open menu)
        _key(page, Qt.Key_Space)
        qt.wait_for(lambda acted=acted: bool(acted) and not menu.isVisible(), 8)
        qt.pump(60)
        d["the menu showed and closed"] = acted == [True] and not menu.isVisible()
        d["the focus is on Use on device"] = QApplication.focusWidget() is btn
        if case.startswith("a click"):
            d["no frame"] = _no_frame(page)
        else:
            d["the frame is on it"] = _frame_on(btn)
        seen[case] = d
    _mouse_in_use(page)
    check("eq page: with the frame on Use on device and its menu opened with Space, a click outside the menu closes "
          "the menu and takes the frame off (the focus stays on the button); after Esc in the menu, the frame is on "
          "the button", all(all(d.values()) for d in seen.values()) and len(seen) == 2, seen)


def test_sliders_keep_their_own_ring_and_the_floating_graph_is_above(eq_screen, check):
    page = eq_screen.page
    _quick(page)
    if not page.current()[1]:
        eqpage.quick_run(eq_screen)
    page.resize(1000, 900)
    qt.pump(150)
    page.activateWindow()
    _mouse_up(page)
    page.set_live_graph_on(True)
    page.set_view("sliders", remember=False)
    qt.pump(100)
    area = page.page_area
    try:
        sliders = page.editor.sliders_scroll.widget().findChildren(QSlider)
        area.ensureWidgetVisible(page.editor, 0, 20)  # (the filters in sight, the graph scrolled away)
        qt.pump(80)
        got = _tab_to(sliders[0])
        own = {"Tab got to a gain slider": got, "no focus frame": _no_frame(page),
               "it says that it draws its own focus": sliders[0].property("ownFocus") is True}
        _key(page, Qt.Key_Up)  # (an edit with the graph out of sight: the graph floats over the page)
        qt.pump(120)
        lg = getattr(page, "live_graph", None)
        floats = lg is not None and lg.isVisible()
        table_tab = page.view_btns["table"]
        table_tab.setFocus(Qt.OtherFocusReason)  # (the keyboard is in use: the frame goes to a control of the page)
        qt.pump(60)
        ring = _rings(page)
        kids = area.viewport().findChildren(QWidget, options=Qt.FindDirectChildrenOnly)
        above = {"the graph floats": floats and lg.isVisible(),
                 "a frame on a control of the page": bool(ring) and (_frame_module() is not None
                                                                     and _frame_module().framed() is table_tab),
                 "both in the page's view": bool(ring) and ring[0].parentWidget() is area.viewport()
                 and lg is not None and lg.parentWidget() is area.viewport(),
                 "the graph is above the frame": bool(ring) and lg in kids and kids.index(lg) > kids.index(ring[0])}
    finally:
        page.set_view("table", remember=False)
        page.undo_all()
        area.verticalScrollBar().setValue(0)
        qt.pump(80)
    check("eq page: a gain slider of the filter editor keeps its own ring round its thumb and gets no focus frame "
          "(it says that it draws its own keyboard focus: the property ownFocus)",
          own == {"Tab got to a gain slider": True, "no focus frame": True,
                  "it says that it draws its own focus": True}, own)
    check("eq page: the graph that floats over the page while the filters are edited is above the focus frame of a "
          "control of the page (the frame is put directly above the page, not above all that is in the view)",
          all(above.values()), above)


def test_the_guide_and_the_frame(eq_screen, check):
    import shiboken6
    from ui import guide
    page = eq_screen.page
    _calculate_in_sight(page)
    seen = {}
    for case in ("Esc ends the Guide", "a click on its ✕ ends the Guide"):
        _calculate_in_sight(page)
        got = _tab_to(page.run_btn)
        page.page_area.ensureWidgetVisible(page.run_btn, 0, 250)
        qt.pump(60)
        d = {"frame on Calculate before": got and _frame_on(page.run_btn)}
        t = guide.start_eq(page)
        t.all_chk.setChecked(False)
        qt.pump(150)
        d["no frame while the Guide shows"] = _no_frame(page)
        _key(page, Qt.Key_Right)  # (the next step)
        qt.pump(150)
        d["no frame on its next step"] = t.i == 1 and _no_frame(page)
        if case.startswith("Esc"):
            _key(page, Qt.Key_Escape)
        else:
            _click(t.end_btn, QPoint(t.end_btn.width() // 2, t.end_btn.height() // 2))
        qt.pump(150)
        f = QApplication.focusWidget()
        mod = _frame_module()
        gets = mod is not None and f is not None and mod.FocusFrame.wants(f)
        d["the Guide closed"] = not shiboken6.isValid(t) or not t.isVisible()
        d["a control of the page has the focus"] = f is not None and page.isAncestorOf(f)
        if case.startswith("Esc"):
            d["the frame is on it, if it is a control that gets one"] = _frame_on(f) if gets else _no_frame(page)
        else:
            d["no frame"] = _no_frame(page)
        seen[case] = d
    page.page_area.verticalScrollBar().setValue(0)
    qt.pump(60)
    check("guide: while the Guide shows, the page under it has no focus frame (the Guide keeps the focus), also on "
          "its next step; ended with Esc, the control of the page that gets the focus has the frame (the keyboard "
          "is in use); ended with a click on its ✕, there is no frame",
          all(all(d.values()) for d in seen.values()) and len(seen) == 2, seen)


@pytest.mark.timeout(600)
def test_each_window_of_the_page(eq_screen, check):
    import net
    from PySide6.QtWidgets import QMessageBox
    from ui.all_results import AllResults
    from ui.compare_results import CompareResults
    from ui.compare_window import CompareWindow
    from ui.history_window import HistoryWindow
    from ui.picker import Picker
    from ui.picture_wait import PictureWait
    from ui.queue_window import QueueWindow
    from ui.sources_window import Sources
    page = eq_screen.page
    _quick(page)
    if not page.current()[1]:
        eqpage.quick_run(eq_screen)
    mod = _frame_module()
    net.set_offline(True)
    seen = {}
    # (the keyboard in use on the page, as when a key opens each of these windows)
    page.resize(1000, 900)
    qt.pump(150)
    on_page = _tab_to(page.run_btn)
    page.page_area.ensureWidgetVisible(page.run_btn, 0, 250)
    qt.pump(60)
    on_page = on_page and _frame_on(page.run_btn)

    def look(win, f, bad):
        if mod is not None and mod.FocusFrame.wants(f):
            if not _frame_on(f):
                bad.append(f"no whole frame on {type(f).__name__} {getattr(f, 'text', lambda: '')()!r}")
            return 1
        if not _no_frame(win):
            bad.append(f"a frame with the focus on {type(f).__name__}")
        return 0

    def tabs(win, name, n=8):
        """Whether win, just opened, shows no frame (no key was pressed in it yet); then Tab pressed n times in it (a
        table keeps Tab for its cells, so Tab does not get to each control), then the focus given, as the app gives
        it, to each of up to 8 of the window's controls that get the frame and are all in sight: for each one,
        whether the frame is on it, whole; with the focus on a control of another type, whether no frame shows."""
        win.activateWindow()
        qt.pump(120)
        _mouse_up(win)
        by_tab, by_code, bad = 0, 0, []
        before = _no_frame(win)
        for _ in range(n):
            _key(win, Qt.Key_Tab)
            f = QApplication.focusWidget()
            if f is not None and f.window() is win:
                by_tab += look(win, f, bad)
        keyboard = mod is not None and mod.keyboard_in_use()
        for c in [c for c in win.findChildren(QWidget) if c.window() is win and _tab_stop(c, win)
                  and mod is not None and mod.FocusFrame.wants(c) and c.visibleRegion().boundingRect() == c.rect()][:8]:
            c.setFocus(Qt.OtherFocusReason)
            qt.pump(20)
            if QApplication.focusWidget() is c:
                by_code += look(win, c, bad)
        seen[name] = {"no frame before a key in it": before, "the keyboard in use after Tab": keyboard,
                      "with the frame after Tab": by_tab, "with the frame, the focus given by the app": by_code,
                      "faults": bad}

    for name, make in (("All results", lambda: AllResults(page)), ("Compare", lambda: CompareResults(page)),
                       ("Queue", lambda: QueueWindow(page)), ("History", lambda: HistoryWindow(page, False)),
                       ("Find…", lambda: Picker(page, "measurement")), ("Sources", lambda: Sources(page)),
                       ("Which measurement", lambda: CompareWindow(page))):
        w = make()
        w.show()
        qt.pump(300)
        if name == "Sources":
            w._refresh_soon.stop()
        tabs(w, name)
        w.close()
        qt.pump(50)
    pk = Picker(page, "measurement")
    pk.show()
    wait = PictureWait(pk, {"name": "Truthear Gate", "site": "Hangout.Audio 5128"})
    wait.show()
    qt.pump(300)
    tabs(wait, "the wait for a picture", 3)
    wait.close()
    pk.close()
    qt.pump(50)
    page.open_trace()
    tw = page.tracer
    qt.pump(300)
    tabs(tw, "the tracer", 6)
    tw.close()
    qt.pump(50)
    box = QMessageBox(QMessageBox.Question, "Clear the history", "Do you want to delete all the entries?",
                      QMessageBox.Yes | QMessageBox.No, page)
    box.show()
    qt.pump(200)
    tabs(box, "a question", 3)
    box.close()
    box.deleteLater()
    qt.pump(50)
    page.activateWindow()
    qt.pump(60)
    check("eq windows: All results, Compare, Queue, History, Find…, Sources, Which measurement, the wait for a "
          "picture, the tracer and a question, each opened with the frame on Calculate (the keyboard in use), show "
          "no frame before a key is pressed in them (the frame was among the parts of Sources, which a test of its "
          "parts found); then, after Tab, each button, tick box, drop-down list and slider that gets the focus (from "
          "Tab, or from the app) has the focus frame, whole on its four sides in the window's picture, and no frame "
          "shows while a control of another type has the focus",
          on_page and len(seen) == 10 and all(
              v["no frame before a key in it"] and v["the keyboard in use after Tab"] and not v["faults"]
              and v["with the frame, the focus given by the app"] >= 1 for v in seen.values()),
          {"frame on Calculate before": on_page, **seen})


def test_one_move_of_the_focus_on_the_page(eq_screen, check):
    page = eq_screen.page
    _calculate_in_sight(page)
    got = _tab_to(page.run_btn)
    pair = (page.run_btn, page.queue_btn)
    took = []
    for i in range(200):
        t0 = time.perf_counter()
        pair[i % 2].setFocus(Qt.OtherFocusReason)
        took.append(time.perf_counter() - t0)
    shown = _frame_on(QApplication.focusWidget())
    median = statistics.median(took) * 1e6
    _mouse_in_use(page)
    check("eq page: with the focus frame shown, one move of the focus between two buttons of the page takes less "
          "than 1 ms (the median of 200 moves)", got and shown and median < qt.time_limit(1000),
          {"Tab got to Calculate": got, "frame shown": shown, "microseconds": round(median, 1)})
