"""The fixtures every part of the tests may use (a pytest plugin, loaded by tests\\conftest.py).

qapp         the process's one QApplication (helpers.qt.app(); no theme: the window tests run unthemed, as the old
             self-test did)
check        check(name, ok, detail) for this test (helpers.checks)
dialogs      the dialogs' answers and what was asked (helpers.dialogs), reset before and after each test (autouse)
guard_check  fails a test in which the guard blocked something, listing it (autouse)
stray_check  fails a test in which a control was shown as a window of its own, unless it's marked
             allow_strays("what flashed, where") (autouse)
(Both look after the test and then clear, rather than clearing first: a module's fixtures are made before a test's
own, so what happened while they were made counts for the first test that uses them.)
offline      the app offline for the whole session (autouse): nothing it does can reach the internet
online       the app online for one test (the guard still blocks real connections: stand in for what would download)
fake_apo     a stand-in Equalizer APO config folder in tmp_path (helpers.apo.fake_apo)
child_env    helpers.session.child_env: the environment for a subprocess
module_monkeypatch  monkeypatch for a whole test file (pytest's own lasts one test): what a file-wide fixture (a
             chain's shared window, Switcher or requests) stands in for, put back after the file's last test

helpers.qt, helpers.session and helpers.guard are imported inside the fixtures that use them, not at the top
(app\\tools\\relevant_tests.py: a fixture brings its own file's top-level imports to every test that asks for it, so
a test asking only for check would otherwise reach ui.theme through helpers.qt, and the samples through
helpers.session and helpers.guard (helpers.paths declares samples/**): a change to the theme or the samples then chose
nearly every test).
"""
import collections

import pytest

from helpers import apo, checks, dialogs as dialogs_mod


@pytest.fixture(scope="session")
def qapp():
    from helpers import qt
    return qt.app()


@pytest.fixture
def check(request):
    return checks.Checks(request.node.nodeid)


@pytest.fixture(autouse=True)
def dialogs():
    dialogs_mod.DIALOGS.reset()
    yield dialogs_mod.DIALOGS
    dialogs_mod.DIALOGS.reset()


@pytest.fixture(autouse=True)
def guard_check():
    # (checked after the test, then cleared, as stray_check below: what was blocked while its module's fixtures
    # were made counts for it too)
    from helpers import guard
    yield
    blocked = guard.violations()
    guard.clear()
    if blocked:
        pytest.fail("The test guard blocked what a test must never do:\n" + "\n".join(blocked), pytrace=False)


@pytest.fixture(autouse=True)
def stray_check(request):
    # (checked after the test, then cleared: what showed while its module's fixtures were made, before it, counts
    # for it too; those are made before this fixture, so clearing first would lose them)
    from helpers import qt
    yield
    watch = qt.stray_watch()
    if watch is None or not watch.found:
        return
    found = list(watch.found)
    watch.clear()
    most = collections.Counter(found).most_common(5)
    mark = request.node.get_closest_marker("allow_strays")
    if mark is not None:
        reason = mark.args[0] if mark.args else mark.kwargs.get("reason", "")
        checks.log({"event": "allowed_strays", "test": request.node.nodeid, "reason": reason, "found": most})
        print(f"(allowed: shown as windows of their own: {most}; {reason})")
        return
    checks.log({"event": "check", "test": request.node.nodeid, "name": qt.STRAY_CHECK, "ok": False,
                "detail": checks.short(most)})
    pytest.fail(f"FAIL {qt.STRAY_CHECK}  (shown during this test or while its fixtures were made: {most})",
                pytrace=False)


@pytest.fixture(scope="session", autouse=True)
def offline():
    import net
    net.set_offline(True)


@pytest.fixture
def online():
    import net
    net.set_offline(False)
    yield
    net.set_offline(True)


@pytest.fixture
def fake_apo(tmp_path):
    return apo.fake_apo(str(tmp_path))


@pytest.fixture
def child_env():
    from helpers import session
    return session.child_env


@pytest.fixture(scope="module")
def module_monkeypatch():
    """monkeypatch for a whole test file: for a file-wide fixture (scope="module") that stands something in, which
    pytest's own monkeypatch (one test) can't serve. Everything is put back after the file's last test."""
    with pytest.MonkeyPatch.context() as mp:
        yield mp
