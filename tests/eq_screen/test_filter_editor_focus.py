"""The focus in the filters' editor of Make an EQ (ui\\filter_editor.py's rebuild) when a filter's ✕ or the Sliders
view's On tick box makes the rows again (2026-11-13, measured with the fault of Calculate: the page went to its top).
The rebuild deleted the control with the focus, and the focus went to no control (a keyboard user's place lost).
Now the focus goes to the new control of the same name ("Remove filter 1": the next filter's ✕), else to
the filter before it (the last filter's ✕), else to Add filter (no filters left). One page for the file (the
eq_screen fixture), an EQ made by hand with 3 filters."""
import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QWidget

from helpers import qt

FILTERS = [{"type": "PK", "freq": f, "gain": g, "q": 1.0} for f, g in ((100, -2.0), (1000, 3.0), (5000, -4.0))]


@pytest.fixture
def hand(eq_screen):
    """An EQ by hand with 3 filters on the result card, in this view; the window active (a key goes to an active window
    only)."""
    page = eq_screen.page

    def make(view):
        page.start_manual([dict(f) for f in FILTERS], "pasted", "Focus")
        page.set_view(view, remember=False)
        page.activateWindow()
        page.page_area.ensureWidgetVisible(page.editor, 0, 40)
        qt.pump(80)
        return page
    yield make
    page.close_manual()


def _named(page, name):
    return next((w for w in page.editor.findChildren(QWidget) if w.accessibleName() == name and w.isVisible()), None)


def _press(page, name):
    """The editor's control of that name pressed with the focus on it, put there as Tab puts it (a ✕ takes no focus
    from a click: a keyboard user's way; its Space is a click of the button. QTest's Space let Qt make the rows again
    inside the key, and then used the deleted tick box). The page's position before and after, and the control with
    the focus after (its class and name: the next rebuild deletes it)."""
    w = _named(page, name)
    w.setFocus(Qt.TabFocusReason)
    bar = page.page_area.verticalScrollBar()
    at = bar.value()
    w.click()
    qt.pump(120)  # (the Sliders view's On makes the rows again 0 ms later)
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)  # (the old rows gone, as Qt deletes them)
    qt.pump(30)
    return at, bar.value(), _said(QApplication.focusWidget())


def _said(w):
    """A control as the checks name it: its class and name, and whether it shows (the old ✕ waited hidden for Qt to
    delete it)."""
    if w is None:
        return None
    return type(w).__name__, w.accessibleName() or (w.text() if hasattr(w, "text") else ""), w.isVisible()


def test_table_x_gives_the_focus_to_the_next_filter(hand, check):
    page = hand("table")
    first = _press(page, "Remove filter 1")
    last = _press(page, "Remove filter 2")  # (2 filters left: the last one's ✕)
    only = _press(page, "Remove filter 1")  # (1 filter left)
    check("filters: ✕ in the table gives the focus to the next filter's ✕, or to the filter before it for the last "
          "filter, or to Add filter when no filters are left; the page stays where it is (the focus went to no "
          "control)",
          [f[2] for f in (first, last, only)] == [("QToolButton", "Remove filter 1", True),
                                                   ("QToolButton", "Remove filter 1", True),
                                                   ("QPushButton", "Add filter", True)]
          and all(f[0] == f[1] for f in (first, last, only)) and page.EDIT == [],
          [first, last, only])


def test_sliders_on_and_x_keep_the_focus(hand, check):
    page = hand("sliders")
    on = _press(page, "Filter 2 on")
    x = _press(page, "Remove filter 3")
    check("filters: in the Sliders view, On keeps the focus on the filter's new On tick box, and ✕ of the last filter "
          "gives it to the filter before it; the page stays where it is (the focus went to no control)",
          on[2] == ("QCheckBox", "Filter 2 on", True) and x[2] == ("QToolButton", "Remove filter 2", True)
          and page.EDIT[1].get("enabled") is False and len(page.EDIT) == 2 and on[0] == on[1] and x[0] == x[1],
          [on, x])


def test_your_filters_window_gives_the_focus_to_add_filter(eq_screen, check, monkeypatch):
    # (Best fit's Your filters window has the same editor, and its own Add filter)
    from PySide6.QtWidgets import QDialog
    from ui.filter_editor import FilterEditor
    page = eq_screen.page
    seen = {}

    def shown(dlg):
        dlg.show()
        dlg.activateWindow()
        qt.pump(200)
        ed = dlg.findChild(FilterEditor)
        x = next(w for w in ed.findChildren(QWidget) if w.accessibleName() == "Remove filter 1" and w.isVisible())
        x.setFocus(Qt.TabFocusReason)
        x.click()
        qt.pump(100)
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        qt.pump(30)
        seen["focus"] = _said(QApplication.focusWidget())
        seen["filters"] = len(ed.filters)
        dlg.hide()
        return QDialog.Rejected  # (Cancel: your own filters stay as they were)
    kept = page.S["best_fit"]["start_filters"]
    monkeypatch.setattr(QDialog, "exec", shown)
    try:
        page.S["best_fit"]["start_filters"] = "Filter 1: ON PK Fc 1000 Hz Gain 2 dB Q 1"
        page.settings.edit_your_filters()
    finally:
        page.S["best_fit"]["start_filters"] = kept
    check("filters: in Your filters, ✕ of the only filter gives the focus to the window's Add filter (it went to no "
          "control)", seen == {"focus": ("QPushButton", "Add filter", True), "filters": 0}, seen)


def test_a_focus_out_of_the_editor_stays_there(hand, check):
    # (2026-11-15, the verifier: the editor gives the focus again only when one of its own controls had it. A
    # double-click on the EQ graph adds a filter and makes the rows again while the graph, out of the editor, has the
    # focus: the focus stays on the graph, not on Add filter)
    import math
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtTest import QTest
    page = hand("table")
    graph = page.eqplot
    page.page_area.ensureWidgetVisible(graph, 0, 40)
    qt.pump(50)
    n = len(page.EDIT)
    vp = graph.viewport()
    at = graph.mapFromScene(graph.getPlotItem().vb.mapViewToScene(QPointF(math.log10(300), -6.0)))  # (no handle)
    QTest.mouseClick(vp, Qt.LeftButton, Qt.NoModifier, at)  # (a click gives the graph the focus)
    qt.pump(50)
    had = QApplication.focusWidget() is graph
    # (the double-click as test_eq_graph_handles.py sends it: QTest's gives the graph no double-click)
    for kind, buttons in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton),
                          (QEvent.MouseButtonDblClick, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        QApplication.sendEvent(vp, QMouseEvent(kind, QPointF(at), QPointF(vp.mapToGlobal(at)), Qt.LeftButton,
                                               buttons, Qt.NoModifier))
    qt.pump(120)
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qt.pump(30)
    f = QApplication.focusWidget()
    check("filters: a double-click on the EQ graph adds a filter, and the focus stays on the graph (it went to Add "
          "filter)", had and len(page.EDIT) == n + 1 and f is graph, (had, n, len(page.EDIT), _said(f)))
