"""Which measurement to use? (ui\\compare_window.py): the model's measurements ranked for the target, each with its
score and reasons, and Use putting the top one in use. Moved from eq_checks.py's ui_checks (lines 1473-1489), on a
page opened as the old checks opened it (the eq_screen fixture), offline: what's on this PC (the studio's samples)
and in the app is ranked, as the old checks did offline. The two are one chain, as there: one window, ranked, then
its top Use."""
import pytest

from helpers import qt


@pytest.fixture(scope="module", autouse=True)
def settled(eq_screen):
    """After the file's last test, the page's background work finished before the eq_screen fixture closes it: each
    load that ends starts the next in the background (the curves, their analysis, the automatic settings), and one
    still on its way once the page is deleted answers a page that's gone (an error inside a Qt call-back, "Internal
    C++ object already deleted"). Quiet for half a second: nothing running, nothing new started."""
    yield
    from PySide6.QtCore import QThreadPool
    idle = {"n": 0}

    def quiet():
        idle["n"] = idle["n"] + 1 if QThreadPool.globalInstance().activeThreadCount() == 0 else 0
        return idle["n"] >= 25
    qt.wait_for(quiet, 30)


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
