"""The window opening Make an EQ (ui\\window.py over ui\\preload.py, 2026-10-24): never importing its code on the
window's thread, and made ahead while the window is open for someone who has used it (ui\\app.py's allow_preload).

The ones that open Make an EQ run in a Python of their own (this test process stays free of the EQ part: the other
window tests count on it), each with a studio of its own in the test's folder (your files and the EQ part's data:
the samples, the database lists, the EQ part's settings file, which says Make an EQ was opened before), offline, the
window drawn off-screen, message boxes recorded and never shown, and a record of the modules loaded on the window's
thread while it's watched:
- made ahead on Devices (the tab pointed at, which starts it at once): no message box, no status line, no window of
  its own, Devices still shown; then the click shows it ready, importing nothing;
- clicked before its code is in: "Opening the EQ part…" at once, nothing imported; Presets and the Guide wait until
  it's ready (also while a page built halfway isn't); a device change meanwhile raises nothing;
- the window opening straight onto Make an EQ: the same at once, nothing imported as it shows;
- the app only in the tray: nothing of the EQ part loaded with its event loop turning; made ahead once the window
  shows (about a second after);
- the gate: never with AUTOEQSTUDIO_PRELOAD=0 (the tests' copies), before a first opening, or while files wait to
  be moved; the window's memory given back to Windows 30 s after it closes to the tray, only in the app's own window.
"""
import json
import os
import shutil

import pytest

from helpers import paths as project
from helpers import qt, session, subproc

COVERS = ("ui.window", "ui.preload", "ui.app", "ui.winsys", "ui.eq_page", "ui.guide", "userfiles", "eq.service")

# The beginning of each Python of its own (argv: the app's copy, the test's folder; its environment points the app's
# folders at the test's studio). It defines: qapp, sw (a Switcher on a stand-in device, no Equalizer APO folder),
# make_window(page, show), pump(sec, until), device_changed() (what the switcher tells its listeners when a device
# starts playing: the error it raised, or None), placeholder_says(win) (the words shown on the screen shown), boxes,
# statuses and windows (message boxes asked for, status line messages, widgets shown as a window of their own), and
# loads with watching[0] (the modules loaded on the window's thread while watching[0] is True).
COMMON = r'''
import json, os, sys, threading, time
sys.path.insert(0, sys.argv[1])
top = sys.argv[2]
factor = float(os.environ.get("AUTOEQSTUDIO_TIME_FACTOR", "1") or 1)
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
qapp = QApplication.instance() or QApplication([])
MAIN = threading.get_ident()
boxes, statuses, windows, loads, watching, WIN = [], [], [], [], [False], [None]
for kind in ("information", "warning", "critical", "question"):
    setattr(QMessageBox, kind, staticmethod(lambda *a, _k=kind, **k: boxes.append(_k) or QMessageBox.Ok))
QMessageBox.exec = lambda self: boxes.append("box") or 0
import _frozen_importlib
real_load = _frozen_importlib._load_unlocked


def load(spec):
    if watching[0] and threading.get_ident() == MAIN:
        loads.append(spec.name)
    return real_load(spec)


_frozen_importlib._load_unlocked = load


class Windows(QObject):
    def eventFilter(self, obj, e):
        if e.type() == QEvent.Show and obj.isWidgetType() and obj.isWindow() and obj is not WIN[0]:
            windows.append(type(obj).__name__)
        return False


seen = Windows()
qapp.installEventFilter(seen)
import net
net.set_offline(True)
from ui import theme, theme_tokens
theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT
theme.apply(qapp, dark=False, contrast=False)
from switcher import core
from switcher import devices as D
from switcher.apo import Apo


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
        net.set_offline(on)


eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, False)]
sw = core.Switcher(os.path.join(top, "s.json"), Apo(os.path.join(top, "no-apo")), endpoints=lambda: eps,
                   playing=lambda: "{5}")


def pump(sec, until=None):
    end = time.monotonic() + sec * factor
    while time.monotonic() < end:
        qapp.processEvents()
        if until is not None and until():
            return True
        time.sleep(0.002)
    return bool(until()) if until is not None else True


def device_changed():
    try:
        for fn in list(sw.listeners):
            fn("devices", {"playing_changed": True})
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    return None


def make_window(page, show=True):
    from ui.window import Window
    sw.s["page"] = page
    win = Window(sw, Stub())
    WIN[0] = win
    real_status = win.status
    win.status = lambda text, ms=6000: (statuses.append(text), real_status(text, ms))[1]
    if show:
        win.show()
    return win


def placeholder_says(win):
    return [lab.text() for lab in win.stack.currentWidget().findChildren(QLabel) if lab.isVisible()]
'''

