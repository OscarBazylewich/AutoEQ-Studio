"""A profile's EQ updated in place (switcher\\core.py's update_profile, 2026-10-26: Make an EQ's EQ by hand, begun from
a profile, put back into it with Use on device › Update): its file holds the new EQ, while its name, its file's name,
the devices that have it and the one it's switched on for stay, so they hear the change at once; a file that isn't an
EQ, or a profile that's gone, changes nothing. Since 2026-11-10 any result of Make an EQ can update a profile you have
(Use on device › Update a profile): the update gives back what its Undo needs, and restore_profile puts the profile's
file back byte for byte with its old record (or says the profile was deleted, or that its file changed since, and
changes nothing); a profile whose file is gone gets it again (and Undo removes it); a source sets the profile's From.
on_for gives the devices a profile is switched on for, not those that only have it in their list (used_by). A save
that fails puts the update (or its Undo) back and raises. On a stand-in APO folder in the test's own folder."""
import os

import pytest

import textfile
from helpers import apo as stand_in
from switcher import core, eqfile
from switcher import devices as D
from switcher.apo import Apo

KEY = "Headset|EarPods"
KEY2 = "Speakers|Realtek"
HEADSET = D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)
SPEAKERS = D.Endpoint("{6}", "Speakers", "Realtek", D.ACTIVE, True)
OLD = b"Preamp: -3 dB\r\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\r\n# a note\r\n"
NEW = "Preamp: -5 dB\nFilter 1: ON PK Fc 1000 Hz Gain 5 dB Q 1\nFilter 2: ON PK Fc 3000 Hz Gain -2 dB Q 2\n"


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _switcher(tmp_path, eps):
    top = str(tmp_path)
    conf = stand_in.fake_apo(top)
    textfile.take_set_aside()  # (nothing another test set aside: the Switcher would take it as its own)
    s = core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: list(eps), playing=lambda: "{5}")
    s.top = top
    return s


@pytest.fixture
def sw(tmp_path):
    return _switcher(tmp_path, [HEADSET])


@pytest.fixture
def sw2(tmp_path):
    """Two devices: Headset (EarPods), playing, and Speakers (Realtek)."""
    return _switcher(tmp_path, [HEADSET, SPEAKERS])


def _old_profile(sw, name="Mine"):
    """A profile whose file has CRLF line ends and a comment (bytes that Undo must give back as they were)."""
    path = os.path.join(sw.top, f"{name}.txt")
    with open(path, "wb") as fh:
        fh.write(OLD)
    return sw.import_profile(path, name)


def _file(sw, pid):
    return os.path.join(sw.apo.profiles, sw.profiles()[pid]["file"])


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
          and gone == "The profile is not there.", (refused, gone))


def test_update_then_undo_puts_the_old_file_back(sw, check):
    pid = _old_profile(sw)
    sw.add_to_device(KEY, pid, switch_on=True)
    sw.profiles()[pid]["changed"] = "2026-01-02 03:04"  # (an update before this one: its date must come back)
    rec_before = dict(sw.profiles()[pid])
    result = _write(os.path.join(sw.top, "Result.txt"), NEW)
    before = sw.update_profile(pid, result, source=os.path.abspath(result))
    p = sw.profiles()[pid]
    updated = (_bytes(_file(sw, pid)) != OLD, p["filters"], os.path.basename(p["source"]), p["changed"] != "2026-01-02 03:04")
    told = []
    sw.listeners.append(lambda what, info: told.append(what))
    switcher_txt = os.path.join(sw.apo.own, "switcher.txt")
    os.remove(switcher_txt)  # (so that Undo is seen to write APO's file again)
    why = sw.restore_profile(pid, before)
    check("core: an update gives back what Undo needs; Undo puts the profile's file back byte for byte (CRLF and a "
          "comment kept), with its old counts, date and From, writes APO's file and tells the screens",
          isinstance(before, dict) and before["raw"] == OLD and updated == (True, 2, "Result.txt", True) and why == ""
          and _bytes(_file(sw, pid)) == OLD and sw.profiles()[pid] == rec_before and "profiles" in told
          and os.path.isfile(switcher_txt) and "profiles\\Mine.txt" in _read(switcher_txt),
          (updated, why, sw.profiles()[pid], rec_before, told))


def test_update_changes_from_only_when_asked(sw, check):
    pid = _old_profile(sw)
    old_source = sw.profiles()[pid]["source"]
    sw.update_profile(pid, _write(os.path.join(sw.top, "Edited.txt"), NEW))
    kept = sw.profiles()[pid]["source"]
    result = _write(os.path.join(sw.top, "Result name.txt"), NEW)
    sw.update_profile(pid, result, source=os.path.abspath(result))
    check("core: an update with a source sets the profile's From to it; with none, From stays",
          kept == old_source and os.path.realpath(sw.profiles()[pid]["source"]) == os.path.realpath(result),
          (old_source, kept, sw.profiles()[pid]["source"]))


