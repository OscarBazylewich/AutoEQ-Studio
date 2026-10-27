"""Reading EQ text made elsewhere (eq\\eqtext.py, 2026-10-26): every Filter line Make an EQ reads draws the curve
Equalizer APO plays for it, checked against APO's own maths (its BiQuadFilterFactory, BiQuadFilter and BiQuad,
transcribed below from its source: how it reads each form, then its coefficients and its gainAt): shelves at a corner
frequency moved to their centre, slopes and widths in octaves as the Q that draws the same curve, decimal commas,
"8.000" read as 8000 Hz. Then whole texts: a Room EQ Wizard export (its header passed over, REW's own type names, the
types an EQ here can't have named), a Peace preset (its shelves by their type codes, its other speakers named), and
Equalizer APO's own lines (switched-off filters kept off, per-channel parts, a graphic EQ, Include and limits named),
and the strict reader for pasted filters (exports.parse_filters) reading the same way."""
import math

import numpy as np

from eq import engines, eqtext, exports
from helpers.checks import raises

FS = 48000
F = np.geomspace(20, 20000, 240)

# (the line after "Filter N:", and how Equalizer APO reads it from its source: its type, frequency, gain, Q or S or
# width, whether that's a slope or width (isBandwidthOrS), and whether the frequency is a shelf's corner)
CASES = [
    ("ON PK Fc 1000 Hz Gain 4 dB Q 1.4", ("PK", 1000, 4, 1.4, False, False)),
    ("ON PEQ Fc 250 Hz Gain -3 dB Q 0.8", ("PK", 250, -3, 0.8, False, False)),
    ("ON  Modal    Fc   63.00 Hz  Gain  -6.00 dB  Q  3.500  T60 target   300 ms", ("PK", 63, -6, 3.5, False, False)),
    ("ON PK Fc 3000 Hz Gain -2 dB BW Oct 1", ("PK", 3000, -2, 1, True, False)),
    ("ON PK Fc 12000 Hz Gain 5 dB BW Oct 0.5", ("PK", 12000, 5, 0.5, True, False)),
    ("ON LS Fc 100 Hz Gain 5 dB", ("LS", 100, 5, 0.9, True, False)),
    ("ON HS Fc 8000 Hz Gain -3 dB", ("HS", 8000, -3, 0.9, True, False)),
    ("ON LS Fc 120 Hz Gain 6 dB Q 0.707", ("LS", 120, 6, 0.707, False, True)),
    ("ON  HS Q     Fc   6000 Hz  Gain   4.00 dB Q  0.900", ("HS", 6000, 4, 0.9, False, True)),
    ("ON LSC Fc 105 Hz Gain 6.4 dB Q 0.7", ("LS", 105, 6.4, 0.7, False, False)),
    ("ON HSC 12 dB Fc 10000 Hz Gain -2.1 dB", ("HS", 10000, -2.1, 1.0, True, False)),
    ("ON LSC 12 dB Fc 100 Hz Gain 4 dB Q 0.7", ("LS", 100, 4, 1.0, True, False)),
    ("ON  LS 6dB   Fc   200.0 Hz  Gain   4.00 dB", ("LS", 200, 4, 0.5, True, True)),
    ("ON  HS 12dB  Fc   4000 Hz  Gain  -5.00 dB", ("HS", 4000, -5, 1.0, True, True)),
    ("ON LS12dB Fc 80 Hz Gain 3 dB", ("LS", 80, 3, 1.0, True, True)),
    ("ON PK Fc 50,0 Hz Gain -10,0 dB Q 2,5", ("PK", 50, -10, 2.5, False, False)),
    ("ON PK Fc 8.000 Hz Gain 2 dB Q 2", ("PK", 8000, 2, 2, False, False)),
]


