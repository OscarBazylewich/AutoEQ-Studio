"""The tracer's automatic read (ui\\trace_auto.py) of a website graph with the forms of a real screen copy (2026-11-11,
Hangout.Audio, B&K 5128): steep, narrow peaks and dips at 8 to 16 kHz where the left and right curves are apart and
cross, and a curve that goes out of the grid at the bottom before 20 kHz (the website does not draw it past the dB
axis). helpers.website_graph draws these forms (STEEP_END, clip_db, top_logo): no real picture is kept here.

The read with the code before this work (be8b0fe): the real screen copy and its look-alike at 1396 px failed
trace_curve and trace_gaps (a channel cut off by _continued at the steep parts, a dip cut as text, the end where a
channel went out of the grid counted as not traced); at 1675 and 2234 px the look-alike passed with a curve 1.01 and
7.37 dB off. Each read here uses the true words of the picture (helpers.website_graph.truth_reader) in place of
Windows' text reader."""
import math

import numpy as np

from helpers.website_graph import STEEP_END, as_rgb, truth_reader, website_graph
from ui import trace_auto, trace_core

REAL = ("#002b83", "#0048b4")  # (the colors of the left and right curve of the real screen copy)
NO_WORDS = lambda rgb: []  # noqa: E731  (the stand-in gives the words)
CREAM = (255, 247, 234)
BLUE = (0, 72, 180)
OUT_TOP = (lambda f: 120 - STEEP_END[0](f), lambda f: 120 - STEEP_END[1](f))  # (upside down: out at the top)


def _bass_out(fn):
    return lambda f: fn(f) - 40 / (1 + (f / 35) ** 2)  # (a bass roll-off: under 40 dB below about 26 Hz)


def read(monkeypatch, w=1396, jpeg=None, crop=(0, 0), **kw):
    """(truth, AutoRead) of the look-alike with the real forms (kw: more website_graph options, or in place of
    them); crop: the columns cut off the picture at the left and at the right."""
    kw = dict(dict(chan_fns=STEEP_END, clip_db=True, top_logo=True, colours=REAL), **kw)
    img, truth = website_graph(plot_w=w, **kw)
    rgb = as_rgb(img, jpeg)
    left, right = crop
    words = truth["words"]
    if left or right:
        rgb = np.ascontiguousarray(rgb[:, left:rgb.shape[1] - right])
        words = [dict(q, x0=q["x0"] - left, x1=q["x1"] - left) for q in words]
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(dict(truth, words=words)))
    return truth, trace_core.auto_read(rgb, NO_WORDS, bool(jpeg), "Sample IEM")


def errors(truth, r):
    """(mean, largest) difference in dB of the points from the true average, or None (no points)."""
    e = [abs(v - truth["avg"](f)) for f, v in r.points or [] if 20 <= f <= 20000]
    return (float(np.mean(e)), float(np.max(e))) if e else None


def failed(r):
    return [c.name for c in r.checks if not c.ok]


def reason(r, name):
    return next((c.reason for c in r.checks if c.name == name), "")


# ---------------------------------------------------------------- the look-alike of the real screen copy
def test_real_form_is_read(qapp, monkeypatch, check):
    truth, r = read(monkeypatch)
    e = errors(truth, r)
    check("the look-alike of the real screen copy (1396 px, PNG): all checks pass (before: trace_curve and trace_gaps "
          "failed)", r.ok and not failed(r), [(c.name, c.reason) for c in r.checks if not c.ok])
    check("the look-alike of the real screen copy: the curve is less than 0.05 dB from the true average (mean), and "
          "less than 0.5 dB at the worst point (measured: 0.014 and 0.42 dB)", e and e[0] < 0.05 and e[1] < 0.5, e)
    check("the look-alike of the real screen copy: the points go from 20 Hz to between 17 and 18.6 kHz (the right "
          "curve goes out of the grid at 18.6 kHz)", r.points and r.points[0][0] < 21.5
          and 17000 < r.points[-1][0] < 18600, (r.points[0], r.points[-1]) if r.points else None)
    words = reason(r, "trace_curve")
    check("the look-alike of the real screen copy: the curve check says where a curve goes out of the grid, and to "
          "where the app traced the curve", "the left or right curve goes below the bottom of the grid. The app "
          "traced the curve to " in words and words.startswith("The curve is on 9"), words)
    check("the look-alike of the real screen copy: the gaps check passes with its usual words",
          reason(r, "trace_gaps") == "All of the curve is traced.", reason(r, "trace_gaps"))


