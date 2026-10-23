r"""The tests a change needs: from the files changed, the test files that reach them, found by reading the code
(Python's ast: nothing is imported or run, so it takes a second or two).

    ".venv\Scripts\python.exe" app\tools\relevant_tests.py [PATHS ...] [--since REF] [--list]
                                                           [--run [--quick] [--jobs N] [-- PYTEST-ARGS]]

What changed: the files named (PATHS); else what git says changed since the last commit (staged or not) and the new
files it doesn't ignore; --since REF: everything changed since this branch left REF (e.g. --since main), committed
or not.
--list   only the test files, one per line.
--run    runs them (app\tools\run_tests.py: each part in its own process, the plain summary) and exits with its exit
         code; --quick leaves the slow ones out, --jobs N runs N parts at once, anything after -- goes to pytest.
Exit code 0 (or the run's), 2 for a wrong command line.

How a test is chosen:
- The app's modules (every .py in app\ but app\eq\vendor and app\tools, named as imported: app\ui\window.py is
  ui.window) and the tools (app\tools\*.py, by their own names) with their imports, each either at load time (at the
  top of the file, in a class, in a top-level if or try) or lazy (inside a function).
- A test file's roots: the modules it imports anywhere in it (in a function too), through a code string it runs in
  another Python (e.g. "import sys; from ui import window"), through import_tool("name"), or names in COVERS; the
  ones the tests' helpers it imports import anywhere (and the helpers those import, in turn); and the ones the
  fixtures it uses import (inside the fixture, and at the top of the file defining it), followed through the
  fixtures those ask for. The root conftest's own imports and the fixtures every test gets without asking (autouse)
  add none: they're the same for every test, and a change to them chooses everything anyway.
- What a test reaches: everything its roots load when imported, plus one lazy import from any of those, and what
  that loads in turn. (Following every lazy import would reach the whole app from almost anywhere.)
- From a changed file to tests: pytest.ini, tests\conftest.py, tests\helpers, tests\fixtures\db, the requirements
  files, and a .py deleted or renamed choose everything; .github and docs choose none; else a test file chooses
  itself, a folder's conftest.py every test under it, an app or tools .py every test that reaches it, rigdata.json,
  rigmap.json and app\eq\vendor count as eq.rigconv, eq.rigmap and eq.engines, and any file chooses the tests whose
  COVERS_FILES (their own, or of the helpers and fixtures they use) match it. A .py of the app no test reaches is
  said so (nothing to run); any other file no rule covers chooses everything.

For other tools: main(argv), Project(root).choose(paths, deleted) and changed_files(root, since).
"""
import argparse
import ast
import dataclasses
import os
import re
import subprocess
import sys

PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (pattern, why) for the files that choose every test, and for those that choose none
EVERYTHING = (
    ("pytest.ini", "pytest's own settings"),
    ("tests/conftest.py", "what every test is set up with"),
    ("tests/helpers/**", "the tests' helpers, which any test may use"),
    ("tests/fixtures/db/**", "the small database lists every test's studio gets"),
    ("app/requirements.txt", "the packages the app runs on"),
    ("app/requirements-dev.txt", "the packages the tests run on"),
    ("app/requirements-any.txt", "the packages the app runs on"),
)
NO_TESTS = ((".github/**", "a file for GitHub (its CI)"), ("docs/**", "the GitHub page's words and pictures"))
# (data the app reads, counted as a change to the module that reads it)
BUILT_IN = (("app/eq/rigdata.json", "eq.rigconv"), ("app/eq/rigmap.json", "eq.rigmap"),
            ("app/eq/vendor/**", "eq.engines"))


def glob_regex(pattern):
    """A path pattern (forward slashes, from the project's folder) as a regular expression: ** any number of folders
    (none too), * anything within one name, ? one character. Case doesn't matter (Windows)."""
    p, i, out = pattern.replace("\\", "/"), 0, []
    while i < len(p):
        if p.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif p.startswith("**", i):
            out.append(".*")
            i += 2
        elif p[i] == "*":
            out.append("[^/]*")
            i += 1
        elif p[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(p[i]))
            i += 1
    return re.compile("".join(out) + r"\Z", re.I)


_PATTERNS = {}


