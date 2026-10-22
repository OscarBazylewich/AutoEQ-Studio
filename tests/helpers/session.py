"""The session's folders and variables. Every pytest process (a session) works in a temporary folder of its own,
%TEMP%\\aeqs-tests-XXXXXXXX: a stand-in home with its own Documents, Downloads and AppData, a stand-in Equalizer APO
folder, and "the studio": a copy of the app with its samples, your-files folders and data folder. Every variable the
app reads for its folders points in there, so no test reaches your files, the real Equalizer APO folder or AppData.

prepare() makes it all (tests\\conftest.py calls it first, before any app module is imported); cleanup() deletes the
folder at the end (kept, and said where, with AUTOEQSTUDIO_KEEP_TEST_FOLDER=1). A run stopped half way (a time
limit, a crash) leaves its folder behind: the next prepare() deletes it once the process that made it is gone.

Every folder here is spelled the long way (os.path.realpath): Windows' TEMP is often the short form
(C:\\Users\\OSCART~1\\...), pytest spells its tmp_path the long way, and the guard compares them.
"""
import ctypes
import dataclasses
import json
import os
import shutil
import sys
import tempfile
import time
from ctypes import wintypes

from helpers import checks
from helpers import paths as project

FOLDER_VARS = ("AUTOEQSTUDIO_ROOT", "AUTOEQSTUDIO_DATA", "AUTOEQSTUDIO_DOCUMENTS", "AUTOEQSTUDIO_APO_CONFIG",
               "AUTOEQSTUDIO_APO_INSTALL", "AUTOEQSTUDIO_OLD_SETTINGS")
LOG_VARS = ("AUTOEQSTUDIO_CHECK_LOG", "AUTOEQSTUDIO_TEST_OUT")  # (the runner's: a child never writes into its log)
REAL_VARS = ("USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "ProgramFiles", "ProgramFiles(x86)")
PREFIX = "aeqs-tests-"


@dataclasses.dataclass
class Session:
    root: str          # the session folder, %TEMP%\aeqs-tests-XXXXXXXX
    tmp: str           # root\tmp: TEMP and TMP for this process and its children
    home: str          # root\home: the stand-in home (Documents, Downloads, Desktop, Music, AppData)
    studio: str        # root\AutoEQ Studio: the copy of the app, its samples, your files' folders, data
    app: str           # studio\app: the copy every test imports
    data: str          # studio\data
    apo_config: str    # root\apo\config: a stand-in for Equalizer APO's config folder
    old_settings: str  # root\old\settings.json: EQ Switcher's settings (never there)
    real_temp: str     # the TEMP folder the run started with (the guard never lets a test write there)
    real_home: str     # the home folder the run started with (likewise)
    real_env: dict     # the variables the run started with, before the session replaced them (read only)


SESSION: Session | None = None

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.OpenProcess.restype = wintypes.HANDLE
_k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_k32.GetCurrentProcess.restype = wintypes.HANDLE
_k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(ctypes.c_uint64)] * 4
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_QUERY = 0x1000      # PROCESS_QUERY_LIMITED_INFORMATION
_STILL_ACTIVE = 259


def _started_at(handle):
    """When a process started (Windows' own count), so a reused process id isn't taken for the one that's gone."""
    times = [ctypes.c_uint64() for _ in range(4)]
    if not _k32.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
        return None
    return times[0].value


def process_alive(pid, started=None):
    """Is this process still running (and, given its start time, the same one)?"""
    handle = _k32.OpenProcess(_QUERY, False, int(pid))
    if not handle:
        return ctypes.get_last_error() == 5  # (access denied: it's there, someone else's)
    try:
        code = wintypes.DWORD()
        if _k32.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value != _STILL_ACTIVE:
            return False
        return started is None or _started_at(handle) in (None, started)
    finally:
        _k32.CloseHandle(handle)


def owner_line():
    """What owner.txt holds: this process's id and its start time."""
    return f"{os.getpid()} {_started_at(_k32.GetCurrentProcess()) or 0}\n"


