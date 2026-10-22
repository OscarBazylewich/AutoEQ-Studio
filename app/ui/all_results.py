"""Every result of a run (AutoEQ Local's "All N results" window, results.js renderRuns/renderGrid, natively):
- the grid: the lowest error for each filter count (or the website's filter rows) and max Q, shaded when it sounds
  the same as the target (the audible pick's rule); a click shows that result (Best fit and the website sweep, with
  several results)
- the table: every result (error, filters, rows, range, gain, Q max, max boost, pre-amp), sorted by a click on a
  heading; a click on a row shows it
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

from ui import theme

HEAD = [("Error (dB)", "rms"), ("Filters", "n_filters"), ("Rows", "rows"), ("Range", None), ("Gain", None),
        ("Q max", "q_max"), ("Max boost", "max_boost"), ("Pre-amp", "preamp")]


class _Num(QTableWidgetItem):
    """A cell that sorts by its number, not its text."""

    def __init__(self, text, value):
        super().__init__(text)
        self.value = value if value is not None else float("inf")
        self.setTextAlignment(Qt.AlignCenter)

    def __lt__(self, other):
        return self.value < getattr(other, "value", float("inf"))


class AllResults(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page = page
        run, _r = page.current()
        self.run = run
        self.setWindowTitle(f"All {len(run['results'])} results of run {run.get('n', 1)}")
        self.resize(900, 720)
        v = QVBoxLayout(self)
        lead = QLabel("Every result the run tried. Click one to show it.")
        theme.mark(lead, role="muted")
        v.addWidget(lead)
        self.grid_title, self.grid, self.grid_note = QLabel(), QTableWidget(), QLabel()
        self.grid_title.setStyleSheet("font-weight: 600;")
        self.grid_note.setWordWrap(True)
        theme.mark(self.grid_note, role="muted")
        for w in (self.grid_title, self.grid, self.grid_note):
            v.addWidget(w)
        self.grid.cellClicked.connect(lambda i, j: self.grid.item(i, j) is not None
                                      and self.grid.item(i, j).data(Qt.UserRole) is not None
                                      and self.pick(self.grid.item(i, j).data(Qt.UserRole)))
        self.table = QTableWidget(0, len(HEAD))
        self.table.setAccessibleName("Every result")
        self.grid.setAccessibleName("Error by filter count and max Q")
        self.table.setHorizontalHeaderLabels([h for h, _k in HEAD])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(lambda row, _c: self.pick(self.table.item(row, 0).data(Qt.UserRole)))
        v.addWidget(self.table, 1)
        self.render()

    def pick(self, rid):
        """A result shown on the result card (the window stays, its marks follow)."""
        self.page.show_result(rid)
        self.render()

    def render(self):
        run, page = self.run, self.page
        tok = theme.tokens()
        # the grid
        rs = run["results"]
        show = run["mode"] in ("site_sweep", "best_fit") and len(rs) > 1
        for w in (self.grid_title, self.grid, self.grid_note):
            w.setVisible(show)
        if show:
            site = run["mode"] == "site_sweep"
            cells = {}
            for r in rs:
                k = (r.get("rows"), r.get("q_max"))
                if k not in cells or r["rms"] < cells[k]["rms"]:
                    cells[k] = r
            rows = sorted({r.get("rows") for r in rs}, key=lambda x: (x is None, x))
            qs = sorted({r.get("q_max") for r in rs}, key=lambda x: (x is None, x))
            best = next(r for r in rs if r["id"] == run["best"])["rms"]
            sc = run.get("settings", {}).get("scoring", {})
            # (shaded = sounds the same as the target: what the audible pick chose among)
            ear_db = run.get("ear_db") or sc.get("ear_db", 0.25)
            g = self.grid
            g.clear()
            g.setRowCount(len(rows))
            g.setColumnCount(len(qs))
            g.setHorizontalHeaderLabels([f"Q max {q}" for q in qs])
            g.setVerticalHeaderLabels([f"{rv} {'rows' if site else 'filters'}" for rv in rows])
            g.setEditTriggers(QAbstractItemView.NoEditTriggers)
            g.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            for i, rv in enumerate(rows):
                for j, q in enumerate(qs):
                    c = cells.get((rv, q))
                    if not c:
                        it = QTableWidgetItem("–")
                    else:
                        sub = (f"{round((c.get('freq_high') or 0) / 1000)}k · {c['n_filters']}f" if site
                               else f"max +{c['max_boost']:.1f}")
                        it = QTableWidgetItem(f"{c['rms']:.2f}  ({sub})")
                        it.setData(Qt.UserRole, c["id"])
                        if c.get("ear") is not None and c["ear"] <= ear_db:
                            it.setBackground(QBrush(QColor(tok["sel"])))
                        if c["id"] == page.sel:
                            f = QFont(it.font())
                            f.setBold(True)
                            it.setFont(f)
                    it.setTextAlignment(Qt.AlignCenter)
                    g.setItem(i, j, it)
            g.setFixedHeight(min(320, g.horizontalHeader().height() + sum(g.rowHeight(i) for i in range(len(rows))) + 4))
            self.grid_title.setText(f"Error by {'filter rows' if site else 'filter count'} and max Q (run {run.get('n', 1)})")
            self.grid_note.setText(f"Lowest error (dB) per cell (the best: {best:.2f} dB); shaded = sounds the same "
                                   f"as the target (within {ear_db:g} dB, as the ear hears it). Click a cell to view it.")
        # the table
        t = self.table
        t.setSortingEnabled(False)
        t.setRowCount(0)
        for r in sorted(rs, key=lambda x: x["rms"])[:500]:
            i = t.rowCount()
            t.insertRow(i)
            err = _Num(f"{r['rms']:.3f}" + ("  pick" if r["id"] == run["pick"] else ""), r["rms"])
            err.setData(Qt.UserRole, r["id"])
            pre = r.get("preamp")
            cells = [err, _Num(str(r["n_filters"]), r["n_filters"]), _Num(str(r.get("rows") or ""), r.get("rows")),
                     _Num(f"{r.get('freq_low', '')}–{r.get('freq_high', '')}" if r.get("freq_low") is not None else "", None),
                     _Num(f"{r.get('gain_min', '')} to {r.get('gain_max', '')}" if r.get("gain_min") is not None else "", None),
                     _Num(f"{r.get('q_max', '')}", r.get("q_max")), _Num(f"+{r['max_boost']:.1f}", r["max_boost"]),
                     _Num(page.preamp_text(pre) if pre is not None else "", pre)]
            for c, it in enumerate(cells):
                if r["id"] == page.sel:
                    f = QFont(it.font())
                    f.setBold(True)
                    it.setFont(f)
                t.setItem(i, c, it)
        t.setSortingEnabled(True)
