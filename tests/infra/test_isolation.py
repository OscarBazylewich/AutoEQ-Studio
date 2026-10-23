"""The tests' isolation (helpers.session, helpers.paths, helpers.capabilities; PLAN.md 3.4, 3.9): every folder the
app uses is in the session's temporary folder, the app comes from its copy there, a child process never writes the
run's check log, stale session folders are cleaned away, the guard lets writes in the session's folders through
however TEMP is spelled, a tool imported in a test leaves the app's modules in the copy, and the helpers every test
loads keep away from the EQ part (so app\\tools\\relevant_tests.py can choose tests well)."""
import ast
import ctypes
import os
import stat
import subprocess
import sys
import tempfile
import time

from helpers import capabilities, guard, paths, session

S = session.SESSION
APP_NAMES = ("backup", "net", "paths", "start", "textfile", "userfiles", "eq", "switcher", "ui")
ALWAYS_LOADED = ("session", "guard", "checks", "dialogs", "qt", "apo", "paths", "subproc", "capabilities",
                 "fixtures_core")


def _short(path):
    """Windows' short (8.3) spelling of a folder that exists, e.g. C:\\Users\\OSCART~1\\..."""
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.windll.kernel32.GetShortPathNameW(path, buf, 1024)
    return buf.value if 0 < n < 1024 else path


