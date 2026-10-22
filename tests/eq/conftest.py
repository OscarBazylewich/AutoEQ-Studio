"""tests\\eq runs as one process (the old EQ checks ran their modules and requests parts each in its own): every test
file here starts from the same state, whatever ran before it (helpers.eq.file_reset: no run going, nothing set
aside, offline, the studio as new)."""
import pytest

from helpers import eq


@pytest.fixture(scope="module", autouse=True)
def reset_before_file():
    eq.file_reset()
