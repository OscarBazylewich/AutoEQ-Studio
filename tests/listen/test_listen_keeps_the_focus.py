"""Listen's card keeps the focus on the parts that it makes again (ui\\listen.py's render_versions and render_pins;
found by the verifier of the Tab sequence, 2026-11-16). A key or a click on a version's button, on Graph or ✕ of an
EQ to compare, or a new name in its name box makes those controls again. The control with the focus was taken out
with it, and Qt gave the focus to the next control of the page: Ears, where the next Space opened its list, or The
selected EQ, where the next Space added an EQ; Tab after a new name went past Graph and ✕ of each row.
Now the focus goes to the control that takes its place: the button of the same version (of the version selected,
when a key selects one), the same control of the row now in that place (else of the last row), and The selected EQ
when the list is empty (UI-RULES 30).
Two more parts of the card (2026-11-17):
- Show the names goes out of view when it is used. With the focus, it gave the focus to list A of the ABX test,
  where the next Space opened that list. Now Hide the names gets the focus: the control at its left in the same row.
- A mouse click after a new name in a name box did nothing: the click took the focus from the box, the new name
  made the rows and the versions' buttons again, and the click went to a removed control. Now the app only records
  the name while a mouse button is down, and shows it on the card when the button is up.
- A click or a drag in the name box of a different row after a new name put the caret at the end of that name with
  nothing selected: the rows were made again after the click. Now the rows stay, and only their names change.
Real mouse clicks and real keys. One page for the file (the eq_screen fixture), with a result and two EQs to compare.
Nothing is played (tests\\listen\\conftest.py stands in for the sound card)."""
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QPushButton

from helpers import eqpage, qt

COVERS = ("ui.listen",)


def _name(w):
    if w is None:
        return None
    words = w.text() if isinstance(w, (QPushButton, QCheckBox)) else ""
    return f"{type(w).__name__} {(words or w.accessibleName())[:44]!r}"


@pytest.fixture(scope="module")
def listen(eq_screen):
    """Listen's card with a result; two(): its list made two EQs to compare again (the result, and the result with
    one more filter), and the card. The list and the version heard as they were after the file's last test."""
    page = eq_screen.page
    page.choose_app("apo")
    page.set_way("auto", remember=False)
    page.activateWindow()  # (a key goes to an active window only)
    eqpage.quick_run(eq_screen)
    lis = page.listen
    was = (list(lis.pins), lis.active, lis.picked)
    lis.choose("sel")  # (the selected EQ heard, whatever a file before this one selected)
    lis.add_selected()
    page.add_filter()
    lis.add_selected()
    page.undo_all()
    both = [dict(p) for p in lis.pins]

    def two():
        lis.pins = [dict(p) for p in both]
        lis.save_pins()
        qt.pump(150)
        return lis
    yield two
    lis.pins, lis.active, lis.picked = was
    lis.save_pins()


