"""A device off the lists (Switcher.remove_device, the Devices screen's Remove, 2026-11-12): after an update of
Equalizer APO or a driver, Windows can give a device a new entry, and the old one stayed in Devices for good. Only a
device that is not connected can go: one that Windows does not list (its record goes), or one that Windows lists as
not connected (also hidden, hidden_devices, until it is connected again: then a new device). Its profiles stay. Undo
(restore_device) puts the record back as it was, in its place. On a stand-in APO folder and settings in the test's own
folder."""
import json
import os

from helpers import apo as stand_in
from switcher import core
from switcher import devices as D
from switcher.apo import Apo

PLAYING = "Headset|EarPods"  # (connected, playing)
AWAY = "Headphones|Buds"  # (in Windows' list, not connected)
GONE = "Headset|USB-C to 3.5mm Headphone Jack Adapter"  # (no longer in Windows' list)


def _switcher(top, eps=None):
    conf = stand_in.fake_apo(top)
    eps = eps if eps is not None else [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True),
                                       D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)]
    sw = core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    return sw, eps


def _profile(sw, top, name):
    path = os.path.join(top, name + ".txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("Preamp: -2 dB\n")
    return sw.import_profile(path, name)


def _gone_device(sw, top):
    """A device that Windows listed before (a record with its endpoint and a profile on), now not in its list."""
    pid = _profile(sw, top, "Old")
    sw.s["devices"][GONE] = {"label": "Headset (USB-C to 3.5mm Headphone Jack Adapter)", "guids": ["{9}"],
                             "profiles": [], "active": None}
    sw.add_to_device(GONE, pid)
    return pid


def _switcher_txt(sw):
    with open(os.path.join(sw.apo.own, "switcher.txt"), encoding="utf-8") as fh:
        return fh.read()


def test_a_device_that_windows_does_not_list(tmp_path, check):
    top = str(tmp_path)
    sw, _ = _switcher(top)
    pid = _gone_device(sw, top)
    shown_before = GONE in sw.listed()
    file_before = "{9}" in _switcher_txt(sw)
    told = []
    sw.listeners.append(lambda what, info: told.append(what))
    before = sw.remove_device(GONE)
    with open(os.path.join(top, "s.json"), encoding="utf-8") as fh:
        saved = json.load(fh)
    got = (shown_before, file_before, before is not None and before["hidden"], sw.record(GONE), GONE in sw.listed(),
           "{9}" in _switcher_txt(sw), GONE in saved["devices"], saved["hidden_devices"], pid in sw.profiles(), told)
    check("core: a device that Windows does not list goes from the settings, the lists and APO's file; it is not "
          "hidden (nothing to hide); its profile stays in Profiles; the listeners are told",
          got == (True, True, False, None, False, False, False, [], True, ["devices"]), got)


def test_a_device_that_windows_lists_not_connected(tmp_path, check):
    top = str(tmp_path)
    sw, eps = _switcher(top)
    pid = _profile(sw, top, "Buds EQ")
    sw.add_to_device(AWAY, pid)
    before = sw.remove_device(AWAY)
    now = (before is not None and before["hidden"], sw.record(AWAY), sw.device(AWAY), AWAY in sw.listed(),
           sw.s["hidden_devices"], "{1}" in _switcher_txt(sw))
    sw.refresh()
    later = (sw.record(AWAY), sw.device(AWAY), sw.s["hidden_devices"])
    again = core.Switcher(os.path.join(top, "s.json"), Apo(sw.apo.config), endpoints=lambda: eps,
                          playing=lambda: "{5}")  # (the next start)
    start = (again.record(AWAY), again.device(AWAY), again.s["hidden_devices"])
    check("core: a device that Windows lists as not connected goes and is hidden: no record and not in the lists, at "
          "the next refresh and at the next start too, and no section in APO's file",
          now == (True, None, None, False, [AWAY], False) and later == (None, None, [AWAY])
          and start == (None, None, [AWAY]), (now, later, start))


def test_a_connected_device_is_refused(tmp_path, check):
    top = str(tmp_path)
    sw, _ = _switcher(top)
    pid = _profile(sw, top, "A")
    sw.add_to_device(PLAYING, pid)
    rec = json.dumps(sw.record(PLAYING), sort_keys=True)
    got = (sw.remove_device(PLAYING), json.dumps(sw.record(PLAYING), sort_keys=True) == rec,
           sw.device(PLAYING) is not None, sw.s["hidden_devices"], sw.remove_device("Nothing|There"))
    sw.read_only = True  # (the settings file held by another program)
    locked = sw.remove_device(AWAY)
    sw.read_only = False
    check("core: a connected device is not removed (nothing changes), nor a key with no record, nor any device while "
          "the settings are read-only", got == (None, True, True, [], None) and locked is None
          and sw.record(AWAY) is not None, (got, locked))


def test_the_hidden_device_connects_again(tmp_path, check):
    top = str(tmp_path)
    sw, eps = _switcher(top)
    pid = _profile(sw, top, "Buds EQ")
    sw.add_to_device(AWAY, pid)
    sw.set_nickname(AWAY, "My buds")
    sw.remove_device(AWAY)
    eps[1] = D.Endpoint("{1}", "Headphones", "Buds", D.ACTIVE, True)  # (plugged in)
    told = []
    sw.listeners.append(lambda what, info: told.append(what))
    sw.refresh()
    rec = sw.record(AWAY)
    got = (rec, sw.device(AWAY) is not None, AWAY in sw.listed(), sw.s["hidden_devices"], "{1}" in _switcher_txt(sw),
           told)
    check("core: a hidden device that is connected again is a new device (no profiles, EQ off, Windows' name, its "
          "section in APO's file again) and goes out of the hidden list",
          got == ({"label": "Headphones (Buds)", "guids": ["{1}"], "profiles": [], "active": None}, True, True, [],
                  True, ["devices"]), got)


def test_a_hidden_key_that_windows_no_longer_lists(tmp_path, check):
    top = str(tmp_path)
    sw, eps = _switcher(top)
    sw.remove_device(AWAY)
    hidden = list(sw.s["hidden_devices"])
    del eps[1]  # (Windows no longer lists it)
    sw.refresh()
    with open(os.path.join(top, "s.json"), encoding="utf-8") as fh:
        saved = json.load(fh)["hidden_devices"]
    check("core: a key in the hidden list that Windows no longer lists goes out of the list (and the settings file)",
          hidden == [AWAY] and sw.s["hidden_devices"] == [] and saved == [] and sw.record(AWAY) is None,
          (hidden, sw.s["hidden_devices"], saved))


def test_undo_puts_each_field_back(tmp_path, check):
    top = str(tmp_path)
    sw, eps = _switcher(top)
    a, b, c = (_profile(sw, top, n) for n in ("A", "B", "C"))
    sw.s["devices"]["Speakers|Realtek"] = {"label": "Speakers (Realtek)", "guids": ["{7}"], "profiles": [],
                                           "active": None}  # (a record after AWAY: the order is kept)
    for pid in (c, a, b):
        sw.add_to_device(AWAY, pid, switch_on=pid == a)
    sw.set_active(AWAY, None)  # (A is the EQ it had last)
    sw.set_active(AWAY, b)
    sw.set_nickname(AWAY, "My buds")
    order = list(sw.s["devices"])
    rec = json.loads(json.dumps(sw.record(AWAY)))
    text = _switcher_txt(sw)
    before = sw.remove_device(AWAY)
    gone = (sw.record(AWAY), "{1}" in _switcher_txt(sw))
    told = []
    sw.listeners.append(lambda what, info: told.append(what))
    got = sw.restore_device(before)
    back = (got, list(sw.s["devices"]) == order, sw.record(AWAY) == rec, sw.s["hidden_devices"],
            sw.device(AWAY) is not None, AWAY in sw.listed(), _switcher_txt(sw) == text, told)
    with open(os.path.join(top, "s.json"), encoding="utf-8") as fh:
        saved = json.load(fh)
    check("core: Undo (restore_device) puts the record back as it was (its profiles in their order, the EQ on, the EQ "
          "it had last, your name), in its place among the records, out of the hidden list, in the lists again, and "
          "APO's file as before; saved",
          gone == (None, False) and back == ("", True, True, [], True, True, True, ["devices"])
          and saved["devices"][AWAY] == rec and saved["hidden_devices"] == [] and rec.get("last") == a
          and rec["profiles"] == [c, a, b] and rec["active"] == b, (gone, back, rec))


def test_undo_after_the_device_connected_again(tmp_path, check):
    top = str(tmp_path)
    sw, eps = _switcher(top)
    pid = _profile(sw, top, "Buds EQ")
    sw.add_to_device(AWAY, pid)
    before = sw.remove_device(AWAY)
    eps[1] = D.Endpoint("{1}", "Headphones", "Buds", D.ACTIVE, True)
    sw.refresh()
    new = json.dumps(sw.record(AWAY), sort_keys=True)
    got = sw.restore_device(before)
    check("core: Undo after the device was connected again (a new record there) changes nothing and says so (\"back\")",
          got == "back" and json.dumps(sw.record(AWAY), sort_keys=True) == new and sw.record(AWAY)["profiles"] == [],
          (got, sw.record(AWAY)))


def test_undo_leaves_out_a_profile_deleted_meanwhile(tmp_path, check):
    top = str(tmp_path)
    sw, _ = _switcher(top)
    a, b = _profile(sw, top, "A"), _profile(sw, top, "B")
    sw.add_to_device(AWAY, a, switch_on=False)
    sw.add_to_device(AWAY, b, switch_on=True)
    before = sw.remove_device(AWAY)
    sw.remove_profile(b)
    sw.restore_device(before)
    rec = sw.record(AWAY)
    check("core: a profile deleted between the removal and Undo is not put back (the device's EQ then off)",
          rec["profiles"] == [a] and rec["active"] is None, rec)


def test_the_profiles_stay(tmp_path, check):
    top = str(tmp_path)
    sw, _ = _switcher(top)
    pid = _profile(sw, top, "Shared")
    sw.add_to_device(AWAY, pid)
    sw.add_to_device(PLAYING, pid)
    sw.remove_device(AWAY)
    got = (pid in sw.profiles(), sw.profile_missing(pid), sw.record(PLAYING)["profiles"], sw.record(PLAYING)["active"],
           sw.used_by(pid), sw.on_for(pid))
    check("core: the profiles of a removed device stay in Profiles (with their files) and on the other devices; "
          "\"used by\" no longer names it",
          got == (True, False, [pid], pid, ["Headset (EarPods)"], [PLAYING]), got)


def test_a_trial_and_a_compare_on_the_device_stop(tmp_path, check):
    top = str(tmp_path)
    sw, eps = _switcher(top)
    pid = _profile(sw, top, "A")
    sw.add_to_device(AWAY, pid)
    sw.try_eq(AWAY, "Preamp: -1 dB\n", "Trial")
    trial_file = os.path.exists(sw.trial_path())
    sw.remove_device(AWAY)
    trial = (trial_file, sw.trial, os.path.exists(sw.trial_path()), core.TRIAL_FILE in _switcher_txt(sw))
    sw2, _ = _switcher(os.path.join(top, "second"))
    pid2 = _profile(sw2, top, "B")
    sw2.add_to_device(AWAY, pid2)
    sw2.compare_toggle(AWAY)
    comparing = bool(sw2.compare)
    sw2.remove_device(AWAY)
    check("core: an EQ for 5 minutes on the removed device stops (its file goes, APO's file no longer names it), and "
          "its EQ off to compare stops",
          trial == (True, None, False, False) and comparing and sw2.compare is None, (trial, comparing, sw2.compare))


def test_a_damaged_hidden_list_loads_as_empty(tmp_path, check):
    top = str(tmp_path)
    got = {}
    for name, value in (("not a list", "Headphones|Buds"), ("not strings", ["Headphones|Buds", 3]),
                        ("a dict", {"Headphones|Buds": True}), ("none", None)):
        folder = os.path.join(top, name.replace(" ", "_"))
        os.makedirs(folder)
        with open(os.path.join(folder, "s.json"), "w", encoding="utf-8") as fh:
            json.dump({"hidden_devices": value}, fh)
        sw, _ = _switcher(folder)
        got[name] = (sw.s["hidden_devices"], sw.device(AWAY) is not None, sw.record(AWAY) is not None)
    folder = os.path.join(top, "older")
    os.makedirs(folder)
    with open(os.path.join(folder, "s.json"), "w", encoding="utf-8") as fh:
        json.dump({"notify": True}, fh)  # (older settings: no such key)
    sw, _ = _switcher(folder)
    got["older"] = (sw.s["hidden_devices"], sw.device(AWAY) is not None, sw.record(AWAY) is not None)
    check("core: a hidden list that is not a list of strings (or not there: older settings) loads as an empty list, "
          "and the device shows", all(v == ([], True, True) for v in got.values()), got)


def test_the_hidden_list_is_not_shared(tmp_path, check):
    # (an empty list from a default, shared by every Switcher, would carry a removal into the next one)
    top = str(tmp_path)
    sw, _ = _switcher(os.path.join(top, "one"))
    sw.remove_device(AWAY)
    other, _ = _switcher(os.path.join(top, "two"))
    check("core: each Switcher has its own hidden list", other.s["hidden_devices"] == [] and other.device(AWAY),
          other.s["hidden_devices"])


def test_a_removal_while_the_settings_are_set_aside_keeps_apo_file(tmp_path, check):
    # (a damaged settings file is set aside at the start (hold): APO's file keeps the EQs until you change an EQ; a
    # removal or its Undo changes no EQ, so they must not write APO's file from the empty settings)
    top = str(tmp_path)
    sw, eps = _switcher(top)
    sw.add_to_device(PLAYING, _profile(sw, top, "P"))
    before = _switcher_txt(sw)
    with open(os.path.join(top, "s.json"), "w", encoding="utf-8") as fh:
        fh.write("{ damaged")  # (the next start sets it aside)
    again = core.Switcher(os.path.join(top, "s.json"), Apo(sw.apo.config), endpoints=lambda: eps,
                          playing=lambda: "{5}")
    held = again.hold
    removed = again.remove_device(AWAY)
    after_removal = _switcher_txt(again)
    again.restore_device(removed)
    got = (held, removed is not None, after_removal == before, _switcher_txt(again) == before, again.hold)
    check("core: a removal and its Undo while the settings are set aside (hold) do not write APO's file from the "
          "empty settings (the EQs of the devices stay)", got == (True, True, True, True, True), (got, before,
                                                                                                after_removal))


def test_two_removals_then_the_two_undos_in_each_sequence(tmp_path, check):
    # (the place of a record was its index at its removal: after two removals, the Undos in the sequence of the
    # removals gave EarPods, Buds, A, C, B for EarPods, Buds, A, B, C)
    top = str(tmp_path)
    got = {}
    for name, undo_first in (("same", 0), ("other", 1)):
        folder = os.path.join(top, name)
        os.makedirs(folder)
        sw, _ = _switcher(folder)
        for n in ("A", "B", "C"):
            key = f"Speakers|{n}"
            sw.s["devices"][key] = {"label": f"Speakers ({n})", "guids": ["{" + n + "}"], "profiles": [],
                                    "active": None}
            sw.add_to_device(key, _profile(sw, folder, n))
        order, text = list(sw.s["devices"]), _switcher_txt(sw)
        undos = [sw.remove_device("Speakers|B"), sw.remove_device("Speakers|C")]
        sw.restore_device(undos[undo_first])
        sw.restore_device(undos[1 - undo_first])
        got[name] = (list(sw.s["devices"]) == order, _switcher_txt(sw) == text, list(sw.s["devices"]))
    check("core: two removals, then their two Undos in either sequence, give the first order of the records and the "
          "same APO file", all(v[:2] == (True, True) for v in got.values()), got)


def test_a_device_connected_since_the_last_poll_is_refused(tmp_path, check):
    top = str(tmp_path)
    sw, eps = _switcher(top)
    pid = _profile(sw, top, "Buds EQ")
    sw.add_to_device(AWAY, pid)
    rec = json.dumps(sw.record(AWAY), sort_keys=True)
    eps[1] = D.Endpoint("{1}", "Headphones", "Buds", D.ACTIVE, True)  # (plugged in after the last poll)
    told = []
    sw.listeners.append(lambda what, info: told.append(what))
    got = (sw.remove_device(AWAY), json.dumps(sw.record(AWAY), sort_keys=True) == rec, sw.s["hidden_devices"],
           bool(sw.device(AWAY) and sw.device(AWAY).connected), "{1}" in _switcher_txt(sw), told)
    check("core: a device that was connected after the last poll is not removed (Windows' list is read again first), "
          "and the listeners are told that it is connected", got == (None, True, [], True, True, ["devices"]), got)


def test_the_playing_device_removed(tmp_path, check):
    # (Windows names only a connected device as the default; a stand-in that names one that is not connected)
    top = str(tmp_path)
    conf = stand_in.fake_apo(top)
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True),
           D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)]
    sw = core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{1}")
    was = sw.playing_key
    sw.remove_device(AWAY)
    key, rec = sw.playing()
    try:
        setup_way = bool(key and not rec["profiles"])  # (as ui/setup_dialog.py reads it)
    except TypeError as e:
        setup_way = repr(e)
    sw.refresh()
    check("core: when the playing device is removed, no device is playing (not a key with no record)",
          (was, key, rec, setup_way, sw.playing_key) == (AWAY, None, None, False, None),
          (was, key, rec, setup_way, sw.playing_key))