def test_screen_scales(qapp, monkeypatch, check):
    """The real screen copy at a screen scale of 100, 150 and 200 % (125 %: test_real_form_is_read)."""
    for w in (1117, 1675, 2234):
        truth, r = read(monkeypatch, w)
        e = errors(truth, r)
        check(f"the look-alike of the real screen copy at {w} px (PNG): all checks pass, and the curve is less than "
              f"0.5 dB from the true average at each point (before: 1117 px failed, 1675 and 2234 px passed with "
              f"1.01 and 7.37 dB)", r.ok and e and e[1] < 0.5, (failed(r), e))


def test_jpeg(qapp, monkeypatch, check):
    for w in (1117, 1396, 1675, 2234):
        truth, r = read(monkeypatch, w, 85)
        e = errors(truth, r)
        check(f"the look-alike of the real screen copy as a JPEG 85 ({w} px): the read fails, or the curve is less "
              f"than 0.5 dB from the true average at each point", not r.ok or (e and e[1] < 0.5), (failed(r), e))


def test_jpeg_known_limit(qapp, monkeypatch, check):
    """A low JPEG quality breaks the lines where the steep right curve crosses the dip of the left curve at 15 kHz: a
    known limit of trace_auto (its docstring has the numbers). The error must not become larger."""
    for w, jpeg, worst in ((1396, 60, 0.65), (1396, 30, 1.11), (2234, 60, 0.77), (2234, 30, 0.70)):
        truth, r = read(monkeypatch, w, jpeg)
        e = errors(truth, r)
        check(f"the look-alike of the real screen copy as a JPEG {jpeg} ({w} px): the read fails, or the curve is "
              f"{worst} dB or less from the true average (the known limit, to 0.01 dB)",
              not r.ok or (e and round(e[1], 2) <= worst), (failed(r), e))


# ---------------------------------------------------------------- more forms of real screen copies
def test_out_at_the_top(qapp, monkeypatch, check):
    for w in (1000, 1396):
        truth, r = read(monkeypatch, w, chan_fns=OUT_TOP)
        e = errors(truth, r)
        check(f"the curves upside down (a curve goes out of the grid at the top before 20 kHz, {w} px): all checks "
              f"pass, the curve is less than 0.5 dB from the true average at each point, and the curve check says "
              f"so", r.ok and e and e[1] < 0.5 and "goes above the top of the grid" in reason(r, "trace_curve"),
              (failed(r), e, reason(r, "trace_curve")))


def test_out_in_the_bass(qapp, monkeypatch, check):
    fns = (_bass_out(STEEP_END[0]), _bass_out(STEEP_END[1]))
    for w, jpeg in ((1000, None), (1396, None), (2234, 85)):
        truth, r = read(monkeypatch, w, jpeg, chan_fns=fns)
        e = errors(truth, r)
        words = reason(r, "trace_curve")
        check(f"a bass roll-off under the grid below 26 Hz ({w} px, {'JPEG ' + str(jpeg) if jpeg else 'PNG'}): all "
              f"checks pass, the curve is less than 0.5 dB from the true average at each point and starts at 25 to 28 "
              f"Hz, and the curve check says from where it traced the curve",
              r.ok and e and e[1] < 0.5 and 25 < r.points[0][0] < 28 and words.startswith("The curve is on 9")
              and "From 20 Hz to " in words and "the left or right curve is below the bottom of the grid. The app "
              "traced the curve from " in words, (failed(r), e, r.points[0] if r.points else None, words))


