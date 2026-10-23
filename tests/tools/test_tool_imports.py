"""The two tools no other test loads (added after the tests' verification, V2, 2026-10-22): app\\tools\\edge_probe.py
(odd files and requests tried on a copy of the app) and download_all.py (every database's curves, for offline use).
Neither is run here (one takes minutes, the other downloads): each is imported, through helpers.paths.import_tool, so
an import that breaks shows at once, and what each loads only when it runs is looked for: the app modules it imports
inside its functions (in the test copy of the app) and the functions of app_copy.py edge_probe.py calls."""
import ast
import os

from helpers import paths, session


def _source(tool):
    with open(os.path.join(paths.TOOLS, tool + ".py"), encoding="utf-8") as fh:
        return ast.parse(fh.read())


def _app_module_there(name):
    """Is this module of the app (eq.databases, paths, ...) in the test copy of the app, as a file or a package?"""
    base = os.path.join(session.SESSION.app, *name.split("."))
    return os.path.isfile(base + ".py") or os.path.isfile(os.path.join(base, "__init__.py"))


def _app_modules_imported_inside(tree):
    """The app's modules a tool imports inside its functions (loaded only when it runs): `import paths`, `from eq
    import databases` (eq and eq.databases), `from ui import audio`; other packages (numpy, PySide6) left out."""
    tops = {n[:-3] if n.endswith(".py") else n for n in os.listdir(session.SESSION.app)
            if n.endswith(".py") or os.path.isdir(os.path.join(session.SESSION.app, n))}
    found = set()
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(func):
            if isinstance(node, ast.Import):
                found |= {a.name for a in node.names if a.name.split(".")[0] in tops}
            elif isinstance(node, ast.ImportFrom) and not node.level and (node.module or "").split(".")[0] in tops:
                found.add(node.module)
                # (from a package: each name is one of its modules)
                if os.path.isdir(os.path.join(session.SESSION.app, *node.module.split("."))):
                    found |= {f"{node.module}.{a.name}" for a in node.names}
    return found


def test_edge_probe_imports(check):
    probe = paths.import_tool("edge_probe")
    tree = _source("edge_probe")
    calls = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
             and isinstance(node.value, ast.Name) and node.value.id == "app_copy"}
    missing = sorted(n for n in calls if not callable(getattr(probe.app_copy, n, None)))
    lazy = _app_modules_imported_inside(tree)
    gone = sorted(m for m in lazy if not _app_module_there(m))
    check("tools: edge_probe.py imports, app_copy.py has every function it calls (make_copy, use_copy, remove_copy), "
          "and the app modules it loads when it runs are there",
          callable(getattr(probe, "main", None)) and {"make_copy", "use_copy", "remove_copy"} <= calls and not missing
          and "eq.service" in lazy and not gone, (sorted(calls), missing, gone))


def test_download_all_imports(check):
    tool = paths.import_tool("download_all")
    lazy = _app_modules_imported_inside(_source("download_all"))
    gone = sorted(m for m in lazy if not _app_module_there(m))
    check("tools: download_all.py imports, and the app modules it loads when it runs (eq.databases, eq.engines, "
          "paths) are there",
          callable(getattr(tool, "main", None)) and {"eq.databases", "eq.engines", "paths"} <= lazy and not gone,
          (sorted(lazy), gone))
