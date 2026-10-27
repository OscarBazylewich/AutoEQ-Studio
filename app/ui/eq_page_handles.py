"""Make an EQ's EQ graph (under the graph) as a place to edit the filters (a part of EqPage, ui/eq_page.py,
2026-10-26): a handle for each filter of the EQ shown, on its own curve at its frequency (a peak's top, a shelf's
middle: half its gain), with its number (over it; under it at the graph's top). Drag one: left and right its
frequency, up and down its gain; the mouse wheel over it: its Q; right-click it: its type, on or off, Remove.
Double-click the graph where there's no handle: a new peak there (with no EQ shown, it starts one by hand). While a
handle is held only what follows it changes (the EQ's curves, the numbers, the table's values, Listen's sound) and the
graph's scale stays as it was until it's let go: a scale that moved under the pointer made the handle run away from
it. A full draw asked for meanwhile (curves loaded in the background, a timer) waits for the let-go too: it would take
the handle away from under the pointer. An EQ being tried on a device (Try for 5 minutes on) plays each change there
too, in every app. The table and the sliders stay the way in by keyboard.
EqHandles is a plain class (no __init__, no signals); EqPage (ui/eq_page.py) joins it with the other parts.
"""
import math

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QPoint, QPointF, Qt, QTimer
from PySide6.QtWidgets import QMenu

from ui import theme

LIGHT_MS = 30     # (the curves, numbers and sound follow a held handle at most this often)
SETTLE_MS = 400   # (after the mouse wheel stops: the whole page again, its scales fitted)
TRY_MS = 200      # (an EQ tried on a device: written for Equalizer APO at most this often while it changes)
KINDS = {"PK": "Peak", "LSQ": "Low shelf", "HSQ": "High shelf"}
NUMBER_GAP = 9    # (px between a handle's middle and its number)


def handle_y(f):
    """Where a filter's handle sits up and down: on its own curve at its frequency (a shelf is half way there)."""
    return f["gain"] if f.get("type", "PK") == "PK" else f["gain"] / 2


class FilterHandle(pg.TargetItem):
    """One filter's handle on the EQ graph: a dot in the EQ's colour with a ring of the graph's (switched off:
    hollow, in the axes' grey), its number over it (under it when the graph's top would cut it off)."""

    def __init__(self, page, i, f, col):
        off = f.get("enabled", True) is False
        ring = pg.mkPen(col["axis"] if off else col["bg"], width=2)
        super().__init__(pos=(math.log10(f["freq"]), handle_y(f)), size=13, symbol="o", pen=ring,
                         brush=pg.mkBrush(col["bg"] if off else col["eq"]), hoverPen=pg.mkPen(col["axis"], width=2),
                         hoverBrush=pg.mkBrush(col["eq"]), movable=True, label=str(i + 1),
                         # (its number over it: the offset is in pixels, up being +)
                         labelOpts={"offset": (0, NUMBER_GAP), "anchor": (0.5, 1), "color": col["axis"]})
        self.page, self.i = page, i
        self.sigPositionChanged.connect(lambda _h: self.place_number())
        self.sigPositionChanged.connect(lambda _h: page.handle_moved(self))
        self.sigPositionChangeFinished.connect(lambda _h: page.handle_let_go())

    def viewTransformChanged(self):
        super().viewTransformChanged()
        self.place_number()

    def place_number(self):
        """Its number over it, or under it when there's no room over it: the EQ graph is short (130 px), and its
        scale's room over the highest filter is for the handle, not always for its number too (it was cut off)."""
        lab, vb = self.label(), self.getViewBox()
        if lab is None or not isinstance(vb, pg.ViewBox):  # (while it's added: the plot widget, not yet its graph)
            return
        per_px = vb.viewPixelSize()[1]
        room = (vb.viewRange()[1][1] - self.pos().y()) / per_px if per_px else 1e9  # (pixels over its middle)
        text = lab.boundingRect().height() - lab.textItem.document().documentMargin()  # (the margin over it is empty)
        over = room >= NUMBER_GAP + text
        lab.offset = QPointF(0, NUMBER_GAP if over else -NUMBER_GAP)
        lab.setAnchor((0.5, 1 if over else 0))
        lab.viewTransformChanged()

    def wheelEvent(self, ev):
        ev.accept()
        self.page.handle_wheel(self.i, ev.delta())

    def mouseClickEvent(self, ev):
        if ev.button() == Qt.RightButton and not self.moving:
            ev.accept()
            self.page.handle_menu(self.i, ev.screenPos())
            return
        if ev.double():  # (not a new filter on top of this one)
            ev.accept()
            return
        super().mouseClickEvent(ev)


