"""Compare… on Make an EQ (ui\\compare_results.py): the result shown now and another side by side (the error as the
result card works it out, every number, both filter tables), and Show B putting B on the result card. Moved from
eq_checks.py's compare_results_checks: one page for the file (the eq_screen fixture) with a History EQ on the card, as
the old check had, and a made-up run of this session to compare it with (the result's first 4 filters). Then the
graph's colours (Windows 11's look, 2026-10-23: the graph's own, never the accent), light and dark, the window at
its smallest, and its numbers and filter tables in Windows 11's table look (no grid lines, each heading over its
words at the left, rows told apart by their shade)."""
import pytest

from helpers import eqpage, qt
from ui.compare_results import CompareResults, options


@pytest.fixture(scope="module")
def history_eq(eq_screen):
    """A History EQ of at least 4 filters on the result card (eq_checks.py lines 1528-1532, 1573-1574 and 1583: a
    quick run, saved as "UI check", brought back with History's Show). B is its first 4 filters, so the check needs
    4 or more: the old run's pick happened to have 5 of the 3 and 5 it tried; here Best fit tries 5 filters only, so
    its result has 5."""
    page = eq_screen.page
    page.choose_app("apo")  # (your EQ app as the old checks had chosen it before their run, line 1491)
    eqpage.quick_run(eq_screen, counts=(5,))  # (raises when the run makes no result)
    entry = eqpage.save_result(eq_screen, "UI check")
    eqpage.show_from_history(eq_screen, entry)
    _run, r = page.current()
    if r is None or len(r["filters"]) < 4:
        raise RuntimeError(f"Compare's check needs a result of 4 filters or more on the card: {r and len(r['filters'])}")
    return entry


def test_compare_two_results(eq_screen, history_eq, check):
    page = eq_screen.page
    run, r = page.current()
    first = page.sel
    # (lines 2481-2499: another run of this session to compare with, the result with its first four filters; Compare
    # opened, B chosen, Show B; then that run taken away and the first result shown again)
    extra = dict(run, n=99, pick="cmp-4", best="cmp-4", device=page.curves["name"],
                 results=[dict(r, id="cmp-4", n_filters=4, rms=r["rms"] + 0.3, filters=r["filters"][:4])])
    page.session_runs.append(extra)
    opts = options(page)
    dlg = CompareResults(page)
    if len(opts) > 1:  # (B: the other run's result; the lists are A to Z, so by its name)
        dlg.combos[1].setCurrentIndex(dlg.combos[1].findText(opts[1]["label"]))
    a_rms = dlg.numbers.item(0, 1).text() if dlg.numbers.rowCount() else ""
    card = page.stats()["rms"]
    names = [dlg.numbers.item(i, 0).text() for i in range(dlg.numbers.rowCount())]
    rows = (dlg.tables[0].rowCount(), dlg.tables[1].rowCount())
    other = opts[1] if len(opts) > 1 else None
    if other and other["rid"] is not None:
        dlg.show_on_card(1)
    moved = page.sel
    dlg.close()
    page.session_runs.remove(extra)
    page.run_result = run
    page.show_result(first)
    # was eq_checks.py:2500
    check("compare: the result shown now and another side by side (the error as the result card's, every number, "
          "both filter tables); Show B puts it on the result card", len(opts) >= 2 and opts[0]["label"].startswith("Shown now")
          and a_rms == f"{card:.2f}" and len(names) == 6 and rows[0] == len(page.active()) and rows[1] == 4
          and (other is None or other["rid"] is None or moved == other["rid"]) and page.cmp_btn.isVisibleTo(page),
          (len(opts), a_rms, card, names, rows, moved))


def test_compare_colours_follow_the_theme(eq_screen, history_eq, check):
    from helpers import palette
    from ui import theme, theme_tokens
    page, qapp = eq_screen.page, eq_screen.qapp
    dlg = CompareResults(page)  # (A: the result shown now, B: the History EQ)
    dlg.show()
    qt.pump(200)

    def drawn():
        """A's and B's pens and the axes' as drawn now, with the graph's colours and the accent."""
        pens = {it.name(): it.opts["pen"].color().name() for it in dlg.plot.listDataItems()}
        col = theme.graph_colours()
        return {"A": (pens.get("A: with the EQ"), col["with_eq"]), "B": (pens.get("B: with the EQ"), col["eq"]),
                "axis": (dlg.plot.getAxis("left").pen().color().name(), col["axis"]),
                "accent": theme.tokens()["accent"]}
    try:
        light = drawn()
        theme.apply(qapp, dark=True)
        qt.pump(200)
        dark = drawn()
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qt.pump(100)
        qt.close(dlg)
    told = {mode: palette.check([g["meas"], g["with_eq"], g["c2"]], mode, base["card"], "all")[0]
            for mode, base, g in (("light", theme_tokens.BASE_LIGHT, theme_tokens.GRAPH_LIGHT),
                                  ("dark", theme_tokens.BASE_DARK, theme_tokens.GRAPH_DARK))}
    ok = (all(d[k][0] == d[k][1] for d in (light, dark) for k in ("A", "B", "axis"))
          and all(d["A"][0] != d["accent"] for d in (light, dark)) and light["A"][0] != dark["A"][0])
    check("compare: A in the graph's blue (with the EQ) and B in its pink, never the accent, both told apart from the "
          "orange measurement by colour-blind eyes too (the dataviz checks); the graph's axes as Make an EQ's; redrawn "
          "when the theme changes", ok and all(told.values()), {"light": light, "dark": dark, "told apart": told})


def test_compare_names_whole_at_its_smallest(eq_screen, history_eq, check):
    page = eq_screen.page
    dlg = CompareResults(page)
    dlg.show()
    dlg.resize(dlg.minimumSize())  # (the smallest the window can be made)
    qt.pump(200)
    t = dlg.numbers
    fm = t.fontMetrics()
    names = [t.item(i, 0).text() for i in range(t.rowCount()) if t.item(i, 0)]
    need = max(fm.horizontalAdvance(n) for n in names)
    got = (dlg.width(), t.columnWidth(0), need)
    qt.close(dlg)
    check("compare: at its smallest the numbers' names are whole (“How far apart, at most (scored range)” was cut)",
          names and got[1] >= got[2] + 10, got)


def test_compare_tables_in_windows_11s_table_look(eq_screen, history_eq, check):
    # (2026-10-23, the restyle's checkers: Compare's numbers and both filter tables kept full grid lines and centred
    # headings, while Profiles, Run several and the filter editor have Windows 11's table look)
    page = eq_screen.page
    dlg = CompareResults(page)  # (A: the result shown now, B: the History EQ)
    try:
        dlg.show()
        qt.pump(200)
        found = {name: {"grid lines": t.showGrid(), "rows shaded": t.alternatingRowColors(),
                        "headings over their words": qt.headings_over_words(t, cols)}
                 for name, t, cols in (("numbers", dlg.numbers, (1, 2)), ("A's filters", dlg.tables[0], range(4)),
                                       ("B's filters", dlg.tables[1], range(4)))}
    finally:
        qt.close(dlg)
    over = lambda pairs: all(h is not None and c is not None and abs(h - c) <= 3 for h, c in pairs)
    check("compare: its numbers and both filter tables in Windows 11's table look, as Profiles and Run several: no "
          "grid lines, each heading at the left over its words, rows told apart by their shade",
          all(not f["grid lines"] and f["rows shaded"] and over(f["headings over their words"]) for f in found.values()),
          found)