# Made ahead on Devices, started by pointing at the Make an EQ tab (the window's own wait made too long to start it
# here), a device change while its code loads and while its page opens; then the click.
AHEAD = COMMON + r'''
from ui.window import Window
Window.AHEAD_MS = 600000
win = make_window("devices")
screens = []
win.stack.currentChanged.connect(lambda i: screens.append(win.page()))
pump(0.3)
win.allow_preload(lambda: True)
pump(1.0)
out = {"not yet": [win.eq_page is None, "ui.eq_page" in sys.modules]}
during = {}


def step():
    p = win.eq_page
    if p is None and "code loading" not in during:
        during["code loading"] = device_changed()
    if p is not None and not p.ready and "page opening" not in during:
        during["page opening"] = device_changed()
    return p is not None and p.ready


t = time.monotonic()
watching[0] = True
QApplication.sendEvent(win.nav["eq"], QEvent(QEvent.Enter))
ok = pump(60, step)
watching[0] = False
out["made ahead"] = round(time.monotonic() - t, 1) if ok else None
pump(1.5)
out.update(page=win.page(), screens=list(screens), boxes=list(boxes), statuses=list(statuses), windows=list(windows),
           status_line=win.status_text.text(), device_changes=during, loads_while_made_ahead=loads[:8])
del loads[:]
watching[0] = True
t = time.perf_counter()
win.show_page("eq", remember=False)
out["click_ms"] = round((time.perf_counter() - t) * 1000, 1)
watching[0] = False
p = win.eq_page
out["clicked"] = [win.page(), p is not None and p.ready, p is not None and p.isVisible(), list(loads)]
print(json.dumps(out))
'''

# Make an EQ clicked before its code is in (no preload): what shows, Presets and the Guide (the tour stood in: whether
# the page was ready when it started), a device change; then a page built halfway (its controls there, not ready).
CLICK = COMMON + r'''
import ui.guide
tours = []
ui.guide.start_eq = lambda page: tours.append(page.ready)
win = make_window("devices")
pump(0.3)
out = {}
watching[0] = True
win.show_page("eq", remember=False)
watching[0] = False
out["at the click"] = [win.page(), win.eq_page is None, placeholder_says(win), list(loads)]


def presets():
    win.presets_menu.aboutToShow.emit()
    return [a.text() for a in win.presets_menu.actions() if a.text()]


out["code loading"] = [presets(), device_changed()]
win.start_guide()
out["guide while its code loads"] = [list(tours), statuses[-1:]]
state = {}


def step():
    p = win.eq_page
    if p is not None and not p.ready and "page opening" not in state:
        state["page opening"] = [presets(), device_changed(), list(tours)]
    return p is not None and p.ready and bool(tours)


ok = pump(60, step)
out["page opening"] = state.get("page opening")
out["opened"] = [ok, win.page(), win.stack.currentWidget() is win.eq_page, list(tours)]
out["presets once open"] = "Save as a preset…" in presets()
page = win.eq_page
page.ready = False
out["half built: presets"] = presets()
win.tour = None
n = len(tours)
win.start_guide()
pump(0.8)
out["half built: guide"] = tours[n:]
page.ready = True
pump(1.5, lambda: len(tours) > n)
out["then ready: guide"] = tours[n:]
print(json.dumps(out))
'''

