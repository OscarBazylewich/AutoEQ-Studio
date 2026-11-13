"""The rules of the automatic read of a target line alone (ui\\trace_auto.py: find_target's alone, second_line,
line_alone, target_ends, db_range_check, the constants ALONE_*, EXIT_CUT, DB_TARGET_LOWEST, ROW_GREY, SECOND_SHARE)
and its known limits, on drawn look-alikes (helpers.website_graph; no picture of a real website is kept here). The true
words of each picture stand in for Windows' text reader (helpers.website_graph.truth_reader). Each test holds a rule
or a measured limit (2026-11-13: the verifier's weak checks S1 and limits S2 of the first build; the final
verification's weak checks SF1, ROW_GREY on a white page SF2, and limits MF3, MF4 and SF4)."""
import math

import numpy as np
import pytest

from helpers.website_graph import as_rgb, target_graph, truth_reader, website_graph
from ui import trace_auto, trace_core

COVERS = ("ui.trace_auto", "ui.trace_core")
NO_WORDS = lambda rgb: []  # noqa: E731  (an ocr_words that reads nothing: the stand-in gives the words)


def read(monkeypatch, w=1000, jpeg=None, look=False, want=None, **kw):
    """(truth, AutoRead) of a look-alike: website_graph(plot_w=w, **kw), or target_graph(w, **kw) with look."""
    img, truth = target_graph(w, **kw) if look else website_graph(plot_w=w, **kw)
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    return truth, trace_core.auto_read(as_rgb(img, jpeg), NO_WORDS, bool(jpeg), "Sample Target",
                                       **({"want": want} if want else {}))


def errors(pts, fn):
    """(largest difference in dB, the count of points more than 0.5 dB off, the count of points) or None."""
    e = [abs(v - fn(f)) for f, v in pts or [] if 20 <= f <= 20000]
    return (max(e), sum(x > 0.5 for x in e), len(e)) if e else None


def failed(r):
    return [(c.name, c.reason) for c in r.checks if not c.ok]


def reason(r, name):
    return next((c.reason for c in r.checks if c.name == name), None)


def harman(lo, hi):
    """A target shape on the dB axis lo to hi (a bass shelf and a peak near 3 kHz), as the verifier's scan."""
    mid, sc = (lo + hi) / 2, (hi - lo) / 40
    return lambda f: (mid - 4 * sc + 6 * sc / (1 + (f / 100) ** 2)
                      + 8 * sc * math.exp(-(math.log2(f / 3000) ** 2) / 1.2))


# ---------------------------------------------------------------- target_ends and db_range_check
def test_target_ends_of_a_line_alone(check):
    width = 1000
    two = {x: 50.0 for x in list(range(0, 400)) + list(range(430, 1000))}
    out = set(trace_auto.target_ends(two, width, trace_auto.ALONE_APART))
    check("target_ends: two parts of a line alone 3 % of the width apart (more than ALONE_APART): the ends next to "
          "the gap have no points", {397, 398, 399, 430, 431, 432} <= out, sorted(out)[:12])
    last = {x: 50.0 for x in list(range(0, 980)) + list(range(992, 1000))}
    out = set(trace_auto.target_ends(last, width, trace_auto.ALONE_APART))
    check("target_ends: a short last piece 1.2 % of the width from the rest (a label after the line's end) has no "
          "points", set(range(992, 1000)) <= out, sorted(out)[-12:])
    first = {x: 50.0 for x in list(range(0, 8)) + list(range(20, 1000))}
    out = set(trace_auto.target_ends(first, width, trace_auto.ALONE_APART))
    check("target_ends: a short first piece 1.2 % of the width from the rest has no points", set(range(0, 8)) <= out,
          sorted(out)[:12])


def test_db_range_of_a_target(check):
    usual = trace_auto.db_range_check(-40, 0, True)
    low = trace_auto.db_range_check(-50, -10, True)
    meas = trace_auto.db_range_check(-20, 20, False)
    check("db_range_check: -40 dB to 0 dB is usual for a target (DB_TARGET_LOWEST -40)",
          usual.ok and usual.reason == "The dB axis is -40 dB to 0 dB.", usual)
    check("db_range_check: -50 dB to -10 dB is not usual for a target, with the words of a target",
          not low.ok and low.reason == "The dB axis is -50 dB to -10 dB. This range is not usual for a graph of a "
          "target.", low)
    check("db_range_check: -20 dB to 20 dB is not usual for a measurement, with the words of a measurement",
          not meas.ok and meas.reason.endswith("This range is not usual for a graph of an IEM or headphone."), meas)


