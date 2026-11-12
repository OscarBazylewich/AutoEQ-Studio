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
import re

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


def last_column_hz(r):
    """The frequency of the last traced column of the curve in the grid, in the words of the app (fmt_hz)."""
    t = r.tracer
    ys = np.asarray(r.curve["ys"], float)
    lo, hi = math.ceil(t.cal["x1"]), math.floor(t.cal["x2"])
    cols = [x for x in np.flatnonzero(np.isfinite(ys)) if lo <= x <= hi]
    return trace_core.fmt_hz(t.calib().hz_at(cols[-1])) if cols else None


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
    check("the look-alike of the real screen copy: the frequency in \"traced the curve to\" is the frequency of the "
          "last traced column", words.endswith(f"The app traced the curve to {last_column_hz(r)}."),
          (words, last_column_hz(r)))
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
        m = re.search(r"traced the curve from ([\d.]+) (k?)Hz\.", words)
        start = float(m.group(1)) * (1000 if m.group(2) else 1) if m else None
        check(f"a bass roll-off under the grid ({w} px): the frequency in \"traced the curve from\" is the first "
              f"point's frequency (2 % or nearer), not 20 Hz",
              start and r.points and abs(start / r.points[0][0] - 1) <= 0.02,
              (start, r.points[0] if r.points else None))
        check(f"a bass roll-off under the grid ({w} px): out_words are the sentences of the two ends, the low end "
              f"first, with one space between them",
              re.fullmatch(r"From 20 Hz to [\d.]+ Hz, the left or right curve is below the bottom of the grid\. The "
                           r"app traced the curve from [\d.]+ Hz\. At 1[89][\d.]* kHz, the left or right curve goes "
                           r"below the bottom of the grid\. The app traced the curve to 1[78][\d.]* kHz\.",
                           r.out_words), r.out_words)


def test_dip_out_of_the_grid(qapp, monkeypatch, check):
    """A deep dip under the grid at 1 kHz (the curve goes out and comes back): no value there is correct, and the
    points would join the two sides with a straight line, so the gaps check fails with that reason. The parts out of
    the grid in the middle count as out of the grid in the curve check too: the gaps check is the first check that
    fails, and the window's status line shows its reason (before: the curve check failed first, "only 92 %")."""
    dip = lambda fn: lambda f: fn(f) - 30 * math.exp(-math.log2(f / 1000) ** 2 / 0.02)  # noqa: E731
    for w in (1000, 1396):
        _truth, r = read(monkeypatch, w, chan_fns=(dip(STEEP_END[0]), dip(STEEP_END[1])))
        words = reason(r, "trace_gaps")
        check(f"a dip under the grid at 1 kHz ({w} px): the gaps check fails, and says between which frequencies the "
              f"curve goes out of the grid", not r.ok and "trace_gaps" in failed(r) and words.startswith("Between ")
              and words.endswith("the left or right curve goes below the bottom of the grid. The app cannot trace "
                                 "that part."), (failed(r), words))
        check(f"a dip under the grid at 1 kHz ({w} px): the gaps check is the first check that fails (the curve check "
              f"passes)", failed(r)[:1] == ["trace_gaps"] and reason(r, "trace_curve").startswith("The curve is on 9"),
              (failed(r), reason(r, "trace_curve")))


def test_one_channel_out_in_the_middle(qapp, monkeypatch, check):
    """One channel goes out of the grid in the middle and the website cuts it at the bottom dB grid line (the usual
    look-alike on a dB axis of 48 to 88 dB: the right channel under 48 dB at 10.5 to 11 kHz). The band there is the
    other channel only: band() leaves those columns out, and the columns next to them touch the edge. On 593a54e all
    checks passed with the curve 0.62 to 0.72 dB off at 2 to 4 points; now the gaps check fails with its reason. A
    curve on the same dB axis where the website draws the curves past the edge (no cut) still passes."""
    for w, jpeg in ((800, None), (1000, None), (1000, 85), (1300, None)):
        _truth, r = read(monkeypatch, w, jpeg, chan_fns=None, clip_db=True, top_logo=False,
                         colours=("#1a48a0", "#0d357d"), db_range=(48, 88), db_step=5)
        words = reason(r, "trace_gaps")
        kind = f"JPEG {jpeg}" if jpeg else "PNG"
        check(f"one channel cut at the bottom edge at 10.5 to 11 kHz ({w} px, {kind}): the gaps check fails first, "
              f"with the frequencies of that part", failed(r)[:1] == ["trace_gaps"]
              and re.fullmatch(r"Between 10\.\d+ kHz and 11\.\d+ kHz, the left or right curve goes below the bottom of "
                               r"the grid\. The app cannot trace that part\.", words), (failed(r), words))
    for w in (800, 1396):
        truth, r = read(monkeypatch, w, chan_fns=None, clip_db=False, top_logo=False, colours=("#1a48a0", "#0d357d"),
                        db_range=(48, 88), db_step=5)
        e = errors(truth, r)
        check(f"the same dB axis where the website draws the curves past the bottom dB grid line (no cut, {w} px): all "
              f"checks pass, the curve less than 0.5 dB from the true average at each point", r.ok and e and e[1] < 0.5,
              (failed(r), e))


