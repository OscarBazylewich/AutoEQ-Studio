"""The Tab sequence of Make an EQ's page (ui\\eq_page_parts.py's tab_order; found by the verifier of the focus work,
2026-11-16: Tab on Queue… gave the focus to the Target row's Adjust…, and the page went to its top, 597 px to 0, as a
click on Calculate had). Qt puts a new control at the end of its window's Tab sequence, wherever it is on the page.
The page makes Adjust…, Settings and More settings after the cards under them, and it makes the filters' rows, the
versions' buttons and the rows of the EQs to compare again with each change: each came after the controls under it.
In two more places the keys stopped: Qt's own Tab in the filters' table went from cell to cell and never left the
table, and Tab in Start from your filters wrote a tab character.
What's checked, in each state of the page that a person can get: real Tab keys go down the page (never back up, nor
back to the left in a row), stop at every control that shows, leave the page after its last control, and Shift+Tab
goes the opposite way.
Only real keys measure the sequence. A Python call of nextInFocusChain makes PySide6 6.11.2 keep the control that it
returns as a child of the control asked: when Qt deletes one control, PySide6 then marks the later ones of the walk
as deleted, the page's scroll bar among them (measured, 2026-11-16).
One page for the file (the eq_screen fixture)."""
import pytest
import shiboken6
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QPushButton, QWidget

from helpers import eqpage, qt

COVERS = ("ui.eq_page_parts", "ui.eq_page_cards", "ui.eq_settings", "ui.filter_editor", "ui.listen")


def _key(w):
    return shiboken6.getCppPointer(w)[0]


def _name(w):
    """A control as a check's detail names it: its class and its words."""
    if w is None:
        return None
    words = w.text() if callable(getattr(w, "text", None)) and not isinstance(w, QLineEdit) else ""
    return f"{type(w).__name__} {(words or w.accessibleName())[:40]!r}"


def _open(eq_screen):
    """The page with Automatically shown, its window active (a key goes to an active window only)."""
    page = eq_screen.page
    page.choose_app("apo")
    page.set_way("auto", remember=False)
    page.activateWindow()
    qt.pump(150)
    return page


def _keys(page, first, key=Qt.Key_Tab):
    """The controls that real Tab keys (Qt.Key_Backtab: Shift+Tab) give the focus to, from `first`, while the focus
    is on the page; and how that ended: "left the page" (after the page's last control), or the control that the
    focus came to again (a control that keeps the key)."""
    inner = page.page_area.widget()
    first.setFocus(Qt.TabFocusReason)
    seq, seen = [], set()
    for _ in range(600):
        w = QApplication.focusWidget()
        if w is None or not inner.isAncestorOf(w):
            return seq, "left the page"
        if _key(w) in seen:
            return seq, f"the focus came to {_name(w)} again"
        seen.add(_key(w))
        seq.append(w)
        QTest.keyClick(w, key)
    return seq, "600 keys and no end"


def _box(w, top):
    return QRect(w.mapTo(top, QPoint(0, 0)), w.size())


def _goes_back(page, a, b):
    """Why the step from control a to control b goes back on the page (None: it goes on). The two parts of their
    nearest common parent that hold them are compared: b's part is above a's part, or left of it in the same row. In
    the Sliders view each filter is a column: there, b's part is left of a's part, or above it in the same column."""
    inner = page.page_area.widget()
    up_a, up_b = [a], [b]
    for up in (up_a, up_b):
        while _key(up[-1]) != _key(inner):
            up.append(up[-1].parentWidget())
    keys_a = [_key(w) for w in up_a]
    at_b = next(i for i, w in enumerate(up_b) if _key(w) in keys_a)
    at_a = keys_a.index(_key(up_b[at_b]))
    if not at_a or not at_b:
        return None  # (one is in the other)
    common = up_b[at_b]
    ra, rb = _box(up_a[at_a - 1], common), _box(up_b[at_b - 1], common)
    sliders = page.editor.sliders_scroll.widget()
    columns = sliders is not None and _key(common) == _key(sliders)
    if columns:
        ra, rb = (QRect(r.y(), r.x(), r.height(), r.width()) for r in (ra, rb))
    if rb.bottom() < ra.top():
        return "to the left" if columns else "up"
    if rb.top() <= ra.bottom() and rb.right() < ra.left():
        return "up in its column" if columns else "to the left in its row"
    return None


