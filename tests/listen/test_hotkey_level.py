"""The on/off hotkey's level match (switcher\\level.py, 2026-10-26) is Listen's measure: how loud an EQ plays next to
none, worked out in plain Python from its file (the tray never loads the EQ part), against Listen's own (ui\\audio.py's
levels: A-weighted pink noise over its 241 frequencies, worked out here with NumPy and the EQ part's own filters).
Here with Listen's tests, as it needs the EQ part (tests\\switcher stays free of it); the rest of the hotkey is in
tests\\switcher\\test_compare_off.py."""
import numpy as np

from switcher import level


def listen_level(filters, preamp=0.0):
    """Listen's measure of these filters, plus a pre-amp."""
    from eq import engines
    from ui import audio
    g = engines.eq_gain(audio.GRID, filters, 48000) + preamp
    return float(10 * np.log10(np.sum(audio.AW * 10 ** (g / 10)) / np.sum(audio.AW)))


def test_loudness_as_listen_measures_it(check):
    cases = [
        ("Filter 1: ON PK Fc 100 Hz Gain 6 dB Q 0.7\nFilter 2: ON PK Fc 3000 Hz Gain -4 dB Q 2",
         [{"type": "PK", "freq": 100, "gain": 6, "q": 0.7}, {"type": "PK", "freq": 3000, "gain": -4, "q": 2}], 0.0),
        ("Preamp: -6.4 dB\nFilter 1: ON LSC Fc 105 Hz Gain 6.4 dB Q 0.7\nFilter 2: ON HSC Fc 10000 Hz Gain -2.1 dB Q 0.7",
         [{"type": "LSQ", "freq": 105, "gain": 6.4, "q": 0.7}, {"type": "HSQ", "freq": 10000, "gain": -2.1, "q": 0.7}],
         -6.4),
        ("Preamp: -3 dB\nFilter 1: ON PK Fc 2000 Hz Gain 5 dB Q 1\nFilter 2: OFF PK Fc 500 Hz Gain 9 dB Q 1",
         [{"type": "PK", "freq": 2000, "gain": 5, "q": 1}], -3.0),
    ]
    got = [(level.level(text)["db"], round(listen_level(fl, pre), 2)) for text, fl, pre in cases]
    check("level: an EQ's loudness next to none, worked out in plain Python from its file (pre-amps, peaks, shelves, a "
          "switched-off filter left out), is Listen's measure within 0.02 dB",
          all(abs(a - b) <= 0.02 for a, b in got), got)
