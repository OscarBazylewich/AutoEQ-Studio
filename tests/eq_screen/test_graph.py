"""Make an EQ's graph (ui\\eq_page.py): curves shown from Find… taken off it with Hide previews; Best fit's own
filters drawn as "With your filters"; the views (Relative to target, the Y range) and the values under the pointer,
kept in the settings. Moved from eq_checks.py's review_checks, review_low_checks and rest_checks: one page for the
file (the eq_screen fixture), each check on its own (any curves do: no run needed)."""
import numpy as np
from PySide6.QtCore import QPoint


def test_hide_shown_curves(eq_screen, check):
    page = eq_screen.page
    # (lines 1698-1701: the measurement shown as a curve from Find… would be, then Hide previews)
    page.add_preview("check", "Check", list(page.curves["meas"]),
                     {"src": "app", "kind": "target", "names": [page.S["files"]["active_target"]]})
    shown = page.clear_prev_btn.isVisibleTo(page)
    page.clear_previews()
    # was eq_checks.py:1702
    check("review: a curve shown from Find… can be hidden from the graph (Hide previews)",
          shown and not page.previews and not page.clear_prev_btn.isVisibleTo(page))


def test_own_filters_drawn(eq_screen, check):
    page = eq_screen.page
    # (lines 1834-1840: Best fit with a line of your own filters, drawn, then put back and drawn again)
    mode, mine = page.S["mode"], page.S["best_fit"].get("start_filters", "")
    page.S["mode"] = "best_fit"
    page.S["best_fit"]["start_filters"] = "Filter 1: ON PK Fc 300 Hz Gain 4 dB Q 1"
    page.draw()
    names = [it.name() for it in page.plot.listDataItems()]
    page.S["mode"], page.S["best_fit"]["start_filters"] = mode, mine
    page.draw()
    # was eq_checks.py:1841
    check("review: Best fit's own filters are drawn as “With your filters”", "With your filters" in names, names)


def test_graph_views_and_the_values_under_the_pointer(eq_screen, check):
    page = eq_screen.page
    # (lines 2005-2017: the views chosen, the plot resized and the pointer at its centre, the views put back and the
    # timer that would save them stopped)
    keep = dict(page.sw.s.get("graph") or {})
    page.set_graph_option(view="rel")
    tgt = dict(page._drawn["series"])["Target"]
    rel_ok = page._drawn["rel"] and float(np.max(np.abs(tgt))) < 1e-9 and page.plot.getAxis("left").labelText == "Δ dB"
    page.set_graph_option(y="30")
    lo, hi = page.plot.viewRange()[1]
    page.set_graph_option(view="abs", y="auto")
    page.plot.resize(800, 300)
    pl = page.plot
    page._hover(pl.mapToScene(QPoint(int(pl.width() * 0.5), int(pl.height() * 0.5))))
    read = page.hover_lab.text()
    page.set_graph_option(**keep)
    page._graph_timer.stop()
    # was eq_checks.py:2018
    check("graph views: Relative to target (the target at 0 dB, the axis Δ dB), a 30 dB Y range, the values under "
          "the pointer (Hz and each curve's dB); kept in the settings", rel_ok and abs((hi - lo) - 30) < 0.01
          and "Hz" in read and "Measurement" in read and (page.sw.s.get("graph") or {}).get("view") == keep.get("view", "abs"),
          (rel_ok, lo, hi, read))


def test_long_auto_message_keeps_the_page_width(eq_screen, monkeypatch, check):
    # (2026-11-10, a code review: a message from /api/auto went whole into the Search line, a label that does not
    # wrap, so a long one made the page wider)
    from PySide6.QtGui import QFontMetrics
    from helpers import qt
    page = eq_screen.page
    page.refresh_auto()
    qt.pump(100)
    before = (page.minimumSizeHint().width(), page.estimate.text(), page.estimate.toolTip())
    long = "The app cannot calculate the automatic settings: " + "the curves are not correct, " * 12 + "end."
    real_call = page.svc.call

    def call(path, body=None):
        return {"error": long} if path == "/api/auto" else real_call(path, body)
    with monkeypatch.context() as m:
        m.setattr(page.svc, "call", call)
        page.refresh_auto()
        qt.pump(100)
        fm = QFontMetrics(page.estimate.font())
        found = {"text": page.estimate.text(), "tooltip": page.estimate.toolTip(),
                 "label width": page.estimate.sizeHint().width(), "room": fm.averageCharWidth() * 61,
                 "page width": page.minimumSizeHint().width(), "page width before": before[0]}
    page.refresh_auto()  # (the real line back)
    qt.pump(100)
    found["back"] = (page.estimate.text(), page.estimate.toolTip()) == before[1:]
    check("make an EQ: a long message from the automatic settings ends in “…” on the Search line, its whole text in "
          "the tooltip, and the page does not get wider (the line does not wrap)",
          found["text"].endswith("…") and len(found["text"]) < len(long) and found["tooltip"] == long
          and found["label width"] <= found["room"] and found["page width"] <= found["page width before"]
          and found["back"], found)
