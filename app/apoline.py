"""Equalizer APO's "Filter:" lines as Equalizer APO itself reads and plays them, from its source (filters/
BiQuadFilterFactory.cpp, BiQuadFilter.cpp and BiQuad.cpp, read 2026-10-26), with nothing heavy imported: Make an EQ
reads EQ files with it (eq\\eqtext.py), and the tray's on/off hotkey works out how loud a profile plays with it
(switcher\\level.py), where the EQ part never loads.

parse(params)          the text after "Filter N:" ("ON PK Fc 100 Hz Gain 3 dB Q 1"): ("biquad", b), ("none", None)
                       for REW's empty slots and switched-off filters of other types, ("other", what) for REW's
                       first-order and Linkwitz filters and words APO doesn't take, ("bad", why). b: {"kind" (PK, LS,
                       HS, LP, HP, BP, NO, AP), "on", "freq" (as written, read as APO reads it), "gain", "value" (Q,
                       or the S of a slope, or a width in octaves), "by_width" (value isn't a Q), "corner" (a shelf's
                       frequency is its corner, moved to its centre)}
centre(b)              the frequency APO makes the filter at (a shelf at its corner moved by 10^(|gain| / 80 / S))
coefficients(b, fs)    APO's biquad (b0, b1, b2, a1, a2), divided by a0, at sample rate fs
gain_db(c, f, fs)      APO's gainAt: the biquad's gain in dB at frequency f

APO's rules: every comma is a decimal point; a frequency written like "8.000" is 8000 Hz (a dot 4th from the end, no
exponent: "because of Room EQ Wizard"); PEQ and REW's Modal are peaks; Q, else a width in octaves (not a shelf's),
else a slope in dB (a shelf's, S = dB / 12); a shelf with neither has S 0.9 at its centre, LP/HP/BP Q 1/√2, a notch
Q 30; "LS"/"HS" with a Q or slope are at their corner, "LSC"/"HSC" at their centre; gain counts for peaks and
shelves only.
"""
import math
import re

KINDS = {"PK": "PK", "PEQ": "PK", "MODAL": "PK", "LS": "LS", "LSC": "LS", "HS": "HS", "HSC": "HS", "LP": "LP",
         "LPQ": "LP", "HP": "HP", "HPQ": "HP", "BP": "BP", "NO": "NO", "AP": "AP"}
NAMES = {"PK": "peaking", "LS": "low-shelf", "HS": "high-shelf", "LP": "low-pass", "HP": "high-pass",
         "BP": "band-pass", "NO": "notch", "AP": "all-pass"}
# REW's own spellings of what APO can't read, as REW meant them (for saying what's left out)
_REW = {"NOTCH": "notch", "ALL": "all-pass", "IIR": "IIR", "L": "Linkwitz transform"}

_TYPE = re.compile(r"^\s*(ON|OFF)\s+([A-Za-z]+)(\d*)", re.I)
_FREQ = re.compile(r"\s+Fc\s*([-+0-9.eE\u00a0]+)\s*H\s*z", re.I)
_GAIN = re.compile(r"\s+Gain\s*([-+0-9.eE]+)\s*dB", re.I)
_Q = re.compile(r"\s+Q\s*([-+0-9.eE]+)", re.I)
_BW = re.compile(r"\s+BW\s+Oct\s*([-+0-9.eE]+)", re.I)
_SLOPE = re.compile(r"^\s*([-+0-9.eE]+)\s*dB", re.I)


def number(text):
    try:
        v = float(text)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def read_freq(text):
    """A frequency as APO reads it: a non-breaking space dropped; "8.000" (a dot 4th from the end, no exponent) is
    8000."""
    s = text.replace("\u00a0", "")
    v = number(s)
    if v is not None and len(s) >= 5 and "e" not in s.lower() and s[-4] == ".":
        v *= 1000
    return v


def parse(params):
    """One Filter line's text after the colon, read as APO reads it (see the module's words)."""
    p = params.replace(",", ".")
    m = _TYPE.match(p)
    if not m:
        return "bad", "it doesn't start with ON or OFF and a filter type"
    on, word, digits = m[1].upper() == "ON", m[2].upper(), m[3]
    rest = p[m.end():]
    kind = KINDS.get(word)
    if word == "NONE" or (not on and kind not in ("PK", "LS", "HS")):
        return "none", None  # (REW's empty slot; a switched-off filter of another type plays nothing)
    if word in ("LP", "HP") and digits == "1":  # (REW's first-order filters: APO plays a second-order one instead)
        return "other", f"first-order {NAMES[word]}"
    if kind is None:
        return "other", _REW.get(word, word)
    rest = (digits + rest) if digits else rest  # ("LS12dB": the slope follows the type)
    f = _FREQ.search(rest)
    freq = read_freq(f[1]) if f else None
    if freq is None or freq <= 0:
        return "bad", "no frequency (Fc … Hz)"
    gain = 0.0
    g = _GAIN.search(rest)
    if kind in ("PK", "LS", "HS", "BP"):
        gain = number(g[1]) if g else None
        if gain is None and kind != "BP":
            return "bad", "no gain (Gain … dB)"
        gain = gain or 0.0
    shelf = kind in ("LS", "HS")
    value, by_width = 0.0, False
    q = _Q.search(rest)
    if q and number(q[1]) is not None:
        value = number(q[1])
    bw = None if shelf else _BW.search(rest)
    if bw and number(bw[1]) is not None:
        value, by_width = number(bw[1]), True
    slope = _SLOPE.match(rest) if shelf else None
    if slope and number(slope[1]) is not None:
        value, by_width = number(slope[1]), True
    corner = False
    if value == 0:
        if kind in ("PK", "AP"):
            return "bad", "no Q or width"
        if kind in ("LP", "HP", "BP"):
            value = 1 / math.sqrt(2)
        elif shelf:
            value, by_width = 0.9, True
        elif kind == "NO":
            value = 30.0
    elif shelf:
        if by_width:
            value /= 12
        corner = not word.endswith("C")
    if value <= 0:
        return "bad", "no Q or width"
    return "biquad", {"kind": kind, "on": on, "freq": freq, "gain": gain, "value": value, "by_width": by_width,
                      "corner": corner}