def matches(pattern, path) -> bool:
    if pattern not in _PATTERNS:
        _PATTERNS[pattern] = glob_regex(pattern)
    return bool(_PATTERNS[pattern].match(path))


def _parents(name):
    """a.b.c -> a, a.b, a.b.c (importing a.b.c loads a and a.b first)."""
    bits = name.split(".")
    return [".".join(bits[:i]) for i in range(1, len(bits) + 1)]


def _parse(path):
    try:
        with open(path, "rb") as fh:
            return ast.parse(fh.read(), path)
    except (OSError, SyntaxError, ValueError):
        return None


def _import_nodes(tree):
    """(import statement, inside a function?) for every import in the tree."""
    todo = [(tree, False)]
    while todo:
        node, lazy = todo.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                yield child, lazy
            else:
                todo.append((child, lazy or isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))))


def _named(node, current="", is_package=False):
    """The module names an import statement can load: `import a.b` loads a and a.b; `from a import b` loads a and,
    when b is a module, a.b; a relative import is taken inside its package (current: the importing module)."""
    if isinstance(node, ast.Import):
        return [n for alias in node.names for n in _parents(alias.name)]
    base = node.module or ""
    if node.level:
        if not current:
            return []  # (a relative import outside a package: nothing known)
        package = current if is_package else current.rpartition(".")[0]
        for _ in range(node.level - 1):
            package = package.rpartition(".")[0]
        base = f"{package}.{base}" if package and base else package or base
    if not base:
        return []
    return _parents(base) + [f"{base}.{alias.name}" for alias in node.names if alias.name != "*"]


def _strings(tree):
    """Every string in the tree that could be code (it holds "import"): plain ones, and f-strings with each {...} as
    a name."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
        elif isinstance(node, ast.JoinedStr):
            text = "".join(v.value if isinstance(v, ast.Constant) and isinstance(v.value, str) else "_"
                           for v in node.values)
        else:
            continue
        if "import" in text:
            yield text


def _code_imports(tree):
    """The import statements inside the code strings of a tree (e.g. a `python -c` string run in another
    process)."""
    found = []
    for text in _strings(tree):
        try:
            code = ast.parse(text)
        except (SyntaxError, ValueError):
            continue
        found += [node for node, _lazy in _import_nodes(code)]
    return found


def _tool_calls(tree):
    """The tools a test imports through helpers.paths.import_tool("name")."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
            if name == "import_tool":
                yield node.args[0].value


def _declared(tree, name):
    """A module-level declaration (COVERS, COVERS_FILES, pytest_plugins) as a tuple of strings, or None."""
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(
            node, ast.AnnAssign) and node.value is not None else []
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            try:
                value = ast.literal_eval(node.value)
            except ValueError:
                return None
            if isinstance(value, str):
                return (value,)
            if isinstance(value, (tuple, list, set)) and all(isinstance(v, str) for v in value):
                return tuple(value)
            return None
    return None


def _fixture_mark(func):
    """(is it a fixture?, autouse?, its name) for a function's decorators."""
    for dec in func.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        name = target.attr if isinstance(target, ast.Attribute) else target.id if isinstance(target, ast.Name) else ""
        if name != "fixture":
            continue
        autouse, own_name = False, func.name
        for kw in dec.keywords if isinstance(dec, ast.Call) else []:
            if kw.arg == "autouse" and isinstance(kw.value, ast.Constant):
                autouse = bool(kw.value.value)
            elif kw.arg == "name" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                own_name = kw.value.value
        return True, autouse, own_name
    return False, False, func.name


def _params(func):
    a = func.args
    return [p.arg for p in a.posonlyargs + a.args + a.kwonlyargs if p.arg not in ("self", "cls")]


@dataclasses.dataclass
class _Fixture:
    name: str
    autouse: bool
    params: list
    node: object       # its function
    source: object     # the _Source defining it


