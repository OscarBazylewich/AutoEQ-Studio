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
"""
import collections

import pytest

from helpers import apo, checks, dialogs as dialogs_mod, guard, qt, session


@pytest.fixture(scope="session")
def qapp():
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
    yield
    blocked = guard.violations()
    guard.clear()
    if blocked:
        pytest.fail("The test guard blocked what a test must never do:\n" + "\n".join(blocked), pytrace=False)


@pytest.fixture(autouse=True)
def stray_check(request):
    # (checked after the test, then cleared: what showed while its module's fixtures were made, before it, counts
    # for it too; those are made before this fixture, so clearing first would lose them)
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
    return session.child_env
