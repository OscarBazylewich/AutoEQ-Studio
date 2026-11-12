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


def _old_background(px):
    """Tracer.background as it was before 2026-11-12 (keys in int32 from a copy of the picture >> 4), to compare."""
    import math

    import numpy as np
    h, w = px.shape[:2]
    step = max(1, int(math.sqrt(w * h / 250000)))
    s = px[::step, ::step].reshape(-1, 3)
    if not len(s):
        return (255, 255, 255)
    q = s >> 4
    keys = q[:, 0].astype(np.int32) << 8 | q[:, 1].astype(np.int32) << 4 | q[:, 2]
    count = np.bincount(keys)
    k = count.argmax()
    here = keys == k
    return tuple(int(math.floor(int(np.add.reduce(s[:, i], where=here, dtype=np.int64)) / count[k] + 0.5))
                 for i in range(3))


def test_background_as_the_old_formula(check):
    # (2026-11-12: the keys of background are made in place, a channel at a time; a key from a wrong channel passed
    # every test. Random pictures, also with a most common colour and noise, and sizes that skip pixels)
    import numpy as np
    from ui import trace_core
    rng = np.random.default_rng(20261112)
    bad = []
    for n in range(40):
        h, w = (int(rng.integers(1, 60)), int(rng.integers(1, 60))) if n < 20 else (int(rng.integers(500, 1300)),
                                                                                    int(rng.integers(500, 1300)))
        px = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
        if n % 2:  # (a background colour on most pixels, with noise of a few levels)
            base = rng.integers(0, 256, 3)
            noise = rng.integers(-6, 7, (h, w, 3))
            keep = rng.random((h, w)) < 0.7
            px[keep] = np.clip(base + noise[keep], 0, 255).astype(np.uint8)
        t = trace_core.Tracer()
        t.px, t.H, t.W = px, h, w
        got, want = t.background(), _old_background(px)
        if got != want:
            bad.append((n, h, w, got, want))
    check("tracer: background gives the same colour as the old formula on 40 random pictures (with and without a most "
          "common colour, small and large)", not bad, bad[:5])