def shelf_s(b):
    """A shelf's steepness S (from its Q when it was given one), as APO works it out."""
    if b["by_width"]:
        return b["value"]
    a = 10 ** (b["gain"] / 40)
    return 1 / ((1 / (b["value"] ** 2) - 2) / (a + 1 / a) + 1)


def centre(b):
    """The frequency APO makes the filter at: a shelf at its corner moved to its centre (BiQuadFilter::initialize)."""
    if not b["corner"] or b["kind"] not in ("LS", "HS"):
        return b["freq"]
    s = shelf_s(b)
    if s <= 0:
        return b["freq"]
    c = 10 ** (abs(b["gain"]) / 80 / s)
    return b["freq"] * c if b["kind"] == "LS" else b["freq"] / c


def coefficients(b, fs):
    """APO's biquad for the filter (BiQuad::BiQuad): (b0, b1, b2, a1, a2), divided by a0; None when it can't be made
    (its frequency past half the sample rate, or a slope too steep for its gain)."""
    kind, gain, value = b["kind"], b["gain"], b["value"]
    a = 10 ** (gain / (40 if kind in ("PK", "LS", "HS") else 20))
    w = 2 * math.pi * centre(b) / fs
    if not 0 < w < math.pi:
        return None
    sn, cs = math.sin(w), math.cos(w)
    if not b["by_width"]:
        alpha = sn / (2 * value)
    elif kind in ("LS", "HS"):
        inside = (a + 1 / a) * (1 / value - 1) + 2
        if inside <= 0:
            return None
        alpha = sn / 2 * math.sqrt(inside)
    else:
        alpha = sn * math.sinh(math.log(2) / 2 * value * w / sn)
    beta = 2 * math.sqrt(a) * alpha
    if kind == "PK":
        c = (1 + alpha * a, -2 * cs, 1 - alpha * a, 1 + alpha / a, -2 * cs, 1 - alpha / a)
    elif kind == "LS":
        c = (a * ((a + 1) - (a - 1) * cs + beta), 2 * a * ((a - 1) - (a + 1) * cs), a * ((a + 1) - (a - 1) * cs - beta),
             (a + 1) + (a - 1) * cs + beta, -2 * ((a - 1) + (a + 1) * cs), (a + 1) + (a - 1) * cs - beta)
    elif kind == "HS":
        c = (a * ((a + 1) + (a - 1) * cs + beta), -2 * a * ((a - 1) + (a + 1) * cs), a * ((a + 1) + (a - 1) * cs - beta),
             (a + 1) - (a - 1) * cs + beta, 2 * ((a - 1) - (a + 1) * cs), (a + 1) - (a - 1) * cs - beta)
    elif kind == "LP":
        c = ((1 - cs) / 2, 1 - cs, (1 - cs) / 2, 1 + alpha, -2 * cs, 1 - alpha)
    elif kind == "HP":
        c = ((1 + cs) / 2, -(1 + cs), (1 + cs) / 2, 1 + alpha, -2 * cs, 1 - alpha)
    elif kind == "BP":
        c = (alpha, 0.0, -alpha, 1 + alpha, -2 * cs, 1 - alpha)
    elif kind == "NO":
        c = (1.0, -2 * cs, 1.0, 1 + alpha, -2 * cs, 1 - alpha)
    else:  # (AP)
        c = (1 - alpha, -2 * cs, 1 + alpha, 1 + alpha, -2 * cs, 1 - alpha)
    a0 = c[3]
    return c[0] / a0, c[1] / a0, c[2] / a0, c[4] / a0, c[5] / a0


def gain_db(c, f, fs):
    """The biquad's gain in dB at frequency f (BiQuad::gainAt)."""
    b0, b1, b2, a1, a2 = c
    phi = math.sin(math.pi * f / fs) ** 2
    num = (b0 + b1 + b2) ** 2 - 4 * (b0 * b1 + 4 * b0 * b2 + b1 * b2) * phi + 16 * b0 * b2 * phi * phi
    den = (1 + a1 + a2) ** 2 - 4 * (a1 + 4 * a2 + a1 * a2) * phi + 16 * a2 * phi * phi
    if num <= 0 or den <= 0:
        return -200.0 if num <= 0 else 200.0
    return 10 * math.log10(num) - 10 * math.log10(den)
