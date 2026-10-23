"""The tests a change needs (app\\tools\\relevant_tests.py, PLAN.md 5): the import graph (load-time and lazy
imports, one lazy hop), what a test file reaches (its imports anywhere, code strings, import_tool, COVERS and
COVERS_FILES, the helpers and fixtures it uses; never what the root conftest or an autouse fixture loads), the rules
from changed files to tests, git's list of changes (--since too), and the command line (--list, --run). On a made-up
project in tmp_path, and on this project's own tests (PLAN.md 5's expected choices)."""
import os
import shutil
import stat
import subprocess
import time

import pytest

from helpers import paths, qt

relevant_tests = paths.import_tool("relevant_tests")
run_tests = paths.import_tool("run_tests")

# The made-up project: each file after its "=== path ===" line. (One block of text that isn't Python as a whole, so
# relevant_tests.py, reading this file, doesn't take the made-up imports for this test's own.)
TOY = '''
=== app/launch.py ===
import places


def main():
    from screens import main
    return main
=== app/places.py ===
import os
=== app/web.py ===
import os
=== app/textio.py ===
import os
=== app/player/__init__.py ===
=== app/player/files.py ===
import textio
=== app/player/engine.py ===
import places
from player import files


def apply():
    from player import devices
    return devices
=== app/player/devices.py ===
import os
=== app/screens/__init__.py ===
=== app/screens/look.py ===
import os
=== app/screens/helpwords.py ===
from . import look
=== app/screens/main.py ===
from player import engine
from screens import look


def open_page():
    from screens.page import Page
    return Page
=== app/screens/page.py ===
from screens import look


class Page:
    def run(self):
        from eq import service
        return service
=== app/eq/__init__.py ===
import os
=== app/eq/settings.py ===
import textio
=== app/eq/engines.py ===
from . import settings


def convert():
    from . import rigconv
    return rigconv
=== app/eq/service.py ===
from . import engines


def remember():
    from .history import add
    return add
=== app/eq/history.py ===
import textio


def add():
    pass
=== app/eq/rigconv.py ===
import os
=== app/eq/rigmap.py ===
import os
=== app/eq/rigdata.json ===
{}
=== app/eq/vendor/lib.py ===
import os
=== app/tools/maker.py ===
import places


def build():
    from player import engine
    return engine
=== app/tools/notes.txt ===
notes
=== README.md ===
the project
=== tests/conftest.py ===
import web
import pytest

pytest_plugins = ["helpers.fixtures_toy"]


@pytest.fixture(autouse=True)
def everywhere():
    from eq import history
    return history
=== tests/helpers/__init__.py ===
=== tests/helpers/toysession.py ===
COVERS_FILES = ("samples/**",)


def prepare():
    import places
    return places
=== tests/helpers/toyhelp.py ===
from helpers import toysession


def service():
    from eq import service
    return service
=== tests/helpers/fixtures_toy.py ===
import pytest

from helpers import toysession


@pytest.fixture
def check():
    return print


@pytest.fixture
def studio():
    from helpers import toyhelp
    return toyhelp


@pytest.fixture
def page(studio, check):
    return studio


@pytest.fixture(autouse=True)
def reset():
    from player import devices
    return devices
=== tests/fixtures/db/lists.json ===
{}
=== tests/eq/conftest.py ===
import pytest

from helpers import toyhelp


@pytest.fixture(scope="module", autouse=True)
def reset_before_file():
    toyhelp.service()
=== tests/eq/test_options.py ===
from eq import settings


def test_defaults():
    assert settings
=== tests/player/test_files.py ===
from player import files


def test_summary(check):
    assert files
=== tests/player/test_own_fixture.py ===
import pytest


@pytest.fixture
def mine(studio):
    return studio


def test_mine(mine):
    assert mine
=== tests/screens/test_main.py ===
COVERS = ("screens.helpwords", "screens.nothere")


def test_light():
    code = "import sys; from screens import main; print(sorted(sys.modules))"
    assert code
=== tests/screens/test_page.py ===
def test_opens(page):
    assert page
=== tests/screens/test_marked.py ===
import pytest


@pytest.mark.usefixtures("studio")
def test_marked():
    pass
=== tests/tools/test_maker.py ===
COVERS_FILES = ("app/tools/*.txt",)


def test_builds():
    maker = paths.import_tool("maker")
    assert maker
'''

