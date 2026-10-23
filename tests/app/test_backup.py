"""Settings › Backup (backup.py): everything of yours in one .zip (by the names backups have always had; not the log,
downloads or a trial's file) and back again, keeping how things were first and this PC's folder for your files; a
backup's odd names never written outside its parts, and a file that isn't a backup, or one from a newer AutoEQ
Studio, said plainly. Moved from selftest.py's backup_checks.

The app's folders are pointed at this file's own test folder for its tests (AUTOEQSTUDIO_ROOT and AUTOEQSTUDIO_DATA,
then paths.locate()), and put back afterwards, even when a test fails. The first two run as a chain, in this order:
the second restores the backup the first makes. (This file never imports the EQ part: eq.paths keeps the folders it
was first loaded with.)"""
import json
import os
import types
import zipfile

import pytest

import backup
import paths
from helpers import session


@pytest.fixture(scope="module")
def place(tmp_path_factory):
    """The app's folders in this file's own test folder, with nine files of the kinds a backup takes or leaves out
    (selftest.py lines 679-695); put back as the session's when the file is done (lines 742-748)."""
    top = str(tmp_path_factory.mktemp("backup"))
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("AUTOEQSTUDIO_ROOT", top)
        mp.setenv("AUTOEQSTUDIO_DATA", os.path.join(top, "data"))
        paths.locate()
        prof = os.path.join(top, "apo", "AutoEQ Studio", "profiles")
        files = {os.path.join(top, "data", "settings.json"): '{"profiles": {"a": 1}, "files_folder": "Z:/gone"}',
                 os.path.join(top, "data", "eq", "history.json"): "[1]",
                 os.path.join(top, "data", "app.log"): "log",
                 os.path.join(top, "Targets", "T.csv"): "20 0",
                 os.path.join(top, "Saved EQs", "My EQ.txt"): "Preamp: -3 dB",
                 os.path.join(top, "downloads", "site", "M.txt"): "20 0",
                 os.path.join(prof, "P.txt"): "Preamp: -1 dB", os.path.join(prof, "_trying.txt"): "Preamp: 0 dB",
                 os.path.join(prof, "_Aux.txt"): "Preamp: -2 dB"}  # (a profile named Aux: Windows' reserved name, "_")
        for p, text in files.items():
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fh:
                fh.write(text)
        yield types.SimpleNamespace(top=top, prof=prof, zip=None)
    finally:
        mp.undo()
        paths.locate()
    assert os.path.normcase(paths.DATA) == os.path.normcase(session.SESSION.data), \
        f"the app's folders weren't put back as the session's: {paths.DATA}"


def test_one_zip_of_whats_yours(place, check):
    z = os.path.join(place.top, "b.zip")
    info = backup.make(z, place.prof)
    place.zip = z
    with zipfile.ZipFile(z) as zf:
        names = sorted(zf.namelist())
    # was selftest.py:699
    check("backup: one .zip of what's yours (settings, History, targets, saved EQs, the profiles' files; by the "
          "names backups have always had), not the log, downloads or a trial's file", names == ["apo-profiles/P.txt", "apo-profiles/_Aux.txt", "backup.json", "data/eq/history.json",
                                                         "data/settings.json", "inputs/target/T.csv",
                                                         "output/My EQ.txt"]
          and (info["files"], info["profiles"]) == (6, 2), names)


def test_restoring_puts_files_back(place, check):
    top, prof = place.top, place.prof
    if not place.zip:
        pytest.fail("This test continues test_one_zip_of_whats_yours (it restores the backup that test makes): run the "
                    "whole file.", pytrace=False)
    with open(os.path.join(top, "data", "settings.json"), "w") as fh:
        fh.write('{"profiles": {}}')
    os.remove(os.path.join(top, "Targets", "T.csv"))
    os.remove(os.path.join(prof, "P.txt"))
    with open(os.path.join(top, "Targets", "New.csv"), "w") as fh:
        fh.write("20 1")
    got = backup.restore(place.zip, prof, keep_dir=os.path.join(top, "kept"))
    with open(os.path.join(top, "data", "settings.json")) as fh:
        settings = json.load(fh)
    back = (settings, os.path.isfile(os.path.join(top, "Targets", "T.csv")),
            os.path.isfile(os.path.join(top, "Targets", "New.csv")), os.path.isfile(os.path.join(prof, "P.txt")))
    with zipfile.ZipFile(got["kept"]) as zf:
        kept = zf.namelist()
    # was selftest.py:715
    check("backup: restoring puts the files back (settings, a deleted target, a profile), keeps the others, and "
          "keeps how things were first; your files' folder stays this PC's (review 2)", back == ({"profiles": {"a": 1}}, True, True, True)
          and got["files"] == 6 and "inputs/target/New.csv" in kept, (back, got))


def test_odd_backups(place, check):
    # (odd backups: not one, a newer one, names reaching outside its parts. Outside: <top>\..\evil.txt and
    # <top's parent>\evil2.txt, pytest's own folder for this run's test folders, in the session folder)
    top, prof = place.top, place.prof
    odd = os.path.join(top, "odd.zip")
    with zipfile.ZipFile(odd, "w") as zz:
        zz.writestr("backup.json", json.dumps({"app": "AutoEQ Studio", "format": 1, "made": "x", "files": 3,
                                               "profiles": 0}))
        zz.writestr("../evil.txt", "x")
        zz.writestr("data/../../evil2.txt", "x")
        zz.writestr("data/other.json", "x")
        zz.writestr("inputs/target/Ok.csv", "20 0")
    r = backup.restore(odd, prof, keep_dir=os.path.join(top, "kept"))
    newer = os.path.join(top, "newer.zip")
    with zipfile.ZipFile(newer, "w") as zz:
        zz.writestr("backup.json", json.dumps({"app": "AutoEQ Studio", "format": 99}))
    said = []
    for bad in (os.path.join(top, "Targets", "Ok.csv"), newer):
        try:
            backup.read(bad)
        except ValueError as e:
            said.append(str(e))
    # was selftest.py:737
    check("backup: a backup's odd names are never written outside its parts; a file that isn't a backup, or one "
          "from a newer AutoEQ Studio, is said", r["files"] == 1 and not os.path.exists(os.path.join(top, "..", "evil.txt"))
          and not os.path.exists(os.path.join(os.path.dirname(top), "evil2.txt"))
          and not os.path.exists(os.path.join(top, "data", "other.json")) and len(said) == 2
          and "isn't one of" in said[0] and "newer" in said[1], (r, said))