def _stops(page):
    """The page's controls that Tab stops at now: each shows, is on, and takes the focus of the Tab key."""
    win = page.window()
    return [w for w in page.page_area.widget().findChildren(QWidget)
            if w.focusPolicy() & Qt.TabFocus and w.isVisibleTo(win) and w.isEnabled() and w.focusProxy() is None
            and w.window() is win]


def _wrong(page):
    """What is wrong with the page's Tab sequence as the page is now ({}: nothing), measured with real keys from the
    page's first control (Target); and the sequence."""
    qt.pump(150)  # (the page laid out after the change before)
    seq, end = _keys(page, page.target_combo)
    out = {}
    if end != "left the page":
        out["Tab"] = end
    back = [f"{_name(a)} -> {_name(b)}: {why}" for a, b in zip(seq, seq[1:])
            for why in [_goes_back(page, a, b)] if why]
    if back:
        out["goes back"] = back[:3]
    reached = {_key(w) for w in seq}
    missed = [_name(w) for w in _stops(page) if _key(w) not in reached]
    if missed:
        out["not reached"] = [len(missed), *missed[:3]]
    rev, _end = _keys(page, seq[-1], Qt.Key_Backtab) if seq else ([], "")
    if [_key(w) for w in rev] != [_key(w) for w in reversed(seq)]:
        out["Shift+Tab"] = next(([_name(x), _name(y)] for x, y in zip(rev, reversed(seq)) if _key(x) != _key(y)),
                                [len(rev), len(seq)])
    if len(seq) < 30:  # (the page has more controls than this in each state)
        out["controls"] = len(seq)
    return out, seq


def _tab(page, start, key=Qt.Key_Tab):
    """One real Tab key on `start`, in sight and with the focus as Tab gives it: the control that got the focus, and
    the page's place before and after (its scroll bar's value)."""
    bar = page.page_area.verticalScrollBar()
    start.setFocus(Qt.TabFocusReason)
    page.page_area.ensureWidgetVisible(start, 0, 200)
    qt.pump(60)
    at = bar.value()
    QTest.keyClick(start, key)
    qt.pump(60)
    return QApplication.focusWidget(), at, bar.value()


def _under(page, a, b):
    """Whether control b is on the page and under control a."""
    inner = page.page_area.widget()
    return b is not None and inner.isAncestorOf(b) and _box(b, inner).top() > _box(a, inner).bottom()


def _named(page, name):
    """The filter editor's control of that name ("Filter 2 on", "Remove filter 2")."""
    return next((w for w in page.editor.findChildren(QWidget) if w.accessibleName() == name and w.isVisible()), None)


def test_tab_at_the_parts_made_after_the_cards_under_them(eq_screen, check):
    page = _open(eq_screen)
    got, at, after = _tab(page, page.queue_btn)
    back = _tab(page, page.queue_btn, Qt.Key_Backtab)[0]
    check("eq page: Tab on Queue… gives the focus to the next control down the page, and the page does not go up (the "
          "focus went to the Target row's Adjust…, and the page to its top); Shift+Tab on Queue… goes to Calculate",
          _under(page, page.queue_btn, got) and at > 0 and after >= at and back is page.run_btn,
          (_name(got), at, after, _name(back)))
    adjust = page.settings.adjust_btn
    add = next(b for b in page.target_box.findChildren(QPushButton) if b.text() == "Add…")
    got = [_tab(page, add)[0], _tab(page, adjust)[0], _tab(page, adjust, Qt.Key_Backtab)[0],
           _tab(page, page.measurement_combo, Qt.Key_Backtab)[0]]
    check("eq page: Tab on the Target row's Add… goes to its Adjust…, and Tab on Adjust… to Measurement; Shift+Tab "
          "goes the opposite way (Adjust… came after Queue…)",
          got == [adjust, page.measurement_combo, add, adjust], [_name(w) for w in got])
    fold, more = page.settings.fold.btn, page.settings.adv.btn
    got = [_tab(page, page.mode_combo)[0], _tab(page, fold)[0], _tab(page, more)[0],
           _tab(page, page.run_btn, Qt.Key_Backtab)[0], _tab(page, fold, Qt.Key_Backtab)[0]]
    check("eq page: Tab on Method goes to Settings, then to More settings, then to Calculate; Shift+Tab on Calculate "
          "goes to More settings, and on Settings to Method (Tab on Method went to Calculate: Settings and More "
          "settings came after Queue…)",
          got == [fold, more, page.run_btn, more, page.mode_combo], [_name(w) for w in got])


