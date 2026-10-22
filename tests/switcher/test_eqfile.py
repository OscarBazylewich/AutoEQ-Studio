"""EQ files (switcher\\eqfile.py): what a profile's EQ file holds (the filters switched on, the pre-amp, a GraphicEQ),
which files are refused, and a profile's name from its file's name. Moved from selftest.py's eqfile_checks."""
from helpers.apo import EARPODS
from switcher import eqfile


def test_filters_and_preamp(check):
    s = eqfile.summary(EARPODS.decode())
    # was selftest.py:46
    check("eq files: filters switched on and the pre-amp counted", s == {"filters": 2, "preamp": -26.7, "graphic": False}, s)


def test_graphic_eq_and_decimal_comma(check):
    s = eqfile.summary("Preamp: -3,3 dB\nGraphicEQ: 20 -1; 1000 0; 20000 2\n")
    # was selftest.py:48
    check("eq files: a GraphicEQ, and a decimal comma", s == {"filters": 0, "preamp": -3.3, "graphic": True}, s)


def test_refused(check):
    refused = []
    for text in ("Device: Speakers\nPreamp: 1 dB", "Include: other.txt\n", "Convolution: room.wav\n", "hello\n", ""):
        try:
            eqfile.summary(text)
        except eqfile.NotAnEqFile as e:
            refused.append(str(e)[:12])
    # was selftest.py:55
    check("eq files: a Device or Include line, a convolution by a short path, and no EQ at all are refused",
          len(refused) == 5, refused)
    # was selftest.py:57 (no check() of its own there either: summary() raises NotAnEqFile, failing the test, if a
    # convolution with a full path were refused)
    eqfile.summary("Convolution: C:\\IRs\\room.wav\n")  # (a full path works anywhere: kept)


def test_name_from_file(check):
    names = [eqfile.name_from_file(n) for n in ("Truthear GATe to Harman - Best fit - filters.txt",
                                                "Samson SR950 ParametricEQ.txt", "Moondrop Aria EqualizerAPO.txt",
                                                "EQ.txt")]
    # was selftest.py:61
    check("eq files: a profile's name leaves out where the file came from", names ==
          ["Truthear GATe to Harman", "Samson SR950", "Moondrop Aria", "EQ"], names)
