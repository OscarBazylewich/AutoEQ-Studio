"""Saving an EQ: the pre-amp, and the file formats (Equalizer APO / squiglink text, GraphicEQ, Poweramp, USB Audio
Player PRO, SoundSource, Voicemeeter, Rockbox, a convolution impulse response) written into your Saved EQs folder
(paths.SAVED_EQS), plus the HTML
report.

A filter is {"type": "PK" | "LSQ" | "HSQ", "freq", "gain", "q", "enabled" (optional, default on)}.
"""
import json
import math
import os
import re
from xml.sax.saxutils import quoteattr

from . import eqtext
from . import paths
from . import settings
import textfile

OUTPUT_DIR = paths.OUTPUT_DIR
FORMATS = ("apo", "graphic", "poweramp", "uapp", "soundsource", "voicemeeter", "rockbox", "convolution")  # (settings "export.<format>": on or off)


TYPES = ("PK", "LSQ", "HSQ")


def clean_filters(filters):
    """Filters as sent by the page, checked: numbers as numbers (text like "100" too), a known type, on or off.
    Raises ValueError naming the filter that can't be used."""
    if not isinstance(filters, list):
        raise ValueError("The filters are missing.")
    out = []
    for i, f in enumerate(filters, 1):
        if not isinstance(f, dict):
            raise ValueError(f"Filter {i} isn't a filter.")
        g = {"type": f.get("type") or "PK", "enabled": f.get("enabled", True) is not False}
        if g["type"] not in TYPES:
            raise ValueError(f"Filter {i}: unknown type “{g['type']}” (PK, LSQ or HSQ).")
        for k, what in (("freq", "frequency"), ("gain", "gain"), ("q", "Q")):
            v = f.get(k)
            if isinstance(v, bool) or not isinstance(v, (int, float)):  # (numbers stay as they are: 105 prints as 105)
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    v = math.nan
            g[k] = v
            if not math.isfinite(g[k]):
                raise ValueError(f"Filter {i}: its {what} isn't a number.")
            lim = settings.UI_LIMITS["edit." + k]  # (the filter table's own limits: Q 0 or 0 Hz would break an EQ app)
            if not lim["min"] <= v <= lim["max"]:
                raise ValueError(f"Filter {i}: its {what} ({v:g}) is outside {lim['min']:g} to {lim['max']:g}"
                                 f"{' ' + lim['unit'] if lim.get('unit') else ''}.")
        out.append(g)
    return out


# "Filter 1: ON PK Fc 100 Hz Gain 3.0 dB Q 1.41" (Equalizer APO, Peace, squiglink, AutoEq's ParametricEQ.txt, Room
# EQ Wizard, this app's files): read as Equalizer APO plays it (eqtext.filter_line: its shelves at a corner moved to
# their centre, a slope or a width in octaves as the Q that draws the same curve)
_FILTER_LINE = re.compile(r"^\s*filter\s*\d*\s*:\s*(.*)$", re.I)
_TYPE_WORD = re.compile(r"^\s*(?:on|off)\s+([a-z]+)", re.I)