def test_dip_out_of_the_grid(qapp, monkeypatch, check):
    """A deep dip under the grid at 1 kHz (the curve goes out and comes back): no value there is correct, and the
    points would join the two sides with a straight line, so the gaps check fails with that reason."""
    dip = lambda fn: lambda f: fn(f) - 30 * math.exp(-math.log2(f / 1000) ** 2 / 0.02)  # noqa: E731
    for w in (1000, 1396):
        _truth, r = read(monkeypatch, w, chan_fns=(dip(STEEP_END[0]), dip(STEEP_END[1])))
        words = reason(r, "trace_gaps")
        check(f"a dip under the grid at 1 kHz ({w} px): the gaps check fails, and says between which frequencies the "
              f"curve goes out of the grid", not r.ok and "trace_gaps" in failed(r) and words.startswith("Between ")
              and words.endswith("the left or right curve goes below the bottom of the grid. The app cannot trace "
                                 "that part."), (failed(r), words))


def test_dip_that_touches_the_edge(qapp, monkeypatch, check):
    """A dip that touches the grid's edge and comes back (the usual look-alike, a dB axis of 50 to 90 dB, the right
    channel 3 dB higher: its 10.5 kHz dip goes 0.5 dB under the bottom dB grid line) is not a steep line that goes out
    (steep_exit left out 41 columns there, and the read failed)."""
    truth, r = read(monkeypatch, 1000, chan_fns=None, clip_db=False, top_logo=False, colours=("#1a48a0", "#0d357d"),
                    db_range=(50, 90), offset_db=3)
    e = errors(truth, r)
    check("a dip that touches the bottom edge and comes back (1000 px): all checks pass, the curve less than 0.5 dB "
          "from the true average at each point", r.ok and e and e[1] < 0.5, (failed(r), e))


def test_legend_on_the_steep_part(qapp, monkeypatch, check):
    for xy in ((700, 150), (650, 120), (560, 100), (680, 180), (700, 220)):
        truth, r = read(monkeypatch, 1396, legend_xy=xy)
        e = errors(truth, r)
        check(f"the legend on the steep peaks of the real form ({xy}, 1396 px): the read fails, or the curve is less "
              f"than 0.5 dB from the true average at each point", not r.ok or (e and e[1] < 0.5), (failed(r), e))


def test_legend_known_limit(qapp, monkeypatch, check):
    """The legend's words across the crossing of the steep curves at 15 kHz: a part of the band (known limit 2 of
    trace_auto, with these numbers). The error must not become larger."""
    for w, xy, worst in ((1396, (690, 200), 1.87), (1000, (690, 200), 1.57), (1000, (700, 150), 1.43)):
        truth, r = read(monkeypatch, w, legend_xy=xy)
        e = errors(truth, r)
        check(f"the legend across the crossing at 15 kHz ({xy}, {w} px): the read fails, or the curve is {worst} dB "
              f"or less from the true average (the known limit, to 0.01 dB)",
              not r.ok or (e and round(e[1], 2) <= worst),
              (failed(r), e))


def test_cut_screen_copy(qapp, monkeypatch, check):
    for crop in ((5, 5), (20, 0), (0, 25)):
        truth, r = read(monkeypatch, 1396, crop=crop)
        e = errors(truth, r)
        check(f"a screen copy that cuts {crop} columns off at the left and right, not into the grid: all checks pass, "
              f"the curve less than 0.5 dB from the true average", r.ok and e and e[1] < 0.5, (failed(r), e))
    for crop in ((40, 0), (0, 40)):
        _truth, r = read(monkeypatch, 1396, crop=crop)
        check(f"a screen copy that cuts the 20 Hz or the 20 kHz grid line off {crop}: the read fails at the grid",
              not r.ok and "axes_plot" in failed(r), failed(r))


# ---------------------------------------------------------------- the rules, on drawn bands and arrays
def _band(rgb):
    return trace_auto.band(rgb, {"x0": 10.0, "x1": 589.0, "y0": 10, "y1": 290}, CREAM, BLUE)


