"""The plain-words checks and the check log.

A test asks for the `check` fixture and calls it as the self-test called check(): check("what is true, in plain
words", condition, detail). Each prints "ok   name" or "FAIL name  (detail)", and a failed one doesn't stop the test:
every check of it runs, and the test then fails listing every failed name (tests\\conftest.py does that after the
test). A check that can't run here says so with check.skipped(reason, "name", ...): its names are logged as skipped,
with the reason, and the test is skipped.

The check log: when AUTOEQSTUDIO_CHECK_LOG names a file, every check adds one JSON line to it ({"event": "check",
"test", "name", "ok", "detail"}); tests\\conftest.py adds a line when each test starts and one per phase of it,
helpers.qt one per error inside a Qt call-back, and the session one line with its process and folder. Each line is
one write in append mode. app\\tools\\run_tests.py builds its summary from these lines, and the reorganization's
parity check reads the names.
"""
import json
import os
import sys
import threading
from typing import NoReturn

_lock = threading.Lock()
# (the log's file, taken once as the session starts: a test that changes the variable, e.g. to try child_env, can't
# move this run's log)
LOG = os.path.abspath(os.environ["AUTOEQSTUDIO_CHECK_LOG"]) if os.environ.get("AUTOEQSTUDIO_CHECK_LOG") else None


def short(text, n=300):
    """text, cut to n characters."""
    text = str(text)
    return text if len(text) <= n else text[:n - 1] + "…"


def log(record):
    """One line in the check log (nothing when AUTOEQSTUDIO_CHECK_LOG wasn't set as the session started)."""
    path = LOG
    if not path:
        return
    data = (json.dumps(record, ensure_ascii=False, default=str) + "\n").encode("utf-8")
    with _lock:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_BINARY)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)


def _say(line):
    try:
        print(line)
    except UnicodeEncodeError:  # (a console that lacks a character of the name: shown as ?)
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        print(line.encode(enc, "replace").decode(enc))


class Checks:
    """The check fixture of one test: check(name, ok, detail) as the self-test's check()."""

    def __init__(self, test: str):
        self.test = test
        self.failed: list[tuple[str, str]] = []  # (name, detail) of each failed check, in order
        self.names: list[str] = []

    def __call__(self, name: str, ok, detail="") -> bool:
        """The self-test's check(): prints "ok   name" or "FAIL name  (detail)", keeps the name, and logs it."""
        ok = bool(ok)
        detail = "" if ok else short(detail)
        self.names.append(name)
        _say(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({detail})"))
        if not ok:
            self.failed.append((name, detail))
        log({"event": "check", "test": self.test, "name": name, "ok": ok, "detail": detail})
        return ok

    def raise_if_failed(self):
        """AssertionError listing every failed check, when one failed."""
        if self.failed:
            raise AssertionError("check(s) failed:\n" + "\n".join(f"FAIL {n}  ({d})" for n, d in self.failed))

    def skipped(self, reason: str, *names: str) -> NoReturn:
        """Each name logged as skipped with the reason, then the test skipped (pytest.skip): a check that can't run
        here (Inno Setup, Windows' text reader, a desktop...) shows as skipped, with why, never as missing."""
        import pytest
        for name in names:
            _say(f"skip {name}  ({reason})")
            log({"event": "check", "test": self.test, "name": name, "ok": None, "skipped": True,
                 "detail": short(reason)})
        pytest.skip(reason)
