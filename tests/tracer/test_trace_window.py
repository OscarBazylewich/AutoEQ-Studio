"""The tracer's window (ui\\trace_window.py) on Make an EQ, with the app's sample graph: two fingers zooming and
dragging the picture (made-up touch events: no touch screen needed), a curve's name box selected without its rows
rebuilt, saving without a dB value, and Add as measurement. Moved from eq_checks.py's rest_checks, review_checks and
trace_checks.

The last two were the end of the old trace checks' chain on one picture (test_trace_core.py has the rest): each test
here traces the sample again and takes the old chain's steps up to it (tracing it takes about half a second). Add as
measurement changes the studio's Measurements: the studio is new again after it (fresh_studio)."""
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QFocusEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QGestureEvent, QLineEdit, QMessageBox, QPinchGesture

from helpers import eqpage
from ui.trace_window import sample_image

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_core", "ui.ocr", "ui.eq_page", "eq.service", "eq.inputs")


def test_two_fingers_zoom_and_drag(eq_screen, monkeypatch, check):
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    eq_screen.wait_for(lambda: not tw.reading, 60)
    st = tw.stage
    st.resize(900, 600)
    v0 = dict(st.view)
    g = QPinchGesture()  # (two fingers, made up)
    g.setScaleFactor(1.5)
    centre = st.mapToGlobal(QPoint(450, 300))
    g.setCenterPoint(QPointF(centre))
    g.setLastCenterPoint(QPointF(centre) - QPointF(10, 0))
    st.event(QGestureEvent([g]))
    v1 = dict(st.view)
    tw.set_tool("trace")
    monkeypatch.setattr(st, "line_at", lambda *_a: None)  # (a finger here, not on a calibration line)
    v_before = dict(st.view)

    def finger(kind, x, y):
        p = QPointF(x, y)
        st.event(QMouseEvent(kind, p, p, QPointF(st.mapToGlobal(p.toPoint())), Qt.LeftButton,
                             Qt.LeftButton if kind != QEvent.MouseButtonRelease else Qt.NoButton, Qt.NoModifier,
                             Qt.MouseEventSynthesizedBySystem))
    finger(QEvent.MouseButtonPress, 300, 300)
    finger(QEvent.MouseMove, 340, 320)
    finger(QEvent.MouseButtonRelease, 340, 320)
    panned = (st.view["ox"] - v_before["ox"], st.view["oy"] - v_before["oy"])
    monkeypatch.undo()  # (the stand-in gone before the window closes, as the old check did)
    tw.close()
    # was eq_checks.py:2109
    check("tracer: two fingers zoom about their centre and drag the picture; a finger that moves drags it (a tap "
          "would trace)", abs(v1["s"] / v0["s"] - 1.5) < 0.01 and v1["ox"] != v0["ox"]
          and panned == (40, 20), (v0, v1, panned))


def test_name_box_selected_without_rebuilding(eq_screen, check):
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    eq_screen.wait_for(lambda: not tw.reading, 60)
    tw.t.v.update(d1="90", d2="40")
    tw.auto_trace()
    tw.auto_trace()
    rows = list(tw.curve_rows)
    box = rows[0].findChild(QLineEdit)
    QApplication.sendEvent(box, QFocusEvent(QEvent.FocusIn, Qt.MouseFocusReason))
    eq_screen.qapp.processEvents()
    same = tw.curve_rows == rows and tw.t.cur == 0 and not box.isHidden()
    tw.t.v["dashed"] = not tw.dashed.isChecked()
    tw.changed()
    # was eq_checks.py:1800
    check("review: the tracer: a curve's name box is selected without rebuilding the rows; values it sets show",
          same and tw.dashed.isChecked() == tw.t.v["dashed"], (same, tw.dashed.isChecked(), tw.t.v["dashed"]))
    tw.close()


def test_saving_without_db_value(eq_screen, check):
    # (the sample traced as the old chain had it: opened, its labels read or the dB values typed, Auto trace three
    # times, eq_checks.py lines 2771-2790; then its steps before this check, lines 2818-2828: erased beside the
    # picture, all erased, Undo, Smooth, Undo, Redo. test_trace_core.py checks those)
    tw, _truth, _msgs = eqpage.open_traced_sample(eq_screen)
    t = tw.t
    tw.changed()
    t.erase(-50, 0, -10, t.H)
    t.erase(0, 0, t.W, t.H)
    t.undo()
    t.smooth()
    t.undo()
    t.redo()
    t.undo()
    t.cur = 0
    t.v["d1"] = ""
    tw.update_ui()
    try:
        t.outputs()
        missing = ""
    except ValueError as e:
        missing = str(e)
    # was eq_checks.py:2839
    check("trace: saving without a dB value says to type it", "Type the values" in missing
          and "Type the dB values" in tw.save_note.text(), (missing, tw.save_note.text()))
    tw.close()


def test_add_as_measurement(eq_screen, fresh_studio, monkeypatch, check):
    page = eq_screen.page
    # (the two curves the old chain's check before this one had: the sample loaded again, its labels' reading waited
    # for, the dB values typed, Auto trace twice: L and R. eq_checks.py lines 2853-2857; test_trace_core.py checks
    # their files)
    img, _s = sample_image()
    page.open_trace()
    tw = page.tracer
    t = tw.t
    tw.load_image(img, "Sample IEM")
    eq_screen.wait_for(lambda: not tw.reading, 60)
    t.v.update(d1="90", d2="40")
    t.auto_trace()
    t.auto_trace()
    with monkeypatch.context() as mp:
        mp.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))  # (as eq_checks.py lines 2870-2875)
        tw.save("measurement")
    loaded = eq_screen.wait_for(lambda: page.curves is not None and page.curves.get("name") == "Sample IEM", 60)
    # was eq_checks.py:2877
    check("trace: Add as measurement puts the curves in the app as one device, in use (on the graph)",
          loaded and "2 files of one measurement" in tw.save_note.text()
          and [m["name"] for m in page.inputs["measurements"] if m["included"]] == ["Sample IEM L.txt", "Sample IEM R.txt"],
          (tw.save_note.text(), page.graph_title.text()))
    tw.close()
