"""All results on Make an EQ (ui\\all_results.py): every result of a run listed, the grid's cells by filter count and
max Q (the best per cell), a click shows one (and marks it), the table sorts by value. Moved from eq_checks.py's
rest_checks: one page for the file (the eq_screen fixture) with the EQ the old check had on the card (a quick run
saved as "UI check" and brought back with History's Show); the run of 18 results is made up from it, as there.
Then its look (Windows 11's, 2026-10-23) on a made-up run of four: the shading in the theme's colour for "good",
light and dark (read from what's drawn), the grid's corner and words, and the window at its smallest; Windows 11's
table look for the grid and the table (no grid lines, each heading over its words at the left, the grid's rows
told apart by a line in the theme's colour); and the grid's rows saying their results' own filter count."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from helpers import eqpage, qt
from ui.all_results import AllResults


@pytest.fixture(scope="module")
def history_eq(eq_screen):
    """The History EQ on the result card (eq_checks.py lines 1528-1532, 1573-1574 and 1583: a quick run, saved as
    "UI check", brought back with History's Show)."""
    page = eq_screen.page
    page.choose_app("apo")  # (your EQ app as the old checks had chosen it before their run, line 1491)
    eqpage.quick_run(eq_screen)  # (raises when the run makes no result)
    entry = eqpage.save_result(eq_screen, "UI check")
    eqpage.show_from_history(eq_screen, entry)
    return entry


def test_all_results(eq_screen, history_eq, check):
    page = eq_screen.page
    # (lines 1979-1999: a run of 18 results made from the one shown, filter counts 4, 6, 8 by max Q 2, 4, 6, two
    # each; All results opened on it, a grid cell picked, the table sorted; closed and the real run put back)
    real = page.run_result
    page.show_result(real["pick"])
    base = next(r for r in real["results"] if r["id"] == real["pick"])
    rs = [dict(base, id=f"t{n}-{q}" + "b" * k, n_filters=n, rows=n, q_max=q, rms=base["rms"] + 0.01 * (8 - n) + 0.002 * q + k * 0.0001)
          for n in (4, 6, 8) for q in (2, 4, 6) for k in (0, 1)]
    fake = dict(real, mode="best_fit", results=rs, best="t8-2", pick="t8-2")
    page.run_result = fake
    page.show_result("t8-2")
    ar = AllResults(page)
    grid_cells = [ar.grid.item(i, j) for i in range(ar.grid.rowCount()) for j in range(ar.grid.columnCount())]
    ids = [c.data(Qt.UserRole) for c in grid_cells if c is not None and c.data(Qt.UserRole) is not None]
    ar.pick("t4-6")
    grid_cells = [ar.grid.item(i, j) for i in range(ar.grid.rowCount()) for j in range(ar.grid.columnCount())]
    bold = [c.data(Qt.UserRole) for c in grid_cells if c is not None and c.font().bold()]
    picked = page.sel
    ar.table.sortItems(1, Qt.DescendingOrder)
    counts = [ar.table.item(i, 1).value for i in range(ar.table.rowCount())]
    shape = (ar.grid.rowCount(), ar.grid.columnCount(), ar.table.rowCount(), ar.grid.isHidden())
    ar.close()
    page.run_result = real
    page.show_result(real["pick"])
    # was eq_checks.py:2000
    check("all results: every result listed, the grid's cells by filter count and max Q (the best per cell), a click "
          "shows one (and marks it), the table sorts by value", shape == (3, 3, 18, False) and len(ids) == 9
          and picked == "t4-6" and bold == ["t4-6"] and counts == sorted(counts, reverse=True) and counts[0] == 8,
          (shape, len(ids), picked, bold, counts[:3]))


# ---------------------------------------------------------------- the look (the restyle's stage 2, 2026-10-23)
def _near(a, b, by=8):
    """Two colours the same but for a little rounding (each of red, green and blue within `by`)."""
    a, b = QColor(a), QColor(b)
    return max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue())) <= by


