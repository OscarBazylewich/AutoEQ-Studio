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
    changes the picture before the read. Returns (truth, rgb, AutoRead). (The test asks for the qapp fixture: the
    look-alike draws with Qt.)"""
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
    # (0.79 of the span: where the band hides the target line, at the left end, there are no points, finding A9; and
    # none in the first and last 3 columns of each traced part, trace_auto.target_ends)
    check(f"website graph with a target: the target curve is less than 0.4 dB from the true target (mean), 1 dB at "
          f"the worst point, on 79 % of the width ({kind})", e and e[0] < 0.4 and e[1] < 1 and e[2] >= 0.79, e)
    ea = errors(r.points, truth["avg"])
    check(f"website graph with a target: the average curve stays less than 0.1 dB from the true average ({kind})",
          ea and ea[0] < 0.1 and ea[1] < 0.5, ea)


def test_target_where_the_band_hides_it(qapp, monkeypatch, check):
    cross = lambda f: wg._iem(f) + 3.5 * math.sin(math.log2(f) * 3.1)  # noqa: E731 (crosses the curve many times)
    near = lambda f: (wg._left(f) + wg._right(f)) / 2 - 1.5  # noqa: E731 (1.5 dB under the curve)
    for w, jpeg, kw, what in ((1000, 60, {"target": "dashed", "target_fn": cross}, "a dashed target that crosses the "
                               "curve many times, JPEG 60"),
                              (600, 60, {"target": "dashed"}, "600 px, dashed, JPEG 60"),
                              (1000, None, {"target": "solid"}, "1000 px, solid"),
                              (800, 50, {"target": "solid", "page": True}, "a page, 800 px, solid, JPEG 50"),
                              (800, 50, {"target": "dashed", "page": True}, "a page, 800 px, dashed, JPEG 50"),
                              (600, None, {"target": "dashed", "target_fn": near}, "600 px, dashed, 1.5 dB under the "
                               "curve"),
                              (800, 60, {"target": "solid", "target_fn": lambda f: 62.5}, "a level target at the "
                               "band's edge, 800 px, JPEG 60")):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, **kw)
        e = errors(r.target_points, truth["tgt"], 20, 20000)
        check(f"a target line that the band hides: no target, or the target is less than 1 dB from the true target at "
              f"each point ({what})", r.target is None or (e and e[1] < 1), e)
    # the rule itself: no target point in a column where the band hides the line, or between two parts of the line
    # far apart; a target that crosses the curve many times (a PNG: the target is found)
    seen = []
    real = trace_auto.find_target

    def keep(*a):
        seen.append(real(*a))
        return seen[-1]
    monkeypatch.setattr(trace_auto, "find_target", keep)
    truth, _rgb, r = fresh(monkeypatch, 1000, None, target="dashed", target_fn=cross)
    tg = seen[-1]
    k = r.tracer.calib()
    width = r.tracer.box["x1"] - r.tracer.box["x0"]
    xs = sorted(tg["ys"]) if tg else []
    far = [(a, b) for a, b in zip(xs, xs[1:]) if b - a > max(12, int(0.02 * width))]
    at = {int(round(k.x_at(f))) for f, _v in r.target_points or []}
    check("a target that crosses the curve: it is found, some columns are hidden, and two parts of it are far apart",
          r.target is not None and tg and len(tg["hidden"]) >= 20 and far, (tg and len(tg["hidden"]), far))
    check("a target that crosses the curve: no target point is in a hidden column, and the columns between two parts "
          "far apart are hidden", tg and not (set(xs) & tg["hidden"]) and not (at & tg["hidden"])
          and all(set(range(a + 1, b)) <= tg["hidden"] for a, b in far), (set(xs) & tg["hidden"], at & tg["hidden"]))


def test_target_off_the_line(qapp, monkeypatch, check):
    """The third review's targets that were wrong with ok=True (SHOULD FIX 1): follow() went from the line onto text
    far from the band (30 dB), or past a part's end (1 to 3 dB). No target, or each point 1.0 dB or less from the
    true target."""
    avg = lambda f: (wg._left(f) + wg._right(f)) / 2  # noqa: E731
    for w, jpeg, kind, fn, what in ((700, 30, "dashed", lambda f: avg(f) - 1, "dashed, 1 dB under the curve, 700 px, "
                                     "JPEG 30: gray text at the top right"),
                                    (500, 50, "solid", lambda f: avg(f) + 1, "solid, 1 dB over the curve, 500 px, JPEG "
                                     "50: one point after a part's end"),
                                    (1200, 30, "dashed", lambda f: avg(f) - 2, "dashed, 2 dB under the curve, 1200 px, "
                                     "JPEG 30"),
                                    (700, 30, "solid", lambda f: 61.0, "solid, level at 61 dB, 700 px, JPEG 30")):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, target=kind, target_fn=fn)
        e = [abs(v - truth["tgt"](f)) for f, v in r.target_points or [] if 20 <= f <= 20000]
        check(f"a target line near the band or near text: no target, or each target point 1.0 dB or less from the "
              f"true target ({what})", r.target is None or (e and max(e) <= 1.0), (r.target is None, e and max(e)))
    ys = {x: 50.0 for x in list(range(100, 160)) + list(range(200, 205)) + list(range(400, 470))}
    check("target_ends: the first and last 3 columns of each part (parts apart by more than 1 % of 1000 columns)",
          trace_auto.target_ends(ys, 1000) == [100, 101, 102, 157, 158, 159, 200, 201, 202, 203, 204, 400, 401, 402,
                                                467, 468, 469], trace_auto.target_ends(ys, 1000))
    ys = {x: 50.0 for x in list(range(100, 160)) + list(range(300, 319)) + list(range(500, 520))}
    check("target_ends: all the columns of a part shorter than 2 % of 1000 columns (19 columns), the ends of a part of "
          "20 columns", trace_auto.target_ends(ys, 1000) == [100, 101, 102, 157, 158, 159] + list(range(300, 319))
          + [500, 501, 502, 517, 518, 519], trace_auto.target_ends(ys, 1000))
    ys = {x: 50.0 for x in list(range(100, 160)) + list(range(300, 311))}
    check("target_ends: all the columns of a part shorter than 4 times the ends (12 columns) of 500 columns (11 "
          "columns)", trace_auto.target_ends(ys, 500) == [100, 101, 102, 157, 158, 159] + list(range(300, 311)),
          trace_auto.target_ends(ys, 500))
    # (a dashed part: 3 dashes of 4 columns, 10 columns apart, 30 columns from end to end and 12 points)
    ys = {x: 50.0 for x in list(range(100, 160)) + [300, 301, 302, 303, 313, 314, 315, 316, 326, 327, 328, 329]}
    check("target_ends: a dashed part of 30 columns from end to end with 12 points (of 1000 columns) is not short: "
          "its ends only", trace_auto.target_ends(ys, 1000) == [100, 101, 102, 157, 158, 159, 300, 301, 302, 327, 328,
                                                               329], trace_auto.target_ends(ys, 1000))
    ys = {x: 50.0 for x in range(100, 160)}
    check(f"target_ends: the first and last {trace_auto.TARGET_END:g} of 2000 columns (6 columns) of a part",
          trace_auto.target_ends(ys, 2000) == [100, 101, 102, 103, 104, 105, 154, 155, 156, 157, 158, 159],
          trace_auto.target_ends(ys, 2000))


def test_target_near_gray_text(qapp, monkeypatch, check):
    """The fourth review's targets with a dB axis that puts the band near the gray text at the top right (MUST FIX 2):
    a short traced part on the text stayed after target_ends (14.07 dB at 1 point, 6.26 dB at 5 points)."""
    avg = lambda f: (wg._left(f) + wg._right(f)) / 2  # noqa: E731
    for w, jpeg, kind, fn, rng, what in ((700, None, "dashed", lambda f: avg(f) - 1, (32, 72), "dashed, 1 dB under"),
                                         (1000, 30, "solid", lambda f: avg(f) + 1, (33, 73), "solid, 1 dB over")):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, target=kind, target_fn=fn, db_range=rng)
        e = [abs(v - truth["tgt"](f)) for f, v in r.target_points or [] if 20 <= f <= 20000]
        check(f"a target near the band and the gray text: no target, or each target point 1.0 dB or less from the true "
              f"target ({what} the curve, {w} px, JPEG {jpeg}, a dB axis of {rng[0]} to {rng[1]})",
              r.target is None or (e and max(e) <= 1.0), (r.target is None, e and max(e)))


def test_target_known_limit(qapp, monkeypatch, check):
    """A level target line 1 dB over its own name ("Sample Target", in its color): follow() goes onto the words for a
    long part (a known limit of trace_auto, with its number in the docstring). The error must not become larger."""
    truth, _rgb, r = fresh(monkeypatch, 1000, None, target="dashed", target_fn=lambda f: 48.6)
    e = [abs(v - truth["tgt"](f)) for f, v in r.target_points or [] if 20 <= f <= 20000]
    check("a level target 1 dB over its own name (1000 px, PNG): no target, or each target point 1.62 dB or less from "
          "the true target (the known limit, to 0.01 dB)", r.target is None or (e and round(max(e), 2) <= 1.62),
          (r.target is None, e and max(e)))


def test_target_with_two_level_parts(qapp, monkeypatch, check):
    """The fifth review's targets that were wrong with ok=True (MUST FIX 2): a target with two level parts moved the
    fit of the dB rows, and the 60 dB grid line was the target (12.37 dB at 399 points); JPEG marks in the
    background's color beside a grid line were the target (5.62 dB at 53 points)."""
    truth, _rgb, r = fresh(monkeypatch, 1600, 30, target="solid",
                           target_fn=lambda f: 52 + 20 / (1 + math.exp(-40 * math.log2(f / 600))))
    e, c = [abs(v - truth["tgt"](f)) for f, v in r.target_points or [] if 20 <= f <= 20000], _worst(truth, r)
    check("a target with two level parts (52 dB and 72 dB, 1600 px, JPEG 30): no target, or each target point 1.0 dB "
          "or less from the true target", r.target is None or (e and max(e) <= 1.0), (r.target is None, e and max(e)))
    check("a target with two level parts: the curve is 0.5 dB or less from the true average",
          c is not None and c <= 0.5, (r.ok, failed(r), c))
    truth, _rgb, r = fresh(monkeypatch, 1300, 30, target="dashed", target_dash=(8, 4))
    e = [abs(v - truth["tgt"](f)) for f, v in r.target_points or [] if 20 <= f <= 20000]
    check("a target of dashes of 8 units with gaps of 4 (1300 px, JPEG 30): no target, or each target point 1.0 dB or "
          "less from the true target", r.target is None or (e and max(e) <= 1.0), (r.target is None, e and max(e)))


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
          and "The picture can contain more than one measurement" in reason(r, "trace_band"),
          (failed(r), reason(r, "trace_band")))


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
           "two channels": np.zeros((300, 400, 2), np.uint8), "None": None, "a list of words": ["a", "b"]}
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


