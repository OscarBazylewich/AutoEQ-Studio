"""What the window's tests (tests\\ui) share: a stand-in for the app the window talks to, the window itself on
Devices (with a stand-in Equalizer APO folder and two stand-in devices), and the same window after Set up.

devices_window  the window as the old self-test made it (selftest.py lines 336-363): a stand-in APO folder
                (helpers.apo.fake_apo: config.txt including EarPods.txt, Samson.txt's line off), two devices (the
                headset "{5}" playing, without APO on it, and earbuds "{1}" away, with APO), a Switcher on them, and
                the window shown on Devices. One per test file (module scope): a file's tests go through it in the
                order they're written, as the old checks went through one window; no file ever sees another's.
set_up_window   the same window after Set up (selftest.py lines 377-393): the Set up dialog made and its OK pressed,
                with EQ Switcher's side stood in (its Start with Windows entry and its running copy: never this PC's
                Run key or a running EQ Switcher) and any warning answered. Then the window's own questions to APO
                are let finish, so every test starts from a quiet window. After it: profiles EarPods and Samson,
                EarPods on the playing device, APO set up.

themed_window   the code that makes the same window, with the app's theme applied, in a Python of its own: for the
                checks of how the window and its screens look (THEMED_WINDOW below).
shapes          a few lines for such a Python that read a shape off a picture: a pixel clearly not the background,
                the box of those, whether a shape is open on a chevron's side, the runs of inked columns (SHAPES).
stub_app        a stand-in for the app the window talks to, for a test that makes windows of its own (StubApp).

Each window is closed and deleted when its file is done (helpers.qt.close), once the questions it asked APO (in the
background) have their answers. No theme is applied here: the old self-test drew these screens unthemed, and the
accessibility test counts on that (tests that need the theme apply it in a Python of their own: themed_window).
"""
import dataclasses
import os

import pytest

from helpers import apo, qt

KEY = "Headset|EarPods"  # (the playing device, as the Switcher names it)

# The window on the stand-in devices (the headset "{5}" playing, without APO on it; earbuds "{1}" away) in a Python of
# its own, in the app's theme: dark, with Windows' default blue (stood in: this PC's accent never decides a check).
# argv: the app's copy, the test's folder (holding apo\config: the fake_apo fixture, not set up for AutoEQ Studio, so
# the banner shows). A test adds its own lines after it, which can use qapp, theme, t (the colours in use), sw, win
# (shown on Devices), top, conf, KEY and json, and prints one JSON line (helpers.subproc.run_python's data).
THEMED_WINDOW = r'''
import json, os, sys
sys.path.insert(0, sys.argv[1])
top = sys.argv[2]
from PySide6.QtWidgets import QApplication
qapp = QApplication.instance() or QApplication([])
from switcher import core
from switcher import devices as D
from switcher.apo import Apo
from ui import theme, theme_tokens
theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT
theme.apply(qapp, dark=True, contrast=False)
t = theme.tokens()


class Stub:  # (what the window asks of the app)
    hotkey_problem = ""

    def tray_message(self, title, text):
        pass

    @staticmethod
    def autostart_on():
        return False

    def set_autostart(self, on):
        pass

    @staticmethod
    def set_offline(on):
        import net
        net.set_offline(on)


KEY = "Headset|EarPods"
conf = os.path.join(top, "apo", "config")
eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, False),
       D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)]
sw = core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
sw.s["page"] = "devices"
from ui.window import Window
win = Window(sw, Stub())
win.resize(1180, 900)
win.show()
for _ in range(5):
    qapp.processEvents()
'''


# Reading a shape off a picture (a QImage), in a test's Python of its own: differs(colour, background) for a pixel
# clearly not the background (the shape's own, not its edge's faint blend); ink_box(img, x0, y0, x1, y1, background)
# the box [left, top, right, bottom] of those in a part of the picture (None: none); open_side(img, box, background,
# way) whether the shape in the box is open where a chevron is (way "right", ">": at its left middle; "down", "v": at
# its top middle), as a filled triangle (Qt's own arrows) isn't; runs(img, x0, x1, y0, y1, background) the stretches
# [(first, last)] of columns with ink in them, left to right (a button's words, then its chevron).
SHAPES = r'''
def differs(c, bg):
    return sum(abs(a - b) for a, b in zip(c.getRgb()[:3], bg.getRgb()[:3])) > 60


def ink_box(img, x0, y0, x1, y1, bg):
    pts = [(x, y) for x in range(max(0, x0), min(img.width(), x1)) for y in range(max(0, y0), min(img.height(), y1))
           if differs(img.pixelColor(x, y), bg)]
    return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)] if pts \
        else None


def open_side(img, box, bg, way):
    if box is None:
        return None
    x, y = (box[0] + 1, (box[1] + box[3]) // 2) if way == "right" else ((box[0] + box[2]) // 2, box[1] + 1)
    return not differs(img.pixelColor(x, y), bg)


def runs(img, x0, x1, y0, y1, bg):
    found, start = [], None
    for x in range(x0, x1 + 1):
        on = x < x1 and any(differs(img.pixelColor(x, y), bg) for y in range(y0, y1))
        if on and start is None:
            start = x
        elif not on and start is not None:
            found.append((start, x - 1))
            start = None
    return found
'''


