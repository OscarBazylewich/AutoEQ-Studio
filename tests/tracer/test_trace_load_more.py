"""More checks of the load of a picture (proposed by the verifier): an error outside Tracer.load in the thread, a tool
key while a large picture loads over a picture, and 3 Save's changes that go with a new picture."""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from helpers import qt
from ui import trace_window
from ui.trace_window import sample_image


def _large():
    img, _s = sample_image()
    return img.scaled(1600, 960, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


def test_error_outside_tracer_load(eq_screen, monkeypatch, check):
    from helpers.dialogs import DIALOGS
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    qt.wait_for(lambda: not tw.reading, 60)
    asked = len(DIALOGS.asked)
    real = trace_window.rgb_of

    def fails(q):
        if q.width() > 1500:
            raise MemoryError("stand-in")
        return real(q)
    monkeypatch.setattr(trace_window, "rgb_of", fails)
    tw.load_image(_large(), "Large graph")
    qt.wait_for(lambda: not tw.loading, 60)
    said = DIALOGS.asked[asked:]
    after = (tw.loading, tw.t.src_name, tw.stage.isEnabled(), tw.status.text() == trace_window.LOADING)
    tw.close()
    check("tracer: an error outside Tracer.load in the thread of a load: one message, the picture before stays, the "
          "tracer takes input", len(said) == 1 and "cannot open this picture" in said[0][1]
          and after == (False, "Sample IEM", True, False), (said, after))


def test_tool_key_while_loading_over_a_picture(eq_screen, check):
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    qt.wait_for(lambda: not tw.reading, 60)
    tw.load_image(_large(), "Large graph")
    tw.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_D, Qt.NoModifier))
    tool = tw.tool
    qt.wait_for(lambda: not tw.loading, 60)
    tw.close()
    check("tracer: a tool key while a large picture loads over a picture changes nothing", tool == "trace", tool)


def test_new_picture_clears_the_changes_of_3_save(eq_screen, check):
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    qt.wait_for(lambda: not tw.reading, 60)
    tw.name.setText("Mine")
    tw.name.textEdited.emit("Mine")
    was = tw.users_work()
    tw.load_image(img.copy(0, 0, 900, 600), "Another")
    qt.wait_for(lambda: not tw.reading, 60)
    now = tw.users_work()
    tw.close()
    check("tracer: a changed Name box is the user's work, and a new picture (no Remove image) clears it",
          was and not now, (was, now))
