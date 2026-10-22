"""The app's own files: the targets in Targets and the measurements in Measurements (paths.py), which of them are in
use (settings "files": the active target, the measurements left out), and names read from file names.
"""
import os
import re
import time

from . import paths
import textfile

TARGET_DIR, MEAS_DIR = paths.TARGET_DIR, paths.MEAS_DIR
EXTS = (".txt", ".csv", ".tsv", ".frd")  # frequency-response files (text)
# "GATe Wide L1", "HD600_R", "X (Left)": (device, channel, seating number)
CHANNEL_RE = re.compile(r"^(.*?)[\s_-]+(?:\(|\[)?(L|R|Left|Right)(?:\)|\])?[\s_-]*(\d{0,2})$", re.IGNORECASE)
# a file name that says it's a target
TARGET_RE = re.compile(r"target|\btgt\b|harman|diffuse|\bdf\b|preference|\bjm-?1\b|\bise\b|\bksi\b|\biso\s*11904",
                       re.IGNORECASE)


def folder(kind):
    return TARGET_DIR if kind == "target" else MEAS_DIR


def read_text(path):
    """A frequency-response file's text, whatever encoding and number format it was saved in (see textfile)."""
    return textfile.read_fr(path)


def _files(where):
    os.makedirs(where, exist_ok=True)
    return sorted(n for n in os.listdir(where) if n.lower().endswith(EXTS))


def state(cfg):
    """{targets, active_target, measurements: [{name, included}], device}: what the page's Target and Measurement
    fields show. The active target is the first one when the chosen one is gone."""
    targets = _files(TARGET_DIR)
    active = cfg["files"]["active_target"]
    if active not in targets:
        active = targets[0] if targets else ""
    excluded = set(cfg["files"]["excluded"])
    meas = [{"name": n, "included": n not in excluded} for n in _files(MEAS_DIR)]
    on = [m["name"] for m in meas if m["included"]]
    return {"targets": targets, "active_target": active, "measurements": meas, "device": device_name(on) if on else ""}


def device_name(names):
    """'GATe Wide L1.txt' ... 'GATe Wide R5.txt' -> 'GATe Wide' (the most common name once channel/seating is removed)."""
    stems = [os.path.splitext(n)[0] for n in names]
    if not stems:
        return ""
    if len(stems) == 1:  # ("GATe Wide L1" alone is still GATe Wide: its EQs to compare, History, file names)
        m = CHANNEL_RE.match(stems[0].strip())
        one = (m.group(1).strip() if m and m.group(1).strip() else stems[0]).strip()
        return re.sub(r"(\))\s+\d+$", r"\1", one)  # (a download's number after its "(database)" label, as below)
    bases = [re.sub(r"[\s_-]*(L|R|Left|Right)?\s*\d*$", "", s, flags=re.IGNORECASE).strip() or s for s in stems]
    if len(set(bases)) > 1:  # (a database's several measurements, "Foo 1 L", "Foo 2 L": the number before the channel too)
        nums = [re.sub(r"\s+\d+$", "", b) for b in bases]
        if len(set(nums)) == 1:
            bases = nums
    # (a download's own number after its "(database)" label, also when only one of the set is ticked: "Foo (Bar) 1";
    # a model's number, "IE 900", never follows a bracket)
    bases = [re.sub(r"(\))\s+\d+$", r"\1", b) for b in bases]
    return max(dict.fromkeys(bases), key=bases.count)


def selected(cfg, target=None, measurements=None):
    """Paths of the active target and the included measurements (or explicit paths from the command line)."""
    if target is None or measurements is None:
        st = state(cfg)
        if target is None:
            if not st["active_target"]:
                raise ValueError("No target file. Drop one onto the Target box.")
            target = os.path.join(TARGET_DIR, st["active_target"])
        if measurements is None:
            measurements = [os.path.join(MEAS_DIR, m["name"]) for m in st["measurements"] if m["included"]]
    if not measurements:
        raise ValueError("No measurement files. Drop one or more onto the Measurement box.")
    return target, measurements


