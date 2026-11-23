"""The zips for testers and friends (app\\tools\\make_share_zip.py), made in the test folder: the share zip holds none
of the user's files and every module of the app, and the program loads from the unpacked copy (its data beside it,
your files in Documents\\AutoEQ Studio, a stand-in here); the ready-to-run zip's own Python holds what the app needs
(Python, its launcher named AutoEQ Studio, Qt's widgets, numpy, SciPy, the sound card's library) and not pip, Qt's
QML or the tools for working on the app (pytest, Ruff), and its launcher (.bat) has CRLF line endings and guards
against too long a folder. Moved from selftest.py's zip_checks.

The texts that go out with the zips (app\\tools: READ ME FIRST.txt with the installer, START HERE.txt and TESTING.txt
in the share zips) use the names that the app shows and keep the sentence rules of ASD-STE100 (2026-11-22: they had
the names of before 2026-11-08, "press Run", "Quit", "Set up", "Relative to target", "Trace image", with contractions
and semicolons). For these, only the text of the files and of the UI modules is read."""
import datetime
import os
import re
import zipfile

from helpers import paths as project
from helpers import subproc

# (for app\tools\relevant_tests.py: the tools these tests import through helpers.paths.import_tool, what the
# unpacked copy loads (run as text), the files the zips are made from, and the UI modules whose names the texts use:
# "app/**")
COVERS = ("make_share_zip", "brand_exe", "ui.app", "eq.service", "eq.paths")
COVERS_FILES = ("app/**", "samples/**", "AutoEQ Studio.bat", "README.txt", "app/tools/TESTING.txt",
                "app/tools/START HERE.txt", "app/tools/READ ME FIRST.txt", "app/tools/sample_sources.json")

# (the tools for working on the app, never shipped: app\requirements-dev.txt's packages and what they need, and pip,
# by their names at the top of site-packages: a package's folder, a one-file module or its .dist-info folder)
DEVELOPMENT = ("pytest", "_pytest", "pluggy", "iniconfig", "packaging", "pygments", "pytest_timeout", "py", "ruff",
               "pip")


def _norm(p):
    return os.path.normcase(os.path.realpath(p))


def _development(top):
    """Whether a file or folder at the top of site-packages is one of DEVELOPMENT's."""
    name = top[:-3] if top.endswith(".py") else top.split("-")[0] if top.endswith(".dist-info") else top
    return name.lower() in DEVELOPMENT


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
    mz.write_zip(out, entries)
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
    ready = mz.ready_testing_text(testing)
    # was selftest.py:1017
    check("ready-to-run zip: its Python (python, pythonw, the named launcher, Qt's widgets, numpy, SciPy, the sound "
          "card's library) without pip or Qt's QML; its launcher CRLF and guarding against too long a folder",
          all(has(e) for e in ("/runtime/python.exe", "/runtime/pythonw.exe", "/runtime/AutoEQ Studio.exe",
                               "/PySide6/QtWidgets.pyd", "/numpy/__init__.py", "/scipy/__init__.py",
                               "libportaudio64bit.dll"))
          and not any("/site-packages/pip/" in a or "/PySide6/qml/" in a for a in rt)
          and bat.count(b"\n") == bat.count(b"\r\n") and b"goto :toolong" in bat
          and "do not install other items: Python and all the parts that the app uses" in ready,
          len(rt))
    # (2026-11-22: the parts of TESTING.txt about Python were changed with text.replace(), which changes nothing when
    # TESTING.txt has different words: that zip's TESTING.txt then had the steps for Python. Each part must now be in
    # TESTING.txt exactly one time, or no zip is made)
    left = [w for w in ("python.org", "setup.log", "its packages", "%LOCALAPPDATA%", "black window") if w in ready]
    tests = testing[testing.index("DO THESE TESTS"):testing.index("SEND THIS INFORMATION")].replace("\n", "\r\n")
    check("ready-to-run zip: its TESTING.txt has no step for Python, its packages or setup.log; it has the tests of "
          "TESTING.txt, with CRLF line ends", not left and tests in ready and "START THE APP (1 minute)" in ready
          and ready.count("\n") == ready.count("\r\n") and "\r\r" not in ready, left)
    parts = mz.READY_HEADS + tuple(old for old, _new in mz.READY_CHANGES)
    made = []
    for part in parts:
        try:
            mz.ready_testing_text(testing.replace(part, ""))
            made.append(part)
        except SystemExit:
            pass
    check("ready-to-run zip: no zip is made when TESTING.txt does not have a part that this zip's TESTING.txt "
          "changes", len(parts) == 5 and not made, made)
    # (the consolidation, 2026-10-22: pytest is installed in .venv for the tests now; the runtime leaves it out,
    # with everything else only working on the app needs: make_share_zip.development_files)
    dev = sorted({top for top in (a.split("/site-packages/", 1)[1].split("/", 1)[0] for a in rt
                                  if "/site-packages/" in a) if _development(top)})
    check("ready-to-run zip: none of the tools for working on the app in its Python (pytest and what it needs, "
          "pytest-timeout, Ruff, pip)", not dev, dev[:10])


