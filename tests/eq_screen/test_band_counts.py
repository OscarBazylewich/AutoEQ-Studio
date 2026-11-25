"""FxSound's band counts in Make an EQ: a run fits each of its counts (5, 10, 15, 20, 31) and Best result selects
one; the user selects another in Number of filters. No box of Settings holds the counts (the user, 2026-11-24: no
new control), with Automatic settings on or off. The items of Number of filters, All results (no grid), the Report,
Compare, History and the Queue say "bands"; Calculate from these filters keeps the card's band count. Peace is as
before (no box of its own). One page for the file (the eq_screen fixture: Automatic settings off at its start)."""
import copy
import html
import re

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from helpers import eqpage, qt

FILTERS = "best_fit.filter_counts"
ALL_COUNTS = [5, 10, 15, 20, 31]


@pytest.fixture(scope="module")
def rows(eq_screen):
    """The Settings fold open (a row hidden in a closed fold is not in sight)."""
    page = eq_screen.page
    page.settings.fold.btn.setChecked(True)
    qt.pump(50)
    return page.settings


def _in_sight(page, path):
    return page.settings.form.fields[path].box.isVisibleTo(page)


def _line(page, key):
    """The one line of the ⓘ after Your EQ app for an app, without the link."""
    return html.unescape(page.app_note_text(key).split(" <a ")[0])


def test_no_box_for_the_band_counts(eq_screen, rows, check):
    page, st = eq_screen.page, rows
    page.choose_app("fxsound")
    seen = {}
    for auto in (False, True):
        st.auto_switched(auto)
        page.refresh_auto()
        eq_screen.wait_for(lambda: page.estimate.text().startswith("5 EQs"), 30)
        seen[auto] = (page.estimate.text().split(" · ")[0], page.estimate.toolTip().split(" · ")[0],
                      _in_sight(page, FILTERS), _in_sight(page, "best_fit.low_shelf"), st.fixed_note.text(),
                      st.fixed_note.isVisibleTo(page), [p for p in st.form.fields if "band_count" in p])
    st.auto_switched(False)
    want = ("5 EQs, 5 to 31 bands", "FxSound: 5 EQs (5, 10, 15, 20, and 31 bands), -12 to +12 dB (1 dB steps)", False,
            False, "FxSound: Best fit adjusts band gains only. Edit range and step in More settings › Best fit.", True,
            [])
    check("band counts: with FxSound, Settings has no box for the band counts (Automatic settings on and off): "
          "Settings to try says 5 EQs, 5 to 31 bands, and the gray line under Best fit is as it was",
          seen == {False: want, True: want}, seen)
    page.choose_app("peace")
    peace = (_in_sight(page, FILTERS), _line(page, "peace"))
    page.choose_app("apo")
    check("band counts: Peace shows Filter counts to try, and its ⓘ reads “Up to 31 bands · ±30 dB”",
          peace == (True, "Up to 31 bands · ±30 dB"), peace)


@pytest.fixture(scope="module")
def five_counts(eq_screen, rows):
    """A run of FxSound on the result card (Automatic settings off): one result for each band count."""
    page = eq_screen.page
    page.choose_app("fxsound")
    page.S["auto"]["enabled"] = False
    before = page.run_result
    page.run_btn.click()
    eq_screen.wait_for(lambda: page.run_btn.isEnabled() and page.run_result is not before, 180)
    if page.run_result is None or page.run_result is before:
        raise RuntimeError(f"the FxSound run made no result: {page.progress_text.text()!r}")
    return page.run_result


