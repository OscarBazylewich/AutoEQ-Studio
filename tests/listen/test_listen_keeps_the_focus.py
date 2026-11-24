"""Listen's card keeps the focus on the parts that it makes again (ui\\listen.py's render_versions and render_pins;
found by the verifier of the Tab sequence, 2026-11-16). A key or a click on a version's button, on Graph or ✕ of an
EQ to compare, or a new name in its name box made those controls again. The control with the focus was taken out
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
Enter after a new name in a name box (2026-11-22) made the rows again, as a calculation that ended did. The new name
box of that row had its caret at the end of the name with nothing selected, and the next letter went there. A new
box now gets the caret and the selection of the box that it replaces, when it has the same text. When the app records
the name differently (no space at its two ends, one space for each group of spaces, 80 characters at most), the caret
stays at the end of the name: a position counted again went between the two halves of an emoji (2 positions in a
name box), and the next letter took the emoji out of the name.
A name box shows the recorded name (2026-11-22). After Enter, or when the focus went to a different control, the
box kept text that the name did not have: a space at one end, the letters after 80 characters, or no text when
the person removed the name. Now the box shows the recorded name then. While the person uses a different
program, the box with the focus keeps its text: the person can get a name from that program. Back from that
program, Tab or a click with no new letter shows the recorded name too (Qt told the end of the edit only when the
program changed). The recorded name goes into the box as an edit: Ctrl+Z gives the typed text again.
A new name keeps its name box (2026-11-22). Enter after a new name, Tab, and a change to a different program made
the rows again, as a mouse click did before 2026-11-17. After Enter, the name box was a new control: Ctrl+Z did
not take the typed letters out again, and a name wider than its box moved under the caret. A space typed before
a change to a different program went out of the box. Now the rows stay, and only the names on the card change.
A calculation that ends keeps the rows (2026-11-22): the list is the same. The rows were made again, and a person
who typed in a name box then got a new box: the half-typed name was recorded, a space at its end went out of the
box, a box with no text got the recorded name again, and Ctrl+Z did nothing. Now the rows are made again only when
the list has different EQs (one added or removed, Graph, another IEM).
Real mouse clicks and real keys. One page for the file (the eq_screen fixture), with a result and two EQs to compare.
Nothing is played (tests\\listen\\conftest.py stands in for the sound card)."""
import pytest
from PySide6.QtCore import QEvent, QPoint, QRect, Qt
from PySide6.QtGui import QFocusEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QLineEdit, QPushButton

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


def _in_sight(page, *ws):
    """Is each of the controls all in the page's view?"""
    vp = page.page_area.viewport()
    return all(vp.rect().contains(QRect(w.mapTo(vp, QPoint(0, 0)), w.size())) for w in ws)


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
    # (2026-11-22: Ears in sight before the keys below. Tab to a control out of sight moves the page to it, as a
    # scroll area does. With the font Segoe UI and no Segoe UI Variable, as on GitHub's machine, the click left the
    # versions' buttons at the bottom edge of the view and Ears 38 px below it: the page moved 88 px at Tab)
    page.page_area.ensureWidgetVisible(lis.ears, 0, 120)
    qt.pump(40)
    _click(page, _versions(lis)[0])
    at = bar.value()
    seen = _in_sight(page, lis.ears, *_versions(lis))
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
          "Right selected no version); then Tab goes to Ears, and Shift+Tab back to the lit version's button; with "
          "Ears and the versions' buttons all in sight before the keys, the page does not move",
          [ok for _n, ok in right] == [True, True] and out is lis.ears and back is _at(_versions(lis), 2)
          and seen and bar.value() == at, (right, _name(out), _name(back), seen, at, bar.value()))
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


def _keys(key, times=1, shift=False):
    """A real key to the control with the focus, a number of times; shift: with Shift down (it selects letters)."""
    for _ in range(times):
        QTest.keyClick(QApplication.focusWidget(), key, Qt.ShiftModifier if shift else Qt.NoModifier)
    qt.pump(40)


EMOJI = "\U0001F3A7"  # (headphones: one letter for Python, 2 positions in a name box, as most emoji)


