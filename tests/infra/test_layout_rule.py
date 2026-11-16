"""The tests' two checks of layout items (helpers.qt; app\\ui\\__init__.py says why): the record of a layout with items
given to a layout in a window (LAYOUT_RULE_CHECK, the layout_rule_check fixture; through ui.placed, the line that
called it) and the search, after each test (tests\\conftest.py), for the Python objects that PySide6 made for layout
items, stale or not (ITEM_OBJECT_CHECK; stale_layout_items tells which no layout holds). Each is shown to find what it
is for, on a small window made here or in an inner run; and a test process that never uses Qt never loads it."""
import sys

from helpers import inner, qt

pytest_plugins = ["pytester"]


def _line_of(fn):
    """The line of this file where fn() (a lambda on one line) makes its call."""
    return fn.__code__.co_firstlineno


def test_the_rule_records_each_call_that_breaks_it(qapp, check):
    from PySide6.QtWidgets import QFormLayout, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

    def filled():
        row = QHBoxLayout()
        row.addWidget(QLabel("a"))
        return row
    w = QWidget()
    try:
        v = QVBoxLayout(w)
        grid_w, form_w = QWidget(), QWidget()
        v.addWidget(grid_w)
        v.addWidget(form_w)
        grid, form = QGridLayout(grid_w), QFormLayout(form_w)
        qt.take_layout_breaks()
        calls = (("QBoxLayout.addLayout", lambda: v.addLayout(filled())),
                 ("QBoxLayout.insertLayout", lambda: v.insertLayout(0, filled())),
                 ("QGridLayout.addLayout", lambda: grid.addLayout(filled(), 0, 0)),
                 ("QFormLayout.addRow", lambda: form.addRow("Label", filled())),
                 ("QFormLayout.insertRow", lambda: form.insertRow(0, "Label", filled())),
                 ("QFormLayout.setLayout", lambda: form.setLayout(5, QFormLayout.ItemRole.FieldRole, filled())))
        want, seen = [], []
        for method, call in calls:
            call()
            want.append(f"tests/infra/test_layout_rule.py:{_line_of(call)} {method}")
            seen += [where for _test, where in qt.take_layout_breaks()]
        # what the rule permits: an empty layout put in its place first, then filled; a filled layout given to a
        # layout with no widget yet, which then becomes a widget's own layout
        row = QHBoxLayout()
        v.addLayout(row)
        row.addWidget(QLabel("b"))
        loose = QVBoxLayout()
        loose.addLayout(filled())
        holder = QWidget()
        v.addWidget(holder)
        holder.setLayout(loose)
        permitted = qt.take_layout_breaks()
    finally:
        qt.close(w)
    check("tests: the layout rule records each of the six calls that give a layout with items to a layout in a "
          "window, with the file and line of the call, and nothing for the calls that it permits",
          seen == want and permitted == [], {"seen": seen, "want": want, "permitted": permitted})


def test_the_stale_item_search_finds_a_deleted_item(qapp, check):
    import shiboken6
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
    w = QWidget()
    try:
        v = QVBoxLayout(w)
        row = QHBoxLayout()
        a = QLabel("a")
        row.addWidget(a)
        row.addWidget(QLabel("b"))
        base = {id(o) for o in qt.layout_item_objects()}
        v.addLayout(row)  # (breaks the rule on purpose: PySide6 makes an object for each item of row)
        qt.take_layout_breaks()
        made = len([o for o in qt.layout_item_objects() if id(o) not in base])
        before = qt.stale_layout_items()
        a.setParent(None)  # (Qt deletes a's item in row, and does not tell PySide6)
        stale = qt.stale_layout_items()
        names = qt.forget_items(stale)  # (at once: no Qt object is made in between)
        after = qt.stale_layout_items()
        forgotten = [shiboken6.isValid(o) for o in stale]
        stale.clear()
        a.deleteLater()
    finally:
        qt.close(w)
    check("tests: the search for stale layout items finds the object of an item that Qt deleted (its widget taken out "
          "of the window), and none before; once forgotten, PySide6 no longer has it",
          made == 2 and before == [] and names == ["QWidgetItem"] and after == [] and forgotten == [False],
          {"made": made, "before": len(before), "names": names, "after": len(after), "valid": forgotten})


def test_no_python_is_given_the_layout_items_of_qt(qapp, check):
    # (a window laid out as the app does it: each layout put in its place empty, then filled; then a widget moved and
    # one deleted, as the tracer's 3 Save row and a list drawn again do)
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
    base = {id(o) for o in qt.layout_item_objects()}
    w = QWidget()
    try:
        v = QVBoxLayout(w)
        row = QHBoxLayout()
        v.addLayout(row)
        labels = [QLabel(t) for t in "abc"]
        for lab in labels:
            row.addWidget(lab)
        row.insertWidget(0, labels[2])
        labels[1].setParent(None)
        labels[1].deleteLater()
        made = [o for o in qt.layout_item_objects() if id(o) not in base]
        stale = qt.stale_layout_items()
    finally:
        qt.close(w)
    check("tests: a window laid out with each layout in its place before its items has no Python object of a layout "
          "item, after a widget moved and one deleted", made == [] and stale == [],
          {"made": [type(o).__name__ for o in made], "stale": len(stale), "python": sys.version_info[:2]})


# (an inner run: tests that never use Qt; the third one says which of Qt's modules its process has loaded by then,
# after the checks that ran after the first two)
NO_QT = '''
import sys

from helpers import checks


def test_one():
    assert sum([1, 2]) == 3


def test_two():
    assert "".join(["a", "b"]) == "ab"


def test_modules_then():
    names = ("shiboken6", "PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets")
    checks.log({"event": "qt_modules", "loaded": sorted(m for m in names if m in sys.modules)})
'''


