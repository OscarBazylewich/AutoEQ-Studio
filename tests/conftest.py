"""Every test runs on temporary folders and a temporary copy of the app: never your files, the real Equalizer APO
folder, AppData, the registry or the internet.

Before any test file is read (pytest reads this file first), helpers.session makes this run's own folder in TEMP: a
stand-in home, a stand-in Equalizer APO folder and a copy of the app with its samples, and points every variable the
app reads for its folders there; this process goes into a Windows job object of its own (helpers.subproc), so
everything it starts, the app's fitting workers too, ends when it ends, however it ends; the app's `paths` is then
loaded from that copy, and the guard (helpers.guard) blocks and reports anything a test must never do. The folder is
deleted when the run ends.

What else happens here, for every test:
- tests that open Make an EQ (every file in tests\\eq_screen, any test using the eq_screen fixture, any file that
  imports helpers.eqpage) are marked slow: selftest.py --quick leaves them out, as the old --quick left out the EQ
  part; the check log names the slow tests --quick left out (relevant_tests.py's quick run says how many);
- a test that used the check fixture fails, after it ran, listing every check that failed;
- after each test, once its fixtures (and after a file's last test, the file's) are taken down: the Qt objects it left
  for Python's garbage collector are deleted then, and fail it (helpers.qt.free_leftovers: left, one could be deleted
  in the middle of a later test's events, which crashes the process);
- the check log (AUTOEQSTUDIO_CHECK_LOG) gets a line as each test starts and one per phase of it (setup, call,
  teardown: its outcome, how long it took, and the last line of a failure, a skip's reason or an xfail's reason);
- at the end, the stray watch's one "ok" line (no control was ever shown as a window of its own), when Qt was used.
"""
import ast
import os
import sys

import pytest

sys.dont_write_bytecode = True  # (no __pycache__ for the app's copy, the helpers or the tools)
from helpers import session  # noqa: E402  (tests\ is on the path: pytest.ini)

SESSION = session.prepare()  # the folders, the variables, the app's copy, the studio (PLAN.md 3.9)
from helpers import subproc  # noqa: E402

subproc.contain_this_process()  # (this process in its job object: all it starts ends with it, however it ends)
import paths  # noqa: E402,F401  (the copy's: loaded before any tool can put the project's app\ first on the path)
from helpers import guard  # noqa: E402

guard.install(SESSION)  # the audit hook (PLAN.md 3.9)
pytest_plugins = ["helpers.fixtures_core", "helpers.fixtures_eq", "helpers.fixtures_screen"]

from helpers import checks, qt  # noqa: E402
from helpers import paths as project  # noqa: E402

_SCREEN = os.path.join(project.TESTS, "eq_screen")
_eqpage_files = {}


def _under(path, folder):
    p, f = os.path.normcase(os.path.realpath(str(path))), os.path.normcase(os.path.realpath(folder))
    return p.startswith(f.rstrip(os.sep) + os.sep)


def _imports_eqpage(path):
    """Does this test file import helpers.eqpage, in any form and anywhere in it (inside functions too)? Read with
    ast, once per file: nothing of it is run."""
    key = os.path.normcase(str(path))
    if key not in _eqpage_files:
        try:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
        except (OSError, SyntaxError, ValueError):
            tree = None
        found = False
        for node in ast.walk(tree) if tree is not None else ():
            if isinstance(node, ast.Import):
                found |= any(a.name == "helpers.eqpage" or a.name.startswith("helpers.eqpage.") for a in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level:
                mod = node.module or ""
                found |= (mod == "helpers.eqpage" or mod.startswith("helpers.eqpage.")
                          or (mod == "helpers" and any(a.name == "eqpage" for a in node.names)))
        _eqpage_files[key] = found
    return _eqpage_files[key]


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # (tmp_path inside the session folder, spelled the long way as pytest spells it: before pytest's own
    # pytest_configure reads it)
    config.option.basetemp = os.path.join(SESSION.root, "pytest")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    for item in items:
        if (_under(item.path, _SCREEN) or "eq_screen" in getattr(item, "fixturenames", ())
                or _imports_eqpage(item.path)):
            item.add_marker(pytest.mark.slow)


def pytest_deselected(items):
    # (the slow tests --quick, -m "not slow", left out: named in the check log, so relevant_tests.py's quick run can
    # say how many of the tests a change needs it didn't run)
    slow = [item.nodeid for item in items if item.get_closest_marker("slow")]
    if slow:
        checks.log({"event": "left_out", "why": "slow", "tests": slow})


@pytest.hookimpl(wrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    result = yield
    check = pyfuncitem.funcargs.get("check")
    if isinstance(check, checks.Checks):
        check.raise_if_failed()
    return result


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    guard.current = item.nodeid


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    try:
        result = yield
    finally:  # (after every fixture's clean-up, a moment when Qt is handling no event)
        left = qt.free_leftovers()
    if left:
        checks.log({"event": "check", "test": item.nodeid, "name": qt.LEFTOVER_CHECK, "ok": False,
                    "detail": checks.short(f"left: {left}")})
        pytest.fail(f"FAIL {qt.LEFTOVER_CHECK}  (left: {left}; delete it before the test ends, helpers.qt.close, or "
                    f"give it a parent)", pytrace=False)
    return result


def pytest_runtest_logstart(nodeid, location):
    checks.log({"event": "start", "test": nodeid})


def _message(report):
    """The last line of a failure (without pytest.fail's "Failed: ", so a check's "FAIL …" from a clean-up reads as
    the check's line and isn't said twice in the run's summary), a skip's reason, or an xfail's reason."""
    if hasattr(report, "wasxfail"):
        return report.wasxfail
    if report.skipped and isinstance(report.longrepr, tuple):
        return str(report.longrepr[2]).removeprefix("Skipped: ")
    if report.failed:
        crash = getattr(report.longrepr, "reprcrash", None)
        lines = [line for line in str(crash.message if crash is not None else report.longreprtext).splitlines()
                 if line.strip()]
        return lines[-1].removeprefix("Failed: ") if lines else ""
    return ""


def pytest_runtest_logreport(report):
    outcome = report.outcome
    if hasattr(report, "wasxfail"):  # (marked xfail: failed as expected, or passed; a strict pass is a failure)
        outcome = "xfailed" if report.skipped else "xpassed"
    checks.log({"event": "report", "test": report.nodeid, "when": report.when, "outcome": outcome,
                "duration": round(report.duration, 3), "message": checks.short(_message(report))})


def pytest_sessionfinish(session, exitstatus):
    watch = qt.stray_watch()
    if watch is not None and watch.found:  # (shown after the last test: while a module's page was closed)
        checks.log({"event": "check", "test": guard.current, "name": qt.STRAY_CHECK, "ok": False,
                    "detail": checks.short(f"shown after the last test: {watch.found[:5]}")})
        print(f"\nFAIL {qt.STRAY_CHECK}  (shown after the last test: {watch.found[:5]})")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
    elif watch is not None and not watch.seen_any:
        checks.log({"event": "check", "test": "tests/conftest.py::stray_watch", "name": qt.STRAY_CHECK, "ok": True,
                    "detail": ""})
    left = guard.violations()
    if left:  # (blocked after the last test: while a module's or the session's fixtures were taken down)
        checks.log({"event": "guard", "test": guard.current, "blocked": left})
        print("\nThe test guard blocked, after the last test:\n" + "\n".join(left))
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_unconfigure(config):
    session.cleanup()
