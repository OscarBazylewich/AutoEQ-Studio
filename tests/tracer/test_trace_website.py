"""The tracer's automatic read of a graph from a CrinGraph website (ui\\trace_auto.py, through trace_core.auto_read),
on drawn look-alikes of such a graph (helpers.website_graph: no picture of a real website is kept here): the grid,
the axes, the one curve (the average of the left and right channel), the target line, and the checks with their
reasons; and what trace_core gained for it: Tracer.take (the window takes the result's state), outputs() with a name
and without the target line, and the target mark going when the user changes that curve.

Most tests use the true words of the picture in place of Windows' text reader (helpers.website_graph.truth_reader
stands in for trace_auto.read_strip), so that they do not depend on the reader of this PC; the last test uses the
real reader, and skips, with the reason, where Windows has none. The cached results of the `read` fixture are not
changed by any test: a test that changes a tracer reads its own picture (`fresh`).

The review of 2026-11-10 (its findings A1 to A11 and T1 to T10) added: a failing case for each check, with its
reason; the dB axis from 3 or more labels; the channels kept where they are apart, at the grid's edges and at the
faded ends; text in the curve's color; the target line where the band hides it; the input forms; read_strip."""
import ast
import inspect
import math

import numpy as np
import pytest

from helpers import capabilities
from helpers import website_graph as wg
from helpers.qt import time_limit
from helpers.website_graph import as_rgb, truth_reader, website_graph
from ui import ocr, trace_auto, trace_core
from ui.trace_core import Tracer

COVERS = ("ui.trace_auto", "ui.trace_core")
REAL_READ_STRIP = trace_auto.read_strip  # (the real one, for the tests with Windows' text reader)
NO_WORDS = lambda rgb: []  # noqa: E731  (an ocr_words that reads nothing: the stand-in gives the words)
ORANGE = ("#e67e22", "#c96a15")
CREAM = (255, 247, 234)


def errors(pts, fn, lo=20.5, hi=19500):
    """Mean and largest difference in dB between [(Hz, dB)] and the true curve fn, and the share of 20 Hz to 20 kHz
    (in octaves) that the points cover."""
    if not pts:
        return None
    e = [abs(v - fn(f)) for f, v in pts if lo <= f <= hi]
    if not e:
        return None
    span = math.log2(min(pts[-1][0], 20000) / max(pts[0][0], 20)) / math.log2(1000)
    return float(np.mean(e)), float(np.max(e)), span


@pytest.fixture(scope="module")
def read(qapp, module_monkeypatch):
    """read(plot_w, jpeg, **website_graph's options) -> (truth, rgb, AutoRead), with the true words; each picture read
    once for the file (no test changes these results)."""
    done = {}

    def go(w=1000, jpeg=None, **kw):
        key = (w, jpeg, tuple(sorted(kw.items())))
        if key not in done:
            img, truth = website_graph(plot_w=w, **kw)
            rgb = as_rgb(img, jpeg)
            module_monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
            done[key] = truth, rgb, trace_core.auto_read(rgb, NO_WORDS, bool(jpeg), "Sample IEM")
        return done[key]
    return go


def fresh(monkeypatch, w=1000, jpeg=None, words=None, edit=None, **kw):
    """A new read of a look-alike (not the cache): words(truth) -> the words that the stand-in gives; edit(rgb, truth)
    changes the picture before the read. Returns (truth, rgb, AutoRead)."""
    img, truth = website_graph(plot_w=w, **kw)
    rgb = as_rgb(img, jpeg)
    if edit:
        edit(rgb, truth)
    stand = dict(truth, words=words(truth)) if words else truth
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(stand))
    return truth, rgb, trace_core.auto_read(rgb, NO_WORDS, bool(jpeg), "Sample IEM")


def failed(r):
    return [c.name for c in r.checks if not c.ok]


def reason(r, name):
    return next((c.reason for c in r.checks if c.name == name), None)


def is_hz(truth, w):
    return w["y0"] > truth["plot"]["y1"]  # (the frequency labels are under the grid, the dB labels in it)


CHECKS = ["axes_plot", "axes_grid", "axes_hz_labels", "axes_hz_range", "axes_db_labels", "axes_db_range",
          "trace_curve", "trace_gaps", "trace_band", "trace_steps", "trace_single"]


def test_all_checks_pass(read, check):
    truth, _rgb, r = read(1000)
    check("website graph 1000 px PNG: all checks pass", r.ok and not failed(r) and len(r.checks) == len(CHECKS),
          "; ".join(f"{c.name}: {c.reason}" for c in r.checks))
    names = [c.name for c in r.checks]
    check("website graph: the checks come in their sequence, each one an axes_ or trace_ check", names == CHECKS, names)
    t = r.tracer
    check("website graph: one curve, named Average, the selected one, and its points",
          len(t.curves) == 1 and t.curves[0]["label"] == "Average" and t.cur == 0 and r.curve is t.curves[0]
          and r.target is None and r.points and r.target_points is None,
          f"{[c['label'] for c in t.curves]}, cur {t.cur}")
    check("website graph: the axis values are 20 Hz to 20 kHz and 80 dB to 40 dB, from the grid lines",
          (t.v["f1"], t.v["f2"], t.v["d1"], t.v["d2"]) == ("20", "20000", "80", "40") and len(t.v_lines) == 25
          and len(t.grid_x) == 25 and len(t.h_lines) == 9 and t.v["every"], f"{t.v}, {len(t.h_lines)} dB lines")
    p = r.plot
    check("website graph: the tracer has the crop of the picture (the graph and a small margin)",
          p and t.W == p["x1"] - p["x0"] and t.H == p["y1"] - p["y0"] and t.px.shape[:2] == (t.H, t.W), f"{p}, {t.W}x{t.H}")
    check("website graph: the green boxes of the window show the labels that the app used", len(t.label_words) >= 7,
          len(t.label_words))
    drawn = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in ("#1a48a0", "#0d357d")]
    colour = r.curve["colour"]
    check("website graph: the curve has the color of the drawn channels (within 30)",
          min(math.dist(colour, d) for d in drawn) <= 30, colour)
    check("website graph: a PNG is not loaded as a JPEG", t.ta["jpeg"] is False, t.ta["jpeg"])
    want = f"{reason(r, 'axes_hz_range')} {reason(r, 'axes_db_range')}"
    check("website graph: the axis note is the reasons of the two range checks", t.axis_note == want == t.detect_note,
          (t.axis_note, want))


