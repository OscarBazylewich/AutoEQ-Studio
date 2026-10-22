"""The settings: their defaults, the limits and choices each one allows, and reading and saving them (data\\settings.json
and presets\\*.json). A settings dict ("cfg") always has every key of DEFAULTS, with values in range: load(),
with_auto() and clamp() make sure of that, whatever a hand edit or an old preset left in the file.

Settings are addressed by dotted paths ("site_sweep.q_max", "scoring.band_hz.1": the second item of a list): the page
binds its boxes to them (data-path), and LIMITS, CHOICES and the automatic settings use them too.
"""
import copy
import json
import math
import os
import threading
import time

from . import eq_apps
from . import layouts
from . import paths
import textfile

PATH = paths.SETTINGS_PATH
PRESET_DIR = paths.PRESET_DIR

MODES = {  # (in the method list's order: by where the EQ goes, the most used first)
    "best_fit": "Best fit",
    "site_sweep": "Website AutoEQ (find best settings)",
    "site_single": "Website AutoEQ (one run)",
}

DEFAULTS = {
    "mode": "best_fit",
    "eq_app": "",  # the EQ app or device the EQ is for (eq_apps.py); "" = not chosen yet, "other" = not listed
    "files": {"active_target": "", "excluded": []},
    "site": {"profile": "listener800", "scale_smoothing": 0.2, "smooth_level": 3, "normalization": "Hz~",
             "norm_hz": 500, "norm_db": 60, "phon_table": "ISO 226:2023", "treble_start_from": 15000,
             "sample_rate": 48000},
    "target_adjust": {"tilt": 0.0, "bass_gain": 0.0, "bass_freq": 105, "bass_q": 0.707,
                      "halftilt_gain": 0.0, "halftilt_freq": 630, "ear_gain": 0.0, "ear_freq": 3000, "ear_q": 1.0,
                      "treble_gain": 0.0, "treble_freq": 2500, "treble_q": 0.42,
                      "air_gain": 0.0, "air_freq": 10000, "air_q": 0.707},
    "scoring": {"band_hz": [20, 10000], "pick": "audible", "ear_db": 0.25,
                "priority": ["n_filters", "max_q", "max_boost"]},
    "site_single": {"rows": 8, "freq_low": 20, "freq_high": 12000, "gain_min": -12, "gain_max": 6,
                    "q_min": 0.5, "q_max": 3},
    "site_sweep": {"filter_rows": [4, 5, 6, 7, 8, 9, 10], "freq_low": 20, "freq_high": [8000, 10000, 12000, 16000],
                   "gain_ranges": [[-12, 6], [-12, 9], [-16, 16]], "q_min": 0.5, "q_max": [1, 2, 3, 4]},  # (within LIMITS)
    "best_fit": {"filter_counts": list(range(1, 11)), "freq_range": [20, 16000], "gain_min": -12,
                 "gain_max": [6, 9], "q_min": 0.5, "q_max": [1, 2, 3, 5], "low_shelf": False, "high_shelf": False,
                 "low_shelf_freq": [20, 400], "high_shelf_freq": [1000, 16000],
                 # (gain_penalty, treble_guard, high_shelf and scoring.priority: kept, not on the screens since 1.0.9:
                 # the tests never found better values)
                 "gain_penalty": 0.00005, "treble_guard": 0.02,
                 # each value is tried with every boost and Q limit (2026-10-13: the two penalties found the fewest
                 # filters for different IEMs: BENCHMARKS.md, the combined search)
                 "fight_penalty": [0.003, 0.01],
                 # your own filters to start from (text: Equalizer APO lines or "freq gain Q" lines); keep: they stay
                 # as they are and the fit adds filters on top; else the fit may adjust them too; add: off = no
                 # filters added, only yours fine-tuned (the result card's "Retry from these filters")
                 "start_filters": "", "start_keep": True, "start_add": True,
                 # what the filters are for (layouts.py): "any" (a parametric EQ), fixed bands (a graphic EQ: only the
                 # gains are fitted, within its sliders' range and step; "bands": your own frequencies and Q) or a
                 # device (its number of filters and ranges)
                 "layout": "any",
                 "bands": {"freqs": [31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000], "q": 1.41,
                           "gain_min": -12, "gain_max": 12, "step": 0.1}},
    "export": {"apo": True, "graphic": False, "preamp_rounding": "safe", "extra_headroom": 0.0, "q_decimals": 3,
               "report": True,
               # Android: Poweramp / Poweramp Equalizer (.json), USB Audio Player PRO's ToneBoosters parametric EQ (.xml)
               "poweramp": False, "uapp": False,
               # macOS: SoundSource (.txt); Windows: Voicemeeter (.xml); music players: Rockbox (.cfg); convolution EQs
               # (Viper4Android, JamesDSP, EasyEffects, Roon, foobar2000…): an impulse response (.wav) at this rate
               "soundsource": False, "voicemeeter": False, "rockbox": False, "convolution": False,
               "convolution_rate": 48000},
    "performance": {"cores": 0},
    # measurement and target from different rigs (e.g. a 711 measurement, a 5128 target): convert the target to the
    # measurement's rig when rigdata.json has that pair (rigconv.py)
    "rig_convert": {"enabled": True},
    "library": {"folders": []},  # folders the search box indexes; empty = Downloads, Documents, Desktop, Music
    "databases": {"disabled": [], "enabled": [], "extra": []},  # databases turned off / optional ones turned on / extra pages
    # past EQs (history.py): keep the saved ones or every run's; say under Measurement when it was EQ'd before
    "history": {"keep": "saved", "eqd_before": True},
    # settings fitted to the measurement and target (autoset.py); manual: settings the user changed, which keep
    # their values
    "auto": {"enabled": True, "manual": []},
}