def test_traced_range_words(check):
    # (the final verification's T15: in each test the line reached neither end of the frequency axis, and a sentence
    # only when both ends are not at an end of the axis was not seen)
    words = {k: trace_auto.traced_range_words(pts, 20.0, 20000.0) for k, pts in (
        ("neither end", [(24.1, 10.0), (18486.0, -1.4)]), ("only the low end", [(20.0, 10.0), (18486.0, -1.4)]),
        ("only the high end", [(24.1, 10.0), (19990.0, -1.4)]), ("both ends", [(20.01, 10.0), (19960.0, -1.4)]),
        ("no points", []))}
    check("traced_range_words: 3 Save's sentence gives the first and the last traced frequency when one of them, or "
          "the two, are not at an end of the frequency axis; none when the line reaches the two ends",
          words == {"neither end": "The app traced the target line from 24.1 Hz to 18.5 kHz.",
                    "only the low end": "The app traced the target line from 20 Hz to 18.5 kHz.",
                    "only the high end": "The app traced the target line from 24.1 Hz to 20 kHz.",
                    "both ends": "", "no points": ""}, words)


# ---------------------------------------------------------------- rows_are_grey and second_line (made data)
class _Rows:
    """What rows_are_grey reads of a Tracer: a page of one color (bg) with dB grid lines of 1 row in another color,
    each at its position plus `below` rows (a thin line that the position rounds to the row above it)."""

    def __init__(self, bg, line, below=0):
        self.bg = np.array(bg, float)
        self.px = np.empty((100, 200, 3), np.uint8)
        self.px[:] = bg
        self.rows = [20.0, 40.0, 60.0, 80.0]
        for r in self.rows:
            self.px[int(r) + below, :] = line
        self.H = 100


def grey(bg, line, below=0):
    t = _Rows(bg, line, below)
    return trace_auto.rows_are_grey(t, t.rows, np.arange(3, 197, 2))


WHITE, CREAM = (255, 255, 255), (255, 247, 234)


def test_rows_are_grey(check):
    # (the final verification's T01 to T05: the look-alike's page was always cream, 21 levels between its channels,
    # and its dB grid lines 25 levels or more from it: ROW_GREY and the other limits had no test)
    got = {
        "white page, 6 levels": grey(WHITE, (150, 150, 156)), "white page, 12 levels": grey(WHITE, (150, 150, 162)),
        "white page, 29 levels from it": grey(WHITE, (238, 238, 238)),
        "white page, 20 levels from it": grey(WHITE, (243, 243, 243)),
        "cream page, 17 levels": grey(CREAM, (158, 160, 175)), "cream page, 19 levels": grey(CREAM, (158, 160, 177)),
        "white page, one row below": grey(WHITE, (150, 150, 150), below=1)}
    check("rows_are_grey: on a white page, dB grid lines with 6 levels between their channels are gray (ROW_GREY 8), "
          "with 12 levels they are not", got["white page, 6 levels"] and not got["white page, 12 levels"], got)
    check("rows_are_grey: dB grid lines 29 levels from the page are gray, 20 levels from it are not (25 levels)",
          got["white page, 29 levels from it"] and not got["white page, 20 levels from it"], got)
    check("rows_are_grey: on the cream page (21 levels), dB grid lines with 17 levels are gray, with 19 levels they "
          "are not (the page's levels less 3)", got["cream page, 17 levels"] and not got["cream page, 19 levels"], got)
    check("rows_are_grey: a thin dB grid line one row below its position is found (the pixel farthest from the "
          "page's color, not the middle row)", got["white page, one row below"], got)


def _line(xs, y):
    return {int(x): float(y if not callable(y) else y(x)) for x in xs}


def second(other_ys, lw=2.0):
    best = {"ys": _line(range(1000), 100), "line": _line(range(1000), 100)}
    return trace_auto.second_line(best, [{"ys": other_ys}], lw, {"x0": 0, "x1": 1000})


