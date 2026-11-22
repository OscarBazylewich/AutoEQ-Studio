"""Ruff, the linter (ruff.toml in the main folder): no unused or undefined names, no likely bugs, in the program
(app\\) and its tests (tests\\). Only where it's installed (the development environment: it isn't part of the app):
skipped, and said, without it. Moved from selftest.py's lint_checks.

Two rules of the project's own, read from the source (app\\ui\\__init__.py says why: no Python object for a layout
item). The tests' check of each call (tests\\helpers\\qt.py) sees only the code that the tests run: these read all
of it.
- No use of a layout's itemAt (or a grid's itemAtPosition) in app\\ or tests\\, but in the itemAt of a layout class of
  the app's own (a class whose base is a layout class: forms.FlowLayout, picker.Lines, listen's rows,
  eq_page_parts.WrapRow) and in the files of ITEM_AT_FILES. A view's itemAt(pos) (QListWidget, QGraphicsView: an item
  of a list or a scene, not of a layout) makes no such object: put the comment "(a view's itemAt" on its line, and it
  is let through.
- In app\\, every layout given to another layout through ui.placed (an empty layout put in its place before its items):
  no use of addLayout or insertLayout outside placed.
Each use of the name counts, not only a call: `add = v.addLayout` too.

A third rule, with the same reader: no new walk of Qt's focus chain from Python (nextInFocusChain,
previousInFocusChain) in app\\ or tests\\. PySide6 6.11.2 records the control that such a call returns as a child of the
control asked (measured, 2026-11-16; such records were a cause of an access violation in the tests, 2026-11-15). A
test measures a Tab sequence with real keys (tests\\tracer\\test_trace_tab_keys.py's _tab_stops). The files of
FOCUS_CHAIN_FILES had such a walk when this rule came (2026-11-22)."""
import ast
import os
import subprocess

from helpers import capabilities, qt, session
from helpers import paths as project

# (for app\tools\relevant_tests.py: what Ruff reads)
COVERS_FILES = ("app/**/*.py", "tests/**/*.py", "ruff.toml")

NAME = "code: Ruff finds nothing (unused or undefined names, likely bugs)"
ITEM_AT = ("code: no Python call of a layout's itemAt in the app or its tests (it makes a Python object for a layout "
           "item)")
PLACED = "code: the app gives a layout to another layout only through ui.placed (empty, before its items)"
CHECKER = "code: the layout rules' reader finds a kept method, an itemAt outside a layout class and one in the tests"
# (the files of tests\ that use a layout's itemAt on purpose, with why: they make no object of Qt's)
ITEM_AT_FILES = {
    "tests/helpers/qt.py": "reads the items of the app's own layouts through their own Python itemAt (it makes "
                           "nothing)",
}
VIEW_MARK = "(a view's itemAt"
FOCUS_CHAIN = ("code: no new Python call of nextInFocusChain or previousInFocusChain in the app or its tests (PySide6 "
               "records the returned control as a child of the control asked)")
FOCUS_CHAIN_READER = ("code: the focus chain rule's reader finds a new call, a method kept and a known file with a "
                      "different count, and no call in a comment")
FOCUS_CHAIN_NAMES = {"nextInFocusChain", "previousInFocusChain"}
# (the files with a walk of the focus chain on 2026-11-22, each with the count of its uses, not changed yet. A file
# changed to real keys gets its new count or goes from this list: the check fails until then. No file comes into it)
FOCUS_CHAIN_FILES = {
    "app/ui/tour.py": 2,
    "tests/eq_screen/test_focus_frame_page.py": 4,
    "tests/eq_screen/test_picture_wait.py": 1,
    "tests/eq_screen/test_result_narrow.py": 1,
    "tests/eq_screen/test_run_keeps_the_page.py": 2,
    "tests/eq_screen/test_your_value_tag_keeps_the_page.py": 2,
}