# The settings the automatic configuration sets, per EQ method ("all": every method).
AUTO_PATHS = {
    "all": ["scoring.band_hz.1"],
    "site_single": ["site_single.rows", "site_single.freq_high", "site_single.gain_min", "site_single.gain_max",
                    "site_single.q_max"],
    "site_sweep": ["site_sweep.filter_rows", "site_sweep.freq_high", "site_sweep.gain_ranges", "site_sweep.q_max",
                   "scoring.pick", "scoring.ear_db"],
    "best_fit": ["best_fit.filter_counts", "best_fit.freq_range.1", "best_fit.gain_min", "best_fit.gain_max",
                 "best_fit.q_max", "best_fit.low_shelf", "best_fit.high_shelf", "best_fit.fight_penalty",
                 "scoring.pick", "scoring.ear_db"],
}
ALL_AUTO_PATHS = list(dict.fromkeys(p for ps in AUTO_PATHS.values() for p in ps))

# listener800: config_5128iem.js + its graphtool.js (its dB mode uses ISO 226:2023 tables). squig.link lab:
# equalizer.js TrebleStartFrom 7000, its graphtool smoothing (level 5, 0.01 scale = 0.1 here) and its default
# "dB" levelling at 60 phon with the ISO 226:2003 tables.
SITE_PROFILES = {"listener800": {"treble_start_from": 15000, "scale_smoothing": 0.2, "smooth_level": 3,
                                 "normalization": "Hz~", "norm_hz": 500, "norm_db": 60, "phon_table": "ISO 226:2023"},
                 "squig.link lab": {"treble_start_from": 7000, "scale_smoothing": 0.1, "smooth_level": 5,
                                    "normalization": "dB", "norm_hz": 500, "norm_db": 60,
                                    "phon_table": "ISO 226:2003"}}