def guess_kind(filename):
    return "target" if TARGET_RE.search(filename) else "measurement"


def add_file(kind, filename, content):
    """Save an uploaded/dropped file into the right input folder. Returns the stored name (see add_files)."""
    return add_files(kind, [(filename, content)])[0]


def add_files(kind, files):
    """Save files [(file name, text)] into the right input folder (decimal commas and semicolons made plain, names
    Windows accepts, each written in one step). A different file already there under a name is never replaced: the
    set is saved as "<name> (2)" (before a channel: "GATe (2) L1", so its files stay one device), the same number for
    all. Returns the stored names."""
    from . import engines  # (the site's own parser counts the points)
    where = folder(kind)
    os.makedirs(where, exist_ok=True)
    ready = []
    for filename, content in files:
        name = textfile.safe_name(os.path.basename(filename or "").strip(), "file.txt")
        if not name.lower().endswith(EXTS):
            name += ".txt"
        ext = next(e for e in EXTS if name.lower().endswith(e))
        if not name[:-len(ext)].strip(". "):  # (only an extension: ".txt")
            name = "file" + ext
        content = textfile.normalize_fr(content)
        n = engines.count_points(content)
        if n < 32:
            raise ValueError(f"{name}: only {n} frequency/dB points found - is this a frequency response file?")
        ready.append((name, content))
    for k in range(1, 1000):
        names = [_numbered(name, k) for name, _ in ready]
        if all(_free_or_same(os.path.join(where, n), c) for n, (_, c) in zip(names, ready)):
            break
    for n, (_, content) in zip(names, ready):
        textfile.write_atomic(os.path.join(where, n), content)
    return names


def _numbered(name, k):
    """"GATe L1.txt" as the k-th file of that name: "GATe (2) L1.txt" (1: as it is)."""
    if k == 1:
        return name
    stem, ext = os.path.splitext(name)
    m = CHANNEL_RE.match(stem)
    if m and m.group(1).strip():
        return f"{m.group(1).strip()} ({k}) {stem[len(m.group(1)):].strip(' _-')}{ext}"
    return f"{stem} ({k}){ext}"


def _free_or_same(path, content):
    """Can content be saved at path: nothing there, or the same curve (line endings aside)?"""
    if not os.path.exists(path):
        return True
    try:
        old = textfile.read(path)
    except OSError:
        return False
    return old.replace("\r\n", "\n").strip() == content.replace("\r\n", "\n").strip()


def _plain_name(name):
    """A file's name without any folder part; never empty, "." or ".." (those would mean the folder itself)."""
    base = os.path.basename(name) if isinstance(name, str) else ""
    if base.strip(" .") == "":
        raise ValueError("No file name was given.")
    return base


def _in_use_retry(fn, *args):
    """fn(*args), tried again for up to a second while Windows says the file is in use: a curves load in the
    background may be reading it at that moment (Undo's removal failed so, 2026-10-08)."""
    for i in range(11):
        try:
            return fn(*args)
        except PermissionError:
            if i == 10:
                raise
            time.sleep(0.1)


def remove_file(kind, name):
    path = os.path.join(folder(kind), _plain_name(name))
    if os.path.isfile(path):
        _in_use_retry(os.remove, path)


def move_file(kind, name):
    """Move a file from the `kind` folder to the other one (a different file of that name there is never replaced)."""
    src_dir, dst_dir = (TARGET_DIR, MEAS_DIR) if kind == "target" else (MEAS_DIR, TARGET_DIR)
    name = _plain_name(name)
    src = os.path.join(src_dir, name)
    if not os.path.isfile(src):
        raise ValueError(f"{name} isn't in the {kind} folder any more.")
    os.makedirs(dst_dir, exist_ok=True)
    if not _free_or_same(os.path.join(dst_dir, name), textfile.read(src)):
        other = "Measurement" if kind == "target" else "Target"
        raise ValueError(f"{other} already has a different “{name}”: remove or rename one of them first.")
    _in_use_retry(os.replace, src, os.path.join(dst_dir, name))
    return name