def parse_filters(text, fs=eqtext.FS):
    """Filters from text a person pastes: Equalizer APO lines, or one filter per line as "frequency gain Q" (with the
    type first if it isn't a peaking filter: "LSQ 105 4 0.7"). Pre-amp lines, comments and switched-off filters are
    skipped. Raises ValueError naming the line it can't read, or the filter outside the filter table's limits.
    (Make an EQ's "By hand" reads whole files with eqtext.read, which names what it leaves out instead.)"""
    out = []
    for i, line in enumerate(str(text or "").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith(("#", ";", "//")) or s.lower().startswith("preamp"):
            continue
        m = _FILTER_LINE.match(s)
        if m:
            kind, value = eqtext.filter_line(m[1], fs)
            if kind == "none" or (kind == "filter" and not value["enabled"]):
                continue
            if kind == "other":
                word = _TYPE_WORD.match(m[1].replace(",", "."))
                raise ValueError(f"Your filters, line {i}: Equalizer APO's “{(word[1] if word else value).upper()}” filters "
                                 f"aren't supported (peaking, low and high shelf are).")
            if kind == "bad":
                raise ValueError(f"Your filters, line {i}: can't read “{s[:60]}” ({value}). Write Equalizer APO lines "
                                 f"(Filter 1: ON PK Fc 100 Hz Gain 3 dB Q 1) or one filter per line as frequency, gain "
                                 f"and Q (100 3 1).")
            out.append({k: value[k] for k in ("type", "freq", "gain", "q")})
            continue
        f = eqtext.plain_line(s)
        if f is None:
            raise ValueError(f"Your filters, line {i}: can't read “{s[:60]}”. Write Equalizer APO lines (Filter 1: ON PK "
                             f"Fc 100 Hz Gain 3 dB Q 1) or one filter per line as frequency, gain and Q (100 3 1).")
        out.append(f)
    try:
        return clean_filters(out)
    except ValueError as e:
        raise ValueError(f"Your filters: {e}") from None


def filters_text(filters):
    """Filters as Equalizer APO lines exactly as they are (none of an app's rounding: apo_text rounds Q to the Q
    decimals setting and gains to 0.1 dB), for Best fit's own filters (Retry from these filters)."""
    num = lambda v: f"{float(v):.6f}".rstrip("0").rstrip(".")
    kind = {"PK": "PK", "LSQ": "LSC", "HSQ": "HSC"}
    return "\n".join(f"Filter {i}: {'ON' if f.get('enabled', True) else 'OFF'} {kind[f.get('type', 'PK')]} Fc {num(f['freq'])} Hz "
                     f"Gain {num(f['gain'])} dB Q {num(f['q'])}" for i, f in enumerate(filters, 1))


def clean_preamp(preamp):
    try:
        p = float(preamp)
    except (TypeError, ValueError):
        p = math.nan
    if not math.isfinite(p):
        raise ValueError("The pre-amp isn't a number.")
    return p


def preamp_value(cfg, preamp, rounding=None):
    """The pre-amp to write: the EQ's own (minus its highest boost) less any extra headroom, rounded to 0.1 dB
    ("safe": always down, so it never under-attenuates; "site": as squiglink rounds it)."""
    e = cfg["export"]
    rounding = rounding or e["preamp_rounding"]
    p = preamp - float(e.get("extra_headroom", 0) or 0)
    if rounding == "site":
        return round(p, 1) + 0.0  # squiglink's toFixed(1)
    return math.floor(p * 10 + 1e-9) / 10


# ---------------------------------------------------------------- what each app does with the filters
# The ranges each app takes (a value past one is set to its nearest end) and the precision its file holds: decimals
# for frequency, gain and Q (None: as it is; "q": the Q decimals setting). The EQ methods give whole Hz, 0.1 dB and
# Q to 0.01, which every file holds exactly except Rockbox's Q (tenths). Sources: Rockbox's source code
# (apps/menus/eq_menu.h), Voicemeeter Potato's manual (peaks -36 to +18 dB), autoeq.app's limits for Poweramp
# (Q 0.1-12) and USB Audio Player PRO (the ToneBoosters EQ's ranges).
APPS = {
    "apo": {"name": "Equalizer APO file", "digits": (2, 1, "q")},
    "soundsource": {"name": "SoundSource", "digits": (2, 1, "q")},
    "poweramp": {"name": "Poweramp", "gain": (-15, 15), "q": (0.1, 12), "digits": (0, 3, 6)},
    "uapp": {"name": "USB Audio Player PRO", "freq": (16, 20000), "gain": (-20, 20), "q": (0.1, 10),
             "digits": (None, None, None)},
    "voicemeeter": {"name": "Voicemeeter", "gain": (-36, 18), "digits": (2, 2, 2)},
    "rockbox": {"name": "Rockbox", "freq": (20, 22040), "gain": (-24, 24), "q": (0.1, 6.4), "digits": (0, 1, 1)},
}
_WHAT = {"freq": ("frequency", " Hz"), "gain": ("gain", " dB"), "q": ("Q", "")}


def for_app(app, filters, q_decimals=3):
    """The filters as the app gets them: each value within its range and at its file's precision. Returns (filters,
    the kinds of value that were past a range: "freq", "gain", "q")."""
    rule, out, past = APPS[app], [], set()
    for f in filters:
        g = dict(f)
        for k, d in zip(("freq", "gain", "q"), rule["digits"]):
            v = float(f[k])
            lo, hi = rule.get(k, (-math.inf, math.inf))
            if not lo <= v <= hi:
                v = min(max(v, lo), hi)
                past.add(k)
            d = q_decimals if d == "q" else d
            g[k] = v if d is None else round(v, d) + 0.0
            if k == "q" and d is not None and g[k] < 10 ** -d:  # (a Q under half a step isn't 0: an app can't make that)
                g[k] = 10 ** -d
        out.append(g)
    return out, [k for k in ("freq", "gain", "q") if k in past]


def note_change(app, filters, applied, past, preamp, notes):
    """Say (in notes) how much the app's ranges and precision change the EQ when it's 0.1 dB or more, and when the
    pre-amp no longer keeps it from clipping. Checked from 20 Hz to 20 kHz."""
    if notes is None:
        return
    import numpy as np
    from . import engines
    f = np.geomspace(20, 20000, 1000)
    on = [x for x in filters if x.get("enabled", True)]
    new = engines.eq_gain(f, [x for x in applied if x.get("enabled", True)], 48000)
    old = engines.eq_gain(f, on, 48000)
    d = np.abs(new - old)
    i = int(np.argmax(d)) if len(d) else 0
    name, rule = APPS[app]["name"], APPS[app]
    if len(d) and d[i] >= 0.1:
        why = "; ".join(f"its {_WHAT[k][0]} goes from {rule[k][0]:g} to {rule[k][1]:{'+g' if k == 'gain' else 'g'}}"
                        f"{_WHAT[k][1]}" for k in past) or "the precision its file holds"
        if app == "rockbox" and not past:
            why = "its Q goes in steps of 0.1"
        notes.append(f"{name}: {why}, which changes this EQ by up to {d[i]:.1f} dB (around {_fmt_hz(f[i])}).")
    # (only what the app's limits add: a pre-amp chosen too small by hand is the filter table's to show)
    clip = float(np.max(new)) + preamp - max(0.0, float(np.max(old)) + preamp) if len(new) else 0.0
    if clip > 0.05:
        notes.append(f"{name}: its limits make this EQ clip by up to {clip:.1f} dB: lower the pre-amp by that much.")


def _fmt_hz(hz):
    return f"{hz:.0f} Hz" if hz < 1000 else f"{hz / 1000:.1f} kHz"


def _num(v, digits):
    """A number with at most this many decimals, and none it doesn't need (105, 105.5)."""
    return f"{v:.{digits}f}".rstrip("0").rstrip(".") if digits else f"{v:.0f}"


def apo_text(cfg, filters, preamp, notes=None):
    """squiglink "Export" layout: readable by its Import, Equalizer APO, Peace and EasyEffects. Whole Hz unless a
    frequency has decimals (typed in the filter table)."""
    qd = int(cfg["export"].get("q_decimals", 3))
    kind = {"PK": "PK", "LSQ": "LSC", "HSQ": "HSC"}
    applied, past = for_app("apo", filters, qd)
    note_change("apo", filters, applied, past, preamp, notes)
    lines = [f"Preamp: {preamp:.1f} dB"]
    for i, f in enumerate(applied):
        on = "ON" if f.get("enabled", True) else "OFF"
        lines.append(f"Filter {i + 1}: {on} {kind[f.get('type', 'PK')]} Fc {_num(f['freq'], 2)} Hz "
                     f"Gain {f['gain']:.1f} dB Q {f['q']:.{qd}f}")
    return "\r\n".join(lines) + "\r\n"


# ---------------------------------------------------------------- Poweramp
POWERAMP_TYPES = {"LSQ": 0, "HSQ": 1, "PK": 2}  # its band types, as in its own exported presets


def poweramp_json(filters, preamp, name, notes=None):
    """A preset Poweramp and Poweramp Equalizer import (Equalizer › Presets › Import): its parametric layout, like
    the presets it exports. Its first two bands are always the bass and treble tone controls (left at 0 dB)."""
    bands = [{"type": 0, "channels": 0, "frequency": 90, "q": 0.0, "gain": 0.0, "color": 0},
             {"type": 1, "channels": 0, "frequency": 10000, "q": 0.0, "gain": 0.0, "color": 0}]
    applied, past = for_app("poweramp", filters)
    note_change("poweramp", filters, applied, past, preamp, notes)
    for f in applied:
        if f.get("enabled", True):
            bands.append({"type": POWERAMP_TYPES[f.get("type", "PK")], "channels": 0, "frequency": int(f["freq"]),
                          "q": f["q"], "gain": f["gain"], "color": 0})
    return json.dumps([{"name": name, "preamp": round(float(preamp), 2), "parametric": True, "bands": bands}], indent=1)


# ---------------------------------------------------------------- USB Audio Player PRO
# its parametric EQ (ToneBoosters): 10 bands, each stored as 6 values from 0 to 1
UAPP_BANDS, UAPP_F, UAPP_Q, UAPP_GAIN = 10, (16.0, 20000.0), (0.1, 10.0), 20.0
UAPP_BELL = "0.21428572"  # filter type "analog bell"


def uapp_xml(filters, preamp, name, notes=None):
    """A preset for UAPP's ToneBoosters parametric EQ (copy it into the TBEQPresets folder in UAPP's folder on the
    phone). Frequency and Q are stored as cube roots of their position in the range, gain as its position in
    +-20 dB. Only peaking filters, at most 10: returns None (and says why in notes) for an EQ it can't hold."""
    on = [f for f in filters if f.get("enabled", True)]
    why = ("it holds peaking filters only, and this EQ has shelves" if any(f.get("type", "PK") != "PK" for f in on)
           else f"it holds {UAPP_BANDS} filters, and this EQ has {len(on)}" if len(on) > UAPP_BANDS else "")
    if why:
        if notes is not None:
            notes.append(f"No USB Audio Player PRO file: {why}. (Best fit without shelves and at most {UAPP_BANDS} "
                         f"filters fits it.)")
        return None

    def num(v):
        return repr(round(float(v), 8))

    def position(v, lo, hi):  # 0..1 within the range
        return (min(max(float(v), lo), hi) - lo) / (hi - lo)

    applied, past = for_app("uapp", on)  # (its ranges: APPS["uapp"])
    pre = max(-UAPP_GAIN, min(UAPP_GAIN, float(preamp)))
    note_change("uapp", on, applied, past, pre, notes)
    if float(preamp) < -UAPP_GAIN:  # (as Rockbox's: said, not silently clipped)
        notes.append(f"USB Audio Player PRO: its pre-amp goes to {UAPP_GAIN:g} dB and this EQ needs {-float(preamp):.1f} "
                     "dB: it can clip.")
    on = applied
    values = []
    for i in range(UAPP_BANDS):
        if i < len(on):
            f = on[i]
            values += [num(position(f["freq"], *UAPP_F) ** (1 / 3)), num((f["gain"] + UAPP_GAIN) / (2 * UAPP_GAIN)),
                       "1", num(position(f["q"], *UAPP_Q) ** (1 / 3)), UAPP_BELL, "0"]
        else:  # an unused band: off, 16 kHz, 0 dB, Q 0.71
            values += ["0.9282573", "0.5", "0", "0.39434525", UAPP_BELL, "0"]
    values += ["0", num((pre + UAPP_GAIN) / (2 * UAPP_GAIN)), "1", "0.33333334", "0.05", "0"]  # the output (pre-amp) section
    return ('<?xml version="1.0" encoding="iso-8859-1"?>\r\n<Preset>\r\n'
            f'<PresetInfo Name={quoteattr(name)} TenBand="1">\r\n'
            + "".join(f"<Value>{v}</Value>\r\n" for v in values) + "</PresetInfo>\r\n</Preset>")


# ---------------------------------------------------------------- other apps
# Layouts as AutoEq's web app (autoeq.app) writes them for these apps.
SOUNDSOURCE_FILTERS = 32  # Rogue Amoeba: "up to 32 parametric filter settings"


def soundsource_text(cfg, filters, preamp, notes=None):
    """SoundSource (macOS): Headphone EQ › Add Other Profile…. Equalizer APO's layout, with LS/HS for the shelves.
    None for an EQ with more than 32 filters."""
    qd = int(cfg["export"].get("q_decimals", 3))
    kind = {"PK": "PK", "LSQ": "LS", "HSQ": "HS"}
    on = [f for f in filters if f.get("enabled", True)]
    if len(on) > SOUNDSOURCE_FILTERS:
        if notes is not None:
            notes.append(f"No SoundSource file: it holds {SOUNDSOURCE_FILTERS} filters, and this EQ has {len(on)}.")
        return None
    applied, past = for_app("soundsource", on, qd)
    note_change("soundsource", on, applied, past, preamp, notes)
    lines = [f"Preamp: {preamp:.2f} dB"] + [
        f"Filter {i}: ON {kind[f.get('type', 'PK')]} Fc {_num(f['freq'], 2)} Hz Gain {f['gain']:.1f} dB Q {f['q']:.{qd}f}"
        for i, f in enumerate(applied, 1)]
    return "\n".join(lines) + "\n"


VOICEMEETER_CELLS = 6  # EQ cells per channel on a Voicemeeter bus
VOICEMEETER_TYPES = {"PK": 0, "LSQ": 5, "HSQ": 6}


def voicemeeter_xml(filters, preamp, notes=None):
    """Voicemeeter (Windows): open a bus's EQ, right-click its top bar › Load EQ Settings. The same filters on all 8
    channels; unused cells are switched off. The file has no pre-amp (notes say what to set the bus to). None for
    an EQ with more filters than its cells."""
    on = [f for f in filters if f.get("enabled", True)]
    if len(on) > VOICEMEETER_CELLS:
        if notes is not None:
            notes.append(f"No Voicemeeter file: its EQ holds {VOICEMEETER_CELLS} filters, and this EQ has {len(on)}. "
                         f"(Best fit with at most {VOICEMEETER_CELLS} filters fits it.)")
        return None
    applied, past = for_app("voicemeeter", on)
    note_change("voicemeeter", on, applied, past, preamp, notes)
    if notes is not None and preamp < 0:
        notes.append(f"Voicemeeter: its EQ file has no pre-amp. Turn the bus's gain down by {-preamp:.1f} dB.")
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<VBAudioVoicemeeterBUSEQConfig>", "<VoiceMeeterBUSEQ>"]
    for channel in range(1, 9):
        for i in range(VOICEMEETER_CELLS):
            f = applied[i] if i < len(applied) else {"type": "PK", "freq": 1000, "gain": 0, "q": 1}
            lines.append(f'<Bus index="1" channel="{channel}" cell="{i + 1}" EQon="{int(i < len(on))}" '
                         f'EQtype="{VOICEMEETER_TYPES[f.get("type", "PK")]}" dblevel="{float(f["gain"]):.2f}" '
                         f'freq="{float(f["freq"]):.2f}" Q="{float(f["q"]):.2f}" />')
    return "\n".join(lines + ["</VoiceMeeterBUSEQ>", "</VBAudioVoicemeeterBUSEQConfig>"]) + "\n"


ROCKBOX_PEAKS = 8  # its EQ: a low shelf, 8 peaking filters, a high shelf
ROCKBOX_UNUSED = (64, 125, 250, 500, 1000, 2000, 4000, 8000)  # where unused peaking bands sit (at 0 dB)


def rockbox_cfg(filters, preamp, notes=None):
    """Rockbox (music players running it): copy it onto the player, then Sound Settings › Equalizer › Browse EQ
    Presets. Frequency in Hz, Q and gain in tenths; the pre-amp is its "precut" (0 to 24 dB). Its filters are the
    same maths as the app's. None for an EQ it can't hold."""
    on = [f for f in filters if f.get("enabled", True)]
    low = [f for f in on if f.get("type", "PK") == "LSQ"]
    high = [f for f in on if f.get("type", "PK") == "HSQ"]
    peaks = [f for f in on if f.get("type", "PK") == "PK"]
    why = ("it has one low shelf and one high shelf, and this EQ has more" if len(low) > 1 or len(high) > 1
           else f"it holds {ROCKBOX_PEAKS} peaking filters (and a shelf at each end), and this EQ has {len(peaks)}"
           if len(peaks) > ROCKBOX_PEAKS else "")
    if why:
        if notes is not None:
            notes.append(f"No Rockbox file: {why}. (Best fit with at most {ROCKBOX_PEAKS} filters fits it.)")
        return None
    applied, past = for_app("rockbox", on)
    precut = min(240, max(0, round(-float(preamp) * 10)))
    note_change("rockbox", on, applied, past, float(preamp), notes)
    if -float(preamp) > 24.05 and notes is not None:
        notes.append(f"Rockbox: its precut (pre-amp) goes to 24 dB and this EQ needs {-float(preamp):.1f} dB: it can clip.")
    low, high, peaks = ([f for f in applied if f.get("type", "PK") == t] for t in ("LSQ", "HSQ", "PK"))

    def band(f):
        return f"{round(float(f['freq']))}, {max(1, round(float(f['q']) * 10))}, {round(float(f['gain']) * 10)}"

    peaks += [{"freq": hz, "gain": 0, "q": 1} for hz in ROCKBOX_UNUSED[len(peaks):]]
    lines = ["eq enabled: on", f"eq precut: {precut}",
             "eq low shelf filter: " + band(low[0] if low else {"freq": 32, "gain": 0, "q": 0.7})]
    lines += [f"eq peak filter {i}: {band(f)}" for i, f in enumerate(peaks, 1)]
    lines.append("eq high shelf filter: " + band(high[0] if high else {"freq": 16000, "gain": 0, "q": 0.7}))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- convolution (an impulse response)
WAV_RATES = (44100, 48000, 96000)


def impulse_response(filters, preamp, fs, notes=None):
    """The EQ as an impulse response (the filters played on one click, pre-amp included), for convolution EQs:
    Viper4Android, JamesDSP, EasyEffects' Convolver, Roon, foobar2000, HQPlayer, Equalizer APO's Convolution.
    Exactly the filters' sound (the same maths as the graph), with no limit on their number. As long as the sound
    takes to die away (to -120 dB), at most 1.4 s. None when a filter can't be made at fs."""
    import numpy as np
    from scipy.signal import lfilter
    from . import engines
    on = [f for f in filters if f.get("enabled", True) and float(f["gain"])]
    too_high = [f for f in on if float(f["freq"]) >= 0.49 * fs]
    if too_high:
        if notes is not None:
            notes.append(f"No convolution file: a filter at {float(too_high[0]['freq']):g} Hz is too high for "
                         f"{fs} Hz (choose a higher sample rate under the result card's Save filters: Change).")
        return None
    n = 1 << (16 + (fs > 48000))  # 65,536 samples (1.4 s at 48 kHz); 131,072 at 96 kHz
    h = np.zeros(n)
    h[0] = 10 ** (float(preamp) / 20)
    for f in on:
        a1, a2, b0, b1, b2 = engines.biquad(f.get("type", "PK"), float(f["freq"]), float(f["gain"]), float(f["q"]), fs)
        h = lfilter([b0, b1, b2], [1.0, a1, a2], h)
    if not np.isfinite(h).all():
        if notes is not None:
            notes.append("No convolution file: the filters couldn't be turned into one.")
        return None
    audible = np.nonzero(np.abs(h) >= 1e-6)[0]
    length = min(n, max(4096, 1 << int(audible[-1] if len(audible) else 0).bit_length()))
    h = h[:length]
    if len(audible) and audible[-1] >= length - 1:  # still ringing at the end: fade the last 1/16 out
        k = length // 16
        h[-k:] *= np.cos(np.linspace(0, np.pi / 2, k)) ** 2
    peak = float(np.max(np.abs(h)))
    if peak > 1:  # (can't happen with the EQ's own pre-amp, but a smaller one could clip)
        h /= peak
        if notes is not None:
            notes.append(f"Convolution file: turned down {20 * math.log10(peak):.1f} dB more so it can't clip.")
    return h


def wav_bytes(h, fs):
    """A 32-bit float stereo WAV, both channels the same (the layout convolution EQs take most widely). Float:
    16 bits would round away the quiet, long tail of bass filters (0.2 dB off at 20 Hz in a test)."""
    import struct
    import numpy as np
    data = np.repeat(np.asarray(h, dtype="<f4"), 2).tobytes()
    fmt = struct.pack("<HHIIHHH", 3, 2, int(fs), int(fs) * 8, 8, 32, 0)  # IEEE float, 2 channels, 4 bytes each
    chunks = (b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"fact" + struct.pack("<II", 4, len(h))
        + b"data" + struct.pack("<I", len(data)) + data)
    return b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks


# ---------------------------------------------------------------- writing the files
SQUIGLINK_FILTERS = 20    # squiglink's EQ rows (its extraEQBandsMax); its Import drops the rest
EASYEFFECTS_FILTERS = 32  # EasyEffects' equalizer bands
NAME_MAX = 110  # characters for a file's name before " - GraphicEQ.txt" etc. (within Windows' path limit)


def file_base(name, max_len=NAME_MAX):
    """A Windows-safe file name part. When too long, the last " - " part (the method and filter count: "best fit
    10f") stays whole and the rest (device and target) is shortened at a word, marked with "…"."""
    name = textfile.safe_name(name, "EQ", max_len=10 ** 6)
    if len(name) <= max_len:
        return name
    head, sep, tail = name.rpartition(" - ")
    if not sep or len(tail) > max_len // 2:
        head, sep, tail = name, "", ""
    room = max_len - len(sep + tail) - 1
    cut = head[:room].rsplit(" ", 1)[0] if " " in head[:room] else head[:room]
    return textfile.safe_name(cut.rstrip(" -,.(") + "…" + sep + tail, "EQ", max_len=max_len)


# each format's file: the name ("File name" on the result card, or the automatic one) + its ending
ENDINGS = {"apo": " - filters.txt", "graphic": " - GraphicEQ.txt", "poweramp": " - Poweramp.json", "uapp": " - UAPP.xml",
           "soundsource": " - SoundSource.txt", "voicemeeter": " - Voicemeeter.xml", "rockbox": " - Rockbox.cfg"}


def _formats(cfg, formats):
    if not formats:
        return [k for k in FORMATS if cfg["export"].get(k)]
    wrong = [k for k in formats if k not in FORMATS] if isinstance(formats, list) else [formats]
    if wrong:
        raise ValueError(f"Unknown file format: {wrong[0]}")
    return formats


def file_names(cfg, base_name, formats=None):
    """{format: file name} that write() would write (each format's ending on the name)."""
    safe = file_base(base_name)
    rate = int(cfg["export"].get("convolution_rate", 48000))
    return {k: safe + ENDINGS[k] if k in ENDINGS else f"{safe} - convolution {rate / 1000:g} kHz.wav"
            for k in _formats(cfg, formats)}


def existing(cfg, base_name, formats=None, out_dir=OUTPUT_DIR, filters=None):
    """The files write() would replace (already in your Saved EQs folder), by name: with the filters, only the formats that
    can hold them (an app's file that can't isn't written, so there's nothing to ask about)."""
    names = file_names(cfg, base_name, formats)
    return [n for k, n in names.items() if os.path.exists(os.path.join(out_dir, n))
            and (filters is None or writable(cfg, k, filters))]


def writable(cfg, fmt, filters):
    """Can this format hold these filters? (write() leaves out the ones that can't, with a note saying why.)"""
    holds = {"uapp": lambda: uapp_xml(filters, 0.0, "x") is not None,
             "soundsource": lambda: soundsource_text(cfg, filters, 0.0) is not None,
             "voicemeeter": lambda: voicemeeter_xml(filters, 0.0) is not None,
             "rockbox": lambda: rockbox_cfg(filters, 0.0) is not None,
             "convolution": lambda: all(float(f["freq"]) < 0.49 * int(cfg["export"].get("convolution_rate", 48000))
                                        for f in filters if f.get("enabled", True) and float(f["gain"]))}
    return holds.get(fmt, lambda: True)()


def write(cfg, filters, preamp_raw, base_name, formats=None, out_dir=OUTPUT_DIR, notes=None):
    """Write the chosen formats (default: those switched on in the settings). Returns ({format: path}, pre-amp).
    notes (a list) gets what couldn't be written as it is."""
    from . import engines  # (the site's own GraphicEQ text)
    os.makedirs(out_dir, exist_ok=True)
    formats = _formats(cfg, formats)
    written = {}
    preamp = preamp_value(cfg, preamp_raw)
    safe = file_base(base_name)
    names = file_names(cfg, base_name, formats)

    def out(suffix, text, **kw):  # (in one step: Equalizer APO reloads a file it uses the moment it changes)
        p = os.path.join(out_dir, safe + suffix)
        textfile.write_atomic(p, text, **kw)
        return p

    if "apo" in formats:
        written["apo"] = out(ENDINGS["apo"], apo_text(cfg, filters, preamp, notes), encoding="utf-8", newline="")
        n = sum(1 for f in filters if f.get("enabled", True))
        if n > SQUIGLINK_FILTERS and notes is not None:
            notes.append(f"Equalizer APO file: this EQ has {n} filters. Equalizer APO and Peace take them all, but "
                         f"squiglink's Import keeps only the first {SQUIGLINK_FILTERS}"
                         + (f" and EasyEffects the first {EASYEFFECTS_FILTERS}." if n > EASYEFFECTS_FILTERS else "."))
    if "graphic" in formats:
        written["graphic"] = out(ENDINGS["graphic"], engines.graphic_eq_text(cfg, filters), encoding="utf-8")
    if "poweramp" in formats:
        written["poweramp"] = out(ENDINGS["poweramp"], poweramp_json(filters, preamp, safe, notes), encoding="utf-8", newline="")
    if "uapp" in formats:
        text = uapp_xml(filters, preamp, safe, notes)
        if text is not None:
            written["uapp"] = out(ENDINGS["uapp"], text, encoding="iso-8859-1", errors="xmlcharrefreplace", newline="")
    if "soundsource" in formats:
        text = soundsource_text(cfg, filters, preamp, notes)
        if text is not None:
            written["soundsource"] = out(ENDINGS["soundsource"], text, encoding="utf-8", newline="")
    if "voicemeeter" in formats:
        text = voicemeeter_xml(filters, preamp, notes)
        if text is not None:
            written["voicemeeter"] = out(ENDINGS["voicemeeter"], text, encoding="utf-8", newline="")
    if "rockbox" in formats:
        text = rockbox_cfg(filters, preamp, notes)
        if text is not None:
            written["rockbox"] = out(ENDINGS["rockbox"], text, encoding="ascii", newline="")
    if "convolution" in formats:
        fs = int(cfg["export"].get("convolution_rate", 48000))
        h = impulse_response(filters, preamp, fs, notes)
        if h is not None:
            p = os.path.join(out_dir, names["convolution"])
            textfile.write_atomic(p, wav_bytes(h, fs))
            written["convolution"] = p
    return written, preamp


def report_name(device, target_name, name=""):
    """The report's file name: your own name (the result card's File name), else "<device> to <target>"; kept short
    and valid like the EQ files (two long names together could pass Windows' path limit)."""
    return file_base(name or f"{device} to {target_name}") + " - report.html"


def write_report(curves, band, device, target_name, n_files, cards, grids=(), out_dir=OUTPUT_DIR, name=""):
    """The HTML report for a measurement and target (report.py): "<device> to <target> - report.html", or your own
    name (the result card's File name) + " - report.html". Returns its path."""
    from . import engines
    from . import report
    no_eq = engines.rms_error(curves["f"], curves["meas"], curves["target"], band)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, report_name(device, target_name, name))
    report.write(path, title=f"{device} → {target_name}",
                 subtitle=f"{n_files} measurement file{'s' if n_files > 1 else ''} averaged like squiglink · "
                          f"errors are RMS over {band[0]}–{band[1]} Hz · without EQ: {no_eq:.2f} dB",
                 curves=curves, band=band, cards=cards, grids=grids)
    return path
