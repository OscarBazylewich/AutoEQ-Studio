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
