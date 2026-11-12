"""The load of a picture into the tracer (ui\\trace_window.py's load_image, prepared and picture_loaded): a picture of
more than SYNC_PIXELS loads in a thread, so the window does not stop (a 3840 x 2160 picture stopped it for 286 ms,
2026-11-11). While it loads, the tracer says so and takes no input; a new picture or Remove image meanwhile wins, the
close of the window is safe, and a picture whose load fails is said. The result is the same as a load on the
window's thread (Tracer.load). Also: Tracer.unload and Remove image set the typed values and the moved lines back.

No test here waits for a fixed time: each one waits for the window's `loading` flag, or for the answers that it
counts."""
import threading

import numpy as np
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QImage, QKeyEvent

from helpers import qt
from ui import trace_core, trace_window
from ui.trace_window import SYNC_PIXELS, sample_image

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_core", "ui.ocr", "ui.eq_page", "eq.service", "eq.inputs")


def _large():
    """The sample graph at 1600 x 960: more than SYNC_PIXELS, so its load is in a thread."""
    img, _s = sample_image()
    big = img.scaled(1600, 960, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    assert big.width() * big.height() > SYNC_PIXELS
    return big


def _tracer(eq_screen):
    page = eq_screen.page
    page.open_trace()
    return page.tracer


def _answers(tw, monkeypatch):
    """A list that has one item for each answer of a load that comes to the window (also a dropped one)."""
    seen = []
    real = tw.picture_loaded

    def counted(token, res, err, name, entry):
        seen.append(token)
        real(token, res, err, name, entry)
    monkeypatch.setattr(tw, "picture_loaded", counted)
    return seen


def _settled(tw):
    """The load and the label read of the tracer ended."""
    return qt.wait_for(lambda: not tw.loading and not getattr(tw, "reading", False), 60)


def _state(t):
    return (t.W, t.H, repr(t.h_lines), repr(t.v_lines), repr(t.grid_x), repr(t.box), repr(t.cal), t.bg,
            t.axis_note, t.src_name, repr(sorted((k, v) for k, v in t.v.items() if k not in ("d1", "d2"))),
            t.ta["noise"], repr(t.ta["notes"]), len(t.curves), int(t.dbg.sum()))


def test_large_picture_loads_in_a_thread(eq_screen, monkeypatch, check):
    tw = _tracer(eq_screen)
    tw.remove_image()
    main = threading.get_ident()
    where = {}
    for name in ("rgb_of", "picture_mark", "stage_image"):
        real = getattr(trace_window, name)

        def spy(*a, _real=real, _name=name, **k):
            where.setdefault(_name, set()).add(threading.get_ident())
            return _real(*a, **k)
        monkeypatch.setattr(trace_window, name, spy)
    real_load = trace_core.Tracer.load

    def load_spy(self, *a, **k):
        where.setdefault("Tracer.load", set()).add(threading.get_ident())
        return real_load(self, *a, **k)
    monkeypatch.setattr(trace_core.Tracer, "load", load_spy)
    monkeypatch.setattr(tw, "read_labels", lambda: None)  # (its answer would change the axes: not this test's)
    # (the user's own settings go to the thread's Tracer: "Follow all grid lines" off and the automatic settings off)
    tw.every.setChecked(False)
    tw.auto_on.setChecked(False)
    img = _large()
    tw.load_image(img, "Large graph")
    during = (tw.loading, tw.status.text(), tw.stage.isEnabled(), tw.side_scroll.isEnabled(),
              tw.guide_btn.isEnabled(), tw.t.has_image)
    tw.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_D, Qt.NoModifier))  # (a tool key: no change while it loads)
    tool = tw.tool
    came = _settled(tw)
    after = (tw.loading, tw.stage.isEnabled(), tw.side_scroll.isEnabled(), tw.guide_btn.isEnabled(),
             tw.t.has_image, tw.t.src_name, tw.file_lab.whole, tw.pages.currentIndex())
    threads = {k: set(v) for k, v in where.items()}  # (before the reference load below, on this thread)
    ref = trace_core.Tracer()
    ref.v["every"] = False
    ref.ta["enabled"] = False
    real_load(ref, trace_window.rgb_of(img), "Large graph", False)
    got, want = _state(tw.t), _state(ref)
    same = got == want
    settings = (tw.t.v["every"], tw.t.ta["enabled"])
    tw.every.setChecked(True)  # (back to the defaults: the screen is the file's)
    tw.auto_on.setChecked(True)
    tw.close()
    slow = ("rgb_of", "picture_mark", "stage_image", "Tracer.load")
    check("tracer: the slow steps of the load of a large picture (the scale, the mark, the stage's picture, "
          "Tracer.load) run in a thread, not on the window's thread",
          all(k in threads and main not in threads[k] for k in slow), {k: main in v for k, v in threads.items()})
    check("tracer: while a large picture loads, the status line says so, and the picture, the side and Guide take "
          "no input (a key changes nothing)", during == (True, trace_window.LOADING, False, False, False, False)
          and tool == "trace", (during, tool))
    check("tracer: after the load, the tracer has the picture (its name, 1 Axes) and takes input again",
          came and after == (False, True, True, True, True, "Large graph", "Large graph", 0), after)
    check("tracer: a picture loaded in a thread gives the same tracer as Tracer.load on the window's thread, with "
          "the user's settings (Follow all grid lines off, the automatic settings off)",
          same and settings == (False, False), (settings, got[10], want[10]))