def test_tab_sequence_with_no_result(eq_screen, check):
    page = _open(eq_screen)
    fold, more, form = page.settings.fold.btn, page.settings.adv.btn, page.settings.adv_form
    was = (fold.isChecked(), more.isChecked(), form.pages.currentIndex())
    block = form.fields["best_fit.start_filters"].box
    text = block.toPlainText()
    wrong = {}

    def measure(state):
        bad, seq = _wrong(page)
        if bad:
            wrong[state] = bad
        return seq
    try:
        fold.setChecked(False)
        more.setChecked(False)
        measure("Automatically")
        fold.setChecked(True)
        measure("Settings open")
        more.setChecked(True)
        tabs = {b.text(): i for i, b in form.tab_btns.items() if not b.isHidden()}
        for words, i in tabs.items():
            form.show_tab(i)
            measure(f"Settings and More settings open, its tab {words}")
        fold.setChecked(False)
        form.show_tab(tabs["Best fit"])
        seq = measure("More settings open")
        # (the tabs' buttons before the settings of the tab shown: each came after its own tab's settings)
        names = [_name(w) for w in seq]
        tab_row = names[names.index(_name(more)) + 1:][:len(tabs)]
        after_block = _tab(page, block)[0]
        typed = block.toPlainText()
        more.setChecked(False)
        page.set_way("hand", remember=False)
        measure("Manually")
    finally:
        if block.toPlainText() != text:  # (the setting as it was)
            block.setPlainText(text)
        page.set_way("auto", remember=False)
        fold.setChecked(was[0])
        more.setChecked(was[1])
        form.show_tab(was[2])
    check("eq page: with no result, the Tab sequence goes down the page (never back up, nor back to the left in a "
          "row), stops at every control that shows, and Shift+Tab goes the opposite way: Automatically, Settings "
          "open, More settings open on each of its tabs, and Manually", not wrong and len(tabs) >= 5, (wrong, tabs))
    check("eq page: in More settings, Tab goes from More settings through the tabs' buttons, then to the settings of "
          "the tab shown (each button came after its own tab's settings)",
          tab_row == [f"QPushButton {words!r}" for words in tabs], (tab_row, list(tabs)))
    check("eq page: Tab in Start from your filters (More settings) goes to the next control and does not change the "
          "text (it wrote a tab character into the setting, and the focus stayed in the box)",
          typed == text and after_block is not block and _under(page, block, after_block),
          (repr(text), repr(typed), _name(after_block)))


def test_tab_sequence_with_pasted_filters(eq_screen, check):
    # (2026-11-25: Manually's Name and Filters boxes, in the card with Pasted filters, and Add filter beside Start)
    page = _open(eq_screen)
    c = page.hand_source
    was = c.currentIndex()
    wrong = {}
    try:
        page.set_way("hand", remember=False)
        c.setCurrentIndex(c.findData("paste"))
        bad, seq = _wrong(page)
        if bad:
            wrong["Pasted filters"] = bad
        keys = [_key(w) for w in seq]
        order = [keys.index(_key(w)) if _key(w) in keys else -1 for w in (c, page.hand_paste_name, page.hand_paste)]
        page.hand_paste.setPlainText("Filter 1: ON PK Fc 100 Hz Gain 3 dB Q 1")
        after = _tab(page, page.hand_paste)[0]
        typed, under = page.hand_paste.toPlainText(), _under(page, page.hand_paste, after)
        c.setCurrentIndex(c.findData("empty"))
        bad, seq = _wrong(page)
        if bad:
            wrong["An empty EQ"] = bad
        keys = [_key(w) for w in seq]
        add_after_start = _key(page.hand_add) in keys and keys.index(_key(page.hand_add)) ==             keys.index(_key(page.hand_start)) + 1
    finally:
        page.hand_paste.clear()
        c.setCurrentIndex(was)
        page.set_way("auto", remember=False)
    check("eq page: on Manually with Pasted filters and with An empty EQ, the Tab sequence goes down the page, stops at "
          "every control that shows, and Shift+Tab goes the opposite way: Start from, Name, then Filters; Add filter "
          "right after Start", not wrong and -1 not in order and order == sorted(order) and add_after_start,
          (wrong, order, add_after_start))
    check("eq page: Tab in Manually's Filters box goes to the next control and does not change the text (no tab "
          "character)", typed == "Filter 1: ON PK Fc 100 Hz Gain 3 dB Q 1" and after is not page.hand_paste
          and under, (repr(typed), _name(after)))