# The window made hidden on Make an EQ (as when the app starts in the tray on it), then shown.
STRAIGHT = COMMON + r'''
win = make_window("eq", show=False)
out = {"hidden": [win.eq_page is None, "ui.eq_page" in sys.modules]}
watching[0] = True
win.show()
watching[0] = False
out["shown"] = [win.page(), win.eq_page is None, placeholder_says(win), list(loads)]
ok = pump(60, lambda: win.eq_page is not None and win.eq_page.ready)
out["opened"] = [ok, win.page(), win.stack.currentWidget() is win.eq_page]
print(json.dumps(out))
'''

# The App itself (argv: the app's copy, the test's folder). Its settings say offline, Devices, no hotkey.
APP = r'''
import json, os, shutil, sys, threading, time
sys.path.insert(0, sys.argv[1])
top = sys.argv[2]
factor = float(os.environ.get("AUTOEQSTUDIO_TIME_FACTOR", "1") or 1)
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
qapp = QApplication([])
boxes = []
for kind in ("information", "warning", "critical", "question"):
    setattr(QMessageBox, kind, staticmethod(lambda *a, _k=kind, **k: boxes.append(_k) or QMessageBox.Ok))
EQ = ("eq", "numpy", "pyqtgraph", "scipy", "py_mini_racer", "ui.eq_page")


def pump(sec, until=None):
    end = time.monotonic() + sec * factor
    while time.monotonic() < end:
        qapp.processEvents()
        if until is not None and until():
            return True
        time.sleep(0.002)
    return bool(until()) if until is not None else True


def loaded():
    return sorted(m for m in EQ if m in sys.modules)


from ui.app import App
'''

# Only in the tray for 5 s (its event loop turning), then the window shown.
TRAY = APP + r'''
a = App(qapp, show=False)
QTimer.singleShot(5000, qapp.quit)
qapp.exec()
out = {"tray": [loaded(), [t.name for t in threading.enumerate() if t.name == "Make an EQ's code"],
                a.win.eq_page is None]}
a.win.show_front()
t = time.monotonic()
ok = pump(60, lambda: a.win.eq_page is not None and a.win.eq_page.ready)
out["shown"] = [ok, a.win.page(), list(boxes)]
a.tray.hide()
print(json.dumps(out))
'''

# As the tests' copies of the app start (helpers.session.child_env: AUTOEQSTUDIO_PRELOAD=0), then allowed as the app
# does: before a first opening (no settings file for the EQ part yet), with files waiting to be moved, then neither
# (the window hidden and shown again each time).
GATE = APP + r'''
a = App(qapp, show=True)
out = {}
pump(2.5)
out["AUTOEQSTUDIO_PRELOAD=0"] = [loaded(), a.win.eq_page is None, os.environ.get("AUTOEQSTUDIO_PRELOAD")]
a.win.allow_preload(a.preload_worth_it)


def again(wait=2.5, until=None):
    a.win.hide()
    pump(0.2)
    a.win.show_front()
    return pump(wait, until)


again()
out["not opened before"] = [loaded(), a.win.eq_page is None, a.preload_worth_it()]
data = os.environ["AUTOEQSTUDIO_DATA"]
os.makedirs(os.path.join(data, "eq"), exist_ok=True)
shutil.copy(os.path.join(top, "eq-settings.json"), os.path.join(data, "eq", "settings.json"))
import userfiles
real = userfiles.old_places
userfiles.old_places = lambda bases=None: ([("C:\\old\\inputs\\target", "C:\\new\\Targets")], [])
again()
out["files waiting"] = [loaded(), a.win.eq_page is None, a.preload_worth_it()]
userfiles.old_places = real
ok = again(60, lambda: a.win.eq_page is not None and a.win.eq_page.ready)
out["worth it"] = [ok, a.win.page(), a.preload_worth_it(), list(boxes)]
a.tray.hide()
print(json.dumps(out))
'''


