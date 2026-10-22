"""What this PC has, for the tests that need it: each function answers (True, what was found) or (False, why not, in
plain words). require(what, check, "name", ...) skips a test when it's missing: through check.skipped, so the
check names are logged as skipped, with the reason, never as missing.

The same tests run on GitHub's Windows machine: there a test skips, and says why, where that machine lacks
something (an interactive desktop for the hotkey, Windows' text reader, Claude's notes).
"""
import ctypes
import os
import shutil
import sys
from ctypes import wintypes

from helpers import paths, session


def iscc_path():
    """Inno Setup 6's compiler (ISCC.exe) in the places make_installer.ISCC lists, but read from the variables the
    run started with (SESSION.real_env): on this PC Inno Setup is installed for the user only, under the real
    LOCALAPPDATA, which the session replaces. None when it isn't installed."""
    env = session.SESSION.real_env if session.SESSION else os.environ
    tops = [os.path.join(env["LOCALAPPDATA"], "Programs") if env.get("LOCALAPPDATA") else None,
            env.get("ProgramFiles(x86)"), env.get("ProgramFiles")]
    for top in tops:
        if top and os.path.isfile(os.path.join(top, "Inno Setup 6", "ISCC.exe")):
            return os.path.join(top, "Inno Setup 6", "ISCC.exe")
    return None


def iscc():
    p = iscc_path()
    return (True, p) if p else (False, "Inno Setup 6 isn't installed here (its compiler, ISCC.exe, wasn't found)")


def ocr_ready():
    """Windows' text reader, with a language installed for it (the tracer reads axis labels with it). Qt is loaded
    first, as in the app: Qt loaded after the reader has started crashes Python (an access violation; checked
    2026-10-22 with PySide6 6.11 and winrt 3.2)."""
    try:
        import PySide6.QtWidgets  # noqa: F401
        from ui import ocr
        ocr._get_engine()
    except Exception as e:  # noqa: BLE001 - ocr.Unavailable, or the winrt packages missing
        return False, f"Windows' text reader isn't available here: {e}"
    return True, "Windows' text reader"


def interactive_desktop():
    """A desktop a person could see (not a service's or a build machine's): the hotkey needs one."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetProcessWindowStation.restype = wintypes.HANDLE

    class Flags(ctypes.Structure):
        _fields_ = [("fInherit", wintypes.BOOL), ("fReserved", wintypes.BOOL), ("dwFlags", wintypes.DWORD)]
    user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                                 ctypes.POINTER(wintypes.DWORD)]
    flags, needed = Flags(), wintypes.DWORD()
    station = user32.GetProcessWindowStation()
    if not station or not user32.GetUserObjectInformationW(station, 1, ctypes.byref(flags), ctypes.sizeof(flags),
                                                           ctypes.byref(needed)):
        return False, "Windows didn't say whether this runs on a desktop"
    if flags.dwFlags & 1:  # (WSF_VISIBLE)
        return True, "an interactive desktop"
    return False, "no interactive desktop here (a service or a build machine): no hotkey can be registered"


def project_venv():
    """The Python environment the tests run in (.venv): sys.prefix when it's one, else the project's .venv."""
    if sys.prefix != sys.base_prefix:
        return True, sys.prefix
    p = os.path.join(paths.PROJECT, ".venv")
    return (True, p) if os.path.isdir(p) else (False, "no Python environment (.venv) here: setup.bat makes one")


def ruff():
    """Ruff, the linter: beside this Python, else in the project's .venv, else on PATH."""
    for p in (os.path.join(os.path.dirname(sys.executable), "ruff.exe"),
              os.path.join(paths.PROJECT, ".venv", "Scripts", "ruff.exe")):
        if os.path.isfile(p):
            return True, p
    p = shutil.which("ruff")
    return (True, p) if p else (False, "Ruff isn't installed here: \".venv\\Scripts\\python.exe\" -m pip install -r "
                                       "app\\requirements-dev.txt")


def claude_notes():
    """Claude's notes (.claude\\CLAUDE.md): on the developer's PC only (git leaves .claude out)."""
    p = os.path.join(paths.PROJECT, ".claude", "CLAUDE.md")
    return (True, p) if os.path.isfile(p) else (False, "no .claude\\CLAUDE.md here (Claude's notes are on the "
                                                       "developer's PC only: git leaves them out)")


def require(what, check=None, *names):
    """Skip the test, with the reason, when `what` (one of the functions above, its name, or its answer) is missing:
    through check.skipped(reason, *names) when a check and the test's check names are given. Returns what was found."""
    if isinstance(what, str):
        what = globals()[what]
    ok, said = what() if callable(what) else what
    if not ok:
        if check is not None and names:
            check.skipped(said, *names)
        import pytest
        pytest.skip(said)
    return said
