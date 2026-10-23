"""Other processes, always with the session's environment (helpers.session.child_env: the test folders, never the
check log): a bit of Python (run_python, start_python), a copy of the program (app_copy), a copy of it running
(RunningCopy), and ending a process with everything it started (kill_tree).

One Windows job object, which this test process holds, ends everything in it when this process ends, however it ends
(JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: Windows closes the job with the process). The test process itself goes in it as
the session starts (contain_this_process, from tests\\conftest.py), so everything it starts joins it by itself: the
app's own fitting workers too (concurrent.futures starts those, not this module), which otherwise sat idle forever
after a test process was stopped half way, waiting for work. Every process started here is also put in it right
after it starts: in a test process it's in already, but a bit of Python that imports this module on its own isn't
in the job itself. So a test process stopped half way (its time limit, a crash, a kill) leaves no copy of the app,
and no fitting worker, running: `taskkill /T` alone can't reach a child whose parent is gone.
"""
import atexit
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
_k32.GetCurrentProcess.restype = wintypes.HANDLE
_k32.CloseHandle.argtypes = [wintypes.HANDLE]
_KILL_ON_JOB_CLOSE = 0x2000
_EXTENDED_LIMITS = 9
_SET_QUOTA_AND_TERMINATE = 0x0100 | 0x0001
_job = []
# (contain_this_process's answer: is this process in the job, and if not, why not)
this_process = {"in_job": False, "why_not": "contain_this_process() wasn't called"}


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


def contain_this_process() -> bool:
    """This test process put into the job object (tests\\conftest.py, as the session starts), so everything it starts
    joins the job by itself and ends when it ends, however it ends. A process that is in a job object already (each
    part run_tests.py runs is in one of its own) gets this one inside that one: Windows 8 and later nest them. True
    when it's in; else this_process["why_not"] says why (the processes started here still go in one by one)."""
    if this_process["in_job"]:
        return True
    try:
        job = _job_handle()
    except OSError as e:
        this_process["why_not"] = f"no job object could be made ({e})"
        return False
    if not _k32.AssignProcessToJobObject(job, _k32.GetCurrentProcess()):
        this_process["why_not"] = f"Windows error {ctypes.get_last_error()} putting this process in its job object"
        return False
    this_process.update(in_job=True, why_not="")
    atexit.register(_say_left_running)  # (registered first, so it runs last: after the other exit functions)
    return True


class _ProcessIdList(ctypes.Structure):
    _fields_ = [("NumberOfAssignedProcesses", wintypes.DWORD), ("NumberOfProcessIdsInList", wintypes.DWORD),
                ("ProcessIdList", ctypes.c_size_t * 1024)]


_k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                           ctypes.c_void_p]
_PROCESS_ID_LIST = 3


def job_others() -> list[int]:
    """The processes in this process's job besides itself (their ids); [] when it has no job."""
    if not _job:
        return []
    info = _ProcessIdList()
    if not _k32.QueryInformationJobObject(_job[0], _PROCESS_ID_LIST, ctypes.byref(info), ctypes.sizeof(info), None):
        return []
    me = os.getpid()
    return [int(p) for p in info.ProcessIdList[:info.NumberOfProcessIdsInList] if int(p) != me]


def _say_left_running():
    """At the very end of a test process (its pools of workers already shut down: Python does that before the exit
    functions): what its tests started and left running goes into the check log, so run_tests.py names it; the job
    then ends it with this process. (Since the test process has a job of its own, the part's job in run_tests.py no
    longer sees such a process still running: the fix-ups' recheck, 2026-10-22.)"""
    left = job_others()
    end = time.monotonic() + 2  # (a process that's just ending still counts for a moment)
    while left and time.monotonic() < end:
        time.sleep(0.1)
        left = job_others()
    if left:
        from helpers import checks
        checks.log({"event": "left_running", "pids": left})


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
    environment (e.g. helpers.session.child_env(AUTOEQSTUDIO_DATA=..., ...): it keeps the session's folders). Refused
    unless env gives it, inside the session folder, its own data folder (then it has a one-copy channel of its own
    and no mutex: it can never reach the app you're running), the stand-in Equalizer APO folder (else it would use
    the real one) and EQ Switcher's stand-in settings, and every other folder it's given is there too
    (helpers.session.copy_env_problem)."""

    def __init__(self, app_dir, env):
        problem = session.copy_env_problem(app_dir, env)
        if problem:
            raise ValueError(f"A copy of the app isn't started: {problem}.")
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