class _Source:
    """A test-side file as read: a test file, a conftest.py or a helper (tests\\helpers\\*.py)."""

    def __init__(self, rel, name, tree):
        self.rel = rel           # its path from the project's folder (forward slashes)
        self.name = name         # a helper's module name (helpers.qt), else ""
        self.tree = tree
        self.fixtures = {}
        self.uses = set()        # fixture names its tests and its own fixtures ask for
        if tree is None:
            self.covers = self.covers_files = self.plugins = ()
            return
        self.covers = _declared(tree, "COVERS") or ()
        self.covers_files = _declared(tree, "COVERS_FILES") or ()
        self.plugins = _declared(tree, "pytest_plugins") or ()
        functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            functions += [(n, cls) for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for item in functions:
            func, cls = item if isinstance(item, tuple) else (item, None)
            is_fixture, autouse, name = _fixture_mark(func)
            if is_fixture:
                self.fixtures[name] = _Fixture(name, autouse, _params(func), func, self)
                self.uses.update(_params(func))
            elif func.name.startswith("test") and (cls is None or cls.name.startswith("Test")):
                self.uses.update(_params(func))
        for node in ast.walk(tree):  # (pytest.mark.usefixtures("a", "b"), request.getfixturevalue("a"))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr in ("usefixtures", "getfixturevalue"):
                self.uses.update(a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str))


@dataclasses.dataclass
class Choice:
    """What a change needs. everything: why every test is needed ([] when not); tests: {test file: its first
    reason}; none: why some changed files need no test (a CI file, an app file no test reaches); total and
    all_tests: how many test files there are, and which."""
    changed: list
    total: int
    everything: list = dataclasses.field(default_factory=list)
    tests: dict = dataclasses.field(default_factory=dict)
    none: list = dataclasses.field(default_factory=list)
    all_tests: list = dataclasses.field(default_factory=list)

    def files(self) -> list:
        """The test files to run, from the project's folder (every one when everything is needed)."""
        return list(self.all_tests) if self.everything else sorted(self.tests)


