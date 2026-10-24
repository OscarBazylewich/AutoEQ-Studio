"""Make an EQ's code loaded ahead, off the window's thread (2026-10-24: the click imported it on the window's thread
and froze the window for 0.5-2 s). The window's thread is the only one that calls these.

start(delay_ms)   begin, after delay_ms (again: nothing more, except that a start still waiting is hurried by a
                  shorter delay)
ready()           the screen's code is imported (or its import failed: error())
error()           the exception its import ended with (the window then imports on its own thread, as before, so
                  the error shows as it did)
when_ready(fn)    fn() on the window's thread once ready (at once when it is; it starts the loading if it hasn't)
hold(), release() pause and resume the background import between modules while the window's thread builds the
                  screen (Python's lock shared with it made each build step about twice as long); release() for each
                  hold()

How, in order:
1. On the window's thread, a few at a time (40 names a turn of the event loop, a few ms each): every class of the Qt
   modules loaded (QtCore, QtGui, QtWidgets, and any other the app has loaded already) is made. PySide6 (6.11) makes
   each class the first time it's asked for, and two threads making the same one at once corrupted memory (a crash in
   5 of 5 stress runs, 2026-10-24); pyqtgraph's import asks for every one of them.
2. A thread of its own (a daemon: quitting never waits for it) imports, Python switching threads every 1 ms meanwhile
   (at the usual 5 ms the window waited up to ~30 ms at a time for Python's lock), then as before:
   - the screen's code: numpy, pyqtgraph, ui.eq_page and the parts its page loads;
   - the EQ part (eq.service and what it loads), only when no files of yours wait to be moved: eq.paths and
     eq.library take your files' folders as they're imported, and the move offered as Make an EQ first opens
     (ui\\your_files.py) may change them;
   then ready(), said on the window's thread;
   - then, in short steps (each a moment to pause in), what the opening loads next in its own background work: V8
     for the curves (py_mini_racer), and SciPy's parts the automatic settings use.
Importing these makes no Qt object (tests\\ui\\test_preload.py checks it): one made in that thread would belong to
it, not to the window's. Nothing here loads anything until start() (the tray stays light: the window starts it only
while it's open, ui\\window.py).
"""
import importlib
import sys
import threading

from PySide6.QtCore import QObject, QTimer, Signal

THREAD_NAME = "Make an EQ's code"  # (the background import's thread, by this name)
PER_TURN = 40                      # (Qt's class names made in one turn of the window's event loop)
SCREEN = ("numpy", "pyqtgraph", "ui.eq_page", "ui.eq_settings", "ui.listen", "ui.filter_editor", "ui.your_files")
EQ_PART = ("eq.bring_over", "eq.databases", "eq.library", "eq.settings", "eq.service")
# (in the order the opening asks for them: V8 for the curves first, then SciPy for their analysis)
LATER = ("py_mini_racer", "scipy.linalg", "scipy.special", "scipy.fft", "scipy.spatial", "scipy.interpolate",
         "scipy.ndimage", "scipy.stats", "scipy.signal")

_state = {"held": 0, "started": False, "ready": False, "error": None, "names": None, "made": 0}
_go = threading.Event()  # (set: the import goes on; cleared while held)
_go.set()
_waiting = []            # (when_ready's functions, until it's ready)
_qt = {}                 # (start's timer and the messenger: kept here, on the window's thread)


class _Messenger(QObject):
    """Says on the window's thread that the import is done (a signal sent from the import's thread is delivered on
    the thread the messenger belongs to, as ui\\tasks.py's)."""
    done = Signal(object)  # (the error, or None)


def start(delay_ms=0):
    """Begin after delay_ms (the window's thread only). Again: nothing more, except that a start still waiting
    begins sooner when asked for sooner (Make an EQ clicked while the window's own wait runs)."""
    delay = max(0, int(delay_ms))
    if _state["started"]:
        timer = _qt.get("timer")
        if timer is not None and timer.isActive() and delay < timer.remainingTime():
            timer.start(delay)
        return
    _state["started"] = True
    messenger = _Messenger()
    messenger.done.connect(_on_ready)
    timer = QTimer(singleShot=True, interval=delay, timeout=_make_classes)
    _qt.update(messenger=messenger, timer=timer)
    timer.start()


