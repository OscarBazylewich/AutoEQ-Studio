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

Layout items (app\\ui\\__init__.py says why the app makes no Python object for one): app() watches the calls that
give a layout to another layout (LAYOUT_CALLS). A call from app\\ or tests\\ that gives a layout with items to a layout
in a window is kept in LAYOUT_BREAKS (the running test, the file and line, the call; for a call through ui.placed, the
line that called placed), and the layout_rule_check fixture fails the test it happened in, naming the line
(LAYOUT_RULE_CHECK); take_layout_breaks() takes them, for a test that breaks the rule on purpose. After each test
(tests\\conftest.py), made_item_objects() finds every Python object that PySide6 made for a layout item (not the app's
own layouts' items), whatever made it (a layout given with items, addItem, insertItem, a Python call of itemAt): the
test fails (ITEM_OBJECT_CHECK) and they are forgotten (forget_items()), so the next tests start clean.
stale_layout_items() tells which of them no layout holds any more; layout_item_objects() counts all of them, the app's
own layouts' items too; layout_parts() tells what a layout holds, in its order, without making one (a test's way
instead of itemAt).

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
LAYOUT_RULE_CHECK = ("ui: a layout that has items is never given to a layout that is in a window (PySide6 then keeps a "
                     "Python object for each of its items; Qt can delete an item without telling PySide6, and a new "
                     "Qt object at the same address got the old object: the tests crashed, an access violation, "
                     "2026-11-15)")
ITEM_OBJECT_CHECK = ("ui: no test leaves a Python object that PySide6 made for a layout item (Qt can delete such an "
                     "item without telling PySide6, and a new Qt object at the same address then gets the old object: "
                     "the process crashes, an access violation, 2026-11-15)")
# (the calls that give a layout to another layout, as (class, method), watched for the app's rule: a layout goes in
# empty. For the QBoxLayout and QGridLayout calls, PySide6 6.11's glue (addLayoutOwnership) makes a Python object for
# each item of a layout with items when the receiving layout has a parent widget; for the three QFormLayout calls it
# makes none (measured: 0), they are watched for the rule only. addItem is not watched: it is virtual, and a Python
# function put on QBoxLayout.addItem or QGridLayout.addItem makes Qt's own calls of it (QLayout::addWidget on a layout
# made from Python) go through Python, which makes an object for each item they add (measured, 2026-11-16: 2 objects
# for 2 such calls, 0 without the function). The check after each test (ITEM_OBJECT_CHECK) finds what addItem makes.)
LAYOUT_CALLS = (("QBoxLayout", "addLayout"), ("QBoxLayout", "insertLayout"), ("QBoxLayout", "insertItem"),
                ("QGridLayout", "addLayout"), ("QFormLayout", "addRow"), ("QFormLayout", "insertRow"),
                ("QFormLayout", "setLayout"))
QT_ERRORS: list[tuple[str, str]] = []  # (the running test, the error's last line)
reported = 0                           # how many of QT_ERRORS the qt_error_check fixture has checked
LAYOUT_BREAKS: list[tuple[str, str]] = []  # (the running test, "file:line Class.method" of a call that broke the rule)
layout_reported = 0                        # how many of LAYOUT_BREAKS have been taken (take_layout_breaks)
OPENED_URLS: list[str] = []            # what the app asked Windows to open (a website, a folder): never opened
_made = []
_watch = []
_plain = {}  # (the font and colours of the QApplication as it was made, for no_theme)


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


def _code_place(frame):
    """Where a frame's code is, as "app/ui/x.py:12" or "tests/ui/test_x.py:34" (the app's code runs from the session's
    copy); None for code outside app\\ and tests\\ (Python's own, PySide6, pyqtgraph)."""
    from helpers import paths as project
    from helpers import session
    path = os.path.realpath(frame.f_code.co_filename)
    roots = [(project.TESTS, "tests"), (project.PROJECT_APP, "app")]
    if session.SESSION is not None:
        roots.insert(0, (session.SESSION.app, "app"))
    for root, name in roots:
        root = os.path.realpath(root)
        if os.path.normcase(path).startswith(os.path.normcase(root) + os.sep):
            return f"{name}/{os.path.relpath(path, root).replace(os.sep, '/')}:{frame.f_lineno}"
    return None


