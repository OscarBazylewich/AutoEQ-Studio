"""Make an EQ's page as a whole (ui\\eq_page.py): the online database lists loaded as it opens, the dark theme and
back (the graph follows), and its keys: "/" opens Find…, a picture pasted opens the tracer with it. Moved from
eq_checks.py's review_checks and review_low_checks, on a page opened as the old checks opened it (the eq_screen
fixture), offline: the lists are the saved ones (tests\\fixtures\\db).

And its Windows 11 look (the restyle's stage 2, 2026-10-23): the page as wide as the window and no wider (at the
window's own size and its narrowest: a long title, long names, two runs this session, the values under the pointer),
Windows 11's symbols beside the main actions' words, what was just done in the window's message line with Undo (the
notice card that moved the page went, 2026-10-27), "yours" and the graph's legend in colours that read 4.5:1, a long
name ending in "…" and an empty note taking no room, the graph card's title in line with the cards' titles under it,
and a theme change while the page is still opening."""
import json
import os

from helpers import qt

# a name too long for any drop-down's room (squig.link's are often long)
LONG = ("Moondrop Blessing 3 (Dusk edition) (Sample 2) (Final E tips, shallow fit, left and right averaged) "
        "(IEC 711 coupler, GRAS RA0045)")
# the window's narrowest today (its top bar's width) and its own size: the page is as wide as the window
WIDTHS = (965, 1040)


def _scroll_area(page):
    from PySide6.QtWidgets import QScrollArea
    return next(a for a in page.findChildren(QScrollArea) if a.widget() and a.widget().isAncestorOf(page.run_btn))


def _near(a, b, by=10):
    """Two colours (#rrggbb) the same but for a little rounding."""
    if not a or not b:
        return False
    return all(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) <= by for i in (1, 3, 5))


def test_database_lists_loaded_on_opening(eq_screen, check):
    from eq import databases
    lists = os.path.exists(os.path.join(os.environ["AUTOEQSTUDIO_DATA"], "eq", "cache", "databases.json"))
    # (a refresh an earlier step started, e.g. by opening Find…, may still be going: it was the flaky part)
    eq_screen.wait_for(lambda: not databases.status()["loading"], 60)
    st = databases.status()
    # was eq_checks.py:1661
    check("review: the online database lists are loaded when Make an EQ opens (offline: the saved ones)",
          not st["loading"] and (st["count"] > 0 or not lists), (st["loading"], st["count"], lists))


def test_dark_theme_and_back(eq_screen, check):
    from ui import theme
    page, qapp = eq_screen.page, eq_screen.qapp
    try:
        theme.apply(qapp, dark=True)
        qapp.processEvents()
        dark = (page.plot.backgroundBrush().color().name(), theme.graph_colours()["bg"].lower())
        theme.apply(qapp, dark=False)
        qapp.processEvents()
        light = (page.plot.backgroundBrush().color().name(), theme.graph_colours()["bg"].lower())
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qapp.processEvents()
    # was eq_checks.py:1811
    check("review: the EQ screen switches to the dark theme and back (the graph follows)",
          dark[0] == dark[1] and light[0] == light[1] and dark[0] != light[0], (dark, light))


def test_slash_and_pasted_picture(eq_screen, check):
    from PySide6.QtGui import QColor, QImage, QShortcut
    from PySide6.QtWidgets import QApplication
    page = eq_screen.page
    keys = [sc.key().toString() for sc in page.findChildren(QShortcut)]
    # (the off-screen clipboard is this process's own: Windows' clipboard isn't touched)
    img = QImage(400, 300, QImage.Format_RGB888)
    img.fill(QColor("white"))
    QApplication.clipboard().setImage(img)
    page.paste_picture()
    pasted = page.tracer.isVisible() and page.tracer.t.has_image
    page.tracer.close()
    # was eq_checks.py:1899
    check("review: “/” opens Find…; a picture pasted on Make an EQ opens the tracer with it", "/" in keys and pasted,
          (keys, pasted))