def test_second_line(check):
    # (the final verification's T06 to T09: SECOND_SHARE, SECOND_TENTHS and the near tolerance had no test)
    got = {"40 % of the points, apart": second(_line([x for x in range(1000) if x % 5 < 2], 300)),
           "20 % of the points, apart": second(_line(range(0, 1000, 5), 300)),
           "8 tenths, apart": second(_line(range(0, 800), 300)),
           "6 tenths, apart": second(_line(range(0, 600), 300)),
           "5 rows off (line width 2)": second(_line(range(1000), 105)),
           "7 rows off (line width 2)": second(_line(range(1000), 107)),
           "40 % near, 60 % apart": second(_line(range(1000), lambda x: 100 if x < 400 else 300)),
           "60 % near, 40 % apart": second(_line(range(1000), lambda x: 100 if x < 600 else 300))}
    check("second_line: a line apart from the best line with 40 % of its points is a second target line, with 20 % "
          "it is not (SECOND_SHARE 0.3)", got["40 % of the points, apart"] and not got["20 % of the points, apart"],
          got)
    check("second_line: a line apart in 8 tenths of the width is a second target line, in 6 tenths it is not "
          "(SECOND_TENTHS 7)", got["8 tenths, apart"] and not got["6 tenths, apart"], got)
    check("second_line: a line 5 rows from the best line (a line width of 2: 2 line widths and 2 rows) is the same "
          "line, 7 rows from it is a second line", not got["5 rows off (line width 2)"]
          and got["7 rows off (line width 2)"], got)
    check("second_line: a line near the best line for 40 % of its points and apart for the others is a second line; "
          "near for 60 % it is not (half of its points)", got["40 % near, 60 % apart"]
          and not got["60 % near, 40 % apart"], got)


# ---------------------------------------------------------------- line_alone (a made line, no picture)
class _Grid:
    """What line_alone reads of a Tracer: the dB grid rows (100 to 500) and the grid's box."""
    h_lines = [{"pos": float(y)} for y in range(100, 501, 50)]
    box = {"x0": 0, "x1": 1000, "y0": 90, "y1": 510}


def alone(ys, line=None, fade=15):
    """line_alone's result for a line with points ys ({column: row}; line: all of the line, ys when None) on a grid
    of 1000 columns, a line width of 2."""
    tg = {"ys": dict(ys), "line": dict(line if line is not None else ys), "fade": fade}
    return trace_auto.line_alone(tg, 2.0, _Grid(), 0, 1000, 1000, lambda c: f"column {c}",
                                 lambda side: "above the top" if side < 0 else "below the bottom", 20.0)


def checks_of(got):
    return {c.name: (c.ok, c.reason) for c in got["checks"]}


def test_line_alone_gaps(check):
    dashed = {x: 300.0 for x in range(1000) if not 400 <= x < 415}
    got = checks_of(alone(dashed))
    check("line_alone: a gap of 15 columns (1.5 % of the width, ALONE_GAP 2 %) counts as line: all of the target "
          "line is traced", got["trace_gaps"] == (True, "All of the target line is traced.")
          and got["trace_curve"][0], got)
    gap = {x: 300.0 for x in range(1000) if not 400 <= x < 425}
    got = checks_of(alone(gap))
    check("line_alone: a gap of 25 columns (2.5 % of the width) fails trace_gaps, with its width",
          got["trace_gaps"] == (False, "A part of the target line that is 25 pixels wide is not traced."), got)


