"""Which measurement to use? (ui\\compare_window.py): the model's measurements ranked for the target, each with its
score and reasons, and Use putting the top one in use. Moved from eq_checks.py's ui_checks (lines 1473-1489), on a
page opened as the old checks opened it (the eq_screen fixture), offline: what's on this PC (the studio's samples)
and in the app is ranked, as the old checks did offline. The two are one chain, as there: one window, ranked, then
its top Use. Its Windows 11 look (the restyle, 2026-10-23): the chart in the graph's own colours, drawn again when
the theme changes; at the window's smallest every part has its room; the accent on its one main action; its warning
symbol read as "Warning"; and on a short screen (a laptop at 150 % or 175 %, stood in) it fits above the taskbar with
Close in sight. The recheck's (the same day): each measurement's and average's box starts its words where a card's
do."""
import pytest

from helpers import qt

NOTE = ("None of these was measured on the B&K 5128, the rig your target is made for, so every one will be off above "
        "about 2 kHz. A target made for the 711-type coupler would suit them better.")
# (a 1920 x 1080 laptop's room above the taskbar at 150 % and 175 %, as Qt gives it; and Windows 11's title bar there)
SMALL_SCREENS = ((1280, 672), (1097, 569))
TITLE_BAR = 32


def _read_as(widget):
    """What a screen reader reads for a widget (its accessible name)."""
    from PySide6.QtGui import QAccessible
    iface = QAccessible.queryAccessibleInterface(widget)
    return (iface.text(QAccessible.Name) if iface is not None else "") or ""


def _shown_with(page, monkeypatch, items=2):
    """Which measurement shown with a made-up answer (nothing compared or downloaded): `items` measurements on one rig
    (the B&K 5128), the target's, with a note to heed."""
    import numpy as np
    from ui import compare_window
    monkeypatch.setattr(compare_window.CompareWindow, "run", lambda self, auto=False: None)
    cw = compare_window.CompareWindow(page)
    f = np.geomspace(20, 20000, 60)
    made = [{"name": f"Model {k + 1}", "hash": f"h{k}", "rig": "5128", "rig_name": "B&K 5128", "sure": True,
             "source": f"Site {k + 1}", "site": f"Site {k + 1}", "n_files": 2, "channels": ["L", "R"], "dev": 0.5,
             "score": 80.0 - 9 * k, "reasons": [("+", "Same rig as your target"), ("−", "Stops at 16 kHz")],
             "vals": (np.sin(np.log(f)) * 3 + 1.5 * k).round(2).tolist(), "body": {"src": "db", "id": f"x{k}"}}
            for k in range(items)]
    cw.data = {"query": "Model", "items": made, "f": f.round(2).tolist(), "target_rig": "5128",
               "target_rig_name": "B&K 5128", "note": NOTE, "errors": [], "links": []}
    cw.render()
    cw.show()
    qt.pump(200)
    return cw


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


def test_says_when_nothing_could_be_loaded(eq_screen, monkeypatch, check):
    # (a bug the tests' reorganization found, fixed 2026-10-22: when the model's measurements were found but none could
    # be loaded, the window failed with "list index out of range"; and its line said nothing called it was found)
    from eq import compare
    from helpers import qt, studio
    from ui.compare_window import CompareWindow
    # (two measurements of the model found, neither loadable: compare's search and download stood in, as
    # tests\eq\test_compare.py's nothing_loads does)
    found = [{"src": "db", "id": f"x{i}", "name": "Truthear GATe", "source": f"Site {i}", "site": f"Site {i}"}
             for i in range(2)]
    monkeypatch.setattr(compare, "candidates", lambda query, links=None: [dict(c) for c in found])

    def no_internet(c):
        raise OSError("no internet in the tests")
    monkeypatch.setattr(compare, "_fetch", no_internet)
    cw = CompareWindow(eq_screen.page)
    try:
        cw.data = compare.compare(eq_screen.page.S, "Truthear GATe", studio.target_path())
        cw.render()
        status, note = cw.status.text(), cw.note.text()
        reasons = [w.text() for w in cw.scroll.widget().findChildren(type(cw.status)) if w.text().startswith("Couldn't")]
    finally:
        qt.close(cw)
    check("ui: Which measurement says none of the model's measurements could be loaded, and why (not that nothing was "
          "found)", "could be loaded" in status and "was found" not in status and "could be loaded" in note
          and reasons and "no internet in the tests" in reasons[0], (status, note, reasons))


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