def test_steep_line_not_cut(check):
    """_continued with edge_slope: a level line, and a second line that falls 12 rows for each column from it, are
    both kept in each column (before: the slope of the level edge cut the steep line off)."""
    rgb = np.full((300, 600, 3), CREAM, np.uint8)
    rgb[100:104, 10:590] = BLUE
    for x in range(10, 590):
        y = 110 + max(0, x - 300) * 12  # (from column 300 the line falls 12 rows for each column)
        if y + 4 < 290:
            rgb[y:y + 4 + (12 if x >= 300 else 0), x] = BLUE
    b = _band(rgb)
    for x in (303, 306, 310):
        y = 110 + (x - 300) * 12
        bot = float(b["full_bot"][x - b["x0"]])
        check(f"a line that falls 12 rows for each column beside a level line: its rows are kept at column {x} (the "
              f"band's bottom edge within 2 rows of {y + 16})", abs(bot - (y + 15.5)) <= 2, bot)


def test_edge_slope(check):
    last = [(10, 50, 60, 50, 60), (11, 50, 63, 50, 66), (12, 50, 66, 50, 72)]
    check("edge_slope: a bottom edge that moves 6 rows for each column, twice: at the next column 78 rows, margin 5",
          trace_auto.edge_slope(last, 4, 13) == (78.0, 5.0), trace_auto.edge_slope(last, 4, 13))
    check("edge_slope: a top edge that does not move: none", trace_auto.edge_slope(last, 3, 13) is None)
    jump = [(10, 50, 60, 50, 60), (11, 50, 61, 50, 61), (12, 50, 75, 50, 75)]
    check("edge_slope: a jump of 14 rows after a move of 1 row (text): none",
          trace_auto.edge_slope(jump, 4, 13) is None)
    check("edge_slope: columns that are not side by side: none",
          trace_auto.edge_slope([(10, 0, 0, 0, 60), (11, 0, 0, 0, 66), (13, 0, 0, 0, 72)], 4, 14) is None)


def test_comes_in(check):
    check("comes_in: a track from the bottom edge row that moves up 15 rows for each column: a line",
          trace_auto.comes_in([(0, 560, 569), (1, 530, 569), (2, 500, 569)], (18.0, 569.0)))
    check("comes_in: a level track on the bottom edge row (a grid line in the curve's color): not a line",
          not trace_auto.comes_in([(0, 566, 569), (1, 566, 569), (2, 566, 569)], (18.0, 569.0)))
    check("comes_in: a track that moves up, 40 rows from the edge: not a line",
          not trace_auto.comes_in([(0, 500, 529), (1, 470, 529), (2, 440, 529)], (18.0, 569.0)))
    check("comes_in: 2 columns only: not yet", not trace_auto.comes_in([(0, 560, 569), (1, 530, 569)], (18.0, 569.0)))


def test_dip_beside_a_steep_line(check):
    """flat_beside_steep with band()'s lines: a channel's dip (a line of its own, one line width high, its edge bent
    smoothly) beside a steep channel is not text; a level edge of text (high, its edge jumps at the word's end) is."""
    n, lw = 60, 3.0
    x = np.arange(n, dtype=float)
    steep = 100 + 10 * x  # (the top edge: a channel that falls 10 rows for each column)
    dip = 400 + 0.05 * (x - 30) ** 2  # (the bottom edge: the other channel's dip)
    runs, first = np.full(n, 2), steep + 30
    c2 = dip - 1.5  # (a line 3 rows high)
    got = trace_auto.flat_beside_steep(steep, dip, lw, (runs, first, steep + 15, c2))
    check("a dip of one channel beside a steep channel: no column", not got.any(), np.flatnonzero(got))
    check("the same with no lines given (as before): the columns of the dip",
          trace_auto.flat_beside_steep(steep, dip, lw).any())
    text = dip.copy()
    text[26:34] = text[30]
    text[34:] = text[34:] + 12  # (the end of a word: the edge jumps back to the curve)
    got = trace_auto.flat_beside_steep(steep, text, lw, (runs, first, steep + 15, text - 6))
    check("a level edge of text 12 rows high beside a steep channel: its columns", got[27:33].all(),
          np.flatnonzero(got))


