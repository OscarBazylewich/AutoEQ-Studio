"""The guard (helpers.guard, PLAN.md 3.9): a write outside the test folders, a connection to the internet, a registry
write, opening a file or a link with Windows, and starting the project's own app are each blocked before they
happen and reported, with the test that tried. Each attempt is made so that, even if the guard didn't stop it,
nothing would reach your PC: a file in TEMP, an address that leads nowhere, a registry handle that's no handle, a
program that isn't there."""
import ctypes
import os
import shutil
import socket
import subprocess
import webbrowser
import winreg

from helpers import guard, inner, paths, session

pytest_plugins = ["pytester"]
S = session.SESSION


def _short(path):
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.windll.kernel32.GetShortPathNameW(path, buf, 1024)
    return buf.value if 0 < n < 1024 else path


def _attempt(fn):
    """What an attempt raised: "blocked" for the guard's PermissionError, else the error's kind, or "done"."""
    try:
        fn()
    except PermissionError as e:
        return "blocked" if str(e).startswith("test guard:") else f"PermissionError: {e}"
    except Exception as e:  # noqa: BLE001 - any other error: the attempt wasn't blocked by the guard
        return type(e).__name__
    return "done"


def test_writes_outside_blocked(tmp_path, check):
    probe = f"aeqs-guard-probe-{os.getpid()}"
    real_temp, short_temp = S.real_temp, _short(S.real_temp)
    src = os.path.join(tmp_path, "src.txt")
    with open(src, "w") as fh:
        fh.write("x")
    attempts = {
        "open for writing": lambda: open(os.path.join(real_temp, probe + ".txt"), "w"),
        "open, TEMP spelled short": lambda: open(os.path.join(short_temp, probe + "-short.txt"), "a"),
        "os.open": lambda: os.open(os.path.join(real_temp, probe + ".os"), os.O_WRONLY | os.O_CREAT),
        "os.mkdir": lambda: os.mkdir(os.path.join(real_temp, probe + "-dir")),
        "shutil.copyfile": lambda: shutil.copyfile(src, os.path.join(real_temp, probe + ".copy")),
        "os.rename into": lambda: os.rename(os.path.join(tmp_path, "none.txt"), os.path.join(real_temp, probe)),
        "os.remove": lambda: os.remove(os.path.join(real_temp, probe + ".never-there")),
        "os.rmdir": lambda: os.rmdir(os.path.join(real_temp, probe + "-never-there")),
        "the project's folder": lambda: open(os.path.join(paths.PROJECT, probe + ".txt"), "w"),
    }
    with guard.expect_blocked() as blocked:
        said = {k: _attempt(fn) for k, fn in attempts.items()}
    made = [n for n in os.listdir(real_temp) if n.startswith(probe)] + \
        [n for n in os.listdir(paths.PROJECT) if n.startswith(probe)]
    check("guard: a write outside the test folders (open, os.open, a folder made, a copy, a rename, a delete; TEMP "
          "spelled either way, the project's folder) is blocked before it happens and reported with its test",
          all(v == "blocked" for v in said.values()) and not made and len(blocked) == len(attempts)
          and all(b.startswith("tests/infra/test_guard.py::test_writes_outside_blocked: a write outside") for b in blocked),
          (said, made, blocked[:2]))


def test_internet_blocked_and_this_pc_allowed(check):
    def connect_far():
        with socket.socket() as s:
            s.settimeout(2)
            s.connect(("192.0.2.1", 80))  # (TEST-NET-1: an address that leads nowhere, should the guard fail)

    with guard.expect_blocked() as blocked:
        said = {"look-up": _attempt(lambda: socket.getaddrinfo("example.invalid", 443)),
                "connection": _attempt(connect_far),
                "create_connection": _attempt(lambda: socket.create_connection(("example.invalid", 80), timeout=2))}
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with guard.expect_blocked() as local_blocked:
            local = _attempt(lambda: socket.create_connection(server.getsockname(), timeout=5).close())
    check("guard: a look-up or a connection to the internet is blocked before it happens and reported; this PC "
          "(127.0.0.1, as V8 and the text reader use) is allowed",
          all(v == "blocked" for v in said.values()) and len(blocked) == 3 and local == "done" and not local_blocked,
          (said, local, blocked))


