"""The tracer's window (ui\\trace_window.py) on Make an EQ, with the app's sample graph: two fingers zooming and
dragging the picture (made-up touch events: no touch screen needed), a curve's name box selected without its rows
rebuilt, saving without a dB value, and Add as measurement. Moved from eq_checks.py's rest_checks, review_checks and
trace_checks.

The last two were the end of the old trace checks' chain on one picture (test_trace_core.py has the rest): each test
here traces the sample again and takes the old chain's steps up to it (tracing it takes about half a second). Add as
measurement changes the studio's Measurements: the studio is new again after it (fresh_studio)."""
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QFocusEvent, QKeyEvent, QMouseEvent
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


def test_fits_a_small_screen(eq_screen, monkeypatch, check):
    # (2026-10-24, left from the restyle: it opened 1320 x 860, bigger than a 1920 x 1080 laptop's screen at 150 %
    # (1280 x 672 above the taskbar) and 175 %)
    from helpers import qt
    from ui.trace_window import TraceWindow
    seen = qt.on_screens(monkeypatch, lambda: TraceWindow(eq_screen.page))
    big = seen[qt.BIG_SCREEN]
    check("trace: the tracer's window opens within a laptop's screen at 150 % and 175 % (above the taskbar, its "
          "smallest size too), its parts not squeezed; on a big screen as before (1320 x 860)",
          all(seen[s]["fits"] for s in qt.SMALL_SCREENS) and big["fits"] and big["opens"] == (1320, 860), seen)


def _sample_open(eq_screen, name="Sample IEM"):
    """The tracer on the sample graph, its labels' reading waited for."""
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, name)
    eq_screen.wait_for(lambda: not tw.reading, 60)
    return tw


def _key(tw, key, mods=Qt.NoModifier):
    tw.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, mods))


def test_messages_in_sight_on_every_tab(eq_screen, monkeypatch, check):
    # (2026-11-10, the code's review: the message line was in 2 Trace's card, so a value moved to its limit on 1 Axes,
    # an empty clipboard or Remove image said nothing on the other tabs)
    tw = _sample_open(eq_screen)
    eq_screen.qapp.processEvents()
    seen = []
    tw.show_tab(0)
    box = tw.boxes["f2"]
    box.setText("99999999")
    tw.value_left("f2", "trace.hz")
    seen.append(("1 Axes, a value moved to its limit", tw.status.isVisibleTo(tw), tw.status.text()))
    tw.show_tab(2)
    QApplication.clipboard().clear()  # (the off-screen clipboard: Windows' is not touched)
    tw.paste()
    seen.append(("3 Save, an empty clipboard", tw.status.isVisibleTo(tw), tw.status.text()))
    tw.show_tab(1)
    tw.say("A message on 2 Trace.")
    seen.append(("2 Trace", tw.status.isVisibleTo(tw), tw.status.text()))
    tw.show_tab(2)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    tw.remove_image()
    seen.append(("3 Save, Remove image", tw.status.isVisibleTo(tw), tw.status.text()))
    inside = tw.rect().contains(QRect(tw.status.mapTo(tw, QPoint(0, 0)), tw.status.size()))
    tw.close()
    check("trace: the tracer's messages show on every tab (1 Axes, 2 Trace, 3 Save), inside the window",
          all(shown and text for _w, shown, text in seen) and "changed the value" in seen[0][2]
          and "clipboard" in seen[1][2] and "removed the picture" in seen[3][2] and inside, (seen, inside))


def test_keys_show_their_tab(eq_screen, check):
    # (2026-11-10, the code's review: Ctrl+Z and the arrows changed the curves or a line while another tab showed)
    tw = _sample_open(eq_screen)
    if QApplication.focusWidget() is not None:
        QApplication.focusWidget().clearFocus()  # (a key typed in a box is the box's own)
    tabs = {}
    tw.show_tab(0)
    _key(tw, Qt.Key_Z, Qt.ControlModifier)
    tabs["Ctrl+Z on 1 Axes"] = tw.pages.currentIndex()
    tw.show_tab(2)
    _key(tw, Qt.Key_Y, Qt.ControlModifier)
    tabs["Ctrl+Y on 3 Save"] = tw.pages.currentIndex()
    tw.show_tab(2)
    line = next(k for k in tw.t.cal if k[0] == "y")
    tw.stage.sel_line = line
    was = tw.t.cal[line]
    _key(tw, Qt.Key_Down)
    tabs["Down on 3 Save, a red line selected"] = tw.pages.currentIndex()
    moved = tw.t.cal[line] != was
    tw.stage.sel_line = None
    tw.show_tab(2)
    _key(tw, Qt.Key_F)
    tabs["F on 3 Save (the picture's own)"] = tw.pages.currentIndex()
    tw.close()
    check("trace: a key shows the tab of what it changes (Ctrl+Z, Ctrl+Y: 2 Trace; an arrow on a selected line: "
          "1 Axes); F, the picture's own key, keeps the tab", tabs == {"Ctrl+Z on 1 Axes": 1, "Ctrl+Y on 3 Save": 1,
                                                                   "Down on 3 Save, a red line selected": 0,
                                                                   "F on 3 Save (the picture's own)": 2} and moved,
          (tabs, moved))