def sweep_stale(folder):
    """Delete the session folders in `folder` whose process is gone (a run stopped by a time limit or a crash leaves
    one). Only folders named aeqs-tests-* holding an owner.txt that can be read: so only ones the tests made, and
    never one still being made. Returns the folders deleted."""
    gone = []
    try:
        names = os.listdir(folder)
    except OSError:
        return gone
    for name in names:
        path = os.path.join(folder, name)
        if not name.startswith(PREFIX) or not os.path.isdir(path):
            continue
        try:
            with open(os.path.join(path, "owner.txt"), encoding="utf-8") as fh:
                pid, started = (int(x) for x in fh.read().split()[:2])
        except (OSError, ValueError):
            continue
        if not process_alive(pid, started or None):
            shutil.rmtree(path, ignore_errors=True)
            gone.append(path)
    return gone


def _long(path):
    """A Windows folder spelled the long way; anything else (e.g. Git Bash's /c/Users/... HOME) as it is."""
    return os.path.realpath(path) if path and os.path.splitdrive(path)[0] else path


def install_lists(cache):
    """The small database lists (tests\\fixtures\\db) copied into a data\\eq\\cache folder, every "time" set to now: fresh,
    so the app never downloads them again, even when a test goes online."""
    os.makedirs(cache, exist_ok=True)
    now = time.time()
    for name in ("databases.json", "squigsites.json"):
        with open(os.path.join(project.DB_FIXTURES, name), encoding="utf-8") as fh:
            lists = json.load(fh)
        if name == "databases.json":
            for entry in lists.values():
                if isinstance(entry, dict):
                    entry["time"] = now
        else:
            lists["time"] = now
        with open(os.path.join(cache, name), "w", encoding="utf-8") as fh:
            json.dump(lists, fh, indent=1)


