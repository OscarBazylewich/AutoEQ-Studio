"""The EQ part's fixtures (a pytest plugin, loaded by tests\\conftest.py; each imports the EQ part only when a test
asks for it).

fresh_studio   the session's studio back to new before and after the test (helpers.studio.reset)
eq_cfg         the EQ part's default settings, completed (settings.with_auto({}))
sample_curves  the sample target and device loaded once per session (helpers.eq.sample_load: curves, measurement
               texts, target text)
db_guard       the online databases' module state saved and put back after the test; downloads stood in for
               (helpers.eq.DbGuard: a download raises OSError("no internet in the tests"))
api            requests to the EQ part as the window makes them (helpers.eq.Api); opening a folder is recorded in
               api.opened, never done
"""
import pytest


@pytest.fixture
def fresh_studio():
    from helpers import studio
    studio.reset()
    yield
    studio.reset()


@pytest.fixture
def eq_cfg():
    from eq import settings
    return settings.with_auto({})


@pytest.fixture(scope="session")
def sample_curves():
    from helpers import eq
    return eq.sample_load()


@pytest.fixture
def db_guard():
    from helpers.eq import DbGuard
    guard = DbGuard()
    guard.save()
    guard.stub_get()
    yield guard
    guard.restore()


@pytest.fixture
def api(monkeypatch):
    from eq import service
    from helpers.eq import Api
    a = Api()
    monkeypatch.setattr(service, "open_path", a.opened.append)
    return a