def _click(page, w):
    """A real mouse click in the middle of a control of the card, the control in sight first."""
    page.page_area.ensureWidgetVisible(w, 0, 120)
    qt.pump(40)
    QTest.mouseClick(w, Qt.LeftButton, Qt.NoModifier, QPoint(w.width() // 2, w.height() // 2))
    qt.pump(120)


def _key(key):
    """A real key to the control with the focus: the control with the focus after it, and whether a list opened
    (closed again)."""
    QTest.keyClick(QApplication.focusWidget(), key)
    qt.pump(120)
    f = QApplication.focusWidget()
    popup = QApplication.activePopupWidget()
    if popup is not None:
        QTest.keyClick(popup, Qt.Key_Escape)
        qt.pump(60)
    return f, popup is not None


def _versions(lis):
    return [b for b in lis.ab_box.findChildren(QPushButton) if b.isVisible()]


def _rows(lis, kind):
    """The name boxes (QLineEdit), the Graph boxes (QCheckBox) or the ✕ buttons (QPushButton) of the list's rows."""
    return [w for w in lis.pins_box.findChildren(kind) if w.isVisible() and (kind is not QPushButton or w.text() == "✕")]


def _at(ws, i):
    return ws[i] if len(ws) > i else None


@pytest.mark.timeout(900)  # (a Best fit run for the result, and one more: each allowed 180 s times the time factor)
def test_the_versions_keep_the_focus(eq_screen, listen, check):
    page, lis = eq_screen.page, listen()
    bar = page.page_area.verticalScrollBar()
    # (to a version's button that is not lit, as a person gets there: Shift+Tab from the list, up to the versions)
    _click(page, _rows(lis, QLineEdit)[0])
    for _ in range(12):
        if QApplication.focusWidget() in _versions(lis):
            break
        _key(Qt.Key_Backtab)
    start = QApplication.focusWidget()
    # (what it is now: the calculation's end deletes this button)
    last = (_at(_versions(lis), 3) is start, start.isChecked() if isinstance(start, QPushButton) else None, lis.active,
            _name(start))
    eqpage.quick_run(eq_screen)  # (a calculation that ends makes the card again)
    qt.pump(150)
    f = QApplication.focusWidget()
    check("listen: a calculation that ends while a version's button that is not lit has the focus keeps the focus on "
          "that version's button, and selects no other version (the focus went to Ears)",
          last[:3] == (True, False, "sel") and f is _at(_versions(lis), 3) and not f.isChecked()
          and lis.active == "sel", (last, _name(f), lis.active))
    _click(page, _versions(lis)[0])
    at = bar.value()
    clicked = QApplication.focusWidget()
    on0 = clicked is _versions(lis)[0]
    first, opened1 = _key(Qt.Key_Space)
    on1 = first is _versions(lis)[0]
    again, opened2 = _key(Qt.Key_Space)
    on2 = again is _versions(lis)[0]
    check("listen: a click on a version's button keeps the focus on that version's button, and Space on it, two "
          "times, opens no list and does not move the page (the focus went to Ears, where the next Space opened "
          "its list)",
          lis.active == "off" and on0 and on1 and on2 and not opened1 and not opened2
          and lis.ears.currentData() == "both" and bar.value() == at,
          (lis.active, _name(clicked), _name(first), _name(again), opened1, opened2, at, bar.value()))
    right = []
    for n in (1, 2):
        f = _key(Qt.Key_Right)[0]
        b = _at(_versions(lis), n)
        right.append((_name(f), b is not None and f is b and b.isChecked()))
    out = _key(Qt.Key_Tab)[0]
    back = _key(Qt.Key_Backtab)[0]
    check("listen: the Right key on the lit version's button selects the next version and gives its button the focus, "
          "and the next Right selects the version after it (the first Right gave the focus to Ears, and the second "
          "Right selected no version); then Tab goes to Ears, and Shift+Tab back to the lit version's button",
          [ok for _n, ok in right] == [True, True] and out is lis.ears and back is _at(_versions(lis), 2)
          and bar.value() == at, (right, _name(out), _name(back), at, bar.value()))
    f = _key(Qt.Key_1)[0]
    check("listen: the key 1 while a version's button has the focus selects version 1 and gives its button the focus "
          "(the focus went to Ears)",
          lis.active == "off" and f is _versions(lis)[0] and f.isChecked(), (lis.active, _name(f)))


@pytest.mark.timeout(900)  # (the Best fit run for the result, when this test runs alone)
def test_the_eqs_to_compare_keep_the_focus(eq_screen, listen, check):
    page, lis = eq_screen.page, listen()
    bar = page.page_area.verticalScrollBar()
    before = [p["name"] for p in lis.pins]
    _click(page, _rows(lis, QLineEdit)[0])
    _key(Qt.Key_Tab)  # (no new name: Tab goes to Graph, and the rows stay)
    at = bar.value()
    one = _key(Qt.Key_Space)[0]
    shown, on1 = lis.pins[0].get("shown", True), one is _rows(lis, QCheckBox)[0]
    two = _key(Qt.Key_Space)[0]
    on2 = two is _rows(lis, QCheckBox)[0]
    check("listen: Space on Graph of an EQ to compare keeps the focus on that Graph, and the next Space sets Graph on "
          "again; the page does not move (the focus went to The selected EQ, and the next Space did not change "
          "Graph)",
          len(before) == 2 and shown is False and lis.pins[0].get("shown", True) is True and on1 and on2
          and [p["name"] for p in lis.pins] == before and bar.value() == at,
          (before, shown, _name(one), _name(two), at, bar.value()))
    _click(page, _rows(lis, QLineEdit)[0])
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_End)
    QTest.keyClicks(QApplication.focusWidget(), "x")
    tab = [_key(Qt.Key_Tab)[0]]
    on_graph = tab[0] is _rows(lis, QCheckBox)[0]
    tab.append(_key(Qt.Key_Tab)[0])
    check("listen: after a new name in the name box of an EQ to compare, Tab goes to Graph of that row, then to its ✕, "
          "and the page does not move (Tab went to The selected EQ, past Graph and ✕ of each row)",
          lis.pins[0]["name"] == before[0] + "x" and on_graph and tab[1] is _rows(lis, QPushButton)[0]
          and bar.value() == at, (lis.pins[0]["name"], [_name(w) for w in tab], at, bar.value()))
    _click(page, _rows(lis, QLineEdit)[1])
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_End)
    QTest.keyClicks(QApplication.focusWidget(), "y")
    up = _key(Qt.Key_Backtab)[0]
    on_x = up is _rows(lis, QPushButton)[0]
    _click(page, _rows(lis, QLineEdit)[0])
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_End)
    QTest.keyClicks(QApplication.focusWidget(), "z")
    enter = _key(Qt.Key_Return)[0]
    check("listen: after a new name in the name box of an EQ to compare, Shift+Tab goes to ✕ of the row above, and "
          "Enter keeps the focus in that name box (each gave the focus to The selected EQ)",
          [p["name"] for p in lis.pins] == [before[0] + "xz", before[1] + "y"] and on_x
          and enter is _rows(lis, QLineEdit)[0], ([p["name"] for p in lis.pins], _name(up), _name(enter)))
    lis = listen()
    _click(page, _rows(lis, QLineEdit)[0])
    _key(Qt.Key_Tab)
    _key(Qt.Key_Tab)  # (the ✕ of the first row)
    first = _key(Qt.Key_Space)[0]
    left = [p["name"] for p in lis.pins]
    on_next = first is _at(_rows(lis, QPushButton), 0)
    second = _key(Qt.Key_Space)[0]
    check("listen: Space on ✕ of an EQ to compare removes it and gives the focus to ✕ of the row now in its place (the "
          "focus went to The selected EQ, where the next Space added an EQ); Space on that ✕ removes the last EQ "
          "and gives the focus to The selected EQ, the control below the empty list",
          left == before[1:] and on_next and lis.pins == [] and second is lis.add_sel_btn,
          (left, _name(first), len(lis.pins), _name(second)))
    lis = listen()
    _click(page, _rows(lis, QLineEdit)[1])
    _key(Qt.Key_Tab)
    _key(Qt.Key_Tab)  # (the ✕ of the last row)
    f = _key(Qt.Key_Space)[0]
    check("listen: Space on ✕ of the last EQ of the list removes it and gives the focus to ✕ of the row above it (the "
          "focus went to The selected EQ)",
          [p["name"] for p in lis.pins] == before[:1] and f is _at(_rows(lis, QPushButton), 0),
          ([p["name"] for p in lis.pins], _name(f)))
    lis = listen()
    _click(page, _rows(lis, QCheckBox)[1])
    graph = QApplication.focusWidget()
    on_graph, shown = graph is _rows(lis, QCheckBox)[1], [p.get("shown", True) for p in lis.pins]
    _click(page, _rows(lis, QPushButton)[0])
    x = QApplication.focusWidget()
    check("listen: a click on Graph of an EQ to compare keeps the focus on that Graph, and a click on ✕ gives the "
          "focus to ✕ of the row now in its place (each gave the focus to The selected EQ)",
          on_graph and shown == [True, False] and [p["name"] for p in lis.pins] == before[1:]
          and x is _at(_rows(lis, QPushButton), 0), (_name(graph), shown, len(lis.pins), _name(x)))