# The symbols' font looked up ahead (theme.warm_symbols) once Make an EQ is being made ahead, only at a quiet moment:
# Windows' time since the last key or mouse input stood in (busy, then quiet); and not again
WARM = COMMON + r'''
from ui import winsys
from ui.window import Window
Window.AHEAD_MS = 100
quiet = [0]
winsys.idle_ms = lambda: quiet[0]
calls = []
real = theme.warm_symbols
theme.warm_symbols = lambda: calls.append(1) or real()
win = make_window("devices")
pump(0.3)
win.allow_preload(lambda: True)
pump(1.2)
out = {"while busy": len(calls), "warm while busy": theme.symbols_warm(),
       "made while busy": win.eq_page is not None or "ui.eq_page" in sys.modules}
quiet[0] = 5000
made = pump(60, lambda: win.eq_page is not None and win.eq_page.ready)
out.update({"once quiet": len(calls), "warm": theme.symbols_warm(), "made": made, "page": win.page()})
pump(0.6)
out["later"] = len(calls)
print(json.dumps(out))
'''


def _studio(top, eq_settings=True):
    """A studio of its own in top: your files (the samples, the sample target and device) and the EQ part's data
    (the database lists; its settings file, This PC's search on the samples, unless eq_settings is False: then it's
    left beside it as eq-settings.json). The environment for a Python of its own on it."""
    studio = os.path.join(top, "studio")
    shutil.copytree(project.SAMPLES, os.path.join(studio, "samples"))
    os.makedirs(os.path.join(studio, "Targets"))
    shutil.copy(os.path.join(project.SAMPLES, "targets", project.SAMPLE_TARGET), os.path.join(studio, "Targets"))
    shutil.copytree(os.path.join(project.SAMPLES, "measurements", project.SAMPLE_DEVICE),
                    os.path.join(studio, "Measurements"))
    data = os.path.join(studio, "data")
    session.install_lists(os.path.join(data, "eq", "cache"))
    session.write_eq_settings(studio)
    if not eq_settings:
        shutil.move(os.path.join(data, "eq", "settings.json"), os.path.join(top, "eq-settings.json"))
    return {"AUTOEQSTUDIO_ROOT": studio, "AUTOEQSTUDIO_DATA": data}


def _app_env(top, conf, eq_settings=True, **more):
    """The App's environment: a studio of its own, its settings (offline, on Devices, no hotkey, told about the
    tray), the stand-in APO folder and EQ Switcher's stand-in settings, and more (AUTOEQSTUDIO_PRELOAD=None: removed,
    so the app makes Make an EQ ahead; left out, it's the tests' own 0)."""
    env = _studio(top, eq_settings)
    with open(os.path.join(env["AUTOEQSTUDIO_DATA"], "settings.json"), "w", encoding="utf-8") as fh:
        json.dump({"offline": True, "hotkey": "", "onoff_hotkey": "", "page": "devices", "told_tray": True}, fh)
    env.update(AUTOEQSTUDIO_APO_CONFIG=conf, AUTOEQSTUDIO_OLD_SETTINGS=os.path.join(top, "no-eqswitcher.json"), **more)
    return env


def _run(code, top, env, timeout=240):
    out = subproc.run_python(code, session.SESSION.app, top, env=env, timeout=timeout)
    return out.data or {}, out.stderr[-700:]


@pytest.fixture(scope="module")
def ahead(tmp_path_factory):
    top = str(tmp_path_factory.mktemp("ahead"))
    return _run(AHEAD, top, _studio(top))


@pytest.fixture(scope="module")
def clicked(tmp_path_factory):
    top = str(tmp_path_factory.mktemp("click"))
    return _run(CLICK, top, _studio(top))


@pytest.mark.slow
def test_made_ahead_on_devices_with_nothing_showing(ahead, check):
    d, err = ahead
    check("window: Make an EQ made ahead while the window is on Devices (the tab pointed at starts it at once) shows "
          "nothing early: no message box, status line or window of its own, and Devices stays the screen shown",
          d.get("not yet") == [True, False] and d.get("made ahead") is not None and d.get("page") == "devices"
          and all(s == "devices" for s in d.get("screens", ["?"])) and d.get("boxes") == []
          and d.get("statuses") == [] and d.get("windows") == [] and d.get("status_line") == "", d or err)