def test_trace_curve_and_gaps_fail(qapp, monkeypatch, check):
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


def test_grid_check_fails(qapp, monkeypatch, check):
    def edit(rgb, truth):
        y0, y1 = int(truth["plot"]["y0"]) - 2, int(truth["plot"]["y1"]) + 3
        for f in (300, 400, 3000, 4000):
            x = int(round(truth["x"](f)))
            rgb[y0:y1, x - 2:x + 3] = CREAM
    _t, _rgb, r = fresh(monkeypatch, edit=edit)
    check("4 of the 25 frequency grid lines not in the picture: the grid check fails (only 21 of the 25)",
          "axes_grid" in failed(r) and reason(r, "axes_grid") == "The app found only 21 of the 25 frequency grid lines "
          "of a graph from the website.", (failed(r), reason(r, "axes_grid")))

    def moved(rgb, truth):
        y0, y1 = int(truth["plot"]["y0"]) - 2, int(truth["plot"]["y1"]) + 3
        x = int(round(truth["x"](3000)))
        part = rgb[y0:y1, x - 2:x + 3].copy()
        rgb[y0:y1, x - 2:x + 3] = CREAM
        rgb[y0:y1, x + 1:x + 6] = part
    _t, _rgb, r = fresh(monkeypatch, edit=moved)
    check("the grid line of 3 kHz 3 pixels from its place (all 25 lines found, but one is too far): the grid check fails "
          "(only 24 of the 25 in their positions)", "axes_grid" in failed(r) and reason(r, "axes_grid") == "The app found "
          "only 24 of the 25 frequency grid lines of a graph from the website.", (failed(r), reason(r, "axes_grid")))


def test_hz_labels_fail(qapp, monkeypatch, check):
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


def test_db_labels(qapp, monkeypatch, check):
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


def test_db_labels_each_by_itself(qapp, monkeypatch, check):
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


def test_db_range(qapp, monkeypatch, check):
    check("a usual dB axis: its smallest span, its lowest and highest values are constants",
          trace_auto.DB_MIN_SPAN == 15 and (trace_auto.DB_LOWEST, trace_auto.DB_HIGHEST) == (10, 130))
    _t, _rgb, r = fresh(monkeypatch, words=lambda truth: _db(truth, {v: f"{v + 60}" for v in range(40, 81, 5)}))
    check("all dB labels read 60 dB too high (they agree): the dB range check fails, its highest value is not usual",
          reason(r, "axes_db_range") == "The dB axis is 100 dB to 140 dB. This range is not usual for a graph of an IEM "
          "or headphone." and "axes_db_labels" not in failed(r), (reason(r, "axes_db_range"), failed(r)))
    _t, _rgb, r = fresh(monkeypatch, words=lambda truth: _db(truth, {v: f"{120 - v}" for v in range(40, 81, 5)}))
    check("dB labels that rise downwards (a dB axis always falls downwards): they do not agree, the label check fails",
          reason(r, "axes_db_labels") == "The dB labels that the app read do not agree with each other." and not r.ok,
          (reason(r, "axes_db_labels"), failed(r)))
    half = {60: "60", 65: "65", 70: "70", 45: "47.5", 50: "52.5", 75: "77.5"}
    _t, _rgb, r = fresh(monkeypatch, words=lambda truth: _db(truth, half))
    check("3 dB labels at their grid lines and 3 half-way between two grid lines: the 3 do not agree, too many "
          "against", reason(r, "axes_db_labels") == "3 dB labels agree with the grid lines (5 dB between grid lines), "
          "and 3 do not. Too many labels do not agree." and not r.ok, reason(r, "axes_db_labels"))
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


def test_band_check(qapp, monkeypatch, check):
    _t, _rgb, r = fresh(monkeypatch, offset_db=-6.5)
    x = float(reason(r, "trace_band").split()[9])
    check("channels about 7 dB apart (6 to 9): the band check fails and gives the width",
          "trace_band" in failed(r) and 6 < x < 9, reason(r, "trace_band"))
    for off in (5, -5):
        truth, _rgb, r = fresh(monkeypatch, offset_db=off)
        fs = [20 * 1000 ** (i / 999) for i in range(1000)]
        true = float(np.percentile([abs(truth["chans"][0](f) - truth["chans"][1](f)) for f in fs], 90))
        words = reason(r, "trace_band").split()
        x = float(words[9])
        check(f"the band check gives the true difference of the channels within 0.3 dB, the same for the higher one "
              f"left or right (offset {off:+} dB)", abs(x - true) <= 0.3, (x, round(true, 2), reason(r, "trace_band")))


# ---------------------------------------------------------------- the review's cases of the curve
def test_channel_cut_from_the_band(qapp, monkeypatch, check):
    truth, _rgb, r = fresh(monkeypatch, 1000, 60, colours=ORANGE)
    e = errors(r.points, truth["avg"])
    check("orange channels, JPEG 60: the second channel is kept where it breaks from the band, the curve is less than "
          "0.5 dB from the true average at each point", r.ok and e and e[1] < 0.5, (failed(r), e))


def test_channel_out_of_the_grid(qapp, monkeypatch, check):
    for kw in ({"db_range": (50, 90)}, {"db_range": (50, 76), "db_step": 2}):
        truth, _rgb, r = fresh(monkeypatch, **kw)
        e = errors(r.points, truth["avg"])
        check(f"one channel goes below the grid: the read fails, or the curve is less than 0.5 dB from the true average "
              f"({kw})", not r.ok or (e and e[1] < 0.5), (r.ok, failed(r), e))
    # one line near the grid's edge where the other channel would be past the edge (1000 px; and 600 px, JPEG 60); and
    # a channel under the grid's bottom row at 9.8 to 10.8 kHz (the third review: 1.08 dB with ok=True before)
    for w, jpeg, kw in ((600, 60, {"db_range": (46, 76), "db_step": 2, "offset_db": -3}),
                        (1000, None, {"db_range": (40, 70), "offset_db": -3}),
                        (1000, None, {"db_range": (50, 76), "db_step": 2, "offset_db": -3}),
                        (900, None, {"db_range": (48, 72), "db_step": 2})):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, **kw)
        e = errors(r.points, truth["avg"], 20, 20000)
        check(f"a channel past the grid's edge: the read fails, or the curve is less than 0.5 dB from the true average "
              f"({w} px, {kw})", not r.ok or (e and e[1] < 0.5), (r.ok, failed(r), e))