FILES = "tests/player/test_files.py"
OWN = "tests/player/test_own_fixture.py"
MAIN = "tests/screens/test_main.py"
PAGE = "tests/screens/test_page.py"
MARKED = "tests/screens/test_marked.py"
MAKER = "tests/tools/test_maker.py"
OPTIONS = "tests/eq/test_options.py"
ALL = sorted([FILES, OWN, MAIN, PAGE, MARKED, MAKER, OPTIONS])
STUDIO_USERS = sorted([OWN, PAGE, MARKED])  # (the tests reaching the made-up EQ part, through the studio fixture)


def make_toy(top):
    top = str(top)
    name, lines = None, []
    for line in TOY.splitlines()[1:] + ["=== end ==="]:
        if line.startswith("=== ") and line.endswith(" ==="):
            if name:
                path = os.path.join(top, *name.split("/"))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("\n".join(lines) + ("\n" if lines else ""))
            name, lines = line[4:-4], []
        else:
            lines.append(line)
    return top


def chosen(project, *changed, deleted=()):
    choice = project.choose(list(changed), deleted)
    return "everything" if choice.everything else sorted(choice.tests) or "none"


# ---------------------------------------------------------------- the graph
def test_graph(tmp_path, check):
    project = relevant_tests.Project(make_toy(tmp_path))
    load, lazy = project.modules["screens.main"]
    s_load, s_lazy = project.modules["eq.service"]
    check("relevant tests: each module's imports are split into load-time and lazy ones (inside a function), with "
          "packages and relative imports placed",
          {"player", "player.engine", "screens", "screens.look"} <= load and "screens.page" in lazy
          and "screens.page" not in load and {"eq", "eq.engines"} <= s_load and "eq.history" in s_lazy
          and "eq.history" not in s_load, (load, lazy, s_load, s_lazy))
    check("relevant tests: the app's modules are named as imported (a package by its folder), the tools by their own "
          "names, and app\\eq\\vendor isn't read",
          {"launch", "places", "player", "player.files", "screens.main", "eq", "eq.engines", "maker"}
          <= set(project.modules) and not any("vendor" in m or m.startswith("tools") for m in project.modules),
          sorted(project.modules))
    main = project.closure("screens.main")
    check("relevant tests: a module reaches what it loads, plus one lazy import from any of those and what that "
          "loads, and no further",
          {"screens.page", "player.devices", "player.files", "textio"} <= main
          and not any(m.startswith("eq") for m in main), sorted(main))
    roots, files = project.reach(PAGE)
    check("relevant tests: a fixture brings what it imports, followed through the fixtures it asks for (with the "
          "helpers those import), and the COVERS_FILES of its helpers",
          roots.get("eq.service") == "from the studio fixture" and "places" in roots
          and any(p == "samples/**" for p, _owner in files), (roots, files))