@pytest.mark.slow
def test_the_click_shows_it_ready(ahead, check):
    d, err = ahead
    check("window: once made ahead, the click on Make an EQ shows it ready at once, importing nothing on the window's "
          "thread", d.get("clicked") == ["eq", True, True, []], d or err)


@pytest.mark.slow
def test_clicked_before_its_code_is_in(clicked, check):
    d, err = clicked
    check("window: Make an EQ clicked before its code is in shows “Opening the EQ part…” at once, nothing imported on "
          "the window's thread; the page takes its place when its code is in",
          d.get("at the click") == ["eq", True, ["Opening the EQ part…"], []]
          and (d.get("opened") or [])[:3] == [True, "eq", True], d or err)


@pytest.mark.slow
def test_the_guide_and_presets_wait_for_ready(clicked, check):
    d, err = clicked
    note = ["Presets are ready as soon as Make an EQ has opened"]
    check("window: Presets and the Guide wait until Make an EQ is ready: while its code loads, while its page opens, "
          "and while a page built halfway (its controls there) isn't ready; then the Guide starts on the ready page",
          (d.get("code loading") or [None])[0] == note
          and d.get("guide while its code loads") == [[], ["The Guide starts as soon as Make an EQ has opened…"]]
          and (d.get("page opening") or [None, None, None])[0] == note and d["page opening"][2] == []
          and (d.get("opened") or [None] * 4)[3] == [True] and d.get("presets once open") is True
          and d.get("half built: presets") == note and d.get("half built: guide") == []
          and d.get("then ready: guide") == [True], d or err)


@pytest.mark.slow
def test_a_device_change_while_it_opens(ahead, clicked, check):
    d, err = ahead
    c, err2 = clicked
    check("window: a device change while Make an EQ opens (its code loading, its page made but not ready: no Listen "
          "card yet) raises nothing, made ahead or clicked",
          d.get("device_changes") == {"code loading": None, "page opening": None}
          and (c.get("code loading") or [None, "?"])[1] is None and (c.get("page opening") or [None, "?"])[1] is None,
          (d.get("device_changes") if d else err, c.get("code loading") if c else err2, c.get("page opening")))


@pytest.mark.slow
def test_opening_straight_onto_make_an_eq(check, tmp_path):
    d, err = _run(STRAIGHT, str(tmp_path), _studio(str(tmp_path)))
    check("window: shown straight onto Make an EQ (the app started on it), “Opening the EQ part…” at once, nothing "
          "imported on the window's thread as it shows; then the page",
          d.get("hidden") == [True, False] and d.get("shown") == ["eq", True, ["Opening the EQ part…"], []]
          and d.get("opened") == [True, "eq", True], d or err)


@pytest.mark.slow
def test_never_while_only_in_the_tray(check, fake_apo, tmp_path):
    top = str(tmp_path)
    d, err = _run(TRAY, top, _app_env(top, fake_apo, AUTOEQSTUDIO_PRELOAD=None))
    check("app: Make an EQ isn't made ahead while the app is only in the tray (nothing of the EQ part loaded, its event "
          "loop turning for 5 s); once the window shows, it is (Devices still shown, no message box)",
          d.get("tray") == [[], [], True] and d.get("shown") == [True, "devices", []], d or err)


@pytest.mark.slow
def test_only_when_used_before_and_no_files_wait(check, fake_apo, tmp_path):
    top = str(tmp_path)
    d, err = _run(GATE, top, _app_env(top, fake_apo, eq_settings=False))
    check("app: Make an EQ never made ahead in the tests' copies of the app (AUTOEQSTUDIO_PRELOAD=0, helpers.session's "
          "child_env), before it was ever opened (no settings file of the EQ part), or while files wait to be moved; "
          "made ahead once it was opened and none wait",
          d.get("AUTOEQSTUDIO_PRELOAD=0") == [[], True, "0"] and d.get("not opened before") == [[], True, False]
          and d.get("files waiting") == [[], True, False] and d.get("worth it") == [True, "devices", True, []],
          d or err)


