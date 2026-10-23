"""Where the EQ part keeps its files (eq\\paths.py): in AutoEQ Studio's folders (its own in data\\eq\\; your Targets,
Measurements, Saved EQs and Presets), and the program's data (rigdata.json, squiglink's code) next to its modules.
Moved from eq_checks.py's studio_checks.

Checked on this session's own folders, in this process: tests\\conftest.py set AUTOEQSTUDIO_ROOT to the session's
studio and AUTOEQSTUDIO_DATA to its data folder before anything of the app was imported (as the old check's use_copy
did for its copy), and the folders are fixed when eq.paths is first imported."""
import os

from eq import paths
from helpers import session

COVERS_FILES = ("app/eq/rigdata.json", "app/eq/vendor/squiglink/equalizer.js")  # (looked for next to eq.paths)


def same(a, b):
    """The same place: both spelled the long way (os.path.realpath on both sides), never compared as text."""
    return os.path.realpath(a) == os.path.realpath(b)


def test_eq_files_in_the_studio_folders(check):
    top = session.SESSION.studio  # (the old check's copy: here the session's studio)
    # was eq_checks.py:1252
    check("studio: the EQ part's files are in AutoEQ Studio's folders (data\\eq\\; your Targets, Measurements, Saved "
          "EQs, Presets), its data next to it",
          same(paths.DATA, os.path.join(top, "data", "eq")) and same(paths.TARGET_DIR, os.path.join(top, "Targets"))
          and same(paths.MEAS_DIR, os.path.join(top, "Measurements")) and same(paths.OUTPUT_DIR, os.path.join(top, "Saved EQs"))
          and same(paths.PRESET_DIR, os.path.join(top, "Presets"))
          and same(paths.SOURCES_PATH, os.path.join(top, "data", "eq", "sources.json"))
          and os.path.isfile(os.path.join(paths.APP, "rigdata.json"))
          and os.path.isfile(os.path.join(paths.APP, "vendor", "squiglink", "equalizer.js")), (paths.DATA, paths.APP))
