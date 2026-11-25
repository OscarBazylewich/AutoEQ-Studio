"""The joined messages of the tracer's core (ui\\trace_core.py) that the text survey of 2026-11-24 changed: the error
of one of several curves (the error's own end period goes before "(or remove it on 2 Trace)") and the message after
a save with untraced gaps (one gap or more); sentences, which joins the causes of the automatic read (area 25), and
a label read after its note. No window: a plain white picture with typed axis values."""
import numpy as np

from ui.trace_core import NBSP, Tracer


def _tracer():
    """A tracer on a white picture with the 4 axis values typed: 20 Hz to 20 kHz across 0 to 399 px."""
    t = Tracer()
    t.load(np.full((300, 400, 3), 255, np.uint8), "Traced graph")
    t.v.update(f1="20", f2="20000", d1="90", d2="40")
    t.cal.update(x1=0.0, x2=399.0, y1=50.0, y2=250.0)
    return t


def test_error_of_one_curve_of_several(check):
    t = _tracer()
    t.curves[0]["ys"][:] = 150.0  # (L: the whole width traced)
    t.add_curve()
    t.curves[1]["ys"][200:225] = 150.0  # (R: 25 px, too few points to save)
    try:
        t.outputs()
        said = ""
    except ValueError as e:
        said = str(e)
    check("tracer: an error of one of several curves names the curve and ends with “(or remove it on 2 Trace)”, with "
          "no period of the error before the bracket",
          said.startswith("Curve “R”: Only ") and "(32 min). Trace more of the curve or increase points per octave "
          f"(or remove it on 2{NBSP}Trace)" in said and ". (" not in said, said)


def test_gaps_message(check):
    one = Tracer.gaps_text([{"gaps": [(1000.0, 2000.0)]}])
    two = Tracer.gaps_text([{"gaps": [(1000.0, 2000.0)]}, {"gaps": [(5000.0, 8000.0)]}])
    check("tracer: the message after a save with untraced parts says “gap” for one and “gaps” for more, with each range",
          one.startswith("Saved a straight line across untraced gap at ") and "gaps" not in one.split(".")[0]
          and two.startswith("Saved a straight line across untraced gaps at ")
          and two.endswith(". Trace or draw across those gaps for an accurate curve.") and two.count("–") == 2,
          (one, two))
    # (a review of the text survey, 2026-11-24: one gap said "Trace or draw across those gaps")
    check("tracer: the message after a save with one untraced gap says “across that gap”",
          one.endswith(". Trace or draw across that gap for an accurate curve.") and "those" not in one, one)
    check("tracer: no message when every part is traced", Tracer.gaps_text([{"gaps": []}]) == "")


def test_sentences(check):
    # (area 25 of the text survey: the causes of the automatic read have no end period, and the window joins them
    # with the next sentence: the first part gets a period, the last stays as typed, an empty cause is left out)
    from ui.trace_core import sentences
    check("tracer: sentences gives a part with no end period one when another sentence follows it, and leaves out "
          "empty parts",
          sentences(["Couldn't auto-trace this image.", "No graph grid found",
                     "Copy a new graph image and paste it here (Ctrl+V)."])
          == "Couldn't auto-trace this image. No graph grid found. Copy a new graph image and paste it here (Ctrl+V)."
          and sentences(["Axes: 20 Hz to 20 kHz, 40 to 90 dB", "", "Reading axis labels…"])
          == "Axes: 20 Hz to 20 kHz, 40 to 90 dB. Reading axis labels…"
          and sentences(["", "Detected dB labels don't match each other"]) == "Detected dB labels don't match each other"
          and sentences([]) == "")


def test_label_read_after_the_automatic_note(check):
    # (1 Axes' note of the automatic read, "Axes: … dB", has no end period: a label read that finds no labels adds
    # its sentence after a period, not run together)
    t = _tracer()
    note = t.use_labels({"token": t.label_token, "hz": None, "db": None, "seconds": 0.1, "scale": 1},
                        "Axes: 20 Hz to 20 kHz, 40 to 90 dB")
    check("tracer: a label read with no labels after the automatic read's note joins the two with a period",
          note == "Axes: 20 Hz to 20 kHz, 40 to 90 dB. Couldn't read axis labels. Enter the red and blue line values "
          "manually.", note)


def test_range_note_follows_the_range(check):
    # (a review of the text survey, 2026-11-24: the range to save snaps to 20 kHz for a frame that ends above
    # 18.5 kHz, but its note said "visible graph range" for a frame that ends below 19.9 kHz: "Save 20 Hz–20 kHz:
    # visible graph range". The frame's right side is moved; its left side is at 20 Hz)
    t = _tracer()
    k = t.calib()
    notes = {}
    for name, (lo, hi) in (("whole", (20, 20000)), ("to 18.7 kHz", (20, 18700)), ("30 Hz to 15 kHz", (30, 15000))):
        t.box.update(x0=k.x_at(lo), x1=k.x_at(hi))
        t.fit_settings()
        notes[name] = t.ta["notes"]["fmin"]
    check("tracer: the note of the range to save says “audible range” when it saves 20 Hz to 20 kHz, and “visible "
          "graph range” for a shorter range",
          notes == {"whole": "Save 20 Hz–20 kHz: audible range (covered by graph)",
                    "to 18.7 kHz": "Save 20 Hz–20 kHz: audible range (covered by graph)",
                    "30 Hz to 15 kHz": "Save 30 Hz–15 kHz: visible graph range"}, notes)


def test_your_value_ends_with_a_new_picture_as_help_says(check):
    # (a review of the text survey, 2026-11-24: Help said that the app keeps your value "for the next picture", but a
    # new picture gives the automatic values again)
    import os

    from ui import help_text_trace
    from ui.help_text_trace import SETTINGS_TRACE
    guide_file = os.path.join(os.path.dirname(help_text_trace.__file__), "guide_trace.py")  # (its words, as text)
    t = _tracer()
    t.v["tol"] = 70
    t.mark_your_value("tol")
    yours = t.is_your_value("tol")
    t.load(np.full((300, 400, 3), 255, np.uint8), "Another picture")
    body = next(i for s in SETTINGS_TRACE for i in s["items"] if i["key"] == "#tr-auto-on")["body"][0]
    with open(guide_file, encoding="utf-8") as fh:
        guide = fh.read()
    check("tracer: a value you set stops being yours with a new picture, and Help and the Guide say so",
          yours and not t.is_your_value("tol") and "until you click ↺ or open a new picture" in body
          and "next picture" not in body and "until you click ↺ or open a new picture" in guide, body)
