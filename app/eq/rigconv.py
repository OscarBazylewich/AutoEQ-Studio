"""Converting a target to the measurement's rig.

A target is made for one kind of ear simulator (B&K 5128, 711-type coupler, GRAS 43AG, HMS); a measurement from
another rig differs from it in a systematic way, mostly above ~2 kHz, so EQing it to that target would also "correct"
the difference between the rigs. rigdata.json (made by tools/build_rig_conversions.py from models measured on both
rigs in the online databases) holds, per pair of rigs and kind of device, the average difference and how well it
predicts a device it wasn't made from (the uncertainty). When the measurement and the target come from different
rigs and there's data for that pair, the target is converted to the measurement's rig: the target's text gets the
difference added, so every EQ method, the graph and the scores use the converted target.
"""
import json
import os
import re

import numpy as np

from . import rigs

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "rigdata.json")
_data = {}


def data():
    if "d" not in _data:
        try:
            with open(DATA_PATH, encoding="utf-8") as fh:
                d = json.load(fh)
            d["grid"] = np.array(d["grid"])
            # (a conversion without its error figures can't be judged or ranked: it isn't used)
            for k in ("pairs", "units"):
                d[k] = [c for c in d.get(k, []) if error_of(c.get("bands")) is not None]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            d = {"grid": np.array([20.0, 20000.0]), "pairs": []}
        _data["d"] = d
    return _data["d"]


def find(device, frm, to):
    """The conversion from rig `frm` to rig `to` (what to add to a curve measured/made for `frm`) for a kind of
    device, with its uncertainty: {"conversion", "uncertainty", "mismatch", "models", "bands", "device"} or None."""
    for p in data()["pairs"]:
        if p["device"] != device:
            continue
        if (p["from"], p["to"]) == (frm, to):
            sign = 1
        elif (p["from"], p["to"]) == (to, frm):
            sign = -1
        else:
            continue
        return {"device": device, "from": frm, "to": to, "models": p["models"], "bands": p["bands"],
                "conversion": (sign * np.array(p["conversion"])).tolist(), "uncertainty": p["uncertainty"],
                "mismatch": p["mismatch"], "via": p.get("via")}  # (via: through a middle rig, too few models for its own)
    return None


def find_unit(unit, frm):
    """A database's own conversion (tools/build_unit_conversions.py) from rig `frm` to its measurements, or None:
    {"conversion", "uncertainty", "mismatch", "models", "bands", "device", "name", "rig"}."""
    for u in data().get("units", []):
        if u["unit"] == unit and u["from"] == frm:
            return {k: u[k] for k in ("conversion", "uncertainty", "mismatch", "models", "bands", "device", "name", "rig")}
    return None


def example():
    """For the Guide's demo: a 5128 target converted for an IEM measured on a 711 coupler (the commonest case)."""
    c = find("iem", "5128", "711")
    if not c:
        return None
    return {"grid": [round(float(x), 2) for x in data()["grid"]], "conversion": c["conversion"],
            "uncertainty": c["uncertainty"], "models": c["models"], "bands": c["bands"], "from": "5128", "to": "711"}


def devices_for(frm, to):
    return [p["device"] for p in data()["pairs"] if {p["from"], p["to"]} == {frm, to}]


_IEM = re.compile(r"\biem\b|in-?ear|\bie\b|harman ie|earphone|\b711\b", re.I)
_HP = re.compile(r"over-?ear|\boe\b|headphone|on-?ear", re.I)


def device(meas_rig, target_rig, target_name, meas_hint=""):
    """"iem" or "headphone": from the rigs (a 711 coupler only takes IEMs, a 43AG is for headphones), the target's
    and measurement's names or sources, else whichever the data has for this pair (IEMs if both)."""
    if "711" in (meas_rig,) or (meas_rig != "43AG" and target_rig == "711" and not _HP.search(target_name)):
        return "iem"
    if meas_rig == "43AG":
        return "headphone"
    for text in (target_name, meas_hint):
        if _HP.search(text or ""):
            return "headphone"
        if _IEM.search(text or ""):
            return "iem"
    if target_rig == "43AG":
        return "headphone"
    have = devices_for(meas_rig, target_rig)
    return have[0] if len(have) == 1 else "iem"


