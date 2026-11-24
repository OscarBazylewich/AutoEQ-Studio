"""Best fit's filter layouts (best_fit.layout): what kind of EQ the filters are for.

"any": a parametric EQ that takes any filters (Equalizer APO…): Best fit places them freely.
Fixed bands (a graphic EQ): the bands' frequencies and Q are set, only their gains are fitted (engines.graphic_run),
  within the sliders' range and in their steps (best_fit.bands: gain_min, gain_max, step; "bands": your own
  frequencies and Q too).
The EQ apps (eq_apps.py, the "Your EQ app" choice) add their own: "app:<key>", fixed bands for a graphic EQ (its
sliders' stated range and steps kept: sliders()) or, for an app with a set number of filters and ranges, a device:
Best fit's own settings are kept within them (device_settings(); its "bands" are peaking filters and shelves
together). The shared fixed layouts are eq_apps.BAND_LAYOUTS.

What the user sets per EQ app (settings best_fit.per_app.<key>, described by eq_apps.user_items) is read here
only, through own(bf): device(bf) is a device with the user's numbers (Peace: its bands and its ± gain), and
counts_to_try(bf) the band counts of a graphic EQ app that offers several (FxSound: COUNTS). DEVICES and FIXED
hold the apps' own values and never change."""
import copy
import math

from . import eq_apps

FIXED = {k: (n, list(f), q) for k, (n, f, q) in eq_apps.BAND_LAYOUTS.items()}  # key: (name, centres, each band's Q)
OWN_BANDS = "bands"  # your own frequencies and Q (best_fit.bands.freqs, .q)

# Devices: key: name, peaking filters ("peaks"; or "bands": peaking filters and shelves together), a low and a high
# shelf or not, gain, Q, filter frequencies. They're the EQ apps' (eq_apps.py), with the limits their makers state.
DEVICES = {}
SLIDERS = {}  # a graphic EQ app's stated sliders: {"gain": (lowest, highest), "step"}
# A graphic EQ app that offers more than one band count (eq_apps "band_sets"): key: {count: (centres, each band's Q)},
# and the count it starts with. FIXED has its default set, so a caller that knows nothing of counts gets that one.
COUNTS = {}
DEFAULT_COUNT = {}
# The devices this list had before the EQ apps (AutoEq's presets): a saved layout with one of these keys is the app's now
OLD_KEYS = {k: "app:" + k for k in ("qudelix_5k", "poweramp", "uapp", "neutron", "minidsp_2x4hd", "minidsp_il_dsp",
                                     "moondrop_free_dsp", "aunbandeq")}
# the EQ apps' own layouts
for _k, _a in eq_apps.APPS.items():
    if eq_apps.layout_key(_k) != "app:" + _k:
        continue
    if _a["kind"] == "graphic":
        _sets = eq_apps.band_sets(_k)
        if _sets:
            COUNTS["app:" + _k], DEFAULT_COUNT["app:" + _k] = _sets, _a["band_default"]
        _freqs, _q = _sets[_a["band_default"]] if _sets else (_a["freqs"], _a["q"])
        FIXED["app:" + _k] = (_a["name"], list(_freqs), _q)
        SLIDERS["app:" + _k] = {f: _a[f] for f in ("gain", "step") if f in _a}
    else:
        DEVICES["app:" + _k] = {"name": _a["name"], **{f: _a[f] for f in ("bands", "peaks", "shelves", "gain", "q", "freq") if f in _a}}
        if "bands" in DEVICES["app:" + _k]:
            DEVICES["app:" + _k]["shelves"] = True
        if not any(f in _a for f in ("bands", "peaks")):
            DEVICES["app:" + _k]["open"] = True  # (no stated count: as many as the filter counts allow)
        DEVICES["app:" + _k].setdefault("peaks", DEVICES["app:" + _k].get("bands", 32))
        DEVICES["app:" + _k].setdefault("shelves", True)
APP_KEYS = [k for k in (*FIXED, *DEVICES) if k.startswith("app:")]
KEYS = ["any", *[k for k in FIXED if k not in APP_KEYS], OWN_BANDS, *APP_KEYS]  # (every device is an EQ app's)


def is_fixed(key):
    return key in FIXED or key == OWN_BANDS


