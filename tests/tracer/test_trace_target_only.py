"""The tracer's automatic read of a picture with only a target line (ui\\trace_auto.py: auto_read's target_only, its
want, line_alone, for_entry), on drawn look-alikes (helpers.website_graph: website_graph(curves=False) and
target_graph, the look of a website's graph of a target; no picture of a real website is kept here). The true words
of each picture stand in for Windows' text reader (helpers.website_graph.truth_reader).

What is held: the line alone is the result (its label "Target", its mark "target"), within 0.5 dB of the truth, solid
and dashed, 1000 to 2400 px, PNG and JPEG; the dB axis of a target graph (-20 to 20 dB); the blue shape and the gray
watermark are not the curve; the kind of the entry against the kind of the picture (want, for_entry); a line out of
the grid at an end; a picture with no line gives no target result with all checks passed."""
import math

import numpy as np
import pytest

from helpers.website_graph import as_rgb, target_graph, truth_reader, website_graph
from ui import trace_auto, trace_core

COVERS = ("ui.trace_auto", "ui.trace_core")
NO_WORDS = lambda rgb: []  # noqa: E731  (an ocr_words that reads nothing: the stand-in gives the words)


def dark(rgb):
    """The same hue and chroma, the lightness inverted (a dark page)."""
    a = rgb.astype(np.int32)
    return np.clip(a + (255 - a.max(2) - a.min(2))[..., None], 0, 255).astype(np.uint8)


def through_jpeg(rgb, q):
    from PySide6.QtGui import QImage
    h, w = rgb.shape[:2]
    rgb = np.ascontiguousarray(rgb)
    return as_rgb(QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy(), q)


def read(monkeypatch, w=1000, jpeg=None, look=False, page_dark=False, want=None, **kw):
    """(truth, AutoRead) of a look-alike: website_graph(plot_w=w, **kw), or target_graph(w, **kw) with look."""
    img, truth = target_graph(w, **kw) if look else website_graph(plot_w=w, **kw)
    rgb = as_rgb(img)
    if page_dark:
        rgb = dark(rgb)
    if jpeg:
        rgb = through_jpeg(rgb, jpeg)
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    return truth, trace_core.auto_read(rgb, NO_WORDS, bool(jpeg), "Sample Target", **({"want": want} if want else {}))


def errors(pts, fn):
    """(largest difference in dB, the count of points more than 0.5 dB off, the count of points) or None."""
    e = [abs(v - fn(f)) for f, v in pts or [] if 20 <= f <= 20000]
    return (max(e), sum(x > 0.5 for x in e), len(e)) if e else None


def failed(r):
    return [(c.name, c.reason) for c in r.checks if not c.ok]


def is_target(r):
    """The result is the target line alone: target_only, one curve "Target" with the mark, no second target."""
    t = r.tracer
    return (getattr(r, "target_only", False) and len(t.curves) == 1 and r.curve is t.curves[0]
            and r.curve["label"] == "Target" and r.curve.get("target") is True and r.target is None
            and r.target_points is None)


@pytest.mark.parametrize("w", [1000, 1396, 2234])
def test_target_line_alone(qapp, monkeypatch, check, w):
    for kind in ("solid", "dashed"):
        for jpeg in (None, 85):
            truth, r = read(monkeypatch, w, jpeg, target=kind, curves=False)
            e = errors(r.points, truth["tgt"])
            check(f"a picture with only a target line ({kind}, {w} px, {'JPEG 85' if jpeg else 'PNG'}): all checks "
                  "pass, and the result is the target line alone", r.ok and is_target(r), failed(r))
            check(f"a picture with only a target line ({kind}, {w} px, {'JPEG 85' if jpeg else 'PNG'}): the curve is "
                  "within 0.5 dB of the true target, from 23 Hz or less to 17 kHz or more",
                  e and e[0] <= 0.5 and r.points[0][0] <= 23 and r.points[-1][0] >= 17000, (e, r.points[:1],
                                                                                           r.points[-1:]))