def test_undo_after_the_profile_was_deleted_or_its_file_changed(sw, check):
    pid = _old_profile(sw)
    before = sw.update_profile(pid, _write(os.path.join(sw.top, "Result.txt"), NEW))
    with open(_file(sw, pid), "ab") as fh:  # (another program changes the file after the update)
        fh.write(b"Filter 9: ON PK Fc 200 Hz Gain 1 dB Q 1\r\n")
    changed_bytes = _bytes(_file(sw, pid))
    rec = dict(sw.profiles()[pid])
    changed = sw.restore_profile(pid, before)
    kept = _bytes(_file(sw, pid)) == changed_bytes and sw.profiles()[pid] == rec
    other = _old_profile(sw, "Other")
    before2 = sw.update_profile(other, _write(os.path.join(sw.top, "Result2.txt"), NEW))
    sw.remove_profile(other)
    deleted = sw.restore_profile(other, before2)
    check("core: Undo of an update says the profile was deleted, or that its file changed after the update, and "
          "changes nothing then (the other change is kept)",
          changed == "changed" and kept and deleted == "deleted" and other not in sw.profiles()
          and not os.path.exists(os.path.join(sw.apo.profiles, "Other.txt")), (changed, kept, deleted))


def test_update_of_a_profile_whose_file_is_gone(sw, check):
    pid = _old_profile(sw)
    os.remove(_file(sw, pid))
    missing = sw.profile_missing(pid)
    before = sw.update_profile(pid, _write(os.path.join(sw.top, "Result.txt"), NEW))
    made = os.path.isfile(_file(sw, pid)) and not sw.profile_missing(pid)
    why = sw.restore_profile(pid, before)
    check("core: updating a profile whose file is gone makes the file again; Undo removes it again",
          missing and before["raw"] is None and made and why == "" and not os.path.exists(_file(sw, pid))
          and sw.profile_missing(pid), (missing, made, why))


def test_on_for_names_only_the_devices_where_it_is_on(sw2, check):
    pid = _old_profile(sw2)
    sw2.add_to_device(KEY, pid, switch_on=True)
    sw2.add_to_device(KEY2, pid, switch_on=False)
    other = _old_profile(sw2, "Other")
    sw2.add_to_device(KEY2, other, switch_on=True)
    one = sw2.on_for(pid)
    used = sorted(sw2.used_by(pid))
    sw2.add_to_device(KEY2, pid, switch_on=True)  # (now on for both: in Devices' order, A to Z by the name shown)
    sw2.set_nickname(KEY, "Zed")
    both = sw2.on_for(pid)
    check("core: on_for gives the devices that have a profile switched on, in Devices' order, not the ones that only "
          "have it in their list (used_by gives both)",
          one == [KEY] and used == ["Headset (EarPods)", "Speakers (Realtek)"] and both == [KEY2, KEY]
          and sw2.on_for(other) == [] and sw2.on_for("gone") == [], (one, used, both))


def test_an_eq_for_5_minutes_keeps_its_line_ends(sw, check):
    crlf = "Preamp: -3 dB\r\nFilter 1: ON PK Fc 1000 Hz Gain -3 dB Q 1\r\n"  # (as Make an EQ gives it)
    sw.try_eq(KEY, crlf, "Tried")
    first = _bytes(sw.trial_path())
    sw.trial_update(crlf.replace("-3 dB Q", "-4 dB Q"))
    second = _bytes(sw.trial_path())
    sw.end_trial()
    check("core: an EQ for 5 minutes, and each change to it, is written with the text's own CRLF line ends (text mode "
          "made them CR CR LF)",
          first == crlf.encode() and second == crlf.replace("-3 dB Q", "-4 dB Q").encode(), (first, second))


def _disk_record(sw, pid):
    """The profile's record in the settings file on the disk."""
    return textfile.read_json(sw.path)["profiles"][pid]


def test_a_save_that_fails_puts_the_update_and_its_undo_back(sw, check, monkeypatch):
    pid = _old_profile(sw)
    sw.add_to_device(KEY, pid, switch_on=True)
    rec, disk = dict(sw.profiles()[pid]), _disk_record(sw, pid)

    def refuse():
        raise PermissionError("Another program uses the settings file.")
    monkeypatch.setattr(sw, "save", refuse)
    try:
        sw.update_profile(pid, _write(os.path.join(sw.top, "Result.txt"), NEW), source="Result.txt")
        update = None
    except OSError as e:
        update = type(e).__name__
    after_update = (_bytes(_file(sw, pid)) == OLD, sw.profiles()[pid] == rec, _disk_record(sw, pid) == disk)
    monkeypatch.undo()
    before = sw.update_profile(pid, _write(os.path.join(sw.top, "Result.txt"), NEW), source="Result.txt")
    new_bytes, new_rec = _bytes(_file(sw, pid)), dict(sw.profiles()[pid])
    monkeypatch.setattr(sw, "save", refuse)
    try:
        sw.restore_profile(pid, before)
        undo = None
    except OSError as e:
        undo = type(e).__name__
    after_undo = (_bytes(_file(sw, pid)) == new_bytes, sw.profiles()[pid] == new_rec)
    monkeypatch.undo()
    check("core: when the settings can't be saved, an update and its Undo raise the error and put the profile's file "
          "and its record back as they were (no device plays an EQ that the settings don't name)",
          update == "PermissionError" and after_update == (True, True, True)
          and undo == "PermissionError" and after_undo == (True, True)
          and sw.restore_profile(pid, before) == "" and _bytes(_file(sw, pid)) == OLD,
          (update, after_update, undo, after_undo))


def test_a_save_that_fails_removes_a_file_the_update_made(sw, check, monkeypatch):
    pid = _old_profile(sw)
    os.remove(_file(sw, pid))

    def refuse():
        raise OSError("The disk is full.")
    monkeypatch.setattr(sw, "save", refuse)
    try:
        sw.update_profile(pid, _write(os.path.join(sw.top, "Result.txt"), NEW))
        raised = False
    except OSError:
        raised = True
    check("core: when the save fails after an update made a profile's missing file, the file is removed again",
          raised and not os.path.exists(_file(sw, pid)), raised)
