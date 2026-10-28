"""Make an EQ's graph while you edit the filters (ui\\eq_page_live.py; the user's ask, 2026-10-27: changing a slider
or a table's value far below the graph, its result couldn't be seen): it floats over the page with an edit while the
graph is out of sight, clear of the filters (or of the control in use), following each edit with the page's own
curves; it goes when the graph comes back into sight; the tick box beside the filters' tools, or its ✕, turns it off
and that's kept. One page for the file (the eq_screen fixture), a run's result on its card."""
import numpy as np
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QSlider, QToolButton

from helpers import eqpage, qt


def _rect(page, w):
    vp = page.page_area.viewport()
    return QRect(w.mapTo(vp, QPoint(0, 0)), w.size())


def _ready(eq_screen):
    """A result on the card, the Sliders view, the floating graph on; its sliders."""
    page = eq_screen.page
    if not page.current()[1]:
        eqpage.quick_run(eq_screen)
    page.set_live_graph_on(True)
    page.set_view("sliders", remember=False)
    qt.pump(100)
    return page.editor.sliders_scroll.widget().findChildren(QSlider)


def _nudge(page, s, by=5):
    s.setFocus()
    s.setValue(s.value() + by)
    qt.pump(80)


def test_floats_over_the_page_while_the_graph_is_out_of_sight(eq_screen, check):
    page = eq_screen.page
    sl = _ready(eq_screen)
    area = page.page_area
    try:
        area.verticalScrollBar().setValue(0)  # (the graph in sight)
        qt.pump(80)
        _nudge(page, sl[0])
        lg = getattr(page, "live_graph", None)
        with_graph = lg is not None and lg.isVisible()
        area.ensureWidgetVisible(page.editor, 0, 20)  # (the filters in sight, the graph scrolled away)
        qt.pump(80)
        _nudge(page, sl[0])
        lg = page.live_graph
        shown = lg.isVisible()
        clear = not _rect(page, lg).intersects(_rect(page, sl[0]))
        first = np.array(lg.shown[3])
        same = np.allclose(first, page._live_series["with"])
        _nudge(page, sl[0], 30)
        follows = not np.allclose(np.array(lg.shown[3]), first) and np.allclose(lg.shown[3], page._live_series["with"])
        area.verticalScrollBar().setValue(0)  # (back to the graph)
        qt.pump(80)
        gone = not lg.isVisible()
    finally:
        page.set_view("table", remember=False)
        page.revert()
    check("live graph: an edit while the graph is in sight shows nothing more; with the graph scrolled away, the graph "
          "floats over the page clear of the slider in use, with the page's own curves, and follows the next edit; "
          "scrolled back to the graph, it goes",
          not with_graph and shown and clear and same and follows and gone,
          (with_graph, shown, clear, same, follows, gone))


def test_clear_of_the_filters_at_the_top(eq_screen, check):
    # (the filters at the top of what's shown: at the top it went over the sliders beside the one held)
    page = eq_screen.page
    sl = _ready(eq_screen)
    area = page.page_area
    try:
        y = page.editor.mapTo(area.widget(), QPoint(0, 0)).y()
        area.verticalScrollBar().setValue(y)  # (the filters' top at the top of what's shown)
        qt.pump(80)
        _nudge(page, sl[0])
        lg = page.live_graph
        r, vp = _rect(page, lg), area.viewport().rect()
        place = (lg.isVisible(), r.bottom() > vp.center().y(), r.intersects(_rect(page, page.editor).intersected(vp)))
    finally:
        page.set_view("table", remember=False)
        page.revert()
        page.hide_live_graph()
    check("live graph: with the filters at the top of what's shown, it floats at the bottom, clear of them",
          place[0] and place[1] and not place[2], place)


def test_turned_off_and_kept(eq_screen, check):
    page, sw = eq_screen.page, eq_screen.sw
    sl = _ready(eq_screen)
    area = page.page_area
    try:
        area.ensureWidgetVisible(page.editor, 0, 20)
        qt.pump(80)
        page.live_check.setChecked(False)
        _nudge(page, sl[0])
        off = (getattr(page, "live_graph", None) is None or not page.live_graph.isVisible(), sw.s.get("live_graph"))
        page.live_check.setChecked(True)
        _nudge(page, sl[0])
        on = page.live_graph.isVisible()
        x = next(b for b in page.live_graph.findChildren(QToolButton) if b.text() == "✕")
        x.click()
        qt.pump(50)
        closed = (not page.live_graph.isVisible(), page.live_check.isChecked(), sw.s.get("live_graph"))
    finally:
        page.set_live_graph_on(True)
        page.set_view("table", remember=False)
        page.revert()
    check("live graph: unticked, an edit shows nothing and that's kept; ticked again it floats with the next edit; "
          "its ✕ hides it and turns it off (the tick box unticked, kept)",
          off == (True, False) and on and closed == (True, False, False), (off, on, closed))
