"""tests\\tracer: the tracer (ui\\trace_core.py, ui\\trace_window.py) and Windows' text reader (ui\\ocr.py).

What every file here shares: it starts from the same state, whatever ran before it (helpers.eq.file_reset: no run
going, nothing set aside, offline, the studio as new, no window left open), as the files of tests\\eq and
tests\\eq_screen do. A file that needs the tracer's window opens it from its own Make an EQ (the eq_screen fixture,
on the settings the old screen checks started from: helpers.eqpage.OLD_START), as the old checks did.
"""
import pytest

from helpers import eq


@pytest.fixture(scope="module", autouse=True)
def reset_before_file():
    eq.file_reset()
