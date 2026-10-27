"""Two EQs side by side (the result card's Compare…): the result shown now (as edited), this session's runs (the best
for each filter count) and this IEM's History, any two of them: on one graph with the measurement and the target,
their numbers (the error in the scored range, filters, pre-amp, biggest boost and Q, how far apart they are) and their
filters in two tables. Nothing is changed; Show A / Show B put one back on the result card when it's a result of
this session.
The graph is drawn as Make an EQ's (in a card, the graph's own colours, never the accent): A in its blue (with the
EQ), B in its pink, the three told apart from the orange measurement by colour-blind eyes too (the dataviz checks;
the graph's green failed them beside the orange); its legend at the bottom left, on the card's colour, where it
hides the least. Redrawn when Windows switches light/dark or its accent colour.
The numbers and both filter tables in Windows 11's table look, as Profiles and Run several (2026-10-23): no grid
lines, each heading at the left over its words (the cells' room at the left: ui\\theme_sheet.py's eq_windows,
#eqwNumbers and #eqwCmpFilters), rows told apart by their shade.
Its size kept within the screen's room (window_parts.fit_to_screen): on a short screen (a laptop at 150 %) its parts
scroll as a page, its footer under them in sight: every window's (window_parts.Footer: its own message line, where
Show A / Show B say what they did, and Close). The lists are A to Z, as every list (the user's ask), the result shown
now pinned on top (it sorted last); Enter presses nothing (Qt made "Show A" Enter's).
"""
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ui import theme
from ui.history_window import follow_theme
from ui.search_combo import SearchCombo, natural_key
from ui.theme_sheet import CARD
from ui.window_parts import Footer, enter_presses, fit_to_screen

TYPES = {"PK": "Peak", "LSQ": "Low shelf", "HSQ": "High shelf", "LSC": "Low shelf", "HSC": "High shelf"}
TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]  # (as the EQ screen's graph)
LEFT = Qt.AlignLeft | Qt.AlignVCenter  # (Windows 11's tables: words at the left, under their heading)


def _table_look(t):
    """Windows 11's table look: no grid lines, each heading at the left over its words, rows told apart by their
    shade."""
    t.setShowGrid(False)
    t.setAlternatingRowColors(True)
    t.horizontalHeader().setDefaultAlignment(LEFT)
    t.horizontalHeader().setHighlightSections(False)


def _filters(fs):
    return [{"enabled": f.get("enabled", True) is not False, "type": f.get("type") or "PK", "freq": f["freq"],
             "gain": f["gain"], "q": f["q"]} for f in fs if f.get("freq") and f.get("q")]


def options(page):
    """[{"label", "filters", "run", "rid"}]: what can be compared, the result shown now first."""
    out = []
    run, r = page.current()
    if r:
        out.append({"label": "Shown now: " + page.run_label(run, r) + (" (edited)" if page.edited() else ""),
                    "filters": page.active(), "run": run, "rid": r["id"]})
    name = (page.curves or {}).get("name")
    for rn in reversed(page.session_runs):
        if rn.get("device") not in (None, name):
            continue
        if rn.get("mode") == "manual":  # (an EQ by hand: one EQ, its filters as you left them, no run's error)
            x = rn["results"][0]
            if rn is not run:
                on = [f for f in x["filters"] if f.get("enabled", True) is not False]
                out.append({"label": f"Run {rn.get('n', '?')} · by hand · {len(on)} filter{'' if len(on) == 1 else 's'}",
                            "filters": _filters(x["filters"]), "run": rn, "rid": x["id"]})
            continue
        by_n = {}
        for x in rn["results"]:
            had = by_n.get(x["n_filters"])
            if not had or x["id"] == rn["pick"] or (had["id"] != rn["pick"] and x["rms"] < had["rms"]):
                by_n[x["n_filters"]] = x
        for k, x in sorted(by_n.items()):
            if r and rn is run and x["id"] == r["id"] and not page.edited():
                continue
            out.append({"label": f"Run {rn.get('n', '?')} · {k} filters · {x['rms']:.2f} dB"
                                 + ("  ✓ picked for you" if x["id"] == rn["pick"] else ""),
                        "filters": _filters(x["filters"]), "run": rn, "rid": x["id"]})
    from ui.history_window import day_of, time_of
    for e in sorted((e for e in page.history if e.get("device") == name), key=lambda e: e["when"], reverse=True):
        out.append({"label": f"History · {day_of(e['when'])} {time_of(e['when'])} · {e.get('n_filters', '?')} filter{'' if e.get('n_filters') == 1 else 's'}",
                    "filters": _filters(e.get("filters") or []), "run": None, "rid": None})
    return out