def test_target_line_alone_checks(qapp, monkeypatch, check):
    _truth, r = read(monkeypatch, 1000, target="dashed", curves=False)
    names = [c.name for c in r.checks]
    # (2026-11-13: trace_single, a second target line, the verifier's M2)
    check("a target line alone: the checks of the axes, then trace_kind, trace_single, trace_curve and trace_gaps",
          names == ["axes_plot", "axes_grid", "axes_hz_labels", "axes_hz_range", "axes_db_labels", "axes_db_range",
                    "trace_kind", "trace_single", "trace_curve", "trace_gaps"], names)
    reasons = {c.name: c.reason for c in r.checks}
    check("a target line alone: the words of its checks are for a target line",
          reasons["trace_kind"] == "The picture has a target line and no measurement curve."
          and reasons["trace_single"] == "The picture has one target line."
          and reasons["trace_curve"].startswith("The target line is on ")
          and reasons["trace_gaps"] == "All of the target line is traced.", reasons)


@pytest.mark.parametrize("form", ["dB axis 35 to 85, JPEG 60", "dB axis 45 to 75, dark, JPEG 85",
                                  "dB axis 40 to 80, dark, PNG"])
def test_target_line_alone_more_forms(qapp, monkeypatch, check, form):
    # (dashed, 1000 px: a JPEG lost one dash next to a frequency grid line, ALONE_GAP; the default target near the 60 dB
    # grid line: find_target's alone keeps its points there)
    rng = (35, 85) if "35" in form else (45, 75) if "45" in form else (40, 80)
    jpeg = 60 if "60" in form else 85 if "85" in form else None
    truth, r = read(monkeypatch, 1000, jpeg, page_dark="dark" in form, target="dashed", curves=False, db_range=rng)
    e = errors(r.points, truth["tgt"])
    check(f"a dashed target line alone ({form}, 1000 px): all checks pass, within 0.5 dB",
          r.ok and is_target(r) and e and e[0] <= 0.5, (failed(r), e))


@pytest.mark.parametrize("w", [1200, 1458, 2400])
def test_target_graph_of_a_website(qapp, monkeypatch, check, w):
    for jpeg in (None, 85):
        truth, r = read(monkeypatch, w, jpeg, look=True)
        e = errors(r.points, truth["tgt"])
        check(f"the look of a website's graph of a target ({w} px, {'JPEG 85' if jpeg else 'PNG'}): all checks pass, "
              "the result is the target line, within 0.5 dB of the truth on the axis of the picture (-20 to 20 dB)",
              r.ok and is_target(r) and e and e[0] <= 0.5 and e[2] >= 450, (failed(r), e))
        reason = next(c.reason for c in r.checks if c.name == "axes_db_range")
        check(f"the look of a website's graph of a target ({w} px): the dB axis -20 dB to 20 dB is usual for a target",
              reason == "The dB axis is -20 dB to 20 dB." and r.tracer.axis_note.endswith(reason), reason)


def test_negative_axis_only_for_a_target(qapp, monkeypatch, check):
    # (the measurement's rule stays: a measurement on a dB axis of -20 to 20 dB is not usual)
    _truth, r = read(monkeypatch, 1000, db_range=(-20, 20), chan_fns=(lambda f: 1.0 + math.sin(math.log2(f)),
                                                                       lambda f: math.sin(math.log2(f))))
    reason = next(c.reason for c in r.checks if c.name == "axes_db_range")
    check("a measurement on a dB axis of -20 to 20 dB: axes_db_range fails, as before",
          not r.ok and not getattr(r, "target_only", False)
          and reason == "The dB axis is -20 dB to 20 dB. This range is not usual for a graph of an IEM or headphone.",
          (reason, failed(r)))


def test_blue_shape_and_watermark_are_not_the_curve(qapp, monkeypatch, check):
    # (the blue logo: a strong color with many pixels; the watermark: large gray text in the gray of the line, nearer
    # the middle than the line, found first at 1000 px)
    for w, jpeg, page_dark in ((1000, 85, True), (1000, None, False), (1700, None, False)):
        truth, r = read(monkeypatch, w, jpeg, look=True, page_dark=page_dark)
        e = errors(r.points, truth["tgt"])
        check(f"the look of a website's graph of a target ({w} px, {'JPEG 85' if jpeg else 'PNG'}"
              f"{', dark' if page_dark else ''}): the curve is the target line, not the blue logo or the watermark",
              r.ok and is_target(r) and e and e[0] <= 0.5, (failed(r), e))