def test_one_line_at_the_grid_edge(check):
    """band()'s edge rule: one line near the columns where the band touches the grid's bottom row is left out only
    when the other channel (as far away as the two lines beside it) would be past the grid's edge."""
    def edge_cut(one_rows):
        rgb = np.full((300, 800, 3), CREAM, np.uint8)
        rgb[278:281, 10:400] = BLUE  # (two lines, the second at the grid's bottom row: 8 rows between the middles)
        rgb[286:289, 10:400] = BLUE
        rgb[one_rows, 400:790] = BLUE  # (then one line)
        return trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290}, CREAM, BLUE)["cut"]["edge"]
    far, near = edge_cut(slice(250, 253)), edge_cut(slice(282, 285))
    check("one line 39 rows from the grid's bottom edge (more than the distance of the two lines and a line width): "
          "not left out", far == 0, far)
    check("one line 7 rows from the grid's bottom edge (under the distance of the two lines and a line width): the "
          "columns near the edge columns (5 % of the width) left out", 35 <= near <= 40, near)


def test_faded_ends(qapp, monkeypatch, check):
    for off in (-3, 3):
        truth, _rgb, r = fresh(monkeypatch, offset_db=off)
        e = errors(r.points, truth["avg"], 20, 20000)
        check(f"channels 3 dB apart: at the faded ends the curve is the average of both, less than 0.5 dB at each "
              f"point ({off:+} dB)", r.ok and e and e[1] < 0.5, (failed(r), e))
    # an axis of 80 dB: the channels 1 to 1.5 dB apart at 20 kHz are 2 line widths apart or less, but 1 dB or more
    truth, _rgb, r = fresh(monkeypatch, db_range=(20, 100), db_step=10, offset_db=3)
    e = errors(r.points, truth["avg"], 20, 20000)
    check("an axis of 20 to 100 dB, channels about 1 dB apart at the right end, one of them faded: the read fails, or "
          "the curve is less than 0.5 dB from the true average", not r.ok or (e and e[1] < 0.5), (r.ok, failed(r), e))


def test_faded_end_rule(check):
    """faded_ends(): the columns at an end of the band that are one line, where the band inside is two lines apart."""
    n = 500  # (the end zone: 3 % of 500, 15 columns)
    top, c1 = np.full(n, 100.0), np.full(n, 101.5)
    runs = np.full(n, 2)
    runs[:10] = 1  # (the first 10 columns: one line, the other channel faded)

    def ends(apart, lw=3.0, px_db=None, split=None):
        c2 = np.where(runs >= 2, c1 + apart, c1)
        r = runs.copy()
        if split is not None:  # (a JPEG splits the one line into two runs `split` rows apart in columns 4 and 5)
            r[4:6], c2[4:6] = 2, c1[4:6] + split
        return list(np.flatnonzero(trace_auto.faded_ends(top, r, c1, c2, lw, px_db)))
    check("two lines 7 rows apart (more than 2 line widths of 3 rows), the first 10 columns one line: those columns",
          ends(7.0) == list(range(10)), ends(7.0))
    check("two lines 5.4 rows apart (under 2 line widths): no column", ends(5.4) == [], ends(5.4))
    check("two lines 7 rows apart with 8 rows for each dB (under 1 dB, but 2 line widths or more): those columns",
          ends(7.0, px_db=8.0) == list(range(10)), ends(7.0, px_db=8.0))
    check("two lines 5 rows apart with 2 rows for each dB (1 dB or more, and 1.5 line widths or more, under 2): those "
          "columns", ends(5.0, px_db=2.0) == list(range(10)), ends(5.0, px_db=2.0))
    check("two lines 4 rows apart with 2 rows for each dB (1 dB or more, but under 1.5 line widths): no column",
          ends(4.0, px_db=2.0) == [], ends(4.0, px_db=2.0))
    check("the one line split into two runs 2 rows apart (under half the distance) in 2 columns: still those columns",
          ends(7.0, split=2.0) == list(range(10)), ends(7.0, split=2.0))
    check("two lines again at column 4 (half the distance or more): the columns before it only",
          ends(7.0, split=4.0) == list(range(4)), ends(7.0, split=4.0))
    # (just inside the end zone, columns 15 to 24, two lines 14 rows apart in each second column only: the median of
    # the distances is 7 rows, but the band there is not two lines)
    r, c2 = runs.copy(), c1 + 14.0
    r[15:25:2] = 1
    c2 = np.where(r >= 2, c2, c1)
    got = list(np.flatnonzero(trace_auto.faded_ends(top, r, c1, c2, 3.0)))
    check("the band just inside the end zone two lines in half of its columns only: no column", got == [], got)


def test_legend_on_the_curve(qapp, monkeypatch, check):
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


def test_legend_known_limit(qapp, monkeypatch, check):
    """The legend's words along a steep part at 700 px (the third review, MUST FIX 2): a known limit of trace_auto
    (its docstring gives the largest error for each size). The error must not become larger than that number."""
    for xy in ((680, 220), (680, 184)):
        truth, _rgb, r = fresh(monkeypatch, 700, legend_xy=xy)
        e = _worst(truth, r)
        check(f"the legend's words along a steep part at 700 px: the read fails, or the curve is 1.56 dB or less from "
              f"the true average (the known limit, to 0.01 dB) ({xy})",
              not r.ok or (e is not None and round(e, 2) <= 1.56), (r.ok, e))


def test_light_colour_known_limit(qapp, monkeypatch, check):
    """A dB grid line next to a curve in a light color near the grid's color gets the curve's color in a JPEG and is
    read as a part of the band (the fifth review, MUST FIX 3): a known limit of trace_auto, with its numbers in the
    docstring. The error must not become larger than the largest of them."""
    truth, _rgb, r = fresh(monkeypatch, 700, 40, colours=("#d9a05b", "#c08a45"), offset_db=1.5)
    e = _worst(truth, r)
    check("a dB grid line next to a light curve (#d9a05b, 700 px, JPEG 40, +1.5 dB): the read fails, or the curve is "
          "2.77 dB or less from the true average (the known limit, to 0.01 dB)",
          not r.ok or (e is not None and round(e, 2) <= 2.77), (r.ok, failed(r), e))


def test_legend_words_at_600_px(qapp, monkeypatch, check):
    """At 600 px a word of the legend is one piece of 2 to 3 % of the grid's width (the second review, M1)."""
    for xy in ((300, 212), (300, 196), (590, 84), (300, 120), (650, 188), (650, 84)):
        truth, _rgb, r = fresh(monkeypatch, 600, legend_xy=xy)
        e = errors(r.points, truth["avg"], 20, 20000)
        check(f"the legend's words near the curve at 600 px: the read fails, or the curve is less than 0.5 dB from the "
              f"true average at each point ({xy})", not r.ok or (e and e[1] < 0.5), (r.ok, failed(r), e))


BLUE = (26, 72, 160)


def _band_of(*pieces):
    """band() of a drawn picture: cream, a blue line in rows 100 to 102 from column 10 to 789, and more blue
    [(rows, columns)] (slices). Returns band's result."""
    rgb = np.full((300, 800, 3), CREAM, np.uint8)
    rgb[100:103, 10:790] = BLUE
    for rs, cs in pieces:
        rgb[rs, cs] = BLUE
    return trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290}, CREAM, BLUE)


