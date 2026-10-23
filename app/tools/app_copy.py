"""A temporary copy of AutoEQ Studio for the tools that try the app on something other than your own files:
edge_probe.py (odd files and requests) and the README pictures (.claude\\notes\\readme-pictures\\shots.py, on this
PC only). Moved unchanged from the old EQ checks (eq_checks.py, retired 2026-10-22: the tests in tests\\ have their
own copy, tests\\helpers\\session.py).

    base, top = make_copy()   # a new folder in TEMP: <base>\\AutoEQ Studio (top) holds the copy
    use_copy(top)             # this process works in it (call before the app's modules are imported)
    remove_copy(base)         # deleted again (True when it's gone)

The copy: the program (app\\ without its tools, Python's caches, .venv or data), the samples, the sample target in
Targets and the sample device's measurements in Measurements, and the database lists in data\\eq\\cache (AutoEQ
Studio's own once it has them, else AutoEQ Local's: read, never changed). Your own files, settings and Equalizer APO
are never used.
"""
import os
import shutil
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(TOOLS)
ROOT = os.path.dirname(APP)
SAMPLE_TARGET = os.path.join("targets", "Diffuse field 5128 -1dB per octave (AutoEq).csv")
SAMPLE_DEVICE = os.path.join("measurements", "Truthear GATe - B&K 5128, 10 seatings")
# the database lists (8 MB, downloaded): AutoEQ Studio's own once it has them, else AutoEQ Local's (beside it, or in
# Downloads since 2026-10-08)
DB_LISTS = [os.path.join(ROOT, "data", "eq", "cache"), os.path.join(os.path.dirname(ROOT), "AutoEQ Local", "data", "cache"),
            os.path.join(os.path.expanduser("~"), "Downloads", "AutoEQ Local", "data", "cache")]


def make_copy():
    base = tempfile.mkdtemp(prefix="aeqstudio-eqchecks-")
    top = os.path.join(base, "AutoEQ Studio")
    shutil.copytree(APP, os.path.join(top, "app"), ignore=shutil.ignore_patterns("__pycache__", "tools", ".venv", "data"))
    shutil.copytree(os.path.join(ROOT, "samples"), os.path.join(top, "samples"))
    t, m = os.path.join(top, "Targets"), os.path.join(top, "Measurements")
    os.makedirs(t)
    shutil.copy(os.path.join(ROOT, "samples", SAMPLE_TARGET), t)
    shutil.copytree(os.path.join(ROOT, "samples", SAMPLE_DEVICE), m)
    cache = os.path.join(top, "data", "eq", "cache")
    os.makedirs(cache)
    src = next((d for d in DB_LISTS if os.path.isfile(os.path.join(d, "databases.json"))), None)
    for n in ("databases.json", "squigsites.json"):
        if src and os.path.isfile(os.path.join(src, n)):
            shutil.copy(os.path.join(src, n), cache)
    return base, top


def use_copy(top):
    """This process works in the copy: eq.paths reads these when it's first imported."""
    os.environ.update(AUTOEQSTUDIO_ROOT=top, AUTOEQSTUDIO_DATA=os.path.join(top, "data"))
    sys.path.insert(0, os.path.join(top, "app"))


def remove_copy(base):
    """Delete a test copy, trying again for a few seconds while stopped processes let go of its files."""
    for _ in range(20):
        shutil.rmtree(base, ignore_errors=True)
        if not os.path.exists(base):
            return True
        time.sleep(0.3)
    return False
