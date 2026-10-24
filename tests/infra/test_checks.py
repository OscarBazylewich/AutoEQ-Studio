"""The check fixture and the check log (helpers.checks, tests\\conftest.py; PLAN.md 3.6): names logged, a failed
check fails its test listing every failed name, check.skipped logs its names as skipped, an xfail test's report
says xfailed, an error inside a Qt call-back is logged and fails its test, a Qt object left for Python's garbage
collector is deleted after its test and fails it (tests\\conftest.py), and the log's lines. All on an
inner pytest run (its own process and check log: its deliberate failures never reach this run's log). And raises(),
the EQ part's tests' shared helper (a ValueError's message, or None)."""
from helpers import checks, inner

pytest_plugins = ["pytester"]

INNER = '''
import pytest


def test_names(check):
    check("inner: first", True)
    check("inner: second", 1 == 1)


def test_fails(check):
    check("inner: one", True)
    check("inner: two", False, "detail2")
    check("inner: three", False, "detail3")


def test_skips(check):
    check.skipped("no such thing here", "inner: skipped one", "inner: skipped two")


@pytest.mark.xfail(reason="a known bug")
def test_known_bug(check):
    check("inner: the known bug", False, "still there")


def test_qt_error(qapp):
    from PySide6.QtCore import QTimer
    from helpers import qt
    QTimer.singleShot(0, lambda: 1 / 0)
    qt.pump(300)
'''

LEFTOVER = '''
import weakref

KEPT = {}


def test_leaves_one(qapp):
    from PySide6.QtWidgets import QComboBox
    box = QComboBox()
    box.setObjectName("left behind")
    box.me = box  # (a loop of references: only Python's garbage collector would free it)
    KEPT["box"] = weakref.ref(box)


def test_after_it(qapp):
    import shiboken6
    box = KEPT["box"]()
    assert box is None or not shiboken6.isValid(box), "still there after the test that left it"


def test_lets_go(qapp):
    from PySide6.QtWidgets import QComboBox
    QComboBox().setObjectName("freed at once")  # (no loop: freed as soon as it's let go)
'''


LEFTOVER_FROZEN = '''
import gc


def test_leaves_one_set_aside(qapp):
    from PySide6.QtWidgets import QComboBox
    box = QComboBox()
    box.setObjectName("set aside")
    box.me = box  # (a loop of references: only Python's garbage collector would free it)
    del box
    gc.freeze()  # (as Make an EQ's opening does: what's alive now is out of the collector's reach)
'''


def test_qt_leftovers_set_aside(pytester, monkeypatch, check):
    # (2026-10-24, the checkers: Make an EQ's opening runs gc.freeze(), which takes what's alive out of the
    # collector's reach for good, so a Qt object left in a loop of references before it was never found)
    from helpers import qt
    result, log = inner.run(pytester, monkeypatch, {"test_inner_frozen.py": LEFTOVER_FROZEN}, "-q")
    found =[r for r in log if r["event"] == "check" and r["name"] == qt.LEFTOVER_CHECK]
    check("checks: a Qt object a test leaves for Python's garbage collector is found even when the collector was "
          "told to set what's alive aside (gc.freeze, as Make an EQ's opening does)",
          [(r["test"].split("::")[-1], r["ok"]) for r in found] == [("test_leaves_one_set_aside", False)]
          and "QComboBox “set aside”" in found[0]["detail"], (result.parseoutcomes(), found))


def test_qt_leftovers(pytester, monkeypatch, check):
    from helpers import paths, qt
    result, log = inner.run(pytester, monkeypatch, {"test_inner_leftovers.py": LEFTOVER}, "-q")
    said = [f for f in paths.import_tool("run_tests").summarize("inner", log, result.ret).fails if "test_leaves_one" in f]
    reports = {(r["test"].split("::")[-1], r["when"]): r for r in log if r["event"] == "report"}
    found = [r for r in log if r["event"] == "check" and r["name"] == qt.LEFTOVER_CHECK]
    torn = reports.get(("test_leaves_one", "teardown"), {})
    check("checks: a Qt object a test leaves for Python's garbage collector is deleted after that test, when Qt "
          "handles no event (never in the middle of a later test's events), and fails it, naming the object (one FAIL "
          "line in the run's summary)",
          [(r["test"].split("::")[-1], r["ok"]) for r in found] == [("test_leaves_one", False)]
          and "QComboBox “left behind”" in found[0]["detail"]
          and torn.get("outcome") == "failed" and torn.get("message", "").startswith("FAIL ")
          and reports.get(("test_after_it", "call"), {}).get("outcome") == "passed"
          and reports.get(("test_lets_go", "teardown"), {}).get("outcome") == "passed"
          and result.parseoutcomes() == {"passed": 3, "errors": 1} and len(said) == 1,
          (torn, result.parseoutcomes(), said, found))


