"""Editing the result's filters on Make an EQ (ui\\filter_editor.py under ui\\eq_page.py): a typed value changes the
error, the title, the file name and the line on how it sounds at once; a value past the edit limits is red and not
used; Revert gives the run's filters back and Sort alone isn't an edit; the Sliders view edits the same filters.
Moved from eq_checks.py's ui_checks: one page for the file (the eq_screen fixture), a quick run of its own (the
result the old checks edited), then the edits one after another in the old order. Then the editor's look
(Windows 11's, 2026-10-23) on an editor of its own in a window, as Your own filters has it: as tall as the view
shown, its colours the theme's, light and dark (read from what's drawn), and its table's headings over their words
(Type's at the left); and Your own filters itself (Settings › Edit as a table…), its Sliders view whole as the window
opens and at its smallest."""
import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QSlider

from helpers import eqpage, qt


@pytest.fixture(scope="module")
def chain(eq_screen):
    """The Run button's result on the card (eq_checks.py lines 1528-1532), and what each edit leaves for the next."""
    page = eq_screen.page
    page.choose_app("apo")  # (your EQ app as the old checks had chosen it before their run, line 1491)
    eqpage.quick_run(eq_screen)  # (raises when the run makes no result)
    run, r = page.current()
    return {"run": run, "r": r}


def test_editing_a_filter(eq_screen, chain, check):
    page, run = eq_screen.page, chain["run"]
    # (lines 1537-1541: filter 1's gain box in the table typed 3 dB higher, as a person types it)
    before = (page.chips["error"].text(), page.name_edit.text())
    box = page.editor.table.cellWidget(0, 4)
    box.setText(str(page.EDIT[0]["gain"] + 3))
    box.textEdited.emit(box.text())
    after = (page.chips["error"].text(), page.res_title.text(), page.name_edit.text(), page.pick_lab.text())
    chain.update(before=before, box=box)
    # was eq_checks.py:1542
    check("ui: editing a filter: the error, the title (edited), the file name (… edited) and the line on how it sounds "
          "follow at once",
          after[0] != before[0] and after[1].endswith("edited") and after[2] == before[1] + " edited"
          and (after[3].startswith("As edited: sounds within") or not run.get("pick_case")), (before, after))


def test_value_past_the_edit_limits(eq_screen, chain, check):
    page, box = eq_screen.page, chain["box"]
    box.setText("99999")  # (lines 1546-1547: the same box)
    box.textEdited.emit(box.text())
    # was eq_checks.py:1548
    check("ui: editing: a value past the edit limits is red and not used", box.property("bad") is True
          and page.EDIT[0]["gain"] != 99999)


def test_revert_and_sort(eq_screen, chain, check):
    page, before = eq_screen.page, chain["before"]
    page.revert()  # (lines 1550-1551)
    page.sort_filters()
    # was eq_checks.py:1552
    check("ui: Revert gives the run's filters back; Sort alone isn't an edit",
          page.chips["error"].text() == before[0] and not page.edited() and page.name_edit.text() == before[1],
          page.chips["error"].text())


def test_sliders_edit_the_same_filters(eq_screen, chain, check):
    page, r = eq_screen.page, chain["r"]
    # (lines 1555-1559: a new filter, then the Sliders view, the last slider dragged to +2.5 dB)
    page.add_filter()
    n = len(page.active())
    page.set_view("sliders")
    sl = page.editor.sliders_scroll.widget().findChildren(QSlider)
    sl[-1].setValue(25)
    # was eq_checks.py:1560
    check("ui: the sliders edit the same filters (a new one at 1 kHz, its gain dragged to +2.5 dB)",
          n == len(r["filters"]) + 1 and page.EDIT[-1]["freq"] == 1000 and page.EDIT[-1]["gain"] == 2.5, page.EDIT[-1])
    page.set_view("table")  # (lines 1562-1563: the Table view again, the run's own filters)
    page.revert()


# ---------------------------------------------------------------- the look (the restyle's stage 2, 2026-10-23)
FILTERS = [{"enabled": True, "type": "LSQ", "freq": 105, "gain": 3.5, "q": 0.7},
           {"enabled": False, "type": "PK", "freq": 1000, "gain": -2.0, "q": 1.4},  # (switched off)
           {"enabled": True, "type": "HSQ", "freq": 8000, "gain": -1.5, "q": 0.7}]


def _near(a, b, by=8):
    """Two colours the same but for a little rounding (each of red, green and blue within `by`)."""
    a, b = QColor(a), QColor(b)
    return max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue())) <= by


@pytest.fixture
def own_editor(eq_screen):
    """A filter editor of its own (three filters, the second switched off) in a window taller than it, as Your own
    filters has it; closed after."""
    from PySide6.QtWidgets import QDialog, QVBoxLayout
    from ui.filter_editor import FilterEditor
    dlg = QDialog(eq_screen.page)
    dlg.resize(820, 600)
    v = QVBoxLayout(dlg)
    ed = FilterEditor(eq_screen.page.meta.get("limits", {}))
    ed.set_filters([dict(f) for f in FILTERS])
    v.addWidget(ed, 1)
    dlg.show()
    qt.pump(150)
    yield ed
    qt.close(dlg)


