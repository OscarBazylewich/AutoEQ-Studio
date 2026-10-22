"""Where the EQ part's things are: the app's own paths.py says (your files in Documents\\AutoEQ Studio or the folder
you chose; the app's data, downloads and caches where it keeps them; paths.py's docstring has the whole picture).
The program's data is next to these modules (app\\eq\\: rigdata.json, rigmap.json, vendor\\).

    TARGET_DIR, MEAS_DIR     your targets and measurements (Targets, Measurements: what Make an EQ uses)
    OUTPUT_DIR               saved EQ files and reports (Saved EQs)
    PRESET_DIR               saved settings presets (Presets)
    SOURCES_PATH             which database each of your files came from (for its rig)
    DOWNLOAD_DIR, CACHE      curves downloaded from the online databases; the database lists and other caches
    SAMPLES_DIR              example curves to try (the program's)
    DATA                     the EQ part's own files: settings.json, history.json, listen.json
    LOG_PATH                 AutoEQ Studio's log (shared with the rest of the app)

Taken when the EQ part loads: a folder chosen later takes effect when the app starts again (userfiles.py restarts it).
The maths libraries' thread counts are set by eq\\__init__.py, before numpy loads.
"""
import os

import paths as _studio  # (the app's own paths.py: where things are)

APP = os.path.dirname(os.path.abspath(__file__))           # (app\eq: the EQ part's program and data)
ROOT = _studio.ROOT  # (your files' folder)
PROGRAM = _studio.PROGRAM  # (the program's own folder)
STUDIO_DATA = _studio.DATA
DATA = os.path.join(STUDIO_DATA, "eq")
CACHE = _studio.CACHE
TARGET_DIR = _studio.TARGETS
MEAS_DIR = _studio.MEASUREMENTS
OUTPUT_DIR = _studio.SAVED_EQS
PRESET_DIR = _studio.PRESETS
SOURCES_PATH = _studio.SOURCES
DOWNLOAD_DIR = _studio.DOWNLOADS
SAMPLES_DIR = _studio.SAMPLES
SETTINGS_PATH = os.path.join(DATA, "settings.json")
LOG_PATH = _studio.LOG
PREVIOUS_LOG_PATH = _studio.LOG + ".old"

os.makedirs(CACHE, exist_ok=True)