# ---------------------------------------------------------------- the texts that go out with the zips
TEXTS = {"READ ME FIRST.txt": "\n", "START HERE.txt": "\n", "TESTING.txt": "\r\n"}  # (each file and its line end)
# The names of the app's controls and screens that the texts use, by the UI module that shows each. Each must be a
# string of its module (for a name with " (", the texts have the part before it), so a control with a new name fails
# here until the texts have that name too.
NAMES = {"window.py": ("Make an EQ", "Devices", "Settings", "Guide", "Help", "Online", "Add AutoEQ Studio to APO…"),
         "eq_page_cards.py": ("Measurement", "Find…", "Add…", "Your EQ app", "Calculate", "View",
                              "Difference from target", "Y range", "Trace a graph image…", "Your result",
                              "All results…", "Table", "Sliders", "Save filters", "Use on device",
                              "Open the Saved EQs folder"),
         "listen.py": ("Listen", "Play", "EQ off"), "picker.py": ("Use",),
         "devices_screen.py": ("Off", "Examine again"), "app.py": ("Stop AutoEQ Studio",),
         "settings_screen.py": ("Start with Windows (in the tray)", "Your files", "Backup",
                                "Remove AutoEQ Studio from APO…"),
         "setup_dialog.py": ("Add to APO",)}
# (the names before 2026-11-08, and words of the old texts that are not STE)
OLD = ("press Run", "Press Run", "Run again", "run it", "Quit", "Set up", "set up", "set it up", "Take AutoEQ Studio",
       "Relative to target", "Trace image", "Check again", "Pick your", "untick", "plug in", "Plug in", " own ",
       "e.g.", "maximised")
# an instruction starts with one of these (after "Then", "Also" or "Or", or after the comma of a condition)
COMMANDS = {"Click", "Double-click", "Right-click", "Press", "Select", "Open", "Close", "Put", "Install", "Delete",
            "Send", "Start", "Connect", "Play", "Make", "Edit", "Change", "Record", "Write", "Do", "Look", "Use",
            "Complete", "Clear", "Unzip", "Search", "Listen", "Maximize", "Restart", "Trace", "Go"}
_ITEM = re.compile(r"^\s*(-|\d+\.|[a-z]\.|\[ \])\s+")


def _read_text(name):
    with open(os.path.join(project.TOOLS, name), encoding="utf-8", newline="") as fh:
        return fh.read()


