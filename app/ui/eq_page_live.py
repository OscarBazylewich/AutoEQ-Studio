"""Make an EQ's graph while you edit the filters (a part of EqPage, ui/eq_page.py; the user's ask, 2026-10-27: changing
a slider or a table's value far below the graph, its result couldn't be seen): a copy of the graph (the target, your
IEM, with the EQ) floating over the page while the graph itself is out of sight, out of the way of what you're
changing: at the top of what the page shows, or at its bottom when the control in use is up there.

It comes with an edit of the filters (the table, the sliders, Add filter, Sort) and follows each one (the page's draw,
and a handle held on the EQ graph: follow); it goes when the graph comes back into sight, when the filters scroll out
of it, or with its ✕. The editor's tick box "Show the graph while editing" (next to its tools) turns it off and on,
kept for the next start (the switcher's "live_graph"); its ✕ turns it off too. Drawn as the graph is (its colours,
log frequency axis) on a card with Windows 11's flyout border."""
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout

from ui import help_window, theme
from ui.eq_page_parts import TICKS, hz

LIVE_W, LIVE_H = 560, 250  # (its size: the graph's shape at a glance, over the result card's head)
EDGE = 12                  # (from the edges of what the page shows)


class LiveGraph(QFrame):
    """The floating card: its title and the result's numbers, ✕, and the graph's curves."""

    def __init__(self, parent, on_close):
        super().__init__(parent)
        self.setObjectName("liveGraph")  # (its card and border: theme_sheet's eq_page part)
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 6, 6, 8)
        v.setSpacing(2)
        head = QHBoxLayout()
        head.setSpacing(12)
        title = QLabel("The graph, as you edit")
        title.setObjectName("liveTitle")
        head.addWidget(title)
        self.numbers = QLabel("")
        theme.mark(self.numbers, role="muted")
        head.addWidget(self.numbers, 1)
        x = QToolButton()
        theme.mark(x, quiet=True)  # (as every ✕)
        x.setText("✕")
        x.setToolTip("Hide it (Show the graph while editing, by the filters, brings it back)")
        x.setAccessibleName("Hide the graph while editing")
        x.clicked.connect(on_close)
        head.addWidget(x)
        v.addLayout(head)
        self.plot = pg.PlotWidget()
        self.plot.setAccessibleName("The graph, as you edit")
        self.plot.setLogMode(x=True, y=False)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.hideButtons()
        self.plot.getAxis("bottom").setTicks([[(np.log10(t), hz(t).replace(" Hz", "").replace(" kHz", "k"))
                                                for t in TICKS]])
        self.plot.setXRange(np.log10(20), np.log10(20000), padding=0)
        self.c_target = self.plot.plot()
        self.c_meas = self.plot.plot()
        self.c_with = self.plot.plot()
        v.addWidget(self.plot, 1)
        self.recolour()
        self.hide()

    def recolour(self):
        """The graph's own colours (light, dark, a contrast theme): as the page's graph is drawn."""
        col = theme.graph_colours()
        self.plot.setBackground(col["bg"])
        for ax in ("left", "bottom"):
            self.plot.getAxis(ax).setPen(pg.mkPen(col["axis"]))
            self.plot.getAxis(ax).setTextPen(pg.mkPen(col["axis"]))
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.c_target.setPen(pg.mkPen(col["target"], width=2, style=Qt.DashLine))
        self.c_meas.setPen(pg.mkPen(col["meas"], width=1.6))
        self.c_with.setPen(pg.mkPen(col["with_eq"], width=2.5))

    def show_curves(self, f, target, meas, with_eq, yrange, numbers):
        self.shown = (f, target, meas, with_eq)  # (as drawn: what the checks compare with the page's graph)
        self.c_target.setData(f, target)
        self.c_meas.setData(f, meas)
        self.c_with.setData(f, with_eq)
        if yrange:
            self.plot.setYRange(*yrange, padding=0)
        self.numbers.setText(numbers)


class _Watch(QObject):
    """The page's scroll area's view: when it changes size, the floating graph's place again."""

    def __init__(self, page):
        super().__init__(page)
        self.page = page

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Resize:
            self.page.place_live_graph()
        return False