def test_narrow_gap_next_to_the_edge(qapp, monkeypatch, check):
    """A gap of only 1 to 5 columns next to a column at the bottom edge where the website cuts the curves (the usual
    look-alike on a dB axis of 47.5 to 87.5 dB, and 44.5 to 84.5 dB with the right channel 3 dB lower). The straight
    line across the gap is nearly correct (0.17 to 0.27 dB): it is not a part out of the grid. On 38286f9 each of these
    correct curves failed the gaps check."""
    for lo, w, off in ((47.5, 800, 0.0), (47.5, 1000, 0.0), (47.5, 1396, 0.0), (44.5, 1396, -3.0)):
        truth, r = read(monkeypatch, w, chan_fns=None, clip_db=True, top_logo=False, colours=("#1a48a0", "#0d357d"),
                        db_range=(lo, lo + 40), db_step=5, offset_db=off)
        e = errors(truth, r)
        check(f"a narrow gap next to the bottom edge (dB axis {lo} to {lo + 40} dB, right channel {off:+} dB, {w} px): "
              f"all checks pass, the curve less than 0.5 dB from the true average at each point",
              r.ok and e and e[1] < 0.5, (failed(r), e))


def test_straight_line_known_limit(qapp, monkeypatch, check):
    """A part with no curve of up to MAX_GAP where the curve bends is a straight line in the points (known limit 18 of
    trace_auto, with these numbers): the usual look-alike on a dB axis of 48.5 to 88.5 dB, where the website draws
    the curves past the bottom dB grid line (no cut). The error must not become larger."""
    for w, worst in ((800, 0.66), (1000, 0.63)):
        truth, r = read(monkeypatch, w, chan_fns=None, clip_db=False, top_logo=False, colours=("#1a48a0", "#0d357d"),
                        db_range=(48.5, 88.5), db_step=5)
        e = errors(truth, r)
        check(f"a short part with no curve where the curve bends (dB axis 48.5 to 88.5 dB, {w} px): the read fails, or "
              f"the curve is {worst} dB or less from the true average (the known limit, to 0.01 dB)",
              not r.ok or (e and round(e[1], 2) <= worst), (failed(r), e))


def test_end_and_middle_out_of_the_grid(qapp, monkeypatch, check):
    """The curve check adds a part out of the grid in the middle to the traced columns one time only (MIN_IN_GRID).
    The real form with a bass roll-off under the grid (an end part out of the grid) on a dB axis of 47 to 87 dB or 48
    to 88 dB: a dip at 8 to 16 kHz goes out of the grid in the middle too. The traced columns and the middle part are
    less than 90 % of the width (86.8 % + 2.0 %, 85.3 % + 2.7 %, measured), so the curve check fails."""
    fns = (_bass_out(STEEP_END[0]), _bass_out(STEEP_END[1]))
    for w, lo in ((1000, 47), (1396, 48)):
        _truth, r = read(monkeypatch, w, chan_fns=fns, db_range=(lo, lo + 40), db_step=5)
        check(f"an end and a part in the middle out of the grid (dB axis {lo} to {lo + 40} dB, {w} px): the curve "
              f"check fails, and the gaps check fails too", failed(r)[:2] == ["trace_curve", "trace_gaps"]
              and reason(r, "trace_curve").startswith("The curve is on only 8"),
              (failed(r), reason(r, "trace_curve")))