def test_check_fixture_and_log(pytester, monkeypatch, check):
    result, log = inner.run(pytester, monkeypatch, {"test_inner_checks.py": INNER}, "-q")
    out = "\n".join(result.outlines)
    names = {(r["name"], r["ok"]) for r in log if r["event"] == "check"}
    reports = {(r["test"].split("::")[-1], r["when"]): r for r in log if r["event"] == "report"}
    errors = [r for r in log if r["event"] == "qt_error"]
    session_lines = [r for r in log if r["event"] == "session"]
    starts = [r["test"].split("::")[-1] for r in log if r["event"] == "start"]

    check("checks: each check is logged with its test, its name and ok (true or false, with the detail cut short)",
          {("inner: first", True), ("inner: second", True), ("inner: one", True), ("inner: two", False),
           ("inner: three", False), ("inner: the known bug", False)} <= names
          and any(r.get("detail") == "detail2" and r["test"].endswith("::test_fails") for r in log), sorted(names))
    check("checks: a failed check doesn't stop its test; the test then fails listing every failed check",
          "check(s) failed:" in out and "FAIL inner: two  (detail2)" in out and "FAIL inner: three  (detail3)" in out
          and reports.get(("test_fails", "call"), {}).get("outcome") == "failed"
          and reports.get(("test_names", "call"), {}).get("outcome") == "passed", out[-800:])
    skipped = [r for r in log if r["event"] == "check" and r.get("skipped")]
    check("checks: check.skipped logs each name as skipped, with the reason, and skips the test",
          sorted(r["name"] for r in skipped) == ["inner: skipped one", "inner: skipped two"]
          and all(r["ok"] is None and r["detail"] == "no such thing here" for r in skipped)
          and reports.get(("test_skips", "call"), {}).get("outcome") == "skipped"
          and reports[("test_skips", "call")].get("message") == "no such thing here", skipped)
    check("checks: a test marked xfail that fails is reported as xfailed, with its reason",
          reports.get(("test_known_bug", "call"), {}).get("outcome") == "xfailed"
          and reports[("test_known_bug", "call")].get("message") == "a known bug",
          reports.get(("test_known_bug", "call")))
    torn = reports.get(("test_qt_error", "teardown"), {})
    check("checks: an error inside a Qt call-back is logged (qt_error, with its test) and fails the test it happened "
          "in, naming the error (since 2026-10-22: before, it was only noted)",
          len(errors) == 1 and "ZeroDivisionError" in errors[0]["text"] and errors[0]["test"].endswith("::test_qt_error")
          and torn.get("outcome") == "failed" and "Qt call-back" in torn.get("message", "")
          and "ZeroDivisionError" in torn.get("message", ""), (errors, torn))
    check("checks: the log has the session's line, a start line per test and a report per phase; the run's summary "
          "agrees",
          len(session_lines) == 1 and {"pid", "root", "python"} <= set(session_lines[0])
          and starts == ["test_names", "test_fails", "test_skips", "test_known_bug", "test_qt_error"]
          and all((t, w) in reports for t in starts for w in ("setup", "call", "teardown") if t != "test_skips")
          and result.parseoutcomes() == {"failed": 1, "passed": 2, "skipped": 1, "xfailed": 1, "errors": 1}
          and result.ret == 1, (result.parseoutcomes(), starts))


def test_raises(check):
    def refuse(x):
        raise ValueError(f"no {x}")
    try:
        checks.raises(lambda: 1 / 0)
        through = False
    except ZeroDivisionError:
        through = True
    check("checks: raises() gives the message of the ValueError a call raises (the app's way of refusing), None when "
          "it raises nothing, and lets any other error through (the test then fails on it)",
          checks.raises(refuse, 3) == "no 3" and checks.raises(len, [1]) is None and through)


def test_strict_xpass_fails(pytester, monkeypatch, check):
    test = ("import pytest\n"
            "@pytest.mark.xfail(reason='fixed now?')\n"
            "def test_fixed(check):\n"
            "    check('inner: fixed', True)\n")
    result, log = inner.run(pytester, monkeypatch, {"test_inner_xpass.py": test}, "-q")
    call = next((r for r in log if r["event"] == "report" and r["when"] == "call"), {})
    check("checks: a test marked xfail that passes fails the run (xfail_strict), logged as failed with XPASS(strict)",
          result.ret == 1 and call.get("outcome") == "failed" and "XPASS(strict)" in call.get("message", ""), call)