@pytest.mark.parametrize("w", [600, 1000, 1400])
def test_curve_is_the_true_average(read, check, w):
    for jpeg in (None, 60):
        truth, _rgb, r = read(w, jpeg)
        e = errors(r.points, truth["avg"])
        # (0.96 of the span: the faded ends are cut back to where both channels are, finding A4)
        check(f"website graph 600, 1000 and 1400 px, PNG and JPEG: the average curve is less than 0.1 dB from the true "
              f"average (mean), 0.5 dB at the worst point ({w} px, {'JPEG' if jpeg else 'PNG'})",
              e and e[0] < 0.1 and e[1] < 0.5 and e[2] > 0.96, e)
        check(f"website graph: a JPEG is loaded as a JPEG, a PNG not ({w} px, {'JPEG' if jpeg else 'PNG'})",
              r.tracer.ta["jpeg"] is bool(jpeg), r.tracer.ta["jpeg"])


def test_average_not_one_channel(read, check):
    truth, _rgb, r = read(1000)
    e = errors(r.points, truth["avg"])
    el, er = (errors(r.points, fn) for fn in truth["chans"])
    check("website graph: the curve is the average of the two channels, not one of them",
          e and el and er and e[0] < el[0] and e[0] < er[0] and e[1] < el[1] and e[1] < er[1], (e, el, er))


def test_grid_in_a_full_page(read, check):
    for w in (600, 1000):
        truth, rgb, r = read(w, None, page=True)
        p = trace_auto.find_plot(rgb)
        tp = truth["plot"]
        off = [abs(p[k] - tp[k]) for k in ("x0", "x1", "y0", "y1")] if p["ok"] else None
        check(f"website graph in a full page: the app finds the grid within 1.5 pixels of its true edges ({w} px)",
              off and max(off) <= 1.5 and r.ok, (off, failed(r)))
        e = errors(r.points, truth["avg"])
        check(f"website graph in a full page: the average curve is less than 0.1 dB from the true average ({w} px)",
              e and e[0] < 0.1 and e[1] < 0.5, e)
    # the state moved to the crop (1000 px: the crop's corner is not 0, 0)
    truth, rgb, r = read(1000, None, page=True)
    t, c = r.tracer, r.plot
    cx, cy = c["x0"], c["y0"]
    tp = truth["plot"]
    pw = tp["x1"] - tp["x0"]
    check("website graph in a full page: the crop is the grid with the margins of the code (0.05 of the width at the "
          "sides, 0.04 above, 0.07 below, cut at the picture's edges), within 2 pixels",
          cx > 0 and cy > 0 and abs(cx - (tp["x0"] - 0.05 * pw)) <= 2 and abs(cy - (tp["y0"] - 0.04 * pw)) <= 2
          and abs(c["x1"] - min(rgb.shape[1], tp["x1"] + 0.05 * pw)) <= 2 and abs(c["y1"] - (tp["y1"] + 0.07 * pw)) <= 2,
          (c, tp))
    by_text = {}
    for w_ in truth["words"]:
        by_text.setdefault(w_["text"], []).append(w_)
    far = []
    for w_ in t.label_words:
        best = min((max(abs(w_[k] - (q[k] - (cx if k[0] == "x" else cy))) for k in ("x0", "y0", "x1", "y1"))
                    for q in by_text.get(w_["text"], [])), default=99)
        if best > 2:
            far.append((w_["text"], best))
    check("website graph in a full page: each green box is at its label in the crop, within 2 pixels",
          len(t.label_words) >= 7 and not far, far)
    rows = [y - cy for y in truth["db_rows"]]
    check("website graph in a full page: the dB grid lines are at their rows in the crop, within 1.5 pixels",
          len(t.h_lines) == len(rows) and max(abs(a["pos"] - b) for a, b in zip(t.h_lines, rows)) <= 1.5,
          [(round(a["pos"], 1), round(b, 1)) for a, b in zip(t.h_lines, rows)])
    cols = [truth["x"](f) - cx for f in wg.TICKS]
    check("website graph in a full page: the frequency grid lines are at their columns in the crop, within 1.5 pixels",
          len(t.v_lines) == 25 and max(abs(a["pos"] - b) for a, b in zip(t.v_lines, cols)) <= 1.5
          and max(abs(g["p"] - b) for g, b in zip(t.grid_x, cols)) <= 1.5, [round(a["pos"] - b, 2) for a, b in zip(t.v_lines, cols)])
    box = t.box
    check("website graph in a full page: the box is the grid in the crop, within 1.5 pixels",
          abs(box["x0"] - (tp["x0"] - cx)) <= 1.5 and abs(box["x1"] - (tp["x1"] - cx)) <= 1.5
          and abs(box["y0"] - (tp["y0"] - cy)) <= 1.5 and abs(box["y1"] - (tp["y1"] - cy)) <= 1.5, (box, tp, cx, cy))


def test_one_curve(read, check):
    truth, _rgb, r = read(1000, None, one_curve=True)
    e = errors(r.points, truth["avg"])
    check("website graph with one curve: the curve is that line, all checks pass",
          r.ok and e and e[0] < 0.1 and e[1] < 0.5, (failed(r), e))


@pytest.mark.parametrize("kind,jpeg", [("solid", None), ("dashed", 60)])
def test_target(read, check, kind, jpeg):
    truth, _rgb, r = read(1000, jpeg, target=kind)
    t = r.tracer
    check(f"website graph with a solid target and with a dashed target: the second curve is marked as target, the "
          f"first curve stays selected ({kind})",
          len(t.curves) == 2 and r.target is t.curves[1] and t.curves[1].get("target") is True
          and t.curves[1]["label"] == "Target" and not t.curves[0].get("target") and t.cur == 0 and r.ok,
          f"{[(c['label'], c.get('target')) for c in t.curves]}, cur {t.cur}, {failed(r)}")
    e = errors(r.target_points, truth["tgt"])
    # (0.8 of the span: where the band hides the target line, at the left end, there are no points, finding A9)
    check(f"website graph with a target: the target curve is less than 0.4 dB from the true target (mean), 1 dB at "
          f"the worst point, on 80 % of the width ({kind})", e and e[0] < 0.4 and e[1] < 1 and e[2] >= 0.8, e)
    ea = errors(r.points, truth["avg"])
    check(f"website graph with a target: the average curve stays less than 0.1 dB from the true average ({kind})",
          ea and ea[0] < 0.1 and ea[1] < 0.5, ea)


def test_target_where_the_band_hides_it(monkeypatch, check):
    cross = lambda f: wg._iem(f) + 3.5 * math.sin(math.log2(f) * 3.1)  # noqa: E731 (crosses the curve many times)
    for w, jpeg, kw, what in ((1000, 60, {"target": "dashed", "target_fn": cross}, "a dashed target that crosses the "
                               "curve many times, JPEG 60"),
                              (600, 60, {"target": "dashed"}, "600 px, dashed, JPEG 60"),
                              (1000, None, {"target": "solid"}, "1000 px, solid")):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, **kw)
        e = errors(r.target_points, truth["tgt"])
        check(f"a target line that the band hides: no target, or the target is less than 1 dB from the true target at "
              f"each point ({what})", r.target is None or (e and e[1] < 1), e)