def _watched(real, method):
    """real (a layout's call that takes a layout) with the rule kept in LAYOUT_BREAKS: the given layout has items and
    the receiving one has a parent widget."""
    from PySide6.QtWidgets import QLayout

    def call(self, *args, **kw):
        sub = next((a for a in (*args, *kw.values()) if isinstance(a, QLayout)), None)
        if sub is not None and sub.count() and self.parentWidget() is not None:
            frame = sys._getframe(1)
            if frame.f_code.co_name == "placed" and (_code_place(frame) or "").startswith("app/ui/__init__.py:"):
                frame = frame.f_back  # (through ui.placed: the line that called it is the one to change)
            where = _code_place(frame)
            if where is not None:  # (only the project's own code: it is the code that can change)
                LAYOUT_BREAKS.append((guard.current, f"{where} {method}"))
        return real(self, *args, **kw)
    call.__doc__ = getattr(real, "__doc__", None)
    return call


def _watch_layout_calls():
    from PySide6 import QtWidgets
    for cls_name, name in LAYOUT_CALLS:
        cls = getattr(QtWidgets, cls_name)
        setattr(cls, name, _watched(getattr(cls, name), f"{cls_name}.{name}"))


def take_layout_breaks() -> list[tuple[str, str]]:
    """The calls that broke the layout rule since the last look, taken: layout_rule_check then does not fail the test
    for them (a test that breaks the rule on purpose looks at them with this)."""
    global layout_reported
    new = LAYOUT_BREAKS[layout_reported:]
    layout_reported = len(LAYOUT_BREAKS)
    return new


class _Kinds(dict):
    """A class's kind for _scan: "item" (a layout item that is not a layout), "own" (one of the app's own layout
    classes: an itemAt of their own, in Python), "qt" (a layout class of Qt's), or None. Worked out once for each
    class, at its first look-up."""

    def __missing__(self, cls):
        import types

        from PySide6.QtWidgets import QLayout, QLayoutItem
        if issubclass(cls, QLayout):
            kind = "own" if isinstance(getattr(cls, "itemAt", None), types.FunctionType) else "qt"
        else:
            kind = "item" if issubclass(cls, QLayoutItem) else None
        self[cls] = kind
        return kind


_KINDS = _Kinds()


def _scan():
    """From PySide6's list of its objects: (the layout item objects that Qt made and owns, the app's own layouts, Qt's
    layouts). The layouts and items are picked out by C code (map and compress: no Python loop over every object),
    so with 22,000 objects it takes about 5 ms, most of it for PySide6's own list."""
    from itertools import compress

    import shiboken6
    every = shiboken6.getAllValidWrappers()
    pick = {"item": [], "own": [], "qt": []}
    for o in compress(every, map(_KINDS.__getitem__, map(type, every))):
        pick[_KINDS[type(o)]].append(o)
    # (an item made from Python, as pyqtgraph's menus make a QSpacerItem, is left out: its delete tells PySide6)
    items = [o for o in pick["item"] if not shiboken6.ownedByPython(o) and not shiboken6.createdByPython(o)]
    return items, pick["own"], pick["qt"]


def layout_item_objects() -> list:
    """The Python objects of layout items that Qt made and owns (not the layouts: a layout is an item too). Their
    methods are never called: an item can be deleted already."""
    return _scan()[0] if "shiboken6" in sys.modules else []


def _not_own(items, own):
    """items, but those that the app's own layouts hold (they get each item from Qt as a Python object and keep it:
    read from their own itemAt, which makes nothing)."""
    held = {id(lay.itemAt(i)) for lay in own for i in range(lay.count())}
    return [it for it in items if id(it) not in held]


def made_item_objects() -> list:
    """The layout item objects (layout_item_objects) that PySide6 made, not the app's own layouts' items: what a layout
    with items given to a layout in a window, or a Python call of QLayout.itemAt, leaves."""
    if "shiboken6" not in sys.modules:
        return []
    items, own, _layouts = _scan()
    return _not_own(items, own) if items else []