def test_near_pieces(check):
    """band() keeps a piece of the band's color near the band only when it has the form of a line, and only where the
    widest piece is one line (the other channel, cut from the band by a JPEG break)."""
    at = lambda b, x: float(b["bot"][x - b["x0"]])  # noqa: E731 (the band's bottom edge at a column)
    b = _band_of((slice(120, 123), slice(300, 361)))
    check("a near line of 61 pixels: a part of the band", abs(at(b, 330) - 122.5) < 0.6, at(b, 330))
    def word(a, b, every):
        """Letters: three level strokes from column a to b, and an upright stroke in each `every` column."""
        return [(slice(120, 128), slice(c, c + 1)) for c in range(a, b, every)] + \
            [(slice(r, r + 2), slice(a, b)) for r in (120, 123, 126)]
    b = _band_of(*word(300, 361, 2))
    check(f"a near 'word' of 61 pixels (one run in half of its columns, under {trace_auto.NEAR_LONG_PX} pixels: "
          f"{trace_auto.NEAR_ONE_RUN[0]:g} or more): not a part of the band", abs(at(b, 331) - 102.5) < 0.6, at(b, 331))
    b = _band_of(*word(300, 401, 6))
    check(f"a near line of text of 101 pixels (one run in a sixth of its columns: {trace_auto.NEAR_ONE_RUN[1]:g} or "
          f"more): not a part of the band", abs(at(b, 332) - 102.5) < 0.6, at(b, 332))
    # (a line in rows 120 to 122; in each even column also rows 124 and 125, in each odd column row 123: one piece)
    b = _band_of(*[(slice(120, 123), slice(300, 401))] + [(slice(124, 126), slice(c, c + 1)) for c in range(300, 401, 2)]
                 + [(slice(123, 124), slice(c, c + 1)) for c in range(301, 401, 2)])
    check("a near line of 101 pixels with two runs in half of its columns (as a JPEG breaks a line): a part of the band",
          abs(at(b, 351) - 123.5) < 0.6, at(b, 351))
    b = _band_of((slice(115, 131), slice(300, 361)))
    check("a near block 16 rows high (more than 4 line widths): not a part of the band", abs(at(b, 330) - 102.5) < 0.6,
          at(b, 330))
    b = _band_of((slice(120, 123), slice(300, 320)))
    check(f"a near line of 20 pixels (under {trace_auto.NEAR_PIECE_PX}: a word of a small picture): not a part of the "
          f"band", abs(at(b, 310) - 102.5) < 0.6, at(b, 310))
    two = [(slice(105, 108), slice(280, 381)), (slice(100, 108), slice(280, 281))]  # (a second line, joined to it)
    b = _band_of(*two, (slice(120, 123), slice(300, 361)))
    check("a near line where the band has its two lines: a second measurement, not a part of the band",
          abs(at(b, 330) - 107.5) < 0.6, at(b, 330))
    # (the band has two lines in 18 of the near line's 61 columns: one line in 70 %, under NEAR_ALONE)
    third = [(slice(105, 108), slice(301, 319)), (slice(100, 108), slice(300, 301))]
    b = _band_of(*third, (slice(120, 123), slice(300, 361)))
    check(f"a near line where the band has two lines in 30 % of its columns (one line in {trace_auto.NEAR_ALONE:g} "
          f"or more of them is necessary): not a part of the band", abs(at(b, 340) - 102.5) < 0.6, at(b, 340))
    b = _band_of((slice(200, 203), slice(300, 361)))
    check("a line of 61 pixels 98 rows from the band (more than 0.15 of the grid's height): not a part of the band",
          abs(at(b, 330) - 102.5) < 0.6, at(b, 330))
    b = _band_of((slice(120, 123), slice(300, 330)))
    check(f"a near line of 30 pixels ({trace_auto.NEAR_PIECE_PX} or more: a channel's piece after a JPEG break): a "
          f"part of the band", abs(at(b, 315) - 122.5) < 0.6, at(b, 315))
    # (a line of 50 pixels with a second run of rows in 14 of its columns, joined to it in its first column: one run
    # in 72 % of its columns; the legend's words had 62 to 81 %, the channels' pieces 83 to 100 %)
    b = _band_of((slice(120, 123), slice(300, 350)), (slice(125, 127), slice(301, 315)),
                 (slice(120, 127), slice(300, 301)))
    check(f"a near piece of 50 pixels with one run in 72 % of its columns (under {trace_auto.NEAR_ONE_RUN[0]:g}): not "
          f"a part of the band", abs(at(b, 340) - 102.5) < 0.6, at(b, 340))


def test_piece_beside_the_widest_piece(check):
    """band() keeps a piece beside the widest piece, in the columns of a wide piece, only when it is near that wide
    piece (the fourth review, MUST FIX 1: a word of the legend far below the curve was a part of the band): the
    median of its distances to the wide pieces in each of its columns, 0.15 of the grid's height or less (the fifth
    review, SHOULD FIX 3: the smallest or the largest distance, the first wide piece only, or half or 2 times that
    height passed the tests)."""
    rgb = np.full((300, 800, 3), CREAM, np.uint8)
    rgb[100:103, 10:490] = BLUE  # (the widest piece)
    rgb[104:107, 500:700] = BLUE  # (a wide piece beside it: 200 of 780 columns)
    rgb[200:206, 520:541] = BLUE  # (a piece of 21 columns 94 rows under the wide piece: a word)
    rgb[108:111, 600:641] = BLUE  # (a piece of 41 columns 2 rows under the wide piece: the other channel)
    rgb[150:153, 720:761] = BLUE  # (a piece of 41 columns where no wide piece is: a faded end cut off by a break)
    b = trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290}, CREAM, BLUE)
    at = lambda x: float(b["bot"][x - b["x0"]])  # noqa: E731
    check("a piece beside the widest piece, 94 rows from the wide piece in its columns (more than 0.15 of the grid's "
          "height): not a part of the band", abs(at(530) - 106.5) < 0.6, at(530))
    check("a piece beside the widest piece, 2 rows from the wide piece in its columns: a part of the band",
          abs(at(620) - 110.5) < 0.6, at(620))
    check("a piece beside the widest piece where no wide piece is: a part of the band", abs(at(740) - 152.5) < 0.6,
          at(740))

    def beside(*pieces):
        """band() of the widest piece (rows 100 to 102, columns 10 to 489), a wide piece beside it (rows 104 to 106,
        columns 500 to 699) and more blue [(rows, columns)] (slices)."""
        rgb = np.full((300, 800, 3), CREAM, np.uint8)
        rgb[100:103, 10:490] = BLUE
        rgb[104:107, 500:700] = BLUE
        for rs, cs in pieces:
            rgb[rs, cs] = BLUE
        return trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290}, CREAM, BLUE)
    near = 0.15 * 280  # (42 rows: 0.15 of the grid's height)
    b = beside((slice(137, 140), slice(600, 641)))
    at = lambda x: float(b["bot"][x - b["x0"]])  # noqa: E731
    check(f"a piece beside the widest piece, 31 rows from the wide piece (between half of {near:g} rows and {near:g}): "
          f"a part of the band", abs(at(620) - 139.5) < 0.6, at(620))
    b = beside((slice(167, 173), slice(650, 671)))
    check(f"a word beside the widest piece, 61 rows from the wide piece (between {near:g} rows and 2 times that): not "
          f"a part of the band", abs(at(660) - 106.5) < 0.6, at(660))
    # (an L: a level stroke 94 rows under the wide piece, columns 520 to 579, and an upright stroke in columns 520 to
    # 524 up to 4 rows from it)
    b = beside((slice(200, 203), slice(520, 580)), (slice(110, 203), slice(520, 525)))
    check("a piece beside the widest piece with 5 columns near the wide piece and 55 columns 94 rows from it (the "
          "median distance): not a part of the band", abs(at(550) - 106.5) < 0.6, at(550))
    # two wide pieces beside the widest piece: one far (rows 30 to 32, columns 300 to 569: the wider one, first in
    # the sequence) and one near (rows 154 to 156, columns 340 to 599); the piece is 2 rows under the near one in 50
    # of its columns, and 126 rows under the far one in 20 of its columns
    rgb = np.full((300, 800, 3), CREAM, np.uint8)
    rgb[150:153, 10:300] = BLUE
    rgb[30:33, 300:570] = BLUE
    rgb[154:157, 340:600] = BLUE
    rgb[158:161, 550:620] = BLUE
    b = trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290}, CREAM, BLUE)
    full = float(b["full_bot"][610 - b["x0"]])  # (before the cuts: lost_channel leaves out these columns)
    check("a piece near one wide piece in most of its columns and far from a second wide piece in a few: a part of "
          "the band", abs(full - 160.5) < 0.6 and b["pieces"] == 4, (full, b["pieces"]))


