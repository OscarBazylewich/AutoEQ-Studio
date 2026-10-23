r"""AutoEQ Studio's tests (the tests folder), each part in a process of its own, and a short summary in plain words.

    ".venv\Scripts\python.exe" app\tools\run_tests.py [PATHS ...] [--quick] [--jobs N] [--out DIR] [--all]
                                                      [--timeout MINUTES] [-- PYTEST-ARGS]

PATHS      test folders or files (default: the whole tests folder; one test, file.py::test_name, works too). They are
           grouped by part, the first folder under tests\ (switcher, eq, eq_screen, ui...; tests\helpers and
           tests\fixtures hold no tests), and each part runs in a pytest process of its own: one part's windows,
           worker processes and loaded modules never meet another's.
--quick    leaves out the slow tests (Make an EQ's screen, long fitting runs). A part left with nothing to run says
           so: that's no failure.
--jobs N   how many parts run at once (AUTOEQSTUDIO_TEST_JOBS when it's set; else a quarter of the cores, 1 to 4).
--out DIR  keeps each part's check log (<part>.jsonl) and pytest's output (<part>.txt) in DIR. Without it they go in
           a temporary folder, deleted when everything passed and kept (its place printed) when not.
--all      also prints every check's own line, ok or FAIL, as the old self-test did.
--timeout  a part still running after this many minutes (default 30; fractions too: 0.5 is half a minute) is ended,
           with everything it started.
-- ...     anything after -- goes to pytest as it is (e.g. -- -k theme -x).

The summary, from the check logs: "ok" with a count for each part that passed; a FAIL line for each check or test
that failed (naming its test), and for a part whose process ended before its tests did (naming the last test it
started); a skip, xfail or note line for each test skipped, failing as expected (a known bug), or with an error inside
a Qt call-back (not a failure); the totals; and last "All checks passed." or "<n> check(s) failed.". Exit code 0 when
everything passed, 1 when not, 2 for a wrong command line. Without pytest it says so in one FAIL line (exit code 1):
the release tools show the self-test's FAIL lines.

Each part's process goes in a Windows job object of its own, which ends everything in it when it's closed: the runner
closes it when the part ends (or runs past --timeout), so no copy of the app, fitting worker or anything else a test
started is left running, even when pytest's own time limit ended the process at once.

For other tools: main(argv) and run(paths, quick=False, jobs=None, out=None, show_all=False, extra=()), each giving
the exit code.
"""
import argparse
import ctypes
import dataclasses
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOT_PARTS = ("helpers", "fixtures")  # (folders under tests\ that hold no tests: never a part)
INSTALL = r'".venv\Scripts\python.exe" -m pip install -r app\requirements-dev.txt'
NO_PYTEST = f"FAIL pytest isn't installed here (the tests need it): {INSTALL}"
NO_TIMEOUT_PLUGIN = f"FAIL pytest-timeout isn't installed here (the tests need it): {INSTALL}"
DEFAULT_TIMEOUT = 30.0  # minutes


# ---------------------------------------------------------------- the job object (Windows' own, through ctypes)
class _BasicLimits(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BasicLimits), ("IoInfo", ctypes.c_uint64 * 6),
                ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]


class _Accounting(ctypes.Structure):
    _fields_ = [("TotalUserTime", ctypes.c_int64), ("TotalKernelTime", ctypes.c_int64),
                ("ThisPeriodTotalUserTime", ctypes.c_int64), ("ThisPeriodTotalKernelTime", ctypes.c_int64),
                ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]


_KILL_ON_JOB_CLOSE = 0x2000          # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
_EXTENDED_LIMITS = 9                 # JobObjectExtendedLimitInformation
_ACCOUNTING = 1                      # JobObjectBasicAccountingInformation
_SET_QUOTA_AND_TERMINATE = 0x0100 | 0x0001

if sys.platform == "win32":
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _k32.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
                                               ctypes.c_void_p]
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
else:  # (the app is Windows only; elsewhere a part is simply ended on its own, with taskkill's stand-in below)
    _k32 = None


