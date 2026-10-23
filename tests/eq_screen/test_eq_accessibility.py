"""Accessibility on Make an EQ (app\\tools\\a11y.py): every control on the page (both settings folds open) and in its
windows (All results, Compare, Run several, History, Find…, Sources) has a name a screen reader reads, and Tab
reaches it; the tracer's buttons stay out of the Tab order on purpose (Space is the picture's), so there only the
names. Moved from eq_checks.py's a11y_checks (lines 2540-2584), on a page opened as the old checks opened it (the
eq_screen fixture), with the result the old checks had on the card by then (a run, Retry, saved as "UI check" and
brought back with History's Show: lines 1528-1587; All results reads the result shown), offline. Since 2026-10-23 an
EQ to compare is kept on Listen's card first, so its row (the name box, Graph, ✕) is looked at too: a screen reader
read its name box as nothing, and no check had one there to see it."""
import pytest

from helpers import eqpage, qt

COVERS = ("a11y",)  # (app\tools\a11y.py, imported through helpers.paths.import_tool: no import statement shows it)


def _retry(s):
    """Retry from these filters: Best fit again from them (fine-tune), with the page's own Retry (line 1564), waited
    for (180 s)."""
    page = s.page
    run = page.run_result
    page.run(retry={"filters": page.active(), "add": False})
    if not s.wait_for(lambda: page.run_btn.isEnabled() and page.run_result is not run, 180):
        raise RuntimeError(f"Retry made no result: {page.progress_text.text()!r}")


@pytest.fixture(scope="module")
def as_old(eq_screen):
    """The result card and History as the old checks had them from line 1528 on: Best fit's Run (3 and 5 filters),
    Retry from its filters, saved as "UI check" (a saved EQ in History), brought back with History's Show (lines
    1528-1587): three runs this session. The saved EQ's History entry."""
    eqpage.quick_run(eq_screen)
    _retry(eq_screen)
    entry = eqpage.save_result(eq_screen)
    eqpage.show_from_history(eq_screen, entry)
    return entry


@pytest.mark.timeout(900)  # (the result made first: two Best fit runs, each allowed 180 s times the time factor)
def test_every_control_named_and_reachable(eq_screen, as_old, check):
    import net
    from helpers import paths
    from ui.all_results import AllResults
    from ui.compare_results import CompareResults
    from ui.history_window import HistoryWindow
    from ui.picker import Picker
    from ui.queue_window import QueueWindow
    from ui.sources_window import Sources
    a11y = paths.import_tool("a11y")
    page = eq_screen.page
    lis = page.listen
    kept = len(lis.pins)
    lis.add_selected()  # (an EQ to compare: its row on Listen's card is looked at too)
    folds = (page.settings.fold.btn.isChecked(), page.settings.adv.btn.isChecked())
    page.settings.fold.btn.setChecked(True)
    page.settings.adv.btn.setChecked(True)
    page.window().show()
    qt.pump(300)  # (shown for 0.3 s, as the old check: laid out)
    found = {"Make an EQ": (a11y.unnamed(page), a11y.unreachable(page))}
    pins = len(lis.pins) - kept
    page.settings.fold.btn.setChecked(folds[0])
    page.settings.adv.btn.setChecked(folds[1])
    if pins:  # (taken out again: the card as it was)
        lis.pins = lis.pins[:kept]
        lis.save_pins()
    was_off = net.offline()
    net.set_offline(True)
    try:
        for name, make in (("All results", lambda: AllResults(page)), ("Compare", lambda: CompareResults(page)),
                           ("Run several", lambda: QueueWindow(page)), ("History", lambda: HistoryWindow(page, False)),
                           ("Find…", lambda: Picker(page, "measurement")), ("Sources", lambda: Sources(page))):
            w = make()
            w.show()
            qt.pump(300)
            found[name] = (a11y.unnamed(w), a11y.unreachable(w))
            if name == "Sources":
                w._refresh_soon.stop()
            w.close()
        page.open_trace()
        page.tracer.show()
        qt.pump(300)
        found["Trace image"] = (a11y.unnamed(page.tracer), [])
        page.tracer.close()
    finally:
        net.set_offline(was_off)
    bad = {k: v for k, v in found.items() if v[0] or v[1]}
    # was eq_checks.py:2582
    check("access: every control on Make an EQ and in its windows has a name a screen reader reads, and Tab reaches "
          "it", not bad and pins == 1,
          ({k: ([f"{x[0]}:{x[1] or x[2][:16]}" for x in v[0]], [f"{x[0]}:{x[1]}" for x in v[1]])
            for k, v in bad.items()}, f"{pins} EQ to compare kept on Listen's card"))
