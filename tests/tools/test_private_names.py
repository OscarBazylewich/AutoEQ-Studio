"""No module uses another module's _private names (.claude\\CLAUDE.md's rule): an import of a _name from one of the
program's modules, or module._name on one of them, in the program (app\\). A name a second module needs is public,
with a docstring. The tests can test a module's private helpers (they do, in many files), and private names on
objects (self._x, page._x) are not looked at: only the module-level names that an import makes plain."""
import ast
import os

from helpers import paths as project

# (for app\tools\relevant_tests.py: every file this test reads)
COVERS_FILES = ("app/**/*.py",)

NAME = "code: no module uses another module's _private names"


def _app_modules():
    """The program's module names, as the app imports them (app\\ is on the path): ui.forms, eq.engines, net..."""
    app = os.path.join(project.PROJECT, "app")
    out = set()
    for root, dirs, files in os.walk(app):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "vendor")]
        for f in files:
            if f.endswith(".py"):
                out.add(_module_name(os.path.join(root, f)))
    return out


def _module_name(path):
    """The module name of a file in app\\: ui\\forms.py is ui.forms, eq\\__init__.py is eq."""
    rel = os.path.relpath(path, os.path.join(project.PROJECT, "app"))[:-3].replace(os.sep, ".")
    return rel[:-len(".__init__")] if rel.endswith(".__init__") else rel


def _private(name):
    return name.startswith("_") and not name.startswith("__")


def private_uses(path, modules):
    """Each use in the file at path of a _private name of one of modules, in line order: "line: what"."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), path)
    aliases, out = {}, []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name in modules:
                    aliases[a.asname or a.name] = a.name
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for a in node.names:
                full = f"{node.module}.{a.name}"
                if full in modules:
                    aliases[a.asname or a.name] = full
                elif node.module in modules and _private(a.name):
                    out.append((node.lineno, f"from {node.module} import {a.name}"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and _private(node.attr):
            base, dotted = node.value, []
            while isinstance(base, ast.Attribute):
                dotted.insert(0, base.attr)
                base = base.value
            if isinstance(base, ast.Name) and base.id in aliases:
                module = ".".join([aliases[base.id]] + dotted)
                if module in modules:
                    out.append((node.lineno, f"{module}.{node.attr}"))
    return [f"{line}: {what}" for line, what in sorted(out)]


def test_no_module_uses_another_modules_private_names(check):
    modules = _app_modules()
    found = []
    for root, dirs, files in os.walk(os.path.join(project.PROJECT, "app")):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "vendor")]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                rel = os.path.relpath(path, project.PROJECT)
                found += [f"{rel}:{u}" for u in private_uses(path, modules - {_module_name(path)})]
    check(NAME, not found, "\n".join(found[:30]))


def test_the_scan_finds_a_private_name(check, tmp_path):
    """The scan itself: it finds both forms of the use, and not a public name or a private name on an object."""
    p = tmp_path / "sample.py"
    p.write_text("from ui import forms\nfrom ui.tour import _demo\nimport ui.theme as th\n"
                 "forms._number(1)\nforms.number_text(1)\nth._pal\nself._x\npage._y\n", encoding="utf-8")
    uses = private_uses(str(p), {"ui", "ui.forms", "ui.tour", "ui.theme"})
    check("code: the private-name scan finds an import and a module.attribute use, and only those",
          uses == ["2: from ui.tour import _demo", "4: ui.forms._number", "6: ui.theme._pal"], uses)