class Project:
    """The project's code, read once: the app's import graph and what each test file reaches."""

    def __init__(self, root=None):
        self.root = os.path.abspath(root or PROJECT)
        self.warnings = []
        self.modules = {}    # module name -> (load-time imports, lazy imports)
        self.paths = {}      # a module's file, from the project's folder, lower case -> module name
        self._read_app()
        self.helpers = {}    # helper module name -> _Source
        self.conftests = {}  # folder (tests, tests/eq, ...) -> _Source
        self.tests = {}      # test file -> _Source
        self._read_tests()
        self._closures = {}
        self._helper_memo = {}
        self._reach = {}
        self._reaches = {}

    # ---------------------------------------------------------------- the app side
    def _app_files(self):
        """(module name, file) for every module of the app and every tool."""
        app = os.path.join(self.root, "app")
        found = []
        for here, dirs, files in os.walk(app):
            rel = os.path.relpath(here, app).replace(os.sep, "/")
            dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith(".")
                             and not (rel == "." and d == "tools") and not (rel == "eq" and d == "vendor"))
            for f in sorted(files):
                if not f.endswith(".py"):
                    continue
                bits = ([] if rel == "." else rel.split("/")) + ([] if f == "__init__.py" else [f[:-3]])
                if bits:
                    found.append((".".join(bits), os.path.join(here, f), f == "__init__.py"))
        tools = os.path.join(app, "tools")
        for f in sorted(os.listdir(tools)) if os.path.isdir(tools) else []:
            if f.endswith(".py") and f != "__init__.py":
                found.append((f[:-3], os.path.join(tools, f), False))
        return found

    def _read_app(self):
        files = self._app_files()
        known = {name for name, _path, _pkg in files}
        for name, path, is_package in files:
            self.paths[os.path.relpath(path, self.root).replace(os.sep, "/").lower()] = name
            tree = _parse(path)
            load, lazy = set(), set()
            if tree is None:
                self.warnings.append(f"{os.path.relpath(path, self.root)} couldn't be read as Python: its imports "
                                     "are left out")
            else:
                for node, is_lazy in _import_nodes(tree):
                    (lazy if is_lazy else load).update(n for n in _named(node, name, is_package) if n in known)
            self.modules[name] = (load - {name}, lazy - {name})

    def _load_closure(self, start):
        """Everything these modules load when imported (their packages first, their load-time imports)."""
        seen, todo = set(), list(start)
        while todo:
            m = todo.pop()
            if m in seen or m not in self.modules:
                continue
            seen.add(m)
            todo += _parents(m)[:-1]
            todo += self.modules[m][0]
        return seen

    def closure(self, module) -> set:
        """What a module reaches: everything it loads, plus one lazy import from any of those, and what that loads."""
        if module not in self._closures:
            loaded = self._load_closure([module])
            hop = set(loaded)
            for m in loaded:
                hop |= self.modules[m][1]
            self._closures[module] = self._load_closure(hop)
        return self._closures[module]

    # ---------------------------------------------------------------- the test side
    def _read_tests(self):
        tests = os.path.join(self.root, "tests")
        for here, dirs, files in os.walk(tests):
            rel_here = os.path.relpath(here, self.root).replace(os.sep, "/")
            dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith(".")
                             and not (rel_here == "tests" and d == "fixtures"))
            for f in sorted(files):
                if not f.endswith(".py"):
                    continue
                rel = f"{rel_here}/{f}"
                if rel_here == "tests/helpers":
                    name = "helpers" if f == "__init__.py" else f"helpers.{f[:-3]}"
                    self.helpers[name] = _Source(rel, name, _parse(os.path.join(here, f)))
                elif rel_here.startswith("tests/helpers/"):
                    continue
                elif f == "conftest.py":
                    self.conftests[rel_here] = _Source(rel, "", _parse(os.path.join(here, f)))
                elif f.startswith("test_"):
                    self.tests[rel] = _Source(rel, "", _parse(os.path.join(here, f)))
        for source in list(self.helpers.values()) + list(self.conftests.values()) + list(self.tests.values()):
            if source.tree is None:
                self.warnings.append(f"{source.rel} couldn't be read as Python: what it uses is left out")

    def _split(self, nodes, current=""):
        """The app's and tools' modules, and the helpers, that import statements name."""
        app, helpers = [], []
        for node in nodes:
            for n in _named(node, current, current == "helpers"):
                if n in self.helpers:
                    helpers.append(n)
                elif n in self.modules:
                    app.append(n)
        return app, helpers

    def _uses_of(self, source, nodes, tree):
        """(modules, helpers, code-string modules, code-string helpers) of some import statements and the code
        strings and import_tool calls in a tree."""
        app, helpers = self._split(nodes, source.name)
        app += [t for t in _tool_calls(tree) if t in self.modules]
        code_app, code_helpers = self._split(_code_imports(tree))
        return app, helpers, code_app, code_helpers

    def _helper(self, name):
        """What a helper brings, with the helpers it imports in turn: ({module: helper that brings it}, [(COVERS_FILES
        pattern, helper)])."""
        if name not in self._helper_memo:
            roots, files, seen, todo = {}, [], set(), [name]
            while todo:
                h = todo.pop(0)
                if h in seen or h not in self.helpers:
                    continue
                seen.add(h)
                source = self.helpers[h]
                if source.tree is None:
                    continue
                app, helpers, code_app, code_helpers = self._uses_of(
                    source, [n for n, _lazy in _import_nodes(source.tree)], source.tree)
                self._unknown(source)
                for m in app + code_app + [c for c in source.covers if c in self.modules]:
                    roots.setdefault(m, h)
                files += [(p, h) for p in source.covers_files]
                todo += helpers + code_helpers
            self._helper_memo[name] = (roots, files)
        return self._helper_memo[name]

    def _unknown(self, source):
        """A warning for each name in a file's COVERS that isn't a module of the app or its tools (a typo chooses
        nothing, quietly otherwise)."""
        for m in source.covers:
            if m not in self.modules:
                self.warnings.append(f"{source.rel}: COVERS names {m}, which isn't a module of the app or its tools")

    def _fixture_sources(self, test):
        """Where a test file's fixtures come from, in pytest's order: the file, the conftest.py files from its folder
        up to tests\\, then the plugins (tests\\helpers\\fixtures_*.py and pytest_plugins' helpers)."""
        found = [self.tests[test]]
        folder = os.path.dirname(test).replace(os.sep, "/")
        while folder:
            if folder in self.conftests:
                found.append(self.conftests[folder])
            if folder == "tests" or "/" not in folder:
                break
            folder = folder.rpartition("/")[0]
        plugins = [p for s in found for p in s.plugins if p in self.helpers]
        plugins += [h for h in sorted(self.helpers) if h.startswith("helpers.fixtures_")]
        return found + [self.helpers[p] for p in dict.fromkeys(plugins)]

    def reach(self, test):
        """A test file's roots ({module: where from}, the test's own imports first) and its COVERS_FILES ([(pattern,
        where from)])."""
        if test in self._reach:
            return self._reach[test]
        source = self.tests[test]
        roots, files = {}, []
        if source.tree is not None:
            app, helpers, code_app, code_helpers = self._uses_of(
                source, [n for n, _lazy in _import_nodes(source.tree)], source.tree)
            for m in app:
                roots.setdefault(m, "")
            for m in code_app:
                roots.setdefault(m, "in a code string")
            self._unknown(source)
            for m in source.covers:
                if m in self.modules:
                    roots.setdefault(m, "named in COVERS")
            files += [(p, "") for p in source.covers_files]
            for h in helpers + code_helpers:
                h_roots, h_files = self._helper(h)
                for m in h_roots:
                    roots.setdefault(m, f"from {h}")
                files += [(p, f"{owner}") for p, owner in h_files]
            # The fixtures it asks for, followed through the fixtures those ask for.
            sources = self._fixture_sources(test)
            root_conftest = self.conftests.get("tests")
            seen, todo = set(), sorted(source.uses)
            while todo:
                wanted = todo.pop(0)
                if wanted in seen:
                    continue
                seen.add(wanted)
                fixture = next((s.fixtures[wanted] for s in sources if wanted in s.fixtures), None)
                if fixture is None:
                    continue  # (one of pytest's own, tmp_path, monkeypatch...: nothing of the project's)
                todo += fixture.params
                if fixture.source is source:
                    continue  # (the test file's own fixture: its imports are the file's)
                origin = f"from the {wanted} fixture"
                nodes = [n for n, _lazy in _import_nodes(fixture.node)]
                if fixture.source is not root_conftest:  # (the root conftest's own imports add no roots)
                    nodes += [n for n in fixture.source.tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
                    self._unknown(fixture.source)
                    for m in fixture.source.covers:
                        if m in self.modules:
                            roots.setdefault(m, origin)
                    files += [(p, f"the {wanted} fixture") for p in fixture.source.covers_files]
                app, helpers, code_app, code_helpers = self._uses_of(fixture.source, nodes, fixture.node)
                for m in app + code_app:
                    roots.setdefault(m, origin)
                for h in helpers + code_helpers:
                    h_roots, h_files = self._helper(h)
                    for m in h_roots:
                        roots.setdefault(m, origin)
                    files += [(p, f"the {wanted} fixture ({owner})") for p, owner in h_files]
        self._reach[test] = (roots, files)
        return self._reach[test]

    def reaches(self, test) -> set:
        """Every module of the app and its tools a test file reaches."""
        if test not in self._reaches:
            roots, _files = self.reach(test)
            out = set()
            for m in roots:
                out |= self.closure(m)
            self._reaches[test] = out
        return self._reaches[test]

    def why(self, test, module):
        """Why a test file reaches a module, in a few words (its first root that reaches it), or None."""
        roots, _files = self.reach(test)
        for root, origin in roots.items():
            if module in self.closure(root):
                bits = [module] + ([f"through {root}"] if root != module else [])
                bits += [origin] if origin else ["imported by the test"] if root == module else []
                return ", ".join(bits)
        return None

    # ---------------------------------------------------------------- choosing
    def choose(self, changed, deleted=()) -> Choice:
        """The tests these changed files need (paths from the project's folder, forward slashes; deleted: those of
        them that are gone)."""
        deleted = {d.lower() for d in deleted}
        all_tests = sorted(self.tests)
        choice = Choice(list(changed), len(all_tests), all_tests=all_tests)
        for path in changed:
            low = path.lower()
            why = next((w for p, w in EVERYTHING if matches(p, path)), None)
            if why is None and low.endswith(".py") and low in deleted:
                why = "a .py file deleted or renamed (it can't be placed)"
            if why:
                choice.everything.append(f"{path}: {why}")
                continue
            why = next((w for p, w in NO_TESTS if matches(p, path)), None)
            if why:
                choice.none.append(f"{path}: {why}")
                continue
            chosen = {}
            if low in {t.lower() for t in all_tests}:
                chosen[next(t for t in all_tests if t.lower() == low)] = "the test file itself"
            elif low.startswith("tests/") and low.endswith("/conftest.py"):
                folder = path.rpartition("/")[0] + "/"
                for t in all_tests:
                    if t.lower().startswith(folder.lower()):
                        chosen.setdefault(t, f"{path}, its folder's conftest.py")
            module = self.paths.get(low)
            data = next((m for p, m in BUILT_IN if matches(p, path)), None)
            for target, prefix in ((module, ""), (data, f"{path}, used by ")):
                if target:
                    for t in all_tests:
                        if t not in chosen and target in self.reaches(t):
                            chosen[t] = prefix + self.why(t, target)
            for t in all_tests:
                if t not in chosen:
                    _roots, files = self.reach(t)
                    hit = next(((p, owner) for p, owner in files if matches(p, path)), None)
                    if hit:
                        chosen[t] = f"{path}: COVERS_FILES {hit[0]!r}" + (f" of {hit[1]}" if hit[1] else "")
            if chosen:
                for t, reason in chosen.items():
                    choice.tests.setdefault(t, reason)
            elif module or data or (low.startswith("app/") and low.endswith(".py")):
                choice.none.append(f"no test reaches {path}")
            else:
                choice.everything.append(f"{path}: no rule or test declaration covers it")
        return choice


# ---------------------------------------------------------------- what changed
def _git(root, *args):
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, stdin=subprocess.DEVNULL)
    except OSError as e:
        raise RuntimeError(f"git couldn't be run ({e}): name the changed files instead") from e
    if r.returncode:
        said = r.stderr.decode("utf-8", "replace").strip().splitlines()
        raise RuntimeError(f"git {' '.join(args)} failed: {said[-1] if said else r.returncode}")
    return r.stdout.decode("utf-8", "replace")


