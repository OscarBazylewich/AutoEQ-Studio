"""Which measurement to use? (ui\\compare_window.py): the model's measurements ranked for the target, each with its
score and reasons, and Use putting the top one in use. Moved from eq_checks.py's ui_checks (lines 1473-1489), on a
page opened as the old checks opened it (the eq_screen fixture), offline: what's on this PC (the studio's samples)
and in the app is ranked, as the old checks did offline. The two are one chain, as there: one window, ranked, then
its top Use."""
import pytest


@pytest.fixture(scope="module")
def which(eq_screen):
    """Which measurement to use?, opened and shown as the old checks did (lines 1474-1476)."""
    from ui.compare_window import CompareWindow
    cw = CompareWindow(eq_screen.page)
    cw.show()
    return {"cw": cw}


@pytest.mark.timeout(900)  # (its answer is waited for up to 240 s, times the time factor, as the old check allowed)
def test_ranks_the_measurements(eq_screen, which, check):
    cw = which["cw"]
    cw.q.setText("gate")
    cw.run()
    compared = eq_screen.wait_for(lambda: cw.data is not None and not cw.busy, 240)
    items = (cw.data or {}).get("items") or []
    # was eq_checks.py:1481
    check("ui: Which measurement to use ranks the model's measurements for the target (each with its score and reasons)",
          compared and items and all("score" in c and c.get("reasons") is not None for c in items)
          and items == sorted(items, key=lambda c: -c["score"]), (compared, cw.status.text()))


def test_says_when_nothing_could_be_loaded(eq_screen, monkeypatch, check):
    # (a bug the tests' reorganization found, fixed 2026-10-22: when the model's measurements were found but none could
    # be loaded, the window failed with "list index out of range"; and its line said nothing called it was found)
    from eq import compare
    from helpers import qt, studio
    from ui.compare_window import CompareWindow
    # (two measurements of the model found, neither loadable: compare's search and download stood in, as
    # tests\eq\test_compare.py's nothing_loads does)
    found = [{"src": "db", "id": f"x{i}", "name": "Truthear GATe", "source": f"Site {i}", "site": f"Site {i}"}
             for i in range(2)]
    monkeypatch.setattr(compare, "candidates", lambda query, links=None: [dict(c) for c in found])

    def no_internet(c):
        raise OSError("no internet in the tests")
    monkeypatch.setattr(compare, "_fetch", no_internet)
    cw = CompareWindow(eq_screen.page)
    try:
        cw.data = compare.compare(eq_screen.page.S, "Truthear GATe", studio.target_path())
        cw.render()
        status, note = cw.status.text(), cw.note.text()
        reasons = [w.text() for w in cw.scroll.widget().findChildren(type(cw.status)) if w.text().startswith("Couldn't")]
    finally:
        qt.close(cw)
    check("ui: Which measurement says none of the model's measurements could be loaded, and why (not that nothing was "
          "found)", "could be loaded" in status and "was found" not in status and "could be loaded" in note
          and reasons and "no internet in the tests" in reasons[0], (status, note, reasons))


def test_use_puts_the_top_one_in_use(eq_screen, which, check):
    from PySide6.QtWidgets import QPushButton
    page, cw = eq_screen.page, which["cw"]
    uses = [b for b in cw.scroll.widget().findChildren(QPushButton) if b.text() == "Use"]
    if uses:
        uses[0].click()
        eq_screen.wait_for(lambda: not cw.isVisible(), 60)
    # was eq_checks.py:1488
    check("ui: Which measurement's Use puts the top one in use", uses and not cw.isVisible() and page.curves is not None,
          len(uses))
