"""3 Save of the tracer (ui\\trace_window.py's _save_box): the "Save from (Hz)" boxes show their whole values at the
usual and the smallest size of the window (the "to" box cut the first pixels of "20000" at 964 x 393, 2026-11-11).
The one add button of the row, in the accent, with the name of the picture's type: test_trace_graph_type.py
(test_the_app_selects_the_type) and test_trace_target_save.py (its pictures); the test of it here went there (the
test audit, 2026-11-25)."""
from PySide6.QtWidgets import QStyle, QStyleOptionFrame

from helpers import qt
from ui.trace_window import sample_image

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_core", "ui.ocr", "ui.eq_page", "eq.service", "eq.inputs")


def text_room(box):
    """(room, needed) in pixels for the text of a QLineEdit, as Qt 6's QLineEdit.paintEvent decides that the text
    fits with no scroll: the contents' rectangle less the text margins and 2 px at each side, against the text's
    width and 1 px for the cursor. (Measured on the picture of the box: 37 px of room and 41 px needed cut the
    first pixels of "20000"; 43 px of room showed all of it.)"""
    opt = QStyleOptionFrame()
    box.initStyleOption(opt)
    r = box.style().subElementRect(QStyle.SE_LineEditContents, opt, box)
    tm = box.textMargins()
    return r.width() - tm.left() - tm.right() - 4, box.fontMetrics().horizontalAdvance(box.text()) + 1


def past_the_side(tw):
    """The visible controls of the tab in sight whose right edge is past the side's viewport."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QWidget
    vp = tw.side_scroll.viewport()
    return [(type(w).__name__, w.mapTo(vp, QPoint(w.width(), 0)).x())
            for w in tw.pages.currentWidget().findChildren(QWidget)
            if w.isVisibleTo(tw) and w.mapTo(vp, QPoint(w.width(), 0)).x() > vp.width()]


def test_save_range_boxes_show_their_values(eq_screen, tmp_path, check):
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    qt.wait_for(lambda: not tw.reading, 60)
    tw.show_tab(2)
    usual = tw.size()
    seen = {}
    for which, size in (("usual", usual), ("smallest", tw.minimumSize().expandedTo(tw.minimumSizeHint()))):
        tw.resize(size)
        qt.pump(150)
        for key in ("fmin", "fmax"):
            for value in ("20", "20000", "19999"):
                box = tw.boxes[key]
                box.setText(value)
                seen[(which, key, value)] = text_room(box)
        seen[(which, "size")] = (tw.width(), tw.height(), tw.side_scroll.verticalScrollBar().isVisible())
        seen[(which, "past")] = past_the_side(tw)
    for key in ("fmin", "fmax"):  # (your values: each tag says "custom ↺")
        tw.boxes[key].setText("20000" if key == "fmax" else "30")
        tw.value_typed(key, "trace.save")
    qt.pump(150)
    seen[("smallest", "past with your values")] = (past_the_side(tw), tw.tags["fmax"].text())
    tw.boxes["fmin"].setText("20000")  # (as wide as the widest value, not typed)
    seen[("smallest", "fmin", "20000, your values")] = text_room(tw.boxes["fmin"])
    seen[("smallest", "fmax", "20000, your values")] = text_room(tw.boxes["fmax"])
    for name, theme_on in (("light", qt.light), ("dark", qt.dark)):  # (the pictures: read back by the author)
        theme_on(eq_screen.qapp)
        qt.pump(100)
        tw.pages.currentWidget().grab().save(str(tmp_path / f"save-range-your-values-smallest-{name}.png"))
    qt.light(eq_screen.qapp)
    tw.make_auto(None)
    tw.resize(usual)
    tw.show_values()
    tw.close()
    check("tracer: the boxes of Save from (Hz) show their whole values (20, 20000) at the usual and the smallest size "
          "of the window (there, the side has its scroll bar)", seen[("smallest", "size")][2]
          and all(v[1] <= v[0] for k, v in seen.items() if len(k) == 3), seen)
    check("tracer: no control of 3 Save goes past the side's right edge, at the usual and the smallest size",
          seen[("usual", "past")] == [] and seen[("smallest", "past")] == []
          and seen[("smallest", "past with your values")] == ([], "custom ↺"), seen)

