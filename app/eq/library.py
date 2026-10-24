"""Finds target and frequency-response files on this PC for the search box.

Walks the chosen folders in a background thread, keeps any .txt/.csv/.tsv/.frd file that contains a frequency
response (at least 32 frequency/dB points covering 100 Hz-8 kHz), and groups channel/seating files such as
"GATe Wide L1.txt" ... "GATe Wide R5.txt" into one entry. Results are cached so rescans are quick.
"""
import hashlib
import os
import re
import threading
import time

from . import paths
import textfile
from .inputs import CHANNEL_RE, EXTS, TARGET_RE  # noqa: F401 - (CHANNEL_RE: used here and by other modules)

CACHE_PATH = os.path.join(paths.CACHE, "library.json")
MAX_BYTES = 3_000_000
MAX_DEPTH = 16
SKIP_DIRS = {".venv", "venv", "env", "node_modules", ".git", ".svn", "__pycache__", "site-packages", "appdata",
             "$recycle.bin", "system volume information", "windows", "program files", "program files (x86)",
             "programdata", "recovery", "msocache", ".cache", "cache", "temp", "tmp", "$windows.~bt", "$winreagent"}
# the app's own: saved EQs (filter files, reports), presets, data and caches aren't curves, nor is the program; its
# downloads are the online databases' entries, found under Online databases (Use takes the copy on this PC: offline
# too). With every database downloaded (tools\download_all.py) they were ~95,000 files: each Find… went through them
# all again and listed them twice
SKIP_PATHS = {os.path.normcase(os.path.join(paths.PROGRAM, d))
              for d in ("output", "data", ".venv", "app", "presets", "releases", "downloads", "runtime")} \
    | {os.path.normcase(p) for p in (paths.OUTPUT_DIR, paths.PRESET_DIR, paths.DOWNLOAD_DIR, paths.STUDIO_DATA,
                                     paths.CACHE)}
IN_APP = [os.path.normcase(paths.TARGET_DIR), os.path.normcase(paths.MEAS_DIR)]  # (your targets and measurements)

_lock = threading.Lock()
_state = {"scanning": False, "seen": 0, "found": 0, "cloud": 0, "folders": [], "finished": None, "items": [], "error": ""}
_by_id = {}


def _usual_folders():
    home = os.path.expanduser("~")
    cands = [os.path.join(home, d) for d in ("Downloads", "Documents", "Desktop", "Music")]
    od = os.environ.get("OneDrive")
    if od:
        cands += [os.path.join(od, d) for d in ("Documents", "Desktop")]
    return list(dict.fromkeys(cands))


def default_folders():
    return [c for c in _usual_folders() if os.path.isdir(c)]


def _asked_for(cfg):
    """The folders to search, yours or the usual ones, not yet looked at (folders_for keeps those that exist)."""
    user = [os.path.expandvars(os.path.expanduser(f.strip())) for f in (cfg.get("library", {}).get("folders") or [])
            if f.strip()]
    return user or _usual_folders()


def folders_for(cfg):
    return [f for f in _asked_for(cfg) if os.path.isdir(f)]


def sniff(path):
    """Frequency-response check. Returns {"points", "fmin", "fmax"} or None."""
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None
    text = textfile.decode(raw)
    if "\0" in text[:4096]:  # (a binary file)
        return None
    return sniff_text(textfile.normalize_fr(text))


def sniff_text(text):
    """{"points", "fmin", "fmax"} when the text holds a frequency response (at least 32 rising frequencies covering
    100 Hz-8 kHz), else None."""
    fs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in "*#;":
            continue
        parts = re.split(r"[\s,;]+", line)
        if len(parts) < 2:
            continue
        try:
            f, v = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        if not (0 < f < 50000 and -250 < v < 250):
            continue
        fs.append(f)
    if len(fs) < 32:
        return None
    rising = sum(b > a for a, b in zip(fs, fs[1:]))
    if rising < 0.9 * (len(fs) - 1) or min(fs) > 100 or max(fs) < 8000:
        return None
    return {"points": len(fs), "fmin": min(fs), "fmax": max(fs)}


def guess_kind(path):
    parts = os.path.normpath(path).split(os.sep)
    name = os.path.splitext(parts[-1])[0]
    here = os.path.normcase(os.path.dirname(path))
    if here == os.path.normcase(paths.TARGET_DIR):
        return "target"
    if here == os.path.normcase(paths.MEAS_DIR):
        return "measurement"
    if TARGET_RE.search(name) or any(re.fullmatch(r"targets?", p, re.IGNORECASE) for p in parts[-4:-1]):
        return "target"
    return "measurement"


# file attributes of a file that isn't on this PC (OneDrive's "online-only" files): recall on open / on data access,
# offline
CLOUD_ONLY = 0x40000 | 0x400000 | 0x1000


def _app_downloads(parent, name):
    """A downloads folder of another copy of AutoEQ Studio (a test copy, an unzipped one) or of AutoEQ Local: online
    databases' entries too, not your own curves (beside it, app\\eq\\databases.py or app\\databases.py)."""
    return name.lower() == "downloads" and any(os.path.isfile(os.path.join(parent, "app", *sub, "databases.py"))
                                               for sub in (("eq",), ()))


