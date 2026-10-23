"""Find… (ui\\picker.py): one search over the app's files, this PC and the online lists (offline: the saved ones),
its long list drawn in batches and keeping its place, asking only for the lists' counts while they haven't changed,
the rig filter, Show (a curve on the graph without using it), an online entry offline, Use (a file from this PC into
the app, with Undo); Enter in Find…'s and History's search boxes pressing no button; and every list A to Z.

Moved from eq_checks.py's ui_checks (lines 1380-1472), review_checks (1743-1763), review_low_checks (1862-1881) and
order_checks (2324-2380), on one page (the eq_screen fixture), offline throughout.
- The first eight are one chain, as there: one Find… window (the `find` fixture), its rows for "gate" kept by the
  first for the later ones. Its This PC rows are the studio's samples (This PC's search is set to them): the old run
  found the user's own files there too.
- The old checks from line 1528 on had a result on the card and a saved EQ in History (a run, Retry, Save, History's
  Show), and by the A to Z check the page also owned windows earlier checks had left there (Which measurement,
  Sources, the tracer, Compare…), whose drop-downs its sweep of every drop-down went through. Both are built here
  before those checks (the `as_old` fixture, and _windows_as_old)."""
import os

import pytest

from helpers import eqpage, session

# (as the old checks: the names of the two checks that say "skip" when this PC lacks what they need)
OFFLINE_ENTRY = "ui: offline, an online entry never downloaded says it needs the internet (nothing fetched)"
USE_UNDO = "review: Use offers Undo, which takes the file it made away and puts the measurement back"


def _rows(pk):
    """Find…'s rows now (not its headings and notes)."""
    from PySide6.QtCore import Qt
    return [pk.list.item(i).data(Qt.UserRole) for i in range(pk.list.count()) if pk.list.item(i).data(Qt.UserRole)]


@pytest.fixture(scope="module")
def find(eq_screen):
    """Find… for a measurement as the old checks opened it (lines 1381-1386): offline, This PC's search on the
    studio's samples, shown. The chain's tests share it (and `rows`, its rows for "gate")."""
    import net
    from ui.picker import Picker
    page = eq_screen.page
    net.set_offline(True)
    page.S["library"]["folders"] = [os.path.join(session.SESSION.studio, "samples")]
    pk = Picker(page, "measurement")
    pk.show()
    return {"pk": pk, "rows": []}


def test_searches_three_sources(eq_screen, find, check):
    pk = find["pk"]
    loaded = eq_screen.wait_for(lambda: not pk.db.get("loading") and not pk.lib.get("scanning"), 120)
    pk.q.setText("gate")
    pk.render()
    pk.finish_list()
    rows = find["rows"] = _rows(pk)
    srcs = {r["src"] for r in rows}
    # was eq_checks.py:1393
    check("ui: Find… searches the app's files, this PC and the online lists (offline: the saved ones)",
          loaded and "app" in srcs and "pc" in srcs and ("db" in srcs or not pk.db.get("items")),
          (loaded, srcs, pk.status.text()))