def test_word_beside_a_kept_piece(check):
    """band(): a piece kept beside the widest piece gives its rows to the distance test too (the fifth review, SHOULD
    FIX 1: two pieces of 18 % of the width, not wide, beside the widest piece, and a word far from each)."""
    rgb = np.full((300, 800, 3), CREAM, np.uint8)
    rgb[100:103, 10:490] = BLUE  # (the widest piece)
    rgb[104:107, 500:640] = BLUE  # (a piece beside it: 140 of 780 columns, 18 %: not wide)
    rgb[108:111, 650:790] = BLUE  # (one more piece of 18 %)
    rgb[200:206, 520:541] = BLUE  # (a word of 21 columns, 94 rows under the first piece)
    rgb[30:36, 700:721] = BLUE  # (a word of 21 columns, 72 rows over the second piece)
    b = trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290}, CREAM, BLUE)
    at = lambda x, k: float(b[k][x - b["x0"]])  # noqa: E731
    check("a word 94 rows under a kept piece of 18 %: not a part of the band (the bottom edge at column 530 is the "
          "piece's own edge)", abs(at(530, "bot") - 106.5) < 0.6, at(530, "bot"))
    check("a word 72 rows over a kept piece of 18 %: not a part of the band (the top edge at column 710 is the piece's "
          "own edge)", abs(at(710, "top") - 107.5) < 0.6, at(710, "top"))
    check("the widest piece and the two pieces of 18 % are kept, the two words are not", b["pieces"] == 3, b["pieces"])


def test_channel_far_from_the_band(qapp, monkeypatch, check):
    """The fifth review's look-alikes (MUST FIX 1): on a dB axis of 30 dB the channels 5.5 dB apart are more than
    0.15 of the grid's height apart, and a JPEG cut the second channel into pieces that band() does not keep. The
    band was the first channel only, with each check passed (3.71 and 3.72 dB at all points). Now trace_single fails
    (band()'s "apart": 0.71 and 0.37, 0.2 or more). And a drawn band: a line far from the band is "apart", a word is
    not."""
    for w, jpeg, colours in ((900, 50, ("#74a9f7", "#5c93e6")), (1300, 30, ("#a4b000", "#7d8700"))):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, colours=colours, offset_db=-5, db_range=(40, 70), db_step=5)
        e = _worst(truth, r)
        check(f"a channel far from the band, cut into pieces: the read fails, or the curve is 0.5 dB or less from the "
              f"true average ({w} px, JPEG {jpeg}, {colours[0]}, -5 dB, a dB axis of 40 to 70 dB)",
              not r.ok or (e is not None and e <= 0.5), (r.ok, failed(r), e))
    b = _band_of((slice(200, 203), slice(300, 600)))
    check("a line of 300 of 780 columns 98 rows from the band: a wide piece, kept, so not apart", b["apart"] == 0,
          b["apart"])
    b = _band_of((slice(200, 203), slice(300, 460)))
    check("a line of 160 of 780 columns 98 rows from the band (not kept): its share of the columns is apart",
          abs(b["apart"] - 160 / 780) < 0.01, b["apart"])
    # (letters: three level strokes from column 300 to 459, and an upright stroke in each second column)
    b = _band_of(*[(slice(200, 208), slice(c, c + 1)) for c in range(300, 460, 2)],
                 *[(slice(r, r + 2), slice(300, 460)) for r in (200, 203, 206)])
    check("a word of 160 columns 98 rows from the band (three runs of rows in half of its columns): not apart",
          b["apart"] == 0, b["apart"])
    rgb = np.full((300, 800, 3), CREAM, np.uint8)
    rgb[100:103, 10:790] = BLUE
    rgb[199:202, 300:460] = BLUE
    b = trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290, "hy": [(200.0, 1.0)]}, CREAM, BLUE)
    check("a line of 160 columns on a dB grid row (row 200: a JPEG gives the grid line next to a light curve the "
          "curve's color): not apart", b["apart"] == 0, b["apart"])


def test_word_far_from_the_curve(qapp, monkeypatch, check):
    """The look-alikes of the fourth review where a JPEG cut the lighter channel into pieces and a word of the legend
    at its usual place (far under the curve) was a part of the band: 10.93 dB at 11 points with ok=True (olive), and
    12.39 dB at 69 points where a different check failed by chance (light blue)."""
    for w, jpeg, colours, off in ((800, 30, ("#a4b000", "#7d8700"), 1.5), (500, 85, ("#74a9f7", "#5c93e6"), 1)):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, colours=colours, offset_db=off)
        e = _worst(truth, r)
        check(f"a word of the legend far under the curve: the curve's points are 1.0 dB or less from the true average, "
              f"and 0.5 dB or less when the read passes ({w} px, JPEG {jpeg}, {colours[0]}, {off:+} dB)",
              e is not None and e <= 1.0 and (not r.ok or e <= 0.5), (r.ok, failed(r), e))


def test_short_part_between_gaps(qapp, monkeypatch, check):
    """short_parts(): a part of the curve of 1 or 2 columns with no curve on its two sides is left out."""
    top = np.full(100, 50.0)
    top[40:50] = np.nan
    top[52:62] = np.nan  # (columns 50 and 51 between two gaps of 10)
    top[80] = np.nan
    check("2 columns between two gaps: those columns; a gap with a long part on each side, and the ends: none",
          list(np.flatnonzero(trace_auto.short_parts(top))) == [50, 51],
          np.flatnonzero(trace_auto.short_parts(top)))
    end = np.full(100, 50.0)
    end[2:12] = np.nan
    check("2 columns at the band's first column, before a gap: those columns (an end is no better than a gap)",
          list(np.flatnonzero(trace_auto.short_parts(end))) == [0, 1], np.flatnonzero(trace_auto.short_parts(end)))
    top[50:53] = 50.0
    check("3 columns between two gaps: none", not trace_auto.short_parts(top).any())
    # through band(): two lines (the second at the grid's bottom row), then one line; the edge rule leaves out the one
    # line near the edge columns, but not columns 416 and 417, where a second line joins it: those 2 columns go too
    rgb = np.full((300, 800, 3), CREAM, np.uint8)
    rgb[278:281, 10:400], rgb[286:289, 10:400], rgb[282:285, 400:790] = BLUE, BLUE, BLUE
    rgb[279:282, 415], rgb[276:279, 416:418], rgb[279:282, 418] = BLUE, BLUE, BLUE
    b = trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290}, CREAM, BLUE)
    kept = [int(x) + b["x0"] for x in np.flatnonzero(np.isfinite(b["top"])) if 400 <= x + b["x0"] < 437]
    check("band(): 2 columns with two lines between columns that the edge rule left out: left out too ('alone')",
          b["cut"]["alone"] == 2 and kept == [], (b["cut"], kept))
    # the look-alike: one channel at the grid's bottom edge, a column between two cut parts (the dip at 10.7 kHz)
    truth, _rgb, r = fresh(monkeypatch, 1000, db_range=(50, 90), offset_db=3)
    e = errors(r.points, truth["avg"], 20, 20000)
    check("channels 3 dB apart, one at the grid's bottom edge (axis 50 to 90 dB): the read fails, or the curve is less "
          "than 0.5 dB from the true average", not r.ok or (e and e[1] < 0.5), (r.ok, failed(r), e))