def test_line_alone_ends(check):
    got = checks_of(alone({x: 300.0 for x in range(10, 991)}))
    check("line_alone: the faded ends (10 columns at each end, within the fade and the trim) count as line: the "
          "target line is on 100 % of the width", got["trace_curve"] == (True, "The target line is on 100 % of the "
                                                                          "width of the grid."), got)
    line = {x: 300.0 + max(0, x - 700) for x in range(0, 900)}  # (down to the bottom row, 500, at column 900)
    line.update({x: 500.0 for x in range(895, 905)})
    ys = {x: y for x, y in line.items() if x < 895}
    got = alone(ys, line)
    cut = set(range(895 - 10, 895))
    check("line_alone: the line goes out of the grid at the bottom at column 895: the 10 columns before it "
          "(EXIT_CUT, 1 % of the width) have no points", got["drop"] == cut, sorted(got["drop"]))
    reason = checks_of(got)["trace_curve"]
    check("line_alone: a line out of the grid from 89 % of the width fails trace_curve (MIN_IN_GRID, 90 %), with "
          "the words of the end", not reason[0] and reason[1].startswith("The target line is on only 89 % of the "
                                                                          "width of the grid. At column 895, the "
                                                                          "target line goes below the bottom of the "
                                                                          "grid."), reason)


def test_line_alone_out_of_the_grid_in_the_middle(check):
    line = {x: 300.0 for x in range(1000)}
    line.update({x: 100.0 for x in range(450, 511)})  # (on the top row: the line goes above the grid there)
    ys = {x: y for x, y in line.items() if not 450 <= x < 511}
    got = checks_of(alone(ys, line))
    check("line_alone: a part of the line above the grid in the middle fails trace_gaps, with where",
          got["trace_gaps"] == (False, "Between column 449 and column 511, the target line goes above the top of the "
                                       "grid. The app cannot trace that part."), got)


# ---------------------------------------------------------------- reads of look-alikes
def test_tinted_grey_target(qapp, monkeypatch, check):
    # (ALONE_GREY 25: a gray with a small tint, 16 levels between its channels, is a target line; a website can use
    # such a gray. Gray target lines in JPEGs were 3 to 16 levels, the real picture 8)
    truth, r = read(monkeypatch, 1000, target="solid", curves=False, target_colour="#a09890")
    e = errors(r.points, truth["tgt"])
    check("a target line in a gray with a tint (#a09890, 16 levels): all checks pass, within 0.5 dB",
          r.ok and r.target_only and e and e[0] <= 0.5, (failed(r), e))


def test_no_points_on_a_label(qapp, monkeypatch, check):
    # (find_target alone: no points on a label that the app read, and a line width around it; then target_ends takes
    # the first columns of the part. The line starts at 20 Hz 2 pixels under the label "65")
    _truth, r = read(monkeypatch, 1200, target="solid", curves=False,
                     target_fn=lambda f: 57.5 + 8 / (1 + (f / 100) ** 2))
    t = r.tracer
    nan = np.full(t.W, np.nan)
    lw = trace_auto.line_width(t, trace_auto.target_seeds(t, nan, nan, 2.0)[:40])
    trim = max(3, math.ceil(trace_auto.TARGET_END * (t.box["x1"] - t.box["x0"])))
    label = next(w for w in t.label_words if w["text"] == "65")
    first = int(np.flatnonzero(np.isfinite(r.curve["ys"]))[0]) if r.curve is not None else -1
    check("a target line alone that starts 2 pixels under a dB label: all checks pass, and the first point is after "
          "the label, a line width and the trimmed end of the part", r.ok and r.target_only
          and first >= label["x1"] + lw + trim, (failed(r), first, label["x1"], lw, trim))


def through(rgb, jpeg=None, page_dark=False):
    """The picture with its lightness inverted (a dark page), then through a JPEG of that quality."""
    from PySide6.QtGui import QImage
    if page_dark:
        a = rgb.astype(np.int32)
        rgb = np.clip(a + (255 - a.max(2) - a.min(2))[..., None], 0, 255).astype(np.uint8)
    if jpeg:
        h, w = rgb.shape[:2]
        rgb = np.ascontiguousarray(rgb)
        rgb = as_rgb(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy(), jpeg)
    return rgb


def read_rgb(monkeypatch, w, jpeg=None, page_dark=False, want=None, **kw):
    img, truth = website_graph(plot_w=w, **kw)
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    return truth, trace_core.auto_read(through(as_rgb(img), jpeg, page_dark), NO_WORDS, bool(jpeg), "Sample Target",
                                       **({"want": want} if want else {}))


