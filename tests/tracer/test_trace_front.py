"""The tracer comes to the front when a picture comes or the user opens it (ui\\eq_page_files.py's open_trace): a
minimized tracer is not minimized after Trace a graph image…, a picture pasted on the Make an EQ page and a picture
from a website, and a maximized tracer comes back maximized. (2026-11-11, a trial on the real desktop: the minimized
tracer stayed minimized when a new picture from a website came.)"""
import numpy as np
from PySide6.QtCore import Qt

from helpers import qt
from ui import trace_core
from ui.trace_window import sample_image

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_core", "ui.ocr", "ui.eq_page", "ui.eq_page_files", "eq.service", "eq.inputs")


def _stand_in_read(rgb, ocr_words=None, jpeg=False, name="Traced graph"):
    """The automatic read stood in: a read that was not OK (fast, with no text reader)."""
    from ui import trace_auto
    t = trace_core.Tracer()
    t.load(np.array(rgb, np.uint8, copy=True), name, jpeg)
    return trace_auto.AutoRead(False, t, [trace_auto.Check("trace_curve", False, "No curve.")], None, None, None,
                               None, None, 0.01)


def _ways(page, monkeypatch):
    """The three ways that bring the tracer to the front: Trace a graph image…, a picture pasted on the page, a
    picture from a website (after the wait window)."""
    from PySide6.QtWidgets import QApplication
    monkeypatch.setattr(trace_core, "auto_read", _stand_in_read)
    img, _s = sample_image()

    def button():
        page.trace_btn.click()

    def paste():
        QApplication.clipboard().setImage(img.copy(0, 0, 1000, 700))
        page.paste_picture()
        QApplication.clipboard().clear()

    def website():
        entry = {"name": "Gate", "tag": "Site 1", "site": "Site", "link": "https://example.invalid/x"}
        page._picture_from_website(entry, img.copy(0, 0, 1100, 700), False)
    return {"Trace a graph image…": button, "a paste on the page": paste, "a picture from a website": website}


def _settled(tw):
    return qt.wait_for(lambda: not tw.loading and not tw.reading_graph and not getattr(tw, "reading", False), 60)


def test_minimized_tracer_comes_to_the_front(eq_screen, monkeypatch, check):
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    seen = {}
    for name, way in _ways(page, monkeypatch).items():
        for maximized in (False, True):
            tw.showMaximized() if maximized else tw.showNormal()
            qt.pump(50)
            tw.setWindowState(tw.windowState() | Qt.WindowMinimized)
            qt.pump(50)
            was = tw.isMinimized()
            way()
            qt.pump(50)
            _settled(tw)
            seen[(name, maximized)] = (was, tw.isMinimized(), tw.isVisible(),
                                       bool(tw.windowState() & Qt.WindowMaximized))
            tw.remove_image()
    tw.showNormal()
    tw.close()
    check("tracer: a minimized tracer is not minimized and is in view after each way that brings it to the front",
          all(v[:3] == (True, False, True) for v in seen.values()), seen)
    check("tracer: a maximized tracer that was minimized comes back maximized; a usual one, not maximized",
          all(v[3] == maximized for (_n, maximized), v in seen.items()), seen)
