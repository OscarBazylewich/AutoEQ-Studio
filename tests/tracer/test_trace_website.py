"""The tracer's automatic read of a graph from a CrinGraph website (ui\\trace_auto.py, through trace_core.auto_read),
on drawn look-alikes of such a graph (helpers.website_graph: no picture of a real website is kept here): the grid,
the axes, the one curve (the average of the left and right channel), the target line, and the checks with their
reasons; and what trace_core gained for it: Tracer.take (the window takes the result's state), outputs() with a name
and without the target line, and the target mark going when the user changes that curve.

Most tests use the true words of the picture in place of Windows' text reader (helpers.website_graph.truth_reader
stands in for trace_auto.read_strip), so that they do not depend on the reader of this PC; the last two use the real
reader, and skip, with the reason, where Windows has none."""
import ast
import inspect
import math

import numpy as np
import pytest

from helpers import capabilities
from helpers.qt import time_limit
from helpers.website_graph import as_rgb, truth_reader, website_graph
from ui import ocr, trace_auto, trace_core
from ui.trace_core import Tracer

COVERS = ("ui.trace_auto", "ui.trace_core")
REAL_READ_STRIP = trace_auto.read_strip  # (the real one, for the tests with Windows' text reader)
NO_WORDS = lambda rgb: []  # noqa: E731  (an ocr_words that reads nothing: the stand-in gives the words)


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
    once for the file."""
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


def failed(r):
    return [c.name for c in r.checks if not c.ok]


def reason(r, name):
    return next((c.reason for c in r.checks if c.name == name), None)


def test_all_checks_pass(read, check):
    _truth, _rgb, r = read(1000)
    check("website graph 1000 px PNG: all checks pass", r.ok and not failed(r) and len(r.checks) == 10,
          "; ".join(f"{c.name}: {c.reason}" for c in r.checks))
    names = [c.name for c in r.checks]
    check("website graph: the checks come in their sequence, each one an axes_ or trace_ check",
          names == ["axes_plot", "axes_grid", "axes_hz_labels", "axes_hz_range", "axes_db_labels", "axes_db_range",
                    "trace_curve", "trace_gaps", "trace_band", "trace_single"], names)
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


@pytest.mark.parametrize("w", [600, 1000, 1400])
def test_curve_is_the_true_average(read, check, w):
    for jpeg in (None, 60):
        truth, _rgb, r = read(w, jpeg)
        e = errors(r.points, truth["avg"])
        check(f"website graph 600, 1000 and 1400 px, PNG and JPEG: the average curve is less than 0.1 dB from the true "
              f"average (mean), 0.5 dB at the worst point ({w} px, {'JPEG' if jpeg else 'PNG'})",
              e and e[0] < 0.1 and e[1] < 0.5 and e[2] > 0.97, e)


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
    check(f"website graph with a target: the target curve is less than 0.6 dB from the true target (mean) on 85 % of "
          f"the width ({kind})", e and e[0] < 0.6 and e[2] >= 0.85, e)
    ea = errors(r.points, truth["avg"])
    check(f"website graph with a target: the average curve stays less than 0.1 dB from the true average ({kind})",
          ea and ea[0] < 0.1 and ea[1] < 0.5, ea)


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
    check("no text reader: the label checks give the cause, no error",
          hz.startswith("The app did not read the frequency labels.") and "no text reader for this language" in hz
          and db.startswith("The app did not read the dB labels.") and "no text reader" in db
          and r.curve is not None and not r.ok, (hz, db))
    r2 = trace_core.auto_read(rgb, None, False, "Sample IEM")
    check("no text reader: with no ocr_words, the label checks say that the app did not read the labels",
          reason(r2, "axes_hz_labels") == "The app did not read the frequency labels."
          and reason(r2, "axes_db_labels") == "The app did not read the dB labels." and r2.curve is not None,
          (reason(r2, "axes_hz_labels"), reason(r2, "axes_db_labels")))


def test_channels_apart(read, check):
    _truth, _rgb, r = read(1000, None, offset_db=10)
    check("channels 10 dB apart: the band check fails", failed(r) == ["trace_band"]
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
           "noise 900 x 1600": rng.integers(0, 256, (900, 1600, 3), dtype=np.uint8)}
    for what, rgb in odd.items():
        try:
            fp = trace_auto.find_plot(rgb)
            r = trace_core.auto_read(rgb, NO_WORDS, False, "x")
            err = ""
        except Exception as e:  # noqa: BLE001 - (the error, said)
            fp, r, err = None, None, repr(e)
        check(f"find_plot and auto_read do not raise for a picture of any size or color ({what})",
              not err and not fp["ok"] and not r.ok and r.checks[0].name == "axes_plot", err or (fp, r.checks))


def test_app_sample_graph(qapp, monkeypatch, check):
    from ui.trace_window import rgb_of, sample_image
    img, _truth = sample_image()
    monkeypatch.setattr(trace_auto, "read_strip", lambda *a: [])
    try:
        r = trace_core.auto_read(rgb_of(img), NO_WORDS, False, "Sample IEM")
        err = ""
    except Exception as e:  # noqa: BLE001 - (the error, said)
        r, err = None, repr(e)
    check("the app's sample graph (two colors): the one-measurement check fails, no error",
          not err and "trace_single" in failed(r), err or failed(r))


def test_outputs(read, check):
    _truth, _rgb, r = read(1000, None, target="solid")
    t = r.tracer
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


def test_traced_again_is_a_measurement(read, check):
    _truth, _rgb, r = read(1000, 60, target="dashed")
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
    t2 = Tracer()
    t2.take(r.tracer)
    t2.remove_curve(0)
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
    t = Tracer()
    img, _truth = website_graph(plot_w=600)
    t.load(as_rgb(img), "x")
    missing = [f"ta.{k}" for k in Tracer().ta if f"ta.{k}" not in every] + \
        [f"v.{k}" for k in Tracer().v if f"v.{k}" not in every] + \
        [k for k in vars(t) if k not in ("ta", "v") and k not in every]
    check("Tracer.take: each value of the tracer is copied, kept or reset", not missing, missing)
    stale = [k for k in every if not (k.startswith("ta.") and k[3:] in t.ta or k.startswith("v.") and k[2:] in t.v
                                       or "." not in k and hasattr(t, k))]
    check("Tracer.take: each name in the groups is a part of the tracer's state", not stale, stale)


@pytest.mark.parametrize("auto", [True, False])
def test_take_values(read, qapp, check, auto):
    _truth, _rgb, r = read(1000, None, target="solid")
    src = r.tracer
    t = Tracer()
    t.ta["enabled"] = auto
    t.load(as_rgb(website_graph(plot_w=600)[0]), "Old picture")
    t.v.update(tol=99, ppo=12, fmin=40, fmax=16000, snap=False, dashed=True)
    t.mark_your_value("tol")
    t.push_undo()
    t.typed["d"] = True
    t.moved["f"] = True
    token = t.label_token
    before = {k: t.v[k] for k in ("tol", "ppo", "fmin", "fmax", "snap", "dashed")}
    t.take(src)
    copied, _kept, _reset = _groups()

    def get(o, key):
        part, _, k = key.rpartition(".")
        return getattr(o, part)[k] if part else getattr(o, k)
    same = [k for k in copied if get(t, k) is not get(src, k) and not (isinstance(get(t, k), (str, int, float, bool))
                                                                       and get(t, k) == get(src, k))]
    check(f"Tracer.take: the picture, axes and curves are copied, the automatic settings stay on or off as they were "
          f"(automatic settings {'on' if auto else 'off'})",
          not same and t.ta["enabled"] is auto and t.W == src.W and len(t.curves) == 2, same)
    check(f"Tracer.take: undo, redo and the values typed or moved start again (automatic settings {'on' if auto else 'off'})",
          not t.undo_stack and not t.redo_stack and not t.ta["manual"] and not any(t.typed.values())
          and not any(t.moved.values()) and t.label_token == token + 1, (len(t.undo_stack), t.ta["manual"], t.typed, t.moved))
    now = {k: t.v[k] for k in before}
    if auto:
        check("Tracer.take: with the automatic settings on, the settings fit the new picture, and the user's other "
              "selections stay", now["snap"] is False and now["dashed"] is False and now["tol"] == src.v["tol"]
              and now["ppo"] == 48 and (now["fmin"], now["fmax"]) == (20, 20000), now)
    else:
        check("Tracer.take: with the automatic settings off, the settings stay as they were", now == before, (now, before))
    check(f"Tracer.take: the curve's points are the same as in the result (automatic settings {'on' if auto else 'off'})",
          not auto or t.points(t.curves[0]["ys"])[0] == src.points(src.curves[0]["ys"])[0])


def test_time(read, check):
    _t, _rgb, r = read(1000)
    check("a 1000 px graph is read in less than 5 s", r.seconds < time_limit(5), f"{r.seconds:.2f} s")


def test_light_import(check):
    tree = ast.parse(inspect.getsource(trace_core))
    top = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    names = [a.name for n in top for a in n.names] + [n.module or "" for n in top if isinstance(n, ast.ImportFrom)]
    check("the tracer's core imports the automatic read only at its first use (the app's start stays light)",
          not any("trace_auto" in n for n in names) and "trace_auto" in inspect.getsource(trace_core.auto_read), names)


def test_real_reader(qapp, monkeypatch, check):
    names = ("real text reader, 1000 px PNG: 15 or more frequency labels and 3 or more dB labels agree, all checks pass",
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
    img, truth = website_graph(plot_w=1000, decade=1)
    r = trace_core.auto_read(as_rgb(img), ocr.words, False, "Sample IEM")
    check(names[1], "axes_hz_range" in failed(r) and "200 Hz to 200 kHz" in reason(r, "axes_hz_range"),
          (failed(r), reason(r, "axes_hz_range")))
