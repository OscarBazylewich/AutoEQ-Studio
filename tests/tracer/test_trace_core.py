"""The tracer's workings (ui\\trace_core.py) on the app's sample graph, drawn here with Windows' fonts
(ui\\trace_window.sample_image: an IEM's left and right channel and a dashed grey target): the gridlines and their
frequencies found, Auto trace's three curves against the curves the picture was drawn from (and the target in a JPEG
of it), Erase, Undo, Smooth and Redo, a value you set kept by the automatic settings, one file per curve; and two of
the review's fixes, which need no picture of the sample: an axis with ten gridlines before its first decade line, and
Hz far from two blue lines close together. Moved from eq_checks.py's trace_checks, review_checks and
review_low_checks.

From the third test on, the tests are a chain on one picture in the tracer of this file's Make an EQ, as the old
checks were (trace_checks, lines 2771-2869): what they share is kept in the module's `sample` fixture, and they run
in the order written. The label reading between the first two is checked in test_ocr.py; saving without a dB value
and Add as measurement, the old chain's other two checks, in test_trace_window.py."""
import types

import numpy as np
import pytest

from ui import ocr, trace_core
from ui.trace_core import Tracer
from ui.trace_window import rgb_of, sample_image

COVERS = ("ui.eq_page",)  # (the tracer's window opened from Make an EQ: page.open_trace)


def test_ten_gridlines_before_first_decade(check):
    try:
        vals = trace_core.freq_values([0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 400, 410, 420])
        crash = ""
    except Exception as e:  # noqa: BLE001 - (the crash it had, said)
        vals, crash = None, repr(e)
    # was eq_checks.py:1669
    check("review: the tracer reads an axis with ten gridlines before its first decade line (it crashed)",
          not crash and vals is not None, crash)


def test_hz_far_from_two_close_blue_lines(check):
    # (the old check used the picture the check before it had pasted on Make an EQ, a plain white 400 x 300 one,
    # which the tracer opened as "Traced graph": eq_checks.py lines 1893-1897. The same picture goes straight into a
    # tracer here; the old check said nothing at all when there was no picture, so here it must be there)
    t = Tracer()
    t.load(np.full((300, 400, 3), 255, np.uint8), "Traced graph")
    assert t.has_image, "the white picture didn't load"
    t.v.update(f1="1000", f2="1001", d1="90", d2="40")
    t.cal.update(x1=200.0, x2=203.0)
    k = t.calib()
    try:
        far = k.f(0) if k else None
        ok = True
    except OverflowError:
        ok = False
    # was eq_checks.py:1911
    check("review: the tracer's Hz far from two close blue lines is huge, not an error", ok, far)


@pytest.fixture(scope="module")
def sample(eq_screen):
    """This file's Make an EQ, and what the chain below has done with the sample graph in its tracer so far."""
    return types.SimpleNamespace(page=eq_screen.page, wait_for=eq_screen.wait_for, tw=None, t=None, img=None,
                                 truth=None, errs=None, n=None)


def test_gridlines_found(sample, check):
    img, truth = sample_image()
    sample.page.open_trace()
    tw = sample.page.tracer
    t = tw.t
    sample.tw, sample.t, sample.img, sample.truth = tw, t, img, truth
    tw.load_image(img, "Sample IEM")
    # was eq_checks.py:2776
    check("trace: the gridlines and their frequencies found (20 Hz to 20 kHz, 28 lines), the frame, the clean colours",
          [g["v"] for g in t.grid_x][:3] == [20, 30, 40] and len(t.grid_x) == 28 and t.v["f2"] == "20000"
          and t.bg == (255, 255, 255) and t.v["tol"] == 45, (t.v, t.box))


def test_auto_trace_finds_three_curves(sample, check):
    tw, t, s = sample.tw, sample.t, sample.truth
    # (the axis labels' reading waited for, and the dB values typed when Windows has no text reader, as the old run
    # did between the two: eq_checks.py lines 2779-2789; the reading is checked in test_ocr.py)
    sample.wait_for(lambda: not tw.reading, 60)
    try:
        ocr._get_engine()
    except ocr.Unavailable:
        t.v.update(d1="90", d2="40")
    msgs = [t.auto_trace() for _ in range(3)]
    errs = []
    for c, truth in zip(t.curves, (s["chans"][0], s["chans"][1], s["tgt"])):
        pts, _gaps = t.points(c["ys"])
        errs.append(round(max(abs(v - truth(f)) for f, v in pts), 2))
    sample.errs = errs
    # was eq_checks.py:2795
    check("trace: Auto trace finds the left and right channels and then the dashed target, each within 0.7 dB",
          [c["label"] for c in t.curves] == ["L", "R", "L2"] and max(errs) < 0.7 and "dashed" in msgs[0], (errs, msgs))