def test_no_target(read, check):
    for kw in ({}, {"page": True}, {"one_curve": True}):
        _truth, _rgb, r = read(1000, None, **kw)
        check(f"website graph with no target: no second curve ({kw or 'the graph only'})",
              len(r.tracer.curves) == 1 and r.target is None, [c["label"] for c in r.tracer.curves])


def test_labels_ten_times_off(read, check):
    for decade, words in ((1, "200 Hz to 200 kHz"), (-1, "2 Hz to 2 kHz")):
        _truth, _rgb, r = read(1000, None, decade=decade)
        check(f"labels 10 times too high and 10 times too low: the frequency range check fails and gives the range, "
              f"the other checks pass ({words})",
              failed(r) == ["axes_hz_range"] and words in reason(r, "axes_hz_range")
              and r.tracer.v["f1"] == f"{20 * 10 ** decade:g}", (failed(r), reason(r, "axes_hz_range")))


def test_no_labels(read, check):
    truth, _rgb, r = read(1000, None, labels=False)
    check("no labels in the picture: the label checks fail, the curve is traced, no points, no error",
          set(failed(r)) == {"axes_hz_labels", "axes_hz_range", "axes_db_labels", "axes_db_range", "trace_band"}
          and r.curve is not None and np.isfinite(r.curve["ys"]).sum() > 900 and r.points is None
          and r.tracer.v["d1"] == "" and (r.tracer.v["f1"], r.tracer.v["f2"]) == ("20", "20000"),
          failed(r))
    check("no labels in the picture: the reasons say that a larger picture can help",
          "A larger picture can help" in reason(r, "axes_hz_labels") and "A larger picture can help" in reason(r, "axes_db_labels"),
          (reason(r, "axes_hz_labels"), reason(r, "axes_db_labels")))


def test_no_text_reader(qapp, monkeypatch, check):
    img, truth = website_graph(plot_w=1000)
    rgb = as_rgb(img)

    def no_reader(_rgb):
        raise ocr.Unavailable("no text reader for this language (a stand-in for the test)")
    monkeypatch.setattr(trace_auto, "read_strip", REAL_READ_STRIP)
    r = trace_core.auto_read(rgb, no_reader, False, "Sample IEM")
    hz, db = reason(r, "axes_hz_labels"), reason(r, "axes_db_labels")
    check("no text reader: the label checks give the cause of ocr.Unavailable in a sentence of its own, no error",
          hz == "The app did not read the frequency labels. No text reader for this language (a stand-in for the test)."
          and db == "The app did not read the dB labels. No text reader for this language (a stand-in for the test)."
          and r.curve is not None and not r.ok, (hz, db))
    r2 = trace_core.auto_read(rgb, None, False, "Sample IEM")
    check("no text reader: with no ocr_words, the label checks say that the app did not read the labels",
          reason(r2, "axes_hz_labels") == "The app did not read the frequency labels."
          and reason(r2, "axes_db_labels") == "The app did not read the dB labels." and r2.curve is not None,
          (reason(r2, "axes_hz_labels"), reason(r2, "axes_db_labels")))

    def broken(_rgb):
        raise OSError("[WinError 5] Access is denied")
    r3 = trace_core.auto_read(rgb, broken, False, "Sample IEM")
    check("a text reader that gives an other error: a fixed sentence, without the error's own text",
          reason(r3, "axes_hz_labels") == "The app did not read the frequency labels. The text reader of Windows gave "
          "an error." and "WinError" not in reason(r3, "axes_db_labels"), (reason(r3, "axes_hz_labels"),))
    # an error at the dB labels only: the frequency labels that were read stay, and the two frequency checks agree
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))

    def db_error(*_a):
        raise KeyError("x0")
    monkeypatch.setattr(trace_auto, "read_db", db_error)
    r4 = trace_core.auto_read(rgb, NO_WORDS, False, "Sample IEM")
    check("an error at the dB labels only: the frequency label check and the frequency range check both pass, the dB "
          "label check gives the fixed sentence",
          [c.ok for c in r4.checks[2:4]] == [True, True]
          and reason(r4, "axes_db_labels") == "The app did not read the dB labels. The text reader of Windows gave an "
          "error.", [tuple(c) for c in r4.checks[2:6]])


def test_channels_apart(read, check):
    _truth, _rgb, r = read(1000, None, offset_db=10)
    check("channels 10 dB apart: the band check fails", "trace_band" in failed(r) and not r.ok
          and "It can contain more than one measurement" in reason(r, "trace_band"), (failed(r), reason(r, "trace_band")))


def test_not_a_graph(qapp, check):
    rng = np.random.default_rng(1)
    white = np.full((400, 600, 3), 255, np.uint8)
    noise = rng.integers(0, 256, (400, 600, 3), dtype=np.uint8)
    from PySide6.QtGui import QColor, QFont, QImage, QPainter
    img = QImage(600, 400, QImage.Format_RGB888)
    img.fill(QColor("white"))
    p = QPainter(img)
    p.setFont(QFont("Arial", 14))
    for i in range(12):
        p.drawText(20, 30 + i * 30, "This is a page of text with no graph in it, line %d of 12." % (i + 1))
    p.end()
    text = as_rgb(img)
    for what, rgb in (("white", white), ("noise", noise), ("text only", text)):
        before = rgb.copy()
        r = trace_core.auto_read(rgb, NO_WORDS, False, "Not a graph")
        check(f"a picture that is not a graph (white, noise, text only): the plot check fails, the tracer has the "
              f"picture, no error ({what})",
              [c.name for c in r.checks] == ["axes_plot"] and not r.ok and r.tracer.has_image
              and r.tracer.px.shape == rgb.shape and r.curve is None and r.plot is None, [tuple(c) for c in r.checks])
        check(f"auto_read does not change the caller's picture ({what})", np.array_equal(rgb, before))
    odd = {"1 x 1": np.zeros((1, 1, 3), np.uint8), "10 x 2000": rng.integers(0, 256, (10, 2000, 3), dtype=np.uint8),
           "2000 x 10": np.zeros((2000, 10, 3), np.uint8), "one color": np.full((300, 900, 3), (12, 80, 200), np.uint8),
           "noise 900 x 1600": rng.integers(0, 256, (900, 1600, 3), dtype=np.uint8),
           "a 1-D array": np.zeros(100, np.uint8), "a 2-D (gray) array": np.full((300, 400), 200, np.uint8),
           "an empty picture": np.zeros((0, 0, 3), np.uint8), "RGBA, not a graph": np.full((300, 400, 4), 255, np.uint8),
           "two channels": np.zeros((300, 400, 2), np.uint8)}
    for what, rgb in odd.items():
        try:
            fp = trace_auto.find_plot(rgb)
            r = trace_core.auto_read(rgb, NO_WORDS, False, "x")
            err = ""
        except Exception as e:  # noqa: BLE001 - (the error, said)
            fp, r, err = None, None, repr(e)
        check(f"find_plot and auto_read do not raise for a picture of any size, color or form ({what})",
              not err and not fp["ok"] and not r.ok and r.checks[0].name == "axes_plot", err or (fp, r.checks))