GREY_ROWS = [("800 px, PNG, rows and line #9e9ea3", 800, None, False, "#9e9ea3", "solid", ("#9e9ea3", 1.0)),
             ("1700 px, JPEG 20, a page, thick rows #808080, dashed #6e6e6e", 1700, 20, False, "#6e6e6e", "dashed",
              ("#808080", 2.5)),
             ("2600 px, JPEG 20, dark, rows #a0a8a0, dashed #808080", 2600, 20, True, "#808080", "dashed",
              ("#a0a8a0", 1.0)),
             ("2600 px, JPEG 85, rows #6e6e6e, a pale line #c8c8c8", 2600, 85, False, "#c8c8c8", "solid",
              ("#6e6e6e", 1.0))]


@pytest.mark.parametrize("form", GREY_ROWS, ids=[f[0] for f in GREY_ROWS])
@pytest.mark.parametrize("over", [True, False], ids=["rows over the line", "rows under the line"])
def test_grey_db_grid_lines_are_not_the_target(qapp, monkeypatch, check, form, over):
    # (2026-11-13, the verifier's M1: with dB grid lines in a gray, a row was the target line, 25.0, 20.1, 10.2 and
    # 5.1 dB off with all checks passed. rows_are_grey: no points on a row; second_line: the rows that follow() took
    # as lines are second lines)
    name, w, jpeg, page_dark, colour, kind, rows = form
    truth, r = read_rgb(monkeypatch, w, jpeg, page_dark, curves=False, target=kind, target_fn=harman(30, 80),
                        db_range=(30, 80), target_colour=colour, grey_rows=rows + (over,), page="page" in name)
    e = errors(r.points, truth["tgt"])
    check(f"gray dB grid lines ({name}, the rows {'over' if over else 'under'} the line): no result with all checks "
          "passed that is more than 0.5 dB off", not r.ok or (e and e[0] <= 0.5), (failed(r)[:2], e))


def test_row_grey_on_a_white_page(qapp, monkeypatch, check):
    # (the final verification's SF2: the look-alike's page was always cream, and there "the page's levels less 3",
    # 18, is more than ROW_GREY: ROW_GREY had no measured effect. On a white page it is the limit. Of 600 forms with
    # dB grid lines of 0 to 20 levels on a white, a gray and the cream page, ROW_GREY 4 gave 8 new results with all
    # checks passed that are more than 0.5 dB off, and 16 lost 17 correct results)
    truth, r = read(monkeypatch, 1000, curves=False, target="dashed", target_colour="#b0b0b0", db_range=(-10, 10),
                    db_step=2, target_fn=lambda f: 0.15, grey_rows=("#707078", 1.0, True), background="#ffffff")
    e = errors(r.points, truth["tgt"])
    check("a white page, dB grid lines #707078 (8 levels) over a level dashed line, 1000 px, PNG: no result with all "
          "checks passed more than 0.5 dB off (with ROW_GREY 4: 8.13 dB at all points)",
          not r.ok or (e and e[0] <= 0.5), (failed(r)[:1], e))
    truth, r = read(monkeypatch, 2234, curves=False, target="solid", target_colour="#9e9ea3", db_range=(30, 80),
                    db_step=5, target_fn=lambda f: 55.375, grey_rows=("#b4b4c0", 1.0, False), background="#ffffff")
    e = errors(r.points, truth["tgt"])
    check("a white page, dB grid lines #b4b4c0 (12 levels: not gray) under a level line on a row, 2234 px, PNG: all "
          "checks pass, within 0.5 dB (with ROW_GREY 16 the line has no points on the row: trace_curve fails)",
          r.ok and r.target_only and e and e[0] <= 0.5, (failed(r)[:1], e))


TINTED = [("dB grid lines #9ea3b0 over a level dashed line, 1000 px, PNG", 15.35,
           dict(plot_w=1000, target="dashed", target_colour="#9ca29a", db_range=(40, 80), db_step=5,
                target_fn=lambda f: 60.3, grey_rows=("#9ea3b0", 2.5, True))),
          ("dB grid lines #9ea3b0 under a dashed line, 1800 px, PNG", 9.94,
           dict(plot_w=1800, target="dashed", target_colour="#9e9ea3", db_range=(-10, 10), db_step=2,
                target_fn=harman(-10, 10), grey_rows=("#9ea3b0", 3.5, False)))]