def test_soft_db_bands_in_a_strong_color_are_not_the_curve(qapp, monkeypatch, check):
    # (find_target alone: a seed in the color of the dB grid lines is not the line; the bands of an earlier look-alike,
    # stronger than a real picture's, were traced as the target: 20.8 dB off at all points with all checks passed)
    img, truth = target_graph(1700, bands=((5.0, "#f6ead8"), (3.4, "#efdfc6"), (1.8, "#e6d3b6")))
    rgb = as_rgb(img)
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    r = trace_core.auto_read(rgb, NO_WORDS, False, "Sample Target")
    e = errors(r.points, truth["tgt"])
    check("a target graph with strong dB bands: no result with all checks passed that is more than 0.5 dB off",
          not r.ok or (is_target(r) and e and e[0] <= 0.5), (failed(r), e))
    check("a target graph with strong dB bands: the result is the target line", r.ok and is_target(r), failed(r))


def test_entry_of_a_target(qapp, monkeypatch, check):
    for kind in ("solid", "dashed"):
        truth, r = read(monkeypatch, 1000, target=kind, target_fn=lambda f: website_graph_target(f) - 14,
                        db_range=(30, 80), want="target")
        e = errors(r.points, truth["tgt"])
        check(f"an entry of a target, a picture with a measurement and a {kind} target line apart from it: the result "
              "is the target line alone, all checks pass", r.ok and is_target(r) and e and e[0] <= 0.5,
              (failed(r), e))
    for name, kw in (("a target line across it", {"target": "solid"}), ("no target line", {})):
        _truth, r = read(monkeypatch, 1000, want="target", **kw)
        first = failed(r)[:1]
        check(f"an entry of a target, a picture with a measurement and {name}: trace_kind fails first and tells the "
              "user to remove the measurement", not r.ok and not getattr(r, "target_only", False)
              and first == [("trace_kind", trace_auto.KIND_NOT_TARGET)], first)
    # (one name for one item: "the measurement curve", as in Help #pw-paste; the final verification's SF6)
    check("the words of KIND_NOT_TARGET", trace_auto.KIND_NOT_TARGET == (
        "The picture has a measurement curve. The app cannot trace only the target line. Remove the measurement curve "
        "from the graph of the website."), trace_auto.KIND_NOT_TARGET)


def test_words_for_an_entry_of_a_target(qapp, monkeypatch, check):
    # (2026-11-13, the verifier's S3 and S4: each reason is true for a target)
    _truth, r = read(monkeypatch, 1000, look=True, target=None, want="target", db_range=(-30, 30))
    reasons = {c.name: (c.ok, c.reason) for c in r.checks}
    check("an entry of a target, a picture with no line: trace_curve fails with \"The app did not find a target "
          "line.\", and the dB axis -30 dB to 30 dB is usual for a target",
          not r.ok and failed(r)[:1] == [("trace_curve", "The app did not find a target line.")]
          and reasons["axes_db_range"] == (True, "The dB axis is -30 dB to 30 dB."), failed(r))
    _truth, r = read(monkeypatch, 1000, look=True, target=None, want="target", db_range=(-60, -20))
    check("an entry of a target, a dB axis of -60 dB to -20 dB: not usual, with the words of a target",
          ("axes_db_range", "The dB axis is -60 dB to -20 dB. This range is not usual for a graph of a target.")
          in failed(r), failed(r))
    _truth, r = read(monkeypatch, 1000, target="solid", target_fn=lambda f: website_graph_target(f) - 14,
                     db_range=(30, 80), want="target")
    kind = next(c for c in r.checks if c.name == "trace_kind")
    check("an entry of a target, a measurement and a target line apart from it: trace_kind tells that the picture "
          "has a measurement curve too, and that the app traced only the target line",
          r.ok and kind.reason == "The picture has a target line and a measurement curve. The app traced only the "
          "target line.", kind)


def website_graph_target(f):
    from helpers import website_graph as wg
    return wg._target(f)


def has_curve(r):
    return any(r.tracer.has_data(c) for c in r.tracer.curves)