def test_rgba_graph(read, check):
    _truth, rgb, r = read(1000)
    rgba = np.concatenate([rgb, np.full(rgb.shape[:2] + (1,), 255, np.uint8)], axis=2)
    try:
        r4 = trace_core.auto_read(rgba, NO_WORDS, False, "Sample IEM")
        err = ""
    except Exception as e:  # noqa: BLE001 - (the error, said)
        r4, err = None, repr(e)
    check("a graph as an RGBA array (H x W x 4): read as its RGB channels, the same points, no error",
          not err and r4.ok and r4.points == r.points and r4.tracer.px.shape[2] == 3, err or failed(r4))


def test_app_sample_graph(qapp, monkeypatch, check):
    from ui.trace_window import rgb_of, sample_image
    img, _truth = sample_image()
    monkeypatch.setattr(trace_auto, "read_strip", lambda *a, **k: [])
    try:
        r = trace_core.auto_read(rgb_of(img), NO_WORDS, False, "Sample IEM")
        err = ""
    except Exception as e:  # noqa: BLE001 - (the error, said)
        r, err = None, repr(e)
    check("the app's sample graph (two colors): the one-measurement check fails, no error",
          not err and "trace_single" in failed(r), err or failed(r))


# ---------------------------------------------------------------- each check fails, for the correct reason
def _erase_curve(cols):
    """edit(rgb, truth): the curve's pixels (blue: blue over red by 40 or more) in those columns of the grid made
    the background's color."""
    def edit(rgb, truth):
        for x in cols(truth):
            p = rgb[:, x].astype(int)
            rgb[:, x][(p[:, 2] - p[:, 0]) >= 40] = CREAM
    return edit


def test_trace_curve_and_gaps_fail(monkeypatch, check):
    at = lambda f, n: lambda truth: range(int(truth["x"](f)), int(truth["x"](f)) + n)  # noqa: E731
    _t, _rgb, r = fresh(monkeypatch, edit=_erase_curve(at(700, 12)))
    words = (reason(r, "trace_gaps") or "").split()
    check("1.2 % of the curve not in the picture: the traced-parts check fails with the width of the part (11 to 15 "
          "pixels), the curve check passes", "trace_gaps" in failed(r) and "trace_curve" not in failed(r)
          and " ".join(words[:7]) == "A part of the curve that is" and words[7].isdigit() and 11 <= int(words[7]) <= 15
          and " ".join(words[8:]) == "pixels wide is not traced.", (failed(r), reason(r, "trace_gaps")))
    _t, _rgb, r = fresh(monkeypatch, edit=_erase_curve(at(700, 50)))
    words = (reason(r, "trace_curve") or "").split()
    check("5 % of the curve not in the picture: the curve check fails (only 92 to 95 %)",
          "trace_curve" in failed(r) and " ".join(words[:5]) == "The curve is on only" and words[5].isdigit()
          and 92 <= int(words[5]) <= 95 and " ".join(words[6:]) == "% of the width of the grid.", reason(r, "trace_curve"))


def test_grid_check_fails(monkeypatch, check):
    def edit(rgb, truth):
        y0, y1 = int(truth["plot"]["y0"]) - 2, int(truth["plot"]["y1"]) + 3
        for f in (300, 400, 3000, 4000):
            x = int(round(truth["x"](f)))
            rgb[y0:y1, x - 2:x + 3] = CREAM
    _t, _rgb, r = fresh(monkeypatch, edit=edit)
    check("4 of the 25 frequency grid lines not in the picture: the grid check fails (only 21 of the 25)",
          "axes_grid" in failed(r) and reason(r, "axes_grid") == "The app found only 21 of the 25 frequency grid lines "
          "of a graph from the website.", (failed(r), reason(r, "axes_grid")))


def test_hz_labels_fail(monkeypatch, check):
    def only(n):
        def words(truth):
            hz = [w for w in truth["words"] if is_hz(truth, w)]
            return [w for w in truth["words"] if not is_hz(truth, w)] + hz[5:5 + n]
        return words
    for n, text in ((2, "Only 2 frequency labels agree with the grid lines. The app must have 3 or more labels that "
                        "agree."),
                    (1, "Only 1 frequency label agrees with the grid lines. The app must have 3 or more labels that "
                        "agree.")):
        _t, _rgb, r = fresh(monkeypatch, words=only(n))
        check(f"{n} frequency label(s) read: the frequency label check fails with its own sentence, and the range "
              f"check cannot make sure ({n})",
              reason(r, "axes_hz_labels") == text and "axes_hz_labels" in failed(r) and "axes_hz_range" in failed(r),
              (reason(r, "axes_hz_labels"), failed(r)))

    def against(truth):
        hz = [dict(w) for w in truth["words"] if is_hz(truth, w)][5:11]
        for w in hz[:2]:
            v = trace_core.hz_num(w["text"])
            w["text"] = f"{v * 10 / 1000:g}k" if v * 10 >= 1000 else f"{v * 10:g}"
        return [w for w in truth["words"] if not is_hz(truth, w)] + hz
    _t, _rgb, r = fresh(monkeypatch, words=against)
    check("6 frequency labels read, 2 of them 10 times too high: too many labels do not agree, the check fails",
          reason(r, "axes_hz_labels") == "4 frequency labels agree with the grid lines, and 2 do not. Too many labels "
          "do not agree." and "axes_hz_labels" in failed(r), reason(r, "axes_hz_labels"))


def _db(truth, keep):
    """The true words with the dB labels changed: keep {true dB value: text}; dB labels not in keep are not read."""
    out = []
    for w in truth["words"]:
        if is_hz(truth, w):
            out.append(w)
        elif keep.get(int(trace_core.db_num(w["text"]))):
            out.append(dict(w, text=keep[int(trace_core.db_num(w["text"]))]))
    return out