def test_wide_part_out_in_the_middle(qapp, monkeypatch, check):
    """A wide part out of the grid in the middle (the usual look-alike on a dB axis of 52 to 92 dB, a solid target:
    7.6 to 13.1 kHz) counts for MIN_IN_GRID too: the gaps check is the first check that fails, and the status line
    shows its true reason (on 593a54e: the curve check failed first, "only 89 %")."""
    _truth, r = read(monkeypatch, 1000, chan_fns=None, clip_db=True, top_logo=False, colours=("#1a48a0", "#0d357d"),
                     target="solid", db_range=(52, 92), db_step=5)
    check("a wide part out of the grid in the middle (1000 px): the gaps check is the first check that fails, and the "
          "curve check passes", failed(r)[:1] == ["trace_gaps"] and reason(r, "trace_gaps").startswith("Between 7.")
          and reason(r, "trace_curve").startswith("The curve is on 8"), (failed(r), reason(r, "trace_curve"),
                                                                         reason(r, "trace_gaps")))


def test_curve_that_ends_early(qapp, monkeypatch, check):
    """A curve that goes out of the grid far before 20 kHz (the usual look-alike on a dB axis of 55 to 95 dB: out at
    9.2 kHz, values to 7.6 kHz, 85 % of the width) is not a measurement for an EQ: the curve check fails, with the
    words of the end (before: all checks passed). The curve on MIN_IN_GRID of the grid or more passes (the real
    screen copy's form: 97 %)."""
    truth, r = read(monkeypatch, 1000, chan_fns=None, clip_db=False, top_logo=False, colours=("#1a48a0", "#0d357d"),
                    db_range=(55, 95))
    words = reason(r, "trace_curve")
    e = errors(truth, r)
    check("a curve out of the grid at 9.2 kHz (1000 px, 85 % of the width): the curve check fails, and only it",
          not r.ok and failed(r) == ["trace_curve"], failed(r))
    check("the curve check's words: 'only' 85 %, where the curve goes out of the grid, and to where the app traced it",
          re.fullmatch(r"The curve is on only 85 % of the width of the grid\. At 9\.\d+ kHz, the left or right curve "
                       r"goes below the bottom of the grid\. The app traced the curve to 7\.\d+ kHz\.", words), words)
    check("AutoRead's out_words: the words of the curve check after its first sentence", r.out_words and
          words == "The curve is on only 85 % of the width of the grid. " + r.out_words, (words, r.out_words))
    check("the points of that curve: correct (0.5 dB or less), to 7.4 to 7.8 kHz", e and e[1] <= 0.5
          and 7400 < r.points[-1][0] < 7800, (e, r.points[-1] if r.points else None))
    check("the frequency in \"traced the curve to\" is the frequency of the last traced column",
          words.endswith(f"The app traced the curve to {last_column_hz(r)}."), (words, last_column_hz(r)))
    # (between 86 % and 90 %: a curve that falls out of the grid near 9.8 kHz, 88 % of the width)
    fall = lambda fn: lambda f: fn(f) - 40 * max(0.0, math.log2(f / 7500))  # noqa: E731
    truth, r = read(monkeypatch, 1000, chan_fns=(fall(STEEP_END[0]), fall(STEEP_END[1])))
    words = reason(r, "trace_curve")
    e = errors(truth, r)
    check("a curve out of the grid at 9.8 kHz on 88 % of the width (1000 px, a correct curve to there): the curve "
          "check fails, and only it (MIN_IN_GRID is 90 %)", e and e[1] <= 0.5 and failed(r) == ["trace_curve"]
          and words.startswith("The curve is on only 88 % "), (failed(r), e, words))
    _truth, r = read(monkeypatch)
    check("the real screen copy's form (97 %): AutoRead's out_words are the end of the curve check's words",
          r.ok and r.out_words.startswith("At 18.") and reason(r, "trace_curve").endswith(" " + r.out_words),
          (r.out_words, reason(r, "trace_curve")))
    _truth, r = read(monkeypatch, 1000, chan_fns=None, clip_db=False, top_logo=False)
    check("a curve that stays in the grid: out_words is empty", r.ok and r.out_words == "", r.out_words)