GREY_REASON = "The app did not find a curve in a strong color. If the graph of the website shows only a target, show " \
              "the measurement on the graph."


def test_entry_of_a_measurement(qapp, monkeypatch, check):
    # (2026-11-13, the verifier's M3: for an entry of a measurement the read does not take a gray line alone as the
    # curve. Before, the tracer had a curve "Target" and the words told that the picture had only a target line)
    _truth, r = read(monkeypatch, 1000, target="solid", curves=False, want="measurement")
    check("an entry of a measurement, a picture with only a target line: trace_curve fails with the words of a "
          "measurement and one sentence about the gray line; no curve in the tracer",
          not r.ok and not r.target_only and failed(r) == [("trace_curve", GREY_REASON)] and not has_curve(r),
          (failed(r), has_curve(r)))
    _truth, r0 = read(monkeypatch, 1000, target="solid", curves=False)
    check("the same picture with no entry: the target line alone, all checks pass", r0.ok and is_target(r0),
          failed(r0))
    _truth, r = read(monkeypatch, 1000, want="measurement")
    check("an entry of a measurement, a picture with a measurement: all checks pass, no trace_kind (as before)",
          r.ok and "trace_kind" not in [c.name for c in r.checks], failed(r))


@pytest.mark.parametrize("form", ["purple, 550 px, JPEG 20, 5 dB apart", "blue, 500 px, JPEG 50, 6 dB apart",
                                  "gray (#808080), 1000 px, PNG", "black, 1396 px, JPEG 85"])
def test_measurement_that_the_app_cannot_read(qapp, monkeypatch, check, form):
    # (the verifier's 4 forms: the words and the state of the tracer of 357d228, "The app did not find a curve in a
    # strong color." with no curve, and a second sentence only when the app found a gray line)
    kw, w, jpeg = {"purple": (dict(colours=("#8e44ad", "#6c3483"), offset_db=5), 550, 20),
                   "blue": (dict(offset_db=6), 500, 50), "gray": (dict(colours=("#808080", "#6e6e6e")), 1000, None),
                   "black": (dict(colours=("#000000", "#202020")), 1396, 85)}[form.split(",")[0].split(" ")[0]]
    _truth, r = read(monkeypatch, w, jpeg, want="measurement", **kw)
    first = failed(r)[:1]
    check(f"an entry of a measurement, a measurement that the app cannot read ({form}): trace_curve fails first with "
          "the words of a measurement, no target result, no curve in the tracer",
          not r.ok and not r.target_only and first and first[0][0] == "trace_curve"
          and first[0][1] in ("The app did not find a curve in a strong color.", GREY_REASON) and not has_curve(r),
          (first, has_curve(r)))


def test_entry_of_a_measurement_with_no_grey_line(qapp, monkeypatch, check):
    # (the final verification's T13: no test had an entry of a measurement and no gray line. The sentence about the
    # gray line is only for a picture where the app found one)
    _truth, r = read(monkeypatch, 1000, curves=False, want="measurement")
    check("an entry of a measurement, a picture with no curve and no line: trace_curve fails with the words of "
          "version 1.6.1 only (no sentence about a gray line)",
          not r.ok and failed(r) == [("trace_curve", trace_auto.NO_STRONG_CURVE)], failed(r))


def test_entry_of_a_measurement_and_a_graph_of_a_target(qapp, monkeypatch, check):
    # (the final verification's SF5: the website's graph of a target, -20 dB to 20 dB, for an entry of a measurement.
    # The first failed check was axes_db_range, and the status line shows only that one: the user did not see that
    # the graph showed only a target. That check gets the sentence too; inferred, 2026-11-13)
    _truth, r = read(monkeypatch, 1200, look=True, want="measurement")
    check("an entry of a measurement, the look of a website's graph of a target: axes_db_range fails first, with the "
          "sentence about the gray line after its own words; trace_curve has its words; no target result, no curve",
          not r.ok and not r.target_only and not has_curve(r) and failed(r)[:1] == [(
              "axes_db_range", "The dB axis is -20 dB to 20 dB. This range is not usual for a graph of an IEM or "
              "headphone. " + trace_auto.ONLY_GREY_LINE)] and failed(r)[-1:] == [("trace_curve", GREY_REASON)],
          failed(r))
    _truth, r = read(monkeypatch, 1200, look=True, want="measurement", target=None)
    check("an entry of a measurement, the look of a website's graph of a target with no line: axes_db_range fails "
          "first with its own words only", failed(r)[:1] == [(
              "axes_db_range", "The dB axis is -20 dB to 20 dB. This range is not usual for a graph of an IEM or "
              "headphone.")], failed(r))


