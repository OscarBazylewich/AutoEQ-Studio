"""Make an EQ's floating graph while a job runs (ui\\eq_page_live.py's place_live_graph, ui\\eq_page_result.py's run
and _poll_job; the verifier's find, 2026-11-16). The graph floats at the top of the page's view, at its right, 560 px
wide. In the window's smallest width (841 px: a view of 829 px) that place was over Cancel, which a job shows after
Calculate and Queue…: over all 90 px of it (measured), so no click could stop a job begun while the graph showed (an
edit of the filters, then Calculate from these filters or Calculate). Now the graph makes way for Cancel: it goes
while a job runs and its place is over Cancel, and it is back in its place when the job ends. In a wider window, where
its place is beside Cancel, it stays. One page for the file (the eq_screen fixture)."""
import numpy as np
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

from helpers import eqpage, qt

# (px: the main window's smallest width with Make an EQ shown, at 100 % scale; a width where the floating graph's place
# is beside Cancel: it is from 946 px, calculated from the places measured at 841 px; a height in which Calculate's row
# and the filters are in view together)
NARROW, WIDE, HIGH = 841, 1200, 700
SIZE = (1000, 900)  # (the page's size in the eq_screen fixture)


def _in_view(page, w):
    """Where a control is in the page's view."""
    return QRect(w.mapTo(page.page_area.viewport(), QPoint(0, 0)), w.size())


def _box(r):
    return (r.x(), r.y(), r.width(), r.height())


def _edited(eq_screen, width):
    """The page this wide with a result, Calculate's row at the top of its view, and one edit of the filters (a click
    on Add filter). The floating graph (None if the page made none) and where it is (None if it does not show)."""
    page = eq_screen.page
    page.choose_app("apo")
    page.set_way("auto", remember=False)
    if page.run_result is None or page.run_result.get("mode") != "best_fit":
        eqpage.quick_run(eq_screen)
    page.set_live_graph_on(True)
    page.set_view("table", remember=False)
    page.resize(width, HIGH)
    page.activateWindow()
    qt.pump(250)
    area = page.page_area
    area.verticalScrollBar().setValue(page.run_btn.mapTo(area.widget(), QPoint(0, 0)).y() - 10)
    area.horizontalScrollBar().setValue(0)
    qt.pump(100)
    add = next(b for b in page.result_box.findChildren(QPushButton) if b.text() == "Add filter")
    QTest.mouseClick(add, Qt.LeftButton)
    qt.pump(150)
    lg = getattr(page, "live_graph", None)
    return lg, (_in_view(page, lg) if lg is not None and lg.isVisible() else None)


def _while_it_runs(page, lg):
    """A job just begun, its end not read yet (the caller stopped the page's timer for it): Cancel and the floating
    graph in the page's view, and the control that a click at Cancel's middle goes to (the one on top there)."""
    qt.pump(100)
    at = page.cancel_btn.mapTo(page, page.cancel_btn.rect().center())
    return {"Cancel": _in_view(page, page.cancel_btn), "Cancel shows": page.cancel_btn.isVisible(),
            "graph": _in_view(page, lg) if lg is not None and lg.isVisible() else None,
            "at": at, "on top": page.childAt(at)}


def _named(w):
    if w is None:
        return None
    words = w.text() if callable(getattr(w, "text", None)) else ""
    return f"{type(w).__name__} {words or w.accessibleName()!r}"


def _told(d):
    """What _while_it_runs saw, as a check's detail has it."""
    return {"Cancel": _box(d["Cancel"]), "graph": d["graph"] and _box(d["graph"]),
            "on top at Cancel": _named(d["on top"])}


def _tidy(page):
    """A job that still goes on ended (its timer on again, waited for), the edit undone, no floating graph, the page's
    size back."""
    if not page.run_btn.isEnabled():
        page._poll.start()
        qt.wait_for(lambda: page.run_btn.isEnabled(), 180)
    qt.pump(150)
    page.undo_all()
    page.hide_live_graph()
    page.resize(*SIZE)
    qt.pump(200)


