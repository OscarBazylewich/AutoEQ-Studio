"""3 Save of the tracer (ui\\trace_window.py's _save_box): the "Save from (Hz)" boxes show their whole values at the
usual and the smallest size of the window (the "to" box cut the first pixels of "20000" at 964 x 393, 2026-11-11), and
the accent button of the row is the main action of the picture (Add as target for an entry from Find a target)."""
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
    for key in ("fmin", "fmax"):  # (your values: each tag says "your value ↺")
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
          and seen[("smallest", "past with your values")] == ([], "your value ↺"), seen)


def _stand_in_read(rgb, ocr_words=None, jpeg=False, name="Traced graph"):
    """A stand-in for trace_core.auto_read: the picture as it is, the sample's dB values, a part of a curve, all
    checks OK, no target line."""
    import numpy as np
    from ui import trace_core
    from ui.trace_auto import AutoRead, Check
    t = trace_core.Tracer()
    t.load(np.array(rgb, np.uint8, copy=True), name, jpeg)
    t.v.update(d1="90", d2="40")
    t.curves[0]["ys"][100:200] = 300.0  # (a traced curve)
    return AutoRead(True, t, [Check("axes_plot", True, "The app found the graph in the picture.")], t.curves[0],
                    None, None, None, None, 0.01)


ENTRY = {"name": "Truthear Gate", "tag": "Hangout 5128", "site": "Hangout.Audio", "link": "https://example.invalid/x"}


def _row(tw):
    """3 Save's buttons in their order, each with whether it is the accent button."""
    lay = tw.save_btns
    return [(lay.itemAt(i).widget().text(), lay.itemAt(i).widget().property("primary") in (True, "true"))
            for i in range(lay.count()) if lay.itemAt(i).widget() is not None]


def test_accent_button_is_the_main_action(eq_screen, monkeypatch, tmp_path, check):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage
    from ui import trace_core
    monkeypatch.setattr(trace_core, "auto_read", _stand_in_read)
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    measurement = [("Add as measurement", True), ("Add as target", False), ("Save .txt…", False)]
    target = [("Add as target", True), ("Add as measurement", False), ("Save .txt…", False)]
    rows, pictures = {}, {}

    def read(entry):
        tw.load_image(img, entry=entry)
        qt.wait_for(lambda: not tw.loading and not tw.reading_graph and tw.read_ok is not None, 60)

    read(dict(ENTRY, **{"as": "target"}))
    rows["Find a target"] = (_row(tw), "Add as target." in tw.save_note.text())
    tw.show_tab(2)
    usual = tw.size()
    for which, size in (("usual", usual), ("smallest", tw.minimumSize().expandedTo(tw.minimumSizeHint()))):
        tw.resize(size)
        for name, theme_on in (("light", qt.light), ("dark", qt.dark)):
            theme_on(eq_screen.qapp)
            qt.pump(100)
            path = str(tmp_path / f"save-row-target-{which}-{name}.png")
            tw.pages.currentWidget().grab().save(path)
            pic = QImage(path)
            # (a pixel of each button's fill, 5 px in from its left edge)
            fill = [pic.pixelColor(b.mapTo(tw.pages.currentWidget(), QPoint(5, b.height() // 2))).saturation()
                    for b in (tw.save_tgt, tw.save_meas)]
            pictures[(which, name)] = tuple(fill)
    qt.light(eq_screen.qapp)
    tw.resize(usual)
    tw.load_image(img.copy(0, 0, 800, 500), "A picture of yours")  # (a different picture: the same one keeps all)
    qt.wait_for(lambda: not tw.loading and not tw.reading, 60)
    rows["a picture of yours after it"] = _row(tw)
    read(dict(ENTRY, **{"as": "target"}))
    tw.remove_image()
    rows["Remove image after it"] = _row(tw)
    read(dict(ENTRY))
    rows["Find a measurement"] = (_row(tw), "Add as measurement." in tw.save_note.text())
    tw.show_tab(2)
    for name, theme_on in (("light", qt.light), ("dark", qt.dark)):
        theme_on(eq_screen.qapp)
        qt.pump(100)
        tw.pages.currentWidget().grab().save(str(tmp_path / f"save-row-measurement-usual-{name}.png"))
    qt.light(eq_screen.qapp)
    tw.remove_image()
    tw.close()
    check("tracer: for an entry from Find a target, Add as target is the accent button and the first one of 3 Save's "
          "row (its note says to click it)", rows["Find a target"] == (target, True), rows)
    check("tracer: a new picture or Remove image puts Add as measurement first again, in the accent; an entry from "
          "Find a measurement has it too", rows["a picture of yours after it"] == measurement
          and rows["Remove image after it"] == measurement and rows["Find a measurement"] == (measurement, True), rows)
    check("tracer: the pictures of the row (light and dark, the usual and the smallest size): Add as target has the "
          "accent color, Add as measurement has none", len(pictures) == 4
          and all(t > 80 and m < 40 for t, m in pictures.values()), pictures)