def test_target_when_the_curve_is_out(qapp, monkeypatch, check):
    """A target line on a graph whose curve is out of the grid for a part: no target (before, on a dB axis of 55 to
    85 dB at 800 px, all checks passed with a target 6.57 dB (solid) or 6.63 dB (dashed) off at 29 points: it followed
    its own name). The curve on less than MIN_TRACED of the grid gives no target, except when the curve passes the
    curve check and is out of the grid only at its ends: a bass roll-off under the grid keeps its correct target (on
    593a54e: no target, and the user had to add it)."""
    for kind in ("solid", "dashed"):
        for clip in (False, True):
            truth, r = read(monkeypatch, 800, chan_fns=None, clip_db=clip, top_logo=False,
                            colours=("#1a48a0", "#0d357d"), target=kind, db_range=(55, 85), db_step=5)
            te = [abs(v - truth["tgt"](f)) for f, v in r.target_points or []]
            check(f"a {kind} target, the curve out of the grid at 9 kHz (800 px, a dB axis of 55 to 85 dB, clip_db "
                  f"{clip}): no target line, and never one more than 1 dB off with all checks passed",
                  r.target is None and r.target_points is None and not (r.ok and te and max(te) > 1),
                  (r.ok, failed(r), max(te) if te else None))
    fns = (_bass_out(STEEP_END[0]), _bass_out(STEEP_END[1]))
    for w in (1000, 1396):
        for kind in ("solid", "dashed"):
            truth, r = read(monkeypatch, w, chan_fns=fns, target=kind)
            te = [abs(v - truth["tgt"](f)) for f, v in r.target_points or []]
            check(f"a {kind} target on the real form with a bass roll-off out of the grid ({w} px, all checks pass, "
                  f"the curve on 94 % of the grid, out only at its ends): the target line, less than 0.5 dB from the "
                  f"true target at each point (measured: 0.03 to 0.11 dB)", r.ok and r.target is not None and te
                  and max(te) < 0.5, (failed(r), reason(r, "trace_curve"), max(te) if te else None))
    _truth, r = read(monkeypatch, 1000, chan_fns=None, clip_db=True, top_logo=False, colours=("#1a48a0", "#0d357d"),
                     target="solid", db_range=(48, 88), db_step=5)
    check("a target where one curve goes out of the grid in the middle (1000 px, a dB axis of 48 to 88 dB): no target "
          "line", r.target is None and "trace_gaps" in failed(r), (failed(r), r.target is None))


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
    for w, xy, worst in ((1396, (690, 200), 1.79), (1000, (690, 200), 1.08), (1000, (700, 150), 1.43)):
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


