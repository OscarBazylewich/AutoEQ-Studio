"""Equalizer APO's side (switcher\\apo.py), on stand-in APO config folders in the test's own folder (never the real
one): the folder found and writable, the EQ files config.txt uses offered, the lines on now found, setting up (the
other lines turned off, one line added, the BOM, CRLF and the first copy of config.txt kept) and taking it out again,
AutoEQ Studio's per-device file (switcher.txt) as APO reads it and written only when it changes, and APO's
Configurator found by either of its names. Moved from selftest.py's apo_checks, and the Configurator's names from its
qt_checks (they need no window).

apo_checks worked on one folder from start to end; here each check that stands alone gets a new stand-in folder (as
it was when the old check ran), and the two chains (set up, then "set up" and taking it out; switcher.txt written
twice, then no temporary files) keep theirs in a module-wide fixture, their tests in the old order."""
import os
import types

import pytest

import textfile
from helpers import apo as stand_in
from switcher.apo import INCLUDE_LINE, OFF_MARK, Apo


def test_found_and_writable(fake_apo, check):
    a = Apo(fake_apo)
    # was selftest.py:96
    check("apo: the config folder is found and writable", a.found and a.writable())


def test_files_offered(fake_apo, check):
    a = Apo(fake_apo)
    refs = [os.path.basename(p) for p in a.referenced_files()]
    # was selftest.py:98
    check("apo: the EQ files config.txt uses, on or off, are offered", refs == ["Samson.txt", "EarPods.txt"], refs)


def test_lines_on_found(fake_apo, check):
    a = Apo(fake_apo)
    # was selftest.py:99
    check("apo: the lines on now are found", a.others_on(a.read_config()) == ["Include: EarPods.txt"])


@pytest.fixture(scope="module")
def set_up(tmp_path_factory):
    """AutoEQ Studio set up twice on a new stand-in folder (selftest.py lines 94-105): the lines turned off, then
    config.txt and the copy kept of it, as bytes. The three tests after it use it in the old order: set up, "set up",
    taken out again."""
    conf = stand_in.fake_apo(str(tmp_path_factory.mktemp("apo-set-up")))
    a = Apo(conf)
    off = a.install_line()
    a.install_line()  # (twice: still one line, and the first copy of config.txt kept)
    with open(a.config_txt, "rb") as fh:
        raw = fh.read()
    with open(os.path.join(conf, "config.txt.autoeq-studio-backup"), "rb") as fh:
        backup = fh.read()
    return types.SimpleNamespace(a=a, off=off, raw=raw, backup=backup)


def test_setting_up(set_up, check):
    off, raw, backup = set_up.off, set_up.raw, set_up.backup
    # was selftest.py:106
    check("apo: setting up turns the other lines off, adds its line once, keeps the BOM, CRLF and the first copy",
          off == ["Include: EarPods.txt"] and raw.startswith(b"\xef\xbb\xbf") and raw.count(INCLUDE_LINE.encode()) == 1
          and (OFF_MARK + "Include: EarPods.txt\r\n").encode() in raw and backup == stand_in.CONFIG, raw)


def test_is_set_up(set_up, check):
    # was selftest.py:109
    check("apo: set up", set_up.a.set_up())


def test_taken_out(set_up, check):
    a = set_up.a
    a.remove_line()
    with open(a.config_txt, "rb") as fh:
        back = fh.read()
    # was selftest.py:113
    check("apo: taking AutoEQ Studio out puts config.txt back as it was", back == stand_in.CONFIG and not a.set_up(), back)


def test_one_section_per_device(check):
    # (switcher_text is the same for any folder: it only makes the text)
    text = Apo.switcher_text([("Headset (EarPods)", ["{5}"], "EarPods.txt"), ("Buds", ["{1}", "{2}"], None),
                              ("Never seen", [], "x.txt")])
    lines = [x for x in text.split("\r\n") if x and not x.startswith("#")]
    # was selftest.py:117
    check("apo: one Device section per device (its endpoints, its profile), none without endpoints, then all devices",
          lines == ["Device: {5}", "Include: profiles\\EarPods.txt", "Device: {1}; {2}", "Device: all"], lines)


def test_ids_with_braces(check):
    lines = [x for x in Apo.switcher_text([("A", ["{d3bfcd09-14ce-41c7-b4f5-e83278716021}"], None)]).split("\r\n")
             if x.startswith("Device: {")]
    # was selftest.py:121
    check("apo: each id written as Windows names it, with its { } (APO compares whole words: a bare id never matched)",
          lines == ["Device: {d3bfcd09-14ce-41c7-b4f5-e83278716021}"], lines)


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    """switcher.txt written twice with the same sections on a new stand-in folder (selftest.py lines 123-124):
    whether each write wrote. The second test after it looks in the folder those writes made."""
    a = Apo(stand_in.fake_apo(str(tmp_path_factory.mktemp("apo-written"))))
    first = a.write_switcher([("A", ["{5}"], None)])
    second = a.write_switcher([("A", ["{5}"], None)])
    return types.SimpleNamespace(a=a, first=first, second=second)


def test_written_only_when_changed(written, check):
    # was selftest.py:125
    check("apo: the file is written only when it changes (APO reloads on every write)", written.first and not written.second)


def test_no_temporary_files(written, check):
    # was selftest.py:126
    check("apo: no temporary files left", not [f for f in os.listdir(written.a.own) if f.endswith(".tmp")])


def test_empty_config(fake_apo, check):
    a = Apo(fake_apo)
    textfile.write_atomic(a.config_txt, b"")
    a.install_line()
    # was selftest.py:129
    check("apo: an empty config.txt gets just the line", textfile.read(a.config_txt).strip() == INCLUDE_LINE)


def test_configurator_names(fake_apo, tmp_path, check):
    # (APO's Configurator: DeviceSelector.exe in APO 1.3 and later, Configurator.exe before. Four stand-in APO
    # program folders, in this test's own folder: the old check made them with tempfile.mkdtemp and removed them)
    found = []
    for i, names in enumerate((["DeviceSelector.exe"], ["Configurator.exe"], ["DeviceSelector.exe", "Configurator.exe"], [])):
        inst = os.path.join(tmp_path, f"apo-install-{i}")
        os.makedirs(inst)
        for n in names:
            open(os.path.join(inst, n), "w").close()
        found.append(os.path.basename(Apo(fake_apo, inst).configurator or ""))
    # was selftest.py:438
    check("APO's Configurator is found by its current name (DeviceSelector.exe) and its old one",
          found == ["DeviceSelector.exe", "Configurator.exe", "DeviceSelector.exe", ""], found)