def test_as_wide_as_the_window(eq_screen, check):
    # (at Windows 11's sizes the page was wider than the window at its own size, 1040, so every card was cut on the
    # right and the window scrolled sideways: the graph's title on one line and Runs this session as wide as its
    # longest run made it so, 2026-10-23. Here both made as long as they get, with the values under the pointer)
    page = eq_screen.page
    area = _scroll_area(page)
    size, kept = page.size(), (list(page.session_runs), page.run_result, page.sel)
    runs = [{"mode": "best_fit", "pick": 1, "best": 1, "n": n, "device": LONG, "target_name": LONG,
             "results": [{"id": 1, "filters": [{"type": "PK", "freq": 1000, "gain": -3, "q": 1}], "n_filters": 1,
                          "rms": 1.0, "max_boost": 0}]} for n in (1, 2)]
    found = {}
    try:
        page.session_runs, page.run_result = list(runs), runs[1]
        page.show_result(1)
        page.graph_title.set_pair(LONG, LONG)
        page.hover_lab.setText("1.28 kHz  ·  Target 61.2  ·  Measurement 62.8  ·  With the EQ 61.1 dB  ·  " * 3)
        for width in WIDTHS:
            page.resize(width, 900)
            qt.pump(300)
            found[width] = (area.widget().minimumSizeHint().width(), area.viewport().width(),
                            area.horizontalScrollBar().maximum(), page.runs_row.isVisibleTo(page))
    finally:
        page.session_runs, page.run_result, page.sel = kept
        if page.run_result is None:
            page.result_box.hide()
        else:
            page.show_result(page.sel if page.sel is not None else page.run_result["pick"])
        page.hover_lab.setText("")
        if page.curves:
            page.graph_title.set_pair(page.curves["name"], page.curves["target_name"])
        page.draw()
        page.resize(size)
    check("look: Make an EQ is as wide as the window, at its own size and its narrowest: no card wider, no sideways "
          "scrolling (a long title and names, two runs this session, the values under the pointer)",
          len(found) == len(WIDTHS) and all(m <= room and bar == 0 and runs_shown for m, room, bar, runs_shown
                                            in found.values()), found)


def test_symbols_beside_the_main_actions(eq_screen, check):
    from PySide6.QtWidgets import QPushButton
    page = eq_screen.page

    def named(root, text):
        return next((b for b in root.findChildren(QPushButton) if b.text() == text), None)
    want = {"Run": page.run_btn, "Find… by Target": named(page.target_box, "Find…"),
            "Add… by Target": named(page.target_box, "Add…"), "Find… by Measurement": named(page.measurement_box, "Find…"),
            "Add… by Measurement": named(page.measurement_box, "Add…"), "Trace image": named(page, "Trace image"),
            "Hide shown curves": page.clear_prev_btn, "History": named(page, "History"),
            "Save filters": named(page.result_box, "Save filters"),
            "Use on device": page.use_btn, "Copy": named(page.result_box, "Copy"),
            "Keep to compare": named(page.result_box, "Keep to compare"), "Add filter": named(page.result_box, "Add filter"),
            # (2026-10-23, the restyle's checkers: the only button opening a folder without Windows' folder symbol)
            "Open the Saved EQs folder": named(page.result_box, "Open the Saved EQs folder")}
    missing = sorted(k for k, b in want.items() if b is None or b.icon().isNull())
    old = sorted(b.text() for b in page.findChildren(QPushButton) if b.text().startswith(("✎", "📌", "+ Add filter")))
    check("look: Windows 11's symbols beside the main actions' words (Run, Find…, Add…, Trace image, History, Save "
          "filters, Use on device…), the words kept; no text symbol left in their words (✎, 📌, “+ Add filter”)",
          not missing and not old, (missing, old))


def test_done_with_undo_in_the_message_line(eq_screen, check):
    # (2026-10-27, UI-RULES 24: the notice card between Measurement and Make the EQ moved the page as it came and went;
    # what was done goes to the window's message line now, with Undo beside it)
    page = eq_screen.page
    put_back = []
    page.notify("Moved it.", lambda: put_back.append(True))
    offered = (eq_screen.said[-1], eq_screen.undo_offered())
    pressed = eq_screen.undo()
    page.notify("Saved it.")
    plain = (eq_screen.said[-1], eq_screen.undo_offered())
    check("eq page: what was just done goes to the window's message line, with Undo beside it when it can be undone "
          "(Undo puts it back), none when it can't; no notice card on the page any more (it made the page jump)",
          offered == ("Moved it.", True) and pressed and put_back == [True] and plain == ("Saved it.", False)
          and not hasattr(page, "notice"), (offered, pressed, put_back, plain))