def test_lines_that_meet(check):
    """height_steps with meet(): a line that comes down 8 rows for each column to a level line (two lines 8 to 24 rows
    apart in the 3 columns before) and then one line there is not a channel that is lost."""
    n, lw = 40, 1.6
    c2 = np.full(n, 100.0)
    c1 = np.where(np.arange(n) < 20, 100 - 8.0 * (20 - np.arange(n)), 100.0)
    runs = np.where(np.arange(n) < 20, 2, 1)
    b = {"top": c1 - 1.5, "bot": c2 + 1.5, "runs": runs, "c1": c1, "c2": c2, "lw": lw, "x0": 0}
    check("meet(): both lines, moved by their slopes, are in the rows of the one line: met", trace_auto.meet(b, 20, 20))
    check("height_steps: two lines that met: no step", not trace_auto.height_steps(b), trace_auto.height_steps(b))
    c1b = np.where(np.arange(n) < 20, 92 - 1.0 * (20 - np.arange(n)), 100.0)  # (8 rows over it, level: not coming)
    b2 = dict(b, c1=c1b, top=c1b - 1.5)
    check("meet(): an upper line 8 rows away that does not come down: not met", not trace_auto.meet(b2, 20, 20))
    kinds = [s[1] for s in trace_auto.height_steps(b2)]
    check("height_steps: the upper line lost there: a step", kinds and set(kinds) == {"line"},
          trace_auto.height_steps(b2))


def test_average_rows(check):
    """average_rows: the middle of the two lines where one is steep; a straight line across a short crossing."""
    n, lw = 30, 3.0
    top, bot = np.full(n, 100.0), np.full(n, 200.0)
    c1, c2 = np.full(n, 110.0), np.full(n, 196.0)
    runs, steep = np.full(n, 2), np.ones(n, bool)
    got = trace_auto.average_rows(top, bot, runs, c1, c2, lw, steep)
    check("two lines, one steep: the middle of the lines (153), not of the band's edges (150)",
          np.allclose(got, 153.0), got[:3])
    got = trace_auto.average_rows(top, bot, runs, c1, c2, lw, np.zeros(n, bool))
    check("two level lines: the middle of the band's edges (150), as before", np.allclose(got, 150.0), got[:3])
    x = np.arange(n, dtype=float)
    c1, c2 = 100 + 10 * x, 300 - 2 * x  # (two lines that cross at a steep part)
    top, bot = np.minimum(c1, c2) - 1.5, np.maximum(c1, c2) + 1.5
    runs = np.where(np.abs(c1 - c2) < 20, 1, 2)
    c1m, c2m = np.where(runs >= 2, np.minimum(c1, c2), np.nan), np.where(runs >= 2, np.maximum(c1, c2), np.nan)
    got = trace_auto.average_rows(top, bot, runs, c1m, c2m, lw, np.ones(n, bool))
    one = np.flatnonzero(runs == 1)
    check("two lines that cross (one line for 3 columns): those columns on the straight line of the true middle",
          np.allclose(got[one], ((c1 + c2) / 2)[one]), (got[one], ((c1 + c2) / 2)[one]))
    got = trace_auto.average_rows(top, bot, runs, c1m, c2m, lw, np.ones(n, bool))
    runs2 = runs.copy()
    runs2[one[-1] + 1:] = 0
    top2 = top.copy()
    top2[one[-1] + 1:] = np.nan
    got = trace_auto.average_rows(top2, bot, runs2, c1m, c2m, lw, np.ones(n, bool))
    check("the same with no band after the crossing: no value in those columns", np.isnan(got[one]).all(), got[one])


def test_out_parts(check):
    inside = np.ones(100, bool)
    inside[90:] = False
    touch = np.zeros(100)
    touch[93] = 1
    ends, middle = trace_auto.out_parts(inside, touch)
    check("out_parts: the end after a column that touches the bottom edge: out (the columns 90 to 99)",
          ends == [(90, 100, 1, 93, 93)] and middle == [], (ends, middle))
    ends, middle = trace_auto.out_parts(inside, np.zeros(100))
    check("out_parts: an end with no column at an edge (a faded end): not out", ends == [] and middle == [])
    inside = np.ones(100, bool)
    inside[40:50] = False
    touch = np.zeros(100)
    touch[44] = -1
    ends, middle = trace_auto.out_parts(inside, touch)
    check("out_parts: a gap with a column at the top edge: out in the middle", middle == [(40, 50, -1, 44, 44)],
          middle)


