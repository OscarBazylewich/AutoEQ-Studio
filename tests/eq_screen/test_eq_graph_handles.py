"""Make an EQ's EQ graph as a place to edit the filters (ui\\eq_page_handles.py, 2026-10-26): a handle for each filter
on its own curve (a shelf's half way up), numbered, a switched-off one hollow; dragged with the mouse (real mouse
events sent to the graph: the pointer itself never moves) its filter's frequency and gain follow, and the table and
numbers with it, while the handle stays in hand and the scale stays put; let go, the graph is drawn again with it
there; the mouse wheel over one changes its Q; right-click gives its type, on or off and Delete; a double-click where
there's none adds a filter (with no EQ shown, an EQ by hand begins with it); an EQ tried on a device follows the
edits (its file written again), but never a Guide demo's. One page for the file (the eq_screen fixture)."""
import math
import os

from helpers import eqpage

FILTERS = [{"type": "PK", "freq": 1000, "gain": 4, "q": 1.0}, {"type": "LSQ", "freq": 100, "gain": 6, "q": 0.7},
           {"type": "HSQ", "freq": 8000, "gain": -3, "q": 0.7, "enabled": False}]


def _fresh(page):
    page.start_by_hand([dict(f) for f in FILTERS], "pasted", "Handles")
    page.set_view("table", remember=False)


def _px(page, x, y):
    """The graph's pixel (its viewport's) for a point of the EQ graph (log10 Hz, dB)."""
    from PySide6.QtCore import QPointF
    vb = page.eqplot.getPlotItem().vb
    return page.eqplot.mapFromScene(vb.mapViewToScene(QPointF(x, y)))


def _mouse(page, kind, pt, buttons, button=None):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    vp = page.eqplot.viewport()
    ev = QMouseEvent(kind, QPointF(pt), QPointF(vp.mapToGlobal(pt)), button if button is not None else Qt.NoButton,
                     buttons, Qt.NoModifier)
    QApplication.sendEvent(vp, ev)


def test_handles_on_their_curves(eq_screen, check):
    page = eq_screen.page
    _fresh(page)
    eq_screen.qapp.processEvents()
    got = [(round(h.pos().x(), 4), round(h.pos().y(), 4), h.label().toPlainText() if h.label() else "") for h in page._handles]
    off = page._handles[2].brush.color().name() != page._handles[0].brush.color().name()
    check("handles: one per filter of the EQ shown, on its own curve at its frequency (a shelf half way up: half its "
          "gain), numbered as in the table; a switched-off one drawn hollow",
          got == [(3.0, 4.0, "1"), (2.0, 3.0, "2"), (round(math.log10(8000), 4), -1.5, "3")] and off, (got, off))


def _number(h):
    """Where a handle's number shows on the screen: its text, without the empty margin around it."""
    lab = h.label()
    m = lab.textItem.document().documentMargin()
    return lab.textItem.mapRectToScene(lab.textItem.boundingRect().adjusted(m, m, -m, -m))


def test_numbers_in_sight(eq_screen, check):
    page = eq_screen.page
    page.start_by_hand([{"type": "PK", "freq": 1000, "gain": 2, "q": 1.0},
                        {"type": "PK", "freq": 9850, "gain": 8, "q": 5.0}], "pasted", "Numbers")
    eq_screen.qapp.processEvents()
    graph = page.eqplot.getPlotItem().vb.sceneBoundingRect()

    def placed():
        return [(graph.contains(_number(h)), _number(h).center().y() > h.sceneBoundingRect().center().y())
                for h in page._handles]
    drawn = placed()
    low = page._handles[0]
    low.setPos(low.pos().x(), 8.0)  # (dragged up as high as the other)
    eq_screen.qapp.processEvents()
    up = placed()
    low.setPos(low.pos().x(), 2.0)
    eq_screen.qapp.processEvents()
    down = placed()
    check("every handle's number in sight on the EQ graph (130 px high): over its handle, or under it when the "
          "graph's top would cut it off (a filter at the top of the scale), as it's dragged up and back down too",
          drawn == [(True, False), (True, True)] and up == [(True, True), (True, True)] and down == drawn,
          (drawn, up, down))


