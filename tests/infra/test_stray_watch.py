"""The stray watch (helpers\\qt.py's StrayWatch, installed by qt.app()) with the stray_check fixture
(helpers\\fixtures_core.py), on an inner pytest run: a control shown as a window of its own fails the test in which it
showed, naming it; a control inside a dialog does not; a test marked allow_strays passes with a note. The test audit
of 2026-11-25 found that no test showed a stray on purpose: test_opening.py's last test could only see that the watch
was there, so a watch that recorded nothing would have passed every test."""
from helpers import inner, qt

pytest_plugins = ["pytester"]

STRAYS = '''
import pytest

from helpers import checks, qt


def _shown_alone(text):
    from PySide6.QtWidgets import QLabel
    label = QLabel(text)
    label.show()  # (no parent: a window of its own, as a control shown before it had its parent)
    qt.app().processEvents()
    qt.close(label)


def test_a_label_in_a_dialog(qapp):
    from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout
    dialog = QDialog()
    QVBoxLayout(dialog).addWidget(QLabel("In its dialog"))
    dialog.show()
    qapp.processEvents()
    qt.close(dialog)


def test_a_label_alone(qapp):
    _shown_alone("Alone")


@pytest.mark.allow_strays("the inner test of the stray watch shows one on purpose")
def test_a_label_alone_allowed(qapp):
    _shown_alone("Allowed")


def test_the_watch_then():
    watch = qt.stray_watch()
    checks.log({"event": "stray_watch", "installed": watch is not None,
                "found": list(watch.found) if watch is not None else None,
                "seen_any": watch.seen_any if watch is not None else None})
'''


def test_a_control_shown_alone_fails_its_test(pytester, monkeypatch, check):
    result, log = inner.run(pytester, monkeypatch, {"test_inner_strays.py": STRAYS}, "-q")
    failed = [r for r in log if r.get("event") == "check" and r.get("name") == qt.STRAY_CHECK and not r.get("ok")]
    allowed = [r for r in log if r.get("event") == "allowed_strays"]
    after = next((r for r in log if r.get("event") == "stray_watch"), None)
    seen = {"outcomes": result.parseoutcomes(),
            "failed": [(r["test"].split("::")[-1], r["detail"]) for r in failed],
            "allowed": [(r["test"].split("::")[-1], r["found"]) for r in allowed], "after": after}
    check("tests: a control shown as a window of its own fails the test in which it showed, naming it; a control in a "
          "dialog does not; a test marked allow_strays passes with a note line (the stray watch records each one)",
          # (stray_check fails a test after it, in its teardown: pytest counts the test as passed and the teardown as
          # an error)
          seen["outcomes"] == {"passed": 4, "errors": 1} and len(failed) == 1
          and failed[0]["test"].endswith("::test_a_label_alone") and "QLabel 'Alone'" in failed[0]["detail"]
          and len(allowed) == 1 and allowed[0]["test"].endswith("::test_a_label_alone_allowed")
          and "QLabel 'Allowed'" in str(allowed[0]["found"])
          and after == {"event": "stray_watch", "installed": True, "found": [], "seen_any": True}, seen)
