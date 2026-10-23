"""fixtures_core's module_monkeypatch (helpers\\fixtures_core.py): what a file-wide fixture stands in for through it
lasts for every test of that file and is put back after the file's last test, before the next file runs. On an inner
pytest run (its own process and check log)."""
from helpers import inner

pytest_plugins = ["pytester"]

FILE_A = '''
import os

import pytest


@pytest.fixture(scope="module")
def shared(module_monkeypatch):
    module_monkeypatch.setenv("AEQS_INNER_MODULE_PATCH", "set")
    module_monkeypatch.setattr(os, "aeqs_inner_mark", "set", raising=False)
    return True


def test_first(shared):
    assert os.environ.get("AEQS_INNER_MODULE_PATCH") == "set" and os.aeqs_inner_mark == "set"


def test_second(shared):
    assert os.environ.get("AEQS_INNER_MODULE_PATCH") == "set" and os.aeqs_inner_mark == "set"
'''

FILE_B = '''
import os


def test_put_back():
    assert "AEQS_INNER_MODULE_PATCH" not in os.environ and not hasattr(os, "aeqs_inner_mark")
'''


def test_module_monkeypatch(pytester, monkeypatch, check):
    result, _log = inner.run(pytester, monkeypatch, {"test_inner_patch_a.py": FILE_A, "test_inner_patch_b.py": FILE_B},
                             "-q")
    check("fixtures: module_monkeypatch keeps what a file-wide fixture stands in for through every test of that file, "
          "and puts it back after the file's last test",
          result.ret == 0 and result.parseoutcomes() == {"passed": 3}, (result.parseoutcomes(), result.outlines[-5:]))