def apo_db(kind, freq, gain, value, by_width, corner, f=F, fs=FS):
    """Equalizer APO's response for a filter as it read it (BiQuadFilter::initialize: a corner moved to the centre;
    BiQuad::BiQuad: the RBJ coefficients from Q, S or a width; BiQuad::gainAt), in dB at f."""
    a = 10 ** (gain / 40)
    at = freq
    if corner:
        s = value if by_width else 1 / ((1 / (value * value) - 2) / (a + 1 / a) + 1)
        c = 10 ** (abs(gain) / 80 / s)
        at = freq * c if kind == "LS" else freq / c
    w = 2 * math.pi * at / fs
    sn, cs = math.sin(w), math.cos(w)
    if not by_width:
        alpha = sn / (2 * value)
    elif kind in ("LS", "HS"):
        alpha = sn / 2 * math.sqrt((a + 1 / a) * (1 / value - 1) + 2)
    else:
        alpha = sn * math.sinh(math.log(2) / 2 * value * w / sn)
    beta = 2 * math.sqrt(a) * alpha
    if kind == "PK":
        b0, b1, b2, a0, a1, a2 = 1 + alpha * a, -2 * cs, 1 - alpha * a, 1 + alpha / a, -2 * cs, 1 - alpha / a
    elif kind == "LS":
        b0, b1, b2 = a * ((a + 1) - (a - 1) * cs + beta), 2 * a * ((a - 1) - (a + 1) * cs), a * ((a + 1) - (a - 1) * cs - beta)
        a0, a1, a2 = (a + 1) + (a - 1) * cs + beta, -2 * ((a - 1) + (a + 1) * cs), (a + 1) + (a - 1) * cs - beta
    else:
        b0, b1, b2 = a * ((a + 1) + (a - 1) * cs + beta), -2 * a * ((a - 1) + (a + 1) * cs), a * ((a + 1) + (a - 1) * cs - beta)
        a0, a1, a2 = (a + 1) - (a - 1) * cs + beta, 2 * ((a - 1) - (a + 1) * cs), (a + 1) - (a - 1) * cs - beta
    b0, b1, b2, a1, a2, a0 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0, 1.0
    phi = np.sin(2 * np.pi * f / fs / 2) ** 2
    return (10 * np.log10((b0 + b1 + b2) ** 2 - 4 * (b0 * b1 + 4 * b0 * b2 + b1 * b2) * phi + 16 * b0 * b2 * phi * phi)
            - 10 * np.log10((a0 + a1 + a2) ** 2 - 4 * (a0 * a1 + 4 * a0 * a2 + a1 * a2) * phi + 16 * a0 * a2 * phi * phi))


def test_every_form_draws_what_apo_plays(check):
    worst, bad = 0.0, []
    for line, apo in CASES:
        kind, flt = eqtext.filter_line(line, FS)
        if kind != "filter":
            bad.append((line, kind, flt))
            continue
        ours = engines.filter_db(flt["type"], F, flt["freq"], flt["gain"], flt["q"], FS)
        off = float(np.max(np.abs(ours - apo_db(*apo))))
        worst = max(worst, off)
        if off > 0.005:
            bad.append((line, round(off, 3), flt))
    check("eqtext: every form of a Filter line (peaks, widths in octaves, shelves with and without Q or slope, at a "
          "corner or the centre, REW's spellings, decimal commas, 8.000 Hz) draws the curve Equalizer APO plays for it, "
          f"within 0.005 dB from 20 Hz to 20 kHz ({len(CASES)} lines)", not bad, (bad, worst))


def test_lines_an_eq_here_cant_have(check):
    got = {line: eqtext.filter_line(line) for line in ("ON LP Fc 18000 Hz", "ON  HP1      Fc   25.00 Hz",
                                                       "ON  Notch    Fc   60.00 Hz", "ON  All pass  Fc   1000 Hz  Q  0.707",
                                                       "ON  None", "OFF HP Fc 30 Hz", "ON PK Fc 100 Hz Gain 3 dB",
                                                       "ON IIR Order 2 Coefficients 1 0 0 1 0 0")}
    check("eqtext: other filter types are named in plain words (REW's first-order ones as such), REW's empty slots "
          "and switched-off filters of other types are nothing, a peak without Q can't be read",
          [got[k] for k in got] == [("other", "low-pass"), ("other", "first-order high-pass"), ("other", "notch"),
                                    ("other", "all-pass"), ("none", None), ("none", None), ("bad", "no Q or width"),
                                    ("other", "IIR")], got)


REW = """Filter Settings file

Room EQ V5.31.3
Dated: Oct 26, 2026 10:02:11 AM

Notes:

Equaliser: Generic
Average 1
Filter  1: ON  PK       Fc   48.00 Hz  Gain  -7.50 dB  Q  4.200
Filter  2: ON  Modal    Fc   92.00 Hz  Gain  -3.00 dB  Q  6.100  T60 target   250 ms
Filter  3: ON  LS 12dB  Fc   150.0 Hz  Gain   3.00 dB
Filter  4: ON  HS Q     Fc   5000 Hz  Gain  -2.00 dB Q  0.800
Filter  5: ON  LP       Fc   18000 Hz
Filter  6: ON  HP1      Fc   25.00 Hz
Filter  7: ON  Notch    Fc   60.00 Hz
Filter  8: ON  All pass  Fc   1000 Hz  Q  0.707
Filter  9: ON  L-T      Fc   40.00 Hz  Q   0.90 Fp 25 Qp 0.60
Filter 10: ON  None
Filter 11: OFF PK       Fc  1000 Hz  Gain   2.00 dB  Q  1.000
Filter 12: OFF HP       Fc   30.00 Hz
"""


