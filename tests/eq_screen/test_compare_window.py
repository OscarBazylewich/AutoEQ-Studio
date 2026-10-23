"""Which measurement to use? (ui\\compare_window.py): the model's measurements ranked for the target, each with its
score and reasons, and Use putting the top one in use. Moved from eq_checks.py's ui_checks (lines 1473-1489), on a
page opened as the old checks opened it (the eq_screen fixture), offline: what's on this PC (the studio's samples)
and in the app is ranked, as the old checks did offline. The two are one chain, as there: one window, ranked, then
its top Use. Its Windows 11 look (the restyle, 2026-10-23): the chart in the graph's own colours, drawn again when
the theme changes, and at the window's smallest every part has its room."""
import pytest

from helpers import qt

NOTE = ("None of these was measured on the B&K 5128, the rig your target is made for, so every one will be off above "
        "about 2 kHz. A target made for the 711-type coupler would suit them better.")


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