def _paragraphs(text):
    """The paragraphs of a file, each a list of its sentences. A blank line, a list item, a heading or a line with
    less indent starts a paragraph."""
    paras, cur, indent_before = [], None, 0
    for line in text.replace("\r\n", "\n").split("\n"):
        indent = len(line) - len(line.lstrip(" "))
        if not line.strip() or set(line.strip()) <= set("-="):
            cur = None
            continue
        if cur is None or _ITEM.match(line) or indent < indent_before or line.strip().isupper():
            cur = []
            paras.append(cur)
        cur.append(_ITEM.sub("", line).strip())
        indent_before = indent
    return [[s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"(])", " ".join(p)) if s.strip()] for p in paras]


def _words(sentence):
    # (text in quotation marks is a label or a name: one word, as a web address is)
    plain = re.sub(r'"[^"]*"', "Label", re.sub(r"https?://\S+", "Address", sentence))
    return len(re.findall(r"[A-Za-z0-9…%^][\w'’.,+×/%\\-]*", plain))


def _limit(sentence):
    """20 words for an instruction, 25 for other sentences. A name before a colon ("Make an EQ: it compares …",
    "Python: if you do not have Python, install it …") is not the start of the sentence."""
    said = re.sub(r"^[^:.,]{1,40}: (?=[a-z])", "", re.sub(r"^[(\"]+", "", sentence))
    words = said.split()
    if words and words[0] in ("Then", "Also", "Or") and len(words) > 1:
        words = words[1:]
    first = words[0].capitalize() if words else ""
    after = said.split(", ", 1)[1].split()[0].capitalize() if ", " in said else ""
    return 20 if first in COMMANDS or (first in ("If", "When", "To", "In", "On", "For", "At", "After")
                                        and after in COMMANDS) else 25


def test_share_texts_have_the_names_of_the_app(check):
    texts = {name: _read_text(name) for name in TEXTS}
    not_in_app, not_in_texts = [], []
    for module, names in NAMES.items():
        with open(os.path.join(project.PROJECT_APP, "ui", module), encoding="utf-8") as fh:
            source = fh.read()
        not_in_app += [(module, n) for n in names if f'"{n}"' not in source]
        not_in_texts += [n for n in names if not any(n.split(" (")[0] in t for t in texts.values())]
    check("share texts: each name of a control in READ ME FIRST.txt, START HERE.txt and TESTING.txt is a name that "
          "the app shows", not not_in_app and not not_in_texts, (not_in_app, not_in_texts))
    old = [(name, o) for name, t in texts.items() for o in OLD if o in t]
    check("share texts: none of the three files has a name or a word of before the STE change", not old, old)


def test_share_texts_keep_the_sentence_rules(check):
    texts = {name: _read_text(name) for name in TEXTS}
    ends = [name for name, end in TEXTS.items()
            if texts[name].count("\r") != (texts[name].count("\n") if end == "\r\n" else 0)
            or texts[name].count("\r") != texts[name].count("\r\n")]
    long_lines = [(name, line) for name, t in texts.items() for line in t.replace("\r\n", "\n").split("\n")
                  if len(line) > 120]
    check("share texts: each line has 120 characters or fewer; TESTING.txt has CRLF line ends, READ ME FIRST.txt "
          "and START HERE.txt have LF", not ends and not long_lines, (ends, long_lines))
    short = re.compile(r"\w+n't\b|\w+'(?:ll|re|ve|d)\b|\b(?:it|that|there|what|here|let)'s\b|;", re.I)
    marks = [(name, m) for name, t in texts.items() for m in short.findall(t)]
    check("share texts: no contraction and no semicolon", not marks, marks)
    paras = [(name, p) for name, t in texts.items() for p in _paragraphs(t)]
    long = [(name, _words(s), s) for name, p in paras for s in p if _words(s) > _limit(s)]
    # (the three files have 96 paragraphs: fewer than 60 found shows a fault of _paragraphs, not short texts)
    check("share texts: an instruction has 20 words or fewer, each other sentence 25 or fewer",
          len(paras) > 60 and not long, (len(paras), long))
    many = [(name, len(p), p[0]) for name, p in paras if len(p) > 6]
    check("share texts: each paragraph has 6 sentences or fewer", not many, many)