def name(key):
    return "Parametric filters" if key == "any" else "Your bands" if key == OWN_BANDS else (
        FIXED[key][0] if key in FIXED else DEVICES[key]["name"] if key in DEVICES else key)


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def own(bf):
    """What the user set for the EQ app of the layout: {item name: value}, the defaults of the app's items
    (eq_apps.user_items) with best_fit.per_app[<key>] on top; {} for a layout that is not an app's or whose app has
    no items. The one place that reads best_fit.per_app: settings from before it (no key) give the defaults, which
    are the app's own limits, and a value of another app is never used."""
    lay = bf.get("layout") or ""
    key = lay[4:] if lay.startswith("app:") else ""
    out = copy.deepcopy(eq_apps.user_defaults().get(key, {}))
    per = bf.get("per_app")
    mine = per.get(key) if isinstance(per, dict) else None
    if isinstance(mine, dict):
        out.update({k: copy.deepcopy(v) for k, v in mine.items() if k in out})
    return out


def device(bf):
    """The device of the layout with what the user set for its app on top (a copy: DEVICES keeps the app's own), or
    None for other layouts. "bands": that many peaking filters and shelves together, within 1 and the app's own
    number; "gain": a ± value. A value that is not a usable number (settings that were not checked) leaves the
    app's own."""
    d = DEVICES.get(bf.get("layout"))
    if d is None:
        return None
    d, mine = dict(d), own(bf)
    n, g = mine.get("bands"), mine.get("gain")
    if "bands" in d and _is_number(n):
        d["bands"] = d["peaks"] = int(min(max(math.floor(n + 0.5), 1), d["bands"]))
    if _is_number(g) and g > 0:
        d["gain"] = (-g, g)
    return d


def counts(key):
    """The band counts a layout offers, in rising order ([] for a layout with one set of bands)."""
    return sorted(COUNTS.get(key, {}))


def counts_path(key):
    """The setting that holds the band counts to try of a layout with counts."""
    return f"best_fit.per_app.{key[4:]}.{eq_apps.BAND_COUNTS}"


def counts_to_try(bf):
    """The band counts a run fits, in rising order: the stored ones that the layout offers, else the count the app
    starts with (never none: a count of another app or of a hand-edited file is not used). [] for a layout without
    counts."""
    lay = bf.get("layout")
    if lay not in COUNTS:
        return []
    stored = own(bf).get(eq_apps.BAND_COUNTS)
    stored = stored if isinstance(stored, list) else []
    return sorted({int(n) for n in stored if _is_number(n) and n in COUNTS[lay]}) or [DEFAULT_COUNT[lay]]


def listed(values, word):
    """Numbers in words: "5", "10 and 31", "5, 10, 15, 20, and 31" (word: "and" or "or")."""
    v = [f"{x:g}" for x in values]
    return v[0] if len(v) == 1 else f"{v[0]} {word} {v[1]}" if len(v) == 2 else ", ".join(v[:-1]) + f", {word} {v[-1]}"


def bands(bf, n=None):
    """(centre frequencies, Q) of a fixed-band layout; n: of that band count, for a layout with counts (without n:
    its default set)."""
    if n is not None and bf["layout"] in COUNTS:
        freqs, q = COUNTS[bf["layout"]][n]
        return list(freqs), q
    if bf["layout"] in FIXED:
        return list(FIXED[bf["layout"]][1]), FIXED[bf["layout"]][2]
    return sorted(set(float(x) for x in bf["bands"]["freqs"])), float(bf["bands"]["q"])


def sliders(bf):
    """(lowest, highest, step) of a fixed-band layout's sliders: best_fit.bands', kept within a graphic EQ app's stated
    range and in its steps (as device_settings keeps a parametric app's: a range left from another app, or set in
    Advanced, can't go past what the app's sliders do)."""
    from . import settings  # (it imports this module)
    b, own = bf["bands"], SLIDERS.get(bf["layout"], {})
    lo, hi = own.get("gain", (-math.inf, math.inf))
    lo = max(float(b["gain_min"]), lo, settings.LIMITS["best_fit.bands.gain_min"]["min"])
    hi = min(float(b["gain_max"]), hi, settings.LIMITS["best_fit.bands.gain_max"]["max"])
    return lo, hi, float(own.get("step", b["step"]))


def capacity(bf):
    """How many filters a device holds (its peaking filters and shelves), or None for other layouts. bf: Best fit's
    settings (with what the user set for the app: Peace's bands), or a layout key (the app's own number)."""
    d = DEVICES.get(bf) if isinstance(bf, str) else device(bf)
    if not d or d.get("open"):
        return None
    return d["bands"] if "bands" in d else d["peaks"] + (2 if d["shelves"] else 0)