def test_steep_exit(check):
    """steep_exit: the columns of a steep line that goes out of the grid at the bottom, and the column at the edge."""
    solid = np.zeros((100, 30), bool)
    solid[20:23, :] = True  # (a level line)
    for x in range(10, 20):  # (a line that falls 10 rows for each column and leaves at row 99)
        solid[30 + (x - 10) * 7:min(100, 45 + (x - 10) * 10), x] = True
    top = np.full(30, 20.0)
    bot = np.where(solid.any(0), [np.flatnonzero(solid[:, x])[-1] + 0.5 for x in range(30)], np.nan)
    got = np.flatnonzero(trace_auto.steep_exit(solid, top, bot, (-0.5, 99.5), 0, 3.0))
    check("steep_exit: the steep line's columns to the edge, and not the level line's columns", len(got) >= 5
          and got.max() <= 19 and got.min() >= 10, got)
    solid2 = np.zeros((100, 30), bool)
    solid2[96:99, :] = True  # (a level line along the edge: it goes out slowly)
    got = trace_auto.steep_exit(solid2, np.full(30, 96.0), np.full(30, 99.0), (-0.5, 99.5), 0, 3.0)
    check("steep_exit: a level line at the edge: no column", not got.any(), np.flatnonzero(got))


def test_grid_edges(check):
    plot = {"hy": [(40.0, 1.0), (60.0, 1.0), (240.0, 1.0)]}
    solid = np.zeros((280, 10), bool)
    solid[100:110] = True
    check("grid_edges: the top and bottom dB grid lines when no curve pixel is past them",
          trace_auto.grid_edges(plot, 10, 290, solid) == (30.0, 230.0), trace_auto.grid_edges(plot, 10, 290, solid))
    solid[235:240, 3] = True  # (a curve 5 rows past the bottom dB grid line: the website draws it there)
    check("grid_edges: the band's last row when a curve goes past the bottom dB grid line",
          trace_auto.grid_edges(plot, 10, 290, solid) == (30.0, 279.0), trace_auto.grid_edges(plot, 10, 290, solid))
    check("grid_edges: with no dB grid lines, the band's first and last row",
          trace_auto.grid_edges({}, 10, 290) == (0.0, 279.0))


def test_line_middles(check):
    """line_middles: the middles of the first and the last line, with the breaks of a JPEG closed, and which columns
    have a steep line (high, moving, and two lines for 3 columns or more)."""
    c = np.zeros((200, 8))
    for x in range(6):
        c[10:13, x] = 1.0  # (a level line)
        c[50 + 10 * x:58 + 10 * x, x] = 1.0
        c[60 + 10 * x:66 + 10 * x, x] = 1.0  # (a line that falls 10 rows a column, broken by a JPEG: 2 pieces)
    m1, m2, count, steep = trace_auto.line_middles(c, 3.0, 0)
    check("line_middles: a level line and a steep line in two pieces: 2 lines, the middles 11 and 57.4 (of rows 50 to "
          "65)", count[0] == 2 and abs(m1[0] - 11) < 0.01 and abs(m2[0] - 803 / 14) < 0.01, (count[0], m1[0], m2[0]))
    check("line_middles: the columns of the steep line that moves, between others: steep", steep[1:5].all(),
          steep[:6])
    check("line_middles: an empty column: no line", count[7] == 0 and np.isnan(m1[7]))
    stem = np.zeros((200, 8))
    stem[10:13, :] = 1.0
    stem[50:70, :] = 1.0  # (a high run that does not move: a letter's stem)
    check("line_middles: a high run that does not move (a letter's stem): not steep",
          not trace_auto.line_middles(stem, 3.0, 0)[3].any())
    word = c.copy()
    word[:, 2:] = 0.0
    word[10:13, 2:] = 1.0  # (two lines in 2 columns only, then one: a piece of a word)
    check("line_middles: two lines in 2 columns only: not steep", not trace_auto.line_middles(word, 3.0, 0)[3].any())