def test_worth_it(check, tmp_path, monkeypatch):
    import paths
    import userfiles
    from ui.app import App

    def unreadable(bases=None):
        raise OSError("can't be read")
    monkeypatch.setattr(paths, "DATA", str(tmp_path / "data"))
    seen = {}
    for name, places, settings in (("never opened", ([], []), False), ("opened", ([], []), True),
                                   ("files waiting", ([("old", "new")], []), True),
                                   ("an old record waiting", ([], ["old\\inputs\\sources.json"]), True),
                                   ("can't tell", None, True)):
        monkeypatch.setattr(userfiles, "old_places", (lambda bases=None, p=places: p) if places else unreadable)
        if settings:
            os.makedirs(tmp_path / "data" / "eq", exist_ok=True)
            (tmp_path / "data" / "eq" / "settings.json").write_text("{}", encoding="utf-8")
        seen[name] = App.preload_worth_it()
    check("app: Make an EQ made ahead only once it was opened before (the EQ part's settings file in the data folder) "
          "and no files or records wait to be moved (can't tell: not)",
          seen == {"never opened": False, "opened": True, "files waiting": False, "an old record waiting": False,
                   "can't tell": False}, seen)


TRIM = r'''
import ctypes, json, sys
from ctypes import wintypes
sys.path.insert(0, sys.argv[1])
from ui import winsys


class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t)]


k32 = ctypes.WinDLL("kernel32")
k32.GetCurrentProcess.restype = wintypes.HANDLE
k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]


def working_set():
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return round(pmc.WorkingSetSize / 2**20)


block = bytearray(200 * 2**20)
for i in range(0, len(block), 4096):
    block[i] = 1
before = working_set()
took = winsys.trim_memory()
after = working_set()
print(json.dumps({"took": took, "before": before, "after": after, "kept": block[4096] == 1}))
'''


def test_trim_memory(check):
    out = subproc.run_python(TRIM, session.SESSION.app)
    d = out.data or {}
    check("winsys: the app's memory given back to Windows (the working set emptied: what's used again comes back as "
          "it's used; nothing is lost)",
          d.get("took") is True and d.get("before", 0) >= 200 and d.get("after", 999) < d["before"] - 150
          and d.get("kept") is True, d or out.stderr[-300:])


def test_memory_given_back_in_the_tray(qapp, stub_app, tmp_path, monkeypatch, check):
    from switcher import core
    from switcher import devices as D
    from switcher.apo import Apo
    from ui import winsys
    from ui.window import Window
    trims = []
    monkeypatch.setattr(winsys, "trim_memory", lambda: trims.append(1) or True)
    monkeypatch.setattr(Window, "TRIM_MS", 60)
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, False)]
    sw = core.Switcher(str(tmp_path / "s.json"), Apo(str(tmp_path / "no-apo")), endpoints=lambda: eps,
                       playing=lambda: "{5}")
    sw.s["page"] = "devices"
    plain, own = Window(sw, stub_app), Window(sw, stub_app)
    own.allow_preload(lambda: False)  # (the app's own window, here never worth making Make an EQ ahead)
    seen = {}
    try:
        for name, win in (("a test's window", plain), ("the app's window", own)):
            win.show()
            qt.pump(30)
            win.close()
            qt.pump(400)
            seen[name] = len(trims)
            del trims[:]
        own.show()
        qt.pump(30)
        own.close()
        own.show()  # (shown again before the time's up)
        qt.pump(400)
        seen["shown again"] = len(trims)
    finally:
        qt.close(plain)
        qt.close(own)
    check("window: closed to the tray, the app's own window gives its memory back to Windows after a while (once), "
          "not when it's shown again by then, nor a window the app didn't allow it (a test's)",
          seen == {"a test's window": 0, "the app's window": 1, "shown again": 0}, seen)