def changed_files(root=None, since=None):
    """(the files changed, from the project's folder; those of them that are gone): git's changes since the last
    commit (staged or not) and its new files, or with `since`, everything since this branch left that commit."""
    root = os.path.abspath(root or PROJECT)
    base = "HEAD"
    if since:
        base = _git(root, "merge-base", since, "HEAD").strip()
    names = _git(root, "diff", "--name-only", "--no-renames", "--relative", "-z", base).split("\0")
    names += _git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    names = list(dict.fromkeys(n.replace("\\", "/") for n in names if n))
    return names, {n for n in names if not os.path.exists(os.path.join(root, n))}


def given_files(paths, root=None, cwd=None):
    """The paths named on the command line, from the project's folder (a folder: every file in it). A relative path
    is taken from the current folder when that's inside the project, else from the project's folder. Raises
    ValueError for one outside the project."""
    root = os.path.abspath(root or PROJECT)
    cwd = os.path.abspath(cwd or os.getcwd())
    inside_cwd = os.path.normcase(cwd + os.sep).startswith(os.path.normcase(root + os.sep)) or \
        os.path.normcase(cwd) == os.path.normcase(root)
    out = []
    for given in paths:
        full = os.path.normpath(os.path.join(cwd if inside_cwd else root, given))
        try:
            rel = os.path.relpath(full, root)
        except ValueError:
            rel = os.pardir
        if rel == os.pardir or rel.startswith(os.pardir + os.sep):
            raise ValueError(f"{given} isn't in this project ({root})")
        if os.path.isdir(full):
            for here, dirs, files in os.walk(full):
                dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith("."))
                out += [os.path.relpath(os.path.join(here, f), root).replace(os.sep, "/") for f in sorted(files)]
        else:
            out.append(rel.replace(os.sep, "/"))
    return list(dict.fromkeys(out))