def test_yours_and_the_legend_read_well(eq_screen, check):
    from ui import theme, theme_tokens
    page, qapp = eq_screen.page, eq_screen.qapp
    st = page.settings
    kept = (json.loads(json.dumps(page.S["auto"])), list(page.S["best_fit"]["filter_counts"]))
    found = {}
    try:
        st.auto_switched(True)
        page.refresh_auto()
        st.changed("best_fit.filter_counts", [1, 2, 3, 4, 5, 6])  # (a value of yours: “yours” in Why these values)
        for mode in ("dark", "light"):
            theme.apply(qapp, dark=mode == "dark")
            qapp.processEvents()
            t, g = theme.tokens(), theme.graph_colours()
            # (none set: pyqtgraph's own grey, #969696)
            grey = lambda c: c.name() if c is not None else "#969696"
            legend = grey(page.legend.opts.get("labelTextColor"))
            drawn = {grey(label.opts.get("color")) for _sample, label in page.legend.items}
            found[mode] = {"yours": (t["accent_text"] in st.why.text(), "yours" in st.why.text(),
                                     round(theme_tokens.contrast(t["accent_text"], t["card"]), 2)),
                           "legend": (legend, drawn == {legend}, round(theme_tokens.contrast(legend, g["bg"]), 2))}
    finally:
        qt.light(qapp)
        qapp.processEvents()
        page.S["auto"], page.S["best_fit"]["filter_counts"] = kept
        page.changed()
    check("look: “yours” in Why these values is the accent's text colour, as the “yours ↺” tags, and the graph's "
          "legend the axes' grey: each 4.5:1 on its card, light and dark",
          len(found) == 2 and all(f["yours"][0] and f["yours"][1] and f["yours"][2] >= 4.5 and f["legend"][1]
                                  and f["legend"][2] >= 4.5 for f in found.values()), found)


def test_long_names_and_empty_notes(eq_screen, check):
    page = eq_screen.page
    combo = page.measurement_combo
    i, size = combo.currentIndex(), page.size()
    was = combo.itemText(i)
    long = f"{LONG}  (12 files)"
    try:
        combo.setItemText(i, long)
        page.resize(WIDTHS[0], 900)
        qt.pump(200)
        shown = combo.shown_text()
    finally:
        combo.setItemText(i, was)
        page.resize(size)
    notes = {"target": (page.target_note.isVisibleTo(page), bool(page.target_note.text())),
             "graph": (page.graph_note.isVisibleTo(page), bool(page.graph_note.text())),
             "measurement": (page.measurement_note.isVisibleTo(page), bool(page.measurement_note.text()))}
    check("look: a name too long for its drop-down (Measurement's here) ends in “…”, never cut off part-way; a note "
          "shows when it has words and takes no room when it has none",
          shown.endswith("…") and long.startswith(shown[:-1].rstrip()) and len(shown) < len(long)
          and all(on == has for on, has in notes.values()) and notes["measurement"] == (True, True), (shown, notes))


def test_graph_card_title_lined_up_with_the_cards(eq_screen, check):
    # (2026-10-23, the restyle's recheck: the graph card, a card frame, kept Qt's own 9 px layout margin on top of its
    # padding, so its title started 5 px further in than the cards' titles under it: x 36 on the page against 32)
    from PySide6.QtCore import QPoint, QRect
    from ui import theme_sheet
    page = eq_screen.page
    card, title, box = page.graph_title.parentWidget(), page.graph_title, page.target_box
    at = QRect(title.mapTo(card, QPoint(0, 0)), title.size())
    head = QRect(3, 3, box.width() // 2, 34)  # (the Target card's title, inside its round corners)
    graph, target = qt.words_start(qt.picture(card), at), qt.words_start(qt.picture(box), head)
    found = {"graph card's title": graph is not None and graph + at.left(),
             "Target card's title": target is not None and target + head.left(), "inset": theme_sheet.CARD + 1,
             "cards' left edges": (card.mapTo(page, QPoint(0, 0)).x(), box.mapTo(page, QPoint(0, 0)).x())}
    check("look: the graph card's title starts where the cards' titles under it start (a card's inset inside its "
          "border), not 5 px further in",
          graph is not None and target is not None and abs(found["graph card's title"] - found["Target card's title"]) <= 1
          and abs(found["graph card's title"] - found["inset"]) <= 2 and found["cards' left edges"][0] == found[
              "cards' left edges"][1], found)


def test_theme_changed_while_opening(eq_screen, check):
    # (Windows switched light or dark while the EQ part was still loading: the page's colours, drawn again, reached
    # for the graph before it was there, "no attribute 'plot'", and the theme stopped there: the other screens' own
    # colours, the symbols, weren't drawn again. Found and fixed with the restyle, 2026-10-23)
    from ui.eq_page import EqPage
    qapp = eq_screen.qapp
    opening = EqPage(eq_screen.sw, lambda *a, **k: None)  # (made, not started: still "Opening the EQ part…")
    error = None
    try:
        qt.dark(qapp)
        qt.light(qapp)
    except Exception as e:  # (any: said by the check)
        error = repr(e)
    finally:
        qt.light(qapp)
        qt.close(opening)
    check("look: the theme changing while Make an EQ is still opening does nothing wrong (the other screens follow "
          "it too)", error is None, error)