@pytest.mark.parametrize("form", ["treble down", "treble up, cut", "bass out at the bottom, cut",
                                  "bass out to 21.9 Hz, cut"])
def test_target_line_out_of_the_grid(qapp, monkeypatch, check, form):
    if form == "treble down":  # (out at the bottom at 15.6 kHz; the website draws it to the graph's edge)
        fn, clip = (lambda f: 62.5 - 25 * max(0.0, math.log2(f / 8000)) ** 1.5), False
    elif form == "treble up, cut":  # (out at the top at 14.8 kHz across the gray text there, cut at the top line)
        fn, clip = (lambda f: 62 + 25 * max(0.0, math.log2(f / 8000)) ** 1.5), True
    elif form == "bass out at the bottom, cut":  # (out below 25 Hz, cut at the bottom dB grid line, at the label "40")
        fn, clip = (lambda f: 37.5 + 25 * math.log10(f / 20) if f < 200 else 62.5), True
    else:  # (out below 21.9 Hz, under the label "40": find_target alone has no points on a label)
        fn, clip = (lambda f: 38.5 + 25 * math.log10(f / 20) if f < 200 else 63.5), True
    truth, r = read(monkeypatch, 1000, target="solid", curves=False, target_fn=fn, clip_db=clip)
    e = errors(r.points, truth["tgt"])
    check(f"a target line alone that goes out of the grid ({form}, 1000 px): no result with all checks passed that "
          "is more than 0.5 dB off (the columns before the edge have no points: EXIT_CUT; the label next to the end "
          "is not the line: target_ends, and no points on a label)", not r.ok or (e and e[0] <= 0.5), (failed(r), e))
    if form == "treble down":
        curve = next(c.reason for c in r.checks if c.name == "trace_curve")
        check("a target line alone out of the grid at 15.6 kHz: all checks pass, and trace_curve and the note tell "
              "where", r.ok and "the target line goes below the bottom of the grid. The app traced the target line "
              "to " in curve and r.out_words and r.out_words in curve and r.points[-1][0] < 15600, curve)


@pytest.mark.parametrize("w", [600, 1000, 2234])
def test_no_line_gives_no_target(qapp, monkeypatch, check, w):
    for name, kw in (("the grid only, with its gray text", dict(curves=False)),
                     ("a page, the grid only", dict(curves=False, page=True)),
                     ("the look of a target graph, no line", dict(look=True, target=None)),
                     ("the look of a target graph, the legend only", dict(look=True, target_width=0.01))):
        for jpeg in (None, 60):
            _truth, r = read(monkeypatch, w, jpeg, **kw)
            check(f"{name} ({w} px, {'JPEG 60' if jpeg else 'PNG'}): no target result with all checks passed",
                  not r.ok, (getattr(r, "target_only", None), failed(r)[:1]))


@pytest.mark.parametrize("form", [("#27ae60", "#1e8449", 550, 40, 5), ("#8e44ad", "#6c3483", 800, 40, 3),
                                  ("#27ae60", "#1e8449", 500, 50, 5)])
def test_pale_measurement_is_not_a_target(qapp, monkeypatch, check, form):
    # (a measurement that a poor JPEG made pale has no strong color: the line alone must be gray, ALONE_GREY; these 3
    # passed all checks as a target line, 2.58 dB from the average of the channels)
    c1, c2, w, jpeg, off = form
    _truth, r = read(monkeypatch, w, jpeg, colours=(c1, c2), offset_db=off)
    check(f"a measurement in {c1}, {w} px, JPEG {jpeg}, the channels {off} dB apart: no target result with all checks "
          "passed", not (r.ok and getattr(r, "target_only", False)), (getattr(r, "target_only", None), failed(r)[:1]))
