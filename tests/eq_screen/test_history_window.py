"""History on Make an EQ (ui\\history_window.py, ui\\eq_page.py, eq\\history.py): a saved EQ is kept once (copying it
again adds none); Show brings it back as a result of its own and loads its measurement as choosing it does; the
History window lists the EQs and ✕ removes one; a long History draws in batches and a typed search waits a moment; a
History file that can't be read is said and kept as .bad. Moved from eq_checks.py's ui_checks, review_checks and
review_low_checks: one page for the file (the eq_screen fixture), a quick run of its own saved as "UI check" (the
History entry the old checks used), then the checks in the old order. History starts empty here, as it did for the
old checks (the parts before them had emptied it)."""
import contextlib
import os
import time

import pytest
from PySide6.QtWidgets import QFrame

from helpers import eqpage, paths
from ui import history_window as hwm
from ui.history_window import HistoryWindow

COVERS_FILES = ("samples/**",)  # (the sample EarPods measurement, put in use before Show)
EARPODS = os.path.join(paths.SAMPLES, "measurements", "Apple EarPods - B&K 5128")


@pytest.fixture(scope="module")
def chain(eq_screen):
    """A result saved as "UI check" (eq_checks.py lines 1528-1532 and 1573-1574), and what each check leaves for the
    next one."""
    page = eq_screen.page
    page.choose_app("apo")  # (your EQ app as the old checks had chosen it before their run, line 1491)
    eqpage.quick_run(eq_screen)  # (raises when the run makes no result)
    run, _r = page.current()
    eqpage.save_result(eq_screen, "UI check")  # (raises when Save keeps nothing in History)
    return {"run": run}


def test_history_keeps_a_saved_eq(eq_screen, chain, check):
    page, run = eq_screen.page, chain["run"]
    kept = [e for e in page.history if e.get("saved")]  # (line 1578)
    page.copy_filters(page.active(), page.stats()["preamp_raw"])  # (the off-screen clipboard: Windows' isn't touched)
    chain["kept"] = kept
    # was eq_checks.py:1580
    check("ui: History keeps a saved EQ (copying the same one again doesn't add another)",
          len(kept) == 1 and len([e for e in page.history if e.get("saved")]) == 1
          and kept[0]["device"] == run["device"] and kept[0]["filters"], [e.get("label") for e in page.history])


def test_show_brings_it_back(eq_screen, chain, check):
    page, kept = eq_screen.page, chain["kept"]
    eqpage.show_from_history(eq_screen, kept[0])  # (History's Show, line 1583)
    shown = page.current()
    # was eq_checks.py:1585
    check("ui: History's Show brings the EQ back as a result of its own (its filters, “From History”)",
          shown[0].get("history") == kept[0]["base"] and len(page.EDIT) == len(kept[0]["filters"])
          and page.res_sub.text().startswith("From History"), page.res_sub.text())


def test_history_window_lists_and_removes(eq_screen, chain, check):
    page, kept = eq_screen.page, chain["kept"]
    hw = HistoryWindow(page, True)  # (lines 1589-1591: this IEM only, never shown)
    rows = len(hw.scroll.widget().findChildren(QFrame))
    hw.remove([kept[0]["key"]])
    # was eq_checks.py:1592
    check("ui: the History window lists the EQs (this IEM only) and ✕ removes one", rows >= 1 and not any(
          e["key"] == kept[0]["key"] for e in page.history), rows)
    hw.close()


def test_long_history_in_batches(eq_screen, check):
    page = eq_screen.page
    # (lines 1596-1613: History swapped for 300 made-up entries, put back after)
    real_history = page.history
    base = dict(real_history[0]) if real_history else {"device": "X", "target": "Y", "mode": "best_fit", "filters": [],
                                                         "n_filters": 0, "when": time.time()}
    page.history = [dict(base, key=f"many{i}", when=base.get("when", time.time()) - i * 60) for i in range(300)]
    rows_in = lambda w: sum(1 for x in w.scroll.widget().findChildren(QFrame) if type(x) is QFrame)  # (rows only)
    try:
        hw = HistoryWindow(page, False)
        first = rows_in(hw)
        eq_screen.wait_for(lambda: not hw._todo, 20)
        every = rows_in(hw)
        hw.q.setText("no such words at all")
        at_once = rows_in(hw)
        eq_screen.wait_for(lambda: rows_in(hw) == 0, 5)
        after = rows_in(hw)
        hw.close()
    finally:
        page.history = real_history
    # was eq_checks.py:1614
    check("ui: a long History draws its first rows at once and the rest after; a typed search waits a moment",
          first <= hwm.FIRST_ROWS < every == 300 and at_once == 300 and after == 0, (first, every, at_once, after))


def test_show_loads_the_measurement(eq_screen, chain, check, dialogs):
    page, entry = eq_screen.page, chain["kept"][0]  # (the saved EQ, though ✕ took it out of History: line 1640)
    # (another measurement in use first, as in the old run, where the tracer's "Sample IEM" was by then: so Show
    # really loads the EQ's own measurement again. Here the sample EarPods, added with Add… and chosen)
    dialogs.answer("getOpenFileNames", ([os.path.join(EARPODS, n) for n in sorted(os.listdir(EARPODS))], ""))
    page.add_files("measurement")
    dev = next(d for d, files in page.groups.items() if any(f["name"].startswith("Apple EarPods") for f in files))
    page.use_device(dev)
    eq_screen.wait_for(lambda: page.curves is not None and page.curves["name"] == dev
                       and page.listen.pins_for == dev, 30)
    if page.curves is None or page.curves["name"] == entry["device"] or page.listen.pins_for != dev:
        raise RuntimeError(f"another measurement than the EQ's should be in use before Show: {page.graph_title.text()}"
                           f" (Listen's EQs to compare for {page.listen.pins_for})")
    page.bring_back(entry)  # (lines 1692-1693)
    eq_screen.wait_for(lambda: page.curves is not None, 30)
    # was eq_checks.py:1694
    check("review: History's Show loads the measurement as a choice does (Listen's EQs to compare, Error without EQ)",
          page.curves and page.listen.pins_for == page.curves["name"] and page.chip_noeq.isVisibleTo(page),
          (page.listen.pins_for, page.curves and page.curves["name"]))


def test_unreadable_history_is_said(eq_screen, check, dialogs, fresh_studio):
    # (last in this file: it breaks History on purpose; fresh_studio puts the studio back after it)
    page = eq_screen.page
    hist = os.path.join(os.environ["AUTOEQSTUDIO_DATA"], "eq", "history.json")
    try:
        with open(hist, "w") as fh:  # (lines 1883-1888)
            fh.write("{cut off")
        dialogs.asked.clear()  # (the message boxes said so far: the old BOXES)
        page.svc.call("/api/history")
        eq_screen.wait_for(lambda: dialogs.asked, 5)
        boxes = [text for _kind, text in dialogs.asked]
        # was eq_checks.py:1889
        check("review: a data file that can't be read (History's) is said, kept as .bad", any("couldn't be read" in b for b in boxes)
              and os.path.exists(hist + ".bad"), boxes[-1:])
    finally:
        with contextlib.suppress(FileNotFoundError):  # (the file this test set aside: fresh_studio leaves .bad files)
            os.remove(hist + ".bad")
