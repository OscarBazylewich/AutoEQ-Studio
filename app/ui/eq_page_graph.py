"""Make an EQ's curves and graph (a part of EqPage, ui/eq_page.py): the curves for the settings now (worked out off
the window's thread: an older answer arriving late is dropped), the analysis and the automatic settings (the Search
line), the graph drawn in its views (View, Y range, Channels) with the values under the pointer, the curves shown
from Find… (dotted: not in use) and Listen's marker.
EqGraph is a plain class (no __init__, no signals); EqPage (ui/eq_page.py) joins it with the other parts.
"""
import json

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from ui import tasks, theme


class EqGraph:
    """Make an EQ's curves and graph."""

    # ---------------------------------------------------------------- the curves and the graph
    def load_curves(self):
        """The curves for the settings now, worked out off the window's thread (an older answer arriving after a
        newer request is dropped, as plot.js curveSeq)."""
        s = json.loads(json.dumps(self.S))  # (a copy: the settings may change while it's worked out)
        self._curves_seq = getattr(self, "_curves_seq", 0) + 1
        seq = self._curves_seq

        def done(c, err):
            if seq == self._curves_seq:
                self.curves_loaded({"error": str(err)} if err else c)
        tasks.background(lambda: self.svc.call("/api/curves", {"settings": s}), done, owner=self)

    def curves_loaded(self, c):
        """New curves: the graph, its title and note, the shown curves, History's note, Listen's list, the result's
        numbers, then the analysis and automatic settings."""
        if not c or c.get("error"):
            self.curves, self.rig_note = None, ""
            self.graph_title.setText("")
            self.graph_note.setText(str((c or {}).get("error") or "The curves couldn't be worked out."))
            self.chip_noeq.hide()
            self.draw()
            return
        self.curves = c
        self.graph_title.setText(f"{c['name']}  →  {c['target_name']}")
        self.rig_note = ((c.get("rig") or {}).get("text") or "") if isinstance(c.get("rig"), dict) else ""
        self.graph_note.setText(self.rig_note)
        self.chip_noeq.setVisible(c.get("no_eq_rms") is not None)
        if c.get("no_eq_rms") is not None:
            self.chip_noeq.setText(f"Error without EQ  {c['no_eq_rms']:.2f} dB")
        self.draw()
        self.refresh_previews()
        self.history_note()
        self.listen.show()
        self.listen.load_pins(c["name"])
        if self.current()[1]:
            self.live_update()  # (the error and pre-amp over these curves)
        self.load_analysis()

    def load_analysis(self):
        s = json.loads(json.dumps(self.S))
        seq = getattr(self, "_curves_seq", 0)

        def done(an, err):
            if seq != getattr(self, "_curves_seq", 0):  # (other curves meanwhile: their own analysis follows)
                return
            self.analysis = None if err or (an or {}).get("error") else an
            self.refresh_auto()
        tasks.background(lambda: self.svc.call("/api/analysis", {"settings": s}), done, owner=self)

    def refresh_auto(self):
        """The automatic settings for these curves: their values go into the settings (not yours), and the Search
        line says what a run tries and how long it takes."""
        if self.svc is None:
            return
        a = self.svc.call("/api/auto", {"settings": self.S, "analysis": self.analysis})
        if a.get("error"):
            self.sa_what.setText(a["error"])
            return
        self.auto = a
        from eq import settings as eq_settings
        moved = []
        if self.S["auto"]["enabled"]:
            manual = set(self.S["auto"].get("manual") or [])
            for p, v in (a.get("values") or {}).items():
                if p not in manual and eq_settings.get_path(self.S, p) != v:
                    eq_settings.set_path(self.S, p, v)
                    moved.append(p)
        if moved:  # (kept, and as auto.js applyValues: a new scored range is a new "Error without EQ")
            self._save_timer.start()
            if any(p.startswith("scoring.band_hz") for p in moved):
                self.load_curves()
        search = a.get("search") or ""
        self.sa_what.setText((search[:1].upper() + search[1:] + ".") if search else "")
        self.estimate.setText(f"A run takes {a['time']}" if a.get("time") else "")
        if hasattr(self, "settings"):
            self.settings.refresh()  # (the values filled in, "Why these values")

    def _recolour(self, draw=True):
        col = theme.graph_colours()
        for p in (self.plot, self.eqplot):
            p.setBackground(col["bg"])
            for ax in ("left", "bottom"):
                p.getAxis(ax).setPen(pg.mkPen(col["axis"]))
                p.getAxis(ax).setTextPen(pg.mkPen(col["axis"]))
            p.showGrid(x=True, y=True, alpha=0.25)
        if draw:
            self.draw()
            if hasattr(self, "listen"):
                self.listen.refresh()
            if hasattr(self, "editor"):
                self.editor.rebuild()
            if hasattr(self, "settings"):
                self.settings.refresh()

    def own_filters(self):
        """Best fit's “Start from your own filters”, read (for the graph's “With your filters”): [] when none."""
        if self.S["mode"] != "best_fit" or not self.S["best_fit"].get("start_filters", "").strip():
            return []
        text = self.S["best_fit"]["start_filters"]
        if getattr(self, "_own", (None,))[0] != text:
            r = self.svc.call("/api/filters/parse", {"text": text})
            self._own = (text, [x for x in r.get("filters") or [] if x.get("enabled", True) is not False])
        return self._own[1]

    def current(self):
        """The result shown: (its run, the result) or (None, None)."""
        if not self.run_result or self.sel is None:
            return None, None
        return self.run_result, next((r for r in self.run_result["results"] if r["id"] == self.sel), None)

    def graph_option(self, **kw):
        """A view of the graph chosen (View, Y range, Channels): kept, without redrawing the other screens."""
        sw = self.sw
        sw.s["graph"] = dict(sw.s.get("graph") or {}, **kw)
        if not hasattr(self, "_graph_timer"):
            self._graph_timer = QTimer(self, singleShot=True, interval=500, timeout=sw.save)
        self._graph_timer.start()
        self.draw()

    def demo_graph(self, **kw):
        """A Guide demo shows a view of the graph (View, Y range, Channels), not kept: the function it returns puts
        the graph and its controls back."""
        from PySide6.QtCore import QSignalBlocker
        was = getattr(self, "_graph_demo", None)
        g = self._graph_demo = dict(was or self.sw.s.get("graph") or {}, **kw)

        def show(g):
            with QSignalBlocker(self.view_combo), QSignalBlocker(self.yrange_combo), QSignalBlocker(self.channels_chk):
                self.view_combo.setCurrentIndex(max(0, self.view_combo.findData(g.get("view", "abs"))))
                self.yrange_combo.setCurrentIndex(max(0, self.yrange_combo.findData(g.get("y", "auto"))))
                self.channels_chk.setChecked(bool(g.get("channels")))
            self.draw()
        show(g)

        def undo():
            self._graph_demo = was
            show(was or self.sw.s.get("graph") or {})
        return undo

    def _hover(self, pos):
        """The values under the pointer (frequency, then each curve's dB), as plot.js's tooltip."""
        c = getattr(self, "_drawn", None)
        if not c or not self.plot.sceneBoundingRect().contains(pos):
            self.hover_lab.setText("")
            return
        x = self.plot.getPlotItem().vb.mapSceneToView(pos).x()
        f = 10 ** x
        i = int(np.argmin(np.abs(np.asarray(c["f"]) - f)))
        hz = c["f"][i]
        parts = [f"{hz / 1000:.2f} kHz" if hz >= 1000 else f"{hz:.0f} Hz"]
        for name, vals in c["series"]:
            parts.append(f"{name} {vals[i]:+.1f}" if c["rel"] else f"{name} {vals[i]:.1f}")
        self.hover_lab.setText("  ·  ".join(parts) + " dB")

    def draw(self):
        col = theme.graph_colours()
        self.plot.clear()
        self.eqplot.clear()
        self.legend.clear()
        c = self.curves
        self._drawn = None
        if not c:
            return
        g = getattr(self, "_graph_demo", None) or self.sw.s.get("graph") or {}
        rel = g.get("view") == "rel"
        f = np.asarray(c["f"])
        meas, tgt = np.asarray(c["meas"]), np.asarray(c["target"])
        base = tgt if rel else np.zeros_like(tgt)  # (relative to target: what's left to correct, 0 dB = on target)
        sub = lambda vals: np.asarray(vals, dtype=float) - base
        series = []  # (name, values as drawn): for the Y range and the readout
        t = theme.tokens()
        band = self.S["scoring"]["band_hz"]  # (outside the scored range: shaded, "not scored")
        for lo, hi in ((20, band[0]), (band[1], 20000)):
            if hi > lo:
                self.plot.addItem(pg.LinearRegionItem((np.log10(lo), np.log10(hi)), movable=False,
                                                      brush=pg.mkBrush(QColor(t["shade"])), pen=pg.mkPen(None)))
        chans = c.get("channels") or []
        self.channels_chk.setVisible(len(chans) > 1)
        if g.get("channels") and len(chans) > 1:
            for ch in chans:
                self.plot.plot(f, sub(ch), pen=pg.mkPen(t["muted"], width=1))
        rig = c.get("rig") if isinstance(c.get("rig"), dict) else {}
        if rig.get("applied") and rig.get("uncertainty") and len(rig["uncertainty"]) == len(f):
            u = np.asarray(rig["uncertainty"], dtype=float)  # (a converted target: how far off it may be)
            up = self.plot.plot(f, sub(tgt) + u, pen=pg.mkPen(None))
            dn = self.plot.plot(f, sub(tgt) - u, pen=pg.mkPen(None))
            tc = QColor(col["target"])
            tc.setAlpha(40)
            self.plot.addItem(pg.FillBetweenItem(up, dn, brush=pg.mkBrush(tc)))
        tname = (f"Target (for {rig['unit']})" if rig.get("unit") else f"Target (for the {rig.get('meas_rig')})") \
            if rig.get("applied") else "Target"
        self.plot.plot(f, sub(tgt), pen=pg.mkPen(col["target"], width=2, style=Qt.DashLine), name=tname)
        self.plot.plot(f, sub(meas), pen=pg.mkPen(col["meas"], width=2), name="Measurement")
        series += [("Target", sub(tgt)), ("Measurement", sub(meas))]
        self.clear_prev_btn.setVisible(bool(self.previews))
        for i, (_, name, vals) in enumerate(self.previews):  # (from the search: shown, not in use)
            if len(vals) == len(f):
                self.plot.plot(f, sub(vals), name=f"{name} (preview)",
                               pen=pg.mkPen(t[("c3", "c5", "c4", "c2")[i % 4]], width=1.6, style=Qt.DotLine))
        if hasattr(self, "listen"):
            from eq import engines
            from ui.listen import COLOURS
            for i, pin in enumerate(self.listen.pins):
                if pin.get("shown", True):
                    pg_ = engines.eq_gain(f, [x for x in pin["filters"] if x.get("enabled", True) is not False],
                                          self.S["site"]["sample_rate"])
                    self.plot.plot(f, sub(meas + pg_), name=pin["name"],
                                   pen=pg.mkPen(t[COLOURS[pin.get("color", i) % len(COLOURS)]], width=1.6, style=Qt.DashLine))
        mine = self.own_filters()
        if mine:
            from eq import engines
            self.plot.plot(f, sub(meas + engines.eq_gain(f, mine, self.S["site"]["sample_rate"])), name="With your filters",
                           pen=pg.mkPen(col["with_eq"], width=1.8, style=Qt.DashDotLine))
        self.marker = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(t["c4"], width=1.5))
        self.marker.hide()
        self.plot.addItem(self.marker)
        _, r = self.current()
        if r:
            from eq import engines
            gain = engines.eq_gain(f, self.active(), self.S["site"]["sample_rate"])
            self.plot.plot(f, sub(meas + gain), pen=pg.mkPen(col["with_eq"], width=2.5), name="With the EQ")
            series.append(("With the EQ", sub(meas + gain)))
            self.eqplot.plot(f, gain, pen=pg.mkPen(col["eq"], width=2), fillLevel=0,
                             brush=pg.mkBrush(col["eq"] + "33"))
            top = max(6.0, float(np.max(np.abs(gain))) * 1.15)
            self.eqplot.setYRange(-top, top, padding=0)
        else:
            self.eqplot.setYRange(-12, 12, padding=0)  # (no EQ yet: a sensible scale, not a line's own)
        self.eqplot.addLine(y=0, pen=pg.mkPen(col["axis"], width=1))
        self.plot.setXRange(np.log10(20), np.log10(20000), padding=0)
        # the Y range (plot.js): auto from the curves (60 dB at most), or a span around the target's 100 Hz-10 kHz
        ys = g.get("y", "auto")
        if ys == "auto":
            allv = np.concatenate([v for _n, v in series])
            hi = np.ceil((np.nanmax(allv) + 2) / 5) * 5
            lo = max(np.floor((np.nanmin(allv) - 2) / 5) * 5, hi - 60)
        else:
            span = float(ys)
            mid = (f >= 100) & (f <= 10000)
            centre = 0.0 if rel else float(np.mean(tgt[mid]))
            lo = round((centre - span / 2) / 5) * 5
            hi = lo + span
        self.plot.setYRange(lo, hi, padding=0)
        self.plot.getAxis("left").setLabel("Δ dB" if rel else "dB")
        self._drawn = {"f": list(f), "rel": rel, "series": series}

    # ---------------------------------------------------------------- the curves shown from Find… (dotted: not in use)
    def preview_on(self, key):
        return any(k == key for k, _, _ in self.previews)

    def add_preview(self, key, name, vals, body=None):
        self.previews = [p for p in self.previews if p[0] != key] + [(key, name, vals)]
        self.previews = self.previews[-4:]  # (a few at a time)
        if body is not None:
            self.preview_bodies[key] = body
        self.preview_bodies = {k: b for k, b in self.preview_bodies.items() if self.preview_on(k)}
        self.draw()

    def remove_preview(self, key):
        self.previews = [p for p in self.previews if p[0] != key]
        self.preview_bodies.pop(key, None)
        self.draw()

    def clear_previews(self):
        self.previews, self.preview_bodies = [], {}
        self.draw()

    def refresh_previews(self):
        """The shown curves worked out again with the settings now (smoothing, levelling, rig conversion …)."""
        for key, body in list(self.preview_bodies.items()):
            req = dict(body, settings=self.S)

            def done(res, err, key=key):
                if err or (res or {}).get("error") or not self.preview_on(key):
                    return
                self.previews = [(k, n, res["vals"] if k == key else v) for k, n, v in self.previews]
                self.draw()
            tasks.background(lambda req=req: self.svc.call("/api/preview", req), done, owner=self)

    # ---------------------------------------------------------------- Listen (ui/listen.py): its marker on the graph
    def draw_marker(self):
        """The frequency Listen plays now (a tone, the sweep) as a line on the graph."""
        m = getattr(self, "marker", None)
        if m is None:
            return
        hz = self.listen.marker_hz() if hasattr(self, "listen") else None
        if hz:
            m.setValue(np.log10(hz))
            m.show()
        else:
            m.hide()
