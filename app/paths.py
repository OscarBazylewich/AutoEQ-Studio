"""Where AutoEQ Studio's files are: yours, the app's own, the program, and Equalizer APO's config folder (where APO
reads its configuration, and where AutoEQ Studio keeps the profiles and its per-device file).

Your files (what you make and keep) are where Windows apps keep a user's files: Documents\\AutoEQ Studio (as Room EQ
Wizard's Documents\\REW, Audacity's or REAPER's), each kind in a folder named for it: Targets, Measurements (what Make
an EQ uses), Saved EQs (EQ files and reports), Presets. Settings > Your files chooses another folder (settings.json's
"files_folder"; userfiles.py moves them). Never in the program's folder: an update or a new copy would lose them.

The app's own things:
- installed (the installer's build leaves app\\installed.txt): settings, History, the record of where each of your
  files came from, the log in AppData\\Roaming\\AutoEQ Studio; what can be fetched again (downloaded curves, the
  database lists, caches) in AppData\\Local\\AutoEQ Studio. The program's folder is replaced by each update and
  removed by an uninstall.
- run from its own folder (unzipped, or the project's): in that folder (data\\, downloads\\), as a portable app keeps
  them.

AUTOEQSTUDIO_APO_CONFIG points the app at another APO config folder: the self-test and test copies use a fake one, so
the real one is never written while the app is being worked on. AUTOEQSTUDIO_DATA does the same for the data folder
(and your files' folder with it, as data\\files), AUTOEQSTUDIO_ROOT for your files' folder (and data\\ in it unless
AUTOEQSTUDIO_DATA is given too). A test never reaches your real Documents.
"""
import json
import os
import winreg

APP = os.path.dirname(os.path.abspath(__file__))
PROGRAM = os.path.dirname(APP)  # (the program's own folder)
INSTALLED = os.path.isfile(os.path.join(APP, "installed.txt"))
# (make_installer.py --test-build: its own folders, running channel and mutex, and no Equalizer APO unless a test
# folder is given, so trying the installer never reaches the user's own app, settings or EQs)
TEST_BUILD = os.path.isfile(os.path.join(APP, "test-build.txt"))
NAME = "AutoEQ Studio (test)" if TEST_BUILD else "AutoEQ Studio"
VERSION = "1.0.18"  # (the one place it's set: the installer, Windows' list of apps and Settings read it from here)
FILES_KEY = "files_folder"  # (settings.json: the folder you chose for your files; none: DEFAULT_FILES)
# each kind of your files: its folder's name in your files' folder
TARGETS_NAME, MEASUREMENTS_NAME, SAVED_EQS_NAME, PRESETS_NAME = "Targets", "Measurements", "Saved EQs", "Presets"


def _documents():
    """Windows' Documents folder (it may be moved, e.g. into OneDrive: asked for, not assumed). AUTOEQSTUDIO_DOCUMENTS
    stands in for it in the self-test's installed checks (never the user's real Documents)."""
    if os.environ.get("AUTOEQSTUDIO_DOCUMENTS"):
        return os.environ["AUTOEQSTUDIO_DOCUMENTS"]
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]
    docs = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
    out = ctypes.c_wchar_p()
    try:
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(docs), 0, None, ctypes.byref(out)) == 0:
            return out.value
    except OSError:
        pass
    finally:
        ctypes.windll.ole32.CoTaskMemFree(out)
    return os.path.join(os.path.expanduser("~"), "Documents")


def chosen_folder():
    """The folder you chose for your files (Settings > Your files), or None."""
    try:
        with open(SETTINGS, encoding="utf-8") as fh:
            v = json.load(fh).get(FILES_KEY)
    except (OSError, ValueError, AttributeError):
        return None
    return v if isinstance(v, str) and v.strip() else None