# ---------------------------------------------------------------- the command line
def _say(line="", err=False):
    stream = sys.stderr if err else sys.stdout
    try:
        print(line, file=stream, flush=True)
    except UnicodeEncodeError:
        enc = getattr(stream, "encoding", None) or "ascii"
        print(line.encode(enc, "replace").decode(enc), file=stream, flush=True)


def _plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _quoted(text):
    return f'"{text}"' if " " in text or not text else text


def _show(choice, command):
    _say(f"Changed: {_plural(len(choice.changed), 'file')}")
    for path in choice.changed:
        _say(f"  {path}")
    if choice.everything:
        more = f" (and {len(choice.everything) - 3} more)" if len(choice.everything) > 3 else ""
        _say(f"Everything (why: {'; '.join(choice.everything[:3])}{more}): {_plural(choice.total, 'test file')}")
    elif choice.tests:
        _say(f"Tests to run: {_plural(len(choice.tests), 'file')} of {choice.total}")
        width = max(len(t) for t in choice.tests)
        for test in sorted(choice.tests):
            _say(f"  {test.ljust(width)}   ({choice.tests[test]})")
        for line in choice.none:
            _say(f"Nothing for {line}" if not line.startswith("no test") else line[0].upper() + line[1:] + ".")
    else:
        _say(f"No tests for these changes ({'; '.join(choice.none)}).")
        return
    if command:
        _say(f"To run them: {command} --run   (--quick leaves the slow ones out)")


