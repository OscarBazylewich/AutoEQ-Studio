"""A profile's EQ updated in place (switcher\\core.py's update_profile, 2026-10-26: Make an EQ's EQ by hand, begun from
a profile, put back into it with Use on device › Update): its file holds the new EQ, while its name, its file's name,
the devices that have it and the one it's switched on for stay, so they hear the change at once; a file that isn't an
EQ, or a profile that's gone, changes nothing. On a stand-in APO folder in the test's own folder."""
import os

import pytest

import textfile
from helpers import apo as stand_in
from switcher import core, eqfile
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


@pytest.fixture
def sw(tmp_path):
    top = str(tmp_path)
    conf = stand_in.fake_apo(top)
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)]
    textfile.take_set_aside()  # (nothing another test set aside: the Switcher would take it as its own)
    s = core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: list(eps), playing=lambda: "{5}")
    s.top = top
    return s


def test_profile_updated_in_place(sw, check):
    pid = sw.import_profile(_write(os.path.join(sw.top, "Mine.txt"), "Preamp: -3 dB\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n"),
                            "Mine")
    sw.add_to_device(KEY, pid, switch_on=True)
    told = []
    sw.listeners.append(lambda what, info: told.append(what))
    sw.update_profile(pid, _write(os.path.join(sw.top, "Edited.txt"), "Preamp: -5 dB\nFilter 1: ON PK Fc 1000 Hz Gain 5 dB Q 1\n"
                                  "Filter 2: ON PK Fc 3000 Hz Gain -2 dB Q 2\n"))
    p = sw.profiles()[pid]
    text = _read(os.path.join(sw.apo.profiles, p["file"]))
    rec = sw.record(KEY)
    switcher_txt = _read(os.path.join(sw.apo.own, "switcher.txt"))
    check("core: a profile updated in place holds the new EQ in its own file; its name, its file's name and its device "
          "stay, still switched on (APO's file still includes it), its counts are the new EQ's, and the screens are told",
          "Gain 5 dB" in text and "3000 Hz" in text and p["name"] == "Mine" and p["file"] == "Mine.txt"
          and rec["active"] == pid and rec["profiles"] == [pid] and "profiles\\Mine.txt" in switcher_txt
          and p["filters"] == 2 and p["preamp"] == -5 and "profiles" in told and len(sw.profiles()) == 1,
          (p, rec, told))


def test_update_refused_changes_nothing(sw, check):
    pid = sw.import_profile(_write(os.path.join(sw.top, "Mine.txt"), "Filter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n"), "Mine")
    before = _read(os.path.join(sw.apo.profiles, "Mine.txt"))
    try:
        sw.update_profile(pid, _write(os.path.join(sw.top, "Bad.txt"), "Device: Speakers\nFilter 1: ON PK Fc 100 Hz Gain 1 dB Q 1\n"))
        refused = None
    except eqfile.NotAnEqFile as e:
        refused = str(e)
    try:
        sw.update_profile("gone", os.path.join(sw.top, "Mine.txt"))
        gone = None
    except OSError as e:
        gone = str(e)
    check("core: updating a profile with a file a profile can't hold (Device:) is refused with the reason and leaves "
          "the profile as it was; a profile that's gone says so",
          refused and "Device:" in refused and _read(os.path.join(sw.apo.profiles, "Mine.txt")) == before
          and gone == "That profile isn't there any more.", (refused, gone))
