"""The project's own places (never the session's): the folder holding pytest.ini (a worktree's own folder in a
worktree), its app\\ folder, the tools, the samples, the tests and their fixtures; the sample target and device the
EQ checks use; and import_tool(), the one way a test imports one of app\\tools' scripts.

Tests read the project's own files (sources, samples, tools) through these names, never by a path worked out from
the test file's place.
"""
import importlib
import os
import sys

COVERS_FILES = ("samples/**",)  # (for app\tools\relevant_tests.py: a change to the samples concerns these tests)

TESTS = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
PROJECT = os.path.dirname(TESTS)
PROJECT_APP = os.path.join(PROJECT, "app")
TOOLS = os.path.join(PROJECT_APP, "tools")
SAMPLES = os.path.join(PROJECT, "samples")
FIXTURES = os.path.join(TESTS, "fixtures")
DB_FIXTURES = os.path.join(FIXTURES, "db")
SAMPLE_TARGET = "Diffuse field 5128 -1dB per octave (AutoEq).csv"
SAMPLE_DEVICE = "Truthear GATe - B&K 5128, 10 seatings"


def _inside(path, folder):
    path, folder = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(folder))
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


def import_tool(name):
    """app\\tools\\<name>.py imported (make_share_zip, make_installer, brand_exe, a11y), with sys.path put back as it
    was afterwards: make_share_zip.py and make_installer.py put the project's app\\ first on the path when they're
    imported, and the app's modules must still come from the session's copy (tests\\conftest.py has loaded `paths`
    from it already). Raises ImportError if any app module was loaded from the project's app\\ (outside app\\tools)
    while it imported."""
    saved = list(sys.path)
    before = set(sys.modules)
    try:
        if TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
        module = importlib.import_module(name)
    finally:
        sys.path[:] = saved
    wrong = sorted(m for m in set(sys.modules) - before
                   if getattr(sys.modules[m], "__file__", None) and _inside(sys.modules[m].__file__, PROJECT_APP)
                   and not _inside(sys.modules[m].__file__, TOOLS))
    if wrong:
        raise ImportError(f"importing {name} loaded app modules from the project's app folder, not the test copy: "
                          f"{', '.join(wrong)}")
    return module