def test_long_file_name_cut(eq_screen, check):
    # (2026-11-10, the code's review: a long file name widened the tracer past the screen)
    name = "A very long name of a picture of a graph from a review website " * 5
    tw = _sample_open(eq_screen, name.strip())
    eq_screen.qapp.processEvents()
    lab = tw.file_lab
    least = tw.minimumSizeHint().width()
    shown, tip, reader = lab.text(), lab.toolTip(), lab.accessibleName()
    tw.close()
    check("trace: a long picture name is cut in its middle (…), its whole name in its tooltip and for a screen "
          "reader, and it does not make the window wider", "…" in shown and len(shown) < len(name.strip())
          and tip == name.strip() and reader == name.strip() and least < 1320, (shown, tip, least))


def test_guide_puts_the_tab_back(eq_screen, check):
    # (2026-11-10, the code's review: the Guide's steps show their tabs, and the tracer stayed on 3 Save after it)
    from ui import guide
    tw = _sample_open(eq_screen)
    tw.show_tab(1)
    t = guide.start_trace(tw)
    t.all_chk.setChecked(False)
    t.go_to_step(next(n for n, st in enumerate(t.steps) if st["title"] == "Save"))
    during = tw.pages.currentIndex()
    t.end()
    yours = tw.pages.currentIndex()
    tw.show_tab(0)
    with pytest.MonkeyPatch.context() as m:  # (no picture: the Guide opens the sample graph and closes it after)
        m.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
        tw.remove_image()
    tw.show_tab(2)
    t = guide.start_trace(tw)
    t.all_chk.setChecked(False)
    t.go_to_step(next(n for n, st in enumerate(t.steps) if st["title"] == "Examine the axes"))
    during_sample = tw.pages.currentIndex()
    t.end()
    sample_yours = tw.pages.currentIndex()
    tw.close()
    check("trace: the tracer's Guide shows a step's tab, and the tab that you had comes back when it closes (with "
          "your picture, and on the sample graph)", (during, yours, during_sample, sample_yours) == (2, 1, 0, 2),
          (during, yours, during_sample, sample_yours))


def test_picture_with_no_entry(eq_screen, monkeypatch, check):
    # (2026-11-11, the picture from a website: a picture of yours does what it did before, no automatic read)
    from ui import trace_core
    calls = []
    monkeypatch.setattr(trace_core, "auto_read", lambda *a, **k: calls.append(a))
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    started = (tw.pages.currentIndex(), tw.reading, tw.reading_graph, tw.entry)
    eq_screen.wait_for(lambda: not tw.reading, 60)
    tw.close()
    check("tracer: a picture with no entry does what it did (tab 1 Axes, the labels read, no automatic read)",
          started == (0, True, False, None) and not calls and tw.t.src_name == "Sample IEM", (started, calls))


def test_outputs_name_and_target_mark(eq_screen, check):
    # (2026-11-11: outputs with a name in place of the Name box's; the target line that the automatic read marks is
    # not in the measurement's files, unless it is the one curve asked for)
    tw, _truth, _msgs = eqpage.open_traced_sample(eq_screen)
    t = tw.t
    t.v.update(d1="90", d2="40")
    named = [o["file"] for o in tw.outputs(name="Another name")]
    t.curves[1]["target"] = True
    marked = [o["file"] for o in tw.outputs()]
    t.cur = 1
    one = [o["label"] for o in tw.outputs(True)]
    tw.update_ui()
    button = not tw.save_line.isHidden()  # (on 3 Save, a tab not in sight here)
    t.curves[1].pop("target")
    tw.update_ui()
    tw.close()
    check("tracer: outputs with a name use it", named and all(n.startswith("Another name ") for n in named), named)
    check("tracer: a curve marked as target is not in the measurement's files (Add as target of that curve has it), "
          "and Add the target line as target… shows for it",
          len(marked) == len(named) - 1 and one == [t.curves[1]["label"]] and button, (marked, one, button))