def test_small_picture_loads_at_once(eq_screen, check):
    tw = _tracer(eq_screen)
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    at_once = (tw.loading, tw.t.has_image, tw.t.src_name)
    _settled(tw)
    tw.close()
    check("tracer: a picture of SYNC_PIXELS or less (the sample graph, 1200 x 720) loads at once, with no wait",
          at_once == (False, True, "Sample IEM"), at_once)


def test_new_picture_during_a_load_wins(eq_screen, monkeypatch, check):
    tw = _tracer(eq_screen)
    seen = _answers(tw, monkeypatch)
    tw.load_image(_large(), "First picture")
    img, _s = sample_image()
    tw.load_image(img, "Second picture")  # (a small one: it is there at once, before the first one's answer)
    second = (tw.loading, tw.t.src_name)
    qt.wait_for(lambda: len(seen) == 2, 60)
    _settled(tw)
    late = (len(seen), tw.t.src_name, tw.file_lab.whole, tw.t.W)
    tw.load_image(_large(), "Third picture")
    tw.load_image(_large(), "Fourth picture")
    qt.wait_for(lambda: len(seen) == 4, 60)
    _settled(tw)
    both = (tw.t.src_name, tw.t.W, tw.loading, tw.stage.isEnabled())
    tw.close()
    check("tracer: a new picture during the load of a large picture wins: the late answer of the first one is not "
          "taken", second == (False, "Second picture") and late == (2, "Second picture", "Second picture", 1200),
          (second, late))
    check("tracer: two large pictures, one after the other: the second one is in the tracer",
          both == ("Fourth picture", 1600, False, True), both)


def test_remove_image_during_a_load(eq_screen, monkeypatch, check):
    tw = _tracer(eq_screen)
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    _settled(tw)
    seen = _answers(tw, monkeypatch)
    tw.load_image(_large(), "Large graph")
    loading = tw.loading
    tw.remove_image()  # (the sample has no curve: no question)
    removed = (tw.loading, tw.t.has_image, tw.stage.isEnabled(), tw.side_scroll.isEnabled())
    qt.wait_for(lambda: len(seen) == 1, 60)
    qt.pump(50)
    after = (tw.t.has_image, tw.file_lab.whole, tw.stage.qimg)
    tw.close()
    check("tracer: Remove image while a large picture loads: the picture before goes, the load's late answer is not "
          "taken, and the tracer takes input", loading and removed == (False, False, True, True)
          and after == (False, "No picture", None), (loading, removed, after))