@pytest.fixture
def four(eq_screen, history_eq):
    """All results open on a made-up run of four: 1 and 2 filters by max Q 2 and 4, the 2-filter ones sounding the
    same as the target (0.1 dB as the ear hears it), the 1-filter ones not (1 dB); closed after, the real run put
    back."""
    page = eq_screen.page
    real = page.run_result
    page.show_result(real["pick"])
    base = next(r for r in real["results"] if r["id"] == real["pick"])
    rs = [dict(base, id=f"s{n}-{q}", n_filters=n, rows=n, q_max=q, rms=base["rms"] + 0.1 * (3 - n) + 0.01 * q,
               ear=0.1 if n == 2 else 1.0) for n in (1, 2) for q in (2, 4)]
    page.run_result = dict(real, mode="best_fit", results=rs, best="s2-2", pick="s2-2", ear_db=0.25)
    page.show_result("s2-2")
    ar = AllResults(page)
    ar.show()
    qt.pump(200)
    yield ar
    qt.close(ar)
    page.run_result = real
    page.show_result(real["pick"])


def test_all_results_shading_follows_the_theme(four, eq_screen, check):
    from PySide6.QtWidgets import QAbstractButton
    from ui import theme
    ar, qapp = four, eq_screen.qapp

    def drawn():
        """Each cell's colour away from its words, and the grid's corner, as drawn now; the theme's colours."""
        g = ar.grid
        img = qt.picture(g.viewport())
        cells = {}
        for i in range(g.rowCount()):
            for j in range(g.columnCount()):
                r = g.visualItemRect(g.item(i, j))
                cells[g.item(i, j).data(Qt.UserRole)] = img.pixelColor(r.left() + 3, r.center().y()).name()
        corner = g.findChild(QAbstractButton)  # (the corner between the grid's headings)
        t = theme.tokens()
        return {"cells": cells, "corner": qt.picture(g).pixelColor(corner.geometry().center()).name(),
                "pill": t["pill"], "card": t["card"], "sel": t["sel"]}
    try:
        light = drawn()
        theme.apply(qapp, dark=True)
        qt.pump(200)
        dark = drawn()
        theme.apply(qapp, dark=False, contrast=theme.system_tokens())  # (a contrast theme's colours: Windows' own)
        qt.pump(200)
        contrast = drawn()
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qt.pump(100)

    def marked(d, key):
        return len(d["cells"]) == 4 and all(_near(c, d[key] if rid.startswith("s2") else d["card"])
                                            for rid, c in d["cells"].items())
    check("all results: a cell that sounds the same as the target is shaded in the theme's colour for “good” (the "
          "others not), light and dark: taken as it's drawn, so it follows the theme",
          marked(light, "pill") and marked(dark, "pill") and light["pill"] != dark["pill"], {"light": light, "dark": dark})
    check("all results: in Windows' contrast themes, which have no colour for “good”, such a cell is marked in "
          "Windows' highlight instead (it vanished)", contrast["pill"] == contrast["card"] != contrast["sel"]
          and marked(contrast, "sel"), contrast)
    check("all results: the grid's corner is drawn as its headings (the card's colour), not a grey block",
          _near(light["corner"], light["card"]) and _near(dark["corner"], dark["card"]),
          (light["corner"], light["card"], dark["corner"], dark["card"]))


