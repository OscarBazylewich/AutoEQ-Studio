"""Make an EQ's page while Listen's ABX test starts and stops (ui\\listen.py's abx_begin and abx_end; measured
2026-11-13 with the fault of Calculate, which took the page to its top). Start ABX's row and the test's rows take the
place of each other. A click gives the button the focus; hidden with it, the button gave the focus to the next control
in the page's order (The selected EQ, named "Add the selected EQ"), and when the test stopped the page scrolled to it
(31 px and 40 px, measured). Now the rows that come take the focus (Listen to A; Start ABX). The page goes where it
goes when no control has the focus (the test's rows are taller than Start ABX's row: the page gets shorter when the
test stops). In tests\\eq_screen, not
tests\\listen: the fault is the page's position. One page for the file (the eq_screen fixture), an EQ made by hand
(with EQ off: the two versions a test needs)."""
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from helpers import qt


def _in_sight(page, w):
    vp = page.page_area.viewport()
    return w is not None and w.isVisible() and vp.rect().contains(QRect(w.mapTo(vp, QPoint(0, 0)), w.size()))


def _said(w):
    return None if w is None else f"{type(w).__name__} {w.text() if hasattr(w, 'text') else ''!r}"


def _round(page, at, mouse):
    """Start ABX, then Stop the test, the page put at at[0] and at[1] first. mouse: each pressed with a mouse click
    (it gives the button the focus); else with click() and no control with the focus. For each: the page's position
    after it, the control with the focus, and whether that control is in sight."""
    lis, bar = page.listen, page.page_area.verticalScrollBar()
    seen = []
    for k, button in enumerate((lambda: lis.abx_start,
                                lambda: next(b for b in lis.abx_box.findChildren(QPushButton)
                                             if b.text() == "Stop the test"))):
        bar.setValue(at[k])
        qt.pump(60)
        if QApplication.focusWidget() is not None:
            QApplication.focusWidget().clearFocus()
        b = button()
        if mouse:
            QTest.mouseClick(b, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
        else:
            b.click()
        qt.pump(150)
        f = QApplication.focusWidget()
        seen.append((bar.value(), _said(f), _in_sight(page, f)))
    return seen


def test_abx_start_and_stop_keep_the_page(eq_screen, check):
    page = eq_screen.page
    page.start_manual([{"type": "PK", "freq": 1000, "gain": 3.0, "q": 1.0}], "pasted", "ABX")
    lis, area = page.listen, page.page_area
    try:
        lis.show()
        lis.refresh()
        page.activateWindow()
        qt.pump(150)  # (Listen laid out: the page as long as it is)
        area.ensureWidgetVisible(lis.abx_start, 0, 200)
        qt.pump(60)
        at = [area.verticalScrollBar().value()]
        lis.abx_start.click()
        qt.pump(150)
        stop = next(b for b in lis.abx_box.findChildren(QPushButton) if b.text() == "Stop the test")
        bar = area.verticalScrollBar()
        bar.setValue(bar.maximum() - 100)  # (not at the page's end: the page gets shorter when the test stops)
        qt.pump(60)
        at.append(bar.value())
        stop_seen = _in_sight(page, stop)
        lis.abx_end(finished=False, quiet=True)
        qt.pump(150)
        plain = _round(page, at, mouse=False)
        clicked = _round(page, at, mouse=True)
    finally:
        if lis.abx is not None:
            lis.abx_end(finished=False, quiet=True)
        lis.stop()
        page.close_manual()
    check("listen: Start ABX clicked gives the focus to Listen to A, in sight, and the page goes where it goes with no "
          "control in focus (the focus went to Add the selected EQ)",
          clicked[0] == (plain[0][0], "QPushButton 'Listen to A'", True), (at, plain, clicked))
    check("listen: Stop the test clicked gives the focus to Start ABX, in sight, and the page goes where it goes with "
          "no control in focus (the page moved to Add the selected EQ: 31 px and 40 px, measured)",
          stop_seen and clicked[1] == (plain[1][0], "QPushButton 'Start ABX'", True),
          (at, stop_seen, plain, clicked))