# ---------------------------------------------------------------- limits and choices
# Floors and ceilings for every numeric setting: each one is a measured need, a hard limit of the code or file that
# uses the value, or a standard's range (the tools named below keep their data next to them in tools\, so a limit
# can be checked again). "int" rounds to whole numbers; "list" settings apply the limits to every value.
# - Frequencies: 20 Hz-20 kHz, the range every curve in the app is on (a value outside it acts on no data).
# - The website's AutoEQ (site_*): what its own code clamps its inputs to (graphtool_parts.js runAutoEQ: 20 Hz-20 kHz,
#   whole dB from -20 to +20, Q 0.1-5), and 20 filter rows, what the site's EQ panel imports.
# - Boost, cut and Q for Best fit, its fixed bands and the filter editor: what 99.9% of 3,000 real measurements
#   need to reach their rig's target over the range the app scores (tools/limits_survey.py: boost 34.4 dB, cut
#   15.5 dB, the narrowest peak or dip Q 27.0). The editor also takes every EQ app's own range (Voicemeeter's cut
#   to -36 dB), so any EQ file can be loaded. The broadest Q: a peak as wide as 20 Hz-20 kHz (10 octaves, Q 0.03).
# - Target adjustments: what 99.9% of 3,120 pairs of published targets from the same database differ by
#   (tools/target_spread.py: tilt 3.63 dB/oct, bass 10.6, ear 13.2, treble 19.3, half-tilt 19.8, air 23.6 dB).
# - Picking: the audible limit 0.05-2 dB (closer than any EQ app keeps its numbers; plainly audible)
# - Best fit's filter counts: up to 32 (filter_count_test.py, fitted with up to 40: the simplest result within 0.1 dB
#   never took more than 22, and 36-40 changed what another unit gets by 0.003 dB).
# - Penalties: 1 is where a dB of penalty costs as much as a dB of error (beyond it the fit stops correcting).
# - Phon: ISO 226's equal-loudness contours are defined from 20 to 90 phon.
# - Smoothing: strength = smooth_level x 0.1 x scale_smoothing; at 2 a third-octave peak at 3 kHz or an octave-wide
#   one at 100 Hz is already halved, so the two limits allow 2 at most (the site profiles use 0.05-0.06).
# - Saving: extra headroom up to Rockbox's +24 dB, the most any player the app writes for can boost; Q decimals up to
#   4 (a 4th decimal changes an EQ by at most 0.003 dB, a 5th by nothing measurable).
_HZ = {"min": 20, "max": 20000, "unit": "Hz"}
_HZ_INT = {**_HZ, "int": True}
_SITE_DB = {"min": -20, "max": 20, "unit": "dB", "int": True}
_SITE_Q = {"min": 0.1, "max": 5}
_Q = {"min": 0.03, "max": 27}
_CUT = {"min": -16, "max": 0, "unit": "dB"}
_BOOST = {"min": 0, "max": 35, "unit": "dB"}
_ADJ = {"tilt": 3.7, "bass": 11, "ear": 14, "treble": 20, "halftilt": 20, "air": 24}
LIMITS = {
    "target_adjust.tilt": {"min": -_ADJ["tilt"], "max": _ADJ["tilt"], "unit": "dB/oct"},
    **{f"target_adjust.{k}_gain": {"min": -_ADJ[k], "max": _ADJ[k], "unit": "dB"} for k in ("bass", "halftilt", "ear", "treble", "air")},
    **{f"target_adjust.{k}_freq": _HZ for k in ("bass", "halftilt", "ear", "treble", "air")},
    "site_single.rows": {"min": 1, "max": 20, "int": True},
    "site_single.freq_low": _HZ_INT, "site_single.freq_high": _HZ_INT,
    "site_single.gain_min": _SITE_DB, "site_single.gain_max": _SITE_DB,
    "site_single.q_min": _SITE_Q, "site_single.q_max": _SITE_Q,
    "site_sweep.filter_rows": {"min": 1, "max": 20, "int": True, "list": True},
    "site_sweep.freq_low": _HZ_INT, "site_sweep.freq_high": {**_HZ_INT, "list": True},
    "site_sweep.gain_ranges": {**_SITE_DB, "list": True},
    "site_sweep.q_min": _SITE_Q, "site_sweep.q_max": {**_SITE_Q, "list": True},
    "best_fit.filter_counts": {"min": 1, "max": 32, "int": True, "list": True},
    "best_fit.freq_range.0": _HZ, "best_fit.freq_range.1": _HZ,
    "best_fit.gain_min": _CUT, "best_fit.gain_max": {**_BOOST, "list": True},
    "best_fit.q_min": _Q, "best_fit.q_max": {**_Q, "list": True},
    "best_fit.low_shelf_freq.0": _HZ, "best_fit.low_shelf_freq.1": _HZ,
    "best_fit.high_shelf_freq.0": _HZ, "best_fit.high_shelf_freq.1": _HZ,
    "best_fit.gain_penalty": {"min": 0, "max": 1}, "best_fit.fight_penalty": {"min": 0, "max": 1, "list": True},
    "best_fit.treble_guard": {"min": 0, "max": 1},
    "best_fit.bands.freqs": {**_HZ, "list": True}, "best_fit.bands.q": _Q,
    "best_fit.bands.gain_min": _CUT, "best_fit.bands.gain_max": _BOOST,
    # the audible limit: 0.05 dB (closer than any EQ app keeps its own numbers) to 2 dB (plainly audible)
    "scoring.ear_db": {"min": 0.05, "max": 2, "unit": "dB"},
    "scoring.band_hz.0": _HZ, "scoring.band_hz.1": _HZ,
    "site.norm_hz": _HZ, "site.norm_db": {"min": 20, "max": 90, "unit": "phon"},
    "site.treble_start_from": _HZ, "site.smooth_level": {"min": 0, "max": 20}, "site.scale_smoothing": {"min": 0, "max": 1},
    "export.extra_headroom": {"min": 0, "max": 24, "unit": "dB"},
    "export.q_decimals": {"min": 1, "max": 4, "int": True},
    "performance.cores": {"min": 0, "max": os.cpu_count() or 1, "int": True},  # (0 = all but one)
}
# Pairs of "from" and "to" settings: (from, to, from must be strictly below to). The site allows equal values.
LIMIT_PAIRS = [
    ("site_single.freq_low", "site_single.freq_high", False), ("site_single.gain_min", "site_single.gain_max", False),
    ("site_single.q_min", "site_single.q_max", False), ("site_sweep.freq_low", "site_sweep.freq_high", False),
    ("site_sweep.q_min", "site_sweep.q_max", False), ("best_fit.freq_range.0", "best_fit.freq_range.1", True),
    ("best_fit.gain_min", "best_fit.gain_max", True), ("best_fit.q_min", "best_fit.q_max", True),
    ("best_fit.low_shelf_freq.0", "best_fit.low_shelf_freq.1", True),
    ("best_fit.high_shelf_freq.0", "best_fit.high_shelf_freq.1", True),
    ("best_fit.bands.gain_min", "best_fit.bands.gain_max", True), ("scoring.band_hz.0", "scoring.band_hz.1", True),
]
# What each pair is called, for the message when a run can't use it
PAIR_NAMES = {"site_single.freq_low": "Frequency range", "site_single.gain_min": "Gain range",
              "site_single.q_min": "Q range", "site_sweep.freq_low": "Frequency range", "site_sweep.q_min": "Q range",
              "best_fit.freq_range.0": "Filter frequency range", "best_fit.gain_min": "Max cut and max boost",
              "best_fit.q_min": "Q range", "best_fit.low_shelf_freq.0": "Low shelf frequencies",
              "best_fit.high_shelf_freq.0": "High shelf frequencies", "best_fit.bands.gain_min": "The sliders' range",
              "scoring.band_hz.0": "Scored range"}
