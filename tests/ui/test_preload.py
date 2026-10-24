"""Make an EQ's code loaded ahead, off the window's thread (ui\\preload.py, 2026-10-24), and PySide6's check of every
module's source skipped (ui\\__init__.py). Each runs in a Python of its own: this test process stays free of the EQ
part (the window's tests count on it), and what a Python has loaded is what's checked.

- the source check: answered "no" at once once ui is loaded (no source file read), safe because no module of the app
  uses `from __feature__ import ...`;
- the loading (PRELOAD below, from what the window has loaded): every class of Qt's modules made on the window's
  thread before the thread starts (two threads making one at once corrupted memory); started twice, one thread and
  each waiter called once; the import makes no Qt object; the EQ part loaded too when no files wait to be moved, not
  when some do; Python's thread switch left at the app's; hold() and release() pause and resume it (one release for
  each hold); what's loaded after ready waits for the window's thread to have handled it (a page made then holds it);
- Python's thread switch (ui\\__init__.py): the window's thread gets Python's lock at once beside a busy thread.
"""
import ast
import os

import pytest

from helpers import session, subproc

COVERS = ("ui", "ui.preload", "ui.window", "ui.eq_page", "ui.eq_settings", "ui.listen", "ui.filter_editor",
          "ui.your_files", "eq.service", "userfiles")

# (argv: the app's copy) PySide6's check after ui is loaded: its answer for a module that does say "PySide6", and the
# source files of the app it read (Python's line cache keeps every file read for it)
SOURCE_CHECK = r'''
import json, linecache, os, sys
sys.path.insert(0, sys.argv[1])
import PySide6  # noqa: F401
from ui import window  # noqa: F401 - (ui loaded first, then the window's modules)
feature = sys.modules.get("PySide6.support.feature")
app = os.path.normcase(os.path.abspath(sys.argv[1]))
print(json.dumps({"answer": feature._mod_uses_pyside(sys.modules["ui.window"]) if feature else "no check",
                  "read": sorted(os.path.basename(k) for k in list(linecache.cache)
                                 if os.path.normcase(os.path.abspath(k)).startswith(app))}))
'''

