"""Makes a clean zip of AutoEQ Studio to give to other people (run by "Make share zip.bat" in the main folder).
(AutoEQ Local's app\\tools\\make_share_zip.py, for this app.)

In the zip, under one "AutoEQ Studio" folder:
  AutoEQ Studio.bat, README.txt and TESTING.txt (the testers' checklist, from this folder)
  app\\          the program (without this tools folder and Python's caches), with VERSION.txt saying when it was made
  samples\\      the sample curves
  first-start\\  what the first start puts in place (paths.first_start): one sample IEM and target in your Targets
                and Measurements folders (Documents\\AutoEQ Studio), so a first Run works straight away, where each came
                from (sources.json), and the lists of online databases (cache\\), so searching works at once (not your
                library or timings)
Never in it: your settings, History, EQs to compare, measurements, downloads, output, logs, profiles, or the Python
environment (.venv), which setup.bat makes on each PC. It's written to releases\\ in the main folder, and it stops
before writing when the self-test fails.

--use (no launcher uses it now: "Make zip for friends.bat" runs make_installer.py --zip, whose zip has the installer
and READ ME FIRST.txt): the ready-to-run zip for people who just use it, not testers: START HERE.txt
(from this folder) instead of TESTING.txt, a dated name and version, no "test build".

--ready (Make ready-to-run zip.bat): the same with its own Python in runtime\\ (this PC's, copied: Python 3.14 and
the packages from .venv, without pip, the tools for working on the app (app\\requirements-dev.txt's: Ruff, pytest and
what they need) and the parts of Qt the app never loads), so testers unzip and double-click
AutoEQ Studio.bat: no Python to install, nothing downloaded. About 150 MB. Its launcher starts runtime\\AutoEQ
Studio.exe (a copy of pythonw.exe: Task Manager names it); its TESTING.txt says so. --check-runtime FOLDER checks an
unpacked one's Python, to be sure nothing the app needs was left out: alone, it imports every module of the app;
then the whole self-test (every test) runs with it, pytest lent from .venv for that one run (check_runtime()).
"""
import datetime
import os
import re
import subprocess
import sys
import zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(TOOLS)
ROOT = os.path.dirname(APP)
TOP = "AutoEQ Studio"
sys.path.insert(0, APP)
import paths  # noqa: E402

LAUNCHERS = ["AutoEQ Studio.bat", "README.txt"]
# ready to go on first start: an IEM measured on a B&K 5128 and a target for that rig
PRELOAD = {"target": [r"samples\targets\Diffuse field 5128 -1dB per octave (AutoEq).csv"],
           "measurement": [r"samples\measurements\Truthear GATe - B&K 5128, 10 seatings"]}
DB_LISTS = ["databases.json", "squigsites.json"]  # (not library.json: a list of your own files; not timing.json)
NEVER = {"settings.json", "history.json", "listen.json", "library.json", "timing.json", "switcher.json", "app.log",
         "app.log.old", "setup.log", "requirements.installed"}


def files_under(folder):
    for d, subs, names in os.walk(folder):
        subs[:] = [s for s in subs if s not in ("__pycache__", ".venv", "data")]  # (never a Python environment or logs)
        for n in names:
            if not n.endswith((".pyc", ".pyo")):
                yield os.path.join(d, n)