def test_db_labels(monkeypatch, check):
    cases = (({60: "60"}, False, "The app read only one dB label. It set 5 dB between grid lines.", ("80", "40")),
             ({70: "10", 75: "15"}, False, "Only 2 dB labels agree with the grid lines (5 dB between grid lines). The "
              "app must have 3 or more labels that agree.", None),
             ({60: "80", 65: "85"}, False, None, None),
             ({70: "10", 75: "15", 60: "60"}, False, None, None),
             ({60: "60", 65: "65", 70: "70"}, True, "3 dB labels agree with the grid lines (5 dB between grid lines).",
              ("80", "40")),
             ({60: "60", 65: "65", 70: "70", 45: "15"}, True, "3 dB labels agree with the grid lines (5 dB between grid "
              "lines), and 1 does not.", ("80", "40")),
             ({60: "60", 65: "65", 70: "70", 45: "15", 50: "20"}, False, "3 dB labels agree with the grid lines (5 dB "
              "between grid lines), and 2 do not. Too many labels do not agree.", None))
    for keep, ok, text, axis in cases:
        _t, _rgb, r = fresh(monkeypatch, words=lambda truth, keep=keep: _db(truth, keep))
        got = reason(r, "axes_db_labels")
        check(f"the dB labels {keep}: the dB label check {'passes' if ok else 'fails'} (3 or more labels that agree, "
              f"and at most one against for each 3)",
              ("axes_db_labels" not in failed(r)) is ok and (text is None or got == text) and (r.ok if ok else not r.ok)
              and (axis is None or (r.tracer.v["d1"], r.tracer.v["d2"]) == axis),
              (got, failed(r), r.tracer.v["d1"], r.tracer.v["d2"]))


def test_db_labels_each_by_itself(monkeypatch, check):
    """read_db reads each label's part by itself (3 copies side by side) when the strip of all labels is not enough."""
    img, truth = website_graph(plot_w=1000)
    rgb = as_rgb(img)
    plot = trace_auto.find_plot(rgb)
    strip = truth_reader(truth)
    asked = []

    def only_copies(rgb_, ocr_words, x0, y0, x1, y1, k, gray, copies=1):
        asked.append(copies)
        return [w for w in strip(rgb_, ocr_words, x0, y0, x1, y1, k, gray, copies) if copies > 1]
    monkeypatch.setattr(trace_auto, "read_strip", only_copies)
    db = trace_auto.read_db(rgb, NO_WORDS, plot)
    check("dB labels that the strip does not give: read each by itself with 3 copies, and they agree (9 labels, 5 dB)",
          db and len(db["pairs"]) == 9 and db["step"] == -5 and db["against"] == 0 and trace_auto.LABEL_COPIES in asked
          and asked.count(1) == len(trace_auto.TREATMENTS), (db and len(db["pairs"]), asked[:8]))


def test_db_range(monkeypatch, check):
    check("a usual dB axis: its span, its lowest and highest values are constants",
          trace_auto.DB_SPAN == (15, 120) and (trace_auto.DB_LOWEST, trace_auto.DB_HIGHEST) == (10, 130))
    _t, _rgb, r = fresh(monkeypatch, words=lambda truth: _db(truth, {v: f"{v - 60}" for v in range(40, 81, 5)}))
    check("all dB labels read 60 dB too low (they agree): the dB range check fails, its values are not usual",
          reason(r, "axes_db_range") == "The dB axis is -20 dB to 20 dB. This range is not usual for a graph of an IEM "
          "or headphone." and "axes_db_labels" not in failed(r) and "axes_db_range" in failed(r),
          (reason(r, "axes_db_range"), failed(r)))
    _t, _rgb, r = fresh(monkeypatch, db_range=(60, 72), db_step=2)
    check("an axis of 12 dB: the dB range check fails, its span is not usual",
          reason(r, "axes_db_range") == "The dB axis is 60 dB to 72 dB. This range is not usual for a graph of an IEM "
          "or headphone." and "axes_db_range" in failed(r), reason(r, "axes_db_range"))
    _t, _rgb, r = fresh(monkeypatch, db_range=(55, 95))
    check("an axis of 55 dB to 95 dB: the dB range check passes", reason(r, "axes_db_range") == "The dB axis is 55 dB "
          "to 95 dB." and "axes_db_range" not in failed(r), reason(r, "axes_db_range"))


def test_band_check(monkeypatch, check):
    _t, _rgb, r = fresh(monkeypatch, offset_db=-6.5)
    x = float(reason(r, "trace_band").split()[5])
    check("channels about 7 dB apart (6 to 9): the band check fails and gives the width",
          "trace_band" in failed(r) and 6 < x < 9, reason(r, "trace_band"))
    for off in (5, -5):
        truth, _rgb, r = fresh(monkeypatch, offset_db=off)
        fs = [20 * 1000 ** (i / 999) for i in range(1000)]
        true = float(np.percentile([abs(truth["chans"][0](f) - truth["chans"][1](f)) for f in fs], 90))
        words = reason(r, "trace_band").split()
        x = float(words[9] if words[0] == "The" and words[1] == "difference" else words[5])
        check(f"the band check gives the true difference of the channels within 0.3 dB, the same for the higher one "
              f"left or right (offset {off:+} dB)", abs(x - true) <= 0.3, (x, round(true, 2), reason(r, "trace_band")))


# ---------------------------------------------------------------- the review's cases of the curve
def test_channel_cut_from_the_band(monkeypatch, check):
    truth, _rgb, r = fresh(monkeypatch, 1000, 60, colours=ORANGE)
    e = errors(r.points, truth["avg"])
    check("orange channels, JPEG 60: the second channel is kept where it breaks from the band, the curve is less than "
          "0.5 dB from the true average at each point", r.ok and e and e[1] < 0.5, (failed(r), e))


def test_channel_out_of_the_grid(monkeypatch, check):
    for kw in ({"db_range": (50, 90)}, {"db_range": (50, 76), "db_step": 2}):
        truth, _rgb, r = fresh(monkeypatch, **kw)
        e = errors(r.points, truth["avg"])
        check(f"one channel goes below the grid: the read fails, or the curve is less than 0.5 dB from the true average "
              f"({kw})", not r.ok or (e and e[1] < 0.5), (r.ok, failed(r), e))


def test_faded_ends(monkeypatch, check):
    for off in (-3, 3):
        truth, _rgb, r = fresh(monkeypatch, offset_db=off)
        e = errors(r.points, truth["avg"], 20, 20000)
        check(f"channels 3 dB apart: at the faded ends the curve is the average of both, less than 0.5 dB at each "
              f"point ({off:+} dB)", r.ok and e and e[1] < 0.5, (failed(r), e))