def test_every_folder_in_the_session(check):
    env = os.environ
    places = {k: env.get(k) for k in ("AUTOEQSTUDIO_ROOT", "AUTOEQSTUDIO_DATA", "AUTOEQSTUDIO_DOCUMENTS",
                                      "AUTOEQSTUDIO_APO_CONFIG", "AUTOEQSTUDIO_OLD_SETTINGS", "TEMP", "TMP",
                                      "USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA")}
    places.update(gettempdir=tempfile.gettempdir(), home=os.path.expanduser("~"))
    outside = {k: v for k, v in places.items() if not v or not session.inside(v)}
    check("isolation: every AUTOEQSTUDIO_* folder, TEMP, the home and AppData are inside the session folder",
          not outside and "AUTOEQSTUDIO_APO_INSTALL" not in env
          and not any(env.get(k) for k in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial")), outside)


def test_app_from_the_copy(check):
    import paths as app_paths
    loaded = {n: getattr(m, "__file__", None) for n, m in sys.modules.items()
              if n.split(".")[0] in APP_NAMES and getattr(m, "__file__", None)}
    elsewhere = sorted(n for n, f in loaded.items() if not session.inside(f, S.app))
    check("isolation: the app is imported from the session's copy, never from the project",
          session.inside(app_paths.__file__, S.app) and loaded and not elsewhere, elsewhere)


def test_paths_on_the_studio(check):
    import paths as app_paths
    from eq import paths as eq_paths
    wanted = {"paths.ROOT": (app_paths.ROOT, S.studio), "paths.DATA": (app_paths.DATA, S.data),
              "paths.SAMPLES": (app_paths.SAMPLES, os.path.join(S.studio, "samples")),
              "eq.paths.TARGET_DIR": (eq_paths.TARGET_DIR, os.path.join(S.studio, "Targets")),
              "eq.paths.MEAS_DIR": (eq_paths.MEAS_DIR, os.path.join(S.studio, "Measurements")),
              "eq.paths.CACHE": (eq_paths.CACHE, os.path.join(S.data, "eq", "cache")),
              "paths.apo_folders()": (app_paths.apo_folders()[1], S.apo_config)}
    wrong = {k: v for k, (v, want) in wanted.items() if os.path.normcase(os.path.realpath(v))
             != os.path.normcase(os.path.realpath(want))}
    check("isolation: paths and eq.paths point at the session's studio and stand-in APO folder", not wrong, wrong)


def test_nothing_of_the_old_apps_beside_the_copy(check):
    import paths as app_paths
    beside = os.path.dirname(S.studio)
    there = [n for n in ("AutoEQ Local", "EQ Switcher") if os.path.exists(os.path.join(beside, n))]
    looked = [app_paths.old_app(n) for n in ("AutoEQ Local", "EQ Switcher")]
    check("isolation: nothing named AutoEQ Local or EQ Switcher beside the copy, and the bring-overs look only there",
          not there and all(session.inside(p) for p in looked) and session.inside(app_paths.EQ_SWITCHER_SETTINGS),
          (there, looked))


def test_own_channel(check):
    import start
    users = "AutoEQStudio-" + os.environ.get("USERNAME", "user")
    check("isolation: the session's one-copy channel isn't the user's (a test copy's own)",
          start.SERVER != users and start.SERVER.startswith(users + "-test"), start.SERVER)


def test_child_env_leaves_the_log_out(monkeypatch, check):
    monkeypatch.setenv("AUTOEQSTUDIO_CHECK_LOG", os.path.join(S.tmp, "log.jsonl"))
    monkeypatch.setenv("AUTOEQSTUDIO_TEST_OUT", S.tmp)
    plain, kept = session.child_env(), session.child_env(keep_log=True)
    bare = session.child_env(without_folders=True, QT_QPA_PLATFORM=None, EXTRA="1")
    check("isolation: child_env() leaves out the check log's two variables (unless asked), and the folder variables "
          "when asked; an override of None removes one",
          "AUTOEQSTUDIO_CHECK_LOG" not in plain and "AUTOEQSTUDIO_TEST_OUT" not in plain
          and kept.get("AUTOEQSTUDIO_CHECK_LOG") and kept.get("AUTOEQSTUDIO_TEST_OUT")
          and not any(k in bare for k in session.FOLDER_VARS) and "QT_QPA_PLATFORM" not in bare
          and bare.get("EXTRA") == "1" and plain.get("AUTOEQSTUDIO_DATA") == S.data, sorted(bare)[:5])


def test_stale_folders_cleaned(tmp_path, check):
    ended = subprocess.Popen([sys.executable, "-c", "pass"])
    ended.wait()
    folders = {}
    for name, owner in (("aeqs-tests-gone", f"{ended.pid} 1"), ("aeqs-tests-alive", session.owner_line()),
                        ("aeqs-tests-reused", f"{os.getpid()} 1"), ("aeqs-tests-nobody", None),
                        ("other-gone", f"{ended.pid} 0")):
        folders[name] = os.path.join(tmp_path, name)
        os.makedirs(folders[name])
        if owner:
            with open(os.path.join(folders[name], "owner.txt"), "w") as fh:
                fh.write(owner)
    gone = session.sweep_stale(str(tmp_path))
    left = sorted(n for n in folders if os.path.isdir(folders[n]))
    check("isolation: a stale session folder (its process gone, or its id taken by another) is deleted; a live one, "
          "one without owner.txt and anything not named aeqs-tests-* are kept",
          sorted(os.path.basename(p) for p in gone) == ["aeqs-tests-gone", "aeqs-tests-reused"]
          and left == ["aeqs-tests-alive", "aeqs-tests-nobody", "other-gone"], (gone, left))


def _read_only_inside(folder):
    """A read-only file in a read-only folder inside, as git leaves its object files (Windows won't delete them as
    they are)."""
    sub = os.path.join(folder, "objects", "ab")
    os.makedirs(sub)
    with open(os.path.join(sub, "cdef"), "w") as fh:
        fh.write("x")
    os.chmod(os.path.join(sub, "cdef"), stat.S_IREAD)
    os.chmod(sub, stat.S_IREAD)


def test_left_over_and_kept_folders(tmp_path, check):
    ended = subprocess.Popen([sys.executable, "-c", "pass"])
    ended.wait()
    two_days_ago = time.time() - 2 * 24 * 3600
    folders = {}
    for name, owner, old in (("aeqs-tests-gone-read-only", f"{ended.pid} 1", False),
                             ("aeqs-tests-nobody-old", None, True), ("aeqs-tests-nobody-new", None, False),
                             ("aeqs-tests-kept", f"{ended.pid} 1 {session.KEPT}", True),
                             ("aeqs-tests-marked", f"{ended.pid} 1", True), ("other-old", None, True)):
        folders[name] = path = os.path.join(tmp_path, name)
        os.makedirs(path)
        if owner:
            with open(os.path.join(path, "owner.txt"), "w") as fh:
                fh.write(owner)
        if name == "aeqs-tests-gone-read-only":
            _read_only_inside(path)
        if old:
            os.utime(path, (two_days_ago, two_days_ago))
    session.mark_kept(folders["aeqs-tests-marked"])  # (as cleanup() marks a folder kept at the end of its run)
    gone = session.sweep_stale(str(tmp_path))
    left = sorted(n for n in folders if os.path.isdir(folders[n]))
    check("isolation: a stale session folder holding read-only files (git's object files) is deleted all the same, and "
          "one without owner.txt untouched for over a day (what a run that couldn't delete its folder left); one kept "
          "with AUTOEQSTUDIO_KEEP_TEST_FOLDER=1 (\"kept\" in its owner.txt, from the start or marked at the end), a "
          "newer one without owner.txt and anything not named aeqs-tests-* are left alone",
          sorted(os.path.basename(p) for p in gone) == ["aeqs-tests-gone-read-only", "aeqs-tests-nobody-old"]
          and left == ["aeqs-tests-kept", "aeqs-tests-marked", "aeqs-tests-nobody-new", "other-old"]
          and session.owner_line(kept=True).split()[2:] == [session.KEPT]
          and session.owner_line().split()[2:] == [], (gone, left))
    top = os.path.join(tmp_path, "a session folder")
    os.makedirs(top)
    _read_only_inside(top)
    check("isolation: the session folder is deleted at the end with its read-only files and folders too "
          "(session.remove_tree, which cleanup() uses)", session.remove_tree(top) and not os.path.exists(top), top)


def test_session_root_spelled_the_long_way(check):
    check("isolation: the session folder is spelled the long way (its own realpath), as are TEMP and the home",
          S.root == os.path.realpath(S.root) and os.environ["TEMP"] == os.path.realpath(os.environ["TEMP"])
          and S.home == os.path.realpath(S.home) and S.real_temp == os.path.realpath(S.real_temp),
          (S.root, os.environ["TEMP"], S.home))


def test_writes_in_the_session_pass_the_guard(tmp_path, check):
    short_root = _short(S.root)
    targets = [os.path.join(tmp_path, "in tmp_path.txt"), os.path.join(S.root, "tmp", "in the session.txt"),
               os.path.join(short_root, "tmp", "short spelling.txt"), os.path.join(_short(str(tmp_path)), "short.txt")]
    with guard.expect_blocked() as blocked:
        written = []
        for p in targets:
            try:
                with open(p, "w") as fh:
                    fh.write("x")
                written.append(os.path.isfile(p))
            except PermissionError as e:
                written.append(str(e))
    check("isolation: a write under tmp_path and one under the session folder both pass the guard, spelled the long "
          "or the short way (TEMP's two spellings)",
          written == [True] * 4 and not blocked and str(tmp_path).startswith(S.root), (written, blocked, short_root))


def test_import_tool_keeps_the_copy(check):
    before = list(sys.path)
    mz = paths.import_tool("make_share_zip")
    import paths as app_paths
    loaded = [n for n, m in sys.modules.items() if n.split(".")[0] in APP_NAMES and getattr(m, "__file__", None)]
    wrong = [n for n in loaded if not session.inside(sys.modules[n].__file__, S.app)]
    check("isolation: import_tool(\"make_share_zip\") leaves sys.path as it was and every app module in the copy",
          sys.path == before and session.inside(mz.__file__, paths.TOOLS) and mz.paths is app_paths and not wrong,
          wrong)


def _imports(tree):
    """Every module an ast tree imports, at any level: (module, names, level)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name, (), 0
        elif isinstance(node, ast.ImportFrom):
            yield node.module or "", tuple(a.name for a in node.names), node.level


def test_always_loaded_helpers_keep_away_from_the_eq_part(check):
    tools = {os.path.splitext(n)[0] for n in os.listdir(paths.TOOLS) if n.endswith(".py")}
    found = []
    for name in ALWAYS_LOADED:
        with open(os.path.join(paths.TESTS, "helpers", name + ".py"), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for module, names, level in _imports(tree):
            mods = [f"{module}.{n}" if module else n for n in names] if names else [module]
            if level or module == "helpers":
                bad = [m for m in mods if m.split(".")[-1] in ("studio", "eq", "eqpage")]
            else:
                bad = [m for m in mods if m.startswith("helpers.") and m.split(".")[1] in ("studio", "eq", "eqpage")]
                top = module.split(".")[0]
                if top in APP_NAMES or top in tools:
                    bad += [m for m in mods if m not in ("net", "ui.theme", "ui.ocr")]
            found += [f"{name}.py: {m}" for m in bad]
    check("isolation: the helpers every test loads import no helpers.studio, eq or eqpage, and no app or tools module "
          "but net, ui.theme and ui.ocr (at any level, inside functions too)", not found, found)


def _iscc_places():
    real = S.real_env
    tops = [os.path.join(real["LOCALAPPDATA"], "Programs") if real.get("LOCALAPPDATA") else None,
            real.get("ProgramFiles(x86)"), real.get("ProgramFiles")]
    return [os.path.join(t, "Inno Setup 6", "ISCC.exe") for t in tops if t]


def test_iscc_looked_for_in_the_real_places(check):
    expected = next((p for p in _iscc_places() if os.path.isfile(p)), None)
    found = capabilities.iscc_path()
    check("isolation: capabilities.iscc_path() looks for Inno Setup in the real LOCALAPPDATA and Program Files, not "
          "the session's stand-ins",
          found == expected and (found is None or not session.inside(found))
          and os.path.normcase(os.environ["LOCALAPPDATA"]) != os.path.normcase(S.real_env.get("LOCALAPPDATA", "")),
          (found, expected))


def test_capabilities_answer(check):
    answers = {name: getattr(capabilities, name)() for name in ("iscc", "ocr_ready", "interactive_desktop",
                                                                "project_venv", "ruff", "claude_notes")}
    wrong = {k: v for k, v in answers.items() if not (isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], bool)
                                                      and isinstance(v[1], str) and v[1])}
    check("isolation: each capability answers (found or not, and what was found or why not, in words)", not wrong,
          wrong or {k: v[0] for k, v in answers.items()})


def test_iscc_found_for_the_user_only(check):
    name = ("isolation: Inno Setup installed for the user only (under the real LOCALAPPDATA, which the session "
            "replaces) is found from inside a session")
    mine = _iscc_places()[0] if S.real_env.get("LOCALAPPDATA") else None
    if not (mine and os.path.isfile(mine)):
        check.skipped("Inno Setup isn't installed for the user only here (not under LOCALAPPDATA)", name)
    check(name, capabilities.iscc_path() == mine, (capabilities.iscc_path(), mine))