def test_all_results_words_whole(four, check):
    from PySide6.QtGui import QFont, QFontMetrics
    ar = four
    g = ar.grid
    labels = [g.verticalHeaderItem(i).text() for i in range(g.rowCount())]
    bold = QFont(g.font())
    bold.setBold(True)
    widest = max(QFontMetrics(bold).horizontalAdvance(g.item(i, j).text())
                 for i in range(g.rowCount()) for j in range(g.columnCount()))
    ar.resize(ar.minimumSize())  # (the smallest the window can be made)
    qt.pump(200)
    note = ar.grid_note
    smallest = (ar.width(), ar.height(), note.heightForWidth(note.width()), note.height())
    check("all results: the grid's rows say “1 filter”, “2 filters”; its columns never narrower than their numbers "
          "(in bold, as the one shown); at its smallest the note under the grid is whole (it ran over the grid)",
          labels == ["1 filter", "2 filters"] and g.horizontalHeader().minimumSectionSize() >= widest
          and smallest[2] <= smallest[3], (labels, widest, g.horizontalHeader().minimumSectionSize(), smallest))


def test_all_results_wide_grid_in_a_narrow_window(eq_screen, history_eq, check):
    page = eq_screen.page
    real = page.run_result
    page.show_result(real["pick"])
    base = next(r for r in real["results"] if r["id"] == real["pick"])
    # (a made-up run of 1 and 2 filters by eight max Qs: wider than the window at its smallest)
    rs = [dict(base, id=f"w{n}-{q}", n_filters=n, rows=n, q_max=q, rms=base["rms"] + 0.1 * (3 - n) + 0.01 * q, ear=1.0)
          for n in (1, 2) for q in range(1, 9)]
    page.run_result = dict(real, mode="best_fit", results=rs, best="w2-8", pick="w2-8")
    page.show_result("w2-8")
    ar = AllResults(page)
    try:
        ar.show()
        ar.resize(ar.minimumSize())  # (the smallest the window can be made)
        qt.pump(300)
        g = ar.grid
        last = g.visualItemRect(g.item(g.rowCount() - 1, 0))
        state = {"scrolls sideways": g.horizontalScrollBar().maximum() > 0, "last row ends": last.bottom(),
                 "rows' room": g.viewport().height(), "scrolls down": g.verticalScrollBar().maximum()}
    finally:
        qt.close(ar)
        page.run_result = real
        page.show_result(real["pick"])
    check("all results: in a narrow window a wide grid scrolls sideways, its last row whole above the scroll bar (the "
          "bar covered it)", state["scrolls sideways"] and state["last row ends"] < state["rows' room"]
          and state["scrolls down"] == 0, state)


def test_all_results_in_windows_11s_table_look(four, eq_screen, check):
    # (2026-10-23, the restyle's checkers: All results kept full grid lines and centred headings, while Profiles, Run
    # several and the filter editor have Windows 11's table look)
    from ui import theme
    ar, qapp = four, eq_screen.qapp
    g, t = ar.grid, ar.table

    def lines():
        """The colour of the line under the grid's first cell, half-way across, and the theme's colour for lines."""
        r = g.visualItemRect(g.item(0, 0))
        return qt.picture(g.viewport()).pixelColor(r.center().x(), r.bottom()).name(), theme.tokens()["line"]
    found = {"grid lines": (g.showGrid(), t.showGrid()), "table rows shaded": t.alternatingRowColors(),
             "grid: headings over their words": qt.headings_over_words(g, range(g.columnCount())),
             "table: headings over their words": qt.headings_over_words(t, range(t.columnCount()))}
    try:
        found["line under a grid row, light"] = lines()
        theme.apply(qapp, dark=True)
        qt.pump(200)
        found["line under a grid row, dark"] = lines()
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qt.pump(100)
    over = lambda pairs: all(h is not None and c is not None and abs(h - c) <= 3 for h, c in pairs)
    check("all results: the grid and the table in Windows 11's table look, as Profiles and Run several: no grid lines, "
          "each heading at the left over its words, the grid's rows told apart by a line under each in the theme's "
          "colour for lines (light and dark), the table's by their shade",
          found["grid lines"] == (False, False) and found["table rows shaded"]
          and over(found["grid: headings over their words"]) and over(found["table: headings over their words"])
          and all(_near(*found[f"line under a grid row, {m}"]) for m in ("light", "dark"))
          and found["line under a grid row, light"][1] != found["line under a grid row, dark"][1], found)