def device_settings(bf, n_mine=0):
    """Best fit's settings kept within a device's: at most its peaking filters less your own (kept or adjusted,
    they're in the result), shelves only if it has them, gains, Q and frequencies within its ranges (a range of yours
    outside the device's: the device's own). Other layouts: as they are."""
    d = device(bf)  # (with what the user set for its app: Peace's bands and gain)
    if not d:
        return bf
    bf = copy.deepcopy(bf)
    if not d["shelves"]:
        bf["low_shelf"] = bf["high_shelf"] = False
    # (an app's "bands" hold its shelves too: the shelves in use take bands from the peaking filters)
    used = lambda: (bool(bf.get("low_shelf")) + bool(bf.get("high_shelf"))) if "bands" in d else 0
    room = lambda: (d["bands"] - used() if "bands" in d else d["peaks"]) - n_mine
    if room() < 1 and used():  # (your filters fill it: the shelves go first)
        bf["low_shelf"] = bf["high_shelf"] = False
    if room() < 1:  # (still full: nothing is added, your filters only)
        bf["start_add"] = False
    bf["filter_counts"] = sorted({min(n, max(1, room())) for n in bf["filter_counts"]})
    if "gain" in d:
        lo, hi = d["gain"]
        bf["gain_min"] = max(bf["gain_min"], lo)
        bf["gain_max"] = sorted({min(max(g, 0.5), hi) for g in bf["gain_max"]})
    if "q" in d:
        lo, hi = d["q"]
        bf["q_min"] = min(max(bf["q_min"], lo), hi)
        if bf["q_min"] >= hi:  # (your Q from at or past the device's top: from its bottom, so there's a range)
            bf["q_min"] = lo
        # (a Q max equal to Q from leaves the fit no range at all: every start failed, an EQ with no filters)
        bf["q_max"] = sorted({min(max(q, bf["q_min"]), hi) for q in bf["q_max"]} - {bf["q_min"]}) or [hi]
    if "freq" in d:
        lo, hi = d["freq"]
        bf["freq_range"] = [max(bf["freq_range"][0], lo), min(bf["freq_range"][1], hi)]
        if bf["freq_range"][0] >= bf["freq_range"][1]:  # (yours outside the device's: the device's own)
            bf["freq_range"] = [max(lo, 20), min(hi, 20000)]
    return bf


def summary(key, bf=None):
    """A line on what the layout holds (the page shows it under the layout). bf: Best fit's settings; when their
    layout is this one, a device's numbers are those in use (device(bf): what the user set for the app)."""
    if key == "any":
        return "Filters at all frequencies, with the filter counts that you set: for EQ apps with no limits on the filters."
    if key in COUNTS:  # (each count has its own ends and Q: only the counts are said)
        return f"{listed(counts(key), 'or')} bands: Best fit adjusts only their gains."
    if key in FIXED:
        f, q = FIXED[key][1], FIXED[key][2]
        return f"{len(f)} bands, {_hz(f[0])} to {_hz(f[-1])}, Q {q:g}: Best fit adjusts only their gains."
    if key == OWN_BANDS:
        return "The frequencies and Q that you set: Best fit adjusts only their gains."
    d = device(bf) if bf and bf.get("layout") == key else DEVICES[key]
    parts = (["unlimited filters"] if d.get("open") else
             [f"up to {d['bands']} peaking/shelf filters"] if "bands" in d else
             [f"up to {d['peaks']} peaking filters" + (" + low/high shelves" if d["shelves"] else "")])
    if "gain" in d:
        parts.append(f"gain {d['gain'][0]:+g} to {d['gain'][1]:+g} dB")
    if "q" in d:
        parts.append(f"Q {d['q'][0]:g} to {d['q'][1]:g}")
    if "freq" in d:
        parts.append(f"frequency {_hz(d['freq'][0])} to {_hz(d['freq'][1])}")
    return f"{d['name']} limits: " + ", ".join(parts)


def _hz(v):
    return f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"


def listing():
    """For the page: [{key, name, group, summary, fixed, shelves, counts}] in the layout list's order (counts: the
    band counts the layout offers, [] for most)."""
    group = lambda k: "Any" if k == "any" else "EQ apps (Your EQ app)" if k.startswith("app:") else "Graphic EQ"
    return [{"key": k, "name": name(k), "group": group(k), "summary": summary(k), "fixed": is_fixed(k),
             "shelves": DEVICES[k]["shelves"] if k in DEVICES else not is_fixed(k), "counts": counts(k)}
            for k in KEYS]