def test_long_list_in_batches_keeps_its_place(eq_screen, find, monkeypatch, check):
    # (both checks in one test, as their numbers were taken in one go: first and every before the place is checked)
    from PySide6.QtWidgets import QApplication
    pk = find["pk"]
    # a long list: the first rows at once, the rest a batch at a time (each row is ~2 ms of widgets: a key waited)
    monkeypatch.setattr(pk, "db", {"items": [[f"fake{i}", "m", f"Fakeone {i}", "Sub", "Site", None, "", ""]
                                             for i in range(200)], "loading": False})
    monkeypatch.setattr(pk, "src", "db")
    pk.q.setText("fakeone")
    pk.render()
    first = len(_rows(pk))
    eq_screen.wait_for(lambda: not pk._pending, 10)
    every = len(_rows(pk))
    # (review 2) drawn again with the same search (Show, a file ticked, a list loaded): the place in the list stays
    pk.resize(700, 500)
    QApplication.processEvents()
    bar = pk.list.verticalScrollBar()
    bar.setValue(bar.maximum() // 2)
    pk.list.setCurrentRow(120)
    was = bar.value()
    pk.render()
    QApplication.processEvents()
    # was eq_checks.py:1413
    check("ui: Find… drawn again with the same search keeps its place in the list and the selected row",
          was > 0 and abs(bar.value() - was) <= 2 and pk.list.currentRow() == 120,
          (was, bar.value(), pk.list.currentRow()))
    pk.q.setText("fakeone 19")
    pk.render()
    pk.finish_list()
    narrowed = [r["name"] for r in _rows(pk)]
    monkeypatch.undo()  # (the real lists and source back, as the old check put them back here)
    pk.q.setText("gate")
    pk.render()
    pk.finish_list()
    # was eq_checks.py:1423
    check("ui: Find…'s long list makes its first rows at once and the rest after (typing doesn't wait for 120 rows)",
          first <= 30 and every == 200 and sorted(narrowed) == sorted(f"Fakeone {i}" for i in range(200) if "19" in str(i)),
          (first, every, narrowed[:12]))


def test_asks_only_for_the_counts(eq_screen, find, monkeypatch, check):
    # while nothing changes, Find… asks for the counts only (the whole lists, 55,000 rows, were built every 0.5 s)
    page, pk = eq_screen.page, find["pk"]
    asked, drawn = [], []

    class _Counting:
        def call(self, route, body=None):
            asked.append((route, bool((body or {}).get("items"))))
            return page.svc.call(route, body)
    pk._later.stop()  # (the search typed above: its own drawing, not the poll's)
    monkeypatch.setattr(pk, "svc", _Counting())
    monkeypatch.setattr(pk, "render", lambda: drawn.append(1))
    pk._load()
    eq_screen.wait_for(lambda: not pk._fetching, 10)
    monkeypatch.undo()  # (both put back before the check, as the old check did)
    # was eq_checks.py:1440
    check("ui: Find… asks only for the lists' counts while they haven't changed, and doesn't draw its list again",
          asked and not any(items for _r, items in asked) and not drawn, (asked, len(drawn)))


def test_rig_filter(eq_screen, find, check):
    pk = find["pk"]
    pk.set_filter("rig", "5128")
    kept = _rows(pk)
    # was eq_checks.py:1444
    check("ui: Find…'s rig filter leaves only that rig, and its list counts them",
          kept and all(pk.rig_of(r) == "5128" for r in kept) and "5128" in pk.f_rig.currentText(),
          [r["rig"] for r in kept][:5])


def test_show_draws_without_using(eq_screen, find, check):
    page, pk = eq_screen.page, find["pk"]
    pk.clear_filters()
    app_row = next((r for r in find["rows"] if r["src"] == "app"), None)
    if app_row is not None:
        pk.preview(app_row)
        eq_screen.wait_for(lambda: page.previews, 30)
    # was eq_checks.py:1450
    check("ui: Find…'s Show draws the curve on the graph without using it",
          app_row is not None and [p[0] for p in page.previews] == [app_row["key"]],
          page.previews if app_row is not None else "no row of the app's own for “gate”")
    if app_row is not None:
        page.remove_preview(app_row["key"])


def test_online_entry_offline(eq_screen, find, monkeypatch, check):
    from PySide6.QtWidgets import QMessageBox
    page, pk = eq_screen.page, find["pk"]
    db_row = next((r for r in pk.db_rows([]) if not r.get("link") and r["src"] == "db"), None)
    if not db_row:  # (as the old check, which said "skip" then)
        check.skipped("no database lists on this PC to try it with", OFFLINE_ENTRY)
    # (one new list for what the page says in its status line and the message boxes, as the old check had: it
    # rebound its `said`, which the page's status line wrote into too)
    said = []
    monkeypatch.setattr(page, "status", lambda text, ms=0: said.append(text))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: said.append(a[2])))
    pk.choose(db_row)
    eq_screen.wait_for(lambda: said or pk.busy is None and not pk.isVisible(), 60)
    eq_screen.wait_for(lambda: said, 30)
    # was eq_checks.py:1466
    check(OFFLINE_ENTRY, said and "offline" in said[0] and "Online" in said[0], said)