def test_editor_as_tall_as_its_view(own_editor, check):
    ed = own_editor
    table = (ed.sizeHint().height(), ed.table.height(), ed.stack.y())
    ed.set_view("sliders")
    qt.pump(100)
    sliders = (ed.sizeHint().height(), ed.stack.y(), ed.sliders_scroll.height())
    ed.set_view("table")
    check("filters: the editor is as tall as the view shown, at the top of a taller window (a short table had an "
          "empty band under it, as tall as the Sliders view)",
          table[0] == table[1] < sliders[2] and table[2] == 0 and sliders[:2] == (sliders[2], 0), (table, sliders))


def test_editor_colours_are_the_themes(own_editor, eq_screen, check):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QFrame
    from ui import theme
    ed, qapp = own_editor, eq_screen.qapp

    def drawn():
        """(the pre-amp's bar, the card under a ✕, the longest run of the thumb's grey dot down a switched-off
        slider's middle) as drawn now, with the theme's colours for them."""
        t = theme.tokens()
        ed.set_view("table")
        qt.pump(100)
        x = ed.table.cellWidget(0, 6)
        img = qt.picture(ed.table.viewport())
        p = x.mapTo(ed.table.viewport(), QPoint(3, x.height() // 2))
        under_x = img.pixelColor(p).name()
        ed.set_view("sliders")
        qt.pump(100)
        holder = ed.sliders_scroll.widget()
        bar = next(f for f in holder.findChildren(QFrame) if type(f) is QFrame)  # (the pre-amp's: no words in it)
        bar_colour = qt.picture(bar).pixelColor(bar.width() // 2, bar.height() // 2).name()
        off = holder.findChildren(QSlider)[1]
        pic = qt.picture(off)
        run = best = 0
        for y in range(pic.height()):
            run = run + 1 if _near(pic.pixelColor(pic.width() // 2, y), t["disabled"]) else 0
            best = max(best, run)
        return {"bar": (bar_colour, t["track"]), "under ✕": (under_x, t["card"]), "dot": best,
                "set in code": bar.styleSheet() + x.styleSheet() + off.styleSheet()}
    try:
        light = drawn()
        theme.apply(qapp, dark=True)
        qt.pump(200)
        dark = drawn()
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qt.pump(100)
    ok = all(_near(*d["bar"]) and _near(*d["under ✕"]) and d["dot"] >= 4 and not d["set in code"] for d in (light, dark))
    check("filters: the pre-amp's bar (a slider's empty track), ✕ (a subtle button: the card shows through it) and a "
          "switched-off filter's thumb (its ring with a grey dot, not a flat square) in the theme's colours, light and "
          "dark, none set in the code", ok and light["bar"][1] != dark["bar"][1], {"light": light, "dark": dark})


def _ink_span(img, rect):
    """(first, last): the columns of rect in a picture with words in them (far from the colour at its left), from
    rect's left, read along its middle band (clear of a box's borders); None without words."""
    back = img.pixelColor(rect.left() + 1, rect.center().y())
    far = lambda c: max(abs(c.red() - back.red()), abs(c.green() - back.green()), abs(c.blue() - back.blue())) > 80
    cols = [x for x in range(rect.left(), rect.right() + 1)
            if any(far(img.pixelColor(x, y)) for y in range(rect.center().y() - 5, rect.center().y() + 6))]
    return (cols[0] - rect.left(), cols[-1] - rect.left()) if cols else None


def test_editor_headings_over_their_words(own_editor, check):
    # (2026-10-23, the restyle's recheck: the table's headings were all centred, so “Type” sat in the middle of its
    # column while its drop-downs' words start at their left; the result card and Your own filters both show it)
    from PySide6.QtCore import QPoint, QRect
    t = own_editor.table
    h = t.horizontalHeader()
    head, cells = qt.picture(h), qt.picture(t.viewport())
    spans = {}
    for c, name in ((0, "On"), (2, "Type"), (3, "Frequency (Hz)"), (4, "Gain (dB)"), (5, "Q")):
        x = h.sectionViewportPosition(c)
        w = t.cellWidget(0, c)
        at = w.mapTo(t.viewport(), QPoint(0, 0))
        words = _ink_span(cells, QRect(at, w.size()))
        spans[name] = (_ink_span(head, QRect(x, 0, h.sectionSize(c), h.height())),
                       words and (words[0] + at.x() - x, words[1] + at.x() - x))  # (both from the column's left)
    whole = all(a is not None and b is not None for a, b in spans.values())
    middle = lambda s: (s[0] + s[1]) / 2
    check("filters: the table's Type heading starts at the left, over its drop-downs' words (it sat in the middle of "
          "its column); the other headings stay centred over their values and ticks (the result card's and Your own "
          "filters' table)",
          whole and abs(spans["Type"][0][0] - spans["Type"][1][0]) <= 2
          and all(abs(middle(spans[k][0]) - middle(spans[k][1])) <= 3
                  for k in ("On", "Frequency (Hz)", "Gain (dB)", "Q")), spans)


def test_own_filters_sliders_whole(eq_screen, check, monkeypatch):
    # (found by the restyle's checkers, 2026-10-23: Your own filters with ten filters opened at its smallest height,
    # 820 x 573, and its Sliders view, 440 px tall, got 421: Qt works out a window's smallest height with the note's
    # wrapped second line counted as none, so the editor lost that line. Its bottom, the sideways scroll bar, was
    # under OK and Cancel, and the filters past the fifth couldn't be reached)
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QDialog, QPushButton
    from ui.filter_editor import FilterEditor
    from ui.window_parts import Footer
    page = eq_screen.page
    ten = "\n".join(f"Filter {i}: ON PK Fc {100 * i} Hz Gain 1 dB Q 1" for i in range(1, 11))
    seen = {}

    def where(dlg):
        """The sliders' scroll bar (its top, its bottom, shown, how far it scrolls), the editor's bottom and the
        buttons' top, in the window, as it is now."""
        ed = dlg.findChild(FilterEditor)
        bar = ed.sliders_scroll.horizontalScrollBar()
        top = bar.mapTo(dlg, QPoint(0, 0)).y()
        return {"window": (dlg.width(), dlg.height()), "bar": (top, top + bar.height(), bar.isVisible(), bar.maximum()),
                "editor ends": ed.mapTo(dlg, QPoint(0, ed.height())).y(),
                "buttons start": dlg.findChild(Footer).geometry().y()}

    def shown(dlg):  # (the window's exec: shown as it opens, its Sliders view chosen, then made as small as it goes)
        dlg.show()
        qt.pump(200)
        next(b for b in dlg.findChildren(QPushButton) if b.text() == "Sliders").click()
        qt.pump(200)
        seen["as it opens"] = where(dlg)
        dlg.resize(dlg.minimumSize())
        qt.pump(200)
        seen["at its smallest"] = where(dlg)
        dlg.hide()
        return QDialog.Rejected  # (Cancel: your own filters stay as they were)
    kept = page.S["best_fit"]["start_filters"]
    monkeypatch.setattr(QDialog, "exec", shown)
    try:
        page.S["best_fit"]["start_filters"] = ten
        page.settings.edit_own_filters()
    finally:
        page.S["best_fit"]["start_filters"] = kept
    whole = lambda s: s["bar"][2] and s["bar"][3] > 0 and s["bar"][1] <= s["editor ends"] <= s["buttons start"]
    check("filters: Your own filters' Sliders view is whole, its sideways scroll bar in sight above OK and Cancel, as "
          "the window opens and at its smallest (the window's smallest height counted the note's second line as none: "
          "the bar was under the buttons, the filters past the fifth out of reach)",
          len(seen) == 2 and all(whole(s) for s in seen.values()), seen)


def test_own_filters_window_ends_as_every_window(eq_screen, check, monkeypatch):
    # (2026-10-27, the rules' review: Enter in one of its boxes pressed OK and closed the window, and what the editor
    # changed ("Changed to …") was said in the main window's line, behind it)
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication, QDialog, QLineEdit, QPushButton
    from ui.filter_editor import FilterEditor
    from ui.window_parts import Footer
    page = eq_screen.page
    seen = {}

    def shown(dlg):
        dlg.show()
        qt.pump(200)
        box = next(b for b in dlg.findChild(FilterEditor).findChildren(QLineEdit) if b.isVisible())  # (a cell)
        box.setFocus()
        qt.pump(50)
        QApplication.sendEvent(box, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
        qt.pump(50)
        seen["open after Enter in a box"] = dlg.isVisible()
        dlg.findChild(FilterEditor).say("Changed to 20000 Hz.")
        footer = dlg.findChild(Footer)
        seen["said"] = (footer.line.text.text() if footer else None, page.window_status_said[-1:]
                        if hasattr(page, "window_status_said") else [])
        seen["buttons"] = [b.text() for b in footer.findChildren(QPushButton) if b.isVisible()] if footer else None
        dlg.hide()
        return QDialog.Rejected
    kept = page.S["best_fit"]["start_filters"]
    monkeypatch.setattr(QDialog, "exec", shown)
    try:
        page.S["best_fit"]["start_filters"] = "Filter 1: ON PK Fc 1000 Hz Gain 2 dB Q 1"
        page.settings.edit_own_filters()
    finally:
        page.S["best_fit"]["start_filters"] = kept
    check("filters: Your own filters ends as every window: Enter in one of its boxes stays the box's (the window stays "
          "open), what the editor changed is said in its own line, then OK and Cancel",
          seen.get("open after Enter in a box") is True and (seen.get("said") or (None,))[0] == "Changed to 20000 Hz."
          and seen.get("buttons") == ["OK", "Cancel"], seen)
