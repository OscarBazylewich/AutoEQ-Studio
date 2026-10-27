"""History on Make an EQ (ui\\history_window.py, ui\\eq_page.py, eq\\history.py): a saved EQ is kept once (copying it
again adds none); Show brings it back as a result of its own and loads its measurement as choosing it does; the
History window lists the EQs and ✕ removes one; a long History draws in batches and a typed search waits a moment; a
History file that can't be read is said and kept as .bad. Moved from eq_checks.py's ui_checks, review_checks and
review_low_checks: one page for the file (the eq_screen fixture), a quick run of its own saved as "UI check" (the
History entry the old checks used), then the checks in the old order. History starts empty here, as it did for the
old checks (the parts before them had emptied it). Then the window's look (Windows 11's, 2026-10-23) on a made-up
History: the rows' colours following the theme, the symbols, ✕, and the window at its smallest; a row's words at a
card's inset, and its buttons under its words when the window is narrow."""
import contextlib
import os
import time

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame

from helpers import eqpage, paths, qt
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
    was = next(e for e in page.history if e["key"] == kept[0]["key"])  # (as it is now: Copy kept it again since)
    hw.remove([kept[0]["key"]])
    gone = not any(e["key"] == kept[0]["key"] for e in page.history)
    # (2026-10-27, UI-RULES 20: Undo beside it, in History's own line; it puts the entry back as it was, its time too)
    line = hw.footer.line
    offered = (line.text.text().startswith("Removed"), line.undo_btn.isVisibleTo(hw))
    line.undo_btn.click()
    back = next((e for e in page.history if e["key"] == kept[0]["key"]), None)
    hw.remove([kept[0]["key"]])  # (taken out again: the checks after this one find it gone, as before)
    # was eq_checks.py:1592
    check("ui: the History window lists the EQs (this IEM only) and ✕ removes one, with Undo in its own line that "
          "puts it back as it was", rows >= 1 and gone and offered == (True, True) and back is not None
          and back["when"] == was["when"], (rows, gone, offered, back and back["when"], was["when"]))
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


def _near(a, b, by=8):
    """Two colours the same but for a little rounding (each of red, green and blue within `by`)."""
    a, b = QColor(a), QColor(b)
    return max(abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue())) <= by


@pytest.fixture
def made_up_history(eq_screen):
    """The History window shown on three made-up entries (History swapped for them, put back after)."""
    page = eq_screen.page
    real_history, now = page.history, time.time()
    page.history = [{"key": f"look{i}", "base": f"look{i}", "when": now - (3 - i) * 60, "device": "Look IEM",
                     "target": "Look target", "mode": "best_fit", "label": "Best fit", "saved": True,
                     "filters": [{"type": "PK", "freq": 1000, "gain": 1.0, "q": 1.0}], "n_filters": 1, "rms": 0.5,
                     "preamp": -1.0} for i in range(3)]
    hw = HistoryWindow(page, False)
    hw.show()
    qt.pump(200)
    yield hw
    qt.close(hw)
    page.history = real_history


