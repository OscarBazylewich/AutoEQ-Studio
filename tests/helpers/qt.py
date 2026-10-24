"""Qt off-screen for the tests (QT_QPA_PLATFORM=offscreen: nothing shows on the screen).

app() is the process's one QApplication, made the first time it's asked for, with: the stray watch (below), the
dialogs answered by themselves (helpers.dialogs), a recorder in place of opening links and folders with Windows
(QDesktopServices.openUrl: OPENED_URLS), and a recorder of errors inside Qt call-backs.

Errors inside Qt call-backs (a slot, a timer, an event handler): PySide6 hands them to sys.excepthook and carries on.
Each one is kept in QT_ERRORS (the running test, the error's last line), logged ({"event": "qt_error"}) and passed on
to the usual hook (its traceback is still printed). The qt_error_check fixture fails the test it happened in (or the
one its module's fixtures were made for), since 2026-10-22: until then they were only noted, as in the old checks,
while the Guide's two known ones (demos reaching for a row Find… had drawn again) waited to be fixed. `reported`:
how many of QT_ERRORS have been checked.

The stray watch (the old EQ checks' rule): a control (a button, a label, a box, a bare widget or frame) shown as a
window of its own flashes on the screen: made visible before it had a parent. Windows by design (dialogs, the main
window, menus, pop-up lists, tooltips) aren't counted. The stray_check fixture fails a test in which one showed;
at the end of the session, if the watch was installed and never found one, STRAY_CHECK is logged once as ok.

Leftovers (after every test, tests\\conftest.py): a Qt object made without a parent is Python's to delete. Kept only
by a loop of references (a control whose signal was used is in one), it goes whenever Python's garbage collector
next runs, and if that's while Qt hands it or one of its parts an event, the process crashes (an access violation,
in some later test: GitHub's run of 2026-10-22). free_leftovers() runs the collector after each test, when Qt is
handling no event, deletes the Qt objects it finds and names them; the test that left them fails (LEFTOVER_CHECK).

What's drawn: picture() (a widget's picture at one pixel per point), words_start() and headings_over_words() (where a
table's headings' and cells' words start, read from the pixels: Windows 11's table look).

Small screens: on_screens() opens a window as it would open on a laptop's screen at 150 % and 175 % and on a big one
(SMALL_SCREENS, BIG_SCREEN: the room above the taskbar, stood in for what Qt says the screen has), and measures it.

PySide6 is imported inside the functions, so a test that never uses Qt never loads it.
"""
import os
import sys
import time
import traceback

from helpers import checks, dialogs, guard

STRAY_CHECK = ("ui: no control is ever shown as a window of its own (each flashed on the screen: Find…'s rows showed "
               "one Show button each while the lists loaded, 779 in a session, and each cost the window's time)")
LEFTOVER_CHECK = ("ui: no test leaves a Qt object for Python's garbage collector (it would delete it at a random "
                  "later moment, and one deleted while Qt hands it an event crashes the process: GitHub's run of "
                  "2026-10-22, a drop-down a test had made on its own)")
QT_ERRORS: list[tuple[str, str]] = []  # (the running test, the error's last line)
reported = 0                           # how many of QT_ERRORS the qt_error_check fixture has checked
OPENED_URLS: list[str] = []            # what the app asked Windows to open (a website, a folder): never opened
_made = []
_watch = []


def time_limit(sec) -> float:
    """sec, times AUTOEQSTUDIO_TIME_FACTOR (more time on a busy PC, or with several runs at once)."""
    try:
        factor = float(os.environ.get("AUTOEQSTUDIO_TIME_FACTOR", "1"))
    except ValueError:
        factor = 1.0
    return sec * (factor if factor > 0 else 1.0)


def _stray_watch_class():
    from PySide6.QtCore import QEvent, QObject, Qt
    from PySide6.QtWidgets import (QAbstractButton, QAbstractSlider, QAbstractSpinBox, QComboBox, QFrame, QLabel,
                                   QLineEdit, QProgressBar, QWidget)

    class StrayWatch(QObject):
        """Every control shown as a window of its own (eq_checks.py's watch_strays, line 1309). found: since
        clear(); seen_any: anything found, ever."""

        def __init__(self):
            super().__init__()
            self.found: list[str] = []
            self.seen_any = False

        def clear(self):
            self.found.clear()

        def eventFilter(self, obj, e):
            if e.type() == QEvent.Show and isinstance(obj, QWidget) and obj.isWindow() \
                    and not obj.windowFlags() & (Qt.Popup | Qt.ToolTip) & ~Qt.Window \
                    and (isinstance(obj, (QAbstractButton, QLabel, QLineEdit, QComboBox, QAbstractSlider,
                                          QAbstractSpinBox, QProgressBar)) or type(obj) in (QWidget, QFrame)):
                self.found.append(f"{type(obj).__name__} {getattr(obj, 'text', lambda: '')()!r}"[:60])
                self.seen_any = True
            return False
    return StrayWatch