@pytest.mark.parametrize("form", TINTED, ids=[f[0] for f in TINTED])
def test_limit_grey_db_grid_lines_with_a_tint(qapp, monkeypatch, check, form):
    # (the final verification's MF4, known limit 26: dB grid lines in a blue gray, 18 levels between their channels,
    # are not gray for rows_are_grey on the cream page (21 levels), and a row is the result with all checks passed.
    # A tried rule stopped these and made other results incorrect or lost correct results: not in the code)
    name, worst, kw = form
    img, truth = website_graph(curves=False, **kw)
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    r = trace_core.auto_read(as_rgb(img), NO_WORDS, False, "Sample Target")
    e = errors(r.points, truth["tgt"])
    check(f"{name}: the read fails, or the result is {worst} dB or less from the true target (the known limit, to "
          "0.01 dB)", not r.ok or (e is not None and round(e[0], 2) <= worst), (failed(r)[:1], e))


def tilt(lo, hi):
    mid, sc = (lo + hi) / 2, (hi - lo) / 40
    return lambda f: mid + 6 * sc - sc * math.log2(f / 20)


TWO = [("8 dB above it, solid", "solid", lambda f: harman(-20, 20)(f) + 8),
       ("6 dB under it, dashed", "dashed", lambda f: harman(-20, 20)(f) - 6),
       ("across it, solid", "solid", tilt(-20, 20)), ("level, solid", "solid", lambda f: 0.3)]


@pytest.mark.parametrize("form", TWO, ids=[f[0] for f in TWO])
def test_two_target_lines(qapp, monkeypatch, check, form):
    # (2026-11-13, the verifier's M2: two targets on one graph, one of them was the result, up to 16 dB off with all
    # checks passed. second_line: trace_single fails)
    name, kind, other = form
    _truth, r = read_rgb(monkeypatch, 1396, curves=False, target=kind, target_fn=harman(-20, 20), db_range=(-20, 20),
                         extra=[(other, "#b0b0b0")])
    check(f"two target lines (a second line {name}, 1396 px, PNG): trace_single fails first, with its words",
          not r.ok and failed(r)[:1] == [("trace_single", "The picture has more than one target line. Show only one "
                                                          "target on the graph of the website.")], failed(r))


def test_one_thin_line_is_one_target_line(qapp, monkeypatch, check):
    # (second_line: a second follow() of the same thin line, with other columns, is not a second line)
    img, truth = website_graph(plot_w=1000, page=True, curves=False, target="solid", target_width=0.8,
                               target_colour="#b0b0b0", target_fn=tilt(-15, 15), db_range=(-15, 15), db_step=5)
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    r = trace_core.auto_read(as_rgb(img), NO_WORDS, False, "Sample Target", want="target")
    e = errors(r.points, truth["tgt"])
    check("a thin target line (0.8 units, 1000 px, a page): one target line, all checks pass, within 0.5 dB",
          r.ok and reason(r, "trace_single") == "The picture has one target line." and e and e[0] <= 0.5,
          (failed(r), e))


# ---------------------------------------------------------------- known limits (the module's docstring, items 25 to 30)
def test_limit_dotted_line(qapp, monkeypatch, check):
    # (dots of 1 unit with gaps of 3: of 55 forms of the scan, 54 fail, 1 passes within 0.22 dB)
    truth, r = read(monkeypatch, 1000, target="dashed", target_dash=(1, 3), curves=False, target_fn=harman(-20, 20),
                    db_range=(-20, 20))
    e = errors(r.points, truth["tgt"])
    check("a dotted target line (1000 px, PNG): the read fails, or it is within 0.5 dB",
          not r.ok or (e and e[0] <= 0.5), (failed(r)[:1], e))