def test_a_run_of_five_band_counts_on_the_result_card(eq_screen, five_counts, check):
    from ui.eq_page_cards import COUNT_LONGEST
    page, run = eq_screen.page, five_counts
    by_n = {r["n_filters"]: r for r in run["results"]}
    items = [page.count_combo.itemText(i) for i in range(page.count_combo.count())]
    want = [f"{n} bands  ·  {r['rms']:.2f} dB" + ("  ✓ recommended" if r["id"] == run["pick"] else "")
            for n, r in sorted(by_n.items())]
    picked = next(r for r in run["results"] if r["id"] == run["pick"])["n_filters"]
    fm = page.count_combo.fontMetrics()
    widths = [fm.horizontalAdvance(t) for t in items]
    got = (sorted(by_n), items, page.count_lab.text(), page.all_btn.text(), page.res_sub.text())
    check("band counts: a run of FxSound's five band counts gives one result for each, and Number of filters lists each "
          "as “N bands · error”, the app's pick marked",
          got[0] == ALL_COUNTS and items == want and got[2] == "Number of filters" and got[3] == "All 5 results…",
          (got, want))
    check("band counts: each item of the list fits the width of the list (its longest item)",
          max(widths) <= fm.horizontalAdvance(COUNT_LONGEST), (widths, fm.horizontalAdvance(COUNT_LONGEST)))
    # (in Segoe UI "00 bands" is wider than "00 filters": the longest line was the one with "filters")
    forms = {w: fm.horizontalAdvance(f"00 {w}  ·  00.00 dB  ✓ recommended") for w in ("filters", "bands")}
    check("band counts: the width of Number of filters takes the longer of the two words of a count, “filters” and "
          "“bands”", fm.horizontalAdvance(COUNT_LONGEST) >= max(forms.values()),
          (forms, fm.horizontalAdvance(COUNT_LONGEST)))
    # (the same form as Settings to try, "-12 to +12 dB (1 dB steps)": the line said "-12.0 to +12.0 dB (1.0 dB
    # steps)")
    check("band counts: the line of the result names the band count of the pick, and the range and step of the sliders "
          "as Settings to try does",
          f"FxSound: {picked} bands, -12 to +12 dB (1 dB steps)" in got[4], got[4])
    half = page.run_label({"mode": "best_fit"}, {"engine": "graphic", "layout": "graphic_10", "n_filters": 10,
                                                 "gain_min": -6.5, "gain_max": 6.5, "step": 0.5})
    none = page.run_label({"mode": "best_fit"}, {"engine": "graphic", "layout": "graphic_10", "n_filters": 10})
    check("band counts: the line of a graphic EQ's result keeps a half dB, and a result with no range (an old History "
          "entry) still has its line",
          half == "10-band graphic EQ: 10 bands, -6.5 to +6.5 dB (0.5 dB steps)" and none.startswith("10-band graphic EQ: 10 bands"),
          (half, none))
    a, b = {"id": 1, "ear": 0.18, "ear_at": 2500.0, "engine": "graphic"}, {"id": 2, "ear": 0.47, "ear_at": 6200.0,
                                                                         "engine": "graphic"}
    far = dict(a, ear=0.52)
    notes = (page.pick_note({"pick": 1, "pick_case": "target", "ear_db": 0.25, "results": [a]}, a),
             page.pick_note({"pick": 1, "pick_case": "best", "ear_db": 0.25, "results": [far, b]}, far))
    check("band counts: the note of the pick says “bands” for a graphic EQ's result",
          notes == ("Audibly matches target: within 0.18 dB (limit: 0.25 dB), using the fewest bands needed",
                    "Couldn't match target: closest is 0.47 dB off near 6.2 kHz (fewer bands)"), notes)


def test_all_results_of_five_band_counts_has_no_grid(eq_screen, five_counts, check):
    from ui.all_results import AllResults
    page = eq_screen.page
    ar = AllResults(page)
    try:
        hidden = (ar.grid.isHidden(), ar.grid_title.isHidden(), ar.table.isColumnHidden(3))
        counts = sorted(ar.table.item(i, 1).value for i in range(ar.table.rowCount()))
        gains = {ar.table.item(i, 4).text() for i in range(ar.table.rowCount())}
        marked = [ar.table.item(i, 0).text() for i in range(ar.table.rowCount())
                  if "✓ recommended" in ar.table.item(i, 0).text()]
        check("all results: a run of a graphic EQ's band counts shows no error grid (each count has its own Q) and no "
              "Range column (its bands are fixed), and the table has a row for each of the 5 results, the pick "
              "marked, the slider range without decimals",
              hidden == (True, True, True) and counts == ALL_COUNTS and len(marked) == 1 and gains == {"-12 to 12"},
              (hidden, counts, marked, gains))
    finally:
        ar.close()
        ar.deleteLater()


def test_the_report_of_five_band_counts_has_no_grid(eq_screen, five_counts, check):
    # (the page sends "engine" with each result of the run: without it the Report drew the grid by filter count and
    # maximum Q, filled only on its diagonal. eq.report.grids_for alone was tested)
    page, run = eq_screen.page, five_counts
    page.run_result = run
    page.show_result(run["pick"])
    path = page.report(open_it=False)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    shown = next(r for r in run["results"] if r["id"] == run["pick"])
    check("report: the Report of a run of FxSound's band counts has no error grid, and has the filter table of the "
          "result shown",
          "error by filter count and maximum Q" not in text and "Best fit: error by" not in text
          and text.count("<table") == 1 and f"{shown['n_filters']} bands" in text,
          (path, text.count("<table"), "error by filter count" in text))


