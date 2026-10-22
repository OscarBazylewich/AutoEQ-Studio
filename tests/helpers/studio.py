"""The session's "your files" and the EQ part's data (the studio: helpers.session made it).

target_path(), measurement_paths()  the sample target and the sample device's 10 seatings in the studio's Targets and
                                    Measurements: always these files by name, never "whatever is in Measurements"
install_lists()                     the small database lists (tests\\fixtures\\db) put in, fresh
write_eq_settings(values)           the EQ part's settings file: This PC's search on the studio's samples, plus values
reset(settings=None)                the studio back to new (what each test file of tests\\eq and tests\\eq_screen
                                    starts from)
"""
import os
import shutil
import sys
import time

from helpers import paths, session

COVERS_FILES = ("samples/**",)  # (for app\tools\relevant_tests.py: a change to the samples concerns these tests)


def _studio():
    return session.SESSION.studio


def target_path() -> str:
    return os.path.join(_studio(), "Targets", paths.SAMPLE_TARGET)


def _device_files():
    folder = os.path.join(_studio(), "samples", "measurements", paths.SAMPLE_DEVICE)
    return sorted(n for n in os.listdir(folder) if os.path.isfile(os.path.join(folder, n)))


def measurement_paths() -> list[str]:
    return [os.path.join(_studio(), "Measurements", n) for n in _device_files()]


def install_lists():
    session.install_lists(os.path.join(session.SESSION.data, "eq", "cache"))


def write_eq_settings(values: dict):
    session.write_eq_settings(_studio(), values)


def _remove(path):
    """A file or folder deleted, trying again for two seconds while something lets go of it (a background load)."""
    for attempt in range(20):
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.1)


def _empty(folder):
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(folder):
        _remove(os.path.join(folder, name))


def reset(settings=None):
    """The studio as new: Targets and Measurements back to the sample target and device only; Saved EQs and Presets
    emptied; the EQ part's History, EQs to compare, file sources, This PC's list and learned run times removed; its
    settings file written again (settings, or none of your own), the database lists put back; then, when the EQ
    part is loaded, its caches emptied (helpers.eq.reset_caches)."""
    studio, samples = _studio(), os.path.join(_studio(), "samples")
    _empty(os.path.join(studio, "Targets"))
    shutil.copy(os.path.join(samples, "targets", paths.SAMPLE_TARGET), os.path.join(studio, "Targets"))
    _empty(os.path.join(studio, "Measurements"))
    for name in _device_files():
        shutil.copy(os.path.join(samples, "measurements", paths.SAMPLE_DEVICE, name), os.path.join(studio, "Measurements"))
    for folder in ("Saved EQs", "Presets"):
        if os.path.isdir(os.path.join(studio, folder)):
            _empty(os.path.join(studio, folder))
    eq_data = os.path.join(session.SESSION.data, "eq")
    # (timing.json too, which the plan doesn't name: the run-time estimate learned from earlier runs would otherwise
    # differ from file to file)
    for rel in ("history.json", "listen.json", "sources.json", r"cache\library.json", r"cache\timing.json"):
        _remove(os.path.join(eq_data, rel))
    write_eq_settings(settings or {})
    install_lists()
    if "eq" in sys.modules:
        from helpers import eq
        eq.reset_caches()