def _walk(root, seen_cb, cloud_cb=lambda: None):
    """Yields (path, mtime, size) for candidate files under root."""
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        if os.path.normcase(d) in SKIP_PATHS:
            continue
        try:
            with os.scandir(d) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    if depth < MAX_DEPTH and e.name.lower() not in SKIP_DIRS and not e.name.startswith(".") \
                            and not _app_downloads(d, e.name):
                        stack.append((e.path, depth + 1))
                elif e.name.lower().endswith(EXTS):
                    st = e.stat()
                    if getattr(st, "st_file_attributes", 0) & CLOUD_ONLY:  # (not on this PC: reading it downloads it)
                        cloud_cb()
                        continue
                    seen_cb()
                    yield e.path, st.st_mtime, st.st_size
            except OSError:
                continue


def _group(files):
    """files: [(path, info)] -> index entries (channel/seating files of one device merged)."""
    groups = {}
    for path, info in files:
        folder, fname = os.path.split(path)
        stem = os.path.splitext(fname)[0]
        m = CHANNEL_RE.match(stem)
        base = m.group(1).strip() if m and m.group(1).strip() else stem
        key = (os.path.normcase(folder), base.lower(), guess_kind(path))
        groups.setdefault(key, {"name": base, "folder": folder, "kind": key[2], "files": [], "points": 0})
        g = groups[key]
        g["files"].append(path)
        g["points"] = max(g["points"], info["points"])
    items = []
    for g in groups.values():
        if len(g["files"]) == 1:  # a lone "Name L" stays under its full name
            g["name"] = os.path.splitext(os.path.basename(g["files"][0]))[0]
        g["files"].sort()
        g["in_app"] = any(textfile.inside(g["folder"], d) for d in IN_APP)
        items.append(g)
    items.sort(key=lambda g: (g["name"].lower(), g["folder"].lower()))
    for g in items:  # (by folder and name: a position changed with every rescan, and an old id got another group)
        g["id"] = hashlib.sha1(f"{os.path.normcase(g['folder'])}|{g['name']}|{g['kind']}".encode("utf-8", "replace")).hexdigest()[:12]
    return items


def _scan(folders):
    cache = textfile.read_json(CACHE_PATH, {})  # {path: [mtime, size, sniff()]}: unchanged files aren't read again
    new_cache, found = {}, []

    def seen():
        with _lock:
            _state["seen"] += 1

    def cloud():
        with _lock:
            _state["cloud"] += 1

    try:
        roots = list(dict.fromkeys(folders + [paths.TARGET_DIR, paths.MEAS_DIR]))
        done = set()
        for root in roots:
            for path, mtime, size in _walk(root, seen, cloud):
                key = os.path.normcase(path)
                if key in done:
                    continue
                done.add(key)
                c = cache.get(key)
                info = c[2] if c and c[0] == mtime and c[1] == size else sniff(path)
                new_cache[key] = [mtime, size, info]
                if info:
                    found.append((path, info))
                    with _lock:
                        _state["found"] = len(found)
        items = _group(found)
        textfile.write_json(CACHE_PATH, new_cache)
        with _lock:
            _state.update(items=items, finished=time.time(), error="")
            _by_id.clear()
            _by_id.update({g["id"]: g for g in items})
    except Exception as e:  # keep the app usable whatever happens on disk
        with _lock:
            _state["error"] = str(e)
    finally:
        with _lock:
            _state["scanning"] = False


RESCAN_AFTER = 60  # seconds: the same folders searched again within this only when asked (force)


def start_scan(cfg, force=False):
    """Search the folders in the background. Not again for the same folders within RESCAN_AFTER unless force (Find…
    asks each time it opens; a search that had just ended was done again, and the list drawn again after it). Which
    of them exist is seen in the search's own thread: on a network folder that doesn't answer (or a disk asleep) that
    took seconds, and Make an EQ, Find… and Sources ask from the window's thread (2026-10-24)."""
    asked = _asked_for(cfg)
    with _lock:
        if _state["scanning"]:
            return False
        if not force and _state["finished"] and time.time() - _state["finished"] < RESCAN_AFTER \
                and _state.get("asked") == asked and not _state["error"]:
            return False
        _state.update(scanning=True, seen=0, found=0, cloud=0, asked=asked)
    threading.Thread(target=_scan_asked, args=(asked,), daemon=True).start()
    return True


def _scan_asked(asked):
    folders = [f for f in asked if os.path.isdir(f)]
    with _lock:
        _state["folders"] = folders
    _scan(folders)


def status(with_items=False):
    with _lock:
        out = {k: v for k, v in _state.items() if k != "items"}
        out["count"] = len(_state["items"])
        if with_items:
            out["items"] = list(_state["items"])
    return out


def item(item_id):
    with _lock:
        g = _by_id.get(str(item_id))
    if not g:
        raise ValueError("That file is no longer in the index - rescan and try again.")
    return g