# ---------------------------------------------------------------- the choices
def test_choices(tmp_path, check):
    project = relevant_tests.Project(make_toy(tmp_path))
    check("relevant tests: a changed module chooses the tests that reach it, each with its first reason",
          chosen(project, "app/player/files.py") == sorted([FILES, MAIN, MAKER])
          and project.choose(["app/player/files.py"]).tests[FILES] == "player.files, imported by the test"
          and project.choose(["app/player/files.py"]).tests[MAIN] == "player.files, through screens.main, in a code "
                                                                    "string",
          project.choose(["app/player/files.py"]).tests)
    check("relevant tests: the root conftest's imports and the autouse fixtures add no roots (their changes don't "
          "choose every test)",
          chosen(project, "app/eq/history.py") == STUDIO_USERS and chosen(project, "app/player/devices.py") == [MAIN]
          and chosen(project, "app/eq/service.py") == STUDIO_USERS,
          (chosen(project, "app/eq/history.py"), chosen(project, "app/player/devices.py")))
    check("relevant tests: a helper's imports, inside its functions too, count only for the tests that use it or one "
          "of its fixtures",
          chosen(project, "app/eq/engines.py") == STUDIO_USERS
          and project.choose(["app/eq/engines.py"]).tests[PAGE] == "eq.engines, through eq.service, from the studio "
                                                                   "fixture", project.choose(["app/eq/engines.py"]).tests)
    check("relevant tests: code strings, import_tool(\"name\") and COVERS give a test its roots",
          chosen(project, "app/screens/main.py") == [MAIN] and chosen(project, "app/screens/helpwords.py") == [MAIN]
          and chosen(project, "app/tools/maker.py") == [MAKER], chosen(project, "app/screens/helpwords.py"))
    check("relevant tests: a name in COVERS that isn't a module of the app or its tools is said (not quietly left out)",
          f"{MAIN}: COVERS names screens.nothere, which isn't a module of the app or its tools" in project.warnings,
          project.warnings)
    check("relevant tests: COVERS_FILES choose tests for other files: a test's own, and a helper's (through the "
          "fixtures that use it), never the root conftest's",
          chosen(project, "app/tools/notes.txt") == [MAKER]
          and chosen(project, "samples/targets/x.csv") == sorted([FILES] + STUDIO_USERS),
          chosen(project, "samples/targets/x.csv"))
    check("relevant tests: rigdata.json, rigmap.json and app\\eq\\vendor count as eq.rigconv, eq.rigmap and "
          "eq.engines",
          chosen(project, "app/eq/rigdata.json") == STUDIO_USERS and chosen(project, "app/eq/vendor/lib.py")
          == STUDIO_USERS and project.choose(["app/eq/rigmap.json"]).none == ["no test reaches app/eq/rigmap.json"],
          (chosen(project, "app/eq/rigdata.json"), project.choose(["app/eq/rigmap.json"]).none))
    check("relevant tests: a test file chooses itself, and a folder's conftest.py every test under it",
          chosen(project, MAIN) == [MAIN] and chosen(project, "tests/eq/conftest.py") == [OPTIONS],
          chosen(project, "tests/eq/conftest.py"))
    everything = [chosen(project, p) for p in ("pytest.ini", "tests/conftest.py", "tests/helpers/toyhelp.py",
                                                "tests/fixtures/db/lists.json", "app/requirements.txt",
                                                "app/requirements-dev.txt", "app/requirements-any.txt")]
    check("relevant tests: pytest.ini, tests\\conftest.py, tests\\helpers, tests\\fixtures\\db and the requirements "
          "choose everything; .github and docs choose none",
          everything == ["everything"] * 7 and chosen(project, ".github/workflows/tests.yml") == "none"
          and chosen(project, "docs/screen.png") == "none", everything)
    check("relevant tests: a deleted or renamed .py chooses everything; an app .py no test reaches is said so (nothing "
          "to run); any other file no rule covers chooses everything",
          chosen(project, "app/screens/gone.py", deleted={"app/screens/gone.py"}) == "everything"
          and project.choose(["app/web.py"]).none == ["no test reaches app/web.py"]
          and project.choose(["app/launch.py"]).none == ["no test reaches app/launch.py"]
          and chosen(project, "README.md") == "everything" and chosen(project, "notes.xyz") == "everything",
          (project.choose(["app/web.py"]).none, chosen(project, "README.md")))
    both = project.choose(["app/player/files.py", "app/tools/maker.py", ".github/x.yml"])
    check("relevant tests: several changes choose the union of their tests, each with the first reason found",
          sorted(both.tests) == sorted([FILES, MAIN, MAKER]) and both.tests[MAKER].startswith("player.files")
          and both.files() == sorted([FILES, MAIN, MAKER]) and project.choose(["pytest.ini"]).files() == ALL,
          both.tests)