def test_cancel_is_clear_of_the_floating_graph_in_the_smallest_width(eq_screen, check):
    page = eq_screen.page
    clicks = []
    count = lambda *_: clicks.append(1)
    page.cancel_btn.clicked.connect(count)
    try:
        lg, floated = _edited(eq_screen, NARROW)
        # (the button's menu closed, the focus is on the button again when its action starts the run: Qt's menu)
        page.retry_btn.setFocus(Qt.MouseFocusReason)
        add_more = page.retry_btn.menu().actions()[1]
        add_more.trigger()
        page._poll.stop()  # (Cancel kept in sight until it is clicked, however soon the job ends: read when it starts)
        seen = _while_it_runs(page, lg)
        target = seen["on top"]
        if target is not None:  # (a click where Cancel is, as the mouse gives it: to the control on top there)
            QTest.mouseClick(target, Qt.LeftButton, Qt.NoModifier, target.mapFrom(page, seen["at"]))
        page._poll.start()
        stopped = eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180)
        qt.pump(200)
        back = lg is not None and lg.isVisible()
        words = page.progress_text.text()
    finally:
        page.cancel_btn.clicked.disconnect(count)
        _tidy(page)
    check("live graph: in the window's smallest width (841 px), a job begun with Calculate from these filters while "
          "the graph floats over the page shows Cancel clear of it (the graph's place was over all of Cancel: it goes "
          "while the job runs), and a click at Cancel's middle goes to Cancel",
          add_more.text() == "Keep them and add filters" and floated is not None and seen["Cancel shows"]
          and floated.intersects(seen["Cancel"]) and seen["graph"] is None and target is page.cancel_btn
          and clicks == [1],
          (add_more.text(), floated and _box(floated), _told(seen), clicks, words))
    check("live graph: when the job has stopped, the graph floats over the page again",
          stopped and back, (stopped, back, words))


def test_the_floating_graph_is_back_when_a_job_from_calculate_is_done(eq_screen, check):
    page = eq_screen.page
    try:
        lg, floated = _edited(eq_screen, NARROW)
        before = page.run_result
        QTest.mouseClick(page.run_btn, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
        page._poll.stop()  # (the page kept as it is while the job runs, however soon the job ends)
        seen = _while_it_runs(page, lg)
        page._poll.start()
        done = eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180) and page.run_result is not before
        qt.pump(250)  # (the result card is scrolled into sight 0 ms after the job's end)
        back = lg is not None and lg.isVisible()
        new_curves = back and np.allclose(lg.shown[3], page._live_series["with"])
    finally:
        _tidy(page)
    check("live graph: in the window's smallest width, a job begun with Calculate while the graph floats over the "
          "page shows Cancel clear of it (the graph goes while the job runs), a click at Cancel's middle would go to "
          "Cancel, and when the job is done the graph floats again, with the new result's curves",
          floated is not None and seen["Cancel shows"] and floated.intersects(seen["Cancel"]) and seen["graph"] is None
          and seen["on top"] is page.cancel_btn and done and back and new_curves,
          (floated and _box(floated), _told(seen), done, back, new_curves))


def test_the_floating_graph_stays_beside_cancel_in_a_wide_window(eq_screen, check):
    page = eq_screen.page
    try:
        lg, floated = _edited(eq_screen, WIDE)
        page.retry_btn.setFocus(Qt.MouseFocusReason)
        page.retry_btn.menu().actions()[1].trigger()
        page._poll.stop()  # (the page kept as it is while the job runs, however soon the job ends)
        seen = _while_it_runs(page, lg)
    finally:
        _tidy(page)
    check("live graph: in a window 1200 px wide, where its place is beside Cancel, the floating graph stays in its "
          "place while a job runs, and a click at Cancel's middle would go to Cancel",
          floated is not None and seen["Cancel shows"] and seen["graph"] == floated
          and not floated.intersects(seen["Cancel"]) and seen["on top"] is page.cancel_btn,
          (floated and _box(floated), _told(seen)))
