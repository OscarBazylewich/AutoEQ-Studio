"""Which measurement rig (ear simulator) a curve comes from, or a target is made for.

A rig is one of RIGS' keys, and it comes with "sure": stated by the source, or worked out from its measurements with
high confidence (rigmap.py), against a guess ("the usual rig for that kind of database", a rig named in a file name).
The page shows it as a tag: "5128" (sure), "711?" (a guess) or "" (unknown): rig_tag().

  source_rig(entry)   a database entry, or a record of where a file in the app came from (paths.SOURCES_PATH)
  file_rig(name)      a file: from where the app downloaded it, its database's download folder or "(database)" tag,
                      else a rig named in the file name
  target_rig(name)    a target: where it came from, else its name ("Harman IE" -> 711, "5128 DF" -> 5128 …)

compare.py ranks measurements by rig; rigconv.py converts a target between rigs.
"""
import os
import re
import threading

from . import databases
from . import paths
from . import rigmap
import textfile

RIGS = {"5128": "B&K 5128", "711": "711-type coupler (IEC 60318-4)", "43AG": "GRAS 43AG", "HMS": "Head Acoustics HMS II.3"}

# The AutoEq repository's sources, by source and form: their rigs as the sources describe their setups
AUTOEQ_RIGS = {("oratory1990", "in-ear"): ("711", True), ("oratory1990", "over-ear"): ("43AG", True),
                ("Innerfidelity", "in-ear"): ("HMS", True), ("Innerfidelity", "over-ear"): ("HMS", True),
                ("Innerfidelity", "earbud"): ("HMS", True)}
_AUTOEQ_UNKNOWN = {"rtings", "Rtings", "Headphone.com Legacy"}  # rigs changed over time or aren't documented


def autoeq_source(it):
    """(source, form) of an AutoEq entry ("oratory1990 · in-ear")."""
    src, _, form = (it.get("sub") or "").partition(" · ")
    return src, form


def source_rig(it):
    """(rig key or None, sure) for a database entry (or a recorded average, which carries its rig): the rig worked out
    from the measurements themselves when there is one (rigmap.py), else what the source states or usually uses."""
    if it.get("rig") in RIGS:
        return it["rig"], True
    m = rigmap.lookup(it)
    if m is not None:
        return m[0], m[1]
    site = databases.find_site(it.get("site_url")) or {}
    if site.get("rig"):
        return tuple(site["rig"])
    if site.get("short") == "AutoEq":
        src, form = autoeq_source(it)
        if (src, form) in AUTOEQ_RIGS:
            return AUTOEQ_RIGS[(src, form)]
        if src in _AUTOEQ_UNKNOWN or form != "in-ear":
            return None, False
        return "711", False  # (hobbyist IEM measurements almost all use 711-type couplers or their clones)
    return None, False


def rig_tag(rig):
    """(rig, sure) -> "5128", "711?" (not stated by the source: the usual rig there), or "" (unknown)."""
    return (rig[0] + ("" if rig[1] else "?")) if rig[0] in RIGS else ""


# ---------------------------------------------------------------- where the app's files came from
SOURCES_PATH = paths.SOURCES_PATH
_SOURCES_LOCK = threading.Lock()  # (the server answers requests in parallel: one change to the file at a time)


def sources():
    """{file name in the app: where it came from (site_url, site, sub, name, rig, of)}."""
    return textfile.read_json(SOURCES_PATH, {})


def record_source(names, it):
    """Remember which database entry (or average) files in the app came from, so their rig is known later."""
    with _SOURCES_LOCK:
        d = sources()
        for n in names:
            d[n] = {k: it.get(k) for k in ("site_url", "site", "sub", "name", "rig", "of") if it.get(k) is not None}
        textfile.write_json(SOURCES_PATH, d, indent=1)


def forget_source(names):
    """Files in the app that didn't come from a database (dropped, from this PC) or are gone: an old record under
    their name would give them that database's rig."""
    with _SOURCES_LOCK:
        d = sources()
        if any(n in d for n in names):
            for n in names:
                d.pop(n, None)
            textfile.write_json(SOURCES_PATH, d, indent=1)


# ---------------------------------------------------------------- files
# a rig named in a file name ("…_BK5128_raw"), as a guess
_NAME_RIGS = [(r"5128", "5128"), (r"(?<![0-9])711(?![0-9])", "711"), (r"43ag", "43AG"), (r"(?<![a-z])hms(?![a-z])|innerfidelity", "HMS")]
_TAG_RE = re.compile(r"\(([^()]+)\)(?:[\s_-]*(?:L|R|Left|Right)?[\s_-]*\d{0,2})?$", re.I)  # "(Amigo) L", "(L800 IEM) R3"
_autoeq_index = {}


def _autoeq_item(site_url, name, src):
    """The AutoEq database entry for "<name> (<source>)", for its rig (which depends on the source and form)."""
    items = databases.items()
    if _autoeq_index.get("n") != len(items):
        idx = {}
        for it in items:
            if it.get("site_url") == site_url and it["kind"] == "measurement":
                idx.setdefault((it["name"].lower(), autoeq_source(it)[0].lower()), it)
        _autoeq_index.clear()
        _autoeq_index.update(n=len(items), idx=idx)
    return _autoeq_index["idx"].get((name.lower(), src.lower()))