def test_lost_channel_rule(check):
    """lost_channel(): one line where the band was two lines apart, and not in their middle."""
    n = 500  # (a grid 500 pixels wide)
    one = slice(200, 240)  # (the columns with one line)
    top, c1 = np.full(n, 100.0), np.full(n, 101.5)
    bot, runs, c2 = np.full(n, 123.0), np.full(n, 2), np.full(n, 121.5)
    bot[one], runs[one], c2[one] = 103.0, 1, 101.5
    got = trace_auto.lost_channel(top, bot, runs, c1, c2, 3.0)
    check("two lines 20 rows apart, then the first line only for 40 columns: those 40 columns",
          list(np.flatnonzero(got)) == list(range(200, 240)), np.flatnonzero(got))
    jb, jc1, jc2 = np.full(n, 123.0), c1.copy(), np.full(n, 121.5)
    jc1[one], jc2[one] = 111.5, 111.5
    got = trace_auto.lost_channel(top, jb, runs, jc1, jc2, 3.0)
    check("two lines that join into one high run (a steep part): in the middle and as high as both, no column",
          not got.any(), np.flatnonzero(got))
    nb, nc2 = np.full(n, 106.0), np.full(n, 104.5)
    nb[one], nc2[one] = 103.0, 101.5
    got = trace_auto.lost_channel(top, nb, runs, c1, nc2, 1.0)
    check(f"two lines only 3 rows apart (under {trace_auto.LOST_APART:g} of the width, 4 rows): no column",
          not got.any(), np.flatnonzero(got))
    nb2, nc22 = bot.copy(), c2.copy()
    nb2[240:], nc22[240:] = 108.0, 106.5  # (after the stretch, the two lines only 5 rows apart)
    got = trace_auto.lost_channel(top, nb2, runs, c1, nc22, 3.0)
    check("two lines 20 rows apart, one line for 40 columns, then two lines 5 rows apart (1.5 line widths or more): "
          "those 40 columns only", list(np.flatnonzero(got)) == list(range(200, 240)), np.flatnonzero(got))
    nb3, nc23 = bot.copy(), c2.copy()
    nb3[240:], nc23[240:] = 107.0, 105.5  # (after the stretch, two runs only 4 rows apart: under 1.5 line widths)
    got = trace_auto.lost_channel(top, nb3, runs, c1, nc23, 3.0)
    check("two lines 20 rows apart, one line for 40 columns, then two runs 4 rows apart (under 1.5 line widths: the "
          "edges of one line): from column 200 to the end", list(np.flatnonzero(got)) == list(range(200, n)),
          np.flatnonzero(got)[-3:])
    fb, fr, fc2 = bot.copy(), runs.copy(), c2.copy()
    fb[215], fr[215], fc2[215] = 123.0, 2, 121.5  # (the lost line comes back for one column: a fading line)
    got = trace_auto.lost_channel(top, fb, fr, c1, fc2, 3.0)
    check("the second line back for one column only (a fading line comes and goes): still those 40 columns",
          list(np.flatnonzero(got)) == list(range(200, 240)), np.flatnonzero(got))
    hb, ht = bot.copy(), top.copy()
    ht[one], hb[one] = 92.0, 112.0  # (one run from 92 to 112: not the middle, but as high as both lines)
    got = trace_auto.lost_channel(ht, hb, runs, c1, c2, 3.0)
    check("one run off the middle but as high as two lines with the space between them (text over a line): no column",
          not got.any(), np.flatnonzero(got))
    mt, mb, m1, m2 = top.copy(), bot.copy(), c1.copy(), np.full(n, 121.5)
    mt[one], mb[one], m1[one], m2[one] = 109.0, 114.0, 111.5, 111.5  # (one line in the middle of the two)
    got = trace_auto.lost_channel(mt, mb, runs, m1, m2, 3.0)
    check("one line in the middle of the two lines: no column", not got.any(), np.flatnonzero(got))
    got = trace_auto.lost_channel(top, nb, runs, c1, nc2, 1.0, 2.0)
    check(f"the same with 2 rows for each dB (3 rows: 1.5 dB, {trace_auto.LOST_DB:g} dB or more): those 40 columns",
          list(np.flatnonzero(got)) == list(range(200, 240)), np.flatnonzero(got))
    got = trace_auto.lost_channel(top, nb, runs, c1, nc2, 1.0, 4.0)
    check("the same with 4 rows for each dB (3 rows: under 1 dB): no column", not got.any(), np.flatnonzero(got))
    # (two runs 3 rows apart, 1 row for each dB: LOST_DB, but under 1.5 line widths: the edge of one line)
    eb, ec2 = np.full(n, 106.0), np.full(n, 104.5)
    eb[one], ec2[one] = 103.0, 101.5
    got = trace_auto.lost_channel(top, eb, runs, c1, ec2, 3.0, 1.0)
    check("two runs 3 rows apart (1 dB with 1 row for each dB, but under 1.5 line widths of 3 rows): no column",
          not got.any(), np.flatnonzero(got))
    tb, tc1, tc2 = bot.copy(), c1.copy(), c2.copy()
    tb[one], tc1[one], tc2[one] = 109.0, 104.5, 104.5  # (one line, 9 rows high: a JPEG makes a line thicker)
    got = trace_auto.lost_channel(top, tb, runs, tc1, tc2, 3.0)
    check("the first line only, 3 line widths high (higher than one line, but under one line and half the distance): "
          "those 40 columns", list(np.flatnonzero(got)) == list(range(200, 240)), np.flatnonzero(got))
    ot, ob, o1 = top.copy(), bot.copy(), c1.copy()
    ot[one], ob[one], o1[one] = 102.0, 105.0, 103.5  # (one line 8 rows from the middle: 0.4 of the distance)
    oc2 = c2.copy()
    oc2[one] = 103.5
    got = trace_auto.lost_channel(ot, ob, runs, o1, oc2, 3.0)
    check("one line 0.4 of the distance from the middle of the two lines (0.3 or more): those 40 columns",
          list(np.flatnonzero(got)) == list(range(200, 240)), np.flatnonzero(got))


def _steep(n=300, lost=200):
    """lost_channel's arrays of two steep lines (6 rows for each column, each 22 rows high, their middles 40 rows
    apart) where the first line is lost from column `lost` to the end: (top, bot, runs, c1, c2)."""
    x = np.arange(n, dtype=float)
    top, bot, c1, c2 = 6 * x, 6 * x + 62, 6 * x + 11, 6 * x + 51
    runs = np.full(n, 2)
    top[lost:], c1[lost:], runs[lost:] = 6 * x[lost:] + 40, c2[lost:], 1
    return top, bot, runs, c1, c2


def test_lost_channel_at_a_gap_and_a_junk_run(check):
    """lost_channel() (the third review, MUST FIX 1 and 3): a channel lost after a short gap, after a junk run, and
    two runs of one line that do not end the lost stretch; each way (from the left and from the right)."""
    n = 500
    top, c1 = np.full(n, 100.0), np.full(n, 101.5)
    bot, runs, c2 = np.full(n, 123.0), np.full(n, 2), np.full(n, 121.5)
    bot[200:], runs[200:], c2[200:] = 103.0, 1, 101.5  # (the first line only, from column 200 to the end)
    for a in (top, bot, c1, c2):
        a[195:200] = np.nan  # (no curve in 5 columns: under MAX_GAP of the width, 0.01 x 500)
    runs[195:200] = 0
    got = trace_auto.lost_channel(top, bot, runs, c1, c2, 3.0)
    check("two lines, a gap of 5 columns (under MAX_GAP of the width), then the first line only to the end: those "
          "columns", list(np.flatnonzero(got)) == list(range(200, n)), np.flatnonzero(got)[:5])
    slope = 2 * np.arange(n)  # (the same, the lines 2 rows lower in each next column: the middle at the real column)
    got = trace_auto.lost_channel(top + slope, bot + slope, runs, c1 + slope, c2 + slope, 3.0)
    check("the same on lines that fall 2 rows for each column: those columns", list(np.flatnonzero(got)) ==
          list(range(200, n)), np.flatnonzero(got)[:5])
    for a in (top, bot, c1, c2):
        a[190:200] = np.nan
    runs[190:200] = 0
    got = trace_auto.lost_channel(top, bot, runs, c1, c2, 3.0)
    check("the same with a gap of 10 columns (more than MAX_GAP of the width): no column", not got.any(),
          np.flatnonzero(got)[:5])
    # a junk run in the last column with two lines (a JPEG at a steep part): the middle of the two lines comes from
    # the median of the 3 columns before, not from the last one only
    top, bot, runs, c1, c2 = _steep()
    c2[199], runs[199] = c2[199] + 20, 3
    for way, arrays in (("from the left", (top, bot, runs, c1, c2)),
                        ("from the right", tuple(a[::-1].copy() for a in (top, bot, runs, c1, c2)))):
        got = trace_auto.lost_channel(*arrays, 3.0)
        want = list(range(200, 300)) if way == "from the left" else list(range(0, 100))
        check(f"two steep lines, a junk run under the second one in the last column, then the second line only to the "
              f"end: those columns ({way})", list(np.flatnonzero(got)) == want, np.flatnonzero(got)[:5])
    # the second line split into two runs 15 rows apart by a JPEG (nearer than its height of 22 rows): the lost stretch
    # goes on
    top, bot, runs, c1, c2 = _steep()
    c1[260:263], c2[260:263], runs[260:263] = c2[260:263] - 7, c2[260:263] + 8, 2
    got = trace_auto.lost_channel(top, bot, runs, c1, c2, 3.0)
    check("the one line split into two runs 15 rows apart (nearer than one line's height) for 3 columns: the lost "
          "stretch goes on to the end", list(np.flatnonzero(got)) == list(range(200, 300)), np.flatnonzero(got)[-5:])