def test_a_trial_and_a_compare_on_a_different_device_stay(tmp_path, check):
    top = str(tmp_path)
    sw, _ = _switcher(top)
    pid = _profile(sw, top, "A")
    sw.add_to_device(PLAYING, pid)
    sw.add_to_device(AWAY, pid)
    sw.try_eq(PLAYING, "Preamp: -1 dB\n", "Trial")
    sw.remove_device(AWAY)
    trial = (bool(sw.trial) and sw.trial["key"] == PLAYING, core.TRIAL_FILE in _switcher_txt(sw))
    sw.end_trial()
    sw2, _ = _switcher(os.path.join(top, "second"))
    pid2 = _profile(sw2, top, "B")
    sw2.add_to_device(PLAYING, pid2)
    sw2.add_to_device(AWAY, pid2)
    sw2.compare_toggle(PLAYING)
    sw2.remove_device(AWAY)
    compare = (bool(sw2.compare) and sw2.compare["key"] == PLAYING, core.COMPARE_FILE in _switcher_txt(sw2))
    check("core: an EQ for 5 minutes and an EQ off to compare on a different device stay after a removal",
          trial == (True, True) and compare == (True, True), (trial, compare))


def test_a_hidden_key_with_a_record_again_leaves_the_list(tmp_path, check):
    top = str(tmp_path)
    sw, _ = _switcher(top)
    sw.remove_device(AWAY)
    sw.s["devices"][AWAY] = {"label": "Headphones (Buds)", "guids": ["{1}"], "profiles": [], "active": None}
    sw.refresh()  # (a record from a different source: an older version of the app, or the bring-over)
    check("core: a key in the hidden list that has a record again leaves the list, and the device shows",
          sw.s["hidden_devices"] == [] and sw.device(AWAY) is not None, (sw.s["hidden_devices"], sw.device(AWAY)))