def _site_of_file(name_tag, folder):
    """The database a file was downloaded from: by its download folder, else by its "(database)" name tag."""
    sites = None
    if folder and os.path.normcase(os.path.dirname(os.path.normpath(folder))) == os.path.normcase(databases.DOWNLOAD_DIR):
        here = os.path.basename(os.path.normpath(folder))
        sites = databases.all_sites() + databases.added_sites()
        site = next((s for s in sites if databases.folder_name(s["name"]) == here), None)
        if site:
            return site
    if name_tag:
        sites = sites or databases.all_sites() + databases.added_sites()
        return next((s for s in sites if s.get("short") == name_tag), None)
    return None


def file_rig(name, folder=None, recorded=None):
    """(rig key or None, sure) for a file: from where the app downloaded it, else from its database's download folder
    or its "(database)" name tag, else a rig named in the file name (a guess). recorded: sources(), if already read."""
    rec = (recorded if recorded is not None else sources()).get(name)
    if rec:
        rig = source_rig(rec)
        if rig[0]:
            return rig
    base = os.path.splitext(name)[0]
    m = _TAG_RE.search(base)
    tag = m.group(1).strip() if m else ""
    site = _site_of_file(tag, folder)
    if site:
        if site.get("rig") and site["rig"][0]:
            return tuple(site["rig"])
        if site.get("short") == "AutoEq" and tag:
            it = _autoeq_item(site["url"], base[:m.start()].strip(), tag)
            if it:
                return source_rig(it)
    low = name.lower()
    for pat, rig in _NAME_RIGS:
        if re.search(pat, low):
            return rig, False
    return None, False


def file_unit(name, folder=None, recorded=None):
    """The database (rigmap's unit key: a database's URL, or "autoeq|<source>|<form>") a file in the app came from:
    from where the app downloaded it, else its database's download folder or "(database)" tag; else None."""
    rec = (recorded if recorded is not None else sources()).get(name)
    if rec and rec.get("site_url"):
        return rigmap.unit_key(rec)
    base = os.path.splitext(name)[0]
    m = _TAG_RE.search(base)
    tag = m.group(1).strip() if m else ""
    site = _site_of_file(tag, folder)
    if not site:
        return None
    if site.get("short") == "AutoEq":
        it = _autoeq_item(site["url"], base[:m.start()].strip(), tag) if tag else None
        return rigmap.unit_key(it) if it else None
    return rigmap.unit_key({"site_url": site["url"]})


# ---------------------------------------------------------------- targets
# (over-ear words before the 711 ones, whole words: "Crinacle OE", "IEF OE" and "Harman OE 2018 Linear", whose
# "l-inear" read as in-ear, are 43AG targets: review 2)
_TARGET_NAME_RIGS = [(r"5128|hcom|hpdc|^(iem|headphone) - ", "5128"),
                     (r"\b(oe|over-?ear)\b|43ag", "43AG"),
                     (r"\b711\b|harman.*\b(ie|in-?ear)\b|\bief\b|crinacle|\bin-ear 20(17|19)", "711"),
                     (r"innerfidelity|\bhms\b", "HMS")]


_target_index = {}


def _targets_by_name():
    """{lower-case name: [database target entries]}, made again when the lists change (a scan of all 54,000 entries
    per target was slow with many targets on this PC)."""
    items = databases.items()
    version = (len(items), items[0]["id"] if items else None, items[-1]["id"] if items else None)
    if _target_index.get("v") != version:
        idx = {}
        for it in items:
            if it["kind"] == "target":
                idx.setdefault(it["name"].lower(), []).append(it)
        _target_index.clear()
        _target_index.update(v=version, idx=idx)
    return _target_index["idx"]


def target_rig(name, recorded=None):
    """(rig key or None, how it was worked out) for a target file name. recorded: sources(), if already read."""
    rec = (recorded if recorded is not None else sources()).get(name)
    if rec:
        rig, _ = source_rig(rec)
        if rig:
            return rig, f"it came from {rec['site']}"
    n = name.lower()
    for pat, rig in _TARGET_NAME_RIGS:
        if re.search(pat, n):
            return rig, "from its name"
    stem = re.sub(r"\s*target$", "", os.path.splitext(name)[0], flags=re.I).strip().lower()
    idx = _targets_by_name()
    for it in idx.get(stem, []) + idx.get(stem + " target", []):
        rig, _ = source_rig(it)
        if rig:
            return rig, f"it comes from {it['site']}"
    return None, "unknown"


def target_tag(name, recorded=None):
    """A target's rig tag: the rig it is made for ("?" when that comes only from its name)."""
    rig, how = target_rig(name, recorded)
    return rig_tag((rig, how != "from its name"))


# ---------------------------------------------------------------- tags for the page
def inputs_rigs(inputs_state):
    """{file name: rig tag} for the files in the app (measurements, and targets by what they're made for)."""
    rec = sources()
    out = {m["name"]: rig_tag(file_rig(m["name"], recorded=rec)) for m in inputs_state.get("measurements", [])}
    for t in inputs_state.get("targets", []):
        out[t] = target_tag(t, rec)
    return out


def library_rigs(groups):
    """The rig tag of each group of files found on this PC (added to the groups as "rig")."""
    rec = sources()
    for g in groups:
        name = os.path.basename(g["files"][0]) if g.get("files") else g["name"]
        g["rig"] = target_tag(name, rec) if g.get("kind") == "target" else rig_tag(file_rig(name, g.get("folder"), rec))
    return groups