def _merged(base, more):
    out = dict(base)
    for k, v in more.items():
        out[k] = _merged(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def write_eq_settings(studio, values=None):
    """The EQ part's settings file (studio\\data\\eq\\settings.json): This PC's search on the studio's samples (never a
    home folder), merged with `values`. A settings file there also means the bring-over from AutoEQ Local never runs."""
    cfg = _merged({"library": {"folders": [os.path.join(studio, "samples")]}}, values or {})
    folder = os.path.join(studio, "data", "eq")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "settings.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


def prepare():
    """The session's folders and variables (once per process): PLAN.md 3.9."""
    global SESSION
    if SESSION is not None:
        return SESSION
    real_env = {k: _long(os.environ[k]) for k in REAL_VARS if os.environ.get(k)}
    real_temp = os.path.realpath(tempfile.gettempdir())
    real_home = os.path.realpath(os.path.expanduser("~"))
    sweep_stale(real_temp)
    root = os.path.realpath(tempfile.mkdtemp(prefix=PREFIX, dir=real_temp))
    with open(os.path.join(root, "owner.txt"), "w", encoding="utf-8") as fh:
        fh.write(owner_line())
    tmp, home, studio = os.path.join(root, "tmp"), os.path.join(root, "home"), os.path.join(root, "AutoEQ Studio")
    os.makedirs(tmp)
    for sub in ("Downloads", "Documents", "Desktop", "Music", r"AppData\Roaming", r"AppData\Local"):
        os.makedirs(os.path.join(home, sub))
    app = os.path.join(studio, "app")
    shutil.copytree(project.PROJECT_APP, app, ignore=shutil.ignore_patterns(
        "__pycache__", "tools", "data", "installed.txt", "test-build.txt"))
    shutil.copytree(project.SAMPLES, os.path.join(studio, "samples"))
    os.makedirs(os.path.join(studio, "Targets"))
    shutil.copy(os.path.join(project.SAMPLES, "targets", project.SAMPLE_TARGET), os.path.join(studio, "Targets"))
    shutil.copytree(os.path.join(project.SAMPLES, "measurements", project.SAMPLE_DEVICE),
                    os.path.join(studio, "Measurements"))
    data = os.path.join(studio, "data")
    install_lists(os.path.join(data, "eq", "cache"))
    write_eq_settings(studio)
    apo_config = os.path.join(root, "apo", "config")
    os.makedirs(apo_config)
    with open(os.path.join(apo_config, "config.txt"), "w", encoding="utf-8") as fh:
        fh.write("# Equalizer APO's configuration: a stand-in for the tests (never the real one)\n")
    os.makedirs(os.path.join(root, "old"))

    env = os.environ
    for k in FOLDER_VARS + ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        env.pop(k, None)  # (nothing the run started with may point a test at a real folder)
    env.update(TEMP=tmp, TMP=tmp, USERPROFILE=home, HOME=home, APPDATA=os.path.join(home, "AppData", "Roaming"),
               LOCALAPPDATA=os.path.join(home, "AppData", "Local"), AUTOEQSTUDIO_ROOT=studio,
               AUTOEQSTUDIO_DATA=data, AUTOEQSTUDIO_DOCUMENTS=os.path.join(home, "Documents"),
               AUTOEQSTUDIO_APO_CONFIG=apo_config, AUTOEQSTUDIO_OLD_SETTINGS=os.path.join(root, "old", "settings.json"),
               AUTOEQSTUDIO_NO_MESSAGE_BOX="1", AUTOEQSTUDIO_TEST_SESSION=root, QT_QPA_PLATFORM="offscreen",
               PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    for k, v in (("AUTOEQSTUDIO_MAX_WORKERS", "2"), ("AUTOEQSTUDIO_TIME_FACTOR", "1"),
                 ("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")),
                 ("OPENBLAS_NUM_THREADS", "1"), ("OMP_NUM_THREADS", "1"), ("MKL_NUM_THREADS", "1")):
        env.setdefault(k, v)
    tempfile.tempdir = tmp
    sys.path.insert(0, app)
    SESSION = Session(root=root, tmp=tmp, home=home, studio=studio, app=app, data=data, apo_config=apo_config,
                      old_settings=os.path.join(root, "old", "settings.json"), real_temp=real_temp,
                      real_home=real_home, real_env=real_env)
    checks.log({"event": "session", "pid": os.getpid(), "root": root, "python": sys.executable})
    return SESSION


def inside(path, folder=None):
    """Is path in folder (the session folder when none is given)? Both taken the long way."""
    folder = folder or SESSION.root
    p, f = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(folder))
    return p == f or p.startswith(f.rstrip(os.sep) + os.sep)


def child_env(*, without_folders=False, keep_log=False, **overrides):
    """os.environ for a subprocess (the session's variables are in it already). without_folders: the
    AUTOEQSTUDIO_* folder variables left out; the check log's two variables are left out unless keep_log (a child,
    e.g. an inner pytest, never writes into the run's log); an override of None removes that variable."""
    env = dict(os.environ)
    for k in (FOLDER_VARS if without_folders else ()) + (() if keep_log else LOG_VARS):
        env.pop(k, None)
    for k, v in overrides.items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = str(v)
    return env


def cleanup():
    """The session folder deleted (20 tries, 0.3 s apart, while worker processes let go of its files); kept and said
    where with AUTOEQSTUDIO_KEEP_TEST_FOLDER=1."""
    if SESSION is None or not os.path.isdir(SESSION.root):
        return
    if os.environ.get("AUTOEQSTUDIO_KEEP_TEST_FOLDER") == "1":
        print(f"\nThe test folder is kept (AUTOEQSTUDIO_KEEP_TEST_FOLDER=1): {SESSION.root}")
        return
    if inside(os.getcwd()):
        os.chdir(SESSION.real_temp)  # (Windows can't delete the folder a process is working in)
    for _ in range(20):
        shutil.rmtree(SESSION.root, ignore_errors=True)
        if not os.path.exists(SESSION.root):
            return
        time.sleep(0.3)
    print(f"\nCouldn't delete the test folder (a process still holds it?): {SESSION.root}. The next run deletes it.")
