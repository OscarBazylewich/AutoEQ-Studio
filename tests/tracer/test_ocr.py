"""Windows' text reader (ui\\ocr.py) reading the tracer's sample graph: its axis labels read (+90 to +40 dB, the Hz
labels matching the gridlines), or, on a PC whose Windows has no text reader for its language, the tracer saying it
couldn't read them. Moved from eq_checks.py's trace_checks.

The check takes the way this PC's Windows allows, as the old one did: which way it went here is said in the test's
output. The other way, Windows without a text reader, is tried on every PC with a stand-in
(test_no_text_reader_said, added 2026-10-22: on a PC with a reader, the old check never tried it)."""
from helpers import capabilities
from ui import ocr
from ui.trace_window import sample_image

COVERS = ("ui.trace_core", "ui.eq_page")  # (the labels read into the tracer's values; the tracer opened from Make an EQ)


def test_axis_labels_read_or_said(eq_screen, check):
    page = eq_screen.page
    # (the sample graph opened in the tracer, as the old run's first trace check had it: eq_checks.py lines 2771-2775)
    img, _truth = sample_image()
    page.open_trace()
    tw = page.tracer
    t = tw.t
    tw.load_image(img, "Sample IEM")
    read = eq_screen.wait_for(lambda: not tw.reading, 60)
    try:
        ocr._get_engine()
        has_reader = True
    except ocr.Unavailable:
        has_reader = False
    ready, said = capabilities.ocr_ready()
    print("(this PC has Windows' text reader: the labels are read)" if ready else
          f"(this PC has no text reader, so the tracer says it couldn't read the labels: {said})")
    # was eq_checks.py:2785
    check("trace: the axis labels read (+90 to +40 dB; the Hz labels match the gridlines), or said when Windows has no "
          "text reader", read and ((t.v["d1"], t.v["d2"]) == ("90", "40") and "frequency labels match" in t.axis_note
                                   if has_reader else "Couldn't read" in t.axis_note), t.axis_note)


def test_no_text_reader_said(eq_screen, monkeypatch, check):
    page = eq_screen.page

    def no_reader():
        raise ocr.Unavailable("no text reader for this language (a stand-in for the test)")
    monkeypatch.setattr(ocr, "_get_engine", no_reader)  # (ocr.words asks for it each time: the reader stood in as missing)
    img, _truth = sample_image()
    page.open_trace()
    tw = page.tracer
    t = tw.t
    tw.load_image(img, "Sample IEM")
    read = eq_screen.wait_for(lambda: not tw.reading, 60)
    check("trace: with no text reader in Windows, the tracer says it couldn't read the axis labels, and why (the "
          "values are typed instead)", read and "Couldn't read the labels" in t.axis_note
          and "no text reader" in t.axis_note and "Type the values" in t.axis_note, t.axis_note)