def test_history_look_follows_the_theme(made_up_history, eq_screen, check):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QLabel, QPushButton
    from ui import theme
    hw, qapp = made_up_history, eq_screen.qapp

    def drawn():
        """The rows' first lines, the card's colour under a ✕ as drawn now, and the theme's colours."""
        body = hw.scroll.widget()
        heads = [lab.text() for lab in body.findChildren(QLabel) if "→" in lab.text()]
        x = next(b for b in body.findChildren(QPushButton) if b.text() == "✕")
        row = x.parentWidget()
        pm = row.grab()
        img = pm.toImage()
        p = x.mapTo(row, QPoint(3, x.height() // 2)) * pm.devicePixelRatio()
        t = theme.tokens()
        return {"heads": heads, "muted": t["muted"], "under ✕": (img.pixelColor(p).name(), t["card"])}
    buttons = hw.scroll.widget().findChildren(QPushButton)
    symbols = sorted({b.text() for b in buttons if not b.icon().isNull()})
    # (each row's Show, in the rows' order, newest first: in the accent or not, and its symbol)
    shows = [(b.property("primary") in (True, "true"), not b.icon().isNull()) for b in buttons if b.text() == "Show"]
    try:
        light = drawn()
        theme.apply(qapp, dark=True)
        qt.pump(200)
        dark = drawn()
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qt.pump(100)
    follows = all(len(d["heads"]) == 3 and all(d["muted"] in h for h in d["heads"]) for d in (light, dark)) \
        and light["muted"] != dark["muted"]
    check("history: a row's target is in the theme's quieter colour, redone when Windows switches light/dark (it kept "
          "the colour it was drawn in)", follows, {"light": light["heads"][:1], "dark": dark["heads"][:1]})
    # (2026-10-23, the restyle's checkers: Show has its symbol too now, and its accent on the first row only, below)
    check("history: Copy and Keep to compare show Windows 11's symbols beside their words (Show, the main one, its "
          "accent); ✕ is every row's quiet button: the row's card shows through it, light and dark",
          {"Copy", "Keep to compare"} <= set(symbols) and any(accent for accent, _symbol in shows)
          and all(_near(*d["under ✕"]) for d in (light, dark)), (symbols, shows, light["under ✕"], dark["under ✕"]))
    check("history: only the first row's Show (the newest) is in the accent, the others plain (every row's was: a "
          "column of accent buttons); every Show has Windows 11's symbol beside its words, as Copy and Keep to compare",
          len(shows) == 3 and [accent for accent, _symbol in shows] == [True, False, False]
          and all(symbol for _accent, symbol in shows) and symbols == ["Copy", "Keep to compare", "Show"], (shows, symbols))


def test_history_rows_whole_at_its_smallest(made_up_history, check):
    hw = made_up_history
    hw.resize(hw.minimumSize())  # (the smallest the window can be made)
    qt.pump(200)
    rows = [f for f in hw.scroll.widget().findChildren(QFrame) if type(f) is QFrame]
    view = hw.scroll.viewport()
    smallest = (hw.width(), hw.height(), view.width(), view.height(), [(r.width(), r.height()) for r in rows[:1]])
    check("history: at its smallest a whole row shows, its buttons in sight (no row could be read)",
          rows and all(r.width() <= view.width() for r in rows) and view.height() >= rows[0].height(), smallest)


def _rows_now(hw, first=3):
    """History's first rows as laid out now: for each, its first line's width and where its words start (from what's
    drawn, inside the row), and whether its Show button is under that line or beside it."""
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QLabel, QPushButton
    out = []
    for r in [f for f in hw.scroll.widget().findChildren(QFrame) if type(f) is QFrame][:first]:
        head = next(lab for lab in r.findChildren(QLabel) if "→" in lab.text())
        show = next(b for b in r.findChildren(QPushButton) if b.text() == "Show")
        h, s = QRect(head.mapTo(r, QPoint(0, 0)), head.size()), QRect(show.mapTo(r, QPoint(0, 0)), show.size())
        start = qt.words_start(qt.picture(r), h)
        out.append({"words wide": h.width(), "words start": start if start is None else start + h.left(),
                    "Show under the words": s.top() >= h.bottom(), "Show beside them": s.left() >= h.right(),
                    "row": (r.width(), r.height())})
    return out


def test_history_rows_words_at_a_cards_inset(made_up_history, check):
    # (2026-10-23, the restyle's recheck: each row, a card frame, kept Qt's own 9 px layout margin on top of its
    # padding, so its words started 5 px further in than a card's, 23 px in)
    from ui import theme_sheet
    rows = _rows_now(made_up_history)
    inset = theme_sheet.CARD + 1  # (inside its 1 px border)
    check("history: a row's words start at a card's inset inside its border, as the cards' content does, not 5 px "
          "further in", len(rows) == 3 and all(r["words start"] is not None and abs(r["words start"] - inset) <= 2
                                               for r in rows), {"inset": inset, "rows": rows})


def test_history_rows_buttons_under_the_words_when_narrow(made_up_history, check):
    # (2026-10-23, the restyle's recheck: at its smallest, 520 x 380, each row's words were squeezed into a column about
    # 100 px wide, up to 9 lines tall, beside Show, Copy, Listen and ✕; the Guide's frame shows it about as narrow)
    from ui.history_window import WORDS_ROOM
    hw = made_up_history
    seen = {}
    for name, size in (("its own size", (760, 640)), ("its smallest", None), ("its own size again", (760, 640))):
        if size:
            hw.resize(*size)
        else:
            hw.resize(hw.minimumSize())
        qt.pump(250)
        seen[name] = _rows_now(hw)
    beside = lambda rows: len(rows) == 3 and all(r["Show beside them"] and r["words wide"] >= WORDS_ROOM for r in rows)
    under = lambda rows: len(rows) == 3 and all(r["Show under the words"] and r["words wide"] >= WORDS_ROOM
                                                for r in rows)
    check("history: at its smallest a row's buttons go on a line under its words, which keep room to be read (they "
          "were squeezed into a column about 100 px wide, up to 9 lines tall); at its own size the buttons stay beside "
          "the words",
          beside(seen["its own size"]) and under(seen["its smallest"]) and beside(seen["its own size again"]), seen)


def test_history_deleted_straight_after_drawing_again(made_up_history, check):
    # (drawn again keeping its place in the list, as ✕ does, the window puts the place back once laid out: a moment
    # later, by a timer that had no owner, so it reached for the scroll bar of a window deleted meanwhile, an error
    # inside a Qt call-back (qt_error_check fails this test then). Find… had the same, 2026-10-23)
    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent
    hw = made_up_history
    hw.render(keep=True)
    hw.close()
    hw.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    gone = not shiboken6.isValid(hw)
    qt.pump(200)  # (the timer's moment)
    check("history: deleted straight after it's drawn again keeping its place (✕), nothing reaches for its list "
          "afterwards", gone, gone)


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