class CompareResults(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.opts = options(page)
        self.setWindowTitle("Compare two EQs")
        # (narrower than 760, the tables' words were cut. Within the screen's room: its parts need about 764 px of
        # height, more than a laptop's screen at 150 % has above the taskbar (672), so they're on a page that scrolls
        # there, as Windows 11's Settings, with Close under it in sight; on a big screen it opens as before)
        fit_to_screen(self, (1000, 820), (760, 440))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(CARD, CARD, CARD, CARD)  # (Windows 11's roomier edges, as a card's)
        page_w = QWidget()
        v = QVBoxLayout(page_w)
        v.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # (only up and down: its parts fit its width)
        scroll.setWidget(page_w)
        outer.addWidget(scroll, 1)
        lead = QLabel("Any two of: the result shown now, this session's runs and this IEM's History, on your "
                      "measurement and target as they are now.")
        lead.setWordWrap(True)
        theme.mark(lead, role="muted")
        v.addWidget(lead)
        pick = QGridLayout()
        self.combos = []
        # (A to Z, as every list, the result shown now on top: UI-RULES 22; A and B start as the first two options
        # were: this EQ and the one beside it)
        first = self.opts[:2]
        shown = [o for o in self.opts if o["run"] is not None and o["label"].startswith("Shown now")]
        self.opts = shown + sorted((o for o in self.opts if o not in shown), key=lambda o: natural_key(o["label"]))
        for i, side in enumerate("AB"):
            pick.addWidget(QLabel(side), i, 0)
            c = SearchCombo()
            c.setAccessibleName(f"EQ {side}")
            for o in self.opts:
                c.addItem(o["label"])
            c.pinned = len(shown)  # (kept on top: search_combo's own sort would say so)
            c.setCurrentIndex(self.opts.index(first[min(i, len(first) - 1)]) if first else -1)
            c.currentIndexChanged.connect(self.render)
            pick.addWidget(c, i, 1)
            b = QPushButton(f"Show {side}")
            b.setToolTip("Put it on the result card")
            b.clicked.connect(lambda _=False, i=i: self.show_on_card(i))
            pick.addWidget(b, i, 2)
            self.combos.append(c)
        pick.setColumnStretch(1, 1)
        v.addLayout(pick)
        self.plot = pg.PlotWidget()
        self.plot.setLogMode(x=True, y=False)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.hideButtons()
        self.plot.getAxis("bottom").setTicks([[(np.log10(t), f"{t // 1000}k" if t >= 1000 else str(t)) for t in TICKS]])
        self.plot.getAxis("left").setLabel("dB")
        self.plot.setMinimumHeight(260)
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        # (bottom left: under the curves' bass, which IEMs and headphones keep well above the bottom of the graph)
        self.legend = self.plot.addLegend(offset=(10, -10))
        card = QFrame()  # (the graph in a card, as Make an EQ's)
        theme.mark(card, card=True)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(self.plot)
        v.addWidget(card, 2)
        self.numbers = QTableWidget(0, 3)
        self.numbers.setObjectName("eqwNumbers")  # (room at the left of its cells: ui\theme_sheet.py)
        self.numbers.setAccessibleName("Their numbers")
        self.numbers.setHorizontalHeaderLabels(["", "A", "B"])
        _table_look(self.numbers)
        self.numbers.verticalHeader().hide()
        self.numbers.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.numbers.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.numbers.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # (the names whole)
        v.addWidget(self.numbers)
        tables = QHBoxLayout()
        self.tables = []
        for side in "AB":
            t = QTableWidget(0, 4)
            t.setObjectName("eqwCmpFilters")  # (its cells' room at the left: ui\theme_sheet.py's eq_windows)
            t.setAccessibleName(f"Filters of {side}")
            t.setHorizontalHeaderLabels(["Type", "Hz", "Gain (dB)", "Q"])
            _table_look(t)
            t.verticalHeader().hide()
            t.setEditTriggers(QAbstractItemView.NoEditTriggers)
            t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tables.addWidget(t)
            self.tables.append(t)
        v.addLayout(tables, 2)
        self.footer = Footer(self)
        outer.addWidget(self.footer)
        enter_presses(self)
        self.render()
        follow_theme(self, lambda w: w.render())

    def chosen(self):
        return [self.opts[c.currentIndex()] for c in self.combos] if self.opts else []

    def numbers_of(self, filters):
        """(with the EQ, the EQ, the error in the scored range, the pre-amp, max boost, max Q) on the curves now."""
        from eq import engines
        page, c = self.page, self.page.curves
        f = np.asarray(c["f"])
        on = [x for x in filters if x.get("enabled", True)]
        g = engines.eq_gain(f, on, page.S["site"]["sample_rate"])
        band = page.S["scoring"]["band_hz"]
        inside = (f >= band[0]) & (f <= band[1])
        d = (np.asarray(c["meas"]) + g - np.asarray(c["target"]))[inside]
        return {"with": np.asarray(c["meas"]) + g, "eq": g, "rms": float(np.sqrt(np.mean(d * d))) if d.size else None,
                "preamp": -float(np.max(g)) if on else 0.0, "n": len(on),
                "boost": max([0] + [x["gain"] for x in on]), "q": max([0] + [x["q"] for x in on]), "inside": inside}

    def render(self):
        page = self.page
        self.plot.clear()
        if not self.opts or not page.curves:
            return
        col = theme.graph_colours()
        self.plot.setBackground(col["bg"])
        for ax in ("left", "bottom"):  # (as Make an EQ's graph)
            self.plot.getAxis(ax).setPen(pg.mkPen(col["axis"]))
            self.plot.getAxis(ax).setTextPen(pg.mkPen(col["axis"]))
        back = QColor(col["bg"])
        back.setAlpha(220)  # (the words readable, a curve under them still seen)
        self.legend.setBrush(back)
        self.legend.setPen(None)
        self.legend.setLabelTextColor(col["axis"])
        c = page.curves
        f = np.asarray(c["f"])
        self.plot.plot(f, np.asarray(c["meas"]), pen=pg.mkPen(QColor(col["meas"]), width=1.2, style=Qt.DotLine),
                       name="Measurement")
        self.plot.plot(f, np.asarray(c["target"]), pen=pg.mkPen(col["target"], width=2, style=Qt.DashLine), name="Target")
        nums = []
        # A in the graph's blue for "with the EQ", B over it in its pink (the EQ's on Make an EQ, free here: no EQ
        # curve is drawn), a little thinner, so where they're the same the blue shows at its edges
        for side, o, colour, width in zip("AB", self.chosen(), (col["with_eq"], col["eq"]), (2.6, 1.8)):
            n = self.numbers_of(o["filters"])
            nums.append(n)
            self.plot.plot(f, n["with"], pen=pg.mkPen(colour, width=width), name=f"{side}: with the EQ")
        self.plot.setXRange(np.log10(20), np.log10(20000), padding=0)
        apart = float(np.max(np.abs(nums[0]["with"] - nums[1]["with"])[nums[0]["inside"]])) if nums[0]["inside"].any() else 0
        rows = [("Error in the scored range (dB)", lambda n: f"{n['rms']:.2f}" if n["rms"] is not None else "–"),
                ("Filters", lambda n: str(n["n"])), ("Pre-amp (dB)", lambda n: page.preamp_text(n["preamp"])),
                ("Biggest boost (dB)", lambda n: f"+{n['boost']:.1f}"), ("Biggest Q", lambda n: f"{n['q']:g}")]
        self.numbers.setRowCount(len(rows) + 1)
        for i, (name, fn) in enumerate(rows):
            self.numbers.setItem(i, 0, QTableWidgetItem(name))
            for j, n in enumerate(nums):
                it = QTableWidgetItem(fn(n))
                it.setTextAlignment(LEFT)
                self.numbers.setItem(i, j + 1, it)
        self.numbers.setItem(len(rows), 0, QTableWidgetItem("How far apart, at most (scored range)"))
        it = QTableWidgetItem(f"{apart:.1f} dB")
        it.setTextAlignment(LEFT)
        self.numbers.setItem(len(rows), 1, it)
        self.numbers.setSpan(len(rows), 1, 1, 2)
        self.numbers.setFixedHeight(self.numbers.horizontalHeader().height()
                                    + sum(self.numbers.rowHeight(i) for i in range(len(rows) + 1)) + 4)
        for tbl, o in zip(self.tables, self.chosen()):
            fs = sorted(o["filters"], key=lambda x: x["freq"])
            tbl.setRowCount(len(fs))
            for i, x in enumerate(fs):
                for j, text in enumerate((TYPES.get(x["type"], x["type"]) + ("" if x.get("enabled", True) else " (off)"),
                                          f"{x['freq']:g}", f"{x['gain']:+.1f}", f"{x['q']:g}")):
                    it = QTableWidgetItem(text)
                    it.setTextAlignment(LEFT)
                    tbl.setItem(i, j, it)

    def show_on_card(self, i):
        """A result of this session back on the result card (a History entry: History's Show does that)."""
        o = self.chosen()[i]
        if o["label"].startswith("Shown now"):
            self.footer.say("That one is on the result card already.")
            return
        if o["run"] is None:
            self.footer.say("That one is from History: History's Show brings it back.")
            return
        if o["run"] is not self.page.run_result:
            self.page.run_result = o["run"]
            self.page.name_edit.clear()
        self.page.show_result(o["rid"])
        self.footer.say(f"Shown on the result card: {o['label']}")