def locate():
    """Work out where everything is: when this module loads, and again after your files' folder is chosen while the
    app runs (before the EQ part has loaded: its modules keep the folders they were given)."""
    global DATA, LOCAL, SETTINGS, LOG, DEFAULT_FILES, ROOT, TARGETS, MEASUREMENTS, SAVED_EQS, PRESETS, SOURCES, \
        CACHE, DOWNLOADS, SAMPLES
    env_root, env_data = os.environ.get("AUTOEQSTUDIO_ROOT"), os.environ.get("AUTOEQSTUDIO_DATA")
    if INSTALLED:
        data = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), NAME)
        local = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), NAME)
    else:
        data, local = os.path.join(PROGRAM, "data"), None
    DATA = env_data or (os.path.join(env_root, "data") if env_root else data)
    LOCAL = None if env_root or env_data else local  # (installed only: else in DATA and the program's folder)
    SETTINGS = os.path.join(DATA, "settings.json")
    LOG = os.path.join(DATA, "app.log")
    DEFAULT_FILES = os.path.join(_documents(), NAME)
    ROOT = env_root or (os.path.join(env_data, "files") if env_data else chosen_folder() or DEFAULT_FILES)
    TARGETS, MEASUREMENTS = os.path.join(ROOT, TARGETS_NAME), os.path.join(ROOT, MEASUREMENTS_NAME)
    SAVED_EQS, PRESETS = os.path.join(ROOT, SAVED_EQS_NAME), os.path.join(ROOT, PRESETS_NAME)
    SOURCES = os.path.join(DATA, "eq", "sources.json")  # (which database each of your files came from: its rig)
    CACHE = os.path.join(LOCAL, "cache") if LOCAL else os.path.join(DATA, "eq", "cache")
    DOWNLOADS = os.path.join(LOCAL or env_root or PROGRAM, "downloads")
    SAMPLES = os.path.join(env_root or PROGRAM, "samples")


locate()
SEED = os.path.join(PROGRAM, "first-start")  # (what a new copy puts in place: tools\make_share_zip.py, make_installer.py)


def first_start():
    """A new copy, or a new folder for your files: the sample IEM and target in Measurements and Targets when you
    have neither, so a first Run works at once, and the database lists when there are none, so searching works at
    once. Only what isn't there: nothing of yours is replaced."""
    import shutil
    if not os.path.isdir(SEED):
        return
    if not os.path.exists(TARGETS) and not os.path.exists(MEASUREMENTS):
        for name, dest in ((TARGETS_NAME, TARGETS), (MEASUREMENTS_NAME, MEASUREMENTS)):
            if os.path.isdir(os.path.join(SEED, name)):
                shutil.copytree(os.path.join(SEED, name), dest)
    if os.path.isfile(os.path.join(SEED, "sources.json")) and not os.path.exists(SOURCES):
        os.makedirs(os.path.dirname(SOURCES), exist_ok=True)
        shutil.copy2(os.path.join(SEED, "sources.json"), SOURCES)
    lists = os.path.join(SEED, "cache")
    for n in os.listdir(lists) if os.path.isdir(lists) else []:
        if not os.path.exists(os.path.join(CACHE, n)):
            os.makedirs(CACHE, exist_ok=True)
            shutil.copy2(os.path.join(lists, n), os.path.join(CACHE, n))


def old_app(name):
    """Where an app AutoEQ Studio took over from is: beside it (the same project folder), or in Downloads (where the
    user put them, 2026-10-08); never Downloads for a test copy (AUTOEQSTUDIO_ROOT) or an installed one (it starts
    fresh: the user's choice, 2026-10-11): they use only what's beside them."""
    beside = os.path.join(os.path.dirname(PROGRAM), name)
    if os.path.isdir(beside) or os.environ.get("AUTOEQSTUDIO_ROOT") or INSTALLED:
        return beside
    return os.path.join(os.path.expanduser("~"), "Downloads", name)


# AutoEQ Local: its saved EQs are where "Import" starts looking
AUTOEQ_OUTPUT = os.path.join(old_app("AutoEQ Local"), "output")
# EQ Switcher: its settings, brought over on the first start (its profiles are in APO's folder)
EQ_SWITCHER_SETTINGS = os.environ.get("AUTOEQSTUDIO_OLD_SETTINGS") or \
    os.path.join(old_app("EQ Switcher"), "data", "settings.json")
EQ_SWITCHER_FOLDER = "EQ Switcher"  # (its folder in APO's config folder)

APO_KEY = r"SOFTWARE\EqualizerAPO"
APO_DOWNLOAD = "https://sourceforge.net/projects/equalizerapo/"


def apo_folders():
    """(install folder, config folder) of Equalizer APO, or (None, None) when it isn't installed. Read from the keys
    APO's installer writes (the config folder can be moved, so it's read rather than assumed)."""
    over = os.environ.get("AUTOEQSTUDIO_APO_CONFIG")
    if over:
        return os.environ.get("AUTOEQSTUDIO_APO_INSTALL") or os.path.dirname(over), over
    if TEST_BUILD:  # (a test build without a test APO folder: as if APO weren't installed)
        return None, None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, APO_KEY) as k:
            install = winreg.QueryValueEx(k, "InstallPath")[0]
            try:
                config = winreg.QueryValueEx(k, "ConfigPath")[0]
            except OSError:
                config = os.path.join(install, "config")
    except OSError:
        return None, None
    return install, config
