"""tests\\listen: Listen's sound (ui\\audio.py) and its card on Make an EQ (ui\\listen.py).

What every file here shares:
- it starts from the same state, whatever ran before it (helpers.eq.file_reset: no run going, nothing set aside,
  offline, the studio as new, no window left open), as the files of tests\\eq and tests\\eq_screen do;
- nothing is ever played: Play's sound card is stood in for by a silent one for the whole file (eq_checks.py line 2926
  did the same for the rest of its run, and never put it back), and the sound card's rate is fixed at 48 kHz (the real
  one asks Windows' audio devices, which differ from PC to PC).
"""
import pytest

from helpers import eq


@pytest.fixture(scope="module", autouse=True)
def reset_before_file():
    eq.file_reset()


@pytest.fixture(scope="module", autouse=True)
def silent_sound_card():
    from ui import audio
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(audio.Engine, "start", lambda self: None)  # (silent: no sound card is opened)
        mp.setattr(audio, "card_rate", lambda: 48000)
        yield