def test_use_from_this_pc(eq_screen, find, check):
    page, pk = eq_screen.page, find["pk"]
    pc_row = next(iter(pk.pc_rows(["gate"])), None)
    used = False
    if pc_row is not None:
        pk.choose(pc_row)
        used = eq_screen.wait_for(lambda: not pk.isVisible() and page.curves is not None, 60)
    # was eq_checks.py:1471
    check("ui: Find…'s Use puts a file from this PC into the app and in use", used and any(
          f["included"] for f in page.groups.get(page.measurement_combo.currentData(), [])),
          page.measurement_combo.currentText() if pc_row is not None else "no This PC row for “gate”")


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
def test_enter_presses_no_button(eq_screen, as_old, check):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from ui.history_window import HistoryWindow
    from ui.picker import Picker
    page, qapp = eq_screen.page, eq_screen.qapp
    pk = Picker(page, "measurement")
    pk.show()
    src = pk.src
    pk.q.setText("zzzz qqqq none")
    pk.q.setFocus()
    QTest.keyClick(pk.q, Qt.Key_Return)
    qapp.processEvents()
    pk_ok = pk.isVisible() and pk.src == src
    pk.close()
    hw = HistoryWindow(page, False)  # (with the saved EQ in it: each of its rows has a Show button)
    hw.show()
    run_before = page.run_result
    hw.q.setFocus()
    QTest.keyClick(hw.q, Qt.Key_Return)
    qapp.processEvents()
    hw_ok = hw.isVisible() and page.run_result is run_before
    hw.close()
    # was eq_checks.py:1762
    check("review: Enter in Find…'s and History's search boxes presses no button (no source reset, no EQ brought back)",
          pk_ok and hw_ok, (pk_ok, hw_ok))


def _windows_as_old(s):
    """The windows the old checks had made on the page by the A to Z check, closed but still there (each a child of
    the page): Which measurement (line 1475), Sources (2032), the tracer (2079) and Compare… (2485). The check's sweep
    of every drop-down the page owns went through theirs too."""
    from ui.compare_results import CompareResults
    from ui.compare_window import CompareWindow
    from ui.sources_window import Sources
    page = s.page
    cw = CompareWindow(page)  # (it compares the model in use by itself: offline, what's on this PC and in the app)
    cw.show()
    s.wait_for(lambda: not cw.busy, 240)
    cw.close()
    src = Sources(page)
    src._refresh_soon.stop()
    src.reject()
    page.open_trace()
    page.tracer.close()
    cr = CompareResults(page)
    cr.show()
    cr.close()


