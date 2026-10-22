"""All results on Make an EQ (ui\\all_results.py): every result of a run listed, the grid's cells by filter count and
max Q (the best per cell), a click shows one (and marks it), the table sorts by value. Moved from eq_checks.py's
rest_checks: one page for the file (the eq_screen fixture) with the EQ the old check had on the card (a quick run
saved as "UI check" and brought back with History's Show); the run of 18 results is made up from it, as there."""
import pytest
from PySide6.QtCore import Qt

from helpers import eqpage
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
