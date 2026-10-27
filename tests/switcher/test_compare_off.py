"""The on/off hotkey's "EQ off for now, to compare" (switcher\\core.py's compare_toggle and switcher\\level.py,
2026-10-26), on a stand-in APO folder in the test's own folder: how loud an EQ plays next to none, worked out in plain
Python (the tray never loads the EQ part) the same as Listen's measure (worked out here again with NumPy and the EQ
part's own filters: within 0.02 dB); a graphic EQ's points, a part it can't measure said, per-channel parts passed
over. Then the device's EQ off for now: level-matched, a pre-amp alone turned down to the EQ's loudness (in APO's
file for that device); back on; truly off when Level-matched is off; never saved; ended by choosing an EQ for the
device or by a trial; with no EQ on, the one the device had last switched on (kept through a start)."""
import json
import os

import numpy as np
import pytest

import textfile
from helpers import apo as stand_in
from switcher import core, level
from switcher import devices as D
from switcher.apo import Apo

KEY = "Headset|EarPods"


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def listen_level(filters, preamp=0.0):
    """Listen's measure (ui\\audio.py's levels: A-weighted pink noise over its 241 frequencies) of these filters,
    worked out with NumPy and the EQ part's own filters, plus a pre-amp."""
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


def test_what_level_can_and_cannot_measure(check):
    graphic = level.level("GraphicEQ: 20 0; 1000 0; 2000 6; 20000 6")
    flat = level.level("Preamp: 0 dB")
    conv = level.level("Preamp: -2 dB\nConvolution: C:\\x.wav")
    chan = level.level("Channel: L\nFilter 1: ON PK Fc 1000 Hz Gain 10 dB Q 1\nChannel: all\nPreamp: -1 dB")
    other = level.level("Filter 1: ON LP Fc 2000 Hz\nFilter 2: ON IIR Order 2 Coefficients 1 0 0 1 0 0")
    check("level: a graphic EQ's points count (straight between them on a log scale); a convolution is said to be left "
          "out (incomplete); a part for some channels only is passed over; low-pass filters count, a word APO doesn't "
          "take is said",
          graphic["db"] > 2 and graphic["complete"] and flat["db"] == 0 and conv["db"] == -2 and not conv["complete"]
          and chan["db"] == -1 and chan["complete"] and other["db"] < -1 and not other["complete"],
          (graphic, flat, conv, chan, other))


@pytest.fixture
def sw(tmp_path):
    top = str(tmp_path)
    conf = stand_in.fake_apo(top)
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)]
    textfile.take_set_aside()
    make = lambda path: core.Switcher(path, Apo(conf), endpoints=lambda: list(eps), playing=lambda: "{5}")
    s = make(os.path.join(top, "s.json"))
    s.top, s.make = top, make
    s.pid = s.import_profile(_write(os.path.join(top, "Mine.txt"), "Preamp: -4 dB\nFilter 1: ON PK Fc 100 Hz Gain 6 dB Q 0.7\n"
                                    "Filter 2: ON PK Fc 3000 Hz Gain -4 dB Q 2\n"), "Mine")
    s.add_to_device(KEY, s.pid, switch_on=True)
    return s


def _section(sw):
    """The stand-in device's part of APO's per-device file (switcher.txt): from its heading to the end of devices."""
    text = _read(os.path.join(sw.apo.own, "switcher.txt"))
    start = text.index("# Headset (EarPods)")
    return text[start:text.index("# everything after", start)]


def test_off_for_now_level_matched_then_back(sw, check):
    told = []
    sw.listeners.append(lambda what, info: told.append(what))
    off = sw.compare_toggle(KEY)
    want = round(min(0.0, level.level(_read(os.path.join(sw.apo.profiles, "Mine.txt")))["db"]), 1)
    during = (_section(sw), _read(sw.compare_path()), json.loads(_read(sw.path)).get("compare"))
    on = sw.compare_toggle(KEY)
    after = _section(sw)
    check("compare: off for now, level-matched, the device plays a pre-amp alone turned down to the EQ's loudness (APO's "
          "file for it includes it instead of the EQ); never saved; pressed again, its EQ is back; the screens are told",
          off[0] == "off" and off[1]["matched"] and off[1]["db"] == want < 0 and "Include: profiles\\_compare.txt" in during[0]
          and during[1].strip() == f"Preamp: {want:.1f} dB" and during[2] is None and on == ("on", "Mine")
          and "Include: profiles\\Mine.txt" in after and sw.compare is None and told.count("active") == 2,
          (off, during, on, after))


def test_truly_off_when_not_level_matched(sw, check):
    sw.set("onoff_matched", False)
    off = sw.compare_toggle(KEY)
    section = _section(sw)
    sw.compare_toggle(KEY)
    check("compare: with Level-matched off, “off” is no EQ at all (the device's part of APO's file includes nothing)",
          off[0] == "off" and not off[1]["matched"] and "Include:" not in section.split("Device: all")[0], section)


def test_another_choice_ends_it(sw, check):
    sw.compare_toggle(KEY)
    sw.set_active(KEY, sw.pid)  # (the same EQ chosen again, e.g. in the tray: it's back)
    first = (sw.compare, "Mine.txt" in _section(sw))
    sw.compare_toggle(KEY)
    sw.try_eq(KEY, "Preamp: -1 dB\nFilter 1: ON PK Fc 500 Hz Gain 2 dB Q 1\n", "Tried")
    second = (sw.compare, "_trying.txt" in _section(sw))
    off = sw.compare_toggle(KEY)  # (now the trial's EQ is what's compared)
    trial_db = round(min(0.0, level.level(_read(sw.trial_path()))["db"]), 1)
    sw.end_trial()
    third = sw.compare
    check("compare: choosing an EQ for the device ends it (the same one too), and so do a trial's start and end; during "
          "a trial, it's the trial's EQ that's compared",
          first == (None, True) and second == (None, True) and off[1]["db"] == trial_db and third is None,
          (first, second, off, third))


def test_with_no_eq_on_its_last_one_comes_on(sw, check):
    sw.set_active(KEY, None)
    again = sw.make(sw.path)  # (as at the next start)
    on = again.compare_toggle(KEY)
    bare = sw.make(os.path.join(sw.top, "bare.json"))
    nothing = bare.compare_toggle(KEY)
    check("compare: with no EQ on, the on/off hotkey switches on the one the device had last (kept through a start); "
          "a device with no profiles has nothing to switch",
          on == ("on", "Mine") and again.record(KEY)["active"] == sw.pid and nothing is None, (on, nothing))


def test_quitting_puts_the_eq_back(sw, check):
    sw.compare_toggle(KEY)
    sw.compare_end()
    check("compare: quitting (compare_end) puts the device's EQ back in APO's file",
          sw.compare is None and "Include: profiles\\Mine.txt" in _section(sw), _section(sw))