# Settings with a fixed set of values (the page's dropdowns): anything else goes back to the default
CHOICES = {"mode": list(MODES), "eq_app": ["", eq_apps.OTHER, *eq_apps.APPS], "scoring.pick": ["audible", "lowest"], "site.normalization": ["Hz~", "Hz", "dB"],
           "site.phon_table": ["ISO 226:2023", "ISO 226:2003"], "site.sample_rate": [44100, 48000, 88200, 96000],
           "export.preamp_rounding": ["safe", "site"], "export.convolution_rate": [44100, 48000, 96000], "history.keep": ["saved", "all"],
           "best_fit.layout": layouts.KEYS, "best_fit.bands.step": [0.1, 0.5, 1],
           "site.profile": list(SITE_PROFILES) + ["custom"],
           "target_adjust.bass_q": [0.4, 0.5, 0.6, 0.707, 0.8], "target_adjust.ear_q": [0.4, 0.707, 1, 1.414, 2],
           "target_adjust.treble_q": [0.42, 0.5, 0.6, 0.707, 0.8], "target_adjust.air_q": [0.4, 0.707, 1, 1.414, 2]}
TEXT_LISTS = ("files.excluded", "library.folders", "databases.disabled", "databases.enabled", "databases.extra",
              "auto.manual")