def test_line_that_falls_to_the_end(check):
    """_continued: two lines that fall steeply after a peak at the band's end (a JPEG of a small grid: the upper line
    touches the lower one in one column, then both are level to the end). edge_slope kept a part of the upper line's
    run there, the part left out was beside the line's track, and the track ended: from the right, the upper line was
    not kept in its last 4 columns (an older real picture, a JPEG of a 503 px grid, lost 17.7 to 18.8 kHz). Now its
    rows are kept in its last 3 columns (in the column before them, 3 of its 5 rows stay out: as with no edge_slope)."""
    end = [((30, 36), (52, 58)), ((24, 30), (48, 54)), ((20, 25), (46, 50)), ((18, 22), (45, 48)),
           ((20, 28), (46, 53)), ((27, 41), (42, 56)), ((38, 72), None), ((51, 84), (85, 86)), ((66, 77), (79, 92)),
           ((76, 81), (89, 96)), ((80, 83), (93, 96)), ((81, 84), (92, 95)), ((82, 84), (91, 94)), (None, (91, 93))]
    solid = np.zeros((130, 30 + len(end)), bool)
    solid[40:44, :30] = solid[60:64, :30] = True  # (two level lines)
    for i, pair in enumerate(end):
        for r in pair:
            if r:
                solid[r[0]:r[1], 30 + i] = True
    stay = trace_auto._continued(solid, 4, 7, (0, 129))
    lost = {x: int((solid[:, x] & ~stay[:, x]).sum()) for x in range(40, 43) if (solid[:, x] & ~stay[:, x]).any()}
    check("two lines that fall steeply to the band's end: all rows are kept in the upper line's last 3 columns "
          "(columns 40 to 42)", not lost, lost)
    # (the mirror form: two lines that go up steeply to the band's end. The part of a run left out is then below the
    # part kept, and the track continues where the whole run touches it: its top row a, not only the part's top row)
    up = solid[::-1].copy()
    stay = trace_auto._continued(up, 4, 7, (0, 129))
    lost = {x: int((up[:, x] & ~stay[:, x]).sum()) for x in range(40, 43) if (up[:, x] & ~stay[:, x]).any()}
    check("two lines that go up steeply to the band's end (the mirror form): all rows are kept in the lower line's "
          "last 3 columns (columns 40 to 42)", not lost, lost)


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
    check("comes_in: a track from the bottom edge row that moves up 1 row for each column: a line",
          trace_auto.comes_in([(0, 567, 570), (1, 566, 569), (2, 565, 568)], (18.0, 569.0)))
    check("comes_in: a track from the top edge row that moves down 1 row for each column: a line",
          trace_auto.comes_in([(0, 18, 21), (1, 19, 22), (2, 20, 23)], (18.0, 569.0)))
    check("comes_in: a track from the bottom edge row that moves up half a row for each column: not a line",
          not trace_auto.comes_in([(0, 567, 570), (1, 567, 569), (2, 566, 569)], (18.0, 569.0)))


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
    # (each rule of line_edge alone: a line of the usual height whose edge jumps 3 line widths at the end of a word,
    # and a smooth edge of a line 3 line widths high, are text)
    jump = dip.copy()
    jump[26:34] = jump[30]
    jump[34:] = jump[34:] + 3 * lw
    got = trace_auto.flat_beside_steep(steep, jump, lw, (runs, first, steep + 15, jump - lw / 2))
    check("a level edge of the usual line height (1 line width) that jumps 3 line widths at a word's end, beside a "
          "steep channel: text (the edge must bend by less than 1.5 line widths)", got[27:33].all(),
          np.flatnonzero(got))
    got = trace_auto.flat_beside_steep(steep, dip, lw, (runs, first, steep + 15, dip - 1.5 * lw))
    check("a smooth level edge of a line 3 line widths high beside a steep channel: text (a line is 0.75 to 2 line "
          "widths high)", got[28:33].all(), np.flatnonzero(got))


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
    touch = np.zeros(100)
    touch[[37, 38, 39, 50, 51]] = 1  # (the traced columns next to the gap touch the bottom edge)
    ends, middle = trace_auto.out_parts(inside, touch, (1,))
    check("out_parts: a gap next to columns at the bottom edge, where the website cut the curves (clip): out in the "
          "middle (one channel went out of the grid there)", middle == [(40, 50, 1, 39, 50)], middle)
    ends, middle = trace_auto.out_parts(inside, touch, ())
    check("out_parts: the same gap where the website draws the curves past the edge (no clip): not out",
          middle == [], middle)
    ends, middle = trace_auto.out_parts(inside, touch, (-1,))
    check("out_parts: the same gap with a cut at the top edge only: not out", middle == [], middle)
    inside = np.ones(1000, bool)
    inside[400:403] = False
    touch = np.zeros(1000)
    touch[[398, 399, 403, 404]] = 1
    ends, middle = trace_auto.out_parts(inside, touch, (1,))
    check("out_parts: a gap of 3 columns of 1000 next to columns at the bottom edge, where the website cut the curves: "
          "not out (a straight line across it is nearly correct)", middle == [], middle)
    inside[400:406] = False
    touch = np.zeros(1000)
    touch[[398, 399, 406, 407]] = 1
    ends, middle = trace_auto.out_parts(inside, touch, (1,))
    check("out_parts: a gap of 6 columns of 1000 (0.6 % of the width) next to the same columns: out in the middle",
          middle == [(400, 406, 1, 399, 406)], middle)


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


