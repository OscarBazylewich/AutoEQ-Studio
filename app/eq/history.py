"""Past EQs, kept between sessions in data\\history.json (oldest first): each one's IEM or headphone, target, method,
filters and scores, and whether it was saved (Save filters or Copy).

The page adds an entry when an EQ is saved (and, if Settings › App says so, after every run). Its key names the
result and its filters, so saving the same EQ again updates that entry, and an edited version gets its own. At most
MAX entries are kept: past that, the oldest unsaved ones go first."""
import os
import threading
import time

from . import exports
from . import paths
import textfile

PATH = os.path.join(paths.DATA, "history.json")
MAX = 1000
_LOCK = threading.Lock()  # (the server answers requests in parallel: one change to the file at a time)
TEXT = ("key", "base", "device", "target", "target_file", "mode", "label")  # (the entry's words, each kept short)


def entries():
    # (a file that can't be read is kept as history.json.bad, never written over: textfile.read_json_kept)
    return [e for e in textfile.read_json_kept(PATH, list) if isinstance(e, dict) and e.get("key")]


def _plain(d):
    """A dict of numbers, words, yes/no and None only (a result's scores, the target adjustments)."""
    if not isinstance(d, dict):
        return {}
    return {str(k)[:40]: (v[:200] if isinstance(v, str) else v) for k, v in list(d.items())[:60]
            if v is None or isinstance(v, (bool, int, float, str))}


def _number(v, default=None):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else default


def add(entry):
    """Add an entry, or update the one with its key (it stays saved once saved). Returns all entries."""
    if not isinstance(entry, dict) or not isinstance(entry.get("key"), str) or not entry["key"].strip():
        raise ValueError("This EQ can't go into the history: it has no name.")
    e = {k: str(entry.get(k) or "")[:300] for k in TEXT}
    files = entry.get("meas_files")
    e.update({
        "when": time.time(),
        "saved": bool(entry.get("saved")),
        "filters": exports.clean_filters(entry.get("filters")),
        "meas_files": [str(n)[:300] for n in files[:200]] if isinstance(files, list) else [],
        "adjust": _plain(entry.get("adjust")),
        "result": _plain(entry.get("result")),
        "rms": _number(entry.get("rms")), "preamp": _number(entry.get("preamp"), 0.0),
        "n_filters": int(_number(entry.get("n_filters"), 0)), "tolerance": _number(entry.get("tolerance"), 0.05),
        # (what shaped the curves it was scored on: History's Show brings them back with the files)
        "site": _plain(entry.get("site")), "rig_convert": entry.get("rig_convert") is not False,
        "band": [float(x) for x in band] if isinstance(band := entry.get("band"), list) and len(band) == 2
                and all(_number(x) is not None for x in band) else None,
    })
    with _LOCK:
        return _add(e)


def _add(e):
    items = entries()
    old = next((x for x in items if x["key"] == e["key"]), None)
    if old:
        e["saved"] = e["saved"] or bool(old.get("saved"))
        items.remove(old)
    items.append(e)
    while len(items) > MAX:  # (the oldest unsaved one first, else the oldest)
        items.remove(next((x for x in items if not x.get("saved")), items[0]))
    textfile.write_json(PATH, items, quiet=False)
    return items


def remove(keys):
    """Remove the entries with these keys (all of them: keys=None). Returns what's left."""
    with _LOCK:
        items = [] if keys is None else [x for x in entries() if x["key"] not in set(keys)]
        textfile.write_json(PATH, items, quiet=False)
        return items