@pytest.mark.timeout(900)  # (a Best fit run, allowed 180 s times the time factor)
def test_tab_sequence_while_a_run_goes_on(eq_screen, check):
    page = _open(eq_screen)
    page.S["auto"]["enabled"] = False
    page.S["best_fit"].update(filter_counts=[4, 6, 8, 10], random_starts=0, gain_max=[6], q_max=[2],
                              seed_with_site=False)
    page.page_area.ensureWidgetVisible(page.run_btn, 0, 200)
    page.run_btn.setFocus(Qt.TabFocusReason)
    QTest.keyClick(page.run_btn, Qt.Key_Space)
    # (the page kept as it is while a run goes on, however soon the job ends: its end is read only when this timer
    # starts again, as tests\eq_screen\test_run_keeps_the_page.py does)
    page._poll.stop()
    try:
        qt.pump(100)
        running = not page.run_btn.isEnabled() and QApplication.focusWidget() is page.cancel_btn
        got, at, after = _tab(page, page.cancel_btn)
        back = _tab(page, page.cancel_btn, Qt.Key_Backtab)[0]
        wrong, _seq = _wrong(page)
        still = not page.run_btn.isEnabled()
        page.cancel_btn.setFocus(Qt.OtherFocusReason)  # (as the run left it: the focus goes back to Calculate)
    finally:
        page._poll.start()
    done = eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180)
    qt.pump(150)
    check("eq page: while a run goes on, Tab on Cancel gives the focus to the next control down the page, and the page "
          "does not go up (the focus went to the Target row's Adjust…, and the page to its top); Shift+Tab on Cancel "
          "goes to More settings",
          running and still and done and _under(page, page.cancel_btn, got) and at > 0 and after >= at
          and back is page.settings.adv.btn, (running, still, done, _name(got), at, after, _name(back)))
    check("eq page: while a run goes on, the Tab sequence goes down the page, stops at every control that shows, and "
          "Shift+Tab goes the opposite way", running and still and not wrong, (running, still, wrong))


@pytest.fixture(scope="module")
def result(eq_screen):
    """A result on the result card (a quick Best fit run, 3 and 5 filters), its filters as a table."""
    page = _open(eq_screen)
    eqpage.quick_run(eq_screen)
    page.set_view("table", remember=False)
    return page


def _rows(n):
    """The names of the controls of n filters' rows in the table, as Tab goes through them."""
    return [f"Filter {i} {part}" if part != "x" else f"Remove filter {i}" for i in range(1, n + 1)
            for part in ("on", "type", "frequency (Hz)", "gain (dB)", "Q", "x")]