def test_limit_text_across_the_line(qapp, monkeypatch, check):
    # (gray text across the target line: 1.02 dB at 6 points with all checks passed, 1000 px, JPEG 85)
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QFont, QPainter
    flat = lambda f: 0.3  # noqa: E731
    img, truth = website_graph(plot_w=1000, curves=False, target="dashed", target_fn=flat, db_range=(-20, 20),
                               target_colour="#9ca29a")
    s = truth["scale"]
    g = QPainter(img)
    g.setRenderHint(QPainter.Antialiasing)
    g.setRenderHint(QPainter.TextAntialiasing)
    font = QFont("Arial")
    font.setPixelSize(max(6, round(10 * s)))
    font.setBold(True)
    g.setFont(font)
    g.setPen(QColor("#808080"))
    g.translate(truth["x"](150) + 0.5, truth["y"](0.3) + 0.5)
    g.rotate(-60)
    g.drawText(QPointF(-40 * s, 4 * s), "Sample Target (Tilt)")
    g.end()
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    r = trace_core.auto_read(as_rgb(img, 85), NO_WORDS, True, "Sample Target", want="target")
    e = errors(r.points, truth["tgt"])
    check("gray text across the target line (1000 px, JPEG 85): no result with all checks passed more than 1.1 dB off",
          not r.ok or (e and e[0] <= 1.1), (failed(r)[:1], e))


def test_limit_text_along_the_line(qapp, monkeypatch, check):
    # (the final verification's SF4, known limit 28: the name of the target and its settings in gray near the line,
    # 700 px, PNG, an entry of a target: 1.66 dB at 14 points with all checks passed, the largest of 60 forms)
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QFont, QPainter
    img, truth = website_graph(plot_w=700, curves=False, target="solid", target_colour="#b0b0b0", db_range=(-40, 40),
                               db_step=10, target_fn=tilt(-40, 40), target_look=True)
    s = truth["scale"]
    g = QPainter(img)
    g.setRenderHint(QPainter.Antialiasing)
    g.setRenderHint(QPainter.TextAntialiasing)
    font = QFont("Arial")
    font.setPixelSize(max(6, round(9 * s)))
    font.setBold(True)
    g.setFont(font)
    g.setPen(QColor("#9e9ea3"))
    g.drawText(QPointF(truth["x"](60) - 60 * s, truth["y"](truth["tgt"](60)) + 6 * s),
               "Sample Target (Tilt: -0.8dB/Oct, Bass: 6dB)")
    g.end()
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    r = trace_core.auto_read(as_rgb(img), NO_WORDS, False, "Sample Target", want="target")
    e = errors(r.points, truth["tgt"])
    check("gray text along the target line at 60 Hz (700 px, PNG): the read fails, or the result is 1.66 dB or less "
          "from the true target (the known limit, to 0.01 dB)", not r.ok or (e and round(e[0], 2) <= 1.66),
          (failed(r)[:1], e))


def test_limit_two_lines_with_one_not_found(qapp, monkeypatch, check):
    # (two target lines where find_target follows only one: of 190 forms of the scan, 24 pass, the result is one of
    # the two lines, 0.57 dB or less from it)
    truth, r = read_rgb(monkeypatch, 1000, 70, curves=False, target="dashed", target_fn=harman(-20, 20),
                        db_range=(-20, 20), target_colour="#c8c8c8", extra=[(tilt(-20, 20), "#9e9ea3")],
                        want="target")
    e, e2 = errors(r.points, truth["tgt"]), errors(r.points, tilt(-20, 20))
    check("two target lines, a pale dashed one and a solid one across it (1000 px, JPEG 70): the read fails, or the "
          "result is one of the two lines", not r.ok or (e and e[0] <= 0.6) or (e2 and e2[0] <= 0.6),
          (failed(r)[:1], e, e2))


SHELF = [("a bass shelf of 8 dB, 1000 px, PNG, solid, the second line #808080", 1000, None, "solid", "#808080",
          lambda f: harman(-20, 20)(f) + 8 / (1 + (f / 120) ** 2)),
         ("a treble shelf of 5 dB, 1396 px, PNG, dashed, the second line #b0b0b0", 1396, None, "dashed", "#b0b0b0",
          lambda f: harman(-20, 20)(f) + 5 / (1 + (6000 / f) ** 3)),
         ("a treble shelf of 5 dB, 1000 px, JPEG 85, solid, the second line #b0b0b0", 1000, 85, "solid", "#b0b0b0",
          lambda f: harman(-20, 20)(f) + 5 / (1 + (6000 / f) ** 3))]