def test_close_during_a_load(eq_screen, monkeypatch, check):
    tw = _tracer(eq_screen)
    tw.remove_image()
    errors = len(qt.QT_ERRORS)
    seen = _answers(tw, monkeypatch)
    tw.load_image(_large(), "Large graph")
    tw.close()
    qt.wait_for(lambda: len(seen) == 1, 60)
    _settled(tw)
    after = (tw.isVisible(), tw.t.has_image, tw.t.src_name, tw.was_closed, tw.loading)
    eq_screen.page.open_trace()
    shown = (tw.isVisible(), tw.t.has_image, tw.stage.isEnabled())
    tw.close()
    check("tracer: the close of the window while a large picture loads is safe: the picture is there when the "
          "window opens again", after == (False, True, "Large graph", True, False) and shown == (True, True, True)
          and qt.QT_ERRORS[errors:] == [], (after, shown, qt.QT_ERRORS[errors:]))


def test_picture_that_cannot_be_read(eq_screen, monkeypatch, tmp_path, check):
    from helpers.dialogs import DIALOGS
    tw = _tracer(eq_screen)
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    _settled(tw)
    asked = len(DIALOGS.asked)

    def fails(self, *a, **k):
        raise ValueError("no axes")
    with monkeypatch.context() as m:
        m.setattr(trace_core.Tracer, "load", fails)
        tw.load_image(_large(), "Large graph")
        _settled(tw)
    said = DIALOGS.asked[asked:]
    failed = (tw.loading, tw.t.has_image, tw.file_lab.whole, tw.stage.isEnabled(), tw.side_scroll.isEnabled(),
              tw.status.text() == trace_window.LOADING)
    path = tmp_path / "not a picture.png"
    path.write_text("These are words, not a picture.", encoding="utf-8")
    asked = len(DIALOGS.asked)
    tw.open_file(str(path))
    not_picture = DIALOGS.asked[asked:]
    tw.close()
    check("tracer: a large picture whose load fails (in its thread): the message says so, the tracer is empty and "
          "takes input, and the status line no longer says that it opens the picture", len(said) == 1
          and "cannot read the axes of this picture (no axes)" in said[0][1]
          and failed == (False, False, "No picture", True, True, False), (said, failed))
    check("tracer: a file that is not a picture: the message says so", len(not_picture) == 1
          and "cannot read this file as a picture" in not_picture[0][1], not_picture)


def test_same_picture_again_during_and_after_a_load(eq_screen, monkeypatch, check):
    """A large picture from a website, its automatic read stood in: the same picture again gives the same message
    as a small one (the rule of picture_mark), after its load in a thread."""
    from ui import trace_auto
    tw = _tracer(eq_screen)
    img = _large()
    calls = []

    def read(rgb, ocr_words=None, jpeg=False, name="Traced graph"):
        calls.append(name)
        t = trace_core.Tracer()
        t.load(np.array(rgb, np.uint8, copy=True), name, jpeg)
        return trace_auto.AutoRead(False, t, [trace_auto.Check("trace_curve", False, "No curve.")], None, None, None,
                                   None, None, 0.01)
    monkeypatch.setattr(trace_core, "auto_read", read)
    entry = {"name": "Gate", "tag": "Site 1", "site": "Site", "link": "https://example.invalid/x"}
    tw.load_image(img, entry=entry)
    qt.wait_for(lambda: not tw.loading and not tw.reading_graph and tw.read_ok is not None, 60)
    first = (tw.read_ok, tw.t.src_name, len(calls))
    token = tw.graph_token
    tw.load_image(QImage(img), entry=tw.kept_entry())
    qt.wait_for(lambda: not tw.loading, 60)
    again = (tw.status.text(), tw.graph_token == token, len(calls), tw.entry and tw.entry["name"])
    tw.remove_image()
    tw.close()
    check("tracer: the same large picture from a website again: the tracer keeps its result and says so",
          first == (False, "Gate (Site 1)", 1) and again == ("The tracer has this picture.", True, 1, "Gate"),
          (first, again))


# ---------------------------------------------------------------- A10: typed and moved go with the picture
def test_unload_sets_typed_and_moved_back(check):
    t = trace_core.Tracer()
    t.typed = {"d": True, "f": True}
    t.moved = {"d": True, "f": True}
    t.unload()
    check("tracer: Tracer.unload sets the typed values and the moved lines back",
          t.typed == {"d": False, "f": False} and t.moved == {"d": False, "f": False}, (t.typed, t.moved))