@pytest.mark.slow
def test_symbols_font_looked_up_at_a_quiet_moment(check, tmp_path):
    # (2026-10-24: the first symbol the app's font lacks (✕ ↺ ⇄ ▶ …) took 150-250 ms on the window's thread, Windows
    # finding it in another font; when no screen had drawn one yet, Make an EQ's first drawing paid it at the click.
    # Made ahead, the window looks them up first, and makes Make an EQ ahead only at a quiet moment: the work holds
    # the window now and then, and a click while it ran was answered ~0.4 s late)
    d, err = _run(WARM, str(tmp_path), _studio(str(tmp_path)))
    check("window: Make an EQ made ahead only once the keys and the mouse have been quiet a moment (nothing loaded "
          "while they're busy), the symbols' font looked up first (theme.warm_symbols), once",
          d.get("while busy") == 0 and d.get("warm while busy") is False and d.get("made while busy") is False
          and d.get("once quiet") == 1 and d.get("warm") is True and d.get("made") is True
          and d.get("page") == "devices" and d.get("later") == 1, d or err)


def _window(stub_app, tmp_path):
    """A window of this test's own (on Devices, a stand-in device, no Equalizer APO folder), not shown."""
    from switcher import core
    from switcher import devices as D
    from switcher.apo import Apo
    from ui.window import Window
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, False)]
    sw = core.Switcher(str(tmp_path / "s.json"), Apo(str(tmp_path / "no-apo")), endpoints=lambda: eps,
                       playing=lambda: "{5}")
    sw.s["page"] = "devices"
    return Window(sw, stub_app)


def test_made_ahead_at_a_quiet_moment_or_when_about_to_be_clicked(qapp, stub_app, tmp_path, monkeypatch, check):
    # (2026-10-24, the checkers: made ahead ~20 ms after the window showed, not a second after: Qt gives the Make an
    # EQ tab the focus as the window becomes active, and any focus was taken as "reached with Tab". Its work holds the
    # window now and then: a click while it ran was answered ~0.4 s late. Here what it's asked to do is recorded:
    # nothing is loaded)
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QFocusEvent
    from PySide6.QtWidgets import QApplication
    from ui import theme, winsys
    win = _window(stub_app, tmp_path)
    quiet, calls = [0], []
    monkeypatch.setattr(winsys, "idle_ms", lambda: quiet[0])
    monkeypatch.setattr(theme, "warm_symbols", lambda: calls.append("symbols"))
    monkeypatch.setattr(win, "_eq_when_code_in", lambda: calls.append("made"))
    seen = {}
    try:
        win.show()
        qt.pump(30)
        win.allow_preload(lambda: True)
        win._ahead_timer.stop()  # (its wait after the window shows: the moment it ends is played by hand below)
        win._make_eq_ahead()
        seen["busy"], seen["tried again"] = list(calls), win._ahead_timer.isActive()
        win._ahead_timer.stop()
        quiet[0] = 5000
        win._make_eq_ahead()
        seen["quiet"] = list(calls)
        del calls[:]
        for reason in (Qt.ActiveWindowFocusReason, Qt.OtherFocusReason, Qt.MouseFocusReason):
            QApplication.sendEvent(win.nav["eq"], QFocusEvent(QEvent.FocusIn, reason))
        seen["focus as the window opens or clicked"] = list(calls)
        quiet[0] = 0
        QApplication.sendEvent(win.nav["eq"], QFocusEvent(QEvent.FocusIn, Qt.TabFocusReason))
        seen["reached with Tab, busy"] = list(calls)
        del calls[:]
        QApplication.sendEvent(win.nav["eq"], QEvent(QEvent.Enter))
        seen["pointed at, busy"] = list(calls)
    finally:
        qt.close(win)
    check("window: Make an EQ made ahead at a quiet moment (no key or mouse input for a while: tried again until "
          "then), the symbols' font first; at once when its tab is pointed at or reached with Tab, not for the focus "
          "Qt gives it as the window opens",
          seen == {"busy": [], "tried again": True, "quiet": ["symbols", "made"],
                   "focus as the window opens or clicked": [], "reached with Tab, busy": ["made"],
                   "pointed at, busy": ["made"]}, seen)


