"""Taking over from EQ Switcher (switcher\\core.py and apo.py), on stand-ins in the test's own folder: EQ Switcher's
folder, its switcher.txt and its settings are made up there, never the real EQ Switcher. Its per-device file isn't
offered as an EQ, its profiles (their files copied) and choices come over once, an EQ file with a profile's contents
counts as that profile, and setting up turns its line in config.txt off. Moved from selftest.py's takeover_checks.

takeover_checks worked on one Switcher: here it's the module-wide fixture `takeover`, and `brought` is the bring-over
the two checks after it build on (a second bring-over, a file like a profile), the tests in the old order."""
import json
import os
import types

import pytest

import textfile
from helpers import apo as stand_in
from switcher import core
from switcher import devices as D
from switcher.apo import Apo


@pytest.fixture(scope="module")
def takeover(tmp_path_factory):
    """takeover_checks' start (selftest.py lines 249-265): a stand-in APO folder with EQ Switcher's profiles folder
    (EarPods.txt) and its switcher.txt; config.txt with EQ Switcher's line on and two lines off; EQ Switcher's
    settings (old.json: the profile "EarPods" and one whose file is gone, the headset's choices, its hotkey, notices
    off); one stand-in endpoint, the headset {5}, playing; and AutoEQ Studio's Switcher on new.json."""
    top = str(tmp_path_factory.mktemp("takeover"))
    conf = stand_in.fake_apo(top)
    old_dir = os.path.join(conf, "EQ Switcher", "profiles")
    os.makedirs(old_dir)
    with open(os.path.join(old_dir, "EarPods.txt"), "wb") as fh:
        fh.write(stand_in.EARPODS)
    with open(os.path.join(conf, "EQ Switcher", "switcher.txt"), "w") as fh:
        fh.write("Device: {5}\nInclude: profiles\\EarPods.txt\nDevice: all\n")
    with open(os.path.join(conf, "config.txt"), "w") as fh:
        fh.write("# Include: Samson.txt\n# (EQ Switcher) Include: EarPods.txt\nInclude: EQ Switcher\\switcher.txt\n")
    old = os.path.join(top, "old.json")
    with open(old, "w") as fh:
        json.dump({"profiles": {"p1": {"name": "EarPods", "file": "EarPods.txt", "filters": 2, "preamp": -26.7},
                                "gone": {"name": "Lost", "file": "lost.txt"}},
                   "devices": {"Headset|EarPods": {"label": "Headset (EarPods)", "guids": ["{5}"], "profiles": ["p1", "gone"],
                                                   "active": "p1"}}, "hotkey": "Ctrl+Alt+Q", "notify": False}, fh)
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)]
    textfile.take_set_aside()  # (nothing another test set aside: the Switcher would take it as its own)
    sw = core.Switcher(os.path.join(top, "new.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    return types.SimpleNamespace(conf=conf, old=old, old_dir=old_dir, sw=sw)


def test_switchers_file_not_offered(takeover, check):
    refs = [os.path.basename(p) for p in takeover.sw.apo.referenced_files()]
    # was selftest.py:267
    check("takeover: EQ Switcher's per-device file isn't offered as an EQ; a line another app turned off still is",
          refs == ["Samson.txt", "EarPods.txt"], refs)


@pytest.fixture(scope="module")
def brought(takeover):
    """EQ Switcher's profiles and choices brought over (selftest.py line 269): how many profiles came."""
    return takeover.sw.bring_over(takeover.old, takeover.old_dir)


def test_profiles_and_choices_come_over(takeover, brought, check):
    sw, n = takeover.sw, brought
    rec = sw.record("Headset|EarPods")
    # was selftest.py:271
    check("takeover: EQ Switcher's profiles (their files copied) and choices come over; one whose file is gone doesn't",
          n == 1 and rec["profiles"] == ["p1"] and rec["active"] == "p1" and sw.s["hotkey"] == "Ctrl+Alt+Q"
          and not sw.s["notify"] and os.path.isfile(os.path.join(sw.apo.profiles, "EarPods.txt")), (n, rec))


def test_brought_over_once(takeover, brought, check):
    # was selftest.py:274
    check("takeover: brought over once (a second time does nothing)", takeover.sw.bring_over(takeover.old, takeover.old_dir) == 0)


def test_file_like_a_profile(takeover, brought, check):
    sw, conf = takeover.sw, takeover.conf
    # was selftest.py:275
    check("takeover: an EQ file with a profile's contents counts as that profile (not offered again)",
          sw.has_profile_like(os.path.join(conf, "EarPods.txt")) and not sw.has_profile_like(os.path.join(conf, "Samson.txt")))


def test_setting_up_turns_its_line_off(takeover, check):
    sw = takeover.sw
    off = sw.set_up_apo()
    # was selftest.py:278
    check("takeover: setting up turns EQ Switcher's line off, so the two never both apply an EQ",
          off == ["Include: EQ Switcher\\switcher.txt"] and sw.apo.set_up(), off)
