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
          "text reader", read and ((t.v["d1"], t.v["d2"]) == ("90", "40") and "frequency labels agree with the grid lines" in t.axis_note
                                   if has_reader else "The app cannot read" in t.axis_note), t.axis_note)


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
          "values are typed instead)", read and "The app cannot read the labels" in t.axis_note
          and "no text reader" in t.axis_note and "Type the values" in t.axis_note, t.axis_note)


def test_one_read_at_a_time(monkeypatch, check):
    """Windows' text reader does one read at a time: a second read while one runs fails ("Another RecognizeAsync
    operation is already running!": the automatic read of a picture from a website and the label read of a pasted
    picture can come at the same time). ocr.words lets one read run at a time. A stand-in for the reader's call fails
    in the same way when two calls overlap (the real reader is not used: the same test on each PC)."""
    import asyncio
    import threading

    import numpy as np
    state = {"now": 0, "most": 0}
    count = threading.Lock()

    async def stand_in(rgb):
        with count:
            state["now"] += 1
            state["most"] = max(state["most"], state["now"])
            overlap = state["now"] > 1
        try:
            if overlap:
                raise OSError("Another RecognizeAsync operation is already running!")
            await asyncio.sleep(0.05)
            return [{"text": "90", "x0": 0, "y0": 0, "x1": 10, "y1": 10}]
        finally:
            with count:
                state["now"] -= 1
    monkeypatch.setattr(ocr, "_get_engine", lambda: None)
    monkeypatch.setattr(ocr, "_read", stand_in)
    rgb = np.full((60, 80, 3), 255, np.uint8)
    n = 6
    start, res = threading.Barrier(n), [None] * n

    def work(i):
        start.wait()
        try:
            res[i] = len(ocr.words(rgb))
        except OSError as e:
            res[i] = str(e)
    threads = [threading.Thread(target=work, args=(i,)) for i in range(n)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(30)
    check("trace: reads of the text reader from 6 threads at the same time run one after the other (no read fails "
          "because a different read runs)", res == [1] * n and state["most"] == 1, (res, state))