def __getattr__(name):  # (helpers.qt.StrayWatch: the class, made when first asked for, with Qt loaded then)
    if name == "StrayWatch":
        if "StrayWatch" not in globals():
            globals()["StrayWatch"] = _stray_watch_class()
        return globals()["StrayWatch"]
    raise AttributeError(name)


def stray_watch():
    """The process's stray watch, or None: never installed (no app() yet, or a QApplication made elsewhere)."""
    return _watch[0] if _watch else None


def _excepthook(real):
    def hook(kind, value, tb):
        last = "".join(traceback.format_exception_only(kind, value)).strip().splitlines()
        text = last[-1] if last else kind.__name__
        QT_ERRORS.append((guard.current, text))
        checks.log({"event": "qt_error", "test": guard.current, "text": checks.short(text)})
        real(kind, value, tb)
    return hook


def app():
    """The process's one QApplication (made on the first call; application name "AutoEQ Studio"), with the stray
    watch, the dialogs' answers, the link recorder and the call-back error recorder installed."""
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QApplication
    qapp = QApplication.instance()
    if qapp is None:
        qapp = QApplication(["AutoEQ Studio (tests)"])
        qapp.setApplicationName("AutoEQ Studio")
    elif not isinstance(qapp, QApplication):
        raise RuntimeError("A QGuiApplication was made before the tests' QApplication (e.g. by brand_exe.icon_file): "
                           "ask for the qapp fixture first, so windows can be made in this process.")
    if not _made:
        watch = __getattr__("StrayWatch")()
        qapp.installEventFilter(watch)
        _watch.append(watch)
        dialogs.install()
        QDesktopServices.openUrl = staticmethod(lambda url: (OPENED_URLS.append(url.toString() if hasattr(
            url, "toString") else str(url)), True)[1])
        sys.excepthook = _excepthook(sys.excepthook)
        _made.append(qapp)
    return qapp


def wait_for(cond, sec=90, step=0.02) -> bool:
    """Let Qt work until cond() is true or time_limit(sec) has passed (eq_checks.py's wait_for, line 1365)."""
    from PySide6.QtWidgets import QApplication
    qapp = QApplication.instance()
    end = time.monotonic() + time_limit(sec)
    while not cond():
        if time.monotonic() >= end:
            return bool(cond())
        if qapp is not None:
            qapp.processEvents()
        time.sleep(step)
    return True


def settle(quiet=0.5, sec=30) -> bool:
    """Let Qt work until its background tasks (ui.tasks.background: Qt's thread pool) have had nothing running for
    `quiet` seconds in a row, or time_limit(sec) has passed. Whether it got quiet. "Nothing running right now" isn't
    enough: each task that ends may start the next as its answer arrives (Make an EQ: the curves, then their
    analysis, then the automatic settings)."""
    from PySide6.QtCore import QThreadPool
    pool = QThreadPool.globalInstance()
    since = [None]

    def quiet_long_enough():
        if pool.activeThreadCount():
            since[0] = None
            return False
        since[0] = since[0] or time.monotonic()
        return time.monotonic() - since[0] >= quiet
    return wait_for(quiet_long_enough, sec)


def pump(ms=50):
    """Let Qt work for this long."""
    from PySide6.QtWidgets import QApplication
    qapp = QApplication.instance()
    end = time.monotonic() + ms / 1000
    while True:
        if qapp is not None:
            qapp.processEvents()
        if time.monotonic() >= end:
            return
        time.sleep(0.005)


def close(widget):
    """Close a window or widget, delete it, and let Qt work until it's gone."""
    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent
    if widget is None or not shiboken6.isValid(widget):
        return
    widget.close()
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    wait_for(lambda: not shiboken6.isValid(widget), 5)