@pytest.mark.timeout(900)  # (the result made first, and Calculate from these filters: each run allowed 180 s)
def test_tab_sequence_with_a_result(eq_screen, result, check):
    page = result
    lis = page.listen
    pins = len(lis.pins)
    wrong = {}

    def measure(state):
        bad, seq = _wrong(page)
        if bad:
            wrong[state] = bad
        return seq
    try:
        seq = measure("the filters as a table")
        # (through the table with real keys: from the table itself to the control after its last row)
        names = [w.accessibleName() for w in seq]
        table = names.index("Filters")
        in_table = names[table + 1:table + 1 + 6 * len(page.EDIT)]
        after_table = seq[table + 1 + 6 * len(page.EDIT)] if len(seq) > table + 1 + 6 * len(page.EDIT) else None
        last_x = _tab(page, page.name_edit, Qt.Key_Backtab)[0].accessibleName()
        filters = len(page.EDIT)
        page.set_view("sliders", remember=False)
        measure("the filters as sliders")
        page.set_view("table", remember=False)
        for _ in range(20 - len(page.EDIT)):  # (more rows than the table shows: its rows scroll in it)
            page.add_filter()
        measure("20 filters in the table")
        # (Tab from the last row in the table's sight to the next row, the first one out of its sight)
        t = page.editor.table
        t.verticalScrollBar().setValue(0)
        qt.pump(30)
        view = t.viewport()
        out = next((i for i in range(2, 21)
                    if not view.rect().intersects(_box(_named(page, f"Filter {i} on"), view))), 0)
        f = _tab(page, _named(page, f"Remove filter {out - 1}"))[0] if out else None
        in_sight = (out, f is not None and f.accessibleName() == f"Filter {out} on",
                    f is not None and view.rect().contains(_box(f, view)))
        page.undo_all()
        run = page.run_result
        page.run(retry={"filters": page.enabled_filters(), "add": False})
        again = eq_screen.wait_for(lambda: page.run_btn.isEnabled() and page.run_result is not run, 180)
        measure("after Calculate from these filters")
        lis.add_selected()
        measure("an EQ to compare on Listen's card")
        # (a click on a version's button makes the buttons again; Graph of an EQ to compare makes its rows again)
        first = next(b for b in lis.ab_box.findChildren(QPushButton) if b.isVisible())
        page.page_area.ensureWidgetVisible(first, 0, 100)
        qt.pump(30)
        QTest.mouseClick(first, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
        measure("the versions' buttons made again")
        graph = next(b for b in lis.pins_box.findChildren(QCheckBox) if b.isVisible())
        page.page_area.ensureWidgetVisible(graph, 0, 100)
        qt.pump(30)
        QTest.mouseClick(graph, Qt.LeftButton, Qt.NoModifier, QPoint(8, 8))
        measure("the rows of the EQs to compare made again")
        lis.blind.setChecked(True)
        measure("Hide the names")
        lis.blind.setChecked(False)
    finally:
        if len(lis.pins) > pins:  # (taken out again: the card as it was)
            lis.pins = lis.pins[:pins]
            lis.save_pins()
    check("eq page: with a result, Tab goes through the filters' table row by row (On, Type, Frequency, Gain, Q and ✕ "
          "of each filter), then to File name; Shift+Tab on File name goes to the last filter's ✕ (Tab went from "
          "cell to cell and never left the table, and no On box got the focus)",
          filters >= 3 and in_table == _rows(filters) and after_table is page.name_edit
          and last_x == f"Remove filter {filters}", (filters, in_table[:8], _name(after_table), last_x))
    check("eq page: with a result, the Tab sequence goes down the page, stops at every control that shows, and "
          "Shift+Tab goes the opposite way: the filters as a table and as sliders, 20 filters in the table, after "
          "Calculate from these filters, an EQ to compare on Listen's card, the versions' buttons and the rows of "
          "the EQs to compare made again, and Hide the names", again and not wrong, (again, wrong))
    check("eq page: in a table with more filters than it shows, Tab to a filter out of the table's sight brings its "
          "On box into sight (the focus was on a box that did not show)",
          all(in_sight), in_sight)


@pytest.mark.timeout(900)  # (the result made first, when this test runs alone)
def test_tab_sequence_with_an_eq_by_hand(eq_screen, result, check):
    page = result
    wrong = {}

    def measure(state):
        bad, _seq = _wrong(page)
        if bad:
            wrong[state] = bad
    page.set_way("hand", remember=False)
    page.manual_from_shown()  # (Start from: a copy of the EQ on the result card)
    try:
        manual = page.current()[0].get("mode") == "manual"
        measure("its filters as a table")
        page.add_filter()
        measure("a filter added")
        page.set_view("sliders", remember=False)
        measure("its filters as sliders")
        page.set_view("table", remember=False)
        _named(page, "Remove filter 1").click()
        measure("a filter removed")
    finally:
        page.close_manual()
        page.set_way("auto", remember=False)
    check("eq page: with an EQ by hand, the Tab sequence goes down the page, stops at every control that shows, and "
          "Shift+Tab goes the opposite way: its filters as a table, a filter added, its filters as sliders, and a "
          "filter removed", manual and not wrong, (manual, wrong))