@pytest.mark.timeout(900)  # (as above, when it runs first)
def test_lists_a_to_z(eq_screen, as_old, check):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication, QComboBox
    from ui.picker import Picker
    from ui.search_combo import SEARCH_FROM, SearchCombo, natural_key
    page = eq_screen.page
    _windows_as_old(eq_screen)
    keyed = sorted(["IEM 10", "iem 2", "IEM 1", "Alpha  b"], key=natural_key)
    names = [page.target_combo.itemText(i) for i in range(page.target_combo.count())]
    devs = list(page.groups)
    pk = Picker(page, "measurement")
    pk.finish_list()  # (at once, as the old check: not waiting for its lists)
    rows = _rows(pk)
    app_rows = [r["name"] for r in rows if r["src"] == "app"]
    pc_rows = [r["name"] for r in rows if r["src"] == "pc"]
    combos = all(isinstance(b, SearchCombo) for b in (pk.f_rig, pk.f_form, pk.f_site))
    sites = [pk.f_site.itemData(i) for i in range(pk.f_site.count())]
    # a list over SEARCH_FROM choices opens with the search box; typed in part, the one left; Enter chooses it
    big, small = SearchCombo(), SearchCombo()
    big.addItems([f"Choice {i}" for i in range(1, SEARCH_FROM + 6)])
    small.addItems(["a", "b", "c"])
    last = big.itemText(big.count() - 1)
    big.showPopup()
    pop = big._popup
    pop.q.setText(last)
    shown = [pop.list.item(k).text() for k in range(pop.list.count()) if not pop.list.item(k).isHidden()]
    QApplication.sendEvent(pop.q, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
    chosen = (big.currentIndex() == big.count() - 1, pop.isVisible())
    lay = page.settings.adv_form.fields["best_fit.layout"].box
    rule = (big.searches(), small.searches(), isinstance(lay, SearchCombo) and lay.searches(),
            all(isinstance(b, SearchCombo) for b in page.findChildren(QComboBox)))
    # every drop-down A to Z, numbers as numbers (a first "Choose…" or "Automatic…" may stay on top); Find…'s filters
    # keep their own order (any, "fits", in the app and this PC first, "not known" last)
    unsorted = []
    for c in page.findChildren(SearchCombo):
        # (the Target and Measurement lists: A to Z by name, their own check above; the counts after a name aside)
        if isinstance(c.window(), Picker) or c.count() < 3 or c in (page.target_combo, page.measurement_combo):
            continue
        texts = [c.itemText(k) for k in range(c.count())]
        if not any(texts[k:] == sorted(texts[k:], key=natural_key) for k in (0, 1)):
            unsorted.append((texts[:4], type(c.parent()).__name__))
    pk.clear_filters()
    pk.reject()
    # was eq_checks.py:2370
    check("order: the Target and Measurement lists and Find…'s rows A to Z, numbers as numbers; Find…'s filter lists "
          "open with a search box that narrows them, Enter chooses; every drop-down searches when over SEARCH_FROM "
          "choices (Advanced's Layout), a short one doesn't; every drop-down A to Z",
          keyed == ["Alpha  b", "IEM 1", "iem 2", "IEM 10"] and sorted(["0.8", "0.707", "0.42", "0.5"], key=natural_key) == ["0.42", "0.5", "0.707", "0.8"] and names == sorted(names, key=natural_key)
          and devs == sorted(devs, key=natural_key) and app_rows == sorted(app_rows, key=natural_key)
          and pc_rows == sorted(pc_rows, key=natural_key) and combos and len(sites) >= 2 and shown == [last]
          and chosen == (True, False) and sites[0] == "" and sites[1] in ("app", "pc")
          and rule == (True, False, True, True) and not unsorted,
          (combos, sites[:4], last, shown, chosen, rule, unsorted[:3], names == sorted(names, key=natural_key),
           devs == sorted(devs, key=natural_key), app_rows == sorted(app_rows, key=natural_key),
           pc_rows == sorted(pc_rows, key=natural_key), keyed))


def test_use_offers_undo(eq_screen, dialogs, check):
    from ui.picker import Picker
    page = eq_screen.page
    pk = Picker(page, "measurement")
    eq_screen.wait_for(lambda: not pk.lib.get("scanning"), 60)
    row = next(iter(pk.pc_rows(["earpods"])), None)
    pk.close()
    if not row:  # (as the old check, which said "skip" then)
        check.skipped("no sample measurement found on this PC", USE_UNDO)
    before = list(page.S["files"]["excluded"])
    res = page.svc.call("/api/use", dict(pk.body(row), kind="measurement", settings=page.S))
    page.used(res)
    offered = page.notice.isVisibleTo(page) and page.notice_undo.isVisibleTo(page)
    page.notice_undo.click()
    eq_screen.wait_for(lambda: not any(n in {m["name"] for m in page.inputs["measurements"]}
                                       for n in res.get("created") or []), 30)
    names_now = {m["name"] for m in page.inputs["measurements"]}
    # was eq_checks.py:1875
    check(USE_UNDO,
          offered and sorted(page.S["files"]["excluded"]) == sorted(before)
          and not any(n in names_now for n in res.get("created") or []),
          (offered, res.get("created"), sorted(set(page.S["files"]["excluded"]) ^ set(before)),
           [n for n in res.get("created") or [] if n in names_now], dialogs.asked[-2:]))
