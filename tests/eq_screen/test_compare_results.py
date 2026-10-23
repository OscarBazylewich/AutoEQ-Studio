"""Compare… on Make an EQ (ui\\compare_results.py): the result shown now and another side by side (the error as the
result card works it out, every number, both filter tables), and Show B putting B on the result card. Moved from
eq_checks.py's compare_results_checks: one page for the file (the eq_screen fixture) with a History EQ on the card, as
the old check had, and a made-up run of this session to compare it with (the result's first 4 filters)."""
import pytest

from helpers import eqpage
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
