"""The tests' guard: a Python audit hook (sys.addaudithook, installed once per process by tests\\conftest.py) that
blocks, before it happens, and records, with the running test, anything a test must never do:
- write anywhere but the test folders: open() or os.open() for writing, making or deleting a folder or file,
  renaming, copying or moving onto, truncating, linking, changing a file's times or permissions. Allowed: the
  session folder (pytest's tmp_path is inside it), the check log's folder, the runner's output folder
  (AUTOEQSTUDIO_TEST_OUT), any __pycache__ folder, and NUL;
- connect to anything but this PC (V8 and Windows' text reader talk to themselves through local sockets), or look up
  any other host's address;
- write to the registry (a key made, deleted or opened for writing, a value set or deleted): Start with Windows'
  entry can't be touched even if a test forgets its stand-in;
- open a file or a link with Windows (os.startfile), a web page in the browser, or run a command through os.system;
- start the project's own app (app\\start.py, "AutoEQ Studio.bat"): copies in the session folder are fine, but never
  a start.py without a test data folder (AUTOEQSTUDIO_DATA), which would talk to your running app.
A blocked action raises PermissionError("test guard: ...") instead of happening, and the guard_check fixture then
fails the test, listing what was blocked.

Limits, said plainly: it sees Python's own calls in this process only, not what Qt or Windows do inside their C++
code, and not other processes (those get the session's folders through their environment instead). Opening a link
through Qt (QDesktopServices.openUrl) is replaced by a recorder in helpers.qt.app() instead.
"""
import contextlib
import os
import shlex
import sys
import threading

current = ""  # the running test (tests\conftest.py sets it as each test starts)

_violations = []
_expected = []  # (expect_blocked's lists, innermost last)
_roots = []
_installed = False
_busy = threading.local()
_project = {"start": None, "bat": None}

WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
# (registry rights that change something: set a value, make a key or a link, delete, change permissions or owner)
REG_WRITE = 0x0002 | 0x0004 | 0x0020 | 0x00010000 | 0x00040000 | 0x00080000
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "0:0:0:0:0:0:0:1", "::ffff:127.0.0.1"}
_PATH_ARG0 = {"os.mkdir", "os.remove", "os.rmdir", "shutil.rmtree", "os.truncate", "os.chmod", "os.utime"}
_PATH_ARG1 = {"shutil.copyfile", "shutil.copytree", "shutil.move", "os.link", "os.symlink"}
_REGISTRY = {"winreg.CreateKey", "winreg.DeleteKey", "winreg.DeleteValue", "winreg.SetValue", "winreg.SaveKey",
             "winreg.LoadKey"}
_WATCHED = frozenset({"open", "os.rename", "socket.connect", "socket.getaddrinfo", "winreg.OpenKey", "os.startfile",
                      "os.startfile/2", "webbrowser.open", "os.system", "subprocess.Popen"}
                     | _PATH_ARG0 | _PATH_ARG1 | _REGISTRY)

# The allowlist: places the tests' own tools must write to, each with its reason. (Empty: nothing has needed one.)
ALLOWLIST = ()


def _norm(path):
    return os.path.normcase(os.path.realpath(path))


def allow(path):
    """Let tests write under this folder too (taken the long way, as every path the guard compares)."""
    p = _norm(path)
    if p not in _roots:
        _roots.append(p)


def _allowed(full):
    return any(full == r or full.startswith(r.rstrip(os.sep) + os.sep) for r in _roots)


def _write(path, what):
    """Why this write must not happen, or None."""
    if path is None or isinstance(path, int):
        return None  # (an open file's number: it was opened through open(), already looked at)
    try:
        path = os.fsdecode(os.fspath(path))
    except TypeError:
        return None
    low = path.lower().replace("/", "\\")
    if low in ("nul", "con", "conout$", "conin$", "\\\\.\\nul") or low.startswith("\\\\.\\pipe\\"):
        return None  # (not files on a disk: nowhere, the console, a pipe between processes)
    full = _norm(path)
    if "__pycache__" in full.split(os.sep) or _allowed(full):
        return None
    if what == "os.mkdir" and os.path.isdir(full):
        return None  # (it's there already: os.makedirs(..., exist_ok=True) only checks, nothing is made)
    return f"a write outside the test folders ({what}: {path})"