PRIORITIES = ["n_filters", "max_q", "max_boost"]
# Number boxes outside the settings (the filter editor, the Listen tone, the tracer), for the same hints and checks.
# The filter editor takes what Best fit makes and every EQ app's range (Voicemeeter cuts to -36 dB). The tracer's
# axis boxes are a picture's gridline values, which can go past the audible range: up to 96 kHz (the highest a
# 192 kHz recording holds) and ±194 dB (the loudest sound air carries undistorted); the range it saves is 20 Hz-20 kHz.
UI_LIMITS = {"edit.freq": _HZ, "edit.gain": {"min": -36, "max": _BOOST["max"], "unit": "dB"},
             "edit.q": _Q, "tone.from": _HZ_INT, "tone.to": _HZ_INT,
             "trace.hz": {"min": 1, "max": 96000, "unit": "Hz"}, "trace.save": _HZ,
             "trace.db": {"min": -194, "max": 194, "unit": "dB"}}


# ---------------------------------------------------------------- dotted paths
def get_path(cfg, path):
    """The value at a dotted path ("scoring.band_hz.1"), or None when it isn't there."""
    for k in path.split("."):
        cfg = cfg[int(k)] if isinstance(cfg, list) else cfg.get(k) if isinstance(cfg, dict) else None
        if cfg is None:
            return None
    return cfg


def set_path(cfg, path, value):
    keys = path.split(".")
    for k in keys[:-1]:
        cfg = cfg[int(k)] if isinstance(cfg, list) else cfg[k]
    if isinstance(cfg, list):
        cfg[int(keys[-1])] = value
    else:
        cfg[keys[-1]] = value


# ---------------------------------------------------------------- keeping values valid
def _clamp_value(v, lim):
    v = min(max(v, lim["min"]), lim["max"])
    return int(math.floor(v + 0.5)) if lim.get("int") else v  # rounds like the page (JS Math.round)


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _conform(cfg, defaults):
    """Values of the wrong kind (a hand-edited settings.json, an old preset) go back to the default: a section that
    isn't a section, a switch that isn't on/off, text that isn't text, a list that isn't a list."""
    for k, d in defaults.items():
        v = cfg.get(k)
        if isinstance(d, dict):
            if isinstance(v, dict):
                _conform(v, d)
                continue
        elif isinstance(d, bool):
            if isinstance(v, bool):
                continue
        elif isinstance(d, str):
            if isinstance(v, str):
                continue
        elif isinstance(d, list):
            if isinstance(v, list):
                continue
        else:
            continue  # numbers: LIMITS checks them
        cfg[k] = copy.deepcopy(d)