def stale_layout_items() -> list:
    """The layout item objects that PySide6 made (made_item_objects) and that no layout holds now: Qt deleted their
    items (moved or deleted widgets) and PySide6 was not told."""
    return in_no_layout(made_item_objects())


def in_no_layout(items) -> list:
    """The ones of items (made_item_objects) that no layout of Qt's holds: looked for with QLayout.indexOf, which
    only compares addresses (it never reads a deleted item). (An address that Qt gave at once to a new item of a live
    layout is not seen: the check after each test fails on every made object, stale or not.)"""
    if not items:
        return []
    _items, _own, layouts = _scan()
    return [it for it in items if not any(lay.indexOf(it) >= 0 for lay in layouts)]


def layout_parts(lay, among=None) -> list:
    """What a layout holds, in its order: the widget or the layout at each place, None for a stretch or a spacing.
    Found with QLayout.indexOf among the widgets under the layout's widget (or among) and the layouts in it: unlike
    QLayout.itemAt, it makes no Python object for an item (app\\ui\\__init__.py says why that matters)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLayout, QWidget
    out = [None] * lay.count()
    if among is None:
        host = lay.parentWidget()
        among = host.findChildren(QWidget) if host is not None else []
    for part in [*among, *lay.findChildren(QLayout, options=Qt.FindChildOption.FindDirectChildrenOnly)]:
        i = lay.indexOf(part)
        if 0 <= i < len(out):
            out[i] = part
    return out


def forget_items(items):
    """PySide6 told to forget these objects (shiboken6.invalidate: no Qt object is read, and an item that still lives
    stays in its layout, deleted by Qt as before: measured, 2026-11-16), so a new Qt object at one of their addresses
    gets a new Python object. Returns their class names. Nothing is imported when there are none: a test process that
    never uses Qt never loads it."""
    if not items:
        return []
    import shiboken6
    names = [type(o).__name__ for o in items]
    for o in items:
        shiboken6.invalidate(o)
    return names


def app():
    """The process's one QApplication (made on the first call; application name "AutoEQ Studio"), with the stray
    watch, the dialogs' answers, the link recorder, the call-back error recorder and the watch on the layout calls
    installed."""
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QApplication
    qapp = QApplication.instance()
    if qapp is None:
        qapp = QApplication(["AutoEQ Studio (tests)"])
        qapp.setApplicationName("AutoEQ Studio")
    elif not isinstance(qapp, QApplication):
        raise RuntimeError("A QGuiApplication was made before the tests' QApplication (e.g. by brand_exe.write_icon_file): "
                           "ask for the qapp fixture first, so windows can be made in this process.")
    if not _made:
        watch = __getattr__("StrayWatch")()
        qapp.installEventFilter(watch)
        _watch.append(watch)
        dialogs.install()
        QDesktopServices.openUrl = staticmethod(lambda url: (OPENED_URLS.append(url.toString() if hasattr(
            url, "toString") else str(url)), True)[1])
        sys.excepthook = _excepthook(sys.excepthook)
        _watch_layout_calls()
        if not qapp.styleSheet():
            _plain.update(font=qapp.font(), palette=qapp.palette())
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


def no_theme(qapp=None):
    """The application back to how it draws before the app's theme is applied (ui.theme.apply): no stylesheet, the
    font and the colours it was made with. Nothing when no QApplication is made yet or no theme is on it. A theme
    stays on the application for the whole process: a part of the tests that measures plain windows (tests\\ui) calls
    this before each file, so its sizes are the same whatever ran before it in the process (with the theme's font and
    padding, every control is wider). What the theme keeps beside these stays: its names for a screen reader and its
    focus frame, and the colours ui.theme.tokens() gives."""
    if qapp is None:
        if "PySide6.QtWidgets" not in sys.modules:
            return
        from PySide6.QtWidgets import QApplication
        qapp = QApplication.instance()
    if not _plain or qapp is None or not qapp.styleSheet():
        return
    qapp.setStyleSheet("")
    qapp.setFont(_plain["font"])
    qapp.setPalette(_plain["palette"])


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
