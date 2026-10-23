"""Every result of a run (AutoEQ Local's "All N results" window, results.js renderRuns/renderGrid, natively):
- the grid: the lowest error for each filter count (or the website's filter rows) and max Q, shaded when it sounds
  the same as the target (the audible pick's rule); a click shows that result (Best fit and the website sweep, with
  several results). Best fit's rows say how many filters the run tried ("6 filters", or "up to 7 filters" when a
  result there kept fewer: that cell says its own count, "· 6f", as the website sweep's cells do)
- the table: every result (error, filters, range, gain, Q max, max boost, pre-amp, and for the website's methods its
  filter rows), sorted by a click on a heading; a click on a row shows it
The shading is the theme's colour for "good" (its "pill"), taken as each cell is drawn: it follows light and dark
(in Windows' contrast themes: Windows' highlight).
Both in Windows 11's table look, as Profiles and Run several (2026-10-23): no grid lines, each heading over its
words at the left (the cells' room at the left: ui\\theme_sheet.py's eq_windows, #eqwGrid and #eqwResults); the
grid's rows told apart by a thin line under each (drawn in the theme's colour for lines, as each cell is: shading
there means "sounds the same"), the table's by their shade. The window opens wide enough for its whole grid when
the screen has room.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPalette
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHeaderView, QLabel, QStyledItemDelegate, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from ui import theme
from ui.theme_sheet import CARD

HEAD = [("Error (dB)", "rms"), ("Filters", "n_filters"), ("Rows", "rows"), ("Range", None), ("Gain", None),
        ("Q max", "q_max"), ("Max boost", "max_boost"), ("Pre-amp", "preamp")]
SAME = Qt.UserRole + 1  # (a grid cell's mark: sounds the same as the target)
LEFT = Qt.AlignLeft | Qt.AlignVCenter  # (Windows 11's tables: words at the left, under their heading)
NBSP = chr(0xA0)  # (a space that never ends a line: the words it joins stay together)


class _Shade(QStyledItemDelegate):
    """The grid's cells: one that sounds the same as the target shaded in the theme's "good" colour as it's drawn;
    in Windows' contrast themes, which have no such colour (it's the window's), in Windows' highlight and its text.
    Under each, a thin line in the theme's colour for lines (the grid has no grid lines: its rows told apart so)."""

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if index.data(SAME):
            t = theme.tokens()
            if t["pill"] != t["card"]:
                option.backgroundBrush = QBrush(QColor(t["pill"]))
            else:
                option.backgroundBrush = QBrush(QColor(t["sel"]))
                option.palette.setColor(QPalette.Text, QColor(t["on_sel"]))

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        r = option.rect
        painter.save()
        painter.setPen(QColor(theme.tokens()["line"]))
        painter.drawLine(r.left(), r.bottom(), r.right(), r.bottom())
        painter.restore()


def screen_room(widget):
    """The width of the screen the widget is on, without the taskbar (None when it isn't known)."""
    s = widget.screen()
    return s.availableGeometry().width() if s is not None else None


def _table_look(t):
    """Windows 11's table look: no grid lines, each heading at the left over its words."""
    t.setShowGrid(False)
    t.horizontalHeader().setDefaultAlignment(LEFT)
    t.horizontalHeader().setHighlightSections(False)
    t.verticalHeader().setDefaultAlignment(LEFT)


class _Num(QTableWidgetItem):
    """A cell that sorts by its number, not its text."""

    def __init__(self, text, value):
        super().__init__(text)
        self.value = value if value is not None else float("inf")
        self.setTextAlignment(LEFT)

    def __lt__(self, other):
        return self.value < getattr(other, "value", float("inf"))