def test_ruff_finds_nothing(check):
    ok, ruff = capabilities.ruff()
    if not ok:  # (the old check's words)
        check.skipped("Ruff isn't installed here (\".venv\\Scripts\\python.exe -m pip install ruff\")", NAME)
    # (--no-cache: Ruff leaves no .ruff_cache folder in the project; run in the main folder, so ruff.toml applies)
    out = subprocess.run([ruff, "check", "--no-cache", "--quiet", "app", "tests"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", cwd=project.PROJECT, env=session.child_env(),
                         timeout=qt.time_limit(120))
    # was selftest.py:1091
    check(NAME, out.returncode == 0, (out.stdout + out.stderr)[-600:])


def _is_layout_class(node):
    """A class whose base's name is a layout class's (QLayout, QBoxLayout, …): one of the app's own layouts."""
    return isinstance(node, ast.ClassDef) and any(
        (b.id if isinstance(b, ast.Name) else b.attr if isinstance(b, ast.Attribute) else "").endswith("Layout")
        for b in node.bases)


def uses(source, rel, names, allowed):
    """Each use of an attribute in names (a call, or the method kept: any ast.Attribute) in source, as
    "rel:line name", but where allowed(rel, the function it is in, whether that function is a method of a layout
    class, the line's text) says yes."""
    lines = source.splitlines()
    found = []

    def walk(node, func, in_layout):
        for child in ast.iter_child_nodes(node):
            here, layout_method = func, in_layout
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                here, layout_method = child.name, _is_layout_class(node)
            elif isinstance(child, ast.ClassDef):
                here, layout_method = None, False
            if isinstance(child, ast.Attribute) and child.attr in names \
                    and not allowed(rel, here, layout_method, lines[child.lineno - 1]):
                found.append(f"{rel}:{child.lineno} {child.attr}")
            walk(child, here, layout_method)
    walk(ast.parse(source, rel), None, False)
    return found


def _item_at_allowed(rel, func, layout_method, line):
    return (func == "itemAt" and layout_method) or rel in ITEM_AT_FILES or VIEW_MARK in line


def _placed_allowed(rel, func, _layout_method, _line):
    return rel == "app/ui/__init__.py" and func == "placed"


def _sources(*folders):
    """(path relative to the project with forward slashes, its text) of each .py file in the folders (not vendor\\)."""
    for folder in folders:
        for root, dirs, files in os.walk(os.path.join(project.PROJECT, folder)):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", "vendor")]
            for f in files:
                if f.endswith(".py"):
                    path = os.path.join(root, f)
                    with open(path, encoding="utf-8") as fh:
                        yield os.path.relpath(path, project.PROJECT).replace(os.sep, "/"), fh.read()


def test_no_itemat_call_in_the_app(check):
    found = [u for rel, text in _sources("app", "tests")
             for u in uses(text, rel, {"itemAt", "itemAtPosition"}, _item_at_allowed)]
    check(ITEM_AT, not found, found[:20])


def test_layouts_given_through_placed(check):
    found = [u for rel, text in _sources("app")
             for u in uses(text, rel, {"addLayout", "insertLayout"}, _placed_allowed)]
    check(PLACED, not found, found[:20])


def chain_walks(sources, known):
    """What is wrong with the uses of Qt's focus chain in sources ((rel, text) pairs) against the known counts
    ({rel: count}; a file not in it: 0): {rel: (its uses as "rel:line name", its known count)} for each file whose
    count of uses is not its known count."""
    seen = {rel: uses(text, rel, FOCUS_CHAIN_NAMES, lambda *_a: False) for rel, text in sources}
    return {rel: (seen.get(rel, []), known.get(rel, 0)) for rel in sorted(set(seen) | set(known))
            if len(seen.get(rel, [])) != known.get(rel, 0)}


def test_no_new_walk_of_the_focus_chain(check):
    wrong = chain_walks(_sources("app", "tests"), FOCUS_CHAIN_FILES)
    check(FOCUS_CHAIN, not wrong, wrong)


def test_the_focus_chain_reader_on_made_up_code(check):
    rel = "tests/ui/test_x.py"
    walk = ("def order(w):\n    # (nextInFocusChain in a comment)\n    nxt = w.nextInFocusChain()\n"
            "    back = w.previousInFocusChain\n    return nxt, back\n")
    clean = 'def order(w):\n    """No nextInFocusChain here."""\n    return w\n'
    hits = [f"{rel}:3 nextInFocusChain", f"{rel}:4 previousInFocusChain"]
    seen = {"a new file": chain_walks([(rel, walk)], {}), "a known file": chain_walks([(rel, walk)], {rel: 2}),
            "a known file with one more": chain_walks([(rel, walk)], {rel: 1}),
            "a known file with none left": chain_walks([(rel, clean)], {rel: 2}),
            "no call": chain_walks([(rel, clean)], {})}
    check(FOCUS_CHAIN_READER,
          seen == {"a new file": {rel: (hits, 0)}, "a known file": {}, "a known file with one more": {rel: (hits, 1)},
                   "a known file with none left": {rel: ([], 2)}, "no call": {}}, seen)


def test_the_rules_reader_on_made_up_code(check):
    code = '''
from PySide6.QtWidgets import QLayout, QListWidget


class Own(QLayout):
    def itemAt(self, i):
        return self.items[i].itemAt(0)


def itemAt(lay):
    return lay.itemAt(0)


def kept(v, row):
    add = v.addLayout
    add(row)


def view(lst, pos):
    return lst.itemAt(pos)  # (a view's itemAt: a row of a list)
'''
    item_at = uses(code, "app/ui/x.py", {"itemAt", "itemAtPosition"}, _item_at_allowed)
    in_tests = uses("def test_x(lay):\n    return lay.itemAt(0)\n", "tests/ui/test_x.py", {"itemAt"}, _item_at_allowed)
    kept = uses(code, "app/ui/x.py", {"addLayout", "insertLayout"}, _placed_allowed)
    check(CHECKER, item_at == ["app/ui/x.py:11 itemAt"] and in_tests == ["tests/ui/test_x.py:2 itemAt"]
          and kept == ["app/ui/x.py:15 addLayout"], (item_at, in_tests, kept))