class Job:
    """One part's Windows job object: every process put in it, and everything those start, is ended when it's
    closed (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE). error: why it couldn't be made, or None."""

    def __init__(self):
        self.handle = None
        self.error = None
        if _k32 is None:
            self.error = "no job objects here (not Windows)"
            return
        handle = _k32.CreateJobObjectW(None, None)
        if not handle:
            self.error = f"Windows error {ctypes.get_last_error()} making a job object"
            return
        info = _ExtendedLimits()
        info.BasicLimitInformation.LimitFlags = _KILL_ON_JOB_CLOSE
        if not _k32.SetInformationJobObject(handle, _EXTENDED_LIMITS, ctypes.byref(info), ctypes.sizeof(info)):
            self.error = f"Windows error {ctypes.get_last_error()} setting up a job object"
            _k32.CloseHandle(handle)
            return
        self.handle = handle

    def add(self, pid) -> bool:
        """Put a process in the job (right after it started: before it can start anything of its own)."""
        if not self.handle:
            return False
        process = _k32.OpenProcess(_SET_QUOTA_AND_TERMINATE, False, int(pid))
        if not process:
            self.error = f"Windows error {ctypes.get_last_error()} opening the process"
            return False
        try:
            if _k32.AssignProcessToJobObject(self.handle, process):
                return True
            self.error = f"Windows error {ctypes.get_last_error()} putting the process in a job object"
            return False
        finally:
            _k32.CloseHandle(process)

    def active(self) -> int:
        """How many processes in the job are still running."""
        if not self.handle:
            return 0
        info = _Accounting()
        if not _k32.QueryInformationJobObject(self.handle, _ACCOUNTING, ctypes.byref(info), ctypes.sizeof(info),
                                              None):
            return 0
        return info.ActiveProcesses

    def close(self):
        """Close the job: Windows ends everything still running in it."""
        if self.handle:
            _k32.CloseHandle(self.handle)
            self.handle = None


def _kill_tree(pid):
    """A part ended without a job object: taskkill ends it and what it started (while its parent is still there)."""
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------- the parts
def _has_tests(folder):
    for _here, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]
        if any(f.startswith("test_") and f.endswith(".py") for f in files):
            return True
    return False


def _inside(path, folder):
    path, folder = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(folder))
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


def find_parts(paths=(), root=None, cwd=None) -> dict:
    """{part: [the paths pytest gets, from the project's folder]}: every path given put in its part, the first folder
    under tests\\ (the whole tests folder: every part in it; a test file straight in tests\\: the part "tests").
    A relative path is taken from the current folder when that's in the project (and the path is there), else from
    the project's folder. Raises ValueError, in plain words, for a path that isn't a test folder or file of this
    project."""
    root = os.path.abspath(root or PROJECT)
    tests = os.path.join(root, "tests")
    cwd = os.path.abspath(cwd or os.getcwd())
    parts = {}
    for given in list(paths) or [tests]:
        given = str(given)
        file_part, sep, rest = given.partition("::")
        full = os.path.normpath(os.path.join(cwd, file_part))
        if not os.path.isabs(file_part) and not (_inside(cwd, root) and os.path.exists(full)):
            full = os.path.normpath(os.path.join(root, file_part))
        if not os.path.exists(full):
            raise ValueError(f"no such test folder or file: {given}")
        try:
            rel = os.path.relpath(full, tests)
        except ValueError:  # (another drive)
            rel = os.pardir
        if rel == os.curdir:
            if sep:
                raise ValueError(f"not a test: {given}")
            for name in sorted(os.listdir(tests)):
                sub = os.path.join(tests, name)
                if os.path.isdir(sub) and name not in NOT_PARTS and not name.startswith((".", "__")) \
                        and _has_tests(sub):
                    parts.setdefault(name, []).append(f"tests/{name}")
                elif name.startswith("test_") and name.endswith(".py") and os.path.isfile(sub):
                    parts.setdefault("tests", []).append(f"tests/{name}")
            continue
        if rel == os.pardir or rel.startswith(os.pardir + os.sep):
            raise ValueError(f"{given} isn't in the tests folder ({tests})")
        first = rel.split(os.sep)[0]
        if first in NOT_PARTS:
            raise ValueError(f"{given}: tests\\{first} holds no tests (the tests' {first}), so it isn't a part")
        part = first if os.path.isdir(os.path.join(tests, first)) else "tests"
        parts.setdefault(part, []).append(os.path.relpath(full, root).replace(os.sep, "/") + sep + rest)
    for part, got in parts.items():  # (a part's own folder given: that alone, nothing inside it twice)
        whole = f"tests/{part}"
        parts[part] = [whole] if whole in got else list(dict.fromkeys(got))
    return parts


