"""Best fit's filter layouts (best_fit.layout): what kind of EQ the filters are for.

"any": a parametric EQ that takes any filters (Equalizer APO, Peace…): Best fit places them freely.
Fixed bands (a graphic EQ): the bands' frequencies and Q are set, only their gains are fitted (engines.graphic_run),
  within the sliders' range and in their steps (best_fit.bands: gain_min, gain_max, step; "bands": your own
  frequencies and Q too).
The EQ apps (eq_apps.py, the "Your EQ app" choice) add their own: "app:<key>", fixed bands for a graphic EQ (its
sliders' stated range and steps kept: sliders()) or, for an app with a set number of filters and ranges, a device:
Best fit's own settings are kept within them (device_settings(); its "bands" are peaking filters and shelves
together). The shared fixed layouts are eq_apps.BAND_LAYOUTS."""
import copy
import math

from . import eq_apps

FIXED = {k: (n, list(f), q) for k, (n, f, q) in eq_apps.BAND_LAYOUTS.items()}  # key: (name, centres, each band's Q)
OWN_BANDS = "bands"  # your own frequencies and Q (best_fit.bands.freqs, .q)

# Devices: key: name, peaking filters ("peaks"; or "bands": peaking filters and shelves together), a low and a high
# shelf or not, gain, Q, filter frequencies. They're the EQ apps' (eq_apps.py), with the limits their makers state.
DEVICES = {}
SLIDERS = {}  # a graphic EQ app's stated sliders: {"gain": (lowest, highest), "step"}
# The devices this list had before the EQ apps (AutoEq's presets): a saved layout with one of these keys is the app's now
OLD_KEYS = {k: "app:" + k for k in ("qudelix_5k", "poweramp", "uapp", "neutron", "minidsp_2x4hd", "minidsp_il_dsp",
                                     "moondrop_free_dsp", "aunbandeq")}
# the EQ apps' own layouts
for _k, _a in eq_apps.APPS.items():
    if eq_apps.layout_key(_k) != "app:" + _k:
        continue
    if _a["kind"] == "graphic":
        FIXED["app:" + _k] = (_a["name"], list(_a["freqs"]), _a["q"])
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
    return "Any filters" if key == "any" else "Your own bands" if key == OWN_BANDS else (
        FIXED[key][0] if key in FIXED else DEVICES[key]["name"] if key in DEVICES else key)


def bands(bf):
    """(centre frequencies, Q) of a fixed-band layout."""
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


def capacity(key):
    """How many filters a device holds (its peaking filters and shelves), or None for other layouts."""
    d = DEVICES.get(key)
    if not d or d.get("open"):
        return None
    return d["bands"] if "bands" in d else d["peaks"] + (2 if d["shelves"] else 0)


def device_settings(bf, n_mine=0):
    """Best fit's settings kept within a device's: at most its peaking filters less your own (kept or adjusted,
    they're in the result), shelves only if it has them, gains, Q and frequencies within its ranges (a range of yours
    outside the device's: the device's own). Other layouts: as they are."""
    d = DEVICES.get(bf.get("layout"))
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


def summary(key):
    """A line on what the layout holds (the page shows it under the layout)."""
    if key == "any":
        return "Filters anywhere, as many as the counts below: for EQ apps that take any filters."
    if key in FIXED:
        f, q = FIXED[key][1], FIXED[key][2]
        return f"{len(f)} bands, {_hz(f[0])} to {_hz(f[-1])}, Q {q:g}: only their gains are fitted."
    if key == OWN_BANDS:
        return "The frequencies and Q below: only their gains are fitted."
    d = DEVICES[key]
    parts = (["any number of filters"] if d.get("open") else
             [f"up to {d['bands']} filters (peaking or shelves)"] if "bands" in d else
             [f"up to {d['peaks']} peaking filters" + (" plus a low and a high shelf" if d["shelves"] else "")])
    if "gain" in d:
        parts.append(f"gain {d['gain'][0]:+g} to {d['gain'][1]:+g} dB")
    if "q" in d:
        parts.append(f"Q {d['q'][0]:g}–{d['q'][1]:g}")
    if "freq" in d:
        parts.append(f"{_hz(d['freq'][0])}–{_hz(d['freq'][1])}")
    return f"{d['name']}: " + ", ".join(parts) + ". The settings below are kept within these."


def _hz(v):
    return f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"


def listing():
    """For the page: [{key, name, group, summary}] in the layout list's order."""
    group = lambda k: "Any" if k == "any" else "EQ apps (Your EQ app)" if k.startswith("app:") else "Fixed bands"
    return [{"key": k, "name": name(k), "group": group(k), "summary": summary(k), "fixed": is_fixed(k),
             "shelves": DEVICES[k]["shelves"] if k in DEVICES else not is_fixed(k)} for k in KEYS]
