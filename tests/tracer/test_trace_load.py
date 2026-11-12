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
    real_load(ref, trace_window.rgb_of(img), "Large graph", False)
    same = _state(tw.t) == _state(ref)
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
    check("tracer: a picture loaded in a thread gives the same tracer as Tracer.load on the window's thread", same)


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
