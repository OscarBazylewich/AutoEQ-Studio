"""Where everything is (paths.py), asked of copies of the program in a Python of their own, each with stand-in
Documents and AppData in the test folder (never the real ones), as the old checks did:
- run from its own folder: your files in Documents\\AutoEQ Studio, or in the folder chosen in Settings;
- installed (app\\installed.txt): your files in Documents, settings and log in AppData\\Roaming, downloads and caches
  in AppData\\Local, the samples in the program; nothing brought over from the retired apps; the first start puts the
  sample curves and the database lists in place;
- the installer's test build: its own folders, running channel and mutex, and no Equalizer APO.
Moved from selftest.py's userfiles_checks (the first) and installed_checks (the other two)."""
import json
import os
import types

import pytest

import paths
from helpers import subproc

# (what the copies run, as text: app\tools\relevant_tests.py can't see these imports otherwise)
COVERS = ("paths", "eq.paths", "eq.bring_over", "start")


def _without_own_variables(**more):
    """The session's environment for a copy of the program with none of AutoEQ Studio's own variables (as the old
    checks: the copy works out its folders itself), and these added: overrides for helpers.subproc.run_python, where
    None takes a variable out."""
    return dict({k: None for k in os.environ if k.startswith("AUTOEQSTUDIO_")}, **more)


def _same(a, b):
    """Equal, paths compared the long way (os.path.realpath) and as Windows compares them (any case)."""
    if isinstance(a, str) and isinstance(b, str) and os.path.isabs(a) and os.path.isabs(b):
        return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    return a == b


def test_your_files_documents_or_chosen_folder(tmp_path, check):
    top = str(tmp_path)
    prog = os.path.dirname(subproc.app_copy(os.path.join(top, "prog")))  # (the copy: <top>\prog\app)
    env = _without_own_variables(AUTOEQSTUDIO_DOCUMENTS=os.path.join(top, "docs"))  # (stands in for Documents)
    code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import paths\n"
            "print(json.dumps([paths.ROOT, paths.TARGETS, paths.SAVED_EQS, paths.DATA]))")

    def where():
        out = subproc.run_python(code, os.path.join(prog, "app"), env=env, timeout=60)
        return out.data if isinstance(out.data, list) else out.stderr[-300:]
    first = where()
    os.makedirs(os.path.join(prog, "data"), exist_ok=True)
    with open(os.path.join(prog, "data", "settings.json"), "w", encoding="utf-8") as fh:
        json.dump({"profiles": {}, paths.FILES_KEY: os.path.join(top, "mine")}, fh)
    chosen = where()
    docs = os.path.join(top, "docs", "AutoEQ Studio")
    # was selftest.py:778
    check("your files: Documents\\AutoEQ Studio by default (Targets, Saved EQs …; the app's data stays its own), the "
          "folder chosen in Settings when there is one",
          _same(first, [docs, os.path.join(docs, "Targets"), os.path.join(docs, "Saved EQs"), os.path.join(prog, "data")])
          and _same(chosen[:2], [os.path.join(top, "mine"), os.path.join(top, "mine", "Targets")]), (first, chosen))


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    """An installed copy of the program (app\\installed.txt) with what its installer puts beside it for the first start
    (a target and the database lists), and the environment it runs in: none of AutoEQ Studio's own variables, AppData
    and Documents in the test folder (selftest.py lines 1119-1127)."""
    top = str(tmp_path_factory.mktemp("installed"))
    inst = subproc.app_copy(os.path.join(top, "inst"), installed=True)
    for rel in (r"first-start\Targets\T.txt", r"first-start\cache\databases.json"):  # (what the installer brings)
        os.makedirs(os.path.dirname(os.path.join(top, "inst", rel)), exist_ok=True)
        with open(os.path.join(top, "inst", rel), "w", encoding="utf-8") as fh:
            fh.write("seed")
    env = _without_own_variables(APPDATA=os.path.join(top, "roam"), LOCALAPPDATA=os.path.join(top, "local"),
                                 AUTOEQSTUDIO_DOCUMENTS=os.path.join(top, "docs"))
    return types.SimpleNamespace(top=top, inst=inst, env=env)