@pytest.mark.timeout(900)  # (the Best fit run for the result, when this test runs alone)
def test_show_the_names_keeps_the_focus_in_its_row(eq_screen, listen, check):
    page, lis = eq_screen.page, listen()
    bar = page.page_area.verticalScrollBar()
    seen = {}
    for way in ("a click", "Space"):
        _click(page, lis.blind)  # (Hide the names on: Show the names comes into view at its right)
        there = lis.blind.isChecked() and lis.reveal_btn.isVisible()
        at = bar.value()
        if way == "a click":
            _click(page, lis.reveal_btn)
        else:
            there = there and _key(Qt.Key_Tab)[0] is lis.reveal_btn
            _key(Qt.Key_Space)
        f = QApplication.focusWidget()
        gone, names = not lis.reveal_btn.isVisible(), [b.text() for b in _versions(lis)]
        after, opened = _key(Qt.Key_Space)
        seen[way] = (there, gone, bool(names) and all(" = " in n for n in names), f is lis.blind, after is lis.blind,
                     opened, lis.blind.isChecked(), bar.value() - at, _name(f), _name(after))
        lis.blind.setChecked(False)  # (as it was, also when the Space above did not clear it)
        qt.pump(60)
    good = (True, True, True, True, True, False, False, 0)
    check("listen: Show the names, used with a click or with Space, goes out of view and gives the focus to Hide the "
          "names, the control at its left in the same row; the page does not move, and the next Space clears Hide "
          "the names and opens no list (the focus went to list A of the ABX test, and the next Space opened that "
          "list)", all(seen[way][:8] == good for way in seen), seen)