def _clamped_limit(path, lim, v, default):
    """A LIMITS setting's value within its floor and ceiling (a list: every value; not a number: the default)."""
    if not lim.get("list"):
        return _clamp_value(v, lim) if _is_number(v) else copy.deepcopy(default)
    if path == "site_sweep.gain_ranges":  # [[from, to], …]
        ok = isinstance(v, list) and v and all(isinstance(r, list) and len(r) == 2 and all(map(_is_number, r)) for r in v)
        return [sorted(_clamp_value(x, lim) for x in r) for r in v] if ok else copy.deepcopy(default)
    ok = isinstance(v, list) and v and all(map(_is_number, v))
    return sorted({_clamp_value(x, lim) for x in v}) if ok else copy.deepcopy(default)


def clamp(cfg):
    """Keep every numeric setting within LIMITS (e.g. after hand-editing settings.json or loading an old preset).
    Values that aren't numbers or aren't one of the choices, and from/to pairs in the wrong order, go back to the
    defaults. Changes cfg and returns it."""
    cfg.pop("autoeq", None)  # (the AutoEq method's settings: Best fit's layouts replaced it)
    if isinstance(cfg.get("auto"), dict):  # (the search's level: one search since 1.0.8)
        cfg["auto"].pop("level", None)
    cfg.pop("app", None)  # (AutoEQ Local's browser and window: not used here; settings taken out in 1.0.9)
    for sec, keys in (("best_fit", ("build", "random_starts", "seed_with_site")), ("scoring", ("tolerance_db",))):
        if isinstance(cfg.get(sec), dict):
            for k in keys:
                cfg[sec].pop(k, None)
    bf = cfg.get("best_fit")
    if isinstance(bf, dict) and _is_number(bf.get("fight_penalty")):  # (one penalty before 1.0.8: a list now)
        bf["fight_penalty"] = [bf["fight_penalty"]]
    if isinstance(cfg.get("export"), dict):  # (Send to Equalizer APO's settings: the button was taken out)
        for k in ("apo_folder", "apo_on_save", "apo_enable"):
            cfg["export"].pop(k, None)
    _conform(cfg, DEFAULTS)
    for path in TEXT_LISTS:
        set_path(cfg, path, [x for x in get_path(cfg, path) if isinstance(x, str)])
    for path in LIMITS:  # from/to lists ("band_hz": [20, 10000]) have exactly two numbers
        if path.endswith(".0"):
            parent = path[:-2]
            v = get_path(cfg, parent)
            if not (isinstance(v, list) and len(v) == 2):
                set_path(cfg, parent, copy.deepcopy(get_path(DEFAULTS, parent)))
    if get_path(cfg, "best_fit.layout") in layouts.OLD_KEYS:  # (a device from before the EQ apps: now the app's)
        set_path(cfg, "best_fit.layout", layouts.OLD_KEYS[get_path(cfg, "best_fit.layout")])
    for path, options in CHOICES.items():
        v = get_path(cfg, path)
        if isinstance(v, bool) or v not in options:
            set_path(cfg, path, get_path(DEFAULTS, path))
    priority = cfg["scoring"]["priority"]
    if not (len(priority) == len(PRIORITIES) and sorted(map(str, priority)) == sorted(PRIORITIES)):
        cfg["scoring"]["priority"] = list(DEFAULTS["scoring"]["priority"])
    for path, lim in LIMITS.items():
        try:
            v = get_path(cfg, path)
            if v is None and lim.get("empty"):
                continue
            new = _clamped_limit(path, lim, v, get_path(DEFAULTS, path))
            if new != v:
                set_path(cfg, path, new)
        except (KeyError, IndexError, TypeError, ValueError):
            pass
    for lo, hi, strict in LIMIT_PAIRS:
        try:
            if pair_wrong(cfg, lo, hi, strict):
                set_path(cfg, lo, copy.deepcopy(get_path(DEFAULTS, lo)))
                set_path(cfg, hi, copy.deepcopy(get_path(DEFAULTS, hi)))
        except (KeyError, IndexError, TypeError, ValueError):
            pass
    return cfg


