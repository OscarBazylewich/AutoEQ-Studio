"""Your targets and measurements (eq\\inputs.py): the device's name read from its files' names, targets told apart from
measurements by name, files added under names Windows accepts (a different file of the same name never replaced:
the new set is numbered as one device), files that aren't curves refused, removing and moving only by a file's name
(never the folder) and never onto a different file, and a file in use for a moment still removed. Moved from
eq_checks.py's module_checks, review2_maths_checks and in_use_checks.

The tests that add or remove files use the session's own Targets and Measurements, put back as new before and after
(fresh_studio, or the chain's own fixture): every file in Measurements is taken as the device's, so a file left
there would change the curves every later test loads."""
import os
import threading
import types

import pytest

from eq import inputs
from helpers.checks import raises  # (eq_checks.py's raises, line 50: the message of a ValueError, or None)

# a made-up curve, 80 points from 20 Hz (eq_checks.py line 151)
CURVE = "".join(f"{20 * 1.1 ** i:.2f}\t{80 + i % 5}\n" for i in range(80))


def test_device_name_from_seating_files(check):
    # was eq_checks.py:147
    check("files: device name from seating files", inputs.device_name(["GATe Wide L1.txt", "GATe Wide R5.txt"]) == "GATe Wide"
          and inputs.device_name([]) == "")


def test_targets_told_apart_by_name(check):
    # was eq_checks.py:149
    check("files: targets told apart by name", [inputs.guess_kind(n) for n in ("Harman IE 2019.txt", "JM-1.txt", "HD600.txt")]
          == ["target", "target", "measurement"])


def test_odd_names_stored_safely(fresh_studio, check):
    curve = CURVE
    # was eq_checks.py:152
    check("files: odd names stored safely", [inputs.add_file("measurement", n, curve) for n in (" .txt", "CON", "x.exe")]
          == ["file.txt", "_CON.txt", "x.exe.txt"])
    for n in ("file.txt", "_CON.txt", "x.exe.txt"):  # (as the old checks did after, lines 159-160)
        inputs.remove_file("measurement", n)


def test_not_a_curve_refused(fresh_studio, check):
    # was eq_checks.py:154
    check("files: a file that isn't a curve is refused", raises(inputs.add_file, "measurement", "x.txt", "hello") is not None)


def test_one_line_repeated_refused(fresh_studio, check):
    # was eq_checks.py:155
    check("files: one line repeated isn't a curve", raises(inputs.add_file, "measurement", "x.txt", "1000 80\n" * 500) is not None)


def test_remove_or_move_needs_a_name(fresh_studio, check):
    # (fresh_studio: Targets holds the sample target, as the old checks' copy did)
    blank = [raises(f, "target", n) for f in (inputs.remove_file, inputs.move_file) for n in ("", ".", "..")]
    # was eq_checks.py:157
    check("files: removing or moving needs a file name (never the folder itself)",
          all(blank) and os.path.isdir(inputs.TARGET_DIR) and os.listdir(inputs.TARGET_DIR), blank)


def test_one_seating_file_names_its_device(check):
    # one ticked file of an IEM is still that IEM
    # was eq_checks.py:796
    check("files: one seating file names its device like several do", inputs.device_name(["GATe Wide L1.txt"]) == "GATe Wide"
          and inputs.device_name(["HD 600.txt"]) == "HD 600", inputs.device_name(["GATe Wide L1.txt"]))


def test_database_measurements_named(check):
    named = [inputs.device_name(x) for x in (["Foo (Bar) 1 L.txt", "Foo (Bar) 1 R.txt", "Foo (Bar) 2 L.txt"],
                                             ["Foo (Bar) 1 L.txt", "Foo (Bar) 1 R.txt"], ["IE 900 L.txt", "IE 900 R.txt"])]
    # was eq_checks.py:2192
    check("files: a database's several measurements (\"Foo 1 L\", \"Foo 2 L\"), or one of them, are named Foo; a "
          "model's own number stays", named == ["Foo (Bar)", "Foo (Bar)", "IE 900"], named)


def test_file_in_use_removed_once_free(fresh_studio, check):
    # A file in use for a moment (a curves load reading it) is still removed: Undo's removal failed so once. (As the old
    # check was: the file held open by this process and let go by a timer after 0.3 s, while remove_file tries again
    # for about a second.)
    p = os.path.join(inputs.folder("measurement"), "Busy for a moment L.txt")
    with open(p, "w") as fh:
        fh.write("20 0\n20000 0\n")
    held = open(p, "rb")
    timer = threading.Timer(0.3, held.close)
    timer.start()
    try:
        inputs.remove_file("measurement", "Busy for a moment L.txt")
        gone = not os.path.exists(p)
    except OSError as e:
        gone = e
    # was eq_checks.py:2601
    check("files: one in use for a moment (being read) is removed once it's free, not left behind", gone is True, gone)
    timer.join()  # (nothing of this test left running; fresh_studio removes the file if it's still there)
    held.close()


# ---------------------------------------------------------------- a chain: files of the same name (lines 777-794)
@pytest.fixture(scope="module")
def dups():
    """eq_checks.py lines 778-781, on the studio as new: a set of two "Dup" files added, one of them again (the same
    file: kept as it is), then a set holding a different file of that name (numbered as one device). The two tests
    below check what was stored, then move one of the files onto Targets. Afterwards every Dup file is removed (as
    the old checks did, lines 792-794) and the studio put back as new."""
    from helpers import studio
    studio.reset()
    curve = CURVE
    other = curve.replace("\t8", "\t7", 5)
    first = inputs.add_files("measurement", [("Dup L1.txt", curve), ("Dup R1.txt", curve)])
    again = inputs.add_files("measurement", [("Dup L1.txt", curve)])
    second = inputs.add_files("measurement", [("Dup L1.txt", other), ("Dup R1.txt", curve), ("Dup L2.txt", other)])
    yield types.SimpleNamespace(other=other, first=first, again=again, second=second)
    inputs.remove_file("target", "Dup L1.txt")
    for n in first + second:
        inputs.remove_file("measurement", n)
    studio.reset()


def test_same_name_kept_new_set_numbered(dups, check):
    first, again, second = dups.first, dups.again, dups.second
    # a different file of the same name is never replaced: the new set is "<name> (2)", before the channel
    # was eq_checks.py:782
    check("files: a different file of the same name is kept; the new set is numbered as one device (the same file: as it is)",
          first == ["Dup L1.txt", "Dup R1.txt"] and again == ["Dup L1.txt"]
          and second == ["Dup (2) L1.txt", "Dup (2) R1.txt", "Dup (2) L2.txt"]
          and inputs.device_name(second) == "Dup (2)", (first, again, second))


def test_move_onto_a_different_file_refused(dups, check):
    other = dups.other
    # moving never replaces a different file of that name in the other folder
    inputs.add_file("target", "Dup L1.txt", other)
    moved_msg = raises(inputs.move_file, "measurement", "Dup L1.txt") or ""
    # was eq_checks.py:789
    check("files: moving onto a different file of that name is refused, both kept",
          "already has a different" in moved_msg and os.path.exists(os.path.join(inputs.MEAS_DIR, "Dup L1.txt"))
          and os.path.exists(os.path.join(inputs.TARGET_DIR, "Dup L1.txt")), moved_msg)