def _run_tests():
    """app\\tools\\run_tests.py, beside this file."""
    try:
        import run_tests
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "run_tests", os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_tests.py"))
        run_tests = importlib.util.module_from_spec(spec)
        sys.modules["run_tests"] = run_tests
        spec.loader.exec_module(run_tests)
    return run_tests


def _positive_int(text):
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError(f"not a number of parts at once (1 or more): {text}")
    return value


def main(argv=None, root=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = []
    if "--" in argv:
        at = argv.index("--")
        argv, extra = argv[:at], argv[at + 1:]
    parser = argparse.ArgumentParser(prog="relevant_tests.py", description="The tests a change needs.",
                                     epilog="Anything after -- goes to pytest (with --run).")
    parser.add_argument("paths", nargs="*", help="the changed files (default: what git says changed)")
    parser.add_argument("--since", metavar="REF", help="everything changed since this branch left REF (e.g. main)")
    parser.add_argument("--list", action="store_true", help="only the test files, one per line")
    parser.add_argument("--run", action="store_true", help="run them (run_tests.py)")
    parser.add_argument("--quick", action="store_true", help="with --run: leave out the slow tests")
    parser.add_argument("--jobs", type=_positive_int, help="with --run: how many parts run at once")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:  # (a wrong command line: argparse said why)
        return e.code if isinstance(e.code, int) else 2
    if (args.quick or args.jobs or extra) and not args.run:
        _say("relevant_tests.py: --quick, --jobs and pytest's arguments (after --) go with --run", err=True)
        return 2
    root = os.path.abspath(root or PROJECT)
    try:
        changed, deleted = [], set()
        if args.paths:
            changed = given_files(args.paths, root)
            deleted = {p for p in changed if not os.path.exists(os.path.join(root, p))}
        if args.since or not args.paths:
            more, gone = changed_files(root, args.since)
            changed += [p for p in more if p not in changed]
            deleted |= gone
    except (RuntimeError, ValueError) as e:
        _say(f"relevant_tests.py: {e}", err=True)
        return 2
    if not changed:
        if not args.list:
            _say("Nothing changed" + (f" since {args.since}" if args.since else " since the last commit") +
                 ": no tests to run.")
        return 0
    project = Project(root)
    choice = project.choose(changed, deleted)
    for test in project.tests:  # (every test's declarations looked at, so a misspelt COVERS name is always said)
        project.reach(test)
    for warning in dict.fromkeys(project.warnings):
        _say(f"note: {warning}", err=True)
    if args.list:
        for test in choice.files():
            _say(test)
    else:
        command = None if args.run else " ".join(
            [_quoted(sys.executable), r"app\tools\relevant_tests.py"] + [_quoted(p) for p in args.paths]
            + (["--since", _quoted(args.since)] if args.since else []))
        _show(choice, command)
    if not args.run:
        return 0
    if not choice.everything and not choice.tests:
        _say("Nothing to run.")
        return 0
    paths = [] if choice.everything else [os.path.join(root, *t.split("/")) for t in choice.files()]
    return _run_tests().run(paths, quick=args.quick, jobs=args.jobs, extra=extra, root=root)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):  # (UTF-8 whatever the console)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