def free_leftovers() -> list[str]:
    """Python's garbage collector run now (tests\\conftest.py: after each test, once its fixtures are taken down, when
    Qt is handling no event), and the Qt objects among what it found deleted now, as Qt deletes (deleteLater): those
    owned by Python and kept only by a loop of references. Their names (none when Qt was never loaded here)."""
    if "shiboken6" not in sys.modules:
        return []
    import gc
    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent, QObject
    # (what Make an EQ's opening set aside from the collector, gc.freeze, looked at again: never collected, a loop of
    # references made before it would never be found, 2026-10-24)
    gc.unfreeze()
    gc.set_debug(gc.DEBUG_SAVEALL)  # (what it finds kept in gc.garbage, to look at, rather than freed at once)
    try:
        gc.collect()
        found = list(gc.garbage)
        gc.garbage.clear()
    finally:
        gc.set_debug(0)
    left = [o for o in found if isinstance(o, QObject) and shiboken6.isValid(o) and shiboken6.ownedByPython(o)]
    found.clear()  # (the rest goes back to the collector: nothing of Qt's that's still there is left in it)
    names = [_named(o) for o in left]
    for o in left:
        o.deleteLater()
    if left:
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    return names


def _named(obj) -> str:
    """A Qt object as a message names it: its class, and its name, title or first choice when it has one."""
    text = ""
    for get in ("objectName", "accessibleName", "windowTitle"):
        f = getattr(obj, get, None)
        text = f() if callable(f) else ""
        if text:
            break
    if not text and callable(getattr(obj, "itemText", None)) and obj.count():
        text = obj.itemText(0) + "…"
    return f"{type(obj).__name__} “{text}”" if text else type(obj).__name__


def light(qapp):
    """The app's light theme on the whole application."""
    from ui import theme
    theme.apply(qapp, dark=False)


def dark(qapp):
    """The app's dark theme on the whole application."""
    from ui import theme
    theme.apply(qapp, dark=True)


def picture(widget):
    """What the widget draws, as a picture at one pixel per point."""
    pm = widget.grab()
    img = pm.toImage()
    r = pm.devicePixelRatio()
    return img.scaled(round(img.width() / r), round(img.height() / r)) if r != 1 else img


def words_start(img, rect):
    """How far in from rect's left a picture's words start: the first column with a pixel far from the colour behind
    them (taken at rect's left edge, half-way down); None without words."""
    back = img.pixelColor(rect.left() + 1, rect.center().y())
    for x in range(rect.left(), rect.right() + 1):
        for y in range(rect.top() + 2, rect.bottom() - 1):
            c = img.pixelColor(x, y)
            if max(abs(c.red() - back.red()), abs(c.green() - back.green()), abs(c.blue() - back.blue())) > 80:
                return x - rect.left()
    return None


def headings_over_words(table, cols):
    """For each of a table's columns cols: (where its heading's words start, where its first row's words start), each
    from the column's left, as drawn now (Windows 11's table look has each heading over its words, at the left)."""
    from PySide6.QtCore import QRect
    h = table.horizontalHeader()
    head, cells = picture(h), picture(table.viewport())
    out = []
    for c in cols:
        x = h.sectionViewportPosition(c)
        out.append((words_start(head, QRect(x, 0, h.sectionSize(c), h.height())),
                    words_start(cells, table.visualItemRect(table.item(0, c)))))
    return out


# The room above the taskbar Qt says a 1920 x 1080 laptop's screen has at 150 % and 175 %, and a big screen's; a
# window's title bar (about 32 px at 150 %) comes on top of its own size
SMALL_SCREENS = ((1280, 672), (1097, 569))
BIG_SCREEN = (1920, 1032)
TITLE_BAR = 32


def on_screens(monkeypatch, make, screens=SMALL_SCREENS + (BIG_SCREEN,)):
    """Each window make() returns, made and shown with a screen of each size stood in (the room Qt says it has above
    the taskbar), measured as it opened: {(screen's width, height): {"opens": its size, "needs": what its parts need
    at their smallest, "smallest": the smallest it can be made, "fits": within the screen's room with its title bar,
    its smallest size too, and its parts not squeezed}}. Each window is closed after; Qt's own screen is put back."""
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QScreen
    real, seen = QScreen.availableGeometry, {}
    try:
        for width, height in screens:
            monkeypatch.setattr(QScreen, "availableGeometry", lambda self, w=width, h=height: QRect(0, 0, w, h))
            win = make()
            try:
                win.show()
                pump(150)
                opens, needs = win.size().toTuple(), win.minimumSizeHint().toTuple()
                smallest = (win.minimumWidth(), win.minimumHeight())
                seen[(width, height)] = {
                    "opens": opens, "needs": needs, "smallest": smallest,
                    "fits": opens[0] <= width and opens[1] + TITLE_BAR <= height and smallest[0] <= width
                    and smallest[1] + TITLE_BAR <= height and opens[0] >= needs[0] and opens[1] >= needs[1]}
            finally:
                close(win)
    finally:
        monkeypatch.setattr(QScreen, "availableGeometry", real)
    return seen