def test_tests_without_qt_never_load_it(pytester, monkeypatch, check):
    # (2026-11-16, a verifier: the check after each test imported shiboken6 with nothing to forget, so from the second
    # test on every test process had Qt loaded, and the search of Qt's objects ran after each test in the parts that
    # never use Qt too: tests\switcher 2.64 s, then 3.84 s)
    result, log = inner.run(pytester, monkeypatch, {"test_inner_no_qt.py": NO_QT}, "-q")
    seen = next((r["loaded"] for r in log if r["event"] == "qt_modules"), None)
    check("tests: a test process whose tests never use Qt never loads it (PySide6, shiboken6), also after the checks "
          "that run after each test", seen == [] and result.parseoutcomes() == {"passed": 3},
          (seen, result.parseoutcomes()))


# (an inner run: two tests leave the objects that PySide6 makes for the items of a layout given with its items through
# addItem and insertItem, in a window that stays open, so the objects are in a layout and not stale; the third test
# says how many are left then)
LEFT_IN_A_LAYOUT = '''
import pytest

from helpers import checks, qt

KEPT = []


@pytest.fixture
def fails_after():
    yield
    pytest.fail("a fixture's own check failed")  # (as layout_rule_check fails: before the checks of conftest.py)


def _filled():
    from PySide6.QtWidgets import QHBoxLayout, QLabel
    row = QHBoxLayout()
    row.addWidget(QLabel("a"))
    row.addWidget(QLabel("b"))
    return row


def _window_layout():
    from PySide6.QtWidgets import QVBoxLayout, QWidget
    w = QWidget()
    KEPT.append(w)  # (it stays open: the items live on)
    return QVBoxLayout(w)


def test_add_item(qapp):
    _window_layout().addItem(_filled())


def test_insert_item(qapp):
    _window_layout().insertItem(0, _filled())


def test_add_item_and_a_fixture_that_fails(qapp, fails_after):
    _window_layout().addItem(_filled())


def test_left_then(qapp):
    checks.log({"event": "made_left", "count": len(qt.made_item_objects())})
    for w in KEPT:
        qt.close(w)
'''


def test_check_after_each_test_finds_every_item_object(pytester, monkeypatch, check):
    # (2026-11-16, a verifier: addItem and insertItem with a layout that has items make the same objects, and nothing
    # was recorded; and an object that a layout still holds was never failed, stale or not)
    result, log = inner.run(pytester, monkeypatch, {"test_inner_items_left.py": LEFT_IN_A_LAYOUT}, "-q")
    name = getattr(qt, "ITEM_OBJECT_CHECK", "(no such check)")
    found = sorted(r["test"].split("::")[-1] for r in log if r["event"] == "check" and r["name"] == name
                   and not r["ok"])
    left = next((r["count"] for r in log if r["event"] == "made_left"), None)
    # (the inner run's file is outside tests\, so its lines are not on the line record: the next test shows that)
    check("tests: the check after each test fails a test that leaves an object that PySide6 made for a layout item, "
          "also one that a layout still holds (a layout with items given with addItem or insertItem), also when a "
          "fixture's own check failed first, and forgets them, so the next test starts clean",
          found == ["test_add_item", "test_add_item_and_a_fixture_that_fails", "test_insert_item"] and left == 0,
          (found, left, result.parseoutcomes()))


def test_add_item_and_insert_item_found_and_forgotten(qapp, check):
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

    def filled():
        row = QHBoxLayout()
        row.addWidget(QLabel("a"))
        row.addWidget(QLabel("b"))
        return row
    base = {id(o) for o in qt.made_item_objects()}
    w = QWidget()
    seen = {}
    try:
        v = QVBoxLayout(w)
        qt.take_layout_breaks()
        v.addItem(filled())  # (not on the line record: helpers.qt's LAYOUT_CALLS says why)
        seen["after addItem"] = len([o for o in qt.made_item_objects() if id(o) not in base])
        insert = lambda: v.insertItem(0, filled())  # noqa: E731
        insert()
        made = [o for o in qt.made_item_objects() if id(o) not in base]
        seen["recorded"] = [where for _test, where in qt.take_layout_breaks()]
        seen["want"] = [f"tests/infra/test_layout_rule.py:{_line_of(insert)} QBoxLayout.insertItem"]
        seen["forgotten"] = qt.forget_items(made)  # (taken by the test: it passes)
        seen["left"] = len([o for o in qt.made_item_objects() if id(o) not in base])
        made.clear()
    finally:
        qt.close(w)
    check("tests: a layout with items given with addItem or insertItem leaves an object that PySide6 made for each "
          "of its items: found (insertItem also on the line record, at its line), then forgotten",
          seen.get("after addItem") == 2 and seen.get("forgotten") == ["QWidgetItem"] * 4
          and seen.get("recorded") == seen.get("want") and seen.get("left") == 0, seen)


def test_placed_names_the_line_that_called_it(qapp, check):
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
    from ui import placed
    w = QWidget()
    try:
        v = QVBoxLayout(w)
        row = QHBoxLayout()
        row.addWidget(QLabel("a"))
        qt.take_layout_breaks()
        give = lambda: placed(v, row)  # noqa: E731
        give()
        seen = [where for _test, where in qt.take_layout_breaks()]
    finally:
        qt.close(w)
    want = [f"tests/infra/test_layout_rule.py:{_line_of(give)} QBoxLayout.addLayout"]
    check("tests: a layout with items given through ui.placed is recorded at the line that called placed, not at "
          "placed's own line in app\\ui\\__init__.py", seen == want, (seen, want))
