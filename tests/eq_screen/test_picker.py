"""Find… (ui\\picker.py): one search over the app's files, this PC and the online lists (offline: the saved ones),
its long list drawn in batches and keeping its place, asking only for the lists' counts while they haven't changed,
the rig filter, Show (a curve on the graph without using it), an online entry offline, Use (a file from this PC into
the app, with Undo); Enter in Find…'s and History's search boxes pressing no button; and every list A to Z. Its
Windows 11 look (the restyle, 2026-10-23): rows whole at the new text size, the accent on one Use only, each row's ✕
quiet, the download mark read as words, and its size within a laptop's screen at 150 % and 175 % (stood in); and the
recheck's (the same day): its rows as wide as the list after it's made narrower, everything whole in a frame as
narrow as the Guide's (its filters on two lines, a long name ending in "…"), Files with Windows 11's chevron.

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

from helpers import eqpage, qt, session

# (as the old checks: the names of the two checks that say "skip" when this PC lacks what they need)
OFFLINE_ENTRY = "ui: offline, an online entry never downloaded says it needs the internet (nothing fetched)"
USE_UNDO = "review: Use offers Undo, which takes the file it made away and puts the measurement back"
# (a 1920 x 1080 laptop's room above the taskbar at 150 % and 175 %, as Qt gives it; and Windows 11's title bar there)
SMALL_SCREENS = ((1280, 672), (1097, 569))
TITLE_BAR = 32


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
    # (made firm 2026-10-22: the old check read the rows at once, before This PC's search had finished, so it saw no
    # This PC rows and its "A to Z" for them could never fail. Now its lists and This PC's search are waited for, and
    # This PC's rows (the studio's samples: six) must be there to put in order; the app has one measurement set)
    loaded = eq_screen.wait_for(lambda: not pk.db.get("loading") and not pk.lib.get("scanning"), 120)
    pk.render()
    pk.finish_list()
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
    # (deleted now, not left for Python's garbage collector: big and its pop-up hold each other, and on GitHub's run
    # of 2026-10-22 the collector deleted them in the next test, while Qt was handing the pop-up an event: a crash)
    qt.close(big)
    qt.close(small)
    # every drop-down A to Z, numbers as numbers (a first "Choose…" or "Automatic…" may stay on top, or the special
    # choices a list pins there: its sort_items' pinned, 2026-10-27); Find…'s filters keep their own order (any,
    # "fits", in the app and this PC first, "not known" last)
    unsorted = []
    for c in page.findChildren(SearchCombo):
        # (the Target and Measurement lists: A to Z by name, their own check above; the counts after a name aside)
        if isinstance(c.window(), Picker) or c.count() < 3 or c in (page.target_combo, page.measurement_combo):
            continue
        texts = [c.itemText(k) for k in range(c.count())]
        if not any(texts[k:] == sorted(texts[k:], key=natural_key) for k in (0, 1, c.pinned)):
            unsorted.append((texts[:4], type(c.parent()).__name__))
    pk.clear_filters()
    pk.reject()
    # was eq_checks.py:2370
    check("order: the Target and Measurement lists and Find…'s rows A to Z, numbers as numbers; Find…'s filter lists "
          "open with a search box that narrows them, Enter chooses; every drop-down searches when over SEARCH_FROM "
          "choices (Advanced's Layout), a short one doesn't; every drop-down A to Z",
          keyed == ["Alpha  b", "IEM 1", "iem 2", "IEM 10"] and sorted(["0.8", "0.707", "0.42", "0.5"], key=natural_key) == ["0.42", "0.5", "0.707", "0.8"] and names == sorted(names, key=natural_key)
          and devs == sorted(devs, key=natural_key) and app_rows == sorted(app_rows, key=natural_key)
          and pc_rows == sorted(pc_rows, key=natural_key) and loaded and app_rows and len(pc_rows) >= 2
          and combos and len(sites) >= 2 and shown == [last]
          and chosen == (True, False) and sites[0] == "" and sites[1] in ("app", "pc")
          and rule == (True, False, True, True) and not unsorted,
          (combos, sites[:4], last, shown, chosen, rule, unsorted[:3], names == sorted(names, key=natural_key),
           devs == sorted(devs, key=natural_key), app_rows == sorted(app_rows, key=natural_key),
           pc_rows == sorted(pc_rows, key=natural_key), keyed, loaded, len(app_rows), len(pc_rows)))


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
    offered = eq_screen.undo_offered()  # (Undo beside the message, in the window's line)
    eq_screen.undo()
    eq_screen.wait_for(lambda: not any(n in {m["name"] for m in page.inputs["measurements"]}
                                       for n in res.get("created") or []), 30)
    names_now = {m["name"] for m in page.inputs["measurements"]}
    # was eq_checks.py:1875
    check(USE_UNDO,
          offered and sorted(page.S["files"]["excluded"]) == sorted(before)
          and not any(n in names_now for n in res.get("created") or []),
          (offered, res.get("created"), sorted(set(page.S["files"]["excluded"]) ^ set(before)),
           [n for n in res.get("created") or [] if n in names_now], dialogs.asked[-2:]))


# ---------------------------------------------------------------- the Windows 11 look (the restyle, 2026-10-23)
def _shown_picker(page, query):
    """Find… for a measurement, shown, its lists and This PC's search waited for, `query` searched, every row made
    and laid out."""
    from ui.picker import Picker
    pk = Picker(page, "measurement")
    pk.show()
    qt.wait_for(lambda: not pk.db.get("loading") and not pk.lib.get("scanning"), 120)
    pk.q.setText(query)
    pk._later.stop()
    pk.render()
    pk.finish_list()
    qt.pump(300)  # (laid out: each row's widgets in their place)
    return pk


def _close(pk):
    """Find… closed and deleted, then Qt let work a moment: anything the window left to do (a timer of its own) runs
    while this test is still the one running, so an error in it fails this test (it was found in the next file's)."""
    qt.close(pk)
    qt.pump(100)


def test_rows_keep_their_height(eq_screen, check):
    # (at 10.5 pt a row's height was taken before the theme's text size reached it, and Qt put the row's widgets
    # inside the lists' 7 px padding: names lost their lower parts, buttons were cut)
    from PySide6.QtWidgets import QLabel, QPushButton
    pk = _shown_picker(eq_screen.page, "gate")
    try:
        rows, cut = 0, []
        for i in range(pk.list.count()):
            w = pk.list.itemWidget(pk.list.item(i))
            if w is None:
                continue
            rows += 1
            short = [f"{type(x).__name__} “{x.text()[:24] if hasattr(x, 'text') else 'the row'}” {x.height()} < "
                     f"{x.sizeHint().height()}" for x in [w] + w.findChildren(QLabel) + w.findChildren(QPushButton)
                     if x.isVisible() and x.height() < x.sizeHint().height()]
            if short:
                cut.append((i, short[:2]))
    finally:
        _close(pk)
    check("restyle: Find…'s rows keep their whole height at Windows 11's text size (no name or button cut)",
          rows >= 3 and not cut, (rows, cut[:4]))


def test_one_use_has_the_accent(eq_screen, check):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton
    pk = _shown_picker(eq_screen.page, "")
    try:
        rows = [i for i in range(pk.list.count()) if pk.list.item(i).data(Qt.UserRole)]

        def accented():
            """The rows whose Use (found by its words, as the Guide finds it) has the accent."""
            return [i for i in rows for b in pk.list.itemWidget(pk.list.item(i)).findChildren(QPushButton)
                    if b.text() == "Use" and b.property("primary") in (True, "true")]
        first = accented()
        pk.list.setCurrentRow(rows[2])
        chosen = accented()
        pk.render()  # (drawn again with the same search: the place and the chosen row kept, its Use too)
        pk.finish_list()
        rows = [i for i in range(pk.list.count()) if pk.list.item(i).data(Qt.UserRole)]
        again = accented()
    finally:
        _close(pk)  # (at once after drawing it again: what that left to do must not reach for the deleted list)
    check("restyle: in Find… only the Use that Enter presses has the accent (the first row's, the chosen row's once "
          "one is chosen, still after the list is drawn again); the others are plain buttons",
          len(rows) >= 3 and first == [rows[0]] and chosen == [rows[2]] and again == [rows[2]],
          (len(rows), rows[:3], first, chosen, again))


def _plain_at_rest(button):
    """Drawn without a fill or a border of its own while nothing points at it: its edge the colour of its inside."""
    img = button.grab().toImage()
    mid = img.height() // 2
    return img.pixelColor(0, mid) == img.pixelColor(3, mid)


def test_x_buttons_quiet(eq_screen, check):
    # (a row's ✕ was a plain button with a border, where every other ✕ of the app is quiet: no fill until pointed at)
    from PySide6.QtCore import Qt
    from ui.picker import Picker
    page = eq_screen.page
    seen = {}
    pk = _shown_picker(page, "")  # (a measurement in the app: its row's ✕, and each of its files' when shown)
    try:
        app_row = next(pk.list.item(i).data(Qt.UserRole) for i in range(pk.list.count())
                       if (pk.list.item(i).data(Qt.UserRole) or {}).get("device"))
        pk.toggle_expand(app_row["device"]["name"])
        pk.finish_list()
        qt.pump(200)
        xs = _bins(pk)
        seen["measurement"] = (len(xs), sum(b.property("quiet") == "true" and _plain_at_rest(b) for b in xs))
    finally:
        _close(pk)
    pk = Picker(page, "target")  # (a target in the app: its row's ✕)
    pk.show()
    try:
        pk.finish_list()
        qt.pump(200)
        xs = _bins(pk)
        seen["target"] = (len(xs), sum(b.property("quiet") == "true" and _plain_at_rest(b) for b in xs))
    finally:
        _close(pk)
    check("restyle: Find…'s delete button (a measurement, each of its files, a target: the bin, as a file goes for "
          "good) is quiet as every row's: no fill or border until pointed at", seen["measurement"][0] >= 2 and seen["target"][0] >= 1
          and all(n == quiet for n, quiet in seen.values()), seen)


def _bins(pk):
    """Find…'s delete buttons shown (the bin: a file of yours, deleted for good), by their tooltip."""
    from PySide6.QtWidgets import QPushButton
    return [b for b in pk.list.findChildren(QPushButton) if b.isVisible() and b.toolTip().startswith("Delete")]


def test_x_pointed_at_shows_its_fill(eq_screen, check):
    # (a row of the list is filled too while the mouse is on it, in the colour a quiet button takes when pointed at:
    # on a row, its ✕ pointed at showed nothing. Windows 11 lays a quiet button's fill, the text's colour at 6 %, over
    # the row's. In light and in a contrast theme, where most fills are the window's own colour)
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QHoverEvent, QMouseEvent
    from PySide6.QtWidgets import QApplication
    from ui import theme
    qapp, seen = eq_screen.qapp, {}

    def laid_over(under, ink, alpha=15):
        return [round(u * (1 - alpha / 255) + i * alpha / 255) for u, i in zip(under, ink)]
    try:
        for look in ("light", "contrast"):
            if look == "contrast":
                theme.apply(qapp, dark=False, contrast=theme.system_tokens())  # (Windows' own colours, as there)
                qt.pump(100)
            pk = _shown_picker(eq_screen.page, "")
            try:
                x = _bins(pk)[0]
                view = pk.list.viewport()
                # (the mouse put on it as Qt tells the list and the button on the screen: off-screen a moved mouse goes
                # to the first window under it, here Make an EQ's own, never to Find… over it)
                on = QPointF(x.mapTo(view, x.rect().center()))
                QApplication.sendEvent(view, QHoverEvent(QEvent.HoverEnter, on, on, QPointF(-1, -1)))
                x.setAttribute(Qt.WA_UnderMouse, True)
                mid = QPointF(x.rect().center())
                QApplication.sendEvent(x, QMouseEvent(QEvent.MouseMove, mid, QPointF(x.mapToGlobal(mid)), Qt.NoButton,
                                                      Qt.NoButton, Qt.NoModifier))
                qt.pump(100)
                img = view.grab().toImage()
                at = x.mapTo(view, QPoint(3, x.height() // 2))  # (inside it, beside its ✕)
                row, fill = img.pixelColor(QPoint(3, at.y())), img.pixelColor(at)  # (the row's margin, left of Show)
                ink = theme.tokens()["ink"]
                want = laid_over((row.red(), row.green(), row.blue()), [int(ink[k:k + 2], 16) for k in (1, 3, 5)])
                drawn = (fill.red(), fill.green(), fill.blue())
                seen[look] = {"its row": row.name(), "the ✕": fill.name(),
                              "row pointed at": theme.tokens()["subtle_hover"],
                              "as laid over": all(abs(a - b) <= 1 for a, b in zip(drawn, want))}
                x.setAttribute(Qt.WA_UnderMouse, False)
            finally:
                _close(pk)
    finally:
        qt.light(qapp)  # (the light look back, whatever happened: every later test runs light)
        qt.pump(50)
    check("restyle: Find…'s ✕, pointed at, shows a fill of its own over its row's (the text's colour at 6 %, as "
          "Windows 11 fills a quiet button; the row is filled too while the mouse is on it), in light and in a "
          "contrast theme",
          all(s["its row"] == s["row pointed at"] and s["the ✕"] != s["its row"] and s["as laid over"]
              for s in seen.values()) and len(seen) == 2, seen)


def test_download_mark_named(eq_screen, monkeypatch, check):
    # (the mark beside an online entry is Windows' download symbol, a character of its icon font: a screen reader read
    # that character, which is nothing. A few online entries stood in, so there are some whatever lists this PC has)
    from PySide6.QtGui import QAccessible
    from PySide6.QtWidgets import QLabel
    from ui.picker import Picker
    pk = Picker(eq_screen.page, "measurement")
    pk.show()
    try:
        qt.wait_for(lambda: not pk.db.get("loading") and not pk.lib.get("scanning"), 120)
        monkeypatch.setattr(pk, "db", {"items": [[f"fake{i}", "m", f"Fakeone {i}", "Sub", "Site", None, "", ""]
                                                 for i in range(3)], "loading": False})
        pk.q.setText("fakeone")
        pk._later.stop()
        pk.render()
        pk.finish_list()
        marks = [w for w in pk.list.findChildren(QLabel, "findMark") if w.isVisible()]
        read = sorted({QAccessible.queryAccessibleInterface(w).text(QAccessible.Name) for w in marks})
    finally:
        _close(pk)
    check("access: Find…'s download mark (beside an online entry) is read as “Downloads when used” by a screen reader",
          len(marks) == 3 and read == ["Downloads when used"], (len(marks), read))


def test_fits_a_small_screen(eq_screen, monkeypatch, check):
    # (opening 720 high, its bottom row (Sources…, Trace a graph image…, Close) was under the taskbar of a 1920 x 1080
    # laptop at 150 %. The screen is stood in: the room Qt says it has above the taskbar)
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QScreen
    from PySide6.QtWidgets import QPushButton
    from ui.picker import Picker
    bottom_row = ("Sources…", "Trace a graph image…", "Close")
    seen = {}
    for width, height in SMALL_SCREENS + ((1920, 1032),):  # (and a big screen: nothing changes there)
        monkeypatch.setattr(QScreen, "availableGeometry", lambda self, w=width, h=height: QRect(0, 0, w, h))
        pk = Picker(eq_screen.page, "measurement")
        try:
            opens = (pk.width(), pk.height())
            pk.show()
            qt.pump(200)
            row = [b for b in pk.findChildren(QPushButton) if b.text() in bottom_row]
            seen[height] = {"opens": opens, "smallest": pk.minimumHeight(),
                            "fits": opens[1] + TITLE_BAR <= height and pk.minimumHeight() + TITLE_BAR <= height
                            and opens[0] <= width,
                            "bottom row in sight": len(row) == 3
                            and all(b.isVisible() and pk.rect().contains(b.geometry()) for b in row)}
        finally:
            _close(pk)
    big = seen[1032]
    check("restyle: Find… opens within a laptop's screen at 150 % and 175 % (above the taskbar, its bottom row in "
          "sight); on a big screen it opens as before",
          all(seen[h]["fits"] and seen[h]["bottom row in sight"] for _w, h in SMALL_SCREENS)
          and big["opens"] == (900, 720) and big["smallest"] == 420 and big["bottom row in sight"], seen)


# ---------------------------------------------------------------- the recheck's (2026-10-23)
def _rows_in_sight(pk):
    """[(the row's width, where its last control ends)] of each of Find…'s rows in sight, in the list's own
    coordinates, and the list's width."""
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QWidget
    vp, out = pk.list.viewport(), []
    for i in range(pk.list.count()):
        w = pk.list.itemWidget(pk.list.item(i))
        if w is None or not w.isVisible():
            continue
        r = QRect(w.mapTo(vp, QPoint(0, 0)), w.size())
        if r.bottom() < 0 or r.top() >= vp.height():  # (scrolled out of sight)
            continue
        ends = [c.mapTo(vp, QPoint(c.width(), 0)).x() for c in w.findChildren(QWidget) if c.isVisible()]
        out.append((r.width(), max(ends, default=0)))
    return out, vp.width()


def test_rows_follow_a_narrower_window(eq_screen, check):
    # (the recheck, 2026-10-23: made narrower after it opened, e.g. dragged from 900 to its smallest, 680, Find… kept
    # every row as wide as before: each row's rig tag, Files, ✕ and Use ended at x 855 in a list 644 wide, out of sight
    # with no sideways scrolling, until the list was drawn again. Qt places the rows' widgets before it takes the
    # list's new width; narrower at the same height too, where a list laid out again on each resize still kept them)
    pk = _shown_picker(eq_screen.page, "")  # (900 x 720, as it opens on a big screen)
    seen = {}

    def look(name, tall=True):
        rows, wide = _rows_in_sight(pk)
        seen[name] = {"window": pk.size().toTuple(), "list": wide, "rows (width, last control ends)": rows[:3],
                      "ok": tall and len(rows) >= 3 and all(w == wide and end <= wide for w, end in rows)}
    try:
        for name, size in (("its smallest", (1, 1)), ("wider again", (1000, 700))):
            pk.resize(*size)
            qt.pump(300)
            look(name)
        # (narrower at the same height: the list exactly as tall, which a list laid out again on each resize misses.
        # Its status line may wrap onto one more line as the window narrows, making the list shorter: a step of 20 px
        # at a time until one keeps it as tall)
        for width in range(980, 800, -20):
            high = pk.list.viewport().height()
            pk.resize(width, 700)
            qt.pump(300)
            if pk.list.viewport().height() == high:
                break
        look("narrower, as tall", pk.list.viewport().height() == high)
    finally:
        _close(pk)
    bad = {name: s for name, s in seen.items() if not s["ok"]}
    check("restyle: Find… made narrower after it opens (900 to its smallest, or narrower at the same height) lays its "
          "rows out again, as wide as the list: every row's controls (its rig tag, Files, ✕, Use) stay in sight; and "
          "made wider again",
          seen["its smallest"]["window"] == (680, 420) and len(seen) == 3 and not bad, bad or seen)


def _in_the_guides_frame(page, kind, width):
    """What Find… for `kind` shows `width` px wide, inside a window as the Guide's frame holds it (tour.Api.window: its
    own smallest size taken away, the frame's room deciding; as tall as its parts need at that width, measured as it
    opens, while its lists are still loading), once its lists are in, searching for the sample's long name (the
    device's, the target's: in the app whatever the tests before put there)."""
    from PySide6.QtCore import QPoint, QRect, Qt
    from PySide6.QtWidgets import QAbstractButton, QDialog, QLabel, QWidget
    from ui.picker import Picker
    holder = QDialog(page)
    holder.resize(width + 100, 900)
    pk = Picker(page, kind)
    try:
        pk.setMinimumSize(0, 0)
        pk.setParent(holder, Qt.Widget)
        holder.ensurePolished()  # (in the theme's text, as the Guide measures it)
        tall = max(pk.minimumSizeHint().height(), pk.layout().minimumHeightForWidth(width))  # (as the frame asks)
        pk.setGeometry(0, 0, width, tall - 1)  # (and as it gives: a pixel less, at the app's own sizes)
        holder.show()
        pk.show()
        qt.wait_for(lambda: not pk.db.get("loading") and not pk.lib.get("scanning"), 120)
        pk.q.setText("wide bore" if kind == "measurement" else "diffuse field")
        pk._later.stop()
        pk.render()
        pk.finish_list()
        qt.pump(300)
        parts = [w for w in pk.findChildren(QWidget) if w.parentWidget() is pk and w.isVisible()]
        over = [(type(a).__name__, type(b).__name__) for i, a in enumerate(parts) for b in parts[i + 1:]
                if a.geometry().intersects(b.geometry())]
        cut = [b.text() for b in pk.findChildren(QAbstractButton) if b.parentWidget() is pk and b.isVisible()
               and (b.width() < b.sizeHint().width() or not pk.rect().contains(b.geometry()))]

        def drawn(w):
            """A box's choice or a row's name as drawn: whole, or ending in "…" (one that can't say: cut when it's
            longer than its room)."""
            if hasattr(w, "shown_text"):
                return w.shown_text()
            words = w.currentText() if hasattr(w, "currentText") else w.text()
            return words if w.fontMetrics().horizontalAdvance(words) <= w.width() - (36 if hasattr(w, "currentText")
                                                                                     else 0) else "(cut)"
        vp = pk.list.viewport()
        names = [(lab.text(), drawn(lab)) for lab in pk.list.findChildren(QLabel, "findRowName") if lab.isVisible()
                 and QRect(lab.mapTo(vp, QPoint(0, 0)), lab.size()).intersects(vp.rect())]
        rows, wide = _rows_in_sight(pk)
        st = pk.status
        return {"filters on lines": 2 if pk.f_sure.y() > pk.f_rig.geometry().bottom() else 1, "over": over,
                "cut buttons": cut,
                "boxes (words, drawn, width, smallest)": [(b.currentText(), drawn(b), b.width(),
                                                           b.minimumSizeHint().width())
                                                          for b in (pk.f_rig, pk.f_form, pk.f_site)],
                "names (text, drawn)": names[:3],
                "status (width, height, needs)": (st.width(), st.height(), st.heightForWidth(st.width())),
                "rows ok": bool(rows) and all(end <= wide for _w, end in rows)}
    finally:
        _close(holder)


def test_whole_in_the_guides_frame(eq_screen, check):
    # (the recheck, 2026-10-23: in the Guide's frame for it, 598 px wide at the app's own size and 523 at its smallest,
    # Find… was squeezed under its one line of filters: its boxes read "Any sour", "Any ri", "Any ty", "Made for any
    # ty", its tick "Downloadal"; the in-use row's name was cut mid-letter, "…(L800 IEI", and the status line stopped
    # mid-sentence)
    seen = {(kind, width): _in_the_guides_frame(eq_screen.page, kind, width)
            for kind in ("measurement", "target") for width in (598, 523)}

    def whole(s):
        boxes, names, (_w, high, needs) = (s["boxes (words, drawn, width, smallest)"], s["names (text, drawn)"],
                                           s["status (width, height, needs)"])
        return (not s["over"] and not s["cut buttons"] and s["rows ok"] and high >= needs
                and all(words == drawn and w >= low for words, drawn, w, low in boxes)
                and names and all(d == t or (d.endswith("…") and t.startswith(d[:-1])) for t, d in names))
    bad = {f"{kind} at {width}": s for (kind, width), s in seen.items()
           if not whole(s) or width == 523 and (s["filters on lines"] != 2  # (the narrowest: two lines, a name shortened)
                                                or all(d == t for t, d in s["names (text, drawn)"]))}
    check("restyle: Find…, for a measurement or a target, as narrow as the Guide's frame for it (598 px at the app's "
          "own size, 523 at its smallest): its filters on two lines when they don't fit on one, every box's choice "
          "and every button's and tick's words whole, nothing over another, a long name ending in “…”, the status "
          "line whole", len(seen) == 4 and not bad, bad)


def test_files_with_windows_chevron(eq_screen, check):
    # (the recheck, 2026-10-23: a measurement's Files was "Files ▾" / "Files ▴", typed triangles, where the app now
    # draws Windows 11's chevron, as on every button with a menu: the theme's own picture, in the same place)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMenu, QPushButton
    pk = _shown_picker(eq_screen.page, "")
    seen = {}
    try:
        app_row = next(pk.list.item(i).data(Qt.UserRole) for i in range(pk.list.count())
                       if (pk.list.item(i).data(Qt.UserRole) or {}).get("device"))

        def files_button():
            return next(b for b in pk.list.findChildren(QPushButton) if b.isVisible() and b.text().startswith("Files"))
        for state in ("hidden", "shown"):
            if state == "shown":
                pk.toggle_expand(app_row["device"]["name"])
                pk.finish_list()
                qt.pump(200)
            b = files_button()
            like = QPushButton(b.text(), b.parentWidget())  # (a button with a menu, beside it in its row)
            like.setMenu(QMenu(like))
            like.resize(b.size())
            like.show()
            qt.pump(50)
            same = b.grab().toImage() == like.grab().toImage()
            seen[state] = {"words": b.text(), "as wide": b.sizeHint() == like.sizeHint(), "drawn as it": same,
                           "picture": b.grab().toImage()}
            like.deleteLater()
    finally:
        _close(pk)
    pictures = [s.pop("picture") for s in seen.values()]
    check("restyle: Find…'s Files shows Windows 11's chevron after its word, as a button with a menu draws it (the "
          "theme's picture, its room, its place), down while the files are hidden and turned up while they're shown "
          "(no typed ▾ or ▴)",
          seen["hidden"] == {"words": "Files", "as wide": True, "drawn as it": True}
          and seen["shown"]["words"] == "Files" and seen["shown"]["as wide"] and not seen["shown"]["drawn as it"]
          and pictures[0] != pictures[1], seen)
