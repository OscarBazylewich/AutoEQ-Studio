"""Every window that blocks the app ends the same way (.claude\\notes\\UI-RULES.md 1, 2026-10-27, the user's ask: the
same kind of thing done the same way everywhere): its last row is window_parts.Footer (its extras at the left, its
own message line, its main action, then Close at the bottom right, plain) and it has no other Close. All results had
none at all; Run several's sat mid-window beside Cancel, over its table; Find…'s, History's, Sources', Compare's and
Which measurement's were each made by hand. And Enter in Compare presses nothing (Qt made "Show A" Enter's)."""
from helpers import eqpage, qt


def test_every_window_ends_with_the_footer(eq_screen, check):
    import net
    from PySide6.QtWidgets import QPushButton
    from ui.all_results import AllResults
    from ui.compare_results import CompareResults
    from ui.compare_window import CompareWindow
    from ui.history_window import HistoryWindow
    from ui.picker import Picker
    from ui.queue_window import QueueWindow
    from ui.sources_window import Sources
    page = eq_screen.page
    run, _r = page.current()
    if run is None or run.get("mode") == "manual":  # (All results and Compare need a run's result on the card)
        eqpage.quick_run(eq_screen)
    was_off = net.offline()
    net.set_offline(True)
    seen = {}
    try:
        for name, make in (("All results", lambda: AllResults(page)), ("Compare", lambda: CompareResults(page)),
                           ("Run several", lambda: QueueWindow(page)), ("History", lambda: HistoryWindow(page, False)),
                           ("Find…", lambda: Picker(page, "measurement")), ("Sources", lambda: Sources(page)),
                           ("Which measurement", lambda: CompareWindow(page))):
            w = make()
            w.show()
            qt.pump(200)
            footer = getattr(w, "footer", None)
            lay = w.layout()
            last = lay.itemAt(lay.count() - 1).widget() if lay is not None and lay.count() else None
            closes = [b for b in w.findChildren(QPushButton) if b.text() == "Close" and b.isVisibleTo(w)]
            at_right = footer is not None and footer.close_btn.geometry().right() >= footer.width() - 2
            seen[name] = (last is footer and footer is not None, closes == [getattr(footer, "close_btn", None)],
                          at_right, footer is not None and footer.close_btn.property("primary") not in (True, "true"))
            if hasattr(w, "_refresh_soon"):
                w._refresh_soon.stop()
            w.close()
            qt.pump(50)
    finally:
        net.set_offline(was_off)
    bad = {k: v for k, v in seen.items() if v != (True, True, True, True)}
    check("windows: every window that blocks the app ends with the same footer: its last row, Close at its right end "
          "and plain, no other Close (All results had none; Run several's sat mid-window)", len(seen) == 7 and not bad,
          bad or seen)


def test_enter_in_compare_presses_nothing(eq_screen, check):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ui.compare_results import CompareResults
    page = eq_screen.page
    if page.current()[1] is None:
        page.start_by_hand([{"type": "PK", "freq": 1000, "gain": 2, "q": 1}], "pasted", "Footers")
    before = (page.run_result, page.sel)
    dlg = CompareResults(page)
    dlg.show()
    qt.pump(100)
    dlg.combos[1].setFocus()
    QTest.keyClick(dlg.combos[1], Qt.Key_Return)
    qt.pump(50)
    after = (page.run_result is before[0], page.sel == before[1], dlg.isVisible(), dlg.footer.line.text.text())
    dlg.close()
    check("windows: Enter in Compare presses nothing (Qt made “Show A” Enter's: it put an EQ on the result card)",
          after == (True, True, True, ""), after)
