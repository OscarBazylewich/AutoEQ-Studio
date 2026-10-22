"""Your EQs to compare, one list per IEM or headphone (the measurement's name), kept between sessions in
data\\listen.json: each one's name, filters, a note on where it came from, and whether it's drawn on the graph.

The page adds to a list from the result card (📌 Keep to compare), from History (Listen) or from an EQ file or pasted
filters (in Listen), and plays them all in Listen. At most MAX_EQS per list (each plays through its own filters all
the time, so switching is instant) and MAX_LISTS lists (past that, the one used longest ago goes)."""
import os
import threading
import time

from . import exports
from . import paths
import textfile

PATH = os.path.join(paths.DATA, "listen.json")
MAX_EQS = 12
MAX_LISTS = 300
_LOCK = threading.Lock()  # (the server answers requests in parallel: one change to the file at a time)


def _all():
    # (a file that can't be read is kept as listen.json.bad, never written over: textfile.read_json_kept)
    return textfile.read_json_kept(PATH, dict)


def _device(name):
    name = " ".join(str(name or "").split())[:300]
    if not name:
        raise ValueError("Choose a measurement first: each IEM or headphone has its own list.")
    return name


def get(device):
    """The list for this IEM or headphone ([] if it has none), each EQ checked as put() checks it (one that isn't an
    EQ, e.g. from a hand edit, is left out). Looking at a list counts as using it (the 300-list limit drops the list
    used longest ago), noted at most once a day."""
    device = _device(device)
    with _LOCK:
        data = _all()
        lst = data.get(device)
        if isinstance(lst, dict) and time.time() - (lst.get("used") if isinstance(lst.get("used"), (int, float)) else 0) > 86400:
            lst["used"] = time.time()
            textfile.write_json(PATH, data)  # (quiet: a list shown needn't fail on this)
    out, keys = [], set()
    for i, e in enumerate(lst.get("eqs", []) if isinstance(lst, dict) and isinstance(lst.get("eqs"), list) else []):
        try:
            e = _clean(e, i)
        except ValueError:
            continue
        if e["key"] in keys:  # (two with one key: ✕ would remove the wrong one)
            e["key"] = f"{e['key']}-{i}"
        keys.add(e["key"])
        out.append(e)
    return out


def _clean(e, i):
    if not isinstance(e, dict):
        raise ValueError(f"EQ {i + 1} in the list isn't an EQ.")
    filters = exports.clean_filters(e.get("filters"))
    if not filters:
        raise ValueError(f"“{str(e.get('name') or '')[:60]}” has no filters.")
    color = e.get("color")
    return {"key": str(e.get("key") or f"eq{i}")[:40], "name": " ".join(str(e.get("name") or f"EQ {i + 1}").split())[:80] or f"EQ {i + 1}",
            "note": str(e.get("note") or "")[:200], "filters": filters, "shown": e.get("shown") is not False,
            "color": color if isinstance(color, int) and not isinstance(color, bool) and 0 <= color < 64 else i,
            "added": float(e["added"]) if isinstance(e.get("added"), (int, float)) and not isinstance(e.get("added"), bool) else time.time()}


def put(device, eqs):
    """Replace this IEM's list (checked and cleaned). Returns it as kept."""
    device = _device(device)
    if not isinstance(eqs, list):
        raise ValueError("The list of EQs is missing.")
    if len(eqs) > MAX_EQS:
        raise ValueError(f"At most {MAX_EQS} EQs per IEM or headphone: remove one first.")
    eqs = [_clean(e, i) for i, e in enumerate(eqs)]
    with _LOCK:
        return _put(device, eqs)


def _put(device, eqs):
    data = _all()
    data.pop(device, None)
    if eqs:
        data[device] = {"used": time.time(), "eqs": eqs}
    while len(data) > MAX_LISTS:  # (the list used longest ago goes)
        data.pop(min(data, key=lambda k: data[k].get("used", 0) if isinstance(data[k], dict) else 0))
    textfile.write_json(PATH, data, quiet=False)
    return eqs