def test_blended_pixel_not_taken_for_target(sample, check):
    errs = sample.errs
    # was eq_checks.py:2797
    check("trace: a pixel where two other lines blend into the target's grey isn't taken for it (within 0.2 dB)",
          errs[2] < 0.2, errs)


def test_grey_target_in_a_jpeg(sample, check):
    from PySide6.QtCore import QBuffer, QIODevice
    from PySide6.QtGui import QImage
    t, s, img = sample.t, sample.truth, sample.img
    # (the sample as a JPEG of quality 50, in memory; its scales set as read on the clean picture: the same columns
    # and rows)
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "JPG", 50)
    jp = QImage()
    jp.loadFromData(bytes(buf.data()), "JPG")
    tj = Tracer()
    tj.load(rgb_of(jp), "Sample IEM (JPEG)", True)
    tj.cal, tj.v["d1"], tj.v["d2"], tj.v["f1"], tj.v["f2"] = dict(t.cal), t.v["d1"], t.v["d2"], t.v["f1"], t.v["f2"]
    for _ in range(3):
        tj.auto_trace()
    grey = [c for c in tj.curves if c["colour"] and max(c["colour"]) - min(c["colour"]) < 45]
    jerr = round(max(abs(v - s["tgt"](f)) for f, v in tj.points(grey[0]["ys"])[0]), 2) if grey else None
    # was eq_checks.py:2816
    check("trace: the dashed grey target in a JPEG found by Auto trace and traced within 0.3 dB (it went along the "
          "coloured curves where they neared it)", jerr is not None and jerr < 0.3, (jerr, [c["colour"] for c in tj.curves]))


def test_erase_beside_the_picture(sample, check):
    tw, t = sample.tw, sample.t
    tw.changed()
    n = sample.n = int(np.isfinite(t.ys).sum())
    beside = t.erase(-50, 0, -10, t.H)  # (review 2: a box left of the picture erased nearly the whole curve)
    # was eq_checks.py:2821
    check("trace: Erase with a box beside the picture erases nothing", beside == 0
          and int(np.isfinite(t.ys).sum()) == n, (beside, n))


def test_erase_undo_smooth_redo(sample, check):
    t, n = sample.t, sample.n
    t.erase(0, 0, t.W, t.H)
    erased = int(np.isfinite(t.ys).sum())
    t.undo()
    t.smooth()
    t.undo()
    t.redo()
    # was eq_checks.py:2829
    check("trace: Erase, Undo, Smooth and Redo", erased == 0 and int(np.isfinite(t.ys).sum()) == n and t.undo_stack,
          (n, erased))


def test_value_you_set_is_yours(sample, check):
    tw, t = sample.tw, sample.t
    # (first what the old run did here, saving without a dB value, checked in test_trace_window.py: eq_checks.py
    # lines 2830-2833, an Undo, the first curve chosen, its dB value cleared)
    t.undo()
    t.cur = 0
    t.v["d1"] = ""
    tw.update_ui()
    t.v["d1"] = "90"
    t.v["tol"] = 70
    t.touched("tol")
    t.load(t.px, "Again")  # (another picture: its own automatic values again)
    tw.fit_and_show()
    t.v["tol"] = 70
    t.touched("tol")
    t.fit_settings()
    kept_tol = t.v["tol"]
    t.hand_back("tol")
    # was eq_checks.py:2851
    check("trace: a value you set is yours (kept by the automatic settings) until handed back",
          kept_tol == 70 and t.v["tol"] == 45 and not t.own("tol"), (kept_tol, t.v["tol"]))


def test_each_curve_its_own_file(sample, check):
    tw, t, img = sample.tw, sample.t, sample.img
    tw.load_image(img, "Sample IEM")
    sample.wait_for(lambda: not tw.reading, 60)
    t.v.update(d1="90", d2="40")
    t.auto_trace()
    t.auto_trace()
    t.curves[0]["label"] = "R"
    try:
        t.outputs()
        same = ""
    except ValueError as e:
        same = str(e)
    t.curves[0]["label"] = "L"
    outs = t.outputs()
    # was eq_checks.py:2866
    check("trace: each curve its own file (“Sample IEM L.txt”, “… R.txt”, 48 points per octave); two named alike refused",
          [o["file"] for o in outs] == ["Sample IEM L.txt", "Sample IEM R.txt"] and "named “R”" in same
          and outs[0]["text"].startswith("* Traced from Sample IEM") and 470 < len(outs[0]["text"].splitlines()) < 480,
          ([o["file"] for o in outs], same, len(outs[0]["text"].splitlines())))