def test_room_eq_wizard_export(check):
    r = eqtext.read(REW)
    got = [(f["type"], f["enabled"]) for f in r["filters"]]
    shelf = r["filters"][2]
    check("eqtext: a Room EQ Wizard export: its header passed over, its peaks, Modal and shelves read (the LS 12dB "
          "moved from its corner to its centre), the switched-off peak kept off, its empty slots and a switched-off "
          "high-pass nothing, and what an EQ here can't have named in plain words",
          r["format"] == "Room EQ Wizard" and got == [("PK", True), ("PK", True), ("LSQ", True), ("HSQ", True), ("PK", False)]
          and shelf["freq"] > 150 and abs(shelf["q"] - 0.7071) < 1e-3
          and r["left_out"] == ["a low-pass filter", "a first-order high-pass filter", "a notch filter",
                                "an all-pass filter", "a Linkwitz transform filter"] and r["preamp"] is None, r)


PEACE = """[Frequencies]
Frequency1=80
Frequency2=3000
Frequency3=9000
Frequency4=500
[Gains]
Gain1=5
Gain2=-2.5
Gain3=-3
Gain4=1
[Qualities]
Quality1=0.7
Quality2=2
Quality3=0.7
Quality4=1.2
[Filters]
Filter1=14
Filter3=15
Filter4=7
[Frequencies1]
Frequency4=1000
[General]
PreAmp=-6.2
[Gains2]
Gain1=3
"""


def test_peace_preset(check):
    r = eqtext.read(PEACE)
    got = [(f["type"], f["freq"], f["gain"], f["q"]) for f in r["filters"]]
    check("eqtext: a Peace preset: its filters by number, its low and high shelves by their type codes (14, 15: what "
          "Peace writes as LSC and HSC), its pre-amp; a type it doesn't know and its other speakers' filters named",
          r["format"] == "Peace" and got == [("LSQ", 80, 5, 0.7), ("PK", 3000, -2.5, 2), ("HSQ", 9000, -3, 0.7)]
          and r["preamp"] == -6.2
          and r["left_out"] == ["a filter of Peace's type 7", "filters for some speakers only (Peace's speakers)"], r)


APO = """Preamp: -4 dB
Filter 1: ON PK Fc 200 Hz Gain 2 dB Q 1
Channel: L
Filter 2: ON PK Fc 300 Hz Gain 3 dB Q 1
Channel: all
GraphicEQ: 20 0; 1000 2; 20000 0
Include: other.txt
Filter 3: ON PK Fc 45000 Hz Gain 2 dB Q 1
Filter 4: OFF PK Fc 1000 Hz Gain -1 dB Q 2
Preamp: -0,5 dB
1000 -2 3
"""


def test_apo_lines(check):
    r = eqtext.read(APO)
    got = [(f["type"], f["freq"], f["gain"], f["q"], f["enabled"]) for f in r["filters"]]
    check("eqtext: Equalizer APO's lines: filters for every channel read (a switched-off one kept off), one-filter "
          "lines too, the pre-amps added up; the left channel's filter, a graphic EQ, Include and a filter outside the "
          "limits named",
          r["format"] == "Equalizer APO" and got == [("PK", 200, 2, 1, True), ("PK", 1000, -1, 2, False),
                                                     ("PK", 1000, -2, 3, True)]
          and r["preamp"] == -4.5
          and r["left_out"] == ["filters for some channels or devices only (Channel:, Device:)",
                                "a graphic EQ (GraphicEQ)", "another file it brings in (Include)",
                                "a filter whose frequency (45000) is outside 20 to 20000 Hz"], r)


def test_nothing_readable(check):
    r = eqtext.read("just some words\nand more: here")
    check("eqtext: text with no EQ in it reads as no filters and nothing left out (the page says what it takes)",
          r["filters"] == [] and r["left_out"] == [], r)


def test_pasted_filters_read_the_same_way(check):
    got = exports.parse_filters("Filter 1: ON  Modal    Fc   92.00 Hz  Gain  -3.00 dB  Q  6.100  T60 target   250 ms\n"
                                "Filter 2: ON LS 6dB Fc 200 Hz Gain 4 dB\nFilter 3: OFF LP Fc 18000 Hz")
    kind, apo = eqtext.filter_line("ON LS 6dB Fc 200 Hz Gain 4 dB")
    check("eqtext: pasted filters (Best fit's own, Listen's) are read the same way: REW's Modal as a peak, a shelf at "
          "its corner moved to its centre; a switched-off filter of another type skipped",
          [(f["type"], round(f["freq"], 2)) for f in got] == [("PK", 92), ("LSQ", round(apo["freq"], 2))]
          and apo["freq"] > 200, got)
    check("eqtext: the strict reader still refuses a filter type an EQ here can't have, by its name",
          "“HP” filters aren't supported" in (raises(exports.parse_filters, "Filter 1: ON HP Fc 30 Hz") or ""))
