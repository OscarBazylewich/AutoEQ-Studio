"""The check fixture and the check log (helpers.checks, tests\\conftest.py; PLAN.md 3.6): names logged, a failed
check fails its test listing every failed name, check.skipped logs its names as skipped, an xfail test's report
says xfailed, an error inside a Qt call-back is logged and doesn't fail its test, and the log's lines. All on an
inner pytest run (its own process and check log: its deliberate failures never reach this run's log)."""
from helpers import inner

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
    check("checks: an error inside a Qt call-back is logged (qt_error, with its test) and doesn't fail the test",
          len(errors) == 1 and "ZeroDivisionError" in errors[0]["text"] and errors[0]["test"].endswith("::test_qt_error")
          and reports.get(("test_qt_error", "call"), {}).get("outcome") == "passed", errors)
    check("checks: the log has the session's line, a start line per test and a report per phase; the run's summary "
          "agrees",
          len(session_lines) == 1 and {"pid", "root", "python"} <= set(session_lines[0])
          and starts == ["test_names", "test_fails", "test_skips", "test_known_bug", "test_qt_error"]
          and all((t, w) in reports for t in starts for w in ("setup", "call", "teardown") if t != "test_skips")
          and result.parseoutcomes() == {"failed": 1, "passed": 2, "skipped": 1, "xfailed": 1} and result.ret == 1,
          (result.parseoutcomes(), starts))


def test_strict_xpass_fails(pytester, monkeypatch, check):
    test = ("import pytest\n"
            "@pytest.mark.xfail(reason='fixed now?')\n"
            "def test_fixed(check):\n"
            "    check('inner: fixed', True)\n")
    result, log = inner.run(pytester, monkeypatch, {"test_inner_xpass.py": test}, "-q")
    call = next((r for r in log if r["event"] == "report" and r["when"] == "call"), {})
    check("checks: a test marked xfail that passes fails the run (xfail_strict), logged as failed with XPASS(strict)",
          result.ret == 1 and call.get("outcome") == "failed" and "XPASS(strict)" in call.get("message", ""), call)
