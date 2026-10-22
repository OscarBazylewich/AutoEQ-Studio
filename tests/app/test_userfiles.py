"""Moving your files (userfiles.py): an older copy's targets, measurements, saved EQs and presets moved into your
files' folders (a different file of the same name kept as "(2)", the same one not twice, the old records of where
they came from merged), a folder moved onto itself (also by another path: a junction) losing nothing, and Change…
moving them all to a new folder, which can't be the program's own or one of your files' folders. Moved from
selftest.py's userfiles_checks.

The three run as a chain, in this order, on one set of folders in the test folder: the app's folders are pointed
there for this file only (AUTOEQSTUDIO_ROOT and AUTOEQSTUDIO_DATA, then paths.locate()), and put back afterwards,
even when a test fails. (This file never imports the EQ part: eq.paths keeps the folders it was first loaded with.)"""
import _winapi
import json
import os
import types

import pytest

import paths
import userfiles
from helpers import session


@pytest.fixture(scope="module")
def place(tmp_path_factory):
    """The app's folders in this file's own test folder (selftest.py lines 783-785), put back as the session's when
    the file is done (lines 840-846)."""
    top = str(tmp_path_factory.mktemp("userfiles"))
    mp = pytest.MonkeyPatch()
    try:
        mp.setenv("AUTOEQSTUDIO_ROOT", os.path.join(top, "files"))
        mp.setenv("AUTOEQSTUDIO_DATA", os.path.join(top, "fdata"))
        paths.locate()
        yield types.SimpleNamespace(top=top, moved=False)
    finally:
        mp.undo()
        paths.locate()
    assert os.path.normcase(paths.DATA) == os.path.normcase(session.SESSION.data), \
        f"the app's folders weren't put back as the session's: {paths.DATA}"


def _after_the_move(place):
    if not place.moved:
        pytest.fail("This test continues test_older_copy_moved_in (it works on the files that test moves in): run the "
                    "whole file.", pytrace=False)


def test_older_copy_moved_in(place, check):
    # (an older copy's inputs\target, output\ … into the folder; a different file of the same name kept as (2))
    top = place.top
    old = os.path.join(top, "old")
    for rel, text in ((r"inputs\target\T.csv", "20 0"), (r"inputs\measurement\M L.txt", "20 1"),
                      (r"output\My EQ.txt", "Preamp: -3 dB"), (r"presets\P.json", "{}"),
                      (r"inputs\sources.json", '{"M L.txt": {"site": "Old"}, "T.csv": {"site": "Old"}}')):
        os.makedirs(os.path.dirname(os.path.join(old, rel)), exist_ok=True)
        with open(os.path.join(old, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    os.makedirs(paths.MEASUREMENTS)
    with open(os.path.join(paths.MEASUREMENTS, "M L.txt"), "w", encoding="utf-8") as fh:
        fh.write("20 9")  # (a different file of the same name: both kept)
    os.makedirs(paths.TARGETS)
    with open(os.path.join(paths.TARGETS, "T.csv"), "w", encoding="utf-8") as fh:
        fh.write("20 0")  # (the same file: not kept twice)
    os.makedirs(os.path.dirname(paths.SOURCES))
    with open(paths.SOURCES, "w", encoding="utf-8") as fh:
        json.dump({"T.csv": {"site": "Ours"}}, fh)
    pairs, sources = userfiles.old_places([old])
    n = userfiles.count(pairs)
    moved, renamed = userfiles.move_all(pairs, sources)
    place.moved = True
    have = sorted(os.path.relpath(os.path.join(d, f), paths.ROOT) for d, _s, fs in os.walk(paths.ROOT) for f in fs)
    with open(paths.SOURCES, encoding="utf-8") as fh:
        recs = json.load(fh)
    # was selftest.py:808
    check("your files: an older copy's targets, measurements, saved EQs and presets moved into their folders; a "
          "different file of the same name kept as (2), the same one not twice; the old records merged, ours first; "
          "the old folders gone", (n, moved, renamed) == (4, 3, 1) and have == [
              os.path.join("Measurements", "M L (2).txt"), os.path.join("Measurements", "M L.txt"),
              os.path.join("Presets", "P.json"), os.path.join("Saved EQs", "My EQ.txt"), os.path.join("Targets", "T.csv")]
          and recs == {"T.csv": {"site": "Ours"}, "M L.txt": {"site": "Old"}}
          and (not os.path.exists(old) or not os.listdir(old)), (n, moved, renamed, have, recs, os.listdir(old) if os.path.exists(old) else None))


def test_moving_onto_itself_removes_nothing(place, check):
    # ((review 2) one folder reached by two paths, e.g. a mapped drive; first the same path: nothing removed)
    _after_the_move(place)
    same = userfiles.move_tree(paths.TARGETS, paths.TARGETS)
    link = os.path.join(place.top, "targets-link")
    _winapi.CreateJunction(paths.TARGETS, link)  # (the same folder by another path, as a mapped drive is)
    try:
        linked = userfiles.same_folder(link, paths.TARGETS)
        by_link = userfiles.move_tree(link, paths.TARGETS)
    finally:
        if os.path.lexists(link):  # (the junction only, if the move's tidy-up left it: its folder stays)
            os.rmdir(link)
    # was selftest.py:826
    check("your files: moving a folder onto itself, or onto itself by another path (a junction), removes nothing",
          same == (0, 0) and by_link == (0, 0) and linked and os.path.isfile(os.path.join(paths.TARGETS, "T.csv")),
          (same, by_link, linked))


def test_change_moves_them_all(place, check):
    # (to a new folder; folders that can't hold them: inside the program's folder, here the session's copy of the
    # program, and inside one of your files' own folders)
    _after_the_move(place)
    top = place.top
    new = os.path.join(top, "elsewhere")
    pairs = userfiles.change_pairs(new)
    moved, renamed = userfiles.move_all(pairs)
    there = sorted(os.path.relpath(os.path.join(d, f), new) for d, _s, fs in os.walk(new) for f in fs)
    why = [userfiles.problem_with(p) for p in (os.path.join(paths.PROGRAM, "mine"), os.path.join(paths.TARGETS, "x"),
                                                os.path.join(top, "fine"))]
    # was selftest.py:836
    check("your files: Change… moves them all into the new folder's same folders; not into the program's folder "
          "or one of your files' own", (moved, renamed) == (5, 0) and len(there) == 5
          and "Targets" in {os.path.dirname(t) for t in there} and why[0] and "own folder" in why[0]
          and why[1] and "Targets" in why[1] and why[2] is None, (moved, renamed, there, why))
