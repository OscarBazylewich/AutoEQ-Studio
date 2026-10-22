"""Reading an EQ file to make a profile of it. Profiles are Equalizer APO's own format: what AutoEQ Local's
"Equalizer APO" file, AutoEq's ParametricEQ.txt, squig.link's export and APO's Editor write ("Preamp: -6.5 dB",
"Filter 1: ON PK Fc 105 Hz Gain 3.2 dB Q 0.70", "GraphicEQ: 20 -1; 25 -0.5; …").

A profile is a copy of the file, as it is. What it has is counted for the lists (filters on, pre-amp). Lines that
would break AutoEQ Studio's file are refused:
- "Device:" would take the profile off the device it's chosen for (and onto others);
- "Include:" and a convolution's file are found relative to the file they're in, and the copy is somewhere else
  (a convolution with a full path, "C:\\…\\x.wav", works anywhere and is kept).
"""
import os
import re

from textfile import read

_CMD = re.compile(r"^\s*([A-Za-z]+)(?:\s*\d+)?\s*:\s*(.*)$")
_PREAMP = re.compile(r"^\s*([-+]?\d+(?:[.,]\d+)?)\s*dB", re.I)


class NotAnEqFile(ValueError):
    """The file can't be a profile; the message says why, in plain words."""


def summary(text):
    """{"filters": filters switched on, "preamp": dB (the Preamp lines added up), "graphic": has a GraphicEQ line}.
    Raises NotAnEqFile for a file that isn't one, or has a line a profile can't keep."""
    filters, preamp, graphic, eq_lines = 0, 0.0, False, 0
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _CMD.match(s)
        if not m:
            continue
        cmd, rest = m.group(1).lower(), m.group(2)
        if cmd == "device":
            raise NotAnEqFile(f"Line {n} chooses devices (\"Device:\"): AutoEQ Studio does that itself, so a profile "
                              "can't have it.")
        if cmd == "include":
            raise NotAnEqFile(f"Line {n} brings in another file (\"Include:\"): add that file as the profile instead.")
        if cmd == "convolution" and not re.match(r"^\s*([A-Za-z]:\\|\\\\)", rest):
            raise NotAnEqFile(f"Line {n} uses a convolution file by a short path: give its full path (C:\\…) in the "
                              "file, or add it without that line.")
        if cmd == "filter":
            eq_lines += 1
            if re.match(r"^\s*ON\b", rest, re.I):
                filters += 1
        elif cmd == "preamp":
            eq_lines += 1
            p = _PREAMP.match(rest)
            if p:
                preamp += float(p.group(1).replace(",", "."))
        elif cmd == "graphiceq":
            eq_lines += 1
            graphic = True
        elif cmd in ("convolution", "channel", "copy", "stage", "delay", "loadplugin"):
            eq_lines += 1
    if not eq_lines:
        raise NotAnEqFile("There's no EQ in it: no filters, pre-amp or GraphicEQ line in Equalizer APO's format.")
    return {"filters": filters, "preamp": round(preamp, 2), "graphic": graphic}


def read_eq(path):
    """(the file's bytes, its summary). The bytes are copied as they are (APO read them like that already)."""
    if os.path.getsize(path) > 2_000_000:
        raise NotAnEqFile("It's too big to be an EQ file (over 2 MB).")
    with open(path, "rb") as fh:
        raw = fh.read()
    return raw, summary(read(path))


# words that only say where a file came from, taken off the end of a name made from it
_TAILS = re.compile(r"(\s*[-–]\s*(best fit|website autoeq.*|filters?)|\s*(equalizerapo|parametriceq|fixedbandeq|"
                    r"graphiceq|eq|filters?))+$", re.I)


def name_from_file(path):
    """A profile's name from its file: "Truthear GATe ... - Best fit - filters.txt" → "Truthear GATe ..."."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return (_TAILS.sub("", stem).strip(" -–_") or stem)[:80]