class StubApp:
    """What the window asks of the app (selftest.py's Stub, lines 340-357). Each one has its own list of what it
    said in the tray (the old one's list belonged to the class, shared by every stand-in)."""

    hotkey_problem = ""

    def __init__(self):
        self.said = []

    def tray_message(self, title, text):
        self.said.append(title)

    @staticmethod
    def autostart_on():
        return False  # (never this PC's Run key)

    def set_autostart(self, on):
        pass

    @staticmethod
    def set_offline(on):
        import net
        net.set_offline(on)


@dataclasses.dataclass
class DevicesWindow:
    """One test file's window and what it was made with."""
    win: object            # the window (ui.window.Window), shown on Devices
    sw: object             # its Switcher (switcher.core.Switcher)
    app: StubApp           # the stand-in app the window talks to
    top: str               # this file's own folder (inside the test session's folder)
    conf: str              # the stand-in Equalizer APO config folder
    settings: str          # the Switcher's settings file
    eps: list              # the two stand-in endpoints
    key: str = KEY         # the playing device
    offered: tuple = None  # after Set up: (EQ Switcher's Start with Windows offered ticked, quitting it offered ticked)
    done_es: list = None   # after Set up: what the EQ Switcher stand-ins were asked to do, in order
    warnings: list = None  # after Set up: what it said in a warning box (answered OK)

    def switcher(self):
        """Another Switcher on the same settings file and APO folder: as at the app's next start."""
        from switcher import core
        from switcher.apo import Apo
        return core.Switcher(self.settings, Apo(self.conf), endpoints=lambda: self.eps, playing=lambda: "{5}")


def _take_down(w):
    """The window's questions to APO answered (they run in the background), then the window closed and deleted."""
    import shiboken6
    from PySide6.QtCore import QThreadPool
    if shiboken6.isValid(w.win):
        qt.wait_for(lambda: not w.win._checking, 30)
    QThreadPool.globalInstance().waitForDone(int(qt.time_limit(30) * 1000))
    qt.pump(50)  # (their answers delivered while the window is still there)
    qt.close(w.win)


@pytest.fixture
def themed_window():
    """THEMED_WINDOW: a test runs it with its own lines added, through helpers.subproc.run_python(code,
    session.SESSION.app, str(tmp_path)), with the fake_apo fixture in the same test."""
    return THEMED_WINDOW


@pytest.fixture
def shapes():
    """SHAPES: lines a test's own Python adds after its imports, to read shapes off its pictures."""
    return SHAPES


@pytest.fixture
def stub_app():
    """A stand-in for the app a window talks to (StubApp), for a test that makes windows of its own."""
    return StubApp()


@pytest.fixture(scope="module")
def devices_window(qapp, tmp_path_factory):
    from switcher import core
    from switcher import devices as D
    from switcher.apo import Apo
    from ui.window import Window
    top = str(tmp_path_factory.mktemp("window"))
    conf = apo.fake_apo(top)
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, False),
           D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)]
    settings = os.path.join(top, "s.json")
    sw = core.Switcher(settings, Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    stub = StubApp()
    sw.s["page"] = "devices"  # (Make an EQ has tests of its own: tests\eq_screen)
    w = DevicesWindow(Window(sw, stub), sw, stub, top, conf, settings, eps)
    try:
        w.win.show()
        qapp.processEvents()
        yield w
    finally:
        _take_down(w)


@pytest.fixture(scope="module")
def set_up_window(devices_window, qapp):
    from PySide6.QtWidgets import QMessageBox
    from ui import winsys
    from ui.window import SetUpDialog
    w = devices_window
    done_es, warnings = [], []
    with pytest.MonkeyPatch.context() as mp:
        # (Set up takes over from EQ Switcher: stand-ins, never this PC's Run key or a running EQ Switcher. Without
        # them Set up would delete EQ Switcher's real Start with Windows entry and ask a running one to quit.)
        mp.setattr(winsys, "eq_switcher_autostart", lambda: True)
        mp.setattr(winsys, "eq_switcher_running", lambda: True)
        mp.setattr(winsys, "eq_switcher_autostart_off", lambda: done_es.append("Start with Windows off"))
        mp.setattr(winsys, "eq_switcher_quit", lambda wait=2.0: done_es.append("quit") or True)
        # (a problem is said in a warning box: answered here, and kept for the tests' details)
        mp.setattr(QMessageBox, "warning", staticmethod(
            lambda *a, **k: warnings.append(a[2] if len(a) > 2 else k.get("text", "")) or QMessageBox.Ok))
        dlg = SetUpDialog(w.sw, w.win)
        w.offered = (dlg.chk_es_auto is not None and dlg.chk_es_auto.isChecked(),
                     dlg.chk_es_quit is not None and dlg.chk_es_quit.isChecked())
        dlg._go()  # (its Set up button's action)
    qapp.processEvents()
    w.done_es, w.warnings = done_es, warnings
    qt.wait_for(lambda: not w.win._checking, 30)  # (the device's line asked APO by itself: its answer is in)
    return w