def test_legend_on_the_curve(monkeypatch, check):
    for xy, one in (((650, 236), True), ((300, 150), False)):
        truth, _rgb, r = fresh(monkeypatch, legend_xy=xy, one_curve=one)
        e = errors(r.points, truth["avg"])
        check(f"the legend's text in the curve's color on the curve: the read fails, or the curve is less than 0.5 dB "
              f"from the true average ({xy}, {'one curve' if one else 'two channels'})",
              not r.ok or (e and e[1] < 0.5), (r.ok, e))
    for xy in ((650, 232), (650, 220), (620, 160)):
        truth, _rgb, r = fresh(monkeypatch, legend_xy=xy)
        e = errors(r.points, truth["avg"])
        check(f"the legend's text across a steep part of the curve: the read fails, or the curve is less than 1 dB from "
              f"the true average (a known limit: under 0.5 dB is not always possible) ({xy})",
              not r.ok or (e and e[1] < 1), (r.ok, e))


def test_steps_check(monkeypatch, check):
    """trace_steps fails for a short rise of the band's height (text) and for a channel that goes suddenly."""
    n = 1000  # (a grid 1000 pixels wide: a step of text is 2 to 12 columns)
    b = {"x0": 0, "lw": 2.0, "top": np.full(n, 100.0), "bot": np.full(n, 104.0), "runs": np.ones(n, int),
         "c1": np.full(n, 102.0), "c2": np.full(n, 102.0)}
    check("a band with no step: no step", trace_auto.height_steps(b) == [], trace_auto.height_steps(b))
    text = dict(b, bot=b["bot"].copy())
    text["bot"][80:84] += 9
    check("the band 9 rows higher for 4 columns (4.5 line widths): a step of text", ("text" in
          [k for _x, k in trace_auto.height_steps(text)]), trace_auto.height_steps(text))
    low = dict(text, bot=b["bot"].copy())
    low["bot"][80:84] += 7
    check("the band 7 rows higher for 4 columns (3.5 line widths): no step (the real pictures go to 3)",
          trace_auto.height_steps(low) == [], trace_auto.height_steps(low))
    lost = dict(b, bot=np.r_[np.full(500, 114.0), np.full(500, 104.0)], runs=np.r_[np.full(500, 2), np.ones(500, int)],
                c2=np.r_[np.full(500, 112.0), np.full(500, 102.0)])
    check("two lines 10 rows apart that become one line suddenly, in the place of the first: a step of a lost line",
          [k for _x, k in trace_auto.height_steps(lost)][:1] == ["line"], trace_auto.height_steps(lost))
    join = dict(lost, bot=np.full(n, 114.0))
    check("two lines that become one run with the same height (a steep part): no step", trace_auto.height_steps(join) == [],
          trace_auto.height_steps(join))
    def wrap(fn):
        def band(*a):
            out = fn(*a)
            j = int(np.flatnonzero(np.isfinite(out["top"]))[400])
            out["bot"][j:j + 4] += 6 * out["lw"]
            return out
        return band
    monkeypatch.setattr(trace_auto, "band", wrap(trace_auto.band))
    img, truth = website_graph(plot_w=1000)
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    r = trace_core.auto_read(as_rgb(img), NO_WORDS, False, "Sample IEM")
    check("a band with a short step: the steps check fails, with the frequency of the step",
          failed(r) == ["trace_steps"] and reason(r, "trace_steps").startswith("The height of the band of curves "
                                                                               "changes suddenly at "),
          (failed(r), reason(r, "trace_steps")))


def test_two_measurements(monkeypatch, check):
    """trace_single has two rules: a second hue on half of the columns or more, and a second line in a strong color."""
    for what, fn, col in (("a red curve on 57 % of the width only (the hue rule; too short for a second line)",
                           lambda f: wg._iem(f) + 5 if f < 1500 else -100, "#c0392b"),
                          ("a violet curve (a second line in a strong color; its hue is near the first one's)",
                           lambda f: wg._iem(f) + 5, "#8e44ad")):
        _truth, _rgb, r = fresh(monkeypatch, one_curve=True, extra=[(fn, col)])
        check(f"a second measurement in another color: the one-measurement check fails ({what})",
              "trace_single" in failed(r) and reason(r, "trace_single").startswith("The picture has more than one "
                                                                                   "measurement."), failed(r))


def test_orange_curve_is_one_measurement(monkeypatch, check):
    for jpeg in (None, 90):
        _truth, _rgb, r = fresh(monkeypatch, 1000, jpeg, colours=ORANGE)
        check(f"orange channels: a dB grid line is not a second line, the one-measurement check passes "
              f"({'JPEG 90' if jpeg else 'PNG'})", r.ok and "trace_single" not in failed(r), failed(r))


# ---------------------------------------------------------------- the tracer's part
def test_outputs(read, check):
    _truth, _rgb, r = read(1000, None, target="solid")
    t = Tracer()
    t.take(r.tracer)
    t.curves = [dict(c) for c in t.curves]  # (outputs does not change curves; a copy all the same: the cache stays)
    outs = t.outputs()
    check("the result's Tracer saves one file for the average, without the target",
          [o["file"] for o in outs] == ["Sample IEM.txt"] and outs[0]["label"] == "Average", [o["file"] for o in outs])
    t.cur = 1
    one = t.outputs(only_current=True)
    t.cur = 0
    check("outputs(only_current=True) with the target selected gives the target",
          [o["label"] for o in one] == ["Target"] and one[0]["file"] == "Sample IEM.txt", [o["label"] for o in one])
    named = t.outputs(name="Aria 2")
    check("outputs with a name use it", [o["file"] for o in named] == ["Aria 2.txt"] and t.v["name"] == "Sample IEM",
          [o["file"] for o in named])


