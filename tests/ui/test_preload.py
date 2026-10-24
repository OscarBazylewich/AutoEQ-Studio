"""Make an EQ's code loaded ahead, off the window's thread (ui\\preload.py, 2026-10-24), and PySide6's check of every
module's source skipped (ui\\__init__.py). Each runs in a Python of its own: this test process stays free of the EQ
part (the window's tests count on it), and what a Python has loaded is what's checked.

- the source check: answered "no" at once once ui is loaded (no source file read), safe because no module of the app
  uses `from __feature__ import ...`;
- the loading (PRELOAD below, from what the window has loaded): every class of Qt's modules made on the window's
  thread before the thread starts (two threads making one at once corrupted memory); started twice, one thread and
  each waiter called once; the import makes no Qt object; the EQ part loaded too when no files wait to be moved, not
  when some do; Python's thread switch put back after; hold() and release() pause and resume it (one release for each
  hold).
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
          "put back after",
          d.get("before") == [] and "ui.eq_page" in d.get("after", []) and "scipy.signal" in d.get("after", [])
          and d.get("new_qt") == [] and d.get("control") == [["QObject", False]]
          and d.get("switch_after") == d.get("switch"), d or err)


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