def test_installed_copy_places(installed, check):
    top = installed.top
    code = ("import os, sys, json; sys.path.insert(0, sys.argv[1]); import paths, eq.paths as e, eq.bring_over as b\n"
            "paths.first_start()\n"
            "print(json.dumps({'installed': paths.INSTALLED, 'root': paths.ROOT, 'data': paths.DATA, 'log': paths.LOG,"
            " 'cache': e.CACHE, 'downloads': e.DOWNLOAD_DIR, 'samples': e.SAMPLES_DIR, 'targets': e.TARGET_DIR,"
            " 'eqdata': e.DATA, 'docs': paths._documents(), 'bring': b.default_source(), 'old': paths.old_app('EQ Switcher'),"
            " 'seeded': sorted(os.path.relpath(os.path.join(d, n), paths.ROOT) for d, _s, ns in os.walk(paths.ROOT) for n in ns),"
            " 'lists': os.path.isfile(os.path.join(e.CACHE, 'databases.json'))}))")
    out = subproc.run_python(code, installed.inst, env=installed.env, timeout=60)
    p = out.data if isinstance(out.data, dict) else {"error": out.stderr[-400:]}
    roam, local, prog = (os.path.join(top, d) for d in ("roam", "local", "inst"))
    want = {"installed": True, "root": os.path.join(p.get("docs") or "?", "AutoEQ Studio"),
            "data": os.path.join(roam, "AutoEQ Studio"), "log": os.path.join(roam, "AutoEQ Studio", "app.log"),
            "cache": os.path.join(local, "AutoEQ Studio", "cache"), "downloads": os.path.join(local, "AutoEQ Studio", "downloads"),
            "samples": os.path.join(prog, "samples"), "targets": os.path.join(p.get("docs") or "?", "AutoEQ Studio", "Targets"),
            "eqdata": os.path.join(roam, "AutoEQ Studio", "eq"), "bring": None, "old": os.path.join(top, "EQ Switcher"),
            "docs": os.path.join(top, "docs"), "seeded": [os.path.join("Targets", "T.txt")], "lists": True}
    wrong = {k: (p.get(k), v) for k, v in want.items() if not _same(p.get(k), v)}
    # was selftest.py:1148
    check("installed: your files in Documents, settings and log in AppData\\Roaming, downloads and caches in "
          "AppData\\Local, samples in the program; nothing brought over from the retired apps; the first start puts the sample curves and "
          "the database lists in place", not wrong, wrong)


def test_test_build_own_folders_channel_and_mutex(installed, check):
    # ((review 2) a test build, make_installer.py --test-build, never reaches the user's app, folders or APO: the same
    # installed copy and environment, with test-build.txt beside it for this test only)
    top, inst = installed.top, installed.inst
    marker = os.path.join(inst, "test-build.txt")
    with open(marker, "w") as fh:
        fh.write("test")
    try:
        code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import paths, start\n"
                "print(json.dumps([paths.DATA, paths.ROOT, list(paths.apo_folders()), start.SERVER, start.MUTEX]))")
        out = subproc.run_python(code, inst, env=installed.env, timeout=60)
    finally:
        os.remove(marker)
    t = out.data if isinstance(out.data, list) else [out.stderr[-400:]]
    roam = os.path.join(top, "roam")
    # was selftest.py:1161
    check("installed: a test build has its own folders, running channel and mutex, and no Equalizer APO unless a test "
          "folder is given", len(t) == 5 and _same(t[0], os.path.join(roam, "AutoEQ Studio (test)"))
          and _same(t[1], os.path.join(top, "docs", "AutoEQ Studio (test)")) and t[2] == [None, None]
          and "-test" in t[3] and t[4] == "AutoEQStudioRunning-test", t)
