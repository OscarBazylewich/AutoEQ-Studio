"""Make an EQ's fixture (a pytest plugin, loaded by tests\\conftest.py).

eq_screen  (one per test file) Make an EQ opened on the session as the old EQ screen checks opened it, on the
           settings they started from (helpers.eqpage.OLD_START), offline, with a stand-in device and APO folder;
           closed after the file's last test. Every test using it is marked slow (tests\\conftest.py).
A file that needs other starting settings opens its own page with helpers.eqpage.open_screen(tmp, settings) in a
fixture of its own (marked slow too: its module imports helpers.eqpage).
"""
import pytest


@pytest.fixture(scope="module")
def eq_screen(tmp_path_factory):
    from helpers import eqpage
    s = eqpage.open_screen(str(tmp_path_factory.mktemp("eq_screen")))
    yield s
    eqpage.close_screen(s)