def test_traced_again_is_a_measurement(monkeypatch, check):
    _truth, _rgb, r = fresh(monkeypatch, 1000, 60, target="dashed")
    t = Tracer()
    t.take(r.tracer)
    i = next(i for i, c in enumerate(t.curves) if c.get("target"))
    t.cur = i
    ys, avg = t.curves[i]["ys"], t.curves[0]["ys"]
    # (a click on the target line where it is far from the measurement)
    both = np.flatnonzero(np.isfinite(ys) & np.isfinite(avg))
    x = int(both[np.argmax(np.abs(ys[both] - avg[both]))])
    y = float(ys[x])
    said = t.trace_at(x, y)
    files = [o["file"] for o in t.outputs()]
    check("a curve that the user traces again is a measurement curve",
          not t.curves[i].get("target") and files == ["Sample IEM Average.txt", "Sample IEM Target.txt"], (files, said))
    t.undo()
    check("undo gives back the target line's mark", t.curves[i].get("target") is True)

    def draw():
        t.push_undo()  # (as the window does before a line)
        t.draw_segment(x, y, x + 5, y)
    for what, act in (("make a line", draw), ("erase", lambda: t.erase(x - 3, 0, x + 3, t.H)), ("smooth", t.smooth),
                      ("clear", t.clear)):
        t.cur = i
        act()
        check(f"a target curve that the user changes is a measurement curve ({what})", not t.curves[i].get("target"))
        t.undo()
    _truth, _rgb, r2 = fresh(monkeypatch, 1000, None, target="solid")
    t2 = Tracer()
    t2.take(r2.tracer)
    t2.remove_curve(0)
    check("after the average is removed, the target curve stays, with its mark",
          len(t2.curves) == 1 and t2.curves[0].get("target") is True, [c.get("target") for c in t2.curves])
    t2.remove_curve(0)
    check("a target curve that stays as the only curve and is removed is a measurement curve",
          len(t2.curves) == 1 and not t2.curves[0].get("target"), t2.curves)


def _groups():
    return set(trace_core.TAKE_COPIED), set(trace_core.TAKE_KEPT), set(trace_core.TAKE_RESET)


def test_take_groups(qapp, check):
    copied, kept, reset = _groups()
    every = copied | kept | reset
    check("Tracer.take: no part of the state is in two groups",
          not (copied & kept) and not (copied & reset) and not (kept & reset), (copied & kept, copied & reset, kept & reset))
    loaded = Tracer()
    img, _truth = website_graph(plot_w=600)
    loaded.load(as_rgb(img), "x")
    for what, t in (("a loaded tracer", loaded), ("a new tracer", Tracer())):
        missing = [f"ta.{k}" for k in t.ta if f"ta.{k}" not in every] + \
            [f"v.{k}" for k in t.v if f"v.{k}" not in every] + \
            [k for k in vars(t) if k not in ("ta", "v") and k not in every]
        check(f"Tracer.take: each value of the tracer is copied, kept or reset ({what})", not missing, missing)
        stale = [k for k in every if not (k.startswith("ta.") and k[3:] in t.ta or k.startswith("v.") and k[2:] in t.v
                                           or "." not in k and hasattr(t, k))]
        check(f"Tracer.take: each name in the groups is a part of the tracer's state ({what})", not stale, stale)


def test_take_of_a_result_with_no_picture(qapp, check):
    for what, rgb in (("an empty picture", np.zeros((0, 0, 3), np.uint8)),
                      ("a 2-D array", np.full((300, 400), 200, np.uint8))):
        r = trace_core.auto_read(rgb, None)
        t = Tracer()
        try:
            t.take(r.tracer)
            err = ""
        except Exception as e:  # noqa: BLE001 - (the error, said)
            err = repr(e)
        check(f"Tracer.take of a result with no picture: no error, no picture ({what})",
              not err and not t.has_image and t.axis_note == "", err)


# what take() copies from the result (a list of its own, not trace_core's tuples: a value in the wrong group fails)
COPIED = ["px", "W", "H", "h_lines", "v_lines", "grid_x", "box", "label_words", "src_name", "curves", "cur", "cal",
          "bg", "dbg", "axis_note", "detect_note", "ta.jpeg", "ta.noise", "ta.px_oct", "ta.notes", "ta.dashed_found",
          "ta.last_ocr", "ta.last_trace", "v.name", "v.f1", "v.f2", "v.d1", "v.d2", "v.every"]


@pytest.mark.parametrize("auto", [True, False])
def test_take_values(monkeypatch, qapp, check, auto):
    _truth, _rgb, r = fresh(monkeypatch, 1000, 60, target="solid")  # (a JPEG: ta.jpeg differs from the old picture's)
    src = r.tracer
    t = Tracer()
    t.ta["enabled"] = auto
    t.load(as_rgb(website_graph(plot_w=600)[0]), "Old picture")
    t.v.update(tol=99, ppo=12, fmin=40, fmax=16000, snap=False, dashed=True)
    t.mark_your_value("tol")
    t.auto_trace()  # (a trace: undo and the color matches of the old picture)
    t.push_undo()
    t.undo()  # (and a redo)
    t.typed["d"] = True
    t.moved["f"] = True
    token = t.label_token

    def get(o, key):
        part, _, k = key.rpartition(".")
        return getattr(o, part)[k] if part else getattr(o, k)
    check(f"Tracer.take: before take, undo, redo and the color matches have entries (automatic settings "
          f"{'on' if auto else 'off'})", t.undo_stack and t.redo_stack and get(t, "_match"),
          (len(t.undo_stack), len(t.redo_stack), len(get(t, "_match"))))
    before = {k: t.v[k] for k in ("tol", "ppo", "fmin", "fmax", "snap", "dashed")}
    t.take(src)
    differ = [k for k in COPIED if not (get(t, k) is get(src, k) or (isinstance(get(t, k), (str, int, float, bool))
                                                                    and get(t, k) == get(src, k)))]
    check(f"Tracer.take: the picture, axes, curves and notes are copied from the result, each value of the list "
          f"(automatic settings {'on' if auto else 'off'})", not differ and t.ta["enabled"] is auto
          and t.ta["jpeg"] is True and len(t.curves) == 2, differ)
    check(f"Tracer.take: undo, redo, the color matches and the values typed or moved start again (automatic settings "
          f"{'on' if auto else 'off'})",
          not t.undo_stack and not t.redo_stack and not get(t, "_match") and not t.ta["manual"]
          and not any(t.typed.values()) and not any(t.moved.values()) and t.label_token == token + 1,
          (len(t.undo_stack), len(t.redo_stack), t.ta["manual"], t.typed, t.moved))
    now = {k: t.v[k] for k in before}
    if auto:
        check("Tracer.take: with the automatic settings on, the settings fit the new picture, and the user's other "
              "selections stay", now["snap"] is False and now["dashed"] is bool(src.ta["dashed_found"])
              and now["tol"] == src.v["tol"]
              and now["ppo"] == 48 and (now["fmin"], now["fmax"]) == (20, 20000), now)
        check("Tracer.take: the curve's points are the same as in the result (automatic settings on)",
              t.points(t.curves[0]["ys"])[0] == src.points(src.curves[0]["ys"])[0])
    else:
        check("Tracer.take: with the automatic settings off, the settings stay as they were", now == before, (now, before))