def test_registry_writes_blocked(check):
    never = r"Software\AutoEQ Studio tests (never made)"
    with guard.expect_blocked() as blocked:
        said = {"a key made": _attempt(lambda: winreg.CreateKey(0, never)),
                "a key opened for writing": _attempt(lambda: winreg.OpenKey(winreg.HKEY_CURRENT_USER, never, 0,
                                                                            winreg.KEY_SET_VALUE)),
                "a value set": _attempt(lambda: winreg.SetValueEx(0, "x", 0, winreg.REG_SZ, "y")),
                "a value deleted": _attempt(lambda: winreg.DeleteValue(0, "x")),
                "a key deleted": _attempt(lambda: winreg.DeleteKey(0, never))}

    def read():
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software", 0, winreg.KEY_READ):
            pass
    with guard.expect_blocked() as read_blocked:
        reading = _attempt(read)
    check("guard: a registry write (a key made, opened for writing or deleted, a value set or deleted) is blocked "
          "before it happens and reported; reading is allowed",
          all(v == "blocked" for v in said.values()) and len(blocked) == 5 and reading == "done" and not read_blocked,
          (said, reading))


def test_opening_with_windows_blocked(tmp_path, check):
    with guard.expect_blocked() as blocked:
        said = {"os.startfile": _attempt(lambda: os.startfile(os.path.join(tmp_path, "nothing here.txt"))),
                "a web page": _attempt(lambda: webbrowser.GenericBrowser("aeqs-no-such-browser")
                                       .open("https://example.invalid/")),
                "os.system": _attempt(lambda: os.system("rem"))}
    check("guard: opening a file or a link with Windows (os.startfile), a web page and os.system are blocked before "
          "they happen and reported", all(v == "blocked" for v in said.values()) and len(blocked) == 3, said)


def test_project_app_start_blocked(tmp_path, check):
    nowhere = os.path.join(tmp_path, "no python here.exe")  # (a program that isn't there, should the guard fail)
    copy_start = os.path.join(tmp_path, "copy", "start.py")
    no_data = {k: v for k, v in os.environ.items() if k != "AUTOEQSTUDIO_DATA"}
    no_apo = {k: v for k, v in os.environ.items() if k != "AUTOEQSTUDIO_APO_CONFIG"}
    real_home = dict(os.environ, USERPROFILE=S.real_home)
    with guard.expect_blocked() as blocked:
        said = {"the project's start.py": _attempt(lambda: subprocess.Popen(
                    [nowhere, os.path.join(paths.PROJECT_APP, "start.py"), "--quit"])),
                "the project's AutoEQ Studio.bat": _attempt(lambda: subprocess.Popen(
                    [nowhere, "/c", os.path.join(paths.PROJECT, "AutoEQ Studio.bat")])),
                "a start.py without a test data folder": _attempt(lambda: subprocess.Popen(
                    [nowhere, copy_start, "--quit"], env=no_data)),
                # (the foundation's review: it would use the real APO folder, or your real files)
                "a start.py without the stand-in APO folder": _attempt(lambda: subprocess.Popen(
                    [nowhere, copy_start, "--uninstall"], env=no_apo)),
                "a start.py given your real home": _attempt(lambda: subprocess.Popen(
                    [nowhere, copy_start, "--quit"], env=real_home))}
    with guard.expect_blocked() as copy_blocked:
        copy = _attempt(lambda: subprocess.Popen([nowhere, copy_start, "--quit"]))
    check("guard: starting the project's own app (start.py, AutoEQ Studio.bat), or any start.py without a test data "
          "folder, is blocked before it happens and reported; a copy with its own test data folder may start",
          all(v == "blocked" for v in said.values()) and len(blocked) == 5 and copy == "FileNotFoundError"
          and not copy_blocked, (said, copy))


def test_guard_check_fails_the_test(pytester, monkeypatch, check):
    probe = os.path.join(S.tmp, f"aeqs-inner-probe-{os.getpid()}.txt")  # (the inner run's TEMP: outside its folder)
    test = ("import os\n"
            "def test_writes_outside(check):\n"
            "    try:\n"
            f"        open({probe!r}, 'w').close()\n"
            "    except PermissionError:\n"
            "        pass  # (swallowed, as the app's own code may swallow an OSError)\n"
            "    check('inner: the test itself goes on', True)\n")
    result, log = inner.run(pytester, monkeypatch, {"test_inner_guard.py": test}, "-q")
    out = "\n".join(result.outlines)
    check("guard: a test whose blocked action was swallowed still fails, at its end, listing what was blocked",
          result.ret == 1 and "The test guard blocked what a test must never do" in out
          and "a write outside the test folders" in out and not os.path.exists(probe)
          and any(r.get("when") == "teardown" and r.get("outcome") == "failed" for r in log), out[-600:])
