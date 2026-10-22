"""Other processes, always with the session's environment (helpers.session.child_env: the test folders, never the
check log): a bit of Python (run_python, start_python), a copy of the program (app_copy), a copy of it running
(RunningCopy), and ending a process with everything it started (kill_tree).

Every process started here is put into one Windows job object this test process holds, set to end everything in it
when this process ends (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; the processes those start join it too). So a test process
stopped half way (its time limit, a crash) leaves no copy of the app, and none of its fitting workers, running:
`taskkill /T` alone can't reach a child whose parent is gone.
"""
import ctypes
import dataclasses
import json
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes

from helpers import paths, qt, session


@dataclasses.dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str
    data: object  # the last line of stdout that reads as JSON, or None


# ---------------------------------------------------------------- the job object
class _BasicLimits(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", ctypes.c_uint64 * 6),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateJobObjectW.restype = wintypes.HANDLE
_k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
_k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
_k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
_k32.OpenProcess.restype = wintypes.HANDLE
_k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_KILL_ON_JOB_CLOSE = 0x2000
_EXTENDED_LIMITS = 9
_SET_QUOTA_AND_TERMINATE = 0x0100 | 0x0001
_job = []


def _job_handle():
    """This process's job object (made the first time; Windows closes it when this process ends, however it ends)."""
    if not _job:
        job = _k32.CreateJobObjectW(None, None)
        if not job:
            raise ctypes.WinError(ctypes.get_last_error())
        info = _ExtendedLimits()
        info.BasicLimitInformation.LimitFlags = _KILL_ON_JOB_CLOSE
        if not _k32.SetInformationJobObject(job, _EXTENDED_LIMITS, ctypes.byref(info), ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        _job.append(job)
    return _job[0]


def _into_job(proc):
    handle = _k32.OpenProcess(_SET_QUOTA_AND_TERMINATE, False, proc.pid)
    if not handle:
        return False  # (it has ended already)
    try:
        return bool(_k32.AssignProcessToJobObject(_job_handle(), handle))
    finally:
        _k32.CloseHandle(handle)


def _start(args, env, cwd=None, quiet=False):
    out = subprocess.DEVNULL if quiet else subprocess.PIPE
    proc = subprocess.Popen([str(a) for a in args], env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out,
                            stderr=out, text=not quiet, encoding=None if quiet else "utf-8",
                            errors=None if quiet else "replace")
    _into_job(proc)  # (at once: before it can start anything of its own)
    return proc


def _finish(proc, timeout):
    """(stdout, stderr) once it has ended; past the time limit it's ended with everything it started, and
    subprocess.TimeoutExpired raised."""
    try:
        return proc.communicate(timeout=qt.time_limit(timeout))
    except subprocess.TimeoutExpired:
        kill_tree(proc.pid)
        proc.communicate()
        raise


def _last_json(text):
    for line in reversed((text or "").strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------- Python
def run_python(code, *args, env=None, cwd=None, timeout=120) -> Result:
    """sys.executable -c code args, in the session's environment (env: variables to add or change; None removes
    one), waited for (time_limit(timeout)). data: the last line it printed that reads as JSON."""
    proc = _start([sys.executable, "-c", code, *args], session.child_env(**(env or {})), cwd)
    out, err = _finish(proc, timeout)
    return Result(proc.returncode, out, err, _last_json(out))


def start_python(code, *args, env=None, cwd=None) -> subprocess.Popen:
    """sys.executable -c code args, started and not waited for (quiet: its output goes nowhere), in the job object."""
    return _start([sys.executable, "-c", code, *args], session.child_env(**(env or {})), cwd, quiet=True)


def kill_tree(pid):
    """End a process and everything it started (taskkill /T /F), quietly."""
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------- copies of the app
def app_copy(dest, *, installed=False, test_build=False) -> str:
    """The project's app\\ copied to dest\\app, without its tools, Python's caches, data, installed.txt and
    test-build.txt (selftest.py's _app_copy); installed.txt (an installed copy) and test-build.txt (the installer's
    test build) written when asked. Returns the copy's app folder."""
    app = os.path.join(dest, "app")
    shutil.copytree(paths.PROJECT_APP, app, ignore=shutil.ignore_patterns(
        "__pycache__", "tools", "data", "installed.txt", "test-build.txt"))
    if installed:
        open(os.path.join(app, "installed.txt"), "w").close()
    if test_build:
        with open(os.path.join(app, "test-build.txt"), "w") as fh:
            fh.write("test")
    return app


class RunningCopy:
    """A copy of the app started as Windows would start it (sys.executable start.py ...), with `env` as its whole
    environment (e.g. helpers.session.child_env(AUTOEQSTUDIO_DATA=..., ...)). Refused unless env's
    AUTOEQSTUDIO_DATA is inside the session folder: then the copy has a one-copy channel of its own and no mutex
    (start.py), so it can never reach the app you're running."""

    def __init__(self, app_dir, env):
        data = (env or {}).get("AUTOEQSTUDIO_DATA")
        if not data or session.SESSION is None or not session.inside(data):
            raise ValueError("A copy of the app is started only with its own test data folder (AUTOEQSTUDIO_DATA "
                             "inside the session folder): without one it would talk to the app you're running.")
        self.app_dir, self.env = app_dir, dict(env)
        self.start_py = os.path.join(app_dir, "start.py")
        self.procs = []

    def start(self, *args) -> subprocess.Popen:
        """Started and not waited for (quiet), in the job object."""
        proc = _start([sys.executable, self.start_py, *args], self.env, quiet=True)
        self.procs.append(proc)
        return proc

    def run(self, *args, timeout=60) -> subprocess.CompletedProcess:
        """Started and waited for (time_limit(timeout)): its exit code, output and errors."""
        cmd = [sys.executable, self.start_py, *args]
        proc = _start(cmd, self.env)
        out, err = _finish(proc, timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, out, err)

    def log(self) -> str:
        """The copy's log (data\\app.log), "" when there's none yet."""
        try:
            with open(os.path.join(self.env["AUTOEQSTUDIO_DATA"], "app.log"), encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            return ""

    def started(self) -> int:
        """How many times the log says it started."""
        return self.log().count("started")

    def wait_started(self, n=1, sec=60) -> bool:
        """Wait (time_limit(sec)) until the log says it started n times."""
        end = time.monotonic() + qt.time_limit(sec)
        while self.started() < n:
            if time.monotonic() >= end:
                return False
            time.sleep(0.2)
        return True

    def stop(self):
        """--quit (as the installer asks), then anything of it still running ended."""
        try:
            self.run("--quit", timeout=60)
        except (OSError, subprocess.SubprocessError):
            pass
        for proc in self.procs:
            try:
                proc.wait(qt.time_limit(20))
            except subprocess.TimeoutExpired:
                kill_tree(proc.pid)
                proc.wait(10)