@pytest.mark.parametrize("form", SHELF, ids=[f[0] for f in SHELF])
def test_limit_two_lines_the_same_except_at_one_end(qapp, monkeypatch, check, form):
    # (the final verification's MF3, known limit 25: a second target line that is the same line with a bass or
    # treble shelf. follow() from the second line follows only the part where the two lines are different, and that
    # part is not a second line. Of 75 forms, 49 pass more than 1 dB from the target; the result is one of the two
    # lines, 1.62 dB or less from it. These three: 7.75 and 4.84 dB from the target)
    name, w, jpeg, kind, colour, other = form
    truth, r = read_rgb(monkeypatch, w, jpeg, curves=False, target=kind, target_fn=harman(-20, 20),
                        db_range=(-20, 20), extra=[(other, colour)], want="target")
    e, e2 = errors(r.points, truth["tgt"]), errors(r.points, other)
    check(f"two target lines, the same except at one end ({name}): the read fails, or the result is one of the two "
          "lines, 1.62 dB or less from it (the known limit, to 0.01 dB)",
          not r.ok or (e is not None and round(e[0], 2) <= 1.62) or (e2 is not None and round(e2[0], 2) <= 1.62),
          (failed(r)[:1], e, e2))


def test_limit_grey_measurement(qapp, monkeypatch, check):
    # (a black or gray measurement with no entry: the line alone follows one channel. Of 330 forms, 5 pass as a
    # target, 3 of them 1.26 to 1.29 dB from the average of the channels)
    truth, r = read_rgb(monkeypatch, 1000, 40, page=True, colours=("#000000", "#202020"), db_range=(35, 85))
    e = errors(r.points, truth["avg"])
    check("a black measurement with no entry (1000 px, JPEG 40, a page): no result with all checks passed more than "
          "1.35 dB from the average of the channels", not r.ok or (e and e[0] <= 1.35), (failed(r)[:1], e))
    _truth, r = read_rgb(monkeypatch, 1000, 40, page=True, colours=("#000000", "#202020"), db_range=(35, 85),
                         want="measurement")
    check("the same picture for an entry of a measurement: no target result", not r.ok and not r.target_only,
          failed(r)[:1])


def test_limit_grey_measurement_beside_a_target(qapp, monkeypatch, check):
    # (a gray measurement and a target line, an entry of a target: the two channels are lines in a gray too, and
    # trace_single fails, which is not the true cause; of 120 forms with a measurement and a target, 11 correct results
    # are lost)
    _truth, r = read_rgb(monkeypatch, 1396, curves=True, colours=("#808080", "#808080"), target="solid",
                         target_fn=lambda f: harman(40, 80)(f) - 14, db_range=(40, 80), target_colour="#9ca29a",
                         want="target")
    check("a gray measurement 14 dB above a target line, an entry of a target (1396 px, PNG): trace_single fails",
          not r.ok and failed(r)[:1] and failed(r)[0][0] == "trace_single", failed(r)[:2])


GRAYISH = ((4.3, "#f4f0ea"), (3.0, "#ebe6df"), (1.6, "#e0dbd4"))  # (soft dB bands with little color)
BANDS = [("#c8c8c8, 1000 px, JPEG 70", "#c8c8c8", 1000, 70), ("#b0b0b0, 2000 px, PNG", "#b0b0b0", 2000, None),
         ("#9ca29a, 2000 px, PNG", "#9ca29a", 2000, None), ("#c8c8c8, 2400 px, PNG", "#c8c8c8", 2400, None)]


@pytest.mark.parametrize("form", BANDS, ids=[f[0] for f in BANDS])
def test_soft_grey_db_bands(qapp, monkeypatch, check, form):
    # (find_target alone: a seed less than 25 levels from the dB grid lines' color, hc, is not used, and the color
    # tolerance of follow() is under the distance from hc; hc is the median of all dB grid rows. With soft bands with
    # little color, a seed on a band gave a line on the band: a second line, or 0.55 dB at 2 points)
    name, colour, w, jpeg = form
    truth, r = read(monkeypatch, w, jpeg, look=True, bands=GRAYISH, target_colour=colour)
    e = errors(r.points, truth["tgt"])
    check(f"the look of a target graph with soft gray dB bands (a target line {name}): all checks pass, within 0.5 dB",
          r.ok and r.target_only and e and e[0] <= 0.5, (failed(r)[:2], e))