def test_compare_and_history_say_bands(eq_screen, five_counts, check):
    from ui.compare_results import options
    from ui.history_window import HistoryWindow
    page, run = eq_screen.page, five_counts
    page.run_result = run
    page.show_result(run["pick"])
    shown = next(r for r in run["results"] if r["id"] == run["pick"])
    labels = [o["label"] for o in options(page) if o["run"] is run and not o["label"].startswith("Shown: ")]
    want = [f"#{run.get('n', '?')} · {r['n_filters']} bands · {r['rms']:.2f} dB"
            for r in sorted(run["results"], key=lambda r: r["n_filters"]) if r["id"] != run["pick"]]
    check("compare: the other results of a run of band counts read “#n · N bands · error”",
          len(want) == 4 and labels == want, (labels, want))
    entry = eqpage.save_result(eq_screen, "Band counts check")
    hist = [o["label"] for o in options(page) if o["run"] is None]
    hw = HistoryWindow(page, False)
    kept = []
    add = page.listen.add
    # (the name and the engine only: no EQ goes into the list)
    page.listen.add = lambda name, *a, **k: kept.append((name, k.get("engine"))) or True
    try:
        lines = [w.text().replace(chr(0xA0), " ") for w in hw.findChildren(QLabel)
                 if " bands" in w.text().replace(chr(0xA0), " ")]
        hw.keep_to_compare(entry)
    finally:
        page.listen.add = add
        hw.close()
        hw.deleteLater()
    n = shown["n_filters"]
    check("history: a saved result of a graphic EQ reads “N bands” in Compare's list and in the History window",
          entry["result"].get("engine") == "graphic" and any(h.endswith(f" · {n} bands") for h in hist)
          and any(f"· {n} bands ·" in t for t in lines), (hist, lines))
    # (its engine too: Listen's row of the EQ counts bands with it, 2026-11-24)
    check("history: Keep to compare names the EQ of a graphic result “Best fit, N bands (day time)” and "
          "gives Listen its engine",
          len(kept) == 1 and kept[0][0].startswith(f"Best fit, {n} bands (") and kept[0][1] == "graphic", kept)


@pytest.mark.timeout(600)
def test_calculate_from_a_card_with_bands_switched_off_keeps_its_band_count(eq_screen, five_counts, check):
    # (the band count of the card was taken from the number of filters switched on: the 10-band card with 5 bands
    # off gave the 5-band EQ, at other frequencies than the card)
    page, run = eq_screen.page, five_counts
    page.run_result = run
    ten = next(r for r in run["results"] if r["n_filters"] == 10)
    page.show_result(ten["id"])
    for f in page.EDIT[:5]:
        f["enabled"] = False
    sent = page.retry_from_card(False)
    try:
        page.retry_btn.menu().actions()[0].trigger()  # (Adjust them)
        eq_screen.wait_for(lambda: page.run_btn.isEnabled() and page.run_result is not run, 180)
        again = page.run_result
        rows = [r.get("rows") for r in (again or {}).get("results") or []] if again is not run else None
        freqs = [f["freq"] for f in again["results"][0]["filters"]] if rows else None
    finally:
        page.run_result = run
        page.show_result(run["pick"])
    check("band counts: Calculate from these filters on the 10-band FxSound card with 5 bands switched off sends the "
          "whole card, and the new result has the 10 bands of the card",
          len(sent["filters"]) == 5 and len(sent["card"]) == 10 and rows == [10]
          and freqs == [f["freq"] for f in ten["filters"]], (len(sent["filters"]), len(sent["card"]), rows, freqs))


@pytest.mark.timeout(600)
def test_a_queued_run_says_bands(eq_screen, five_counts, check):
    from ui.queue_window import QueueWindow, _ticked
    page = eq_screen.page
    kept_S = copy.deepcopy(page.S)
    q = QueueWindow(page)
    try:
        q.tgts.item(0).setCheckState(Qt.Checked)
        n = len(_ticked(q.devs)) * len(_ticked(q.tgts))
        q.start()
        done = eq_screen.wait_for(lambda: not q.running, 300)
        said = [q.table.item(i, 2).text() for i in range(q.table.rowCount())]
    finally:
        q.close()
        page.S = kept_S
        page.svc.call("/api/settings", {"settings": page.S})
    check("queue: a queued run of FxSound's band counts says “Done · N bands · error”",
          done and n >= 1 and len(said) == n and all(re.match(r"Done · \d+ bands · \d+\.\d\d dB · ", s) for s in said),
          (done, n, said))