def test_another_screen_asked_for_while_hidden(qapp, stub_app, tmp_path, monkeypatch, check):
    # (2026-10-24, the checkers: the tray's Add a profile… (shown when the playing device has none) opened Make an EQ
    # when Make an EQ had been asked for while the window was hidden: it stayed waiting to be made when it shows)
    from ui import preload
    win = _window(stub_app, tmp_path)
    made = []
    monkeypatch.setattr(preload, "ready", lambda: False)
    monkeypatch.setattr(win, "_eq_when_code_in", lambda: made.append(1))
    try:
        win.show_page("eq", remember=False)  # (asked for while hidden: made when the window shows)
        win.show_page("devices", remember=False)  # (the tray's Add a profile…, then the window shown)
        win.show()
        qt.pump(50)
        shown = win.page()
    finally:
        qt.close(win)
    check("window: the screen asked for last while it was hidden is the one it shows (the tray's Add a profile… "
          "showed Make an EQ when that had been asked for before)", shown == "devices" and not made, (shown, made))


def test_code_that_cant_load_is_said(qapp, stub_app, tmp_path, monkeypatch, check):
    # (2026-10-24, the checkers: with Make an EQ's code broken (a damaged copy), the click showed "Opening the EQ
    # part…" for ever, the error only in the log; the Guide's button raised)
    import sys

    from PySide6.QtWidgets import QLabel
    from ui import guide, preload, theme
    win = _window(stub_app, tmp_path)
    tours = []
    monkeypatch.setattr(preload, "ready", lambda: True)
    monkeypatch.setattr(preload, "error", lambda: ImportError("stood in"))
    monkeypatch.setitem(sys.modules, "ui.eq_page", None)  # (its import fails, as in a damaged copy)
    monkeypatch.setattr(guide, "start_eq", lambda page: tours.append(page))
    monkeypatch.setattr(theme, "warm_symbols", lambda: False)
    raised = None
    try:
        win.show()
        qt.pump(30)
        try:
            win.show_page("eq", remember=False)
            win.start_guide()
        except Exception as e:  # noqa: BLE001 - (what the check reports)
            raised = f"{type(e).__name__}: {e}"
        qt.pump(400)
        words = [lab.text() for lab in win.stack.currentWidget().findChildren(QLabel)]
        seen = {"raised": raised, "page": win.page(), "made": win.eq_page is not None,
                "says": [w.split(":")[0] for w in words], "guide waits": win._guide_waiting, "tours": len(tours)}
    finally:
        qt.close(win)
    check("window: Make an EQ's code that can't be loaded (a damaged copy) is said where Make an EQ shows (“The EQ "
          "part couldn't open: …”), not “Opening the EQ part…” for ever; nothing raises and the Guide doesn't wait",
          seen == {"raised": None, "page": "eq", "made": False, "says": ["The EQ part couldn't open"],
                   "guide waits": False, "tours": 0}, seen)


def test_the_guide_left_when_you_go_on(qapp, stub_app, tmp_path, monkeypatch, check):
    # (2026-10-24, the checkers: the Guide asked for while Make an EQ opened, then another screen chosen: the tour
    # started over that screen once the page was ready)
    from types import SimpleNamespace

    from PySide6.QtWidgets import QLabel
    from ui import guide
    win = _window(stub_app, tmp_path)
    tours = []
    monkeypatch.setattr(guide, "start_eq", lambda page: tours.append(page))
    loading = QLabel("Opening the EQ part…")
    try:
        win.show()
        qt.pump(30)
        win.stack.setCurrentWidget(win.pages["eq"])  # (Make an EQ shown, its page made and still opening)
        win.eq_page = SimpleNamespace(ready=False, loading=loading)
        win._guide_when_ready()
        waiting = win._guide_waiting
        win.show_page("devices", remember=False)  # (gone on to Devices)
        win.eq_page.ready = True
        qt.pump(500)
        seen = {"waited": waiting, "tours": len(tours), "page": win.page()}
    finally:
        win.eq_page = None
        qt.close(win)
        qt.close(loading)
    check("window: the Guide asked for while Make an EQ opens is left when you go on to another screen (it started "
          "over that screen once the page was ready)", seen == {"waited": True, "tours": 0, "page": "devices"}, seen)