# (argv: the app's copy, the mode: "plain", "files waiting" or "held") The loading started from what the window has
# loaded, the window's event loop turning (processEvents) until it's done; one JSON line.
PRELOAD = r'''
import gc, json, os, sys, threading, time
sys.path.insert(0, sys.argv[1])
mode = sys.argv[2]
factor = float(os.environ.get("AUTOEQSTUDIO_TIME_FACTOR", "1") or 1)
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication
qapp = QApplication.instance() or QApplication([])
from ui import window  # noqa: F401 - (what the window has loaded before the loading starts)
from ui import preload
import userfiles
if mode == "files waiting":
    userfiles.old_places = lambda bases=None: ([("C:\\old\\inputs\\target", "C:\\new\\Targets")], [])
WATCHED = ("numpy", "pyqtgraph", "ui.eq_page", "ui.listen", "ui.your_files", "eq", "eq.service", "scipy.signal",
           "py_mini_racer")


def loaded():
    return sorted(m for m in WATCHED if m in sys.modules)


def pump(sec, until=None):
    end = time.monotonic() + sec * factor
    while time.monotonic() < end:
        qapp.processEvents()
        if until is not None and until():
            return True
        time.sleep(0.002)
    return until() if until is not None else True


def running():
    return any(t.name == preload.THREAD_NAME and t.is_alive() for t in threading.enumerate())


out = {"before": loaded(), "switch": sys.getswitchinterval()}
mods = (QtCore, QtGui, QtWidgets)
started = []  # (each start of the loading's thread: the names of those modules not made yet at that moment)
real_start = threading.Thread.start


def start(self):
    if self.name == preload.THREAD_NAME:
        started.append([f"{m.__name__}.{n}" for m in mods for n in dir(m) if n not in m.__dict__])
    return real_start(self)


threading.Thread.start = start
called = []
if mode == "held":
    preload.hold()
    preload.hold()
if mode == "held at ready":  # (as the page made once the code is in: it holds the loading while it opens)
    def at_ready():
        out["later at ready"] = [m for m in preload.LATER if m in sys.modules]
        preload.hold()
    preload.when_ready(at_ready)
preload.start(0)
preload.start(0)
preload.when_ready(lambda: called.append("first"))
preload.when_ready(lambda: called.append("second"))
qt_before = {id(o) for o in gc.get_objects() if isinstance(o, QObject)}
if mode == "held":
    pump(1.5)
    out["held"] = [loaded(), preload.ready(), bool(started)]
    preload.release()
    pump(1.0)
    out["released once"] = [loaded(), preload.ready()]
    preload.release()
if mode == "held at ready":
    pump(60, preload.ready)
    pump(1.0)
    out["later held"] = [m for m in preload.LATER if m in sys.modules]
    preload.release()
done = pump(60, lambda: preload.ready() and started and not running())
new = [o for o in gc.get_objects() if isinstance(o, QObject) and id(o) not in qt_before]
out.update(done=done, after=loaded(), error=repr(preload.error()), threads=len(started),
           missing_at_start=started[0][:5] if started else None, n_missing=len(started[0]) if started else None,
           called=called, switch_after=sys.getswitchinterval(),
           new_qt=[[type(o).__name__, o.thread() is qapp.thread()] for o in new])
# (that a Qt object made in another thread would be seen: one made so now, found the same way)
keep = []
t = threading.Thread(target=lambda: keep.append(QObject()))
t.start()
t.join()
out["control"] = [[type(o).__name__, o.thread() is qapp.thread()] for o in gc.get_objects()
                  if isinstance(o, QObject) and id(o) not in qt_before and o not in new]
print(json.dumps(out))
'''


def _run(mode):
    out = subproc.run_python(PRELOAD, session.SESSION.app, mode, timeout=180)
    return out.data or {}, out.stderr[-600:]


@pytest.fixture(scope="module")
def plain():
    return _run("plain")


def test_pyside_source_check_skipped(check):
    out = subproc.run_python(SOURCE_CHECK, session.SESSION.app)
    d = out.data or {}
    uses = []
    for folder, _subs, names in os.walk(session.SESSION.app):
        for name in names:
            if name.endswith(".py"):
                path = os.path.join(folder, name)
                with open(path, encoding="utf-8", errors="replace") as fh:
                    tree = ast.parse(fh.read(), path)
                for node in ast.walk(tree):
                    if (isinstance(node, ast.ImportFrom) and node.module == "__feature__") or \
                            (isinstance(node, ast.Import) and any(a.name == "__feature__" for a in node.names)):
                        uses.append(os.path.relpath(path, session.SESSION.app))
    check("preload: PySide6's check of every module's source is skipped once ui is loaded (answered no at once, no "
          "file of the app read for it), safe because no module of the app uses `from __feature__ import`",
          d.get("answer") is False and d.get("read") == [] and not uses, (d or out.stderr[-300:], uses))


def test_qt_classes_made_before_the_thread(plain, check):
    d, err = plain
    check("preload: every class of QtCore, QtGui and QtWidgets is made on the window's thread before the loading's "
          "thread starts (two threads making one at once corrupted memory)",
          d.get("threads") == 1 and d.get("n_missing") == 0, d.get("missing_at_start") if d else err)


def test_started_twice_is_harmless(plain, check):
    d, err = plain
    check("preload: started twice, one thread loads; each function waiting for it is called once, on the window's "
          "thread; ready, with no error",
          d.get("done") is True and d.get("threads") == 1 and d.get("called") == ["first", "second"]
          and d.get("error") == "None", d or err)