def _size(root, paths):
    """About how much a part has to do (its test files' size): the biggest parts start first."""
    total = 0
    for p in paths:
        full = os.path.join(root, p.partition("::")[0])
        if os.path.isfile(full):
            total += os.path.getsize(full)
            continue
        for here, dirs, files in os.walk(full):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            total += sum(os.path.getsize(os.path.join(here, f)) for f in files
                         if f.startswith("test_") and f.endswith(".py"))
    return total


def default_jobs():
    """AUTOEQSTUDIO_TEST_JOBS when it's a number of 1 or more; else a quarter of the cores, 1 to 4."""
    try:
        jobs = int(os.environ.get("AUTOEQSTUDIO_TEST_JOBS", ""))
    except ValueError:
        jobs = 0
    return jobs if jobs >= 1 else max(1, min(4, (os.cpu_count() or 1) // 4))


def part_env(part, out, side_by_side, base=None) -> dict:
    """A part's environment: its own check log and the runner's output folder; the worker cap and the time factor
    (kept when they're set already: a busy PC, or several runs at once, sets its own); no bytecode files, UTF-8
    output, and Python's own report of a crash."""
    env = dict(os.environ if base is None else base)
    env["AUTOEQSTUDIO_CHECK_LOG"] = os.path.join(out, f"{part}.jsonl")
    env["AUTOEQSTUDIO_TEST_OUT"] = out
    if not env.get("AUTOEQSTUDIO_MAX_WORKERS"):
        env["AUTOEQSTUDIO_MAX_WORKERS"] = str(max(1, min(4, (os.cpu_count() or 1) // (2 * max(1, side_by_side)))))
    if side_by_side > 1 and not env.get("AUTOEQSTUDIO_TIME_FACTOR"):
        env["AUTOEQSTUDIO_TIME_FACTOR"] = "2"  # (parts side by side: every check that times itself gets twice as long)
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", PYTHONFAULTHANDLER="1")
    return env


# ---------------------------------------------------------------- reading a part's check log
def read_log(path) -> list:
    """The check log's lines (one JSON object each); a line that can't be read (cut short as a process was ended)
    is left out."""
    records = []
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict):
                    records.append(record)
    except OSError:
        pass
    return records


def _plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def duration(seconds) -> str:
    """2.3 s, or 2 min 51 s."""
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, rest = divmod(int(round(seconds)), 60)
    return f"{minutes} min {rest} s"


def _code(code) -> str:
    """An exit code, with Windows' own form for a crash's (3221225477 is 0xC0000005, an access violation)."""
    if code is None:
        return "none"
    return f"{code} (0x{code & 0xFFFFFFFF:08X})" if code > 255 or code < 0 else str(code)


_TIMEOUT_LINE = re.compile(r"^\++ Timeout \++\s*$", re.M)  # (pytest-timeout's, before it ends the process)
_CRASH_LINE = re.compile(r"^(Windows fatal exception: .*|Fatal Python error: .*)$", re.M)  # (faulthandler's)
_COLLECT_TITLE = re.compile(r"^_+ ERROR collecting (.+?) _+\s*$")


def collection_errors(output) -> list:
    """pytest's errors in reading test files ("<file>: <the error>"), from its output."""
    found, current = {}, None
    for line in (output or "").splitlines():
        m = _COLLECT_TITLE.match(line)
        if m:
            current = m.group(1)
            found.setdefault(current, "")
        elif current and line.startswith("E   "):
            found[current] = line[4:].strip()  # (the last E line of the section: the error itself)
        elif line.startswith("ERROR ") and " - " not in line and line[6:].strip() not in found:
            found.setdefault(line[6:].strip(), "")
    return [f"{name}: {error}" if error else name for name, error in found.items()]


def _why_stopped(output):
    """Why pytest stopped before any test, from its output: an error reading a test file, a wrong argument, a crash,
    or its last line."""
    errors = collection_errors(output)
    if errors:
        return errors[0] + (f" (and {len(errors) - 1} more)" if len(errors) > 1 else "")
    lines = [line.strip() for line in (output or "").splitlines() if line.strip() and not line.startswith("# ")]
    for line in lines:
        if line.startswith("ERROR: "):
            return line[7:]
    crash = _CRASH_LINE.search(output or "")
    if crash:
        return crash.group(1)
    return lines[-1].strip(" !=") if lines else ""


def _found(found):
    """allowed_strays' list of [what showed, how many times], in words."""
    words = []
    for item in found or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            words.append(f"{item[0]} ({_plural(item[1], 'time')})")
        else:
            words.append(str(item))
    return ", ".join(words)


@dataclasses.dataclass
class PartResult:
    """One part's summary: its lines, ready to print."""
    part: str
    returncode: object
    seconds: float
    checks: int = 0
    tests: int = 0
    nothing_to_run: bool = False
    nothing_why: str = "pytest found no test to run here"
    fails: list = dataclasses.field(default_factory=list)        # "FAIL ..." lines
    skips: list = dataclasses.field(default_factory=list)        # "skip ..." and "xfail ..." lines
    notes: list = dataclasses.field(default_factory=list)        # "note ..." lines
    check_lines: list = dataclasses.field(default_factory=list)  # every check's own line (--all)
    last_started: str = ""

    def lines(self, show_all=False) -> list:
        """What's printed as the part ends: (--all: every check's line, then) its ok line or its FAIL lines."""
        out = list(self.check_lines) if show_all else []
        if self.fails:
            return out + self.fails
        if self.nothing_to_run:
            return out + [f"ok   {self.part}: nothing to run ({self.nothing_why})"]
        return out + [f"ok   {self.part}: {_plural(self.checks, 'check')} in {_plural(self.tests, 'test')} "
                      f"({duration(self.seconds)})"]


_PHASES = {"setup": "an error before the test ran (in setting it up)", "call": "the test failed",
           "teardown": "an error after the test (in its clean-up)"}


def summarize(part, records, returncode, *, seconds=0.0, txt="", output="", timed_out=False, timeout=None,
              quick=False) -> PartResult:
    """A part's summary from its check log's lines (records), its process's exit code and its pytest output text:
    see the module's docstring. txt: where its output is kept (named in a FAIL line about the process); timeout: the
    --timeout in minutes (named when timed_out)."""
    res = PartResult(part, returncode, seconds)
    started = {}             # test -> the phases reported (setup, call, teardown)
    failed_checks = set()    # tests with a failed check
    qt_errors = {}           # (test, text) -> how many times
    see = f"see {txt}" if txt else "see its pytest output"
    # (a test marked xfail, a known bug, fails as expected: its failed checks are no failure. Its report comes after
    # its checks, so these are found first)
    xfailed = {str(r.get("test") or "") for r in records if r.get("event") == "report"
               and r.get("outcome") == "xfailed"}
    for rec in records:
        event, test = rec.get("event"), str(rec.get("test") or "")
        if event == "start":
            started.setdefault(test, set())
            res.last_started = test
        elif event == "check":
            name, ok, detail = str(rec.get("name", "?")), rec.get("ok"), str(rec.get("detail") or "")
            if rec.get("skipped") or ok is None:
                res.check_lines.append(f"skip {name}  ({detail})")
                continue
            res.checks += 1
            if ok:
                res.check_lines.append(f"ok   {name}")
                continue
            if test in xfailed:
                res.check_lines.append(f"xfail {name}" + (f"  ({detail})" if detail else ""))
                continue
            failed_checks.add(test)
            res.check_lines.append(f"FAIL {name}" + (f"  ({detail})" if detail else ""))
            res.fails.append(f"FAIL {part}: {name}" + (f"  ({detail})" if detail else "") + f"  [{test}]")
        elif event == "report":
            when, outcome, message = rec.get("when"), rec.get("outcome"), str(rec.get("message") or "")
            started.setdefault(test, set()).add(when)
            if outcome == "failed":
                if test in failed_checks and message.startswith("FAIL "):
                    continue  # (failed because of its failed checks: they have their lines already)
                what = _PHASES.get(when, f"an error ({when})")
                res.fails.append(f"FAIL {part}: {what}" + (f": {message}" if message else "") + f"  [{test}]")
            elif outcome == "skipped":
                line = f"skip {test}: {message}"
                if line not in res.skips:
                    res.skips.append(line)
            elif outcome == "xfailed":
                res.skips.append(f"xfail {test}: {message}")
            elif outcome == "xpassed":
                res.notes.append(f"note {test}: marked as a known failure (xfail), but it passed: {message}")
        elif event == "qt_error":
            key = (test, str(rec.get("text") or ""))
            qt_errors[key] = qt_errors.get(key, 0) + 1
        elif event == "allowed_strays":
            res.notes.append(f"note {test}: shown as windows of their own, allowed by its allow_strays mark "
                             f"({rec.get('reason', '')}): {_found(rec.get('found'))}")
        elif event == "guard":
            blocked = [str(b) for b in rec.get("blocked") or []] or ["(nothing said)"]
            more = f" (and {len(blocked) - 1} more)" if len(blocked) > 1 else ""
            res.fails.append(f"FAIL {part}: the test guard blocked, after the last test: {blocked[0]}{more}  [{test}]")
    for (test, text), count in qt_errors.items():
        times = f" ({count} times)" if count > 1 else ""
        res.notes.append(f"note {test}: an error inside a Qt call-back (not a failure): {text}{times}")
    res.tests = len(started)

    # How the process ended.
    unfinished = bool(res.last_started) and "teardown" not in started.get(res.last_started, set())
    last = f"last test started: {res.last_started}" if res.last_started else "no test had started"
    crash = _CRASH_LINE.search(output or "")
    if timed_out:
        limit = duration(timeout * 60) if timeout else "its time limit"
        res.fails.append(f"FAIL {part}: still running after {limit} (--timeout), so it was ended with everything it "
                         f"started ({last}; {see})")
    elif returncode == 5 and not started:
        res.nothing_to_run = True
        if quick:
            res.nothing_why = "every test here is slow, and --quick leaves those out"
    elif unfinished:
        why = ("a test ran past its time limit; " if _TIMEOUT_LINE.search(output or "")
               else f"a crash: {crash.group(1)}; " if crash else "")
        res.fails.append(f"FAIL {part}: the test process ended without finishing ({why}exit code "
                         f"{_code(returncode)}; {last}; {see})")
    elif returncode not in (0, 1, 5):
        if not started:
            reason = _why_stopped(output)
            res.fails.append(f"FAIL {part}: pytest stopped before running any test (exit code "
                             f"{_code(returncode)}{': ' + reason if reason else ''}; {see})")
        else:
            res.fails.append(f"FAIL {part}: the test process ended badly after its last test (exit code "
                             f"{_code(returncode)}{'; ' + crash.group(1) if crash else ''}; {see})")
    elif returncode != 0 and not res.fails:
        errors = collection_errors(output)
        found = f": {errors[0]}" if errors else ", but its check log shows no failure"
        res.fails.append(f"FAIL {part}: pytest says something failed (exit code {_code(returncode)}){found}; {see}")
    return res


# ---------------------------------------------------------------- running
def _say(line=""):
    try:
        print(line, flush=True)
    except UnicodeEncodeError:  # (a console that lacks a character of a check's name: shown as ?)
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        print(line.encode(enc, "replace").decode(enc), flush=True)


def missing_packages() -> list:
    """What the tests need that this Python lacks: "pytest", "pytest_timeout" (looked for, not loaded)."""
    missing = []
    for name in ("pytest", "pytest_timeout"):
        try:
            found = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            missing.append(name)
    return missing


class _Running:
    """One part's pytest process, started in its own job object."""

    def __init__(self, part, paths, out, env, quick, extra, root):
        self.part = part
        self.log = os.path.join(out, f"{part}.jsonl")
        self.txt = os.path.join(out, f"{part}.txt")
        for path in (self.log, self.txt):  # (a log is added to, line by line: an old one in --out would mix in)
            if os.path.exists(path):
                os.remove(path)
        cmd = [sys.executable, "-m", "pytest", *paths, "-q", *(["-m", "not slow"] if quick else []), *extra]
        self.fh = open(self.txt, "wb")
        self.fh.write(f"# {subprocess.list2cmdline(cmd)}\n".encode("utf-8"))
        self.fh.flush()
        self.job = Job()
        self.started = time.monotonic()
        try:
            self.proc = subprocess.Popen(cmd, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=self.fh,
                                         stderr=subprocess.STDOUT)
        except OSError:
            self.job.close()
            self.fh.close()
            raise
        self.in_job = self.job.add(self.proc.pid)  # (at once: before pytest can start anything of its own)
        self.timed_out = False
        self.left_running = 0

    def end(self):
        """End the part now, with everything it started."""
        if self.in_job:
            self.job.close()
        else:
            _kill_tree(self.proc.pid)
        try:
            self.proc.wait(60)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(60)

    def finish(self):
        """After the part's process ended: anything it left running is ended (the job closed), the output closed."""
        if self.in_job:
            end = time.monotonic() + 2  # (a process that's just ending still counts for a moment)
            while self.job.active() and time.monotonic() < end:
                time.sleep(0.1)
            self.left_running = self.job.active()
        self.job.close()
        self.fh.close()


def run(paths=(), quick=False, jobs=None, out=None, show_all=False, extra=(), *, timeout=DEFAULT_TIMEOUT,
        root=None) -> int:
    """Run the tests in `paths` (default: all of them), each part in its own pytest process, up to `jobs` at once,
    and print the summary. out: a folder that keeps the logs (else a temporary one, deleted when all passed); extra:
    more arguments for pytest; timeout: minutes a part may run; root: the project's folder (default: this one's).
    Returns the exit code: 0 when everything passed, 1 when not, 2 for paths that aren't tests."""
    missing = missing_packages()
    if missing:
        _say(NO_PYTEST if "pytest" in missing else NO_TIMEOUT_PLUGIN)
        return 1
    root = os.path.abspath(root or PROJECT)
    try:
        parts = find_parts(paths, root)
    except ValueError as e:
        _say(f"run_tests.py: {e}")
        return 2
    order = sorted(parts, key=lambda p: (-_size(root, parts[p]), p))
    jobs = max(1, int(jobs)) if jobs else default_jobs()
    side_by_side = min(jobs, len(order)) if order else 1
    temporary = not out
    out = os.path.realpath(tempfile.mkdtemp(prefix="aeqs-run-")) if temporary else os.path.abspath(out)
    os.makedirs(out, exist_ok=True)
    base = dict(os.environ)
    limit = float(timeout or DEFAULT_TIMEOUT) * 60
    began = time.monotonic()
    results = []
    _say(f"Running the tests: {_plural(len(order), 'part')}, {min(jobs, len(order)) or 1} at a time "
         f"(each part's log: {out})")
    pending, running = list(order), []
    try:
        while pending or running:
            while pending and len(running) < jobs:
                part = pending.pop(0)
                try:
                    running.append(_Running(part, parts[part], out, part_env(part, out, side_by_side, base), quick,
                                            list(extra), root))
                except OSError as e:
                    res = PartResult(part, None, 0.0, fails=[f"FAIL {part}: pytest couldn't be started ({e})"])
                    for line in res.lines():
                        _say(line)
                    results.append(res)
            time.sleep(0.1)
            for r in list(running):
                code = r.proc.poll()
                if code is None and time.monotonic() - r.started > limit:
                    r.timed_out = True
                    r.end()
                    code = r.proc.returncode
                if code is None:
                    continue
                running.remove(r)
                r.finish()
                results.append(_report(r, code, quick, show_all, timeout))
    except KeyboardInterrupt:
        for r in running:
            r.end()
            r.finish()
        _say(f"Stopped (Ctrl+C): the parts still running were ended. The logs: {out}")
        return 1
    failed = [line for res in results for line in res.fails]
    for res in results:
        for line in res.skips:
            _say(line)
    for res in results:
        for line in res.notes:
            _say(line)
    if failed and temporary:
        _say(f"The logs are kept: {out} (each part's pytest output, <part>.txt, and check log, <part>.jsonl)")
    checks = sum(r.checks for r in results)
    tests = sum(r.tests for r in results)
    _say(f"{_plural(checks, 'check')}, {_plural(tests, 'test')}, {_plural(len(results), 'part')}, "
         f"{duration(time.monotonic() - began)}")
    if failed:
        _say(f"{len(failed)} check(s) failed.")
        return 1
    if temporary:
        shutil.rmtree(out, ignore_errors=True)
    _say("All checks passed." if tests else "Nothing ran: no test was left to run.")
    return 0


def _report(r, code, quick, show_all, timeout):
    """A part that ended: its summary, its lines printed at once."""
    try:
        with open(r.txt, encoding="utf-8", errors="replace") as fh:
            output = fh.read()
    except OSError:
        output = ""
    res = summarize(r.part, read_log(r.log), code, seconds=time.monotonic() - r.started, txt=r.txt, output=output,
                    timed_out=r.timed_out, timeout=timeout, quick=quick)
    if not r.in_job and r.job.error:
        res.notes.append(f"note {r.part}: its process couldn't be put in a job object of its own ({r.job.error}): "
                         "anything it started could have been left running")
    if r.left_running:
        res.notes.append(f"note {r.part}: {_plural(r.left_running, 'process')} its tests started were still running "
                         "when they ended (ended now, with the part's job object)")
    for line in res.lines(show_all):
        _say(line)
    return res


# ---------------------------------------------------------------- the command line
def _positive_int(text):
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError(f"not a number of parts at once (1 or more): {text}")
    return value


def _minutes(text):
    try:
        value = float(text)
    except ValueError:
        value = 0.0
    if not value > 0:
        raise argparse.ArgumentTypeError(f"not a number of minutes above 0 (e.g. 30, or 0.5): {text}")
    return value


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = []
    if "--" in argv:
        at = argv.index("--")
        argv, extra = argv[:at], argv[at + 1:]
    parser = argparse.ArgumentParser(prog="run_tests.py", description="AutoEQ Studio's tests, each part in its own "
                                     "process, with a short summary.", epilog="Anything after -- goes to pytest.")
    parser.add_argument("paths", nargs="*", help="test folders or files (default: the whole tests folder)")
    parser.add_argument("--quick", action="store_true", help="leave out the slow tests")
    parser.add_argument("--jobs", type=_positive_int, help="how many parts run at once")
    parser.add_argument("--out", help="keep the logs in this folder")
    parser.add_argument("--all", action="store_true", dest="show_all", help="also every check's own line")
    parser.add_argument("--timeout", type=_minutes, default=DEFAULT_TIMEOUT,
                        help="minutes a part may run (default 30)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:  # (a wrong command line: argparse said why)
        return e.code if isinstance(e.code, int) else 2
    return run(args.paths, quick=args.quick, jobs=args.jobs, out=args.out, show_all=args.show_all, extra=extra,
               timeout=args.timeout)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):  # (UTF-8 whatever the console: check names have characters like → and ⓘ)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