def status(cfg, target_path, meas_paths):
    """What the Measurement field's rig note shows, and whether the target is converted."""
    tname = os.path.basename(target_path)
    trig, how = rigs.target_rig(tname)
    found, sure, hint, units = set(), True, "", set()
    recorded = rigs.sources()
    for p in meas_paths:
        r, s = rigs.file_rig(os.path.basename(p), os.path.dirname(p), recorded)
        found.add(r)
        sure = sure and s
        units.add(rigs.file_unit(os.path.basename(p), os.path.dirname(p), recorded))
        rec = recorded.get(os.path.basename(p)) or {}
        # (no record: the folder, e.g. "downloads\Earphones Archive headphones (5128)"; the join gave " " before)
        hint = hint or " ".join(str(rec.get(k) or "") for k in ("site", "sub")).strip() or os.path.dirname(p)
    out = {"meas_rig": None, "meas_sure": sure, "target_rig": trig, "target_how": how, "enabled": bool(cfg.get("rig_convert", {}).get("enabled", True)),
           "applied": False}
    # the measurement's database has a conversion of its own from the target's rig: it knows that database's setup
    # (a clone of a rig, a fixture none of the four, its calibration) better than the rigs' average does
    unit = units.pop() if len(units) == 1 else None
    uc = find_unit(unit, trig) if unit and trig else None
    if uc and len(found) == 1:
        out.update(meas_rig=next(iter(found)), state="available", applied=out["enabled"], device=uc["device"], unit=uc["name"],
                   **{k: uc[k] for k in ("models", "bands", "conversion", "uncertainty", "mismatch")})
        return out
    if len(found) != 1 or None in found:
        out["state"] = "mixed" if len(found - {None}) > 1 else "unknown"
        return out
    mrig = found.pop()
    out["meas_rig"] = mrig
    if not trig:
        out["state"] = "unknown"
        return out
    if mrig == trig:
        out["state"] = "same"
        return out
    dev = device(mrig, trig, tname, hint)
    conv = find(dev, trig, mrig)  # (the target, made for its rig, converted to the measurement's)
    out["device"] = dev
    if not conv:
        out["state"] = "nodata"
        return out
    out.update(state="available", applied=out["enabled"], **{k: conv[k] for k in ("models", "bands", "conversion", "uncertainty", "mismatch", "via")})
    return out


# ---------------------------------------------------------------- how close a measurement can get to a target's rig
# (for ranking measurements and marking them in the search list; all errors 1-10 kHz, dB, on models left out)
def error_of(bands, after=True):
    """A conversion's typical error from its bands: after converting (after), or without it."""
    ks = [k for k in ("1000-3000", "3000-6000", "6000-10000") if k in (bands or {})]
    return float(np.sqrt(np.mean([bands[k][1 if after else 0] ** 2 for k in ks]))) if ks else None


def same_rig_spread(device):
    """How far a database's measurements of a model are from the reference sources' on the same rig (units and
    seating; the median over databases): what a measurement from the target's own rig is off by anyway."""
    if "spread" not in _data:
        d, out = data(), {}
        for dev in ("iem", "headphone"):
            v = [u["error_1k_10k"][0] for u in d.get("units_tested", [])
                 if u["device"] == dev and u.get("rig") == u["from"] and not u.get("via") and u.get("error_1k_10k")]
            out[dev] = float(np.median(v)) if v else {"iem": 1.9, "headphone": 2.3}[dev]
        _data["spread"] = out
    return _data["spread"].get(device, 2.0)


def expected(device, target_rig, meas_rig, unit, enabled=True):
    """How a measurement relates to a target's rig: {"how": "same" | "own" | "rigs" | "nodata" | "unknown", "error":
    the typical error left after converting (without, when converting is off), "rig_part": what the rig adds on top of
    the usual units-and-seating spread, "models"}. "own": its database's own conversion; "rigs": the rigs' average."""
    own = find_unit(unit, target_rig) if unit and target_rig else None
    if own:
        c, how = own, "own"
    elif meas_rig and meas_rig == target_rig:
        return {"how": "same"}
    elif not meas_rig:
        return {"how": "unknown"}
    else:
        c, how = find(device, target_rig, meas_rig), "rigs"
        if not c:
            return {"how": "nodata"}
    e = error_of(c["bands"], after=enabled)
    s = same_rig_spread(c.get("device") or device)
    return {"how": how, "error": e, "rig_part": float(np.sqrt(max(0.0, e * e - s * s))), "models": c["models"], "enabled": enabled}


def page_units():
    """{a database as the page names it (site name, or "AutoEq (GitHub)|<source> · <form>"): its own conversions
    [{"from", "device", "models", "error", "before"}]}, for the search list's marks."""
    out = {}
    for u in data().get("units", []):
        name = u["name"]
        if u["unit"].startswith("autoeq|"):
            _, src, form = u["unit"].split("|", 2)
            name = f"AutoEq (GitHub)|{src} · {form}"
        out.setdefault(name, []).append({"from": u["from"], "device": u["device"], "models": u["models"],
                                         "error": round(error_of(u["bands"]), 1), "before": round(error_of(u["bands"], False), 1)})
    return out


def convert_text(text, conversion):
    """The target file's text with the conversion added to every frequency/dB line (interpolated on a log scale;
    beyond the data's 20 Hz–20 kHz, its end values)."""
    grid = np.log10(data()["grid"])
    conv = np.asarray(conversion, dtype=float)
    out = ["* converted to the measurement's rig by AutoEQ Studio"]
    for ln in text.splitlines():
        parts = re.split(r"[\s,]+", ln.strip())
        try:
            f, v = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            continue
        if f <= 0:
            continue
        out.append(f"{f:g}\t{v + float(np.interp(np.log10(f), grid, conv)):.3f}")
    return "\n".join(out) + "\n"


def on_grid(values, f):
    """Values on rigdata's grid, on another frequency grid (the curves')."""
    return np.interp(np.log10(np.asarray(f, dtype=float)), np.log10(data()["grid"]), np.asarray(values, dtype=float)).tolist()