@pytest.mark.timeout(900)  # (the Best fit run for the result, when this test runs alone)
def test_a_click_after_a_new_name_operates_its_control(eq_screen, listen, check):
    page, lis = eq_screen.page, listen()
    before = [p["name"] for p in lis.pins]

    def new_name(row, letter):
        """A click in the name box of a row, then a letter at the end of its name (not recorded yet)."""
        _click(page, _rows(lis, QLineEdit)[row])
        QTest.keyClick(QApplication.focusWidget(), Qt.Key_End)
        QTest.keyClicks(QApplication.focusWidget(), letter)

    new_name(0, "x")
    _click(page, _rows(lis, QCheckBox)[1])
    f = QApplication.focusWidget()
    check("listen: after a new name in the name box of an EQ to compare, a mouse click on Graph of a different row "
          "records the name and clears that Graph, and that Graph has the focus (the click went to a removed "
          "control: Graph did not change)",
          [p["name"] for p in lis.pins] == [before[0] + "x", before[1]]
          and [p.get("shown", True) for p in lis.pins] == [True, False] and f is _at(_rows(lis, QCheckBox), 1)
          and not f.isChecked() and _at(_rows(lis, QLineEdit), 0).text() == before[0] + "x",
          ([p["name"] for p in lis.pins], [p.get("shown", True) for p in lis.pins], _name(f)))
    lis = listen()
    new_name(0, "y")
    _click(page, _rows(lis, QPushButton)[1])
    f = QApplication.focusWidget()
    check("listen: after a new name in the name box of an EQ to compare, a mouse click on ✕ of a different row records "
          "the name and removes the EQ of that row (the click went to a removed control: the EQ stayed in the list)",
          [p["name"] for p in lis.pins] == [before[0] + "y"] and f is _at(_rows(lis, QPushButton), 0),
          ([p["name"] for p in lis.pins], _name(f)))
    lis = listen()
    new_name(1, "z")
    _click(page, _rows(lis, QCheckBox)[1])
    check("listen: after a new name in the name box of an EQ to compare, a mouse click on Graph of the same row "
          "records the name and clears that Graph",
          [p["name"] for p in lis.pins] == [before[0], before[1] + "z"]
          and [p.get("shown", True) for p in lis.pins] == [True, False],
          ([p["name"] for p in lis.pins], [p.get("shown", True) for p in lis.pins]))
    lis = listen()
    lis.choose("sel")
    qt.pump(60)
    new_name(1, "v")
    _click(page, _versions(lis)[0])
    f = QApplication.focusWidget()
    words = [b.text() for b in _versions(lis)]
    check("listen: after a new name in the name box of an EQ to compare, a mouse click on a version's button records "
          "the name and selects that version; the button of the EQ shows the new name",
          lis.active == "off" and f is _at(_versions(lis), 0) and f.isChecked()
          and [p["name"] for p in lis.pins] == [before[0], before[1] + "v"] and words[-1].endswith(before[1] + "v"),
          (lis.active, _name(f), [p["name"] for p in lis.pins], words))
    lis = listen()
    new_name(0, "w")
    _click(page, _rows(lis, QLineEdit)[1])
    f = QApplication.focusWidget()
    QTest.keyClick(f, Qt.Key_End)
    QTest.keyClicks(f, "q")
    enter = _key(Qt.Key_Return)[0]
    check("listen: after a new name in the name box of an EQ to compare, a mouse click in the name box of a "
          "different row records the name and gives that box the focus: the letters typed then go into that box",
          [p["name"] for p in lis.pins] == [before[0] + "w", before[1] + "q"] and enter is _at(_rows(lis, QLineEdit), 1),
          ([p["name"] for p in lis.pins], _name(f), _name(enter)))
    lis = listen()
    new_name(0, "u")
    _click(page, lis.abx_a)
    popup = QApplication.activePopupWidget()
    in_list = [lis.abx_a.itemText(i) for i in range(lis.abx_a.count())]
    if popup is not None:
        QTest.keyClick(popup, Qt.Key_Escape)
    qt.pump(120)
    words = [b.text() for b in _versions(lis)]
    check("listen: after a new name in the name box of an EQ to compare, a mouse click on list A of the ABX test "
          "records the name and opens that list with the new name in it; the button of the EQ shows the new name "
          "when the list closes",
          popup is not None and before[0] + "u" in in_list and [p["name"] for p in lis.pins] == [before[0] + "u", before[1]]
          and len(words) == 4 and words[2].endswith(before[0] + "u"), (popup is not None, in_list, words))
    listen()
    lis.choose("sel")


