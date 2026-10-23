"""The zips for testers and friends (app\\tools\\make_share_zip.py), made in the test folder: the share zip holds none
of the user's files and every module of the app, and the program loads from the unpacked copy (its data beside it,
your files in Documents\\AutoEQ Studio, a stand-in here); the ready-to-run zip's own Python holds what the app needs
(Python, its launcher named AutoEQ Studio, Qt's widgets, numpy, SciPy, the sound card's library) and not pip or Qt's
QML, and its launcher (.bat) has CRLF line endings and guards against too long a folder. Moved from selftest.py's
zip_checks."""
import datetime
import os
import zipfile

from helpers import paths as project
from helpers import subproc

# (for app\tools\relevant_tests.py: the tools these tests import through helpers.paths.import_tool, what the
# unpacked copy loads (run as text), and the files the zips are made from)
COVERS = ("make_share_zip", "brand_exe", "ui.app", "eq.service", "eq.paths")
COVERS_FILES = ("app/**", "samples/**", "AutoEQ Studio.bat", "README.txt", "app/tools/TESTING.txt",
                "app/tools/START HERE.txt", "app/tools/sample_sources.json")


def _norm(p):
    return os.path.normcase(os.path.realpath(p))


def test_share_zip(tmp_path, check):
    # (the database lists it takes for the first start come from paths.CACHE: here the session's small lists)
    mz = project.import_tool("make_share_zip")
    top = str(tmp_path)
    app_dir, root = project.PROJECT_APP, project.PROJECT
    entries = mz.plan(datetime.datetime(2026, 1, 1))
    names = [a for a, _ in entries]
    user = [a for a in names if os.path.basename(a) in mz.NEVER or a.split("/")[1] in ("output", "downloads", "presets")
            or "/.venv/" in a or "/tools/" in a]
    code_files = {os.path.relpath(os.path.join(d, n), root).replace(os.sep, "/") for d, subs, ns in os.walk(app_dir)
                  for n in ns if n.endswith(".py") and "__pycache__" not in d and os.path.join(app_dir, "tools") not in d}
    missing = sorted(f for f in code_files if f"{mz.TOP}/{f}" not in names)
    out = os.path.join(top, "share.zip")
    mz.write(out, entries)
    with zipfile.ZipFile(out) as z:
        z.extractall(os.path.join(top, "unzipped"))
    app = os.path.join(top, "unzipped", mz.TOP, "app")
    # (the unpacked copy as on a tester's PC: no test folders of its own; Documents a stand-in, never the real one)
    env = {"AUTOEQSTUDIO_DATA": None, "AUTOEQSTUDIO_ROOT": None, "AUTOEQSTUDIO_DOCUMENTS": os.path.join(top, "docs")}
    run = subproc.run_python("import sys; sys.path.insert(0, sys.argv[1]); import ui.app, eq.service, "
                             "eq.paths as p; print(p.ROOT); print(p.STUDIO_DATA)", app, env=env, timeout=120)
    where = [_norm(line) for line in run.stdout.strip().splitlines()[-2:]]
    # was selftest.py:1008
    check("share zip: none of the user's files, every module of the app; it loads from the unpacked copy, its data "
          "beside it and your files in Documents\\AutoEQ Studio", not user and not missing and run.returncode == 0
          and where == [_norm(os.path.join(top, "docs", "AutoEQ Studio")), _norm(os.path.join(os.path.dirname(app), "data"))],
          (user[:3], missing[:3], where, run.stderr[-300:]))


def test_ready_to_run_zip(qapp, check):
    # (the ready-to-run zip's own Python: what it holds, not made here (120 MB; --check-runtime tests one unpacked).
    # Listing it makes the named launcher, which draws the app's icon: the tests' QApplication (qapp) is made first,
    # or the drawing would make a plain one and no window could be made in this process afterwards)
    project.import_tool("brand_exe")  # (make_share_zip.launcher imports it)
    mz = project.import_tool("make_share_zip")
    rt = [a for a, _ in mz.runtime_entries()]
    has = lambda end: any(a.endswith(end) for a in rt)
    bat = mz.READY_BAT
    with open(os.path.join(project.TOOLS, "TESTING.txt"), encoding="utf-8") as fh:
        testing = fh.read()
    # was selftest.py:1017
    check("ready-to-run zip: its Python (python, pythonw, the named launcher, Qt's widgets, numpy, SciPy, the sound "
          "card's library) without pip or Qt's QML; its launcher CRLF and guarding against too long a folder",
          all(has(e) for e in ("/runtime/python.exe", "/runtime/pythonw.exe", "/runtime/AutoEQ Studio.exe",
                               "/PySide6/QtWidgets.pyd", "/numpy/__init__.py", "/scipy/__init__.py",
                               "libportaudio64bit.dll"))
          and not any("/site-packages/pip/" in a or "/PySide6/qml/" in a for a in rt)
          and bat.count(b"\n") == bat.count(b"\r\n") and b"goto :toolong" in bat
          and "Nothing needs installing" in mz.ready_testing(testing),
          len(rt))
