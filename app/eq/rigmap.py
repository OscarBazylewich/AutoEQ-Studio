"""Which rig each database (and each AutoEq source) measures on, as worked out from the measurements themselves by
tools/build_rig_map.py (rigmap.json): each database's models compared with the same models from sources whose rig
is certain. rigs.source_rig asks here first; without an answer here it falls back to what the source states or
the usual rig for that kind of database.
"""
import os

from . import databases
import textfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "rigmap.json")
_data = {}


def data():
    if "d" not in _data:
        _data["d"] = textfile.read_json(DATA_PATH, {"units": {}})
    return _data["d"]


def unit_key(it):
    """A database entry's (or recorded source's) unit: its database, or for AutoEq, its source and form."""
    url = it.get("site_url") or ""
    if "jaakkopasanen/AutoEq" in url:
        src, _, form = (it.get("sub") or "").partition(" · ")
        return f"autoeq|{src}|{form}"
    return databases.norm_url(url)


def _note(u):
    n, w = u.get("models", 0), u.get("wins", 0)
    base = (f"worked out from {n} models it shares with sources whose rig is known "
            f"(this rig fits best on {round(w * 100)}% of them)")
    if u.get("loose"):
        base += "; it fits less closely than two measurements on one rig do (probably a clone of it, or another setup)"
    if u.get("mixed"):
        return base + "; some of its measurements fit another rig (the reviewer changed rigs): those are labelled one by one"
    return base


def lookup(it):
    """(rig or None, sure, how) for a database entry, or None when rigmap.json has nothing useful on it."""
    u = data()["units"].get(unit_key(it))
    if not u or u.get("confidence") in (None, "stated", "low"):
        return None  # (stated rigs come from the sources themselves; a weak inference isn't used)
    one = (u.get("entries") or {}).get(it.get("name"))
    if one:
        from . import rigs  # (it imports this module)
        if one not in rigs.RIGS:  # ("unknown" or a rig the app doesn't know: not a rig to use)
            return None, False, "its measurements fit none of the four rigs the app knows; " + _note(u)
        return one, True, "worked out from this measurement itself (compared with the same model from sources whose rig is known)"
    if u["rig"] == "unknown":
        return None, False, "its measurements fit none of the four rigs the app knows (e.g. a MiniDSP EARS or another fixture); " + _note(u)
    return u["rig"], u["confidence"] == "high", _note(u)


def site_notes():
    """{database name, or "AutoEq (GitHub)|<source> · <form>": how its rig was worked out} for the page's rig tags."""
    out = {}
    for key, u in data()["units"].items():
        if u.get("confidence") in (None, "low"):
            continue
        if u.get("confidence") == "stated":
            text = "stated by the source" + (f" ({u['source']})" if u.get("source") else "")
        elif u["rig"] == "unknown":
            text = "fits none of the four rigs the app knows; " + _note(u)
        else:
            text = _note(u) + ("" if u["confidence"] == "high" else " (medium confidence)")
        if key.startswith("autoeq|"):
            _, src, form = key.split("|", 2)
            out[f"AutoEq (GitHub)|{src} · {form}"] = text
        else:
            out[u.get("name", key)] = text
    return out