def selftest():
    """The quick self-test must pass before anything goes out."""
    out = subprocess.run([sys.executable, os.path.join(TOOLS, "selftest.py"), "--quick"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if out.returncode:
        fails = [l for l in out.stdout.splitlines() if l.startswith("FAIL")]
        raise SystemExit("\n".join(fails or [out.stderr[-800:]]) + "\n\nNo zip made: the self-test fails.")


def plan(stamp):
    """What goes in the zip: [(path in the zip, source file or bytes)]."""
    entries = []

    def add(arc, src):
        if os.path.basename(arc) in NEVER:
            raise SystemExit(f"Refusing to put {arc} in the zip.")
        entries.append((TOP + "/" + arc.replace("\\", "/"), src))

    missing = [n for n in LAUNCHERS if not os.path.isfile(os.path.join(ROOT, n))]
    if missing:
        raise SystemExit(f"Missing: {', '.join(missing)}")
    for n in LAUNCHERS:
        add(n, os.path.join(ROOT, n))
    add("TESTING.txt", os.path.join(TOOLS, "TESTING.txt"))
    for p in files_under(APP):
        if os.path.commonpath([p, TOOLS]) != TOOLS:
            add(os.path.relpath(p, ROOT), p)
    add(r"app\VERSION.txt", f"test build {stamp:%Y-%m-%d %H:%M}\r\n".encode())
    for p in files_under(os.path.join(ROOT, "samples")):
        add(os.path.relpath(p, ROOT), p)
    for kind, items in PRELOAD.items():
        folder = {"target": paths.TARGETS_NAME, "measurement": paths.MEASUREMENTS_NAME}[kind]
        for item in items:
            src = os.path.join(ROOT, item)
            for p in ([src] if os.path.isfile(src) else sorted(files_under(src))):
                add(rf"first-start\{folder}\{os.path.basename(p)}", p)
    # (where the sample files came from, so their rigs show: a copy of AutoEQ Local's tools\sample_sources.json)
    sources = os.path.join(TOOLS, "sample_sources.json")
    if os.path.isfile(sources):
        add(r"first-start\sources.json", open(sources, "rb").read())
    for n in DB_LISTS:
        p = os.path.join(paths.CACHE, n)
        if os.path.isfile(p):
            add(rf"first-start\cache\{n}", p)
    return entries


# ---------------------------------------------------------------- the ready-to-run zip: its own Python
RUNTIME_FILES = ["python.exe", "pythonw.exe", "python3.dll", f"python{sys.version_info[0]}{sys.version_info[1]}.dll",
                 "vcruntime140.dll", "vcruntime140_1.dll", "LICENSE.txt"]
SKIP_LIB = {"test", "tests", "idlelib", "tkinter", "turtledemo", "ensurepip", "venv", "lib2to3", "__pycache__",
            "pip", "pip-" , "site-packages"}
# (Qt parts the app never loads: QML and Quick, Designer, its tools' programs, its translations, build files)
SKIP_QT = ("qml", "translations", "metatypes", "include", "typesystems", "glue", "scripts", "examples", "doc")
SKIP_QT_FILES = ("Qt6Quick", "Qt6Qml", "Qt6Designer", "Qt6Pdf", "Qt6Labs", "QtQuick", "QtQml", "QtDesigner",
                 "QtPdf", "Qt6ShaderTools", "QtShaderTools")


def _site_packages():
    import site
    return next(p for p in site.getsitepackages() if p.lower().endswith("site-packages"))


def _norm(name):
    """A package's name as pip compares them ("Pytest_Timeout" and "pytest-timeout" are one)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _listed(path):
    """The package names a requirements file lists (its comments and version numbers left out)."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = [line.strip() for line in fh]
    except OSError:
        return set()
    return {_norm(re.match(r"[A-Za-z0-9._-]*", line).group()) for line in lines if line and not line.startswith("#")}


def _with_needs(names, installed):
    """These packages and every installed package they need, in turn (their optional extras left out)."""
    todo, found = list(names), set()
    while todo:
        name = todo.pop()
        if name in found or name not in installed:
            continue
        found.add(name)
        for req in installed[name].requires or []:
            need, _, condition = req.partition(";")
            if "extra" not in condition:
                todo.append(_norm(re.match(r"[A-Za-z0-9._-]*", need.strip()).group()))
    return found


def development_files(sp=None):
    """Every file of the packages only working on the app needs, as full paths (os.path.normcase): those
    app\\requirements-dev.txt names (Ruff, pytest, pytest-timeout) and what they need, minus anything
    app\\requirements.txt's packages need (colorama stays: pyqtgraph needs it). runtime_entries() leaves them out, so
    no zip or installer carries them. Read from each package's own list of its files (importlib.metadata)."""
    from importlib import metadata
    sp = sp or _site_packages()
    installed = {}
    for dist in metadata.distributions(path=[sp]):
        installed.setdefault(_norm(dist.name or ""), dist)
    dev = (_with_needs(_listed(os.path.join(APP, "requirements-dev.txt")), installed)
           - _with_needs(_listed(os.path.join(APP, "requirements.txt")), installed))
    files = set()
    for name in sorted(dev):
        listed = installed[name].files
        if listed is None:  # (its RECORD is gone: its files can't be told apart, so nothing is made)
            raise SystemExit(f"Can't tell which files are {name}'s (its list of files is missing): no runtime made. "
                             f"Install it again: pip install --force-reinstall {name}")
        files |= {os.path.normcase(os.path.abspath(installed[name].locate_file(f))) for f in listed}
    return files


def launcher():
    """runtime\\AutoEQ Studio.exe: pythonw.exe with AutoEQ Studio's name, version and icon (brand_exe.py: Windows
    names a program by its description, so Task Manager's Startup apps said "Python")."""
    import tempfile
    import brand_exe
    with tempfile.TemporaryDirectory(prefix="aeqs-ico-") as tmp:
        ico = os.path.join(tmp, "AutoEQ Studio.ico")
        brand_exe.icon_file(ico)
        return brand_exe.launcher_bytes(os.path.join(sys.base_prefix, "pythonw.exe"), ico, paths.VERSION)


def runtime_entries():
    """[(path in the zip, source)] for runtime\\: Python itself and the app's packages."""
    base, out = sys.base_prefix, []
    for n in RUNTIME_FILES:
        if os.path.isfile(os.path.join(base, n)):
            out.append((f"{TOP}/runtime/{n}", os.path.join(base, n)))
    out.append((f"{TOP}/runtime/AutoEQ Studio.exe", launcher()))
    for top in ("DLLs", "Lib"):
        for d, subs, names in os.walk(os.path.join(base, top)):
            subs[:] = [s for s in subs if s not in SKIP_LIB and not s.startswith("pip-")]
            for n in names:
                if not n.endswith((".pyc", ".pyo")):
                    p = os.path.join(d, n)
                    out.append((f"{TOP}/runtime/" + os.path.relpath(p, base).replace(os.sep, "/"), p))
    sp = _site_packages()
    dev = development_files(sp)  # (pytest, Ruff and what they need: for working on the app, never shipped)
    for d, subs, names in os.walk(sp):
        rel = os.path.relpath(d, sp).replace(os.sep, "/")
        # (not the packages' own test suites, 23 MB and 1,180 files the app never loads, whose deepest compiled file
        # went past the installer's folder-length limit; nor ruff, the linter: review 2)
        subs[:] = [s for s in subs if s != "__pycache__" and not (rel == "." and (s == "pip" or s.startswith("pip-")))
                   and not (rel == "PySide6" and s in SKIP_QT) and s != "tests"
                   and not (rel == "." and (s == "ruff" or s.startswith("ruff-")))]
        for n in names:
            if n.endswith((".pyc", ".pyo")) or rel == "PySide6" and (n.endswith(".exe") or n.startswith(SKIP_QT_FILES)):
                continue
            p = os.path.join(d, n)
            if os.path.normcase(os.path.abspath(p)) in dev:
                continue
            out.append((f"{TOP}/runtime/Lib/site-packages/" + os.path.relpath(p, sp).replace(os.sep, "/"), p))
    return out


READY_BAT = (b"@echo off\r\n"
             b"rem AutoEQ Studio, ready to run: its own Python is in runtime\\ (nothing to install). Starting it again while it\r\n"
             b"rem runs shows the running one's window.\r\n"
             b"setlocal\r\n"
             b"set \"HERE=%~dp0\"\r\n"
             b"cd /d \"%HERE%\"\r\n"
             b"rem (Windows' 260-character limit: its deepest file is 122 characters below this folder)\r\n"
             b"if not \"%HERE:~130,1%\"==\"\" goto :toolong\r\n"
             b"start \"\" \"%HERE%runtime\\AutoEQ Studio.exe\" \"%HERE%app\\start.py\" %*\r\n"
             b"exit /b 0\r\n"
             b"\r\n"
             b":toolong\r\n"
             b"echo This folder's path is too long for AutoEQ Studio's files (Windows allows 260 characters):\r\n"
             b"echo \"%HERE%\"\r\n"
             b"echo Move the AutoEQ Studio folder somewhere shorter, e.g. straight into Documents, and start it again.\r\n"
             b"pause\r\n"
             b"exit /b 1\r\n")


def ready_testing(text):
    """TESTING.txt for the ready-to-run zip: no Python to install, no first-start download."""
    a = text.index("GETTING IT RUNNING")
    b = text.index("THINGS TO TRY")
    return (text[:a] + "GETTING IT RUNNING (a minute)\r\n"
            "  1. Unzip: right-click the zip > Extract All > Extract. (Not just double-clicking into the zip: the app can't\r\n"
            "     run from inside it.) Open the \"AutoEQ Studio\" folder that comes out.\r\n"
            "  2. Double-click \"AutoEQ Studio.bat\". If Windows asks first (\"Windows protected your PC\": click \"More\r\n"
            "     info\", then \"Run anyway\"), that's normal for any program from the internet, and it only asks once.\r\n"
            "     Nothing needs installing: Python and everything the app uses are in the runtime folder. The app opens,\r\n"
            "     with an icon by the clock (the tray: click the ^ arrow if it's hidden).\r\n\r\n"
            # (and the lines about setting up Python, which this zip doesn't do)
            + text[b:].replace("the files app.log and setup.log from", "the file app.log from")
            .replace("It only goes online to download its packages once and to search/download curves;",
                     "It only goes online to search/download curves;")
            .replace("    (If the black window said it put its packages in %LOCALAPPDATA%\\AutoEQ Studio, delete that "
                     "folder too.)\r\n", ""))


def write(out, entries):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, src in entries:
            if isinstance(src, bytes):
                z.writestr(arc, src)
            else:
                z.write(src, arc)


# (the app's modules the runtime's Python must import by itself: the window, Make an EQ, the EQ part's maths, the
# tracer and its text reader, Listen and its sound)
RUNTIME_MODULES = ("ui.app", "ui.window", "ui.eq_page", "eq.service", "eq.engines", "eq.pipeline", "ui.trace_window",
                   "ui.listen", "ui.audio", "ui.ocr")


def check_runtime(folder):
    """An unpacked ready-to-run zip's own Python (runtime\\python.exe in FOLDER), with the program's code and tests
    from here, in two steps:
    1. that Python alone (-I: nothing borrowed from this PC's Python or .venv) imports every module of the app
       (RUNTIME_MODULES), its folders in a temporary one (never your files, Equalizer APO or EQ Switcher's settings):
       a package left out of the runtime shows here;
    2. the whole self-test (app\\tools\\selftest.py: every test) with that Python. The tests need pytest, which is
       never shipped: its files (development_files(): pytest, pytest-timeout, Ruff and what they need) are copied
       from .venv into the same temporary folder and lent to that one run through PYTHONPATH, so every process the
       tests start (copies of the app, fitting workers) runs on the runtime's Python too.
    Prints the lines that aren't "ok" and gives the self-test's exit code (1 when step 1 fails); the temporary
    folder is deleted."""
    import shutil
    import tempfile
    import time
    py = os.path.join(folder, TOP, "runtime", "python.exe")
    if not os.path.isfile(py):
        raise SystemExit(f"No runtime\\python.exe in {folder}")
    work = tempfile.mkdtemp(prefix="aeqs-runtime-check-")
    try:
        env = dict(os.environ, PYTHONIOENCODING="utf-8", QT_QPA_PLATFORM="offscreen",
                   AUTOEQSTUDIO_ROOT=os.path.join(work, "studio"),
                   AUTOEQSTUDIO_DATA=os.path.join(work, "studio", "data"),
                   AUTOEQSTUDIO_DOCUMENTS=os.path.join(work, "documents"),
                   AUTOEQSTUDIO_APO_CONFIG=os.path.join(work, "apo", "config"),
                   AUTOEQSTUDIO_OLD_SETTINGS=os.path.join(work, "old", "settings.json"))
        code = f"import sys; sys.path.insert(0, sys.argv[1]); import {', '.join(RUNTIME_MODULES)}; print('imported')"
        out = subprocess.run([py, "-I", "-c", code, APP], capture_output=True, text=True, encoding="utf-8",
                             errors="replace", env=env, timeout=600)
        if out.returncode or "imported" not in out.stdout:
            print("FAIL runtime: its Python alone can't import every module of the app:\n"
                  + (out.stderr or out.stdout)[-1500:])
            return 1
        print(f"ok   runtime: its Python alone imports every module of the app ({', '.join(RUNTIME_MODULES)})")
        lent = os.path.join(work, "development-packages")
        sp = _site_packages()
        dev = development_files(sp)
        for d, subs, names in os.walk(sp):  # (each file with its own name's case: Python's imports go by it)
            subs[:] = [s for s in subs if s != "__pycache__"]
            for n in names:
                p = os.path.join(d, n)
                if os.path.normcase(os.path.abspath(p)) in dev:
                    dest = os.path.join(lent, os.path.relpath(p, sp))
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(p, dest)
        out = subprocess.run([py, os.path.join(TOOLS, "selftest.py")], capture_output=True, text=True,
                             encoding="utf-8", errors="replace",
                             env=dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=lent))
        print("\n".join(line for line in out.stdout.splitlines() if not line.startswith("ok")))
        if out.returncode and out.stderr.strip():
            print(out.stderr[-1500:])
        return out.returncode
    finally:
        for _ in range(20):  # (a process that's just ended may still hold a file for a moment)
            shutil.rmtree(work, ignore_errors=True)
            if not os.path.exists(work):
                break
            time.sleep(0.3)


def main():
    if "--check-runtime" in sys.argv:
        return check_runtime(sys.argv[sys.argv.index("--check-runtime") + 1])
    use = "--use" in sys.argv
    ready = "--ready" in sys.argv or use
    if "--no-test" not in sys.argv:
        selftest()
    stamp = datetime.datetime.now()
    os.makedirs(os.path.join(ROOT, "releases"), exist_ok=True)
    out = os.path.join(ROOT, "releases", f"AutoEQ Studio ({stamp:%Y-%m-%d}).zip" if use else
                       f"AutoEQ Studio (test build {stamp:%Y-%m-%d}" + (", ready to run" if ready else "") + ").zip")
    entries = plan(stamp)
    if use:  # (for people who use it: how to start it, not the testers' checklist; a version, not a test build)
        start_here = open(os.path.join(TOOLS, "START HERE.txt"), encoding="utf-8").read().replace("\r\n", "\n")
        entries = [(f"{TOP}/START HERE.txt", start_here.replace("\n", "\r\n").encode()) if a == f"{TOP}/TESTING.txt"
                   else (a, f"version {stamp:%Y-%m-%d}\r\n".encode()) if a == f"{TOP}/app/VERSION.txt" else (a, s)
                   for a, s in entries]
    if ready:
        entries = [(a, READY_BAT if a == f"{TOP}/AutoEQ Studio.bat" else
                    ready_testing(open(s, encoding="utf-8").read().replace("\r\n", "\n").replace("\n", "\r\n")).encode()
                    if a == f"{TOP}/TESTING.txt" else s) for a, s in entries]
        entries = [(a, s) for a, s in entries if not a.endswith("/app/setup.bat") and not a.endswith("requirements.txt")]
        entries += runtime_entries()
    write(out, entries)
    size = os.path.getsize(out) / 2**20
    print(f"Made: {out}")
    print(f"  {len(entries)} files, {size:.1f} MB")
    print(f"  starts with: {os.path.basename(PRELOAD['measurement'][0])} -> "
          f"{os.path.splitext(os.path.basename(PRELOAD['target'][0]))[0]}")
    print("Send the zip; START HERE.txt inside says how to start it." if use else
          "Send the zip; TESTING.txt inside tells your testers what to do and how to send feedback.")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if e.code is None or isinstance(e.code, int):  # (an exit code: --check-runtime gives the self-test's)
            raise
        print(e)  # (a message: why nothing was made)
        sys.exit(1)