def _stand_in_words(seen, k, copies, w, h):
    """An ocr_words for test_read_strip: keeps the picture it gets in seen, gives the mark of each copy (columns 10 to
    30, rows 10 to 20 of the part, enlarged k times) and a word across the first two copies."""
    def words(big):
        seen["shape"], seen["big"] = big.shape, big
        step = w * k + max(8, h * k // 2)
        out = [{"text": "40", "x0": 24 + i * step + 10 * k, "y0": 24 + 10 * k, "x1": 24 + i * step + 30 * k,
                "y1": 24 + 20 * k} for i in range(copies)]
        if copies > 1:  # (a word across two copies: left out)
            out.append({"text": "4040", "x0": 24 + 10 * k, "y0": 24 + 10 * k, "x1": 24 + step + 30 * k, "y1": 24 + 20 * k})
        return out
    return words


def test_read_strip(monkeypatch, check):
    """read_strip with a stand-in ocr_words: the part enlarged k times with 24 px of edge, the words back at their
    place in the picture."""
    rgb = np.full((60, 200, 3), 240, np.uint8)
    rgb[20:30, 40:60] = (20, 20, 20)  # (a dark mark in the part: 10 rows, 20 columns)
    x0, y0, x1, y1 = 30, 10, 130, 40  # (the part)
    for k, gray, copies in ((1, False, 1), (4, False, 1), (1, True, 1), (4, True, 1), (4, True, 3)):
        seen = {}
        got = REAL_READ_STRIP(rgb, _stand_in_words(seen, k, copies, x1 - x0, y1 - y0), x0, y0, x1, y1, k, gray, copies)
        h, w = (y1 - y0) * k, (x1 - x0) * k
        width = w + 2 * 24 + (copies - 1) * (w + max(8, h // 2))
        big = seen["big"]
        dark = big[24 + 15 * k, 24 + 20 * k]
        light = big[24 + 2 * k, 24 + 80 * k]
        what = f"k = {k}, {'gray' if gray else 'color'}, {copies} {'copies' if copies > 1 else 'copy'}"
        check(f"read_strip gives the reader the part enlarged k times with 24 px of edge ({what})",
              seen["shape"] == (h + 48, width, 3) and dark.max() < 100 and light.min() > 200
              and (not gray or (big[..., 0] == big[..., 2]).all()), (seen["shape"], dark, light))
        check(f"read_strip gives each word at its place in the picture ({what})",
              len(got) == copies and all(abs(g["x0"] - 40) < 1e-6 and abs(g["x1"] - 60) < 1e-6 and abs(g["y0"] - 20) < 1e-6
                                         and abs(g["y1"] - 30) < 1e-6 for g in got)
              and (copies == 1 or sorted(g["copy"] for g in got) == list(range(copies))), got)


def test_loose_letters(check):
    got = [trace_auto.hz_loose(s) for s in ("1.5k", "4o", "2oHt", "1ok", "Hz", "2e")] + \
        [trace_auto.db_loose(s) for s in ("65", "SS", "oos", "x")]
    check("the letters that the text reader gives for the website's digits are read as digits (a zero with a line "
          "through it, 5, 1), and a strict number stays strict",
          got == [(1500.0, True), (40.0, False), (20.0, False), (10000.0, False), (None, False), (20.0, False), 65.0,
                  55.0, 5.0, None],
          got)


def test_treatments_in_sequence(qapp, monkeypatch, check):
    """read_hz tries the treatments in sequence: a stand-in that gives the words only for the gray part (the second
    treatment) is read."""
    img, truth = website_graph(plot_w=1000)
    rgb = as_rgb(img)
    plot = trace_auto.find_plot(rgb)
    strip = truth_reader(truth)
    tried = []

    def only_gray(rgb_, ocr_words, x0, y0, x1, y1, k, gray, copies=1):
        tried.append((round(k, 2), gray))
        return strip(rgb_, ocr_words, x0, y0, x1, y1, k, gray, copies) if gray else []
    monkeypatch.setattr(trace_auto, "read_strip", only_gray)
    hz = trace_auto.read_hz(rgb, NO_WORDS, plot)
    check("frequency labels that only the gray treatment gives: read at the second treatment (6 times, gray)",
          len(hz["agree"]) >= 4 and tried == [(2.4, False), (3.6, True)], (len(hz["agree"]), tried))


def test_font_missing(qapp, monkeypatch, check):
    class NoFont:
        def __init__(self, _f):
            pass

        def family(self):
            return ""
    monkeypatch.setattr(wg, "QFontInfo", NoFont)
    try:
        website_graph(plot_w=600)
        err = ""
    except RuntimeError as e:
        err = str(e)
    check("the look-alike raises a clear error when Qt does not find its font", "QT_QPA_FONTDIR" in err
          and "Consolas" in err, err)


def test_time(read, check):
    _t, _rgb, r = read(1000)
    check("a 1000 px graph is read in less than 1.5 s without the text reader (the stand-in words)",
          0 < r.seconds < time_limit(1.5), f"{r.seconds:.2f} s")


def test_light_import(check):
    tree = ast.parse(inspect.getsource(trace_core))
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = [a.name for n in top for a in n.names] + [n.module or "" for n in top if isinstance(n, ast.ImportFrom)]
    check("the tracer's core imports the automatic read only at its first use (the app's start stays light)",
          not any("trace_auto" in n for n in names) and "trace_auto" in inspect.getsource(trace_core.auto_read), names)


def test_real_reader(qapp, monkeypatch, check):
    names = ("real text reader, 1000 px PNG: 15 or more frequency labels and 3 or more dB labels agree, all checks pass",
             "real text reader, 1000 px PNG: the read takes less than 2 s",
             "real text reader, labels 10 times too high: the frequency range check fails")
    capabilities.require(capabilities.ocr_ready, check, *names)
    monkeypatch.setattr(trace_auto, "read_strip", REAL_READ_STRIP)
    img, truth = website_graph(plot_w=1000)
    r = trace_core.auto_read(as_rgb(img), ocr.words, False, "Sample IEM")
    hz, db = reason(r, "axes_hz_labels"), reason(r, "axes_db_labels")
    n_hz = int(hz.split()[0]) if hz[:1].isdigit() else 0
    n_db = int(db.split()[0]) if db[:1].isdigit() else 0
    e = errors(r.points, truth["avg"])
    check(names[0], r.ok and n_hz >= 15 and n_db >= 3 and e and e[0] < 0.1, (failed(r), hz, db, e))
    check(names[1], 0 < r.seconds < time_limit(2), f"{r.seconds:.2f} s")
    img, truth = website_graph(plot_w=1000, decade=1)
    r = trace_core.auto_read(as_rgb(img), ocr.words, False, "Sample IEM")
    check(names[2], "axes_hz_range" in failed(r) and "200 Hz to 200 kHz" in reason(r, "axes_hz_range"),
          (failed(r), reason(r, "axes_hz_range")))