@pytest.mark.timeout(900)  # (the Best fit run for the result, when this test runs alone)
def test_a_click_in_a_name_box_after_a_new_name_keeps_its_caret(eq_screen, listen, check):
    page = eq_screen.page

    def new_name(lis, letters):
        _click(page, _rows(lis, QLineEdit)[0])
        QTest.keyClick(QApplication.focusWidget(), Qt.Key_End)
        QTest.keyClicks(QApplication.focusWidget(), letters)

    def press(new, drag):
        """A mouse click between two letters near the start of the name box of row 2, or a drag from there to the
        right; new: after a new name in row 1. Whether that box has the focus, where its caret is, what is
        selected, and its text after the letter Q."""
        lis = listen()
        if new:
            new_name(lis, "x")
        box = _rows(lis, QLineEdit)[1]
        page.page_area.ensureWidgetVisible(box, 0, 120)
        qt.pump(40)
        y = box.height() // 2
        QTest.mousePress(box, Qt.LeftButton, Qt.NoModifier, QPoint(40, y))
        qt.pump(40)
        for x in (60, 80, 100) if drag else ():
            QTest.mouseMove(box, QPoint(x, y))
            qt.pump(20)
        QTest.mouseRelease(box, Qt.LeftButton, Qt.NoModifier, QPoint(100 if drag else 40, y))
        qt.pump(150)
        f = QApplication.focusWidget()
        if not isinstance(f, QLineEdit):
            return _name(f)
        at = (f is _at(_rows(lis, QLineEdit), 1), f.cursorPosition(), f.selectedText())
        QTest.keyClicks(f, "Q")
        typed = f.text()
        f.setText(lis.pins[1]["name"])  # (the letter is not recorded)
        return (*at, typed)

    seen = {f"{'a drag' if drag else 'a click'}{', after a new name' if new else ''}": press(new, drag)
            for drag in (False, True) for new in (False, True)}
    click, drag = seen["a click"], seen["a drag"]
    check("listen: after a new name in the name box of an EQ to compare, a mouse click in the name box of a different "
          "row puts the caret where the click was, and a drag there selects the letters under it: the letter typed "
          "then goes there, as with no new name before (the caret went to the end of the name with nothing "
          "selected, and the letter went there)",
          isinstance(click, tuple) and click[0] and 0 < click[1] < len(click[3]) - 1 and bool(drag[2])
          and seen["a click, after a new name"] == click and seen["a drag, after a new name"] == drag, seen)
    lis = listen()
    before = lis.pins[0]["name"]
    new_name(lis, "x ")  # (the space after the letter is not a part of the name)
    box = _rows(lis, QLineEdit)[1]
    QTest.mouseClick(box, Qt.LeftButton, Qt.NoModifier, QPoint(40, box.height() // 2))
    qt.pump(150)
    row = [_at(_rows(lis, kind), 0) for kind in (QLineEdit, QCheckBox, QPushButton)]
    shown = (lis.pins[0]["name"], row[0].text(), [w.accessibleName() for w in row], _versions(lis)[2].text())
    check("listen: after that click, the card shows the new name: in its name box, on the button of its version, and "
          "in the names of its row that a screen reader reads",
          shown[:2] == (before + "x", before + "x") and all(before + "x" in n for n in shown[2])
          and shown[2][0] == f"Name of {before}x" and shown[3].endswith(before + "x"), shown)
    listen()