def test_the_import_makes_no_qt_object(plain, check):
    d, err = plain
    check("preload: the screen's code, the EQ part and SciPy imported in the loading's thread make no Qt object (one "
          "would belong to that thread); one made in another thread is seen (the check works); Python's thread switch "
          "left at the app's 0.5 ms (ui sets it as it loads: the window's thread gets Python's lock at once)",
          d.get("before") == [] and "ui.eq_page" in d.get("after", []) and "scipy.signal" in d.get("after", [])
          and d.get("new_qt") == [] and d.get("control") == [["QObject", False]]
          and d.get("switch_after") == d.get("switch") == 0.0005, d or err)


def test_the_eq_part_only_when_no_files_wait(plain, check):
    d, err = plain
    waiting, err2 = _run("files waiting")
    screen = sorted(["numpy", "pyqtgraph", "py_mini_racer", "scipy.signal", "ui.eq_page", "ui.listen", "ui.your_files"])
    check("preload: the EQ part loaded with the screen's code when no files wait to be moved; while some wait, only the "
          "screen's code (the EQ part takes your files' folders as it's imported, and the move offered at the first "
          "opening may change them)",
          d.get("after") == sorted(screen + ["eq", "eq.service"]) and waiting.get("done") is True
          and waiting.get("after") == screen, (d or err, waiting or err2))


def test_hold_and_release(check):
    d, err = _run("held")
    check("preload: held, the loading waits (nothing imported, not ready); released once for each hold, it goes on and "
          "is ready",
          d.get("held") == [[], False, True] and d.get("released once") == [[], False] and d.get("done") is True
          and "ui.eq_page" in d.get("after", []), d or err)


def test_held_as_ready_is_handled(check):
    d, err = _run("held at ready")
    check("preload: held by a function waiting for ready (as the page made then holds it while it opens), nothing loaded "
          "after ready has begun by then (V8 and SciPy's parts were imported meanwhile: a click then was answered ~0.1 s "
          "late), nor a second later; released, it goes on",
          d.get("later at ready") == [] and d.get("later held") == [] and d.get("done") is True
          and "scipy.signal" in d.get("after", []), d or err)


# (argv: the app's copy) The window's thread's calls into Python beside a thread that's busy: Python's lock handed over
# at once (ui sets the switch); then, as a control, at Python's usual 5 ms (it must be seen to wait)
LOCK = r'''
import json, sys, threading, time
sys.path.insert(0, sys.argv[1])
import ui
out = {"switch": sys.getswitchinterval()}


def work(n):
    s = 0
    for i in range(n):
        s += i & 7
    return s


def calls(switch):
    sys.setswitchinterval(switch)
    stop = threading.Event()

    def busy():
        while not stop.is_set():
            work(20000)
    t = threading.Thread(target=busy)
    t.start()
    time.sleep(0.05)
    start = time.perf_counter()
    for _ in range(300):  # (each a short call needing the lock, then let go of, as Qt's call-backs are)
        sum(range(50))
        time.sleep(0)
    took = time.perf_counter() - start
    stop.set()
    t.join()
    return round(took * 1000, 1)


out["the app's (ms)"] = calls(ui.SWITCH)
out["usual 5 ms (ms)"] = calls(0.005)
print(json.dumps(out))
'''


def test_window_gets_the_lock_at_once(check):
    out = subproc.run_python(LOCK, session.SESSION.app, timeout=120)
    d = out.data or {}
    check("ui: Python's thread switch under 1 ms as ui loads, so the window's thread gets Python's lock at once beside "
          "a busy thread: 300 calls into Python take under 0.15 s (at Python's usual 5 ms they took ~0.75 s: each waited "
          "for the lock, and a click while Make an EQ loaded was drawn ~0.1 s late)",
          d.get("switch") is not None and d["switch"] < 0.001 and d.get("the app's (ms)", 1e9) < 150
          and d.get("usual 5 ms (ms)", 0) > 3 * d.get("the app's (ms)", 1e9), d or out.stderr[-600:])
