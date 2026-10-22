"""Backing up everything of yours in AutoEQ Studio as one .zip, and restoring it (Settings › Backup): for a new PC,
a reinstall, or before trying something.

In the backup:
    data/settings.json             the devices, profiles, choices, hotkey, Online / Offline
    data/eq/settings.json, history.json, listen.json
                                   Make an EQ's settings, History, EQs to compare
    inputs/target/, inputs/measurement/, inputs/sources.json, output/, presets/
                                   your targets and measurements (and where each came from), saved EQs and reports,
                                   presets. (The names a backup has always had: one made before the Targets,
                                   Measurements, Saved EQs and Presets folders restores into them, and one made now
                                   into an older copy.)
    apo-profiles/                  the profiles' EQ files (Equalizer APO's "AutoEQ Studio\\profiles" folder)
    backup.json                    what it is: when it was made, how many files
Not in it: downloads\\ (curves from the online databases: downloaded again when used), the database lists and the
logs, the Python environment.

Restoring first keeps a backup of how things are now (data\\backups\\), then puts the backup's files in place:
files with the same name are replaced, nothing else is deleted. The app starts again after it (ui\\app.py), since
everything it has loaded changed. No Qt here.
"""
import json
import os
import time
import zipfile

import paths

FORMAT = 1
TRIAL_FILE = "_trying.txt"  # (switcher.core's: a trial's file, never backed up)
DATA_FILES = ["settings.json", "eq/settings.json", "eq/history.json", "eq/listen.json"]
FOLDERS = ["inputs", "presets", "output"]
PROFILES = "apo-profiles"
SOURCES = "inputs/sources.json"


def _dirs():
    """(name in a backup, the folder it's in on this PC) for your files: asked each time (the folder can change)."""
    return [("inputs/target", paths.TARGETS), ("inputs/measurement", paths.MEASUREMENTS), ("output", paths.SAVED_EQS),
            ("presets", paths.PRESETS)]


def _dest(name):
    """Where a backup's file of yours goes on this PC (None: not one of them)."""
    if name == SOURCES:
        return paths.SOURCES
    for arc, folder in _dirs():
        if name.startswith(arc + "/"):
            return os.path.join(folder, *name[len(arc) + 1:].split("/"))
    return None


def _files(apo_profiles):
    """(name in the backup, the file on this PC) for everything that's there now."""
    out = [("data/" + f, os.path.join(paths.DATA, *f.split("/"))) for f in DATA_FILES]
    for arc, base in _dirs():
        for d, _subs, names in os.walk(base):
            for n in names:
                p = os.path.join(d, n)
                out.append((arc + "/" + os.path.relpath(p, base).replace(os.sep, "/"), p))
    out.append((SOURCES, paths.SOURCES))
    if apo_profiles and os.path.isdir(apo_profiles):
        out += [(PROFILES + "/" + n, os.path.join(apo_profiles, n)) for n in sorted(os.listdir(apo_profiles))
                if n.lower().endswith(".txt") and n.lower() != TRIAL_FILE]  # (not a trial's file; "_Aux.txt" is a
    #                                                                             profile: safe_name's reserved names)
    return [(a, p) for a, p in out if os.path.isfile(p)]


def make(dest, apo_profiles):
    """Write a backup to dest (.zip). Returns its manifest. Raises OSError."""
    files = _files(apo_profiles)
    info = {"app": "AutoEQ Studio", "format": FORMAT, "made": time.strftime("%Y-%m-%d %H:%M"),
            "files": len(files), "profiles": sum(a.startswith(PROFILES + "/") for a, _ in files)}
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    tmp = dest + ".part"
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("backup.json", json.dumps(info, indent=1))
            for arc, p in files:
                z.write(p, arc)
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return info


def _safe(name):
    """A name from a backup that may be restored: one of the parts above, never outside them."""
    parts = name.split("/")
    if not name or name.endswith("/") or name.startswith("/") or ".." in parts or ":" in name or "\\" in name:
        return False
    if name.startswith("data/"):
        return name[5:] in DATA_FILES
    return parts[0] in FOLDERS + [PROFILES] and len(parts) >= 2 and all(parts)


def read(src):
    """A backup's manifest, checked. Raises ValueError (not one of AutoEQ Studio's backups) or OSError."""
    try:
        with zipfile.ZipFile(src) as z:
            info = json.loads(z.read("backup.json").decode("utf-8"))
            names = z.namelist()
    except (zipfile.BadZipFile, KeyError, ValueError, UnicodeDecodeError):
        raise ValueError("That file isn't one of AutoEQ Studio's backups.") from None
    if not isinstance(info, dict) or info.get("app") != "AutoEQ Studio" or not isinstance(info.get("format"), int):
        raise ValueError("That file isn't one of AutoEQ Studio's backups.")
    if info["format"] > FORMAT:
        raise ValueError("That backup was made by a newer AutoEQ Studio: update this one first.")
    info["names"] = [n for n in names if _safe(n)]
    return info


def restore(src, apo_profiles, keep_dir=None):
    """Put a backup's files in place, after keeping how things are now. Returns {"files", "profiles", "kept",
    "skipped"}. Raises ValueError (not a backup) or OSError."""
    info = read(src)
    keep_dir = keep_dir or os.path.join(paths.DATA, "backups")
    kept = os.path.join(keep_dir, time.strftime("before restore %Y-%m-%d %H%M%S.zip"))
    make(kept, apo_profiles)
    done, profiles, skipped = 0, 0, []
    here = paths.chosen_folder()  # (your files go into this PC's folders: its settings keep pointing there)
    with zipfile.ZipFile(src) as z:
        for name in info["names"]:
            parts = name.split("/")
            if parts[0] == "data":
                dest = os.path.join(paths.DATA, *parts[1:])
            elif parts[0] == PROFILES:
                if not apo_profiles:
                    skipped.append(name)
                    continue
                dest = os.path.join(apo_profiles, *parts[1:])
            else:
                dest = _dest(name)
                if not dest:  # (not one of the folders: an older app's file, say)
                    skipped.append(name)
                    continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            tmp = dest + ".restoring"
            with z.open(name) as fh:
                raw = fh.read()
            if name == "data/settings.json":
                raw = _folder_here(raw, here)
            with open(tmp, "wb") as out:
                out.write(raw)
            os.replace(tmp, dest)
            done += 1
            profiles += parts[0] == PROFILES
    return {"files": done, "profiles": profiles, "kept": kept, "skipped": skipped}


def _folder_here(raw, here):
    """A backup's main settings with this PC's folder for your files (where restore put them), not the backup's."""
    try:
        s = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return raw
    if not isinstance(s, dict):
        return raw
    s.pop(paths.FILES_KEY, None)
    if here:
        s[paths.FILES_KEY] = here
    return json.dumps(s, indent=1).encode("utf-8")


def default_name():
    return time.strftime("AutoEQ Studio backup %Y-%m-%d.zip")
