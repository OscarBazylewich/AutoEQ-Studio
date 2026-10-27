"""Reading EQ text made elsewhere, as Equalizer APO plays it: its config lines (AutoEq's ParametricEQ.txt, squig.link's
export, Equalizer APO's Editor, Peace's peace.txt), Room EQ Wizard's filter export ("Export filter settings as text")
and Peace's own presets (.peace). Make an EQ's "By hand" starts from them; the filters you paste or load elsewhere
(Best fit's own filters, Listen's EQs to compare) are read by filter_line too (exports.parse_filters).

The app's EQs have peaking filters and shelves ("PK", "LSQ", "HSQ": a shelf's frequency is its centre, its steepness a
Q, as Equalizer APO's "LSC … Q" plays it). A line in another form is turned into that exactly, by Equalizer APO's own
rules (read from its source, filters/BiQuadFilterFactory.cpp and BiQuadFilter.cpp, 2026-10-26):
- every comma in a Filter line is a decimal point ("Fc 50,0 Hz"), and a frequency written like "8.000" is 8000 Hz
  (APO takes the dot for a thousands separator, "because of Room EQ Wizard");
- "LS"/"HS" with a Q or a slope ("LS 6dB", "HS 12dB", "LS … Q 0.7") is a shelf at its corner frequency: APO moves it
  to its centre by 10^(|gain| / 80 / S); "LSC"/"HSC" and a shelf with neither are at their centre;
- a slope of N dB is a steepness S = N / 12 (S = 1: Q 0.707), and a shelf with neither Q nor slope has S = 0.9; a
  steepness becomes the Q that draws the same curve at that gain: 1 / √((A + 1/A)(1/S − 1) + 2), A = 10^(gain / 40);
- a peaking filter's width in octaves ("BW Oct 1") is the Q of the same filter at the sample rate (APO's own formula
  depends on it: 48 kHz unless said);
- "PEQ" and REW's "Modal" are peaking filters; "None" (REW's empty slots) is nothing.
What it can't hold is left out and named, never dropped without a word: other filter types (high- and low-pass, notch,
all-pass, band-pass, REW's first-order and Linkwitz filters), a graphic EQ, a convolution, Include, Copy, Delay,
conditions and plug-ins, and filters for some channels or devices only. Lines that aren't Equalizer APO's (REW's
header, notes) are passed over.
"""
import math
import re

import apoline

from . import settings

FS = 48000  # (the sample rate a width in octaves is read at, when none is given)

# APO's own commands ("Command: …"), named as they're left out; any other "Word:" (REW's "Dated:", "Notes:") is passed
# over. Filter, Preamp, Channel and Device are read.
COMMANDS = {"graphiceq": "a graphic EQ (GraphicEQ)", "convolution": "a convolution (impulse response)",
            "include": "another file it brings in (Include)", "copy": "a channel copy (Copy)", "delay": "a delay (Delay)",
            "stage": "a processing stage (Stage)", "if": "conditions (If, Eval)", "elseif": "conditions (If, Eval)",
            "else": "conditions (If, Eval)", "endif": "conditions (If, Eval)", "eval": "conditions (If, Eval)",
            "vstplugin": "a VST plug-in (VSTPlugin)"}

_CMD = re.compile(r"^\s*([A-Za-z]+)(?:\s*\d+)?\s*:\s*(.*)$")
_PREAMP = re.compile(r"^\s*([-+0-9.eE]+)\s*dB", re.I)
_PLAIN_TYPES = {"PK": "PK", "PEQ": "PK", "LSQ": "LSQ", "LSC": "LSQ", "LS": "LSQ", "HSQ": "HSQ", "HSC": "HSQ", "HS": "HSQ"}


def _number(text):
    return apoline.number(text)


