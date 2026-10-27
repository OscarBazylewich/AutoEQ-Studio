"""How loud an EQ plays next to no EQ, for the on/off hotkey's level matching (2026-10-26): the measure Listen matches
by (ui\\audio.py's levels: pink noise, A-weighted, its power averaged over 241 frequencies from 20 Hz to 20 kHz),
worked out here in plain Python from the EQ's own file as Equalizer APO plays it (apoline.py): its pre-amps, its
filters of every type, a graphic EQ's points. Nothing heavy is imported: it runs in the tray, where the EQ part never
loads.

level(text, fs) -> {"db": how much louder (+) or quieter (-) than no EQ, "peak": its highest boost, "complete": False
when it has parts this can't measure (a convolution, a plug-in, Include …: those are left out of the sum)}.
Only what plays on every channel and device counts (Channel: and Device: other than "all" are passed over).
"""
import math
import re

import apoline

GRID = [20 * 1000 ** (i / 240) for i in range(241)]


def _a_weight(f):
    f2 = f * f
    ra = 12194 ** 2 * f2 * f2 / ((f2 + 20.6 ** 2) * math.sqrt((f2 + 107.7 ** 2) * (f2 + 737.9 ** 2)) * (f2 + 12194 ** 2))
    return ra * ra


AW = [_a_weight(f) for f in GRID]
_AW_SUM = sum(AW)
_CMD = re.compile(r"^\s*([A-Za-z]+)(?:\s*\d+)?\s*:\s*(.*)$")
_PREAMP = re.compile(r"^\s*([-+0-9.eE]+)\s*dB", re.I)
_UNMEASURED = {"convolution", "include", "copy", "delay", "stage", "if", "elseif", "else", "endif", "eval",
               "vstplugin"}


def _graphic(rest):
    """A GraphicEQ line's points [(Hz, dB)], A to Z by frequency."""
    pts = []
    for part in rest.replace(",", ".").split(";"):
        nums = part.split()
        if len(nums) == 2:
            f, g = apoline.number(nums[0]), apoline.number(nums[1])
            if f and f > 0 and g is not None:
                pts.append((f, g))
    return sorted(pts)


def _graphic_db(pts, f):
    """A graphic EQ's gain at f: straight between its points on a log-frequency scale, held past its ends."""
    if f <= pts[0][0]:
        return pts[0][1]
    if f >= pts[-1][0]:
        return pts[-1][1]
    for (f0, g0), (f1, g1) in zip(pts, pts[1:]):
        if f0 <= f <= f1:
            t = 0.0 if f1 == f0 else (math.log(f) - math.log(f0)) / (math.log(f1) - math.log(f0))
            return g0 + (g1 - g0) * t
    return 0.0


def level(text, fs=48000):
    """The EQ's loudness next to no EQ (see the module's words)."""
    gains = [0.0] * len(GRID)
    complete, scope = True, {"channel": True, "device": True}
    for line in str(text or "").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _CMD.match(s)
        if not m:
            continue
        cmd, rest = m[1].lower(), m[2]
        if cmd in ("channel", "device"):
            scope[cmd] = rest.strip().lower() in ("all", "")
            continue
        if not all(scope.values()):
            continue
        if cmd == "preamp":
            p = _PREAMP.match(rest.replace(",", "."))
            v = apoline.number(p[1]) if p else None
            if v is not None:
                gains = [g + v for g in gains]
        elif cmd == "filter":
            kind, b = apoline.parse(rest)
            if kind == "biquad" and b["on"]:
                c = apoline.coefficients(b, fs)
                if c is None:
                    complete = False
                    continue
                gains = [g + apoline.gain_db(c, f, fs) for g, f in zip(gains, GRID)]
            elif kind in ("other", "bad"):
                complete = False
        elif cmd == "graphiceq":
            pts = _graphic(rest)
            if pts:
                gains = [g + _graphic_db(pts, f) for g, f in zip(gains, GRID)]
        elif cmd in _UNMEASURED:
            complete = False
    loud = 10 * math.log10(sum(w * 10 ** (g / 10) for w, g in zip(AW, gains)) / _AW_SUM)
    return {"db": round(loud, 2), "peak": round(max(gains), 2), "complete": complete}
