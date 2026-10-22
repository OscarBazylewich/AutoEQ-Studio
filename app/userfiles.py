"""Your files' folder (paths.py: Documents\\AutoEQ Studio, or the one you chose in Settings > Your files): moving
your targets, measurements, saved EQs and presets into it from where older copies kept them, and to another folder
you choose. No Qt here: ui\\your_files.py asks you first.

Older copies kept them in the program's folder (inputs\\target, inputs\\measurement, output\\, presets\\), and the first
installer in Documents\\AutoEQ Studio with those names. A move never replaces a file: a different one with the same
name already there is kept beside it as "name (2)"; the same file isn't kept twice. The record of where each file came
from (inputs\\sources.json then; paths.SOURCES now) is merged, ours first.
"""
import filecmp
import os
import shutil

import paths
import textfile


def kinds(root):
    """Each kind of your files and its folder in root (as paths.locate() names them)."""
    return [(os.path.join(root, n)) for n in (paths.TARGETS_NAME, paths.MEASUREMENTS_NAME, paths.SAVED_EQS_NAME,
                                               paths.PRESETS_NAME)]


def _old_layout(base):
    return [os.path.join(base, "inputs", "target"), os.path.join(base, "inputs", "measurement"),
            os.path.join(base, "output"), os.path.join(base, "presets")]


def _has_files(folder):
    return any(names for _d, _s, names in os.walk(folder))


def same_folder(a, b):
    """One folder, also when reached by two paths (a mapped or subst drive, a junction)."""
    if os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b)):
        return True
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def old_places(bases=None):
    """[(old folder, its new folder)] that still hold files, and the old records of where they came from: where
    older copies kept your files (bases: the program's folder and Documents\\AutoEQ Studio). None for a test (it has
    its own folders) unless bases are given."""
    if bases is None:
        if os.environ.get("AUTOEQSTUDIO_ROOT") or os.environ.get("AUTOEQSTUDIO_DATA"):
            return [], []
        bases = [paths.PROGRAM, paths.DEFAULT_FILES, paths.ROOT]
    pairs, sources, seen = [], [], set()
    for base in bases:
        if os.path.normcase(os.path.abspath(base)) in seen:
            continue
        seen.add(os.path.normcase(os.path.abspath(base)))
        for old, new in zip(_old_layout(base), kinds(paths.ROOT)):
            if os.path.isdir(old) and _has_files(old) and not same_folder(old, new):
                pairs.append((old, new))
        rec = os.path.join(base, "inputs", "sources.json")
        if os.path.isfile(rec):
            sources.append(rec)
    return pairs, sources


def change_pairs(new_root):
    """[(your folder now, the same kind's folder in new_root)] that hold files: what a change of folder moves."""
    return [(old, new) for old, new in zip(kinds(paths.ROOT), kinds(new_root))
            if os.path.isdir(old) and _has_files(old) and not same_folder(old, new)]


def count(pairs):
    return sum(len(names) for old, _new in pairs for _d, _s, names in os.walk(old))


def _free(path):
    """path, or "name (2).ext", "(3)" … when that's taken."""
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(path):
        path, n = f"{stem} ({n}){ext}", n + 1
    return path


def move_tree(old, new):
    """Every file in old into new (its subfolders kept). Returns (moved, kept beside a different one of the same
    name). The old folders go when they're empty."""
    moved = renamed = 0
    for d, _subs, names in os.walk(old):
        for n in names:
            src = os.path.join(d, n)
            dest = os.path.join(new, os.path.relpath(src, old))
            if os.path.exists(dest):
                if os.path.samefile(src, dest):  # (the same file by another path: nothing to move, never removed)
                    continue
                if filecmp.cmp(src, dest, shallow=False):  # (already there: the old copy goes)
                    os.remove(src)
                    continue
                dest, renamed = _free(dest), renamed + 1
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(src, dest)
            moved += 1
    for d, _subs, _names in sorted(os.walk(old), key=lambda w: -len(w[0])):  # (deepest first)
        try:
            os.rmdir(d)
        except OSError:  # (not empty: something was left, e.g. a file in use)
            pass
    return moved, renamed


def merge_sources(old):
    """An old record of where your files came from, added to ours (ours first), then removed."""
    theirs, ours = textfile.read_json(old, {}), textfile.read_json(paths.SOURCES, {})
    if isinstance(theirs, dict) and isinstance(ours, dict):
        new = {k: v for k, v in theirs.items() if k not in ours}
        if new or not os.path.exists(paths.SOURCES):
            os.makedirs(os.path.dirname(paths.SOURCES), exist_ok=True)
            textfile.write_json(paths.SOURCES, dict(ours, **new), indent=1)
    os.remove(old)
    try:
        os.rmdir(os.path.dirname(old))  # (the old inputs folder, when that was all that was left)
    except OSError:
        pass


def move_all(pairs, sources=()):
    """Move them (old_places() or change_pairs()). Returns (moved, renamed)."""
    moved = renamed = 0
    for old, new in pairs:
        m, r = move_tree(old, new)
        moved, renamed = moved + m, renamed + r
    for rec in sources:
        merge_sources(rec)
    for old, _new in pairs:  # (an emptied inputs folder of the old layout)
        parent = os.path.dirname(old)
        if os.path.basename(parent).lower() == "inputs":
            try:
                os.rmdir(parent)
            except OSError:
                pass
    return moved, renamed


def problem_with(folder):
    """Why a folder can't hold your files (None: it can): not in the program's folder (an update or a new copy would
    lose them), not inside one of your files' own folders, and one this Windows user can write in."""
    folder = os.path.abspath(folder)
    if textfile.inside(folder, paths.PROGRAM):
        return "That's inside AutoEQ Studio's own folder: an update or a new copy would lose your files there."
    for k in kinds(paths.ROOT):
        if textfile.inside(folder, k):
            return f"That's inside your {os.path.basename(k)} folder: choose the folder that holds them, or another."
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, f".autoeq-studio-probe-{os.getpid()}")
        with open(probe, "w", encoding="utf-8"):
            pass
        os.remove(probe)
    except OSError as e:
        return f"AutoEQ Studio can't write there ({e.strerror or e})."
    return None