def test_undo_leaves_out_a_last_eq_deleted_meanwhile(tmp_path, check):
    top = str(tmp_path)
    sw, _ = _switcher(top)
    a, b = _profile(sw, top, "A"), _profile(sw, top, "B")
    sw.add_to_device(AWAY, a, switch_on=True)
    sw.add_to_device(AWAY, b, switch_on=False)
    sw.set_active(AWAY, None)  # (A is the EQ it had last)
    sw.set_active(AWAY, b)
    last = sw.record(AWAY).get("last")
    before = sw.remove_device(AWAY)
    sw.remove_profile(a)
    sw.restore_device(before)
    rec = sw.record(AWAY)
    check("core: a profile deleted between the removal and Undo is not the EQ that the device had last after Undo",
          last == a and rec["profiles"] == [b] and rec["active"] == b and "last" not in rec, (last, rec))


def test_the_listeners_are_told_after_the_save(tmp_path, check):
    top = str(tmp_path)
    sw, _ = _switcher(top)
    sw.add_to_device(AWAY, _profile(sw, top, "A"))
    seen = []

    def told(what, info):
        with open(os.path.join(top, "s.json"), encoding="utf-8") as fh:
            saved = json.load(fh)
        seen.append((what, AWAY in saved["devices"], "{1}" in _switcher_txt(sw)))
    sw.listeners.append(told)
    before = sw.remove_device(AWAY)
    removal = list(seen)
    seen.clear()
    sw.restore_device(before)
    check("core: after a removal and after its Undo, the listeners are told when the settings file and APO's file "
          "have the change", removal == [("devices", False, False)] and seen == [("devices", True, True)],
          (removal, seen))