def filter_line(params, fs=FS):
    """One "Filter:" line's text after the colon ("ON PK Fc 100 Hz Gain 3 dB Q 1"), read as Equalizer APO reads it
    (apoline.parse): ("filter", {"type", "freq", "gain", "q", "enabled"}) in the app's terms; ("none", None) for REW's
    empty slot; ("other", what) for a type the app's EQs can't have (its plain name: "high-pass", ...); ("bad", why)."""
    kind, b = apoline.parse(params)
    if kind != "biquad":
        return kind, b
    if b["kind"] not in ("PK", "LS", "HS"):
        return "other", apoline.NAMES[b["kind"]]
    freq, gain, on, value = b["freq"], b["gain"], b["on"], b["value"]
    if b["kind"] == "PK":
        if b["by_width"]:  # (a width in octaves: the Q of the same filter at this sample rate, as APO works it out)
            w = 2 * math.pi * freq / fs
            if not 0 < w < math.pi:
                return "bad", "its frequency is above what the sample rate can hold"
            sn = math.sin(w)
            value = sn / (2 * sn * math.sinh(math.log(2) / 2 * value * w / sn))
        return "filter", {"type": "PK", "freq": freq, "gain": gain, "q": value, "enabled": on}
    # a shelf: the Q that draws the same curve at its gain, at its centre (a corner moved there)
    a = 10 ** (gain / 40)
    if b["by_width"]:
        inside = (a + 1 / a) * (1 / value - 1) + 2
        if inside <= 0:
            return "bad", "a slope too steep for its gain"
        q = 1 / math.sqrt(inside)
    else:
        q = value
        if b["corner"] and apoline.shelf_s(b) <= 0:
            return "bad", "a Q too large for a shelf"
    return "filter", {"type": "LSQ" if b["kind"] == "LS" else "HSQ", "freq": apoline.centre(b), "gain": gain, "q": q,
                      "enabled": on}


def plain_line(s):
    """One filter as "frequency gain Q", or with its type first ("LSQ 105 4 0.7"): {"type", "freq", "gain", "q"}, or
    None when the line isn't one."""
    words = [w for w in re.split(r"[\s,;]+", s.strip()) if w]  # (commas part the numbers here, as typed in a list)
    kind = _PLAIN_TYPES.get(words[0].upper()) if words else None
    nums = words[1:] if kind else words
    if len(nums) != 3:
        return None
    vals = [_number(w) for w in nums]
    if any(v is None for v in vals):
        return None
    return {"type": kind or "PK", "freq": vals[0], "gain": vals[1], "q": vals[2]}


def outside_limits(f):
    """Why a filter can't be in the app's EQs (its value outside the filter table's limits), or ""."""
    for key, what in (("freq", "frequency"), ("gain", "gain"), ("q", "Q")):
        lim = settings.UI_LIMITS["edit." + key]
        if not lim["min"] <= f[key] <= lim["max"]:
            unit = f" {lim['unit']}" if lim.get("unit") else ""
            return f"its {what} ({round(f[key], 3):g}) is outside {lim['min']:g} to {lim['max']:g}{unit}"
    return ""


def _tidy(f):
    """Numbers kept to what matters (a shelf moved to its centre has a long tail of digits)."""
    out = dict(f)
    out["freq"] = round(out["freq"], 2)
    out["gain"] = round(out["gain"], 2)
    out["q"] = round(out["q"], 4)
    if out["freq"] == int(out["freq"]):
        out["freq"] = int(out["freq"])
    return out


def _say_left(counts):
    """{reason: how many} as plain words: "2 high-pass filters", "a graphic EQ (GraphicEQ)"."""
    said = []
    for what, n in counts.items():
        if what.endswith(" filter"):
            one = "an" if what[0].lower() in "aeiou" else "a"
            said.append(f"{one} {what}" if n == 1 else f"{n} {what}s")
        else:
            said.append(what if n == 1 else f"{what} ×{n}")
    return said