def test_lost_channel_parts_and_middle(check):
    """lost_channel(): a short part between long gaps, the distance of LOST_APART from the band's full width, the
    middle from the median of the 3 columns, and two lines again at 0.6 of the distance (the fourth review, SHOULD FIX
    2: each rule with a test)."""
    n = 500
    nan = lambda: np.full(n, np.nan)  # noqa: E731
    top, bot, c1, c2, runs = nan(), nan(), nan(), nan(), np.zeros(n, int)
    p = slice(300, 320)  # (the only part with a curve: 20 columns between long gaps)
    top[p], c1[p], c2[p], bot[p], runs[p] = 100.0, 101.5, 121.5, 123.0, 2
    bot[306:320], c2[306:320], runs[306:320] = 103.0, 101.5, 1
    got = trace_auto.lost_channel(top, bot, runs, c1, c2, 3.0)
    check("a part of 20 columns between long gaps, the first line only from its 7th column: those columns",
          list(np.flatnonzero(got)) == list(range(306, 320)), np.flatnonzero(got))
    # (lines 5 rows apart in a part of 200 columns of a band of 1000: under LOST_APART of 1000 columns, 8 rows, but
    # more than LOST_APART of the part, 1.6 rows)
    n = 1000
    top, bot, c1, c2, runs = nan(), nan(), nan(), nan(), np.zeros(n, int)
    p = slice(400, 600)
    top[p], c1[p], c2[p], bot[p], runs[p] = 100.0, 101.5, 106.5, 108.0, 2
    bot[500:600], c2[500:600], runs[500:600] = 103.0, 101.5, 1
    got = trace_auto.lost_channel(top, bot, runs, c1, c2, 1.0)
    check(f"two lines 5 rows apart in a part of 200 columns of 1000 (under {trace_auto.LOST_APART:g} of the band's "
          f"full width, 8 rows): no column", not got.any(), np.flatnonzero(got)[:5])
    # a junk run over the first line in the middle one of the 3 columns before the lost line (each way): the median
    # of the 3 middles stays the middle of the two lines (the mean moves 6.7 rows towards the line that stays)
    n = 500
    top, c1 = np.full(n, 100.0), np.full(n, 101.5)
    bot, runs, c2 = np.full(n, 123.0), np.full(n, 2), np.full(n, 121.5)
    bot[200:240], runs[200:240], c2[200:240] = 103.0, 1, 101.5
    for x in (198, 241):
        top[x], c1[x], runs[x] = 60.0, 61.5, 3
    got = trace_auto.lost_channel(top, bot, runs, c1, c2, 3.0)
    check("a junk run 40 rows over the first line in the middle one of the 3 columns before (each way): the 40 "
          "columns with one line", list(np.flatnonzero(got)) == list(range(200, 240)), np.flatnonzero(got))
    # two lines again 20 rows apart after a lost stretch of lines 30 rows apart, each 22 rows high: 0.6 of the
    # distance (18 rows) or more ends the stretch, though under one line's height
    x = np.arange(300, dtype=float)
    top, bot, c1, c2, runs = 6 * x, 6 * x + 52, 6 * x + 11, 6 * x + 41, np.full(300, 2)  # (steep lines 30 rows apart)
    top[200:], c1[200:], runs[200:] = c2[200:] - 11, c2[200:], 1  # (the first line lost from column 200)
    c1[260:], top[260:], runs[260:] = c2[260:] - 20, c2[260:] - 31, 2  # (two lines 20 rows apart from column 260)
    got = trace_auto.lost_channel(top, bot, runs, c1, c2, 3.0)
    check("two lines 20 rows apart again after a stretch with one line (0.6 of the distance of 30 rows or more): the "
          "stretch ends there", list(np.flatnonzero(got)) == list(range(200, 260)), np.flatnonzero(got)[-5:])


def _worst(truth, r, lo=20, hi=20000):
    """The largest difference in dB of the curve's points from the true average between lo and hi Hz (None: no
    points there)."""
    e = [abs(v - truth["avg"](f)) for f, v in r.points or [] if lo <= f <= hi]
    return max(e) if e else None


def test_lost_channel_look_alikes(qapp, monkeypatch, check):
    """The look-alikes of the third review where one channel is lost after a gap in the band (MUST FIX 1) or after a
    junk run (MUST FIX 3)."""
    for w, jpeg, kw in ((1600, 30, {"colours": ("#74a9f7", "#5c93e6"), "offset_db": -4}),
                        (900, 85, {"colours": ("#a4b000", "#7d8700"), "offset_db": 4})):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, **kw)
        e = _worst(truth, r)
        check(f"a channel lost after a gap in the band: the read fails, or the curve is 0.5 dB or less from the true "
              f"average ({w} px, JPEG {jpeg}, {kw['colours'][0]}, {kw['offset_db']:+} dB)",
              not r.ok or (e is not None and e <= 0.5), (r.ok, failed(r), e))
    truth, _rgb, r = fresh(monkeypatch, 1600, 30, colours=ORANGE, offset_db=-2)
    e8, e = _worst(truth, r, 8000, 9000), _worst(truth, r)
    # (elsewhere a JPEG of quality 30 moves the curve by up to 0.6 dB at a point: a known limit of trace_auto)
    check("a channel lost for 2 columns after a junk run (1600 px, JPEG 30, orange, -2 dB): the read fails, or the "
          "curve is 0.5 dB or less from the true average from 8 to 9 kHz, and 0.6 dB or less at each point",
          not r.ok or (e8 is not None and e8 <= 0.5 and e <= 0.6), (r.ok, failed(r), e8, e))


def test_lost_channel_and_the_text_cut(qapp, monkeypatch, check):
    """band() looks for a lost channel before and after the text rule's cut (the fourth review, SHOULD FIX 3): each
    of these look-alikes passed with a wrong curve when lost_channel looked at one of the two only."""
    for w, jpeg, colours, off, before in ((1800, 20, ("#00a8c6", "#0087a0"), -3, "1.87 dB at 16 points"),
                                          (1000, 30, ORANGE, -2.5, "2.02 dB at 29 points")):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, colours=colours, offset_db=off)
        e = _worst(truth, r)
        check(f"a channel lost near the columns of the text rule: the read fails ({w} px, JPEG {jpeg}, {colours[0]}, "
              f"{off:+} dB; with one look only: {before})", not r.ok, (r.ok, failed(r), e))


def test_text_beside_a_steep_part(check):
    """flat_beside_steep(): one edge of the band level (text) where the other moves fast (a steep part)."""
    x = np.arange(100, dtype=float)
    top = 50 + 4 * x
    bot = top + 3
    flat = top.copy()
    flat[40:46] = flat[40]
    got = trace_auto.flat_beside_steep(flat, bot, 1.5)
    check("the top edge level for 6 columns where the curve moves 4 rows for each column: those columns, and 3 on each "
          "side", got[41:45].all() and not got[:35].any() and not got[52:].any(), np.flatnonzero(got))
    check("a steep curve with no text: no column", not trace_auto.flat_beside_steep(top, bot, 1.5).any())
    flat_b = bot.copy()
    flat_b[40:46] = flat_b[45]
    got = trace_auto.flat_beside_steep(top, flat_b, 1.5)
    check("the bottom edge level for 6 columns where the curve moves 4 rows for each column (text under the curve): "
          "those columns", got[41:45].all() and not got[:35].any() and not got[52:].any(), np.flatnonzero(got))
    t2 = 50 + 2 * x
    b2 = t2 + 4
    t2[39:42] = t2[40]
    b2[41] += 2.5
    check("a JPEG break: the top edge level for 3 columns and the bottom edge 3.2 rows a column there, on a curve that "
          "moves 2 rows a column (under 2 line widths in 9 columns): no column",
          not trace_auto.flat_beside_steep(t2, b2, 1.5).any(), np.flatnonzero(trace_auto.flat_beside_steep(t2, b2, 1.5)))
    check("a level curve: no column", not trace_auto.flat_beside_steep(np.full(100, 50.0), np.full(100, 53.0), 1.5).any())


def test_one_channel_on_a_stretch(qapp, monkeypatch, check):
    """Channels 3 dB apart and JPEG: the band can lose a channel on a stretch at the steep part near 8 to 10 kHz (the
    second review, M2)."""
    for w, colours, off, jpeg in ((1000, ("#00a8c6", "#0087a0"), 3, 60), (1000, ("#74a9f7", "#5c93e6"), -3, 40),
                                  (1000, ("#e84393", "#c2337a"), 3, 60), (1000, ("#00a8c6", "#0087a0"), 3, 40),
                                  (1400, ORANGE, -3, 40)):
        truth, _rgb, r = fresh(monkeypatch, w, jpeg, colours=colours, offset_db=off)
        e = errors(r.points, truth["avg"], 20, 20000)
        check(f"channels 3 dB apart, JPEG: the read fails, or the curve is less than 0.5 dB from the true average at each "
              f"point ({w} px, {colours[0]}, {off:+} dB, JPEG {jpeg})", not r.ok or (e and e[1] < 0.5),
              (r.ok, failed(r), e))