# ---------------------------------------------------------------- the tracer's window
def test_status_line_of_a_failed_read(eq_screen, monkeypatch, tmp_path, check):
    """The status line after an automatic read that failed, in its longest form: the curve check fails with the words
    of the two ends out of the grid (the real form with a bass roll-off on a dB axis of 50 to 90 dB, 1396 px: 6
    sentences). The instruction to correct the step starts a new line: no paragraph has more than 6 sentences (on
    593a54e: 8 in one paragraph). The status line shows all of its words at the usual and the smallest size of the
    window (pictures in light and dark)."""
    from helpers import qt
    from ui.trace_window import CORRECT_STEP
    fns = (_bass_out(STEEP_END[0]), _bass_out(STEEP_END[1]))
    img, truth = website_graph(plot_w=1396, chan_fns=fns, clip_db=True, top_logo=True, colours=REAL, db_range=(50, 90))
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    tw.load_image(img, entry={"name": "Sample IEM", "tag": "Sample 5128", "site": "Sample.Audio",
                              "link": "https://example.invalid/x"})
    qt.wait_for(lambda: not tw.loading and not tw.reading_graph and tw.read_ok is not None, 60)
    text, ok = tw.status.text(), tw.read_ok
    paras = text.split("\n")
    counts = [len(re.findall(r"[.?!](?=\s|$)", p.strip())) for p in paras]
    seen = {}
    usual = tw.size()
    for which, size in (("usual", usual), ("smallest", tw.minimumSize().expandedTo(tw.minimumSizeHint()))):
        tw.resize(size)
        qt.pump(150)
        st = tw.status
        seen[which] = (tw.width(), st.width(), st.height(), st.heightForWidth(st.width()), st.isVisible())
        for name, theme_on in (("light", qt.light), ("dark", qt.dark)):  # (the pictures: read back by the author)
            theme_on(eq_screen.qapp)
            qt.pump(100)
            tw.grab().save(str(tmp_path / f"status-failed-read-{which}-{name}.png"))
    qt.light(eq_screen.qapp)
    tw.resize(usual)
    tw.remove_image()
    tw.close()
    check("tracer: a failed read whose curve check has the words of two ends: the status line is the first sentence "
          "and the reason, then the instruction on a new line", ok is False
          and text.startswith("The app cannot trace this picture automatically. The curve is on only ")
          and "From 20 Hz to " in paras[0] and " At 1" in paras[0] and paras[1:] == [CORRECT_STEP], text)
    check("tracer: no paragraph of that status line has more than 6 sentences (STE)", counts == [6, 2], counts)
    check("tracer: no line of that status line ends with a space", not any(p.endswith(" ") for p in paras),
          [p[-20:] for p in paras])
    check("tracer: the status line shows all of its words at the usual and the smallest size of the window (its "
          "height is the height that its words need)", all(seen[k][4] and seen[k][2] >= seen[k][3]
                                                            for k in ("usual", "smallest")), seen)


# ---------------------------------------------------------------- 3 Save's note in the tracer's window
def test_save_note_tells_the_end(eq_screen, monkeypatch, tmp_path, check):
    """After an automatic read that passed, 3 Save's note says where the curve goes out of the grid and to where the
    app traced it (AutoRead.out_words, the words of trace_curve), before "Compare the curve with the picture.". The
    note shows all of its words at the usual and the smallest size of the window (pictures in light and dark)."""
    from helpers import qt
    from ui.trace_window import rgb_of
    img, truth = website_graph(plot_w=1396, chan_fns=STEEP_END, clip_db=True, top_logo=True, colours=REAL)
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    r = trace_core.auto_read(rgb_of(img), NO_WORDS, False, "Sample IEM")
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    tw.load_image(img, entry={"name": "Sample IEM", "tag": "Sample 5128", "site": "Sample.Audio",
                              "link": "https://example.invalid/x"})
    qt.wait_for(lambda: not tw.loading and not tw.reading_graph and tw.read_ok is not None, 60)
    tw.show_tab(2)
    want = (f"The app traced the graph of “Sample IEM” from “Sample.Audio”. {r.out_words}\nCompare the curve with the "
            "picture. If they agree, click Add as measurement.")
    seen = {"text": tw.save_note.text()}
    usual = tw.size()
    for which, size in (("usual", usual), ("smallest", tw.minimumSize().expandedTo(tw.minimumSizeHint()))):
        tw.resize(size)
        qt.pump(150)
        note = tw.save_note
        seen[which] = (tw.width(), note.width(), note.height(), note.heightForWidth(note.width()))
        for name, theme_on in (("light", qt.light), ("dark", qt.dark)):  # (the pictures: read back by the author)
            theme_on(eq_screen.qapp)
            qt.pump(100)
            tw.pages.currentWidget().grab().save(str(tmp_path / f"save-note-out-of-grid-{which}-{name}.png"))
    qt.light(eq_screen.qapp)
    tw.resize(usual)
    tw.remove_image()
    tw.close()
    check("tracer: after a read of a curve that goes out of the grid, 3 Save's note says where and to where the app "
          "traced it, before 'Compare the curve with the picture.'", r.ok and r.out_words.startswith("At 18.")
          and seen["text"] == want, (seen["text"], want))
    check("tracer: the note shows all of its words at the usual and the smallest size of the window (its height is "
          "the height that its words need)", all(seen[k][2] >= seen[k][3] for k in ("usual", "smallest")), seen)
