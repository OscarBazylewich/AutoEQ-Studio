"""The project's own files: no control characters in its text files (a \\b or \\f a shell wrote as one) and CRLF line
endings in its .bat files (Windows' cmd misreads them otherwise); and the deepest file of the Python environment
setup.bat makes fits under Windows' 260-character limit below a main folder up to 80 characters long. Moved from
selftest.py's file_checks (its third check, about Claude's notes, is tests\\tools\\test_notes.py)."""
import os

from helpers import capabilities
from helpers import paths as project

# (for app\tools\relevant_tests.py: the main folder's own files, every .bat file, app\ and tests\)
COVERS_FILES = ("*", "**/*.bat", "app/**", "tests/**")

DEEPEST = ("setup: the deepest package file ({deepest} characters below the main folder) fits below an 80-character "
           "main folder")


def _project_files():
    """The program's files only: the main folder's own and those in app\\ (not the user's inputs, output, downloads,
    releases), and now the tests' too (tests\\: new files follow the same rules), but not their data
    (tests\\fixtures\\: test files may hold any bytes, e.g. a curve saved as UTF-16 like the one in samples\\)."""
    root = project.PROJECT
    files = [os.path.join(root, n) for n in os.listdir(root) if os.path.isfile(os.path.join(root, n))]
    fixtures = os.path.normcase(os.path.realpath(project.FIXTURES))
    for top in (project.PROJECT_APP, project.TESTS):
        for d, subs, names in os.walk(top):
            subs[:] = [s for s in subs if s != "__pycache__"
                       and os.path.normcase(os.path.realpath(os.path.join(d, s))) != fixtures]
            files += [os.path.join(d, n) for n in names]
    return files


def test_no_control_characters_and_bat_files_crlf(check):
    bad = []
    for p in _project_files():
        n = os.path.basename(p)
        if n.endswith((".py", ".md", ".txt", ".bat")):
            with open(p, "rb") as fh:
                raw = fh.read()
            rel = os.path.relpath(p, project.PROJECT)
            if any(b < 32 and b not in (9, 10, 13) for b in raw):
                bad.append(rel + ": a control character (a \\b or \\f written as one?)")
            if n.endswith(".bat") and raw.count(b"\n") != raw.count(b"\r\n"):
                bad.append(rel + ": not CRLF")
    # was selftest.py:924
    check("files: no control characters; the .bat files have CRLF line endings", not bad, bad)


def test_deepest_package_file_fits(check):
    # ((review #1) setup.bat moves the environment out of a main folder longer than 80 characters; the deepest file in
    # it must fit under Windows' 260-character limit below such a folder. Measured in the environment running the
    # tests, from the folder holding it (as the old check measured .venv from the main folder): from a worktree, the
    # main folder's .venv measured from the worktree would gain ..\..\..\ in front)
    venv = capabilities.require(capabilities.project_venv, check, DEEPEST)
    top = os.path.dirname(os.path.normpath(venv))
    deepest = max((len(os.path.relpath(os.path.join(d, n), top)) for d, _s, ns in os.walk(venv) for n in ns), default=0)
    # was selftest.py:944
    check(f"setup: the deepest package file ({deepest} characters below the main folder) fits below an 80-character "
          "main folder", 81 + deepest <= 259, deepest)
