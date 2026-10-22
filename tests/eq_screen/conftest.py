"""tests\\eq_screen runs as one process (the old EQ screen checks were one long process on one page): every test file
here starts from the same state, whatever ran before it (helpers.eq.file_reset: no run going, nothing set aside,
offline, the studio as new, no window left open)."""
import pytest

from helpers import eq


@pytest.fixture(scope="module", autouse=True)
def reset_before_file():
    eq.file_reset()