def pair_wrong(cfg, lo, hi, strict):
    """Is a from/to pair in the wrong order? (A list of "to" values counts by its smallest.)"""
    a, b = get_path(cfg, lo), get_path(cfg, hi)
    b = min(b) if isinstance(b, list) else b
    return a > b or (strict and a == b)


def merge(defaults, user):
    """defaults with the user's values on top, section by section."""
    out = copy.deepcopy(defaults)
    for k, v in (user or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


def with_auto(user):
    """Complete, valid settings from the user's (possibly partial) ones. Settings from before automatic settings
    existed (or an old preset): whatever differs from the defaults was chosen by the user, so it stays as a manual
    setting; the rest becomes automatic."""
    user = user if isinstance(user, dict) else {}  # (a settings file or preset holding something else entirely)
    cfg = clamp(merge(DEFAULTS, user))
    if user and "auto" not in user:
        cfg["auto"]["manual"] = [p for p in ALL_AUTO_PATHS if get_path(cfg, p) != get_path(DEFAULTS, p)]
    cfg["auto"]["manual"] = [p for p in dict.fromkeys(cfg["auto"].get("manual") or []) if p in ALL_AUTO_PATHS]
    return cfg


# ---------------------------------------------------------------- settings.json and presets
_SAVE_LOCK = threading.Lock()


def load(path=PATH):
    user = {}
    if os.path.exists(path):
        for attempt in range(40):  # (another request may be replacing it, or another program have it open: up to 2 s)
            try:
                user = json.loads(textfile.read(path))  # (any encoding: Notepad may have saved it as UTF-16)
                break
            except FileNotFoundError:
                user = {}
                break
            except ValueError:
                user = None
                if attempt >= 2:
                    break
            except OSError as e:  # (locked, e.g. by an antivirus or backup program: never taken for a broken file)
                if attempt == 39:
                    raise OSError(f"{path} can't be read right now ({e.strerror or e}): another program has it open. "
                                  "Close it, or wait a moment, and try again.") from None
            time.sleep(0.05)
        if not isinstance(user, dict):
            # unreadable (e.g. a hand edit gone wrong): kept as settings.json.bad (never over an earlier .bad), said
            # on the page, and the defaults are used
            try:
                textfile.set_aside(path)
            except OSError:
                pass
            user = {}
    return with_auto(user)


def save(cfg, path=PATH):
    with _SAVE_LOCK:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        textfile.write_atomic(path, json.dumps(cfg, indent=2))


def list_presets():
    os.makedirs(PRESET_DIR, exist_ok=True)
    return sorted(os.path.splitext(n)[0] for n in os.listdir(PRESET_DIR) if n.endswith(".json"))


def preset_path(name):
    safe = textfile.safe_name(name, "")
    if not safe:  # (".." or "...": it would have been "preset.json", over a preset really called that)
        raise ValueError("Give the preset a name.")
    return os.path.join(PRESET_DIR, safe + ".json")


def save_preset(name, cfg):
    """A preset keeps every setting except the files."""
    if not isinstance(cfg, dict):
        raise ValueError("The settings to save are missing.")
    os.makedirs(PRESET_DIR, exist_ok=True)
    s = with_auto(cfg)
    s.pop("files", None)
    textfile.write_atomic(preset_path(name), json.dumps(s, indent=2))  # (never a cut-off preset)


def load_preset(name):
    """The preset's settings with the current files, saved as the settings in use."""
    p = textfile.read_json(preset_path(name))
    if not isinstance(p, dict):
        raise ValueError(f"The preset “{name}” is missing or can't be read.")
    p["files"] = load()["files"]
    cfg = with_auto(p)
    save(cfg)
    return cfg


def delete_preset(name):
    p = preset_path(name)
    if os.path.exists(p):
        os.remove(p)