def test_remove_image_sets_typed_and_moved_back(eq_screen, check):
    tw = _tracer(eq_screen)
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    _settled(tw)
    tw.t.move_line("y1", tw.t.cal["y1"] + 3)
    tw.t.move_line("x1", tw.t.cal["x1"] + 3)
    tw.t.typed["d"] = True
    was = (dict(tw.t.typed), dict(tw.t.moved))
    tw.remove_image()
    after = (dict(tw.t.typed), dict(tw.t.moved))
    tw.close()
    check("tracer: Remove image sets the typed values and the moved lines back",
          was == ({"d": True, "f": False}, {"d": True, "f": True})
          and after == ({"d": False, "f": False}, {"d": False, "f": False}), (was, after))


# ---------------------------------------------------------------- V1: no one call keeps Python's lock for long
def test_scale_and_copy_in_strips(qapp, monkeypatch, check):
    """The rules that keep the window's thread free while a load runs in a thread (they do not depend on the speed
    of the PC): rgb_of draws the scaled picture in strips of STRIP_ROWS rows at most (each strip made white in its
    own draw, no fill of all the picture), with the same pixels as one draw; stage_image copies the pixels with NumPy
    (no QImage.copy); squared_colour_distance looks up DISTANCE_ROWS rows at most at a time. (One draw kept the lock
    for 40 ms at 6000 x 4000, 2026-11-12.)"""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QPainter
    img, _s = sample_image()
    big = img.scaled(1600, 1200, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    monkeypatch.setattr(trace_core, "MAX_PIXELS", 1.5e6)  # (a scale down: 1600 x 1200 to 1414 x 1061)
    W, H = 1414, 1061
    ref = QImage(W, H, QImage.Format_RGB888)  # (one draw of all the picture: the pixels to compare)
    ref.fill(QColor("white"))
    p = QPainter(ref)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawImage(QRectF(0, 0, W, H), big)
    p.end()
    want = np.frombuffer(ref.constBits(), np.uint8, count=ref.bytesPerLine() * H).reshape(H, -1)[:, :W * 3]
    events = []

    class Painter(QPainter):
        def setClipRect(self, *a):
            events.append(("clip", tuple(a)))
            return super().setClipRect(*a)

        def fillRect(self, *a):
            events.append(("fill", tuple(a[:4])))
            return super().fillRect(*a)

        def drawImage(self, *a):
            events.append(("draw",))
            return super().drawImage(*a)

    class Image(QImage):
        def fill(self, *a):
            events.append(("fill all",))
            return super().fill(*a)

        def copy(self, *a):
            events.append(("copy",))
            return super().copy(*a)
    monkeypatch.setattr(trace_window, "QPainter", Painter)
    monkeypatch.setattr(trace_window, "QImage", Image)
    got = trace_window.rgb_of(big)
    scale = list(events)
    events.clear()
    stage = trace_window.stage_image(got)
    copies = list(events)
    monkeypatch.setattr(trace_window, "QPainter", QPainter)
    monkeypatch.setattr(trace_window, "QImage", QImage)
    clips = [e[1] for e in scale if e[0] == "clip"]
    rows = sorted((c[1], c[3]) for c in clips)
    covered = bool(rows) and rows[0][0] == 0 and sum(r for _y, r in rows) == H and all(
        a[0] + a[1] == b[0] for a, b in zip(rows, rows[1:]))
    each = len(scale) == 3 * len(clips) and all(
        e[0] == "clip" and f[0] == "fill" and f[1] == e[1] and d == ("draw",)
        for e, f, d in zip(scale[0::3], scale[1::3], scale[2::3]))
    st = np.frombuffer(stage.constBits(), np.uint8, count=stage.bytesPerLine() * H).reshape(H, -1)[:, :W * 3]
    # (the strips are small: 256 rows at most, so one draw or one look-up keeps the lock for a short time only;
    # a STRIP_ROWS as large as the picture made one strip and passed the checks below, the verifier, 2026-11-12)
    check("tracer: the strips have 256 rows at most (STRIP_ROWS, DISTANCE_ROWS), and this picture has 4 strips or more",
          trace_window.STRIP_ROWS <= 256 and trace_core.DISTANCE_ROWS <= 256 and len(clips) >= 4,
          (trace_window.STRIP_ROWS, trace_core.DISTANCE_ROWS, len(clips)))
    check("tracer: rgb_of draws the scale in strips of STRIP_ROWS rows at most, each strip made white in its own "
          "draw (no fill of all the picture), all rows once",
          len(clips) == -(-H // trace_window.STRIP_ROWS) and all(r <= trace_window.STRIP_ROWS for _y, r in rows)
          and covered and each and ("fill all",) not in scale, (rows, scale[:6]))
    check("tracer: the strips give the same pixels as one draw of all the picture",
          got.shape == (H, W, 3) and np.array_equal(got.reshape(H, -1), want), got.shape)
    check("tracer: stage_image copies the pixels with NumPy (no QImage.copy), the same pixels",
          copies == [] and np.array_equal(st, got.reshape(H, -1)), copies)

    class Rows(np.ndarray):  # (records the rows of each channel that the look-up uses)
        looked = []

        def __getitem__(self, k):
            r = super().__getitem__(k)
            if isinstance(r, np.ndarray) and r.ndim == 2:
                Rows.looked.append(r.shape[0])
            return r
    t = trace_core.Tracer()
    px = got[:1000]
    t.px = px.view(Rows)
    colour = (250, 240, 230)
    d = np.asarray(t.squared_colour_distance(slice(None), slice(None), colour))
    plain = ((px.astype(np.int64) - np.array(colour)) ** 2).sum(-1)
    check("tracer: squared_colour_distance of a large area looks up DISTANCE_ROWS rows at most at a time, with the "
          "same values", bool(Rows.looked) and max(Rows.looked) <= trace_core.DISTANCE_ROWS
          and np.array_equal(d, plain) and d.dtype == np.int32, (max(Rows.looked or [0]), d.dtype))


# ---------------------------------------------------------------- V4: an automatic read that ends during a load
def _held_read(monkeypatch, gate, ended):
    """A stand-in for the automatic read: it waits for `gate`, then gives an OK read of the picture (the sample's
    first channel as its curve). `ended` is set when it ends."""
    from ui import trace_auto

    def read(rgb, ocr_words=None, jpeg=False, name="Traced graph"):
        gate.wait(60)
        t = trace_core.Tracer()
        t.load(np.array(rgb, np.uint8, copy=True), name, jpeg)
        t.v.update(d1="90", d2="40")
        t.auto_trace()
        ended.set()
        return trace_auto.AutoRead(True, t, [trace_auto.Check("trace_curve", True, "")], None, None, None, None,
                                   None, 0.01)
    monkeypatch.setattr(trace_core, "auto_read", read)


def _held_load(monkeypatch, gate, fails=False):
    """prepared of a large picture waits for `gate` (its load is in work until then); with fails, it raises."""
    real = trace_window.prepared

    def held(*a):
        if a[0].width() * a[0].height() <= SYNC_PIXELS:  # (a small picture: at once, as before)
            return real(*a)
        gate.wait(60)
        if fails:
            raise MemoryError("stand-in")
        return real(*a)
    monkeypatch.setattr(trace_window, "prepared", held)


def test_read_that_ends_during_a_load(eq_screen, monkeypatch, check):
    """The automatic read of a picture from a website ends while a large picture loads: its result does not go into
    the tracer during the load (no 3 Save, the status line still says that the app opens the picture), and it goes
    when the new picture comes (graph_token). When the load fails, the picture before stays, and its read goes in
    then. (2026-11-12: the read put its result into the tracer during the load, with 3 Save and its own words.)"""
    from helpers.dialogs import DIALOGS
    tw = _tracer(eq_screen)
    tw.remove_image()
    entry = {"name": "Gate", "tag": "Site 1", "site": "Site", "link": "https://example.invalid/x"}
    img, _s = sample_image()
    seen = {}
    for fails in (False, True):
        read_gate, read_ended, load_gate = threading.Event(), threading.Event(), threading.Event()
        asked = len(DIALOGS.asked)
        with monkeypatch.context() as m:
            _held_read(m, read_gate, read_ended)
            _held_load(m, load_gate, fails)
            tw.load_image(img.copy(0, 0, 1199 - fails, 719), entry=entry)  # (small: at once; its read waits)
            tw.load_image(_large(), "Large graph")  # (its load waits for load_gate)
            read_gate.set()
            qt.wait_for(read_ended.is_set, 60)
            qt.wait_for(lambda: tw.late_read is not None or tw.read_ok is not None, 60)
            during = (tw.loading, tw.status.text() == trace_window.LOADING, tw.read_ok, tw.pages.currentIndex(),
                      "traced the graph" in tw.save_note.text(), tw.stage.isEnabled())
            load_gate.set()
            qt.wait_for(lambda: not tw.loading, 60)
            qt.wait_for(lambda: not tw.reading_graph and not getattr(tw, "reading", False), 60)
            after = (tw.t.src_name, tw.entry and tw.entry["name"], tw.read_ok, tw.reading_graph, tw.stage.isEnabled(),
                     tw.late_read is None)
        seen[fails] = (during, after, [a[1] for a in DIALOGS.asked[asked:]])
        tw.remove_image()
    tw.close()
    check("tracer: an automatic read that ends while a large picture loads: nothing of it goes into the tracer during "
          "the load", all(seen[f][0] == (True, True, None, 0, False, False) for f in (False, True)),
          {f: seen[f][0] for f in (False, True)})
    check("tracer: after the load, the new picture is in the tracer and the read of the picture before is dropped",
          seen[False][1] == ("Large graph", None, None, False, True, True), seen[False][1])
    check("tracer: when the load fails, the picture before stays and its read goes in after the load",
          seen[True][1] == ("Gate (Site 1)", "Gate", True, False, True, True)
          and any("cannot open this picture" in s for s in seen[True][2]), seen[True][1:])


def test_remove_image_no_during_a_load_takes_the_read(eq_screen, monkeypatch, dialogs, check):
    """Remove image during a load, over a picture from a website with curves, and the answer No: the load is dropped,
    the picture stays, and its automatic read that ended during the load goes in. (2026-11-12: in the code, no test
    held it.)"""
    from PySide6.QtWidgets import QMessageBox
    tw = _tracer(eq_screen)
    tw.remove_image()
    entry = {"name": "Gate", "tag": "Site 1", "site": "Site", "link": "https://example.invalid/x"}
    img, _s = sample_image()
    read_gate, read_ended, load_gate = threading.Event(), threading.Event(), threading.Event()
    with monkeypatch.context() as m:
        _held_read(m, read_gate, read_ended)
        _held_load(m, load_gate)
        tw.load_image(img.copy(0, 0, 1199, 719), entry=entry)  # (small: at once; its read waits)
        tw.t.curves[0]["ys"][100:120] = 60.0  # (a curve of the user: Remove image asks first)
        tw.load_image(_large(), "Large graph")  # (its load waits for load_gate)
        read_gate.set()
        qt.wait_for(read_ended.is_set, 60)
        qt.wait_for(lambda: tw.late_read is not None, 60)
        during = (tw.loading, tw.read_ok, tw.late_read is not None)
        dialogs.answer("question", QMessageBox.No)
        asked = len(dialogs.asked)
        tw.remove_image()
        question = [a[1] for a in dialogs.asked[asked:]]
        load_gate.set()
        qt.wait_for(lambda: not tw.reading_graph and not getattr(tw, "reading", False), 60)
        qt.pump(100)
        after = (tw.loading, tw.t.has_image, tw.t.src_name, tw.entry and tw.entry["name"], tw.read_ok,
                 tw.late_read is None, tw.pages.currentIndex())
    tw.remove_image()
    tw.close()
    check("tracer: Remove image with No during a load: the load is dropped, the picture from the website stays, and "
          "its read that ended during the load goes in (3 Save)",
          during == (True, None, True) and question == ["Remove this picture and its traced curves?"]
          and after == (False, True, "Gate (Site 1)", "Gate", True, True, 2), (during, question, after))