def test_dragging_a_handle(eq_screen, check):
    import pyqtgraph as pg
    from PySide6.QtCore import QEvent, QPoint, Qt
    page, qapp = eq_screen.page, eq_screen.qapp
    _fresh(page)
    qapp.processEvents()
    before = list(page._handles)
    y_range = page.eqplot.getPlotItem().vb.viewRange()[1]
    p0, p1 = _px(page, 3.0, 4.0), _px(page, 3.2, 2.0)
    _mouse(page, QEvent.MouseButtonPress, p0, Qt.LeftButton, Qt.LeftButton)
    # (spaced as a mouse's are: pyqtgraph passes on at most mouseRateLimit moves a second, 100, and drops the rest; sent
    # back to back, all but the first were dropped when the process was quick, e.g. after the accessibility tests)
    gap = 1000 / max(1, pg.getConfigOption("mouseRateLimit")) + 2
    for k in range(1, 13):
        _mouse(page, QEvent.MouseMove, QPoint(p0 + (p1 - p0) * (k / 12)), Qt.LeftButton)
        eqpage.qt.pump(gap)
        if k == 6:  # (as when curves loading in the background arrive mid-drag: their draw waits for the let-go)
            page.draw()
    # (the table follows at most every 30 ms: its value caught up with the last move)
    eqpage.qt.wait_for(lambda: page.editor.table.cellWidget(0, 3).text() == str(page.EDIT[0]["freq"]), 2)
    held = (page._handles == before, page.eqplot.getPlotItem().vb.viewRange()[1] == y_range, dict(page.EDIT[0]),
            page.editor.table.cellWidget(0, 3).text(), page.editor.table.cellWidget(0, 4).text(),
            page.chips["boost"].text())
    _mouse(page, QEvent.MouseButtonRelease, p1, Qt.NoButton, Qt.LeftButton)
    qapp.processEvents()
    f = page.EDIT[0]
    want = 10 ** 3.2
    check("handles: dragged with the mouse, a filter's frequency and gain follow it (the table and numbers too) while "
          "the same handle stays in hand and the scale stays put (a draw asked for meanwhile, e.g. curves loaded in "
          "the background, waits); let go, the graph is drawn again with it there",
          held[0] and held[1] and abs(f["freq"] - want) / want < 0.03 and abs(f["gain"] - 2.0) < 0.3
          and held[3] == str(held[2]["freq"]) and float(held[4]) == held[2]["gain"]
          and page._handles != before and abs(page._handles[0].pos().x() - math.log10(f["freq"])) < 1e-6,
          (held, f))


def test_a_drag_never_let_go(eq_screen, check):
    page, qapp = eq_screen.page, eq_screen.qapp
    _fresh(page)
    qapp.processEvents()
    before = list(page._handles)
    before[0].moving = True  # (a drag whose let-go never came: the button let go where the window didn't see it)
    page.draw()
    waited = page._handles == before
    eqpage.qt.wait_for(lambda: page._handles != before, 3)
    check("handles: a drag whose let-go never comes doesn't stop the graph being drawn: once no mouse button is down "
          "(half a second on), it's drawn", waited and page._handles != before and not page.holding_handle(),
          (waited, page._handles == before, page.holding_handle()))


def test_mouse_wheel_changes_q(eq_screen, check):
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication
    page, qapp = eq_screen.page, eq_screen.qapp
    _fresh(page)
    qapp.processEvents()
    vp = page.eqplot.viewport()
    pt = _px(page, 3.0, 4.0)
    for _ in range(2):  # (two notches up: narrower)
        ev = QWheelEvent(QPointF(pt), QPointF(vp.mapToGlobal(pt)), QPoint(0, 0), QPoint(0, 120), Qt.NoButton,
                         Qt.NoModifier, Qt.NoScrollPhase, False)
        QApplication.sendEvent(vp, ev)
        qapp.processEvents()
    check("handles: the mouse wheel over a handle changes its filter's Q (10 % a notch, up: narrower), the table "
          "following", abs(page.EDIT[0]["q"] - 1.21) < 0.011 and page.editor.table.cellWidget(0, 5).text() == "1.21",
          (page.EDIT[0], page.editor.table.cellWidget(0, 5).text()))