def _symbol(text):
    """A symbol to the control with the focus, as one real key event that has the whole symbol as its text (no
    test opens the emoji panel of Windows; a probe with QTest.keyClicks and an emoji stopped its process,
    2026-11-22)."""
    for action in (QTest.KeyAction.Press, QTest.KeyAction.Release):
        QTest.sendKeyEvent(action, QApplication.focusWidget(), Qt.Key_unknown, text, Qt.NoModifier)
    qt.pump(40)


def _units(text):
    """The number of positions of a text in a name box (Qt counts in UTF-16: 2 for an emoji as EMOJI)."""
    return len(text.encode("utf-16-le")) // 2


@pytest.mark.timeout(900)  # (the Best fit run for the result, when this test runs alone)
def test_enter_after_a_new_name_keeps_the_caret_of_its_name_box(eq_screen, listen, check):
    page = eq_screen.page

    def start():
        """The list made two EQs again, then a real mouse click between two letters near the start of the name box
        of row 1: the card, the name of that EQ, and where the click put the caret."""
        lis = listen()
        box = _rows(lis, QLineEdit)[0]
        page.page_area.ensureWidgetVisible(box, 0, 120)
        qt.pump(40)
        QTest.mouseClick(box, Qt.LeftButton, Qt.NoModifier, QPoint(40, box.height() // 2))
        qt.pump(120)
        return lis, lis.pins[0]["name"], box.cursorPosition()

    def write(letters):
        QTest.keyClicks(QApplication.focusWidget(), letters)

    def now(lis):
        """The name box of row 1 as it is now: whether it has the focus, its text, its caret and the letters
        selected in it; then the name of its EQ in the list of the card."""
        box = _rows(lis, QLineEdit)[0]
        return (QApplication.focusWidget() is box, box.text(), box.cursorPosition(), box.selectedText(),
                lis.pins[0]["name"])

    lis, name, c = start()
    _key(Qt.Key_Return)
    base = now(lis)
    check("listen: Enter in the name box of an EQ to compare, with no new name, keeps the caret where a click put "
          "it, between two letters of the name",
          0 < c < len(name) - 3 and base == (True, name, c, "", name), (c, base))
    write("x")
    _key(Qt.Key_Return)
    one = now(lis)
    saved = [e.get("name") for e in page.svc.call("/api/listen", {"device": lis.pins_for}).get("eqs") or []]
    button = _versions(lis)[2].text()
    write("y")
    two = now(lis)
    x, xy, xz = (name[:c] + new + name[c:] for new in ("x", "xy", "xz"))
    check("listen: a letter typed in the middle of the name of an EQ to compare, then Enter: the name box of that row "
          "has the focus with the caret after that letter, and the next letter goes there (the caret went to the "
          "end of the name, and the next letter went there)",
          one[:4] == (True, x, c + 1, "") and two[:4] == (True, xy, c + 2, ""), (c, one[:4], two[:4]))
    check("listen: that Enter records the new name: the list of the card and its file have it, and the button of its "
          "version shows it", one[4] == x and saved[:1] == [x] and button.endswith(x), (one[4], saved, button))
    _keys(Qt.Key_Left, 2, shift=True)  # ("xy" selected, with the caret at its left end)
    _key(Qt.Key_Return)
    left = now(lis)
    _keys(Qt.Key_Right, shift=True)  # (one letter less is selected then, as the caret is at the left end)
    left_end = now(lis)[2:4]
    write("z")  # (in the place of the selected "y")
    _keys(Qt.Key_Right, 3, shift=True)  # (three letters selected, with the caret at their right end)
    _key(Qt.Key_Return)
    right = now(lis)
    _keys(Qt.Key_Left, shift=True)
    right_end = now(lis)[2:4]
    check("listen: letters selected with Shift and an arrow key after a typed letter, then Enter: the name is "
          "recorded, and the same letters stay selected in the name box of that row with the caret at the same end "
          "of them, the left end or the right end (nothing was selected, with the caret at the end of the name)",
          left == (True, xy, c, "xy", xy) and left_end == (c + 1, "y")
          and right == (True, xz, c + 5, name[c:c + 3], xz) and right_end == (c + 4, name[c:c + 2]),
          (c, left[0], left[2:], left_end, right[0], right[2:], right_end))
    lis, name, c = start()
    write("x")
    eqpage.quick_run(eq_screen)  # (a calculation that ends: it made the rows again, as Enter after a new name did)
    qt.pump(150)
    ended = now(lis)
    write("y")
    ended_next = now(lis)[1]
    _key(Qt.Key_Return)
    check("listen: a calculation that ends after a letter typed in the middle of the name of an EQ to compare keeps "
          "the focus in that name box with the caret after that letter, and the next letter goes there (the caret "
          "went to the end of the name, and the next letter went there)",
          ended[:4] == (True, name[:c] + "x" + name[c:], c + 1, "") and ended_next == name[:c] + "xy" + name[c:],
          (c, ended[:4], ended_next))
    # (a name that the app records with fewer characters than the box has: the box gets the recorded name, with
    # the caret at its end)
    lis, name, c = start()
    _keys(Qt.Key_Left, c)  # (the caret to the start of the name, with the arrow key)
    write(" q")
    _key(Qt.Key_Return)
    lead = now(lis)
    write("r")
    lead_next = now(lis)[1]
    _key(Qt.Key_Return)  # (recorded: no letter that is not recorded stays in the box when the list is made again)
    lis, name, c = start()
    write("a  b")
    _key(Qt.Key_Return)
    spaces = now(lis)
    write("c")
    spaces_next = now(lis)[1]
    _key(Qt.Key_Return)
    lis, name, c = start()
    _keys(Qt.Key_End)
    write("w" * (90 - len(name)))
    _keys(Qt.Key_Left, 20, shift=True)  # (the last 20 of the 90 characters selected, with the caret at their left end)
    _key(Qt.Key_Return)
    cut = now(lis)
    write("v")
    cut_next = now(lis)[1]
    _key(Qt.Key_Return)
    q, a_b, long = "q" + name, name[:c] + "a b" + name[c:], (name + "w" * 90)[:80]
    check("listen: Enter after a new name that the app records with fewer characters (a space at its start, two "
          "spaces between two letters, more than 80 characters): the name box of that row has the focus with the "
          "caret at the end of the recorded name and nothing selected, and the next letter goes to the end of the "
          "name",
          lead == (True, q, len(q), "", q) and lead_next == q + "r"
          and spaces == (True, a_b, len(a_b), "", a_b) and spaces_next == a_b + "c"
          and cut == (True, long, 80, "", long) and cut_next == long + "v",
          (c, len(name), lead[:4], lead_next, spaces[:4], spaces_next, cut[0], len(cut[1]), cut[2:4], len(cut_next)))
    # (an emoji at the end of the name, and a space after it that the app does not record: a different text)
    lis, name, c = start()
    _keys(Qt.Key_End)
    _symbol(EMOJI)
    held = now(lis)[1:3]
    write(" ")
    _key(Qt.Key_Return)
    end = now(lis)
    write("y")
    _key(Qt.Key_Return)
    last = now(lis)
    saved = [e.get("name") for e in page.svc.call("/api/listen", {"device": lis.pins_for}).get("eqs") or []]
    button = _versions(lis)[2].text()
    n, new = _units(name), name + EMOJI
    check("listen: an emoji at the end of the name of an EQ to compare (2 positions in the name box), a space, then "
          "Enter: the name is recorded with no space, and the caret is at the end of the name, after the emoji; "
          "the next letter and Enter put that letter after the emoji in the name box, in the list of the card, in "
          "its file and on the button of its version (the caret went between the two halves of the emoji, and the "
          "next letter took the emoji out of the name)",
          held == (new, n + 2) and end == (True, new, n + 2, "", new)
          and last == (True, new + "y", n + 3, "", new + "y") and saved[:1] == [new + "y"]
          and button.endswith(new + "y"),
          ascii((n, held[1], end[0], end[2], _units(end[1]), end[3], last[:3], last[4], saved[:1], button)))
    # (an emoji in the middle of the name: the recorded name is the text of the box, which stays as it is)
    lis, name, c = start()
    _symbol(EMOJI)
    _key(Qt.Key_Return)
    mid = now(lis)
    write("y")
    mid_next = now(lis)[1:3]
    _key(Qt.Key_Return)
    new = name[:c] + EMOJI + name[c:]
    check("listen: an emoji typed in the middle of the name of an EQ to compare, then Enter: the name is recorded "
          "with the emoji, the caret is immediately after the emoji, and the next letter goes there (the caret "
          "went to the end of the name, and the next letter went there)",
          mid == (True, new, c + 2, "", new) and mid_next == (name[:c] + EMOJI + "y" + name[c:], c + 3)
          and lis.pins[0]["name"] == name[:c] + EMOJI + "y" + name[c:],
          ascii((c, mid, mid_next, lis.pins[0]["name"])))
    listen()


def _in_name_box(page, listen):
    """The list made two EQs again, then a real mouse click between two letters near the start of the name box of
    row 1: the card, and the name of that EQ."""
    lis = listen()
    box = _rows(lis, QLineEdit)[0]
    page.page_area.ensureWidgetVisible(box, 0, 120)
    qt.pump(40)
    QTest.mouseClick(box, Qt.LeftButton, Qt.NoModifier, QPoint(40, box.height() // 2))
    qt.pump(120)
    return lis, lis.pins[0]["name"]


def _name_box(lis):
    """The name box of row 1 as it is now: whether it has the focus, its text, its caret and the letters selected
    in it; then the name of its EQ in the list of the card."""
    box = _rows(lis, QLineEdit)[0]
    return (QApplication.focusWidget() is box, box.text(), box.cursorPosition(), box.selectedText(),
            lis.pins[0]["name"])


def _write(letters):
    QTest.keyClicks(QApplication.focusWidget(), letters)
    qt.pump(40)


def _ctrl(key):
    """A real key with Ctrl down to the control with the focus (Ctrl+A selects the full name)."""
    QTest.keyClick(QApplication.focusWidget(), key, Qt.ControlModifier)
    qt.pump(40)


def _window_has_the_keyboard(has):
    """The person goes to a different program (has False) or comes back (has True): the event that Qt then gives to
    the control with the focus. That control stays the focus control of its window. (No test makes the window of a
    different program.)"""
    kind = QEvent.FocusIn if has else QEvent.FocusOut
    QApplication.sendEvent(QApplication.focusWidget(), QFocusEvent(kind, Qt.ActiveWindowFocusReason))
    qt.pump(100)


@pytest.mark.timeout(900)  # (the Best fit run for the result, when this test runs alone)
def test_a_name_box_shows_the_recorded_name(eq_screen, listen, check):
    page = eq_screen.page
    lis, name = _in_name_box(page, listen)
    _keys(Qt.Key_End)
    _write(" ")
    _key(Qt.Key_Return)
    end = _name_box(lis)
    lis, name = _in_name_box(page, listen)
    _keys(Qt.Key_Home)
    _write(" ")
    _key(Qt.Key_Return)
    lead = _name_box(lis)
    same = (True, name, len(name), "", name)
    check("listen: a space typed at the end or at the start of the name of an EQ to compare, then Enter: the name box "
          "shows the recorded name, which has no space at its two ends, with the caret at its end (the box kept the "
          "space, and the recorded name had none)", end == same and lead == same, (name, end, lead))
    lis, name = _in_name_box(page, listen)
    _keys(Qt.Key_End)
    _write("w" * (80 - len(name)))
    _key(Qt.Key_Return)
    full = name + "w" * (80 - len(name))
    _write("v")
    _key(Qt.Key_Return)
    enter = _name_box(lis)
    _write("u")
    on = _key(Qt.Key_Tab)[0]
    tab = _name_box(lis)
    button = _versions(lis)[2].text()
    check("listen: one more letter at the end of a name of 80 characters, then Enter or Tab: the name box shows the "
          "80 recorded characters, as the button of its version (the box kept each letter: 81 characters, then 82, "
          "and the recorded name had 80)",
          enter == (True, full, 80, "", full) and tab[1] == full and tab[4] == full
          and on is _at(_rows(lis, QCheckBox), 0) and button.endswith(full),
          (len(full), enter[0], len(enter[1]), enter[2:4], len(enter[4]), len(tab[1]), len(tab[4]), _name(on),
           len(button)))
    lis, name = _in_name_box(page, listen)
    _ctrl(Qt.Key_A)
    _keys(Qt.Key_Delete)
    held = _name_box(lis)[1]
    _key(Qt.Key_Return)
    enter = _name_box(lis)
    _ctrl(Qt.Key_A)
    _keys(Qt.Key_Delete)
    on = _key(Qt.Key_Tab)[0]
    tab = _name_box(lis)
    check("listen: Enter or Tab in the name box of an EQ to compare with no text in it: the EQ keeps its name, and the "
          "name box shows that name again (the box stayed empty)",
          held == "" and enter == same and on is _at(_rows(lis, QCheckBox), 0) and tab[1] == name and tab[4] == name,
          (name, held, enter, _name(on), tab))
    lis, name = _in_name_box(page, listen)
    _ctrl(Qt.Key_A)
    _keys(Qt.Key_Delete)
    _window_has_the_keyboard(False)
    away = _name_box(lis)
    _window_has_the_keyboard(True)
    _write("N")
    back = _name_box(lis)
    _key(Qt.Key_Return)
    new = _name_box(lis)
    check("listen: the name box of an EQ to compare with no text in it stays empty while the person uses a different "
          "program (the person can get a name there), and the letter typed after that is the new name",
          away == (True, "", 0, "", name) and back == (True, "N", 1, "", name) and new == (True, "N", 1, "", "N"),
          (name, away, back, new))
    # (text that is not the recorded name, a different program, back, then Tab or a click with no new letter: Qt
    # tells the end of an edit when the program changes, and tells no second one at the Tab or the click)
    name = listen().pins[0]["name"]
    texts = {"two spaces between two letters": ("a  b", "a b"), "85 letters": ("w" * 85, "w" * 80),
             "spaces at the start": ("  My", "My"), "no text": ("", name), "a space at the end": (name + " ", name)}
    seen = {}
    for way in ("Tab", "a click"):
        for case, (text, recorded) in texts.items():
            lis, _name_was = _in_name_box(page, listen)
            _ctrl(Qt.Key_A)
            _keys(Qt.Key_Delete)
            _write(text)
            _window_has_the_keyboard(False)
            away = _rows(lis, QLineEdit)[0].text()
            _window_has_the_keyboard(True)
            if way == "Tab":
                _key(Qt.Key_Tab)
            else:
                _click(page, _versions(lis)[0])  # (a version's button: its click does not make the rows again)
            box = _rows(lis, QLineEdit)[0]
            seen[f"{case}, {way}"] = (away == text, box.text() == recorded, lis.pins[0]["name"] == recorded,
                                      QApplication.focusWidget() is not box, len(box.text()), len(lis.pins[0]["name"]))
    check("listen: text typed in the name box of an EQ to compare, then a different program (the box keeps the text), "
          "then Tab or a click on a different control with no new letter: the name box shows the recorded name (the "
          "box kept its text: two spaces between two letters, 85 letters, spaces at the start, no text, or a space "
          "at the end)", all(v[:4] == (True, True, True, True) for v in seen.values()), seen)
    listen().choose("sel")  # (the selected EQ heard again, as before the clicks on a version's button)


@pytest.mark.timeout(900)  # (the Best fit run for the result, when this test runs alone)
def test_a_new_name_keeps_its_name_box(eq_screen, listen, check):
    page = eq_screen.page
    lis, name = _in_name_box(page, listen)
    c = _name_box(lis)[2]
    abc = name[:c] + "abc" + name[c:]
    _write("abc")
    _key(Qt.Key_Return)
    after = _name_box(lis)
    _ctrl(Qt.Key_Z)
    undone = _name_box(lis)
    _key(Qt.Key_Return)
    again = _name_box(lis)
    check("listen: letters typed in the name of an EQ to compare, then Enter, then Ctrl+Z: the letters go out of the "
          "name box, as in a text box of Windows, and the next Enter records the name without them (Ctrl+Z did "
          "nothing: after Enter, the name box was a new control with no step to undo)",
          0 < c < len(name) and after == (True, abc, c + 3, "", abc) and undone[:2] == (True, name)
          and undone[4] == abc and again[:2] == (True, name) and again[4] == name, (c, after, undone, again))
    lis, name = _in_name_box(page, listen)
    _keys(Qt.Key_End)
    _write("abc ")
    _key(Qt.Key_Return)
    after = _name_box(lis)
    steps = []
    for _ in range(3):
        _ctrl(Qt.Key_Z)
        steps.append(_name_box(lis)[1])
    _key(Qt.Key_Return)
    again = _name_box(lis)
    check("listen: letters and a space typed at the end of the name of an EQ to compare, then Enter (the name is "
          "recorded with no space at its end, and the box shows it), then Ctrl+Z: the first one puts the typed text "
          "into the box again, the second one takes it out, and the next Enter records the name without the "
          "letters (Ctrl+Z did nothing: the box got the recorded name as a new text, with no step to undo)",
          after == (True, name + "abc", len(name) + 3, "", name + "abc") and steps == [name + "abc ", name, name]
          and again[:2] == (True, name) and again[4] == name, (after, steps, again))
    lis, name = _in_name_box(page, listen)
    _ctrl(Qt.Key_A)
    _write("W" * 75)
    _key(Qt.Key_Return)
    box = _rows(lis, QLineEdit)[0]
    wide = (box.fontMetrics().horizontalAdvance(box.text()), box.width())
    _keys(Qt.Key_Left, 20)  # (the caret from the end of the name to its middle: the box shows the end of the name)
    _write("i")
    typed = (box.text(), box.cursorPosition(), box.cursorRect().x())
    _key(Qt.Key_Return)
    box = _rows(lis, QLineEdit)[0]
    entered = (box.text(), box.cursorPosition(), box.cursorRect().x())
    check("listen: a letter typed in the middle of a name of an EQ to compare that is wider than its box, then Enter: "
          "the name stays where it is in the box, and the caret also (the name moved under the caret: 254 px in a "
          "box of 744 px)",
          wide[0] > wide[1] and typed == entered and typed[:2] == ("W" * 55 + "i" + "W" * 20, 56)
          and lis.pins[0]["name"] == typed[0], (wide, typed[1:], entered[1:], len(lis.pins[0]["name"])))
    lis, name = _in_name_box(page, listen)
    _ctrl(Qt.Key_A)
    _write("My ")
    _window_has_the_keyboard(False)
    away = _name_box(lis)
    _window_has_the_keyboard(True)
    _write("EQ")
    back = _name_box(lis)
    _key(Qt.Key_Return)
    new = _name_box(lis)
    check("listen: a word and a space typed in the name box of an EQ to compare, then a different program, then a "
          "second word: the name box keeps the space while the person uses that program, and the name has the two "
          "words with the space between them (the box lost the space, and the two words became one word)",
          away == (True, "My ", 3, "", "My") and back == (True, "My EQ", 5, "", "My")
          and new == (True, "My EQ", 5, "", "My EQ"), (name, away, back, new))
    listen()


@pytest.mark.timeout(1500)  # (the Best fit run for the result, and three more: each allowed 180 s times the time factor)
def test_a_calculation_that_ends_keeps_a_name_box_as_it_is(eq_screen, listen, check):
    page = eq_screen.page

    def calculate(lis):
        """A calculation that ends while the name box of row 1 has the focus: whether that box is the same control
        after it."""
        box = _rows(lis, QLineEdit)[0]
        eqpage.quick_run(eq_screen)
        qt.pump(150)
        return _rows(lis, QLineEdit)[0] is box

    lis, name = _in_name_box(page, listen)
    _ctrl(Qt.Key_A)
    _keys(Qt.Key_Delete)
    kept = calculate(lis)
    ended = _name_box(lis)
    _write("N")
    typed = _name_box(lis)
    _key(Qt.Key_Return)
    new = _name_box(lis)
    check("listen: a calculation that ends while the name box of an EQ to compare has no text (the person removed the "
          "name to type a new name): the box stays empty with the focus, and the letter typed then is the new name "
          "(the recorded name came into the box again, and the letter went to its end)",
          kept and ended == (True, "", 0, "", name) and typed == (True, "N", 1, "", name)
          and new == (True, "N", 1, "", "N"), (name, kept, ended, typed, new))
    lis, name = _in_name_box(page, listen)
    _ctrl(Qt.Key_A)
    _write("My ")
    kept = calculate(lis)
    ended = _name_box(lis)
    _write("EQ")
    typed = _name_box(lis)
    _key(Qt.Key_Return)
    new = _name_box(lis)
    check("listen: a calculation that ends after a word and a space typed in the name box of an EQ to compare: the box "
          "keeps the space, the name is recorded only at Enter, and the second word typed then comes after the "
          "space (the calculation recorded the first word, the space went out of the box, and the two words became "
          "one word)",
          kept and ended == (True, "My ", 3, "", name) and typed == (True, "My EQ", 5, "", name)
          and new == (True, "My EQ", 5, "", "My EQ"), (name, kept, ended, typed, new))
    lis, name = _in_name_box(page, listen)
    _write("abc")
    kept = calculate(lis)
    _ctrl(Qt.Key_Z)
    undone = _name_box(lis)
    check("listen: letters typed in the name of an EQ to compare, then a calculation that ends, then Ctrl+Z: the "
          "letters go out of the name box (Ctrl+Z did nothing: the name box was a new control, and the calculation "
          "recorded the name with the letters)",
          kept and undone[:2] == (True, name) and undone[4] == name, (name, kept, undone))
    # (the rows are made again when the list has a different EQ: History's Keep to compare adds one from its window,
    # while the name box is the focus control of the main window)
    lis, name = _in_name_box(page, listen)
    _keys(Qt.Key_Right, 3, shift=True)
    box, before = _rows(lis, QLineEdit)[0], _name_box(lis)
    added = lis.add("From History", [{"type": "PK", "freq": 1234, "gain": 2, "q": 1}], say=lambda *_a: None)
    qt.pump(150)
    boxes = _rows(lis, QLineEdit)
    after = _name_box(lis)
    check("listen: an EQ that comes into the list while the name box of a different EQ has the focus (Keep to compare "
          "in the window of History): the list shows the new EQ in a new row, and the name box keeps the focus, its "
          "caret and its selected letters",
          added and len(before[3]) == 3 and after == before and [b.text() for b in boxes] == [p["name"] for p in lis.pins]
          and len(boxes) == 3 and boxes[2].text() == "From History" and boxes[0] is not box,
          (added, before, after, [b.text() for b in boxes], boxes[0] is box))
    # (an empty list has one line, which tells whether a measurement is selected: a manual EQ shows the card with no
    # measurement, and the measurement selected then has a list with no EQs. The two lists are empty: the line
    # is made again for the measurement)
    lis = listen()
    device = lis.pins_for

    def line():
        return [w.text() for w in lis.pins_box.findChildren(QLabel) if w.isVisible() and w.text() != "■"]

    lis.pins = []
    lis.save_pins()  # (the list of this measurement has no EQs, on the card and in its file)
    qt.pump(60)
    none = line()
    lis.pins, lis.pins_for = [], None  # (the card as it is with no measurement)
    lis.refresh()
    qt.pump(60)
    no_measurement = line()
    lis.load_pins(device)  # (the measurement comes, as the page tells the card)
    qt.pump(60)
    measurement = line()
    check("listen: the line of an empty list of EQs to compare follows the measurement: with no measurement it tells "
          "to select one, and when a measurement with no EQs comes it tells how to add an EQ",
          lis.pins_for == device and none == measurement and len(none) == 1 and none[0].startswith("No saved EQs yet.")
          and len(no_measurement) == 1 and no_measurement[0] == "Select a measurement",
          (none, no_measurement, measurement))
    listen()