# ---------------------------------------------------------------- git's list of changes
def _git(root, *args):
    subprocess.run(["git", "-c", "user.name=Tests", "-c", "user.email=tests@example.invalid", "-c",
                    "commit.gpgsign=false", "-c", "init.defaultBranch=main", "-c", "core.autocrlf=false", *args],
                   cwd=root, check=True, capture_output=True, stdin=subprocess.DEVNULL)


@pytest.fixture
def repo(tmp_path):
    """The made-up project, to be made a git repository; afterwards every file in it made writable again (git makes
    its object files read-only, and Windows then won't let the session's clean-up delete them)."""
    root = make_toy(tmp_path / "repo")
    yield root
    for here, _dirs, files in os.walk(root):
        for f in files:
            os.chmod(os.path.join(here, f), stat.S_IREAD | stat.S_IWRITE)


def test_changes_from_git(repo, capsys, check):
    names = ("relevant tests: git's changes are found: changed (staged or not), new, deleted and renamed files, and "
             "not the ignored ones nor the ones committed",
             "relevant tests: --since REF adds what this branch committed since it left REF",
             "relevant tests: with no file named, the command line uses git's changes (a deleted .py: everything)")
    if not shutil.which("git"):
        check.skipped("git isn't installed here", *names)
    root = repo
    with open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write("*.log\n")
    _git(root, "init")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "start")
    _git(root, "checkout", "-b", "work")
    with open(os.path.join(root, "app", "player", "files.py"), "a", encoding="utf-8") as fh:
        fh.write("# committed on the branch\n")
    _git(root, "commit", "-am", "a change")
    with open(os.path.join(root, "app", "eq", "settings.py"), "a", encoding="utf-8") as fh:
        fh.write("# not staged\n")
    with open(os.path.join(root, "app", "screens", "look.py"), "a", encoding="utf-8") as fh:
        fh.write("# staged\n")
    _git(root, "add", "app/screens/look.py")
    _git(root, "mv", "app/textio.py", "app/textstuff.py")
    for name in ("app/screens/new page.py", "debug.log"):
        with open(os.path.join(root, *name.split("/")), "w", encoding="utf-8") as fh:
            fh.write("import os\n")
    os.remove(os.path.join(root, "app", "launch.py"))
    changed, deleted = relevant_tests.changed_files(root)
    check(names[0],
          sorted(changed) == ["app/eq/settings.py", "app/launch.py", "app/screens/look.py", "app/screens/new page.py",
                              "app/textio.py", "app/textstuff.py"]
          and deleted == {"app/launch.py", "app/textio.py"}, (changed, deleted))
    since, _gone = relevant_tests.changed_files(root, since="main")
    check(names[1], set(since) == set(changed) | {"app/player/files.py"}, since)
    capsys.readouterr()
    code = relevant_tests.main([], root=root)
    out = capsys.readouterr().out
    wrong = relevant_tests.main(["--since", "no-such-branch"], root=root)
    check(names[2], code == 0 and "Changed: 6 files" in out and "Everything (why: app/launch.py: a .py file deleted "
                                                                "or renamed" in out and wrong == 2, out)