def read(text, fs=FS):
    """An EQ file's or pasted text's EQ: {"filters": [{"type", "freq", "gain", "q", "enabled"}], "preamp": its own
    pre-amp in dB (None when it has none), "left_out": [what it has that the app's EQs can't, in plain words],
    "format": "Peace", "Room EQ Wizard" or "Equalizer APO"}. Never raises for a line it can't use: it's left out
    (named) or passed over (a line that isn't Equalizer APO's)."""
    text = str(text or "")
    if re.search(r"^\s*\[(frequencies|gains|qualities)\]\s*$", text, re.I | re.M):
        return _peace(text)
    fmt = "Room EQ Wizard" if re.search(r"room\s*eq|filter settings file", text, re.I) else "Equalizer APO"
    filters, preamp, left = [], None, {}
    scope_all = {"channel": True, "device": True}

    def leave(why):
        left[why] = left.get(why, 0) + 1

    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", ";", "//")):
            continue
        m = _CMD.match(s)
        if m:
            cmd, rest = m[1].lower(), m[2]
            if cmd in ("channel", "device"):
                scope_all[cmd] = rest.strip().lower() in ("all", "")
                continue
            if cmd not in ("filter", "preamp") and cmd not in COMMANDS:
                continue  # (not one of APO's: REW's header, a note)
            if not all(scope_all.values()):
                leave("filters for some channels or devices only (Channel:, Device:)")
                continue
            if cmd == "preamp":
                v = _PREAMP.match(rest.replace(",", "."))
                if v and _number(v[1]) is not None:
                    preamp = (preamp or 0.0) + _number(v[1])
                continue
            if cmd in COMMANDS:
                leave(COMMANDS[cmd])
                continue
            kind, value = filter_line(rest, fs)
            if kind == "filter":
                why = outside_limits(value)
                if why:
                    leave(f"a filter whose {why[4:]}" if why.startswith("its ") else why)
                else:
                    filters.append(_tidy(value))
            elif kind == "other":
                leave(f"{value} filter")
            elif kind == "bad":
                leave(f"a filter line it can't read ({value})")
            continue
        f = plain_line(s)
        if f is not None:
            why = outside_limits(f)
            if why:
                leave(f"a filter whose {why[4:]}")
            else:
                filters.append(dict(_tidy(f), enabled=True))
    return {"filters": filters, "preamp": None if preamp is None else round(preamp, 2), "left_out": _say_left(left),
            "format": fmt}


# ---------------------------------------------------------------- Peace's presets (.peace)
_PEACE_TYPES = {None: "PK", "14": "LSQ", "15": "HSQ"}  # (what Peace writes for them: PK, "LSC … Q", "HSC … Q")


def _peace(text):
    """A Peace preset: [Frequencies] FrequencyN, [Gains] GainN, [Qualities] QualityN, [Filters] FilterN (its type's
    code, for those that aren't peaking: 14 a low shelf, 15 a high shelf), [General] PreAmp. Numbered sections
    ([Gains1] …) are Peace's other speakers: filters there with a gain are left out (named)."""
    sections, cur = {}, None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            cur = s[1:-1].strip().lower()
            sections.setdefault(cur, {})
        elif cur is not None and "=" in s:
            k, v = s.split("=", 1)
            sections[cur][k.strip().lower()] = v.strip()
    num = lambda v: _number(str(v).replace(",", "."))
    freqs, gains = sections.get("frequencies", {}), sections.get("gains", {})
    qs, kinds = sections.get("qualities", {}), sections.get("filters", {})
    filters, left = [], {}
    order = sorted(int(k[9:]) for k in freqs if k.startswith("frequency") and k[9:].isdigit())
    for n in order:
        f, g, q = num(freqs.get(f"frequency{n}")), num(gains.get(f"gain{n}", 0)), num(qs.get(f"quality{n}"))
        code = kinds.get(f"filter{n}")
        kind = _PEACE_TYPES.get(code)
        if kind is None:
            left[f"a filter of Peace's type {code}"] = left.get(f"a filter of Peace's type {code}", 0) + 1
            continue
        if f is None or g is None or q is None or q <= 0:
            left["a filter line it can't read (a number missing)"] = left.get("a filter line it can't read (a number missing)", 0) + 1
            continue
        flt = {"type": kind, "freq": f, "gain": g, "q": q, "enabled": True}
        why = outside_limits(flt)
        if why:
            left[f"a filter whose {why[4:]}"] = left.get(f"a filter whose {why[4:]}", 0) + 1
        else:
            filters.append(_tidy(flt))
    others = [s for s in sections if re.fullmatch(r"gains\d+", s)
              and any((num(v) or 0) != 0 for v in sections[s].values())]
    if others:
        left["filters for some speakers only (Peace's speakers)"] = len(others)
    pre = num(sections.get("general", {}).get("preamp")) if sections.get("general", {}).get("preamp") is not None else None
    return {"filters": filters, "preamp": pre, "left_out": _say_left(left), "format": "Peace"}