# ---------------------------------------------------------------- the Windows 11 look (the restyle, 2026-10-23)
def test_chart_in_the_graphs_colours(eq_screen, monkeypatch, check):
    # (it drew the one on top in c1, the accent since stage 1 (Windows' own colour, any colour), and an average in c2,
    # the graph's pink EQ since stage 1, under a legend saying "Blue" and "Green dashes"; a theme change left it as
    # it was)
    from PySide6.QtCore import Qt
    from ui import theme
    qapp = eq_screen.qapp
    cw = _shown_with(eq_screen.page, monkeypatch)

    def seen():
        """The chart's background, its curves' colours (in drawing order: the one on top last) and the dashed ones'."""
        items = cw.chart.listDataItems()
        return (cw.chart.backgroundBrush().color().name(), [i.opts["pen"].color().name() for i in items],
                [i.opts["pen"].color().name() for i in items if i.opts["pen"].style() == Qt.DashLine])
    try:
        cw._avg_hover("5128")  # (the mouse over the average's box: its dashes drawn)
        light, t_light, g_light = seen(), theme.tokens(), theme.graph_colours()
        theme.apply(qapp, dark=True)
        qapp.processEvents()
        dark, t_dark, g_dark = seen(), theme.tokens(), theme.graph_colours()
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qapp.processEvents()
        qt.close(cw)

    def right(s, t, g):
        bg, curves, dashed = s
        return (bg == g["bg"].lower() and curves[:-1] and curves[-2] == g["with_eq"].lower()
                and dashed == [t["c4"].lower()] and t["accent"].lower() not in curves)
    check("restyle: Which measurement's chart takes the graph's own colours (blue the one on top, green dashes an "
          "average, never the accent) and is drawn again when the theme changes",
          right(light, t_light, g_light) and right(dark, t_dark, g_dark) and light[0] != dark[0],
          (light, dark, t_light["accent"], t_dark["accent"]))


def test_smallest_size_fits(eq_screen, monkeypatch, check):
    # (Qt's own smallest size counts each wrapped line of text once: at it, the chart's card was squeezed and its
    # scale cut off, and the model's box was a few letters wide beside a long target name)
    from PySide6.QtWidgets import QWidget
    cw = _shown_with(eq_screen.page, monkeypatch)
    try:
        cw.resize(1, 1)  # (to its smallest)
        qt.pump(300)
        size = (cw.width(), cw.height())
        parts = [w for w in cw.findChildren(QWidget) if w.parentWidget() is cw and w.isVisible()]
        name = lambda w: f"{type(w).__name__} “{(w.text() if hasattr(w, 'text') else w.objectName())[:20]}”"
        over = [(name(a), name(b)) for i, a in enumerate(parts) for b in parts[i + 1:]
                if a.geometry().intersects(b.geometry())]
        card = cw.chart.parentWidget()
        chart = (cw.chart.height(), cw.chart.minimumHeight(), card.rect().contains(cw.chart.geometry()))
        box = (cw.q.width(), cw.q.sizeHint().width())
    finally:
        qt.close(cw)
    check("restyle: Which measurement at its smallest gives every part its room (the chart whole with its scale, the "
          "model's box its own width, nothing over another)",
          parts and not over and chart[0] >= chart[1] and chart[2] and box[0] >= box[1], (size, chart, box, over[:3]))


def test_one_main_action(eq_screen, monkeypatch, check):
    # (Compare, the first Use and every "Average N and use" had the accent: two to four at once. Windows 11 keeps it
    # for the one main action)
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton
    from ui import compare_window
    seen, ran = {}, []
    for n in (2, 1):  # (two on the target's rig: an average offered; one: none)
        cw = _shown_with(eq_screen.page, monkeypatch, items=n)
        try:
            seen[n] = [b.text() for b in cw.findChildren(QPushButton) if b.property("primary") in (True, "true")]
            if n == 1:  # (Enter in the model's box compares, the button plain)
                monkeypatch.setattr(compare_window.CompareWindow, "run", lambda self, auto=False: ran.append(auto))
                cw.q.setFocus()
                QTest.keyClick(cw.q, Qt.Key_Return)
                seen["Compare"] = cw.go.property("primary") in (True, "true")
        finally:
            qt.close(cw)
    check("restyle: Which measurement has the accent on one button only, its main action: the average's when one is "
          "offered, else the first measurement's Use (Compare plain: Enter in the model's box runs it)",
          seen == {2: ["Average 2 and use"], 1: ["Use"], "Compare": False} and ran == [False], (seen, ran))


def test_warning_symbol_named(eq_screen, monkeypatch, check):
    # (a label holding Windows' warning symbol, a character of its icon font: a screen reader read that character,
    # which is nothing)
    from PySide6.QtWidgets import QLabel
    cw = _shown_with(eq_screen.page, monkeypatch)
    try:
        symbols = [w for w in cw.findChildren(QLabel) if w.isVisible() and len(w.text()) == 1
                   and 0xE000 <= ord(w.text()) <= 0xF8FF]  # (the icon font's characters)
        read = [_read_as(w) for w in symbols]
    finally:
        qt.close(cw)
    check("access: Which measurement's warning symbol (beside a note to heed) is read as “Warning” by a screen reader",
          read == ["Warning"], read)