# ---------------------------------------------------------------- the command line
def test_command_line(tmp_path, capsys, monkeypatch, check):
    root = make_toy(tmp_path)

    def said(*args):
        """(exit code, what it printed) for a command line (the checks' own lines left out)."""
        capsys.readouterr()
        code = relevant_tests.main(list(args), root=root)
        return code, capsys.readouterr().out

    code, text = said("app/player/files.py")
    shown = text.splitlines()
    check("relevant tests: it says what changed, how many test files of how many it chose, each with its reason, and "
          "the command to run them",
          code == 0 and shown[:2] == ["Changed: 1 file", "  app/player/files.py"]
          and shown[2] == "Tests to run: 3 files of 7"
          and shown[3].startswith("  tests/player/test_files.py") and shown[3].endswith("(player.files, imported by "
                                                                                       "the test)")
          and shown[-1].startswith("To run them: ") and "app/player/files.py --run" in shown[-1], shown)
    _code, every = said("pytest.ini")
    _code, none = said(".github/workflows/tests.yml")
    check("relevant tests: everything is said with why, and no tests with why",
          "Everything (why: pytest.ini: pytest's own settings): 7 test files" in every
          and "No tests for these changes (.github/workflows/tests.yml: a file for GitHub (its CI))." in none,
          (every, none))
    _code, listed = said("app/player/files.py", "--list")
    _code, listed_all = said("notes.xyz", "--list")
    check("relevant tests: --list prints only the test files, one per line (every one when everything is needed)",
          listed.splitlines() == sorted([FILES, MAIN, MAKER]) and listed_all.splitlines() == ALL, (listed, listed_all))

    got = []
    monkeypatch.setattr(run_tests, "run", lambda *a, **k: got.append((a, k)) or 5)
    code, _text = said("app/player/files.py", "--run", "--quick", "--jobs", "2", "--", "-x")
    code_none, text_none = said(".github/workflows/tests.yml", "--run")
    code_all, _text = said("pytest.ini", "--run")
    expected = [os.path.join(root, *t.split("/")) for t in sorted([FILES, MAIN, MAKER])]
    check("relevant tests: --run runs the chosen tests through run_tests.py (its --quick, --jobs and pytest's own "
          "arguments) and gives its exit code; no tests: says so, exit code 0",
          code == 5 and got[0] == ((expected,), {"quick": True, "jobs": 2, "extra": ["-x"], "root": root})
          and code_none == 0 and text_none.strip().endswith("Nothing to run.") and code_all == 5
          and got[1][0] == ([],) and len(got) == 2, (got, text_none))
    wrong = [said(*args)[0] for args in (["--quick"], ["x.py", "--", "-x"], ["--run", "--jobs", "0"], ["--nothing"],
                                         [os.path.dirname(root)])]
    check("relevant tests: a wrong command line exits with 2 (--quick, --jobs or pytest's arguments without --run, a "
          "path outside the project)", wrong == [2, 2, 2, 2, 2] and len(got) == 2, wrong)


# ---------------------------------------------------------------- on this project
def test_this_project(check):
    started = time.perf_counter()
    project = relevant_tests.Project(paths.PROJECT)
    eqfile = project.choose(["app/switcher/eqfile.py"])
    engines = project.choose(["app/eq/engines.py"])
    took = time.perf_counter() - started
    check("relevant tests: on this project, a change to switcher\\eqfile.py chooses tests\\switcher\\test_eqfile.py "
          "and not tests\\eq\\test_settings.py",
          "tests/switcher/test_eqfile.py" in eqfile.tests and "tests/eq/test_settings.py" not in eqfile.tests
          and not eqfile.everything, eqfile.tests)
    never = ["tests/switcher/test_eqfile.py", "tests/ui/test_help.py", "tests/ui/test_light.py",
             "tests/infra/test_dialogs.py"]
    check("relevant tests: on this project, a change to eq\\engines.py chooses Make an EQ's tests and the EQ helpers' "
          "tests, and none that would reach the EQ part only through an always-loaded helper",
          {"tests/eq_screen/test_opening.py", "tests/infra/test_eq_helpers.py"} <= set(engines.tests)
          and not set(never) & set(engines.tests) and not engines.everything, engines.tests)
    check("relevant tests: on this project, a change to a helper or a file no rule covers chooses everything, and one "
          "to GitHub's files none",
          chosen(project, "tests/helpers/qt.py") == "everything" and chosen(project, "notes.xyz") == "everything"
          and chosen(project, ".github/workflows/tests.yml") == "none", project.warnings)
    check("relevant tests: reading the whole project and choosing takes under 2 seconds (nothing imported or run)",
          took < qt.time_limit(2), f"{took:.2f} s")