class EqHandles:
    """The EQ graph's handles."""

    def draw_handles(self):
        """The handles of the EQ shown, drawn again with the EQ graph (draw)."""
        self._handles = []
        if not self.current()[1]:
            return
        col = theme.graph_colours()
        for i, f in enumerate(self.EDIT):
            h = FilterHandle(self, i, f, col)
            h.setToolTip(self.handle_tip(i))
            self.eqplot.addItem(h)
            self._handles.append(h)

    def handle_tip(self, i):
        f = self.EDIT[i]
        hz = f"{f['freq'] / 1000:.2f} kHz" if f["freq"] >= 1000 else f"{f['freq']:g} Hz"
        return (f"Filter {i + 1}: {KINDS.get(f.get('type', 'PK'), 'Peak')}, {hz}, {f['gain']:+.1f} dB, Q {f['q']:g}"
                + (" (off)" if f.get("enabled", True) is False else "")
                + "\nDrag: frequency and gain · mouse wheel: Q · right-click: its type, on or off, Delete")

    def _limited(self, key, v):
        return self.editor.limits.clamp("edit." + key, v)

    def handle_moved(self, h):
        """A handle held and moved: its filter's frequency and gain, within the filter table's limits (the handle kept
        there), then what follows it, soon (LIGHT_MS)."""
        if getattr(self, "_placing", False) or h.i >= len(self.EDIT):
            return
        f, p = self.EDIT[h.i], h.pos()
        shelf = f.get("type", "PK") != "PK"
        freq = self._limited("freq", 10 ** p.x())
        f["freq"] = round(freq) if freq >= 100 else round(freq, 1)
        f["gain"] = round(self._limited("gain", p.y() * 2 if shelf else p.y()), 1)
        x, y = math.log10(f["freq"]), handle_y(f)
        if abs(x - p.x()) > 0.01 or abs(y - p.y()) > 0.15:  # (past a limit: the handle stays at it)
            self._placing = True
            try:
                h.setPos(x, y)
            finally:
                self._placing = False
        h.setToolTip(self.handle_tip(h.i))
        self.follow_soon()

    def follow_soon(self):
        if not hasattr(self, "_light_timer"):
            self._light_timer = QTimer(self, singleShot=True, interval=LIGHT_MS, timeout=self.follow)
        if not self._light_timer.isActive():
            self._light_timer.start()

    def follow(self):
        """What follows a held handle (or the mouse wheel): the EQ's curves, the numbers, the table's values and
        Listen's sound; nothing drawn again, so the handle in hand stays and the scale doesn't move."""
        run, r = self.current()
        if not r:
            return
        from eq import engines
        d = getattr(self, "_eq_drawn", None)
        if d is not None:
            f = d["f"]
            gain = engines.eq_gain(f, self.active(), self.S["site"]["sample_rate"])
            d["eq"].setData(f, gain)
            if d.get("with") is not None:
                d["with"].setData(f, d["meas"] + gain - d["base"])
        st = self.stats()
        self.show_numbers(st)
        self.editor.show_values()
        if run.get("mode") == "manual":
            r["filters"], r["n_filters"] = [dict(x) for x in self.EDIT], st["n"]
        if hasattr(self, "listen"):
            self.listen.update_sound()
        self.sync_trial()

    def handle_let_go(self):
        """The handle let go: the whole page again (the graph drawn, its scale fitted to the EQ now)."""
        if hasattr(self, "_light_timer"):
            self._light_timer.stop()
        self.live_update()

    def holding_handle(self):
        """A filter's handle in hand (dragged, not yet let go)."""
        return any(h.moving for h in getattr(self, "_handles", ()))

    def draw_after_drag(self):
        """The graph asked to be drawn again while a handle is held (curves loaded in the background, a timer): it
        waits, as drawing would take the handle away from under the pointer; letting go draws it (handle_let_go). In
        case the let-go never comes (the button let go where the window didn't see it), it's drawn once no mouse
        button is down."""
        if not hasattr(self, "_drag_watch"):
            self._drag_watch = QTimer(self, interval=500, timeout=self._drag_watched)
        self._drag_watch.start()

    def _drag_watched(self):
        from PySide6.QtWidgets import QApplication
        if self.holding_handle() and QApplication.mouseButtons() != Qt.NoButton:
            return
        self._drag_watch.stop()
        if self.holding_handle():
            for h in self._handles:
                h.moving = False
            self.live_update()

    def handle_wheel(self, i, delta):
        """The mouse wheel over a handle: its Q, 10 % a notch (up: narrower), within the limits."""
        if i >= len(self.EDIT) or not delta:
            return
        f = self.EDIT[i]
        q = self._limited("q", f["q"] * 1.1 ** (delta / 120))
        f["q"] = round(q, 3) if q < 1 else round(q, 2)
        if i < len(getattr(self, "_handles", [])):
            self._handles[i].setToolTip(self.handle_tip(i))
        self.follow()
        if not hasattr(self, "_settle_timer"):
            self._settle_timer = QTimer(self, singleShot=True, interval=SETTLE_MS, timeout=self.live_update)
        self._settle_timer.start()

    def handle_menu(self, i, screen_pos):
        """Right-click on a handle: Peak, Low shelf, High shelf (its type now ticked), Switched on, Delete."""
        if i >= len(self.EDIT):
            return
        import shiboken6
        was = getattr(self, "handle_menu_now", None)
        if was is not None and shiboken6.isValid(was):  # (one at a time)
            was.close()
        f = self.EDIT[i]
        m = QMenu(self.eqplot)
        for k, name in KINDS.items():
            a = m.addAction(name)
            a.setCheckable(True)
            a.setChecked(f.get("type", "PK") == k)
            a.triggered.connect(lambda _=False, k=k: self._change(i, type=k))
        m.addSeparator()
        on = m.addAction("Switched on")
        on.setCheckable(True)
        on.setChecked(f.get("enabled", True) is not False)
        on.triggered.connect(lambda checked: self._change(i, enabled=bool(checked)))
        m.addSeparator()  # (set apart: UI-RULES 14; "Remove": the filter off the EQ, not a file gone, UI-RULES 16)
        m.addAction("Remove", lambda: self._delete(i))
        m.aboutToHide.connect(m.deleteLater)
        self.handle_menu_now = m
        m.popup(QPoint(int(screen_pos.x()), int(screen_pos.y())))

    def _change(self, i, **kw):
        if i < len(self.EDIT):
            self.EDIT[i].update(kw)
            self.editor.rebuild()
            self.live_update()

    def _delete(self, i):
        if i < len(self.EDIT):
            del self.EDIT[i]
            self.editor.rebuild()
            self.live_update()

    def eq_graph_clicked(self, ev):
        """A double-click on the EQ graph where there's no handle: a new peak there."""
        if not ev.double() or ev.button() != Qt.LeftButton or ev.isAccepted():
            return
        vb = self.eqplot.getPlotItem().vb
        if not vb.sceneBoundingRect().contains(ev.scenePos()):
            return
        p = vb.mapSceneToView(ev.scenePos())
        self.add_filter_at(10 ** p.x(), p.y())

    def add_filter_at(self, freq, gain):
        """A new peak (Q 1) at this frequency and gain; with no EQ shown, an EQ by hand begun with it."""
        freq = self._limited("freq", freq)
        f = {"enabled": True, "type": "PK", "freq": round(freq) if freq >= 100 else round(freq, 1),
             "gain": round(self._limited("gain", gain), 1), "q": 1.0}
        if not self.current()[1]:
            self.start_by_hand([], "started on the EQ graph")
        self.EDIT.append(f)
        self.editor.rebuild()
        self.live_update()

    # ---------------------------------------------------------------- an EQ tried on a device follows the edits
    def sync_trial(self):
        """The EQ shown is the one being tried on a device (Try for 5 minutes on): each change written for Equalizer
        APO there too (TRY_MS at most), so it plays in every app as you edit."""
        t, sw = getattr(self, "_trying", None), self.sw
        if getattr(self, "no_trial", False):  # (the Guide's demo dragging a handle: never heard on a device)
            return
        run, r = self.current()
        if not t or not sw.trial or sw.trial["key"] != t["key"] or not r or id(run) != t["run"] or r["id"] != t["rid"]:
            return
        if not hasattr(self, "_try_timer"):
            self._try_timer = QTimer(self, singleShot=True, interval=TRY_MS, timeout=self._write_trial)
        if not self._try_timer.isActive():
            self._try_timer.start()

    def _write_trial(self):
        t = getattr(self, "_trying", None)
        if not t or not self.sw.trial or self.sw.trial["key"] != t["key"]:
            return
        res = self.svc.call("/api/text", {"settings": self.S, "filters": self.active(),
                                          "preamp": self.stats()["preamp_raw"]})
        if res.get("apo"):
            try:
                self.sw.trial_update(res["apo"])
            except OSError as e:
                self.status(f"The device's trial couldn't follow the change: {e}", 6000)


def eq_grid():
    """The frequencies the EQ graph is drawn at when there's no measurement (an EQ by hand on its own)."""
    return np.geomspace(20, 20000, 480)