class EqLive:
    """The page's part for its floating graph (a plain class: EqPage joins it with its other parts)."""

    def live_graph_on(self):
        return self.sw is None or self.sw.s.get("live_graph", True) is not False

    def set_live_graph_on(self, on):
        """The tick box (or the card's ✕): the floating graph on or off, kept for the next start."""
        if self.sw is not None and self.sw.s.get("live_graph", True) != bool(on):
            self.sw.set("live_graph", bool(on), tell=False)
        if getattr(self, "live_check", None) is not None and self.live_check.isChecked() != bool(on):
            self.live_check.blockSignals(True)
            self.live_check.setChecked(bool(on))
            self.live_check.blockSignals(False)
        if not on:
            self.hide_live_graph()

    def _live(self):
        """The floating card, made the first time it's wanted (on the page's scroll area's view, over the page)."""
        lg = getattr(self, "live_graph", None)
        if lg is None:
            area = self.page_area
            lg = self.live_graph = LiveGraph(area.viewport(), lambda: self.set_live_graph_on(False))
            help_window.tag(lg, "#live-graph")
            area.verticalScrollBar().valueChanged.connect(lambda _v: self.place_live_graph())
            area.viewport().installEventFilter(_Watch(self))
        return lg

    def poke_live_graph(self):
        """An edit of the filters: the floating graph shown (if it's on and the graph is out of sight), placed and
        drawn."""
        if not self.live_graph_on() or not getattr(self, "_live_series", None) or getattr(self, "page_area", None) is None:
            return
        self._live_wanted = True
        self.place_live_graph()

    def hide_live_graph(self):
        self._live_wanted = False
        lg = getattr(self, "live_graph", None)
        if lg is not None:
            lg.hide()

    def _in_view(self, w, vp):
        """How much of w is in what the page shows (0 to 1 of its height)."""
        if w is None or not w.isVisible():
            return 0.0
        r = QRect(w.mapTo(vp, QPoint(0, 0)), w.size()).intersected(vp.rect())
        return r.height() / max(1, w.height()) if r.isValid() else 0.0

    def place_live_graph(self):
        """Where the floating graph goes now, or that it goes: none while the graph is in sight, the filters out of it,
        or no room; else at the top of what the page shows, right-aligned, or at its bottom when the control in use
        (or, with none, the filters) is under the top place."""
        lg = getattr(self, "live_graph", None)
        if not getattr(self, "_live_wanted", False):
            if lg is not None:
                lg.hide()
            return
        vp = self.page_area.viewport()
        r = vp.rect()
        w, h = min(LIVE_W, r.width() - 2 * EDGE), LIVE_H
        editor_seen = self._in_view(self.editor, vp)
        if self._in_view(self.plot, vp) >= 0.5 or editor_seen <= 0.0 or w < 320 or r.height() < h + 3 * EDGE:
            if lg is not None:
                lg.hide()
            if editor_seen <= 0.0:
                self._live_wanted = False  # (the filters out of sight: shown again with the next edit)
            return
        lg = self._live()
        rect_of = lambda wd: QRect(wd.mapTo(vp, QPoint(0, 0)), wd.size()).intersected(r)
        focus = QApplication.focusWidget()
        held = rect_of(focus) if focus is not None and self.editor.isAncestorOf(focus) else None
        x = r.right() - EDGE - w + 1
        places = [QRect(x, EDGE, w, h), QRect(x, r.bottom() - EDGE - h + 1, w, h)]
        # (clear of the filters if it can be, the top first; else clear of the control in use; else where it covers
        # the least of them: with the filters at the top of what's shown, it went over the sliders beside the one held)
        editor = rect_of(self.editor)
        clear = ([p for p in places if not p.intersects(editor)]
                 or [p for p in places if held is not None and not p.intersects(held)])
        pick = clear[0] if clear else min(places, key=lambda p: (p.intersected(editor).height(), places.index(p)))
        lg.setGeometry(pick)
        self.update_live_graph()
        lg.show()
        lg.raise_()

    def update_live_graph(self):
        """The floating graph's curves as the page's graph has them now (its scale too), and the result's numbers."""
        lg = getattr(self, "live_graph", None)
        s = getattr(self, "_live_series", None)
        if lg is None or not getattr(self, "_live_wanted", False):
            return
        if not s:  # (no EQ on the graph any more: nothing to show while editing)
            lg.hide()
            return
        yr = self.plot.getViewBox().viewRange()[1] if hasattr(self, "plot") else None
        st = self.stats() if self.current()[1] else None
        numbers = (f"Error {st['rms']:.2f} dB  ·  Pre-amp {self.preamp_text(st['preamp_raw'])} dB"
                   if st and st["rms"] is not None else "")
        lg.show_curves(s["f"], s["target"], s["meas"], s["with"], yr, numbers)