def _host(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    return str(host).lower()


def _connect(address):
    if isinstance(address, tuple) and address:
        host = _host(address[0])
        if host in LOCAL_HOSTS or host.startswith("127."):
            return None
        return f"a connection to {host} (the tests stay offline: only this PC is allowed)"
    return None


def _lookup(host):
    if host is None or _host(host) in LOCAL_HOSTS or _host(host).startswith("127."):
        return None
    return f"a look-up of {_host(host)} on the internet (the tests stay offline)"


def _popen(executable, cmd, cwd, env):
    """The project's own app, or a start.py without a test data folder."""
    if isinstance(cmd, (bytes, os.PathLike)):
        cmd = os.fsdecode(cmd)
    if isinstance(cmd, str):
        try:
            parts = [p.strip('"') for p in shlex.split(cmd, posix=False)]
        except ValueError:
            parts = cmd.split()
    else:
        parts = [os.fsdecode(p) for p in cmd or [] if isinstance(p, (str, bytes, os.PathLike))]
    if executable:
        parts.append(os.fsdecode(executable))
    for p in parts:
        if not p.lower().endswith((".py", ".bat")):
            continue
        full = _norm(p if os.path.isabs(p) else os.path.join(cwd or os.getcwd(), p))
        if full in (_project["start"], _project["bat"]):
            return f"the project's own app started ({p}): only copies in the test folders may be started"
        if os.path.basename(full) == "start.py" and not (os.environ if env is None else env).get("AUTOEQSTUDIO_DATA"):
            return f"a copy of the app started without a test data folder (AUTOEQSTUDIO_DATA) ({p})"
    return None


def _judge(event, args):
    """Why this event must not happen, in plain words, or None."""
    if event == "open":
        flags = args[2] if len(args) > 2 else 0
        return _write(args[0], "open") if isinstance(flags, int) and flags & WRITE_FLAGS else None
    if event in _PATH_ARG0:
        return _write(args[0], event)
    if event == "os.rename":
        return _write(args[0], event) or _write(args[1], event)
    if event in _PATH_ARG1:
        return _write(args[1], event)
    if event == "socket.connect":
        return _connect(args[1])
    if event == "socket.getaddrinfo":
        return _lookup(args[0])
    if event in _REGISTRY:
        return f"a registry write ({event})"
    if event == "winreg.OpenKey":
        return "a registry key opened for writing (winreg.OpenKey)" if args[2] & REG_WRITE else None
    if event in ("os.startfile", "os.startfile/2"):
        return f"a file or link opened with Windows (os.startfile: {args[0]})"
    if event == "webbrowser.open":
        return f"a web page opened in the browser ({args[0]})"
    if event == "os.system":
        return f"a command run through os.system ({args[0]})"
    if event == "subprocess.Popen":
        return _popen(*args[:4])
    return None


def _hook(event, args):
    if event not in _WATCHED or getattr(_busy, "on", False):
        return  # (any other event at once; and none raised while the guard itself looks at a path)
    _busy.on = True
    try:
        why = _judge(event, args)
    except Exception:  # noqa: BLE001 - the guard's own mistake never stops what a test does
        why = None
    finally:
        _busy.on = False
    if why:
        record = f"{current or '(no test running)'}: {why}"
        (_expected[-1] if _expected else _violations).append(record)
        raise PermissionError(f"test guard: {why}")


def install(session):
    """The audit hook, once per process: the session folder, the check log's folder and the runner's output folder
    allowed (and ALLOWLIST)."""
    global _installed
    if _installed:
        return
    from helpers import paths as project
    allow(session.root)
    log = os.environ.get("AUTOEQSTUDIO_CHECK_LOG")
    if log:
        allow(os.path.dirname(os.path.abspath(log)))
    if os.environ.get("AUTOEQSTUDIO_TEST_OUT"):
        allow(os.environ["AUTOEQSTUDIO_TEST_OUT"])
    for place, _reason in ALLOWLIST:
        allow(place)
    _project.update(start=_norm(os.path.join(project.PROJECT_APP, "start.py")),
                    bat=_norm(os.path.join(project.PROJECT, "AutoEQ Studio.bat")))
    sys.addaudithook(_hook)
    _installed = True


def violations() -> list[str]:
    """What was blocked since clear(), each with its test."""
    return list(_violations)


def clear():
    _violations.clear()


@contextlib.contextmanager
def expect_blocked():
    """For tests\\infra: an action blocked inside is expected, not a failure. Yields the list of what was blocked
    (each still raises PermissionError where it happens)."""
    got = []
    _expected.append(got)
    try:
        yield got
    finally:
        _expected.remove(got)