def ready():
    return _state["ready"]


def error():
    return _state["error"]


def when_ready(fn):
    if _state["ready"]:
        fn()
        return
    _waiting.append(fn)
    start()


def hold():
    _state["held"] += 1
    _go.clear()


def release():
    _state["held"] = max(0, _state["held"] - 1)
    if not _state["held"]:
        _go.set()


def _qt_modules():
    """The Qt modules whose classes are made first: QtCore, QtGui and QtWidgets, and any other loaded already (the
    window's thread may use those too while the thread imports)."""
    from PySide6 import QtCore, QtGui, QtWidgets
    mods = [QtCore, QtGui, QtWidgets]
    for name in sorted(list(sys.modules)):  # (a copy: another thread may import meanwhile)
        mod = sys.modules.get(name)
        if name.startswith("PySide6.Qt") and name.count(".") == 1 and mod is not None and mod not in mods:
            mods.append(mod)
    return mods


def _make_classes():
    """Step 1, a slice per turn of the window's event loop; the thread started after the last one."""
    try:
        if _state["names"] is None:
            _state["names"] = [(mod, name) for mod in _qt_modules() for name in dir(mod)]
        names, i = _state["names"], _state["made"]
        for mod, name in names[i:i + PER_TURN]:
            try:
                getattr(mod, name, None)
            except Exception:  # noqa: BLE001 - (a name Qt can't make here: nobody can use it, on any thread)
                pass
        _state["made"] = i + PER_TURN
        if _state["made"] < len(names):
            QTimer.singleShot(0, _make_classes)  # (the window answers between slices)
            return
        threading.Thread(target=_load, name=THREAD_NAME, daemon=True).start()
    except Exception as e:  # noqa: BLE001 - (no thread then: the window imports the code itself, as before)
        _on_ready(e)


def _eq_part_wanted():
    """No files of yours wait to be moved (the EQ part may take its folders now)."""
    try:
        import userfiles
        pairs, sources = userfiles.old_places()
    except Exception:  # noqa: BLE001 - (can't tell: left to the page, which loads it after the move is offered)
        return False
    return not pairs and not sources


def _load():
    """Step 2, in the import's own thread."""
    old = sys.getswitchinterval()
    sys.setswitchinterval(0.001)
    told = False
    try:
        err = None
        for name in SCREEN:
            _go.wait()
            try:
                importlib.import_module(name)
            except Exception as e:  # noqa: BLE001 - (said by error(): the window imports it itself, as before)
                err = e
                print(f"Make an EQ's code wasn't loaded ahead ({name}: {type(e).__name__}: {e}); it's loaded as it "
                      "opens instead")
                break
        if err is None and _eq_part_wanted():
            for name in EQ_PART:
                _go.wait()
                try:
                    importlib.import_module(name)
                except Exception:  # noqa: BLE001 - (the page's own loading imports it again and says what's wrong)
                    break
        told = True
        if not _tell(err) or err is not None:
            return
        for name in LATER:
            _go.wait()
            try:
                importlib.import_module(name)
            except Exception:  # noqa: BLE001 - (imported again where it's used, and said there)
                break
    finally:
        sys.setswitchinterval(old)
        if not told:  # (stopped by something other than an import's error: the window imports it itself)
            _tell(RuntimeError("Make an EQ's code wasn't loaded ahead"))


def _tell(err):
    try:
        _qt["messenger"].done.emit(err)
        return True
    except RuntimeError:  # (the app has quit meanwhile)
        return False


def _on_ready(err):
    _state.update(ready=True, error=err)
    waiting = list(_waiting)
    _waiting.clear()
    first = None
    for fn in waiting:
        try:
            fn()
        except Exception as e:  # noqa: BLE001 - (each one called; then the first error said, as Qt's call-backs say it)
            first = first or e
    if first is not None:
        raise first