def test_right_click_menu(eq_screen, check):
    from PySide6.QtCore import QPointF
    page = eq_screen.page
    _fresh(page)
    page.handle_menu(0, QPointF(10, 10))
    acts = {a.text(): a for a in page.handle_menu_now.actions() if a.text()}
    ticked = [t for t, a in acts.items() if a.isChecked()]
    acts["Low shelf"].trigger()
    shelf = page.EDIT[0]["type"]
    page.handle_menu(0, QPointF(10, 10))
    next(a for a in page.handle_menu_now.actions() if a.text() == "Switched on").trigger()
    off = page.EDIT[0]["enabled"]
    page.handle_menu(1, QPointF(10, 10))
    next(a for a in page.handle_menu_now.actions() if a.text() == "Delete").trigger()
    check("handles: right-click shows the filter's type (ticked) and Switched on; choosing changes it, and Delete "
          "takes the filter away (the table and the handles follow)",
          sorted(ticked) == ["Peak", "Switched on"] and shelf == "LSQ" and off is False and len(page.EDIT) == 2
          and len(page._handles) == 2 and page.editor.table.rowCount() == 2, (ticked, shelf, off, page.EDIT))


def test_double_click_adds_a_filter(eq_screen, check):
    from PySide6.QtCore import QEvent, Qt
    page, qapp = eq_screen.page, eq_screen.qapp
    _fresh(page)
    qapp.processEvents()
    pt = _px(page, math.log10(300), -2.0)
    _mouse(page, QEvent.MouseButtonPress, pt, Qt.LeftButton, Qt.LeftButton)
    _mouse(page, QEvent.MouseButtonRelease, pt, Qt.NoButton, Qt.LeftButton)
    _mouse(page, QEvent.MouseButtonDblClick, pt, Qt.LeftButton, Qt.LeftButton)
    _mouse(page, QEvent.MouseButtonRelease, pt, Qt.NoButton, Qt.LeftButton)
    qapp.processEvents()
    new = page.EDIT[-1] if len(page.EDIT) == 4 else None
    on_handle = _px(page, 3.0, 4.0)
    _mouse(page, QEvent.MouseButtonPress, on_handle, Qt.LeftButton, Qt.LeftButton)
    _mouse(page, QEvent.MouseButtonRelease, on_handle, Qt.NoButton, Qt.LeftButton)
    _mouse(page, QEvent.MouseButtonDblClick, on_handle, Qt.LeftButton, Qt.LeftButton)
    _mouse(page, QEvent.MouseButtonRelease, on_handle, Qt.NoButton, Qt.LeftButton)
    qapp.processEvents()
    check("handles: a double-click on the EQ graph where there's no handle adds a peak there (Q 1); on a handle it adds "
          "none", new is not None and abs(new["freq"] - 300) / 300 < 0.03 and abs(new["gain"] + 2) < 0.3
          and new["q"] == 1.0 and len(page.EDIT) == 4, (new, len(page.EDIT)))


def test_double_click_with_no_eq_begins_one(eq_screen, check):
    page = eq_screen.page
    keep = (page.run_result, page.sel)
    try:
        page.run_result, page.sel = None, None
        page.add_filter_at(2500, 3.0)
        run, r = page.current()
        got = (run and run["mode"], run and run["source"], [(f["freq"], f["gain"]) for f in page.EDIT])
    finally:
        if page.run_result is None:
            page.run_result, page.sel = keep
    check("handles: with no EQ shown, a double-click on the EQ graph begins an EQ by hand with that filter",
          got == ("manual", "started on the EQ graph", [(2500, 3.0)]), got)


def test_a_tried_eq_follows_the_edits(eq_screen, check):
    page, sw = eq_screen.page, eq_screen.sw
    _fresh(page)
    page.try_on(eqpage.DEVICE)
    path = sw.trial_path()
    try:
        page.EDIT[0]["gain"] = 7.5
        page.live_update()
        followed = eqpage.qt.wait_for(lambda: "Gain 7.5 dB" in open(path, encoding="utf-8").read(), 3)
        page.no_trial = True  # (as the Guide's drag demo: never heard on the device)
        page.EDIT[0]["gain"] = 2.5
        page.live_update()
        eqpage.qt.pump(400)
        demo_kept_out = "Gain 2.5 dB" not in open(path, encoding="utf-8").read()
    finally:
        page.no_trial = False
        sw.end_trial()
    check("handles: an EQ tried on a device (Try for 5 minutes on) follows the edits there (its file written again), "
          "but not while the Guide's demo drags a handle", followed and demo_kept_out and not os.path.exists(path),
          (followed, demo_kept_out))
