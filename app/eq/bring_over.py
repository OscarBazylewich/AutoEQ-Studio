"""Bringing your AutoEQ Local files into AutoEQ Studio, once: its settings, History, EQs to compare and database lists
(data\\), your targets and measurements (its inputs\\target and inputs\\measurement: into Targets and Measurements),
saved EQs (output\\: into Saved EQs), presets and downloaded curves.

Copied, never moved: AutoEQ Local keeps working as it was. Only when AutoEQ Studio's EQ part has no settings of its
own yet (its first use), so nothing of AutoEQ Studio's is replaced; a file already there is kept. Left behind: the
logs, and the rig builds' download cache (data\\cache\\rig-build: for AutoEQ Local's build tools). timing.json comes
along: it's how long runs took on this PC, for the time estimates.
"""
import os
import shutil

from . import paths
import paths as studio_paths  # (the app's own: installed or not)
import textfile

CACHE_FILES = ["databases.json", "squigsites.json", "library.json", "timing.json"]
# (AutoEQ Local's folder -> AutoEQ Studio's)
FOLDERS = [(r"inputs\target", paths.TARGET_DIR), (r"inputs\measurement", paths.MEAS_DIR), ("output", paths.OUTPUT_DIR),
           ("presets", paths.PRESET_DIR), ("downloads", paths.DOWNLOAD_DIR)]


def default_source():
    """AutoEQ Local's folder: beside AutoEQ Studio (the same project folder), else in Downloads (where the user keeps
    it since 2026-10-08; never for a test copy, AUTOEQSTUDIO_ROOT); None without its settings, and when installed
    (an installed copy starts fresh: the user's choice, 2026-10-11)."""
    if studio_paths.INSTALLED:
        return None
    p = studio_paths.old_app("AutoEQ Local")  # (beside the program, not your files' folder: review 2)
    return p if os.path.isfile(os.path.join(p, "data", "settings.json")) else None


def needed():
    """Is there something to bring (AutoEQ Local beside us) and nothing of ours yet? Never when only the data folder
    is moved (AUTOEQSTUDIO_DATA without AUTOEQSTUDIO_ROOT, a test): the files would land in the real main folder."""
    if os.environ.get("AUTOEQSTUDIO_DATA") and not os.environ.get("AUTOEQSTUDIO_ROOT"):
        return False
    return bool(default_source()) and not os.path.exists(paths.SETTINGS_PATH)


def _copy_file(src, dst, done):
    if os.path.isfile(src) and not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        done.append(dst)


def _merge_sources(src, dst, done):
    """AutoEQ Local's inputs\\sources.json (the database each file came from, for its rig): its records added for the
    files AutoEQ Studio has no record of (a share zip's copy has its samples' already)."""
    theirs, ours = textfile.read_json(src, {}), textfile.read_json(dst, {})
    if not isinstance(theirs, dict) or not isinstance(ours, dict):
        return
    new = {k: v for k, v in theirs.items() if k not in ours}
    if new:
        textfile.write_json(dst, dict(ours, **new), indent=1)
        done.append(dst)


def bring_over(source=None):
    """Copy AutoEQ Local's files from source (its main folder; default_source() when None). Returns the files
    copied (none when there's nothing to bring or AutoEQ Studio has its own settings already)."""
    source = source or default_source()
    if not source or os.path.exists(paths.SETTINGS_PATH):
        return []
    done = []
    data = os.path.join(source, "data")
    for n in CACHE_FILES:
        _copy_file(os.path.join(data, "cache", n), os.path.join(paths.CACHE, n), done)
    for name, dst_root in FOLDERS:
        src_root = os.path.join(source, name)
        for d, _subs, names in os.walk(src_root):
            for n in names:
                src = os.path.join(d, n)
                _copy_file(src, os.path.join(dst_root, os.path.relpath(src, src_root)), done)
    theirs = os.path.join(source, "inputs", "sources.json")  # (where AutoEQ Local's files came from: added to ours)
    if os.path.isfile(theirs):
        if os.path.exists(paths.SOURCES_PATH):
            _merge_sources(theirs, paths.SOURCES_PATH, done)
        else:
            _copy_file(theirs, paths.SOURCES_PATH, done)
    # the settings last: they mark it done (a bring-over stopped halfway is finished on the next start)
    for n in ("history.json", "listen.json", "settings.json"):
        _copy_file(os.path.join(data, n), os.path.join(paths.DATA, n), done)
    return done