def test_fits_a_small_screen(eq_screen, monkeypatch, check):
    # (at 700 x 660 at its smallest, and opening 860 high, its Close was under the taskbar of a 1920 x 1080 laptop at
    # 150 %, out of reach. The screen is stood in: the room Qt says it has above the taskbar)
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QScreen
    from PySide6.QtWidgets import QPushButton, QWidget
    seen = {}
    for width, height in SMALL_SCREENS + ((1920, 1032),):  # (and a big screen: nothing changes there)
        monkeypatch.setattr(QScreen, "availableGeometry", lambda self, w=width, h=height: QRect(0, 0, w, h))
        cw = _shown_with(eq_screen.page, monkeypatch)  # (with a note to heed and an average: its fullest)
        try:
            opens = (cw.width(), cw.height())
            cw.resize(1, 1)  # (to its smallest)
            qt.pump(300)
            parts = [w for w in cw.findChildren(QWidget) if w.parentWidget() is cw and w.isVisible()]
            over = [(type(a).__name__, type(b).__name__) for i, a in enumerate(parts) for b in parts[i + 1:]
                    if a.geometry().intersects(b.geometry())]
            close = next(b for b in cw.findChildren(QPushButton) if b.text() == "Close")
            card = cw.chart.parentWidget()
            seen[height] = {
                "opens": opens, "smallest": (cw.width(), cw.height()),
                "fits": opens[1] + TITLE_BAR <= height and cw.height() + TITLE_BAR <= height
                and max(opens[0], cw.width()) <= width,
                "Close in sight": close.isVisible() and cw.rect().contains(close.geometry()), "over": over,
                "chart": (cw.chart.height(), cw.chart.minimumHeight(), card.rect().contains(cw.chart.geometry())),
                "list": (cw.scroll.height(), cw.scroll.minimumHeight())}
        finally:
            qt.close(cw)
    small, big = [seen[h] for _w, h in SMALL_SCREENS], seen[1032]
    check("restyle: Which measurement fits a laptop's screen at 150 % and 175 % (its size and its smallest above the "
          "taskbar): the chart and the measurements' list give up height, nothing over another, Close in sight; on a "
          "big screen it opens and shrinks as before",
          all(s["fits"] and s["Close in sight"] and not s["over"] and s["chart"][0] >= s["chart"][1] and s["chart"][2]
              and s["list"][0] >= s["list"][1] for s in small)
          and big["opens"] == (940, 860) and big["smallest"] == (700, 660) and big["chart"][1:] == (150, True)
          and big["list"][1] == 120 and big["Close in sight"] and not big["over"], seen)


def test_boxes_words_start_as_a_cards(eq_screen, monkeypatch, check):
    # (the recheck, 2026-10-23: each measurement's and each average's box is a card frame, whose padding leaves 4 px for
    # its layout's own margin; they kept Qt's 9, so their words started 22 px inside, 5 px further in than in Make an
    # EQ's cards)
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QFrame, QGroupBox, QWidget
    page = eq_screen.page
    card = next(b for b in page.findChildren(QGroupBox) if b.isVisible() and b.layout() is not None)

    def inset(box):
        """How far inside the box (from its left and its top) its first words or controls start."""
        kids = [w for w in box.findChildren(QWidget) if w.isVisible() and w.parentWidget() is box]
        at = [w.mapTo(box, QPoint(0, 0)) for w in kids]
        return min(p.x() for p in at), min(p.y() for p in at)
    cw = _shown_with(page, monkeypatch)  # (two on the target's rig: an average's box and two measurements')
    try:
        boxes = {f"{w.objectName()} {n}": inset(w) for n, w in enumerate(
            b for b in cw.scroll.widget().findChildren(QFrame) if b.objectName() in ("whichRow", "whichAverage"))}
        cards = inset(card)[0]
    finally:
        qt.close(cw)
    check("restyle: Which measurement's boxes (each measurement, each average) start their words where a card's do: as "
          "far inside as Make an EQ's cards, at the left and the top",
          len(boxes) == 3 and all(v == (cards, cards) for v in boxes.values()), (cards, boxes))


def test_no_average_of_copies(eq_screen, monkeypatch, check):
    # (the recheck, 2026-10-23: once your own files' rigs were known, the sample's measurement found twice on this PC,
    # the same files in two folders, offered "Average the 2 measurements on the B&K 5128" with only "Tick at least 2":
    # the second left out as the same data. Copies of one measurement: nothing to average, so no box)
    from PySide6.QtWidgets import QFrame, QPushButton
    seen = {}
    for name, step in (("copies", 0.0), ("two different ones", 1.5)):
        cw = _shown_with(eq_screen.page, monkeypatch)
        try:
            for k, c in enumerate(cw.data["items"]):  # (the second the first's curve again, or 1.5 dB from it)
                c["vals"] = [v + step * k for v in cw.data["items"][0]["vals"]]
            cw.picked.clear()
            cw.render()
            qt.pump(100)
            seen[name] = {"averages": len([b for b in cw.scroll.widget().findChildren(QFrame)
                                           if b.objectName() == "whichAverage"]),
                          "accent on": [b.text() for b in cw.findChildren(QPushButton)
                                        if b.property("primary") in (True, "true")]}
        finally:
            qt.close(cw)
    check("restyle: Which measurement offers no average of copies of one measurement (the same files found twice on "
          "this PC: nothing to average), the first measurement's Use its main action then; two different ones on the "
          "rig are still offered their average",
          seen == {"copies": {"averages": 0, "accent on": ["Use"]},
                   "two different ones": {"averages": 1, "accent on": ["Average 2 and use"]}}, seen)