def test_steps_check(qapp, monkeypatch, check):
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
          failed(r) == ["trace_steps"]
          and reason(r, "trace_steps").startswith("The difference between the left and right curves changes "
                                                  "suddenly at "),
          (failed(r), reason(r, "trace_steps")))


def test_two_measurements(qapp, monkeypatch, check):
    """trace_single has two rules: a second hue on half of the columns or more, and a second line in a strong color."""
    for what, fn, col in (("a red curve on 57 % of the width only (the hue rule; too short for a second line)",
                           lambda f: wg._iem(f) + 5 if f < 1500 else -100, "#c0392b"),
                          ("a violet curve (a second line in a strong color; its hue is near the first one's)",
                           lambda f: wg._iem(f) + 5, "#8e44ad")):
        _truth, _rgb, r = fresh(monkeypatch, one_curve=True, extra=[(fn, col)])
        check(f"a second measurement in another color: the one-measurement check fails ({what})",
              "trace_single" in failed(r) and reason(r, "trace_single").startswith("The picture has more than one "
                                                                                   "measurement."), failed(r))
    # a second measurement in a near color, 3 dB from the first and crossing it, JPEG 60 (the second review, S1): its
    # pieces near the band are not the band's other channel (the band has its two channels there)
    near = lambda f: wg._iem(f) + 3 * math.sin(math.log2(f) * 0.5)  # noqa: E731
    _truth, _rgb, r = fresh(monkeypatch, 1000, 60, extra=[(near, "#5a48c0")])
    check("a second measurement in a near color (#5a48c0) beside the two channels: the one-measurement check fails",
          "trace_single" in failed(r) and not r.ok, failed(r))


def test_orange_curve_is_one_measurement(qapp, monkeypatch, check):
    for jpeg in (None, 90):
        _truth, _rgb, r = fresh(monkeypatch, 1000, jpeg, colours=ORANGE)
        check(f"orange channels: a dB grid line is not a second line, the one-measurement check passes "
              f"({'JPEG 90' if jpeg else 'PNG'})", r.ok and "trace_single" not in failed(r), failed(r))
        # (follow() goes along a dB grid line from a pale pixel of the orange text: on a grid row, not a target)
        check(f"orange channels: a dB grid line is not a target line ({'JPEG 90' if jpeg else 'PNG'})",
              r.target is None and len(r.tracer.curves) == 1, [c["label"] for c in r.tracer.curves])


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


def test_traced_again_is_a_measurement(qapp, monkeypatch, check):
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
    paper, ink = (250, 228, 190), (40, 70, 170)  # (a blue mark on a cream background: a color in each)
    rgb = np.full((60, 200, 3), paper, np.uint8)
    rgb[20:30, 40:60] = ink  # (the mark in the part: 10 rows, 20 columns)
    x0, y0, x1, y1 = 30, 10, 130, 40  # (the part)
    for k, gray, copies in ((1, False, 1), (4, False, 1), (4, False, 3), (1, True, 1), (4, True, 1), (4, True, 3)):
        seen = {}
        got = REAL_READ_STRIP(rgb, _stand_in_words(seen, k, copies, x1 - x0, y1 - y0), x0, y0, x1, y1, k, gray, copies)
        h, w = (y1 - y0) * k, (x1 - x0) * k
        width = w + 2 * 24 + (copies - 1) * (w + max(8, h // 2))
        big = seen["big"].astype(int)
        dark = big[24 + 15 * k, 24 + 20 * k]
        light = big[24 + 2 * k, 24 + 80 * k]
        what = f"k = {k}, {'gray' if gray else 'color'}, {copies} {'copies' if copies > 1 else 'copy'}"
        grays = bool((big[..., 0] == big[..., 1]).all() and (big[..., 1] == big[..., 2]).all())
        if gray:
            look = dark.max() < 60 and light.min() > 230 and grays
        else:
            look = max(abs(dark - ink)) <= 8 and max(abs(light - paper)) <= 8 and not grays \
                and max(abs(big[0, 0] - paper)) <= 8  # (the edge and the space between copies: the background)
        check(f"read_strip gives the reader the part enlarged k times with 24 px of edge: gray gives dark text on white "
              f"(equal red, green and blue), color gives the picture's own colors ({what})",
              seen["shape"] == (h + 48, width, 3) and look, (seen["shape"], dark, light, grays))
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

    class NoApp:
        @staticmethod
        def instance():
            return None
    monkeypatch.setattr(wg, "QGuiApplication", NoApp)
    try:
        website_graph(plot_w=600)
        err = ""
    except RuntimeError as e:
        err = str(e)
    check("the look-alike raises a clear error when there is no Qt application (Qt would stop the process)",
          "QGuiApplication" in err and "qapp" in err, err)


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


# ---- the limits of round 5's rules, each from its two sides
def test_apart_limit(qapp, monkeypatch, check):
    """trace_single fails at an "apart" of 0.2 or more, and passes below (the limit from the two sides)."""
    real = trace_auto.band
    for apart, single in ((0.19, True), (0.21, False)):
        def band(*a, _apart=apart, **k):
            b = real(*a, **k)
            if b is not None:
                b["apart"] = _apart
            return b
        monkeypatch.setattr(trace_auto, "band", band)
        _truth, _rgb, r = fresh(monkeypatch, 1000, None)
        check(f"band()'s apart is {apart}: trace_single {'passes' if single else 'fails'}",
              ("trace_single" not in failed(r)) == single, failed(r))


def test_apart_form_and_grid_row(check):
    """band()'s "apart": a line 6 rows from a dB grid row is apart, a block 30 rows thick is not."""
    rgb = np.full((300, 800, 3), CREAM, np.uint8)
    rgb[100:103, 10:790] = BLUE
    rgb[206:209, 300:460] = BLUE
    b = trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290, "hy": [(200.0, 1.0)]}, CREAM, BLUE)
    check("a line of 160 columns 6 rows under a dB grid row: apart", abs(b["apart"] - 160 / 780) < 0.01, b["apart"])
    b = _band_of((slice(190, 220), slice(300, 460)))
    check("a block of 160 columns that is 30 rows thick (not a line): not apart", b["apart"] == 0, b["apart"])


def test_rows_fitted_again(check):
    """uniform_rows(): a level line near a grid line does not move the rows, and grid lines 0.6 pixels up and down
    stay in the fit."""
    true = [40.0 + 50.0 * i for i in range(5)]
    got = trace_auto.uniform_rows([(r, 100.0) for r in true] + [(146.0, 100.0)])
    check("5 grid lines 50 pixels apart and a level line 6 pixels under the third: the 5 rows, each 0.1 pixels or "
          "less from its grid line", len(got) == 5 and max(abs(g[0] - t) for g, t in zip(got, true)) <= 0.1, got)
    got = trace_auto.uniform_rows([(40.0 + 50.0 * i + (0.6 if i % 2 else -0.6), 100.0) for i in range(9)])
    check("9 grid lines 0.6 pixels up and down in turn: 9 rows, each 0.35 pixels or less from the middle position",
          len(got) == 9 and max(abs(g[0] - (40.0 + 50.0 * i)) for i, g in enumerate(got)) <= 0.35, got)


def test_piece_not_kept_gives_no_rows(check):
    """band(): a word that is not kept beside the widest piece does not give its rows to the distance test."""
    rgb = np.full((300, 800, 3), CREAM, np.uint8)
    rgb[100:103, 10:490] = BLUE  # (the widest piece)
    rgb[104:107, 500:700] = BLUE  # (a wide piece beside it)
    rgb[200:206, 520:580] = BLUE  # (a word of 60 columns, 94 rows under the wide piece: not kept)
    rgb[110:113, 530:570] = BLUE  # (a piece of 40 columns, 4 rows under the wide piece and 87 rows over the word)
    b = trace_auto.band(rgb, {"x0": 10.0, "x1": 789.0, "y0": 10, "y1": 290}, CREAM, BLUE)
    bot = float(b["full_bot"][550 - b["x0"]])
    check("a piece near the wide piece, in the columns of a word that is not kept: a part of the band",
          abs(bot - 112.5) < 0.6 and b["pieces"] == 3, (bot, b["pieces"]))