class AllResults(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page = page
        run, _r = page.current()
        self.run = run
        self.setWindowTitle(f"All {len(run['results'])} results of run {run.get('n', 1)}")
        self.resize(940, 720)  # (the note under the grid on one line at Windows 11's text size)
        self.setMinimumSize(720, 560)  # (smaller, the grid's numbers were cut and the note ran over it)
        v = QVBoxLayout(self)
        v.setContentsMargins(CARD, CARD, CARD, CARD)  # (Windows 11's roomier edges, as a card's)
        lead = QLabel("Every result the run tried. Click one to show it.")
        theme.mark(lead, role="muted")
        v.addWidget(lead)
        self.grid_title, self.grid, self.grid_note = QLabel(), QTableWidget(), QLabel()
        theme.mark(self.grid_title, role="section")
        self.grid.setObjectName("eqwGrid")  # (its corner and its cells' room: ui\theme_sheet.py's eq_windows)
        self.grid.setItemDelegate(_Shade(self.grid))
        _table_look(self.grid)
        self._grid_height = None  # (its rows' height: render())
        self.grid.horizontalScrollBar().rangeChanged.connect(self._fit_grid)
        self.grid_note.setWordWrap(True)
        theme.mark(self.grid_note, role="muted")
        for w in (self.grid_title, self.grid, self.grid_note):
            v.addWidget(w)
        self.grid.cellClicked.connect(lambda i, j: self.grid.item(i, j) is not None
                                      and self.grid.item(i, j).data(Qt.UserRole) is not None
                                      and self.pick(self.grid.item(i, j).data(Qt.UserRole)))
        self.table = QTableWidget(0, len(HEAD))
        self.table.setObjectName("eqwResults")  # (its cells' room at the left: ui\theme_sheet.py's eq_windows)
        _table_look(self.table)
        self.table.setAlternatingRowColors(True)  # (rows told apart by their shade, as Run several's)
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
        self._wide_enough()

    def _wide_enough(self):
        """Opened wide enough for its whole grid when the screen has room (its rows' names and every column at its
        narrowest), at most 90 % of the screen's width: narrower, the grid scrolls sideways."""
        g = self.grid
        if g.isHidden():
            return
        self.ensurePolished()
        need = (g.verticalHeader().sizeHint().width() + g.columnCount() * g.horizontalHeader().minimumSectionSize()
                + 2 * g.frameWidth() + 2 * CARD + 4)
        room = screen_room(self) or need
        if need > self.width():  # (never narrower than it opens)
            self.resize(max(self.width(), min(need, int(room * 0.9))), self.height())

    def pick(self, rid):
        """A result shown on the result card (the window stays, its marks follow)."""
        self.page.show_result(rid)
        self.render()

    @staticmethod
    def tried(r):
        """How many filters Best fit tried for a result: those it added (its row in the grid, `rows`), with the
        shelves it added and your own filters (kept, or fine-tuned by a Retry); your own alone (row 0): yours. A
        result may keep fewer: filters too small to matter are left out."""
        added = r.get("rows") or 0
        shelves = bool(r.get("low_shelf")) + bool(r.get("high_shelf")) if added else 0
        return added + shelves + (r.get("yours") or 0)

    @classmethod
    def row_most(cls, rv, cells):
        """(how many filters Best fit tried in a grid row, whether every one of its cells' results kept them all).
        Never fewer than a result there has: the row's words never contradict a result card."""
        row = [c for (k, _q), c in cells.items() if k == rv]
        most = max([cls.tried(c) for c in row] + [c["n_filters"] for c in row])
        return most, all(c["n_filters"] == most for c in row)

    @classmethod
    def _row_words(cls, rv, cells, site):
        """A grid row's words. The website sweep's: its filter rows (what's typed into the site). Best fit's: how many
        filters the run tried there, "6 filters", or "up to 7 filters" when a result kept fewer (each such cell says
        its own count). Best fit's rows are the filters the run added, shelves and your own filters aside: they said
        "9 filters" for results of 10 with their shelf, and a Retry's only row "0 filters"; then each row said the
        counts its results had, and rows that all started at 6 looked alike: "6–7 filters" … "6–10 filters"
        (2026-10-23). Which results share a row is unchanged."""
        if site:
            return f"{rv} row{'' if rv == 1 else 's'}"
        most, every = cls.row_most(rv, cells)
        return f"{most} filter{'' if most == 1 else 's'}" if every else f"up to {most} filters"

    def _fit_grid(self, *_):
        """The grid as tall as its rows, and its scroll bar more while it scrolls sideways (a narrow window): the bar
        covered its last row."""
        if self._grid_height is not None:
            bar = self.grid.horizontalScrollBar()
            self.grid.setFixedHeight(self._grid_height + (bar.sizeHint().height() if bar.maximum() > 0 else 0))

    def render(self):
        run, page = self.run, self.page
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
            labels = [self._row_words(rv, cells, site) for rv in rows]
            g.setVerticalHeaderLabels(labels)
            g.setEditTriggers(QAbstractItemView.NoEditTriggers)
            g.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            most = {} if site else {rv: self.row_most(rv, cells)[0] for rv in rows}
            fewer = None  # (a cell whose result kept fewer filters than its row tried: its count, for the note)
            for i, rv in enumerate(rows):
                for j, q in enumerate(qs):
                    c = cells.get((rv, q))
                    if not c:
                        it = QTableWidgetItem("–")
                    else:
                        own = "" if site or c["n_filters"] == most[rv] else f" · {c['n_filters']}f"
                        if own and fewer is None:
                            fewer = c["n_filters"]
                        sub = (f"{round((c.get('freq_high') or 0) / 1000)}k · {c['n_filters']}f" if site
                               else f"max +{c['max_boost']:.1f}{own}")
                        it = QTableWidgetItem(f"{c['rms']:.2f}  ({sub})")
                        it.setData(Qt.UserRole, c["id"])
                        if c.get("ear") is not None and c["ear"] <= ear_db:
                            it.setData(SAME, True)  # (shaded as it's drawn: _Shade)
                        if c["id"] == page.sel:
                            f = QFont(it.font())
                            f.setBold(True)
                            it.setFont(f)
                    it.setTextAlignment(LEFT)
                    g.setItem(i, j, it)
            # (never narrower than its widest number, in bold as the one shown: in a narrow window the grid scrolls
            # sideways instead)
            g.ensurePolished()  # (the theme's text size)
            bold = QFont(g.font())
            bold.setBold(True)
            fm = QFontMetrics(bold)
            # (the cells' room at the left and right and Qt's margins round the words, 16 px, and 2 to spare)
            g.horizontalHeader().setMinimumSectionSize(18 + max(fm.horizontalAdvance(g.item(i, j).text())
                                                               for i in range(len(rows)) for j in range(len(qs))))
            self._grid_height = min(320, g.horizontalHeader().height() + sum(g.rowHeight(i) for i in range(len(rows))) + 4)
            self._fit_grid()
            self.grid_title.setText(f"Error by {'filter rows' if site else 'filter count'} and max Q (run {run.get('n', 1)})")
            up = next((lab for lab in labels if lab.startswith("up to ")), None)  # (a row where a result kept fewer)
            self.grid_note.setText(f"Lowest error (dB) per cell (the best: {best:.2f} dB); shaded = sounds the same "
                                   f"as the target (within {ear_db:g} dB, as the ear hears it). Click a cell to view it."
                                   + (f" “{up.replace(' ', NBSP)}”: the run tried that many; a cell whose result kept "
                                      f"fewer says how many (“{fewer}f”: filters too small to matter are left out)."
                                      if up and fewer else ""))
        # the table (its Rows column for the website's methods only: there it's the filter rows typed into the site;
        # Best fit's own count of the filters it added said "1" for a 2-filter result and nothing for a Retry's)
        t = self.table
        t.setColumnHidden(2, not str(run.get("mode", "")).startswith("site"))
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
