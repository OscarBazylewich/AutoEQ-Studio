"""A profile put back on a device where it was (Switcher.add_to_device's at=, the Devices screen's Undo after a
profile's ✕, 2026-10-27): back in its place in the device's list (the hotkey's order), on only if it was; a device
whose only profile was off stays off (added without at=, a device's only profile is switched on when none is, as
before). On a stand-in APO folder and settings in the test's own folder."""
import os

from helpers import apo as stand_in
from switcher import core
from switcher import devices as D
from switcher.apo import Apo

KEY = "Headset|EarPods"


def _switcher(top):
    conf = stand_in.fake_apo(top)
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)]
    return core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")


def _profile(sw, top, name):
    path = os.path.join(top, name + ".txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("Preamp: -2 dB\n")
    return sw.import_profile(path, name)


def test_put_back_in_its_place(tmp_path, check):
    top = str(tmp_path)
    sw = _switcher(top)
    a, b, c = (_profile(sw, top, n) for n in ("A", "B", "C"))
    for pid in (a, b, c):
        sw.add_to_device(KEY, pid, switch_on=pid == b)
    sw.remove_from_device(KEY, b)
    sw.add_to_device(KEY, b, switch_on=True, at=1)
    rec = sw.record(KEY)
    check("core: a profile taken off a device and put back (Undo: at=) is in its old place in the device's list, on "
          "again as it was", rec["profiles"] == [a, b, c] and rec["active"] == b, (rec["profiles"], rec["active"]))


def test_an_only_profile_put_back_stays_off(tmp_path, check):
    top = str(tmp_path)
    sw = _switcher(top)
    pid = _profile(sw, top, "Only")
    sw.add_to_device(KEY, pid)
    sw.set_active(KEY, None)
    sw.remove_from_device(KEY, pid)
    sw.add_to_device(KEY, pid, switch_on=False, at=0)
    undone = (sw.record(KEY)["profiles"] == [pid], sw.record(KEY)["active"])
    sw.remove_from_device(KEY, pid)
    sw.add_to_device(KEY, pid, switch_on=False)
    added = sw.record(KEY)["active"]
    check("core: a device's only profile, taken off while its EQ was off and put back (Undo), leaves it off; added "
          "anew, a device's only profile is switched on when none is, as before",
          undone == (True, None) and added == pid, (undone, added))


def test_the_eq_it_had_last_comes_back(tmp_path, check):
    # (2026-10-27, the code's review: taking a profile off a device forgets it as the EQ the device had last, and Undo
    # didn't bring that back: the on/off hotkey then switched another profile on)
    top = str(tmp_path)
    sw = _switcher(top)
    a, b = (_profile(sw, top, n) for n in ("A", "B"))
    sw.add_to_device(KEY, b, switch_on=False)
    sw.add_to_device(KEY, a, switch_on=True)
    sw.set_active(KEY, None)  # (off: A is the EQ it had last)
    before = sw.record(KEY).get("last")
    sw.remove_from_device(KEY, a)
    sw.add_to_device(KEY, a, switch_on=False, at=1, last=True)
    rec = sw.record(KEY)
    check("core: put back (Undo), a profile is again the EQ the device had last (the on/off hotkey's way back), the "
          "device still off", before == a and rec.get("last") == a and rec["active"] is None
          and rec["profiles"] == [b, a], (before, rec.get("last"), rec["active"]))