def test_all_results_rows_say_their_results_count(eq_screen, history_eq, check):
    # (2026-10-23, the restyle's checkers: Best fit's results are grouped by the filters the run added, shelves and
    # your own aside, and the grid said that number: "9 filters" for results of 10 with their shelf, and a Retry's only
    # row "0 filters" though each of its results had 10, as their result card said)
    page = eq_screen.page
    real = page.run_result
    page.show_result(real["pick"])
    base = next(r for r in real["results"] if r["id"] == real["pick"])
    runs = {"a shelf with each": [dict(base, id=f"h{n}-{q}", rows=n, n_filters=n + 1, q_max=q,
                                       rms=base["rms"] + 0.1 * (3 - n) + 0.01 * q) for n in (1, 2) for q in (2, 4)],
            "a Retry": [dict(base, id=f"r{q}", rows=0, n_filters=10, q_max=q, rms=base["rms"] + 0.01 * q)
                        for q in (2, 4)],
            "a filter left out of one": [dict(base, id=f"m{q}", rows=9, n_filters=10 if q == 2 else 9, q_max=q,
                                              rms=base["rms"] + 0.01 * q) for q in (2, 4)]}
    words = {}
    try:
        for name, rs in runs.items():
            page.run_result = dict(real, mode="best_fit", results=rs, best=rs[0]["id"], pick=rs[0]["id"])
            page.show_result(rs[0]["id"])
            ar = AllResults(page)
            try:
                words[name] = [ar.grid.verticalHeaderItem(i).text() for i in range(ar.grid.rowCount())]
            finally:
                qt.close(ar)
    finally:
        page.run_result = real
        page.show_result(real["pick"])
    check("all results: the grid's rows say how many filters their results have, as the result card does (grouped "
          "by the filters the run added, shelves and yours aside, they said “9 filters” for results of 10 and a "
          "Retry's row “0 filters”); which results share a row is as before",
          words == {"a shelf with each": ["2 filters", "3 filters"], "a Retry": ["10 filters"],
                    "a filter left out of one": ["9–10 filters"]}, words)


def test_all_results_opens_wide_enough(eq_screen, history_eq, check, monkeypatch):
    # (2026-10-23: with Windows 11's room at the left of the cells and rows named by their results' count, e.g.
    # “6–10 filters”, a run's grid of nine filter counts by six Q limits was wider than the window as it opened)
    from ui import all_results
    page = eq_screen.page
    real = page.run_result
    page.show_result(real["pick"])
    base = next(r for r in real["results"] if r["id"] == real["pick"])
    rs = [dict(base, id=f"g{n}-{q}", rows=n, n_filters=n + 1 if q > 1 or n < 6 else 6, q_max=q, max_boost=10.0,
               rms=base["rms"] + 0.1 * (10 - n) + 0.01 * q) for n in range(1, 10) for q in (1, 1.5, 2, 3, 4, 5)]
    monkeypatch.setattr(all_results, "screen_room", lambda widget: 1920)  # (a screen with room: the PC's size)
    page.run_result = dict(real, mode="best_fit", results=rs, best="g9-5", pick="g9-5")
    page.show_result("g9-5")
    ar = AllResults(page)
    try:
        ar.show()
        qt.pump(300)
        g = ar.grid
        found = {"window": (ar.width(), ar.height()), "rows": [g.verticalHeaderItem(i).text() for i in (0, 8)],
                 "scrolls sideways": g.horizontalScrollBar().maximum()}
    finally:
        qt.close(ar)
        page.run_result = real
        page.show_result(real["pick"])
    check("all results: opened, its whole grid is in sight when the screen has room (nine filter counts by six Q "
          "limits scrolled sideways)", found["scrolls sideways"] == 0 and found["rows"] == ["2 filters", "6–10 filters"],
          found)
