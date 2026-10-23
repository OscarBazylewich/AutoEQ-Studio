"""Which measurement to use? (AutoEQ Local's compare.js, natively): every measurement of a model from the online
databases, this PC and the app, ranked for the current target by eq\\compare.py (the rig's match first, then how they
agree, the seal, averaging and the data), with the reasons for each.

- the chart: every candidate levelled together; the recommended one (or the one under the mouse) in blue; grey ones
  are on your target's rig, dotted ones on others; while the mouse is over an average's box, that average (green)
- Use: the measurement into the app and in use (downloaded first when it's online)
- Average and use: measurements on one rig averaged into one (unit and fit differences even out); ticked by default,
  except one far from the others (a fit problem?) and the same data published twice
Offline (net.py): what's on this PC and in the app is compared; online measurements downloaded before too; the others
are listed under "Couldn't load".

The look (Windows 11's; theme_sheet's find_windows part matches the names given here): the chart on a card in the
graph's own colours (blue the recommended one, green the average: never the accent, which is Windows' and may be any
colour), drawn again when the theme changes; a note to heed as a warning box; each measurement a card, filled while
the mouse is over it.
"""
import re
import weakref

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget)

import net
from ui import help_window, icons, tasks, theme
from ui.forms import Fold
from ui.search_combo import SearchCombo

TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]


class _Row(QFrame):
    """A box that tells the window when the mouse is over it (the chart then puts its curve on top)."""

    def __init__(self, on_enter, on_leave):
        super().__init__()
        self.on_enter, self.on_leave = on_enter, on_leave

    def enterEvent(self, e):
        self.on_enter()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.on_leave()
        super().leaveEvent(e)


class CompareWindow(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page, self.svc = page, page.svc
        self.data, self.hot, self.avg_hot, self.picked, self.busy, self.again = None, -1, None, {}, False, None
        self.setWindowTitle("Which measurement to use?")
        self.resize(940, 860)
        # (Qt's own minimum counts each wrapped line of text once, and then squeezed the chart's card, cutting off its
        # scale: room here for the note and the legend on two lines each)
        self.setMinimumSize(700, 660)
        v = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Model"))
        self.q = QLineEdit()
        self.q.setPlaceholderText("e.g. Truthear Gate")
        self.q.returnPressed.connect(lambda: self.run())
        top.addWidget(self.q, 1)
        self.go = QPushButton("Compare")
        theme.mark(self.go, primary=True)
        icons.put(self.go, "find")
        self.go.clicked.connect(lambda: self.run())
        top.addWidget(self.go)
        v.addLayout(top)
        # (the target's rig on a line of its own, its words at the left and its choice at the right as Windows 11's
        # settings: beside the model, a long target name left the model's box a few letters wide at 10.5 pt)
        rig_row = QHBoxLayout()
        self.target_lab = QLabel()
        self.target_lab.setWordWrap(True)
        theme.mark(self.target_lab, role="muted")
        rig_row.addWidget(self.target_lab, 1)
        self.rig = SearchCombo()
        help_window.tag(self.q, "#cmp-q")
        help_window.tag(self.rig, "#cmp-rig")
        self.rig.activated.connect(lambda _i: (self.data or self.busy) and self.run())
        rig_row.addWidget(self.rig)
        v.addLayout(rig_row)
        self.status = QLabel()
        self.status.setWordWrap(True)
        theme.mark(self.status, role="muted")
        v.addWidget(self.status)
        self.note_box = QFrame()  # (a note to heed: a warning box, as Windows 11's)
        theme.mark(self.note_box, card="warn")
        nb = QHBoxLayout(self.note_box)
        nb.setContentsMargins(4, 0, 4, 0)
        mark = QLabel(chr(int(icons.GLYPHS["warning"], 16)))  # (Windows 11's symbol: whichNoteMark)
        mark.setObjectName("whichNoteMark")
        nb.addWidget(mark, 0, Qt.AlignTop)
        self.note = QLabel()
        self.note.setWordWrap(True)
        nb.addWidget(self.note, 1)
        self.note_box.hide()
        v.addWidget(self.note_box)
        self.chart = pg.PlotWidget()
        self.chart.setMinimumHeight(150)  # (230 high, less in a small window: the measurements below stay in sight)
        self.chart.setMaximumHeight(230)
        self.chart.setLogMode(x=True, y=False)
        self.chart.setMenuEnabled(False)
        self.chart.setMouseEnabled(x=False, y=False)
        self.chart.hideButtons()
        self.chart.getAxis("bottom").setTicks([[(np.log10(t), f"{t / 1000:g}k" if t >= 1000 else str(t)) for t in TICKS]])
        chart_card = QFrame()  # (on a card, as Make an EQ's graph; its room inside from the layout, not the sheet)
        chart_card.setObjectName("whichChart")
        theme.mark(chart_card, card=True)
        cc = QVBoxLayout(chart_card)
        cc.setContentsMargins(6, 6, 6, 4)
        cc.addWidget(self.chart)
        v.addWidget(chart_card, 1)
        legend = QLabel("Blue: recommended or under the mouse. Grey: your target's rig. Dotted: other rigs. "
                        "Green dashes: an average, while the mouse is over its box.")
        legend.setWordWrap(True)
        theme.mark(legend, role="muted")
        v.addWidget(legend)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(120)  # (a measurement's card in sight however small the window)
        v.addWidget(self.scroll, 4)
        how = Fold("How the ranking works")
        text = QLabel("<b>Rig (40 points).</b> How well its rig matches your target's.<br>"
                      "<b>Agreement (25).</b> How close it is to the others on the same rig.<br>"
                      "<b>Bass (15).</b> Less bass than the others suggests a leaky seal.<br>"
                      "<b>Averaging (10).</b> Several seatings and both channels.<br>"
                      "<b>Data (10).</b> Range and number of points.<br>Units, fit and tips still vary.")
        text.setWordWrap(True)
        how.add(text)
        v.addWidget(how)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        v.addLayout(row)
        _redraw_on_theme(self)
        self.open_query()

    # ---------------------------------------------------------------- asking compare.py
    def open_query(self):
        db = self.svc.call("/api/db")
        if not db.get("count") and not db.get("loading"):  # (the online lists, from this PC's copy: once)
            self.svc.call("/api/db/refresh", {"settings": self.page.S})
        r = self.svc.call("/api/compare/query", {"settings": self.page.S})
        if r.get("error"):
            self.status.setText(r["error"])
            return
        rigs = r.get("rigs") or {}
        auto = f"{rigs.get(r['target_rig'], r['target_rig'])} ({r.get('how')})" if r.get("target_rig") else "not known"
        self.rig.clear()
        self.rig.addItem(f"Automatic: {auto}", "")
        for k, name in rigs.items():
            self.rig.addItem(name, k)
        self.rig.addItem("Don't know / ignore the rig", "none")
        self.rig.sort_items(pinned=1)  # ("Automatic" on top)
        self.target_lab.setText(f"Target {(r.get('target') or 'not chosen').rsplit('.', 1)[0]} is made for")
        self.q.setText(r.get("query") or "")
        if self.q.text().strip():
            self.run(auto=True)
        else:
            self.status.setText("Type a model name, e.g. “Truthear Gate” or “HD 600”.")
            self.q.setFocus()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):  # (the search box runs it; never a Use button made the default)
            return
        super().keyPressEvent(e)

    def done(self, r):
        if hasattr(self, "_retry"):  # (the window closing stops a wait for the lists)
            self._retry.stop()
        super().done(r)

    def run(self, auto=False):
        if self.busy:
            self.again = auto
            return
        query = self.q.text().strip()
        if not query:
            self.q.setFocus()
            return
        self.busy = True
        self.go.setEnabled(False)
        self.status.setText(f"Looking for “{query}”" + (" (offline: what's on this PC)" if net.offline() else
                                                        " and downloading the measurements") + "…")
        body = {"query": query, "rig": self.rig.currentData() or "", "auto": auto is True, "settings": self.page.S}

        def done(res, err):
            self.busy = False
            self.go.setEnabled(True)
            if (res or {}).get("error", "").startswith("The online database lists are still loading"):
                if not self.isVisible():  # (closed meanwhile: nothing more is compared or downloaded)
                    return
                self.status.setText("Loading the online database lists first…")
                a = auto if self.again is None else self.again
                self.again = None
                if not hasattr(self, "_retry"):
                    self._retry = QTimer(self, singleShot=True, interval=800)
                    self._retry.timeout.connect(lambda: self.run(self._retry_auto))
                self._retry_auto = a
                self._retry.start()
                return
            if err or (res or {}).get("error"):
                self.status.setText(str(err or res["error"]))
            else:
                self.data, self.hot, self.avg_hot = res, -1, None
                self.picked.clear()
                self.q.setText(res.get("query") or query)
                self.render()
            if self.again is not None and self.isVisible():  # (not once closed: nothing more downloaded)
                a, self.again = self.again, None
                self.run(a)
            self.again = None
        tasks.background(lambda: self.svc.call("/api/compare", body), done, owner=self)

    # ---------------------------------------------------------------- showing
    def render(self):
        d = self.data
        n = len(d["items"])
        st = (f"{n} measurement{'s' if n != 1 else ''} of “{d['query']}”. " if n else
              f"None of the measurements of “{d['query']}” could be loaded. " if d.get("errors") else
              f"Nothing called “{d['query']}” was found. Try fewer words (e.g. just the model). ")
        st += (f"Your target is made for the {d['target_rig_name']}." if d.get("target_rig") else
               "Your target's rig isn't known, so the rig isn't scored (choose it above if you know it).")
        self.status.setText(st)
        self.note.setText(d.get("note") or "")
        self.note_box.setVisible(bool(d.get("note")))
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setSpacing(8)
        for w in self._averages():
            lay.addWidget(w)
        for i, c in enumerate(d["items"]):
            lay.addWidget(self._row(i, c))
        if d.get("errors"):
            err = QLabel("Couldn't load: " + "; ".join(d["errors"]))
            err.setWordWrap(True)
            theme.mark(err, role="muted")
            lay.addWidget(err)
        if d.get("links"):
            links = " · ".join(f"<a href='{l['link']}'>{_esc(l['name'])}</a> ({_esc(l['site'])}"
                               f"{', ' + _esc(l['rig']) if l.get('rig') else ''})" for l in d["links"])
            lk = QLabel("Also measured by sites that don't allow downloads (open them to look, or trace their graph): " + links)
            lk.setWordWrap(True)
            lk.setTextFormat(Qt.RichText)
            lk.setOpenExternalLinks(not net.offline())
            if net.offline():
                lk.setToolTip("Offline: go online to open these sites.")
            lay.addWidget(lk)
        lay.addStretch(1)
        self.scroll.setWidget(body)
        self.draw()

    def _row(self, i, c):
        row = _Row(lambda: self._hover(i), lambda: self._hover(-1))
        row.setObjectName("whichRow")  # (filled while the mouse is over it: theme_sheet's find_windows)
        theme.mark(row, card=True)
        h = QHBoxLayout(row)
        rank = QLabel(str(i + 1))
        rank.setObjectName("whichRank")
        rank.setFixedWidth(30)
        h.addWidget(rank, 0, Qt.AlignTop)
        main = QVBoxLayout()
        head = QHBoxLayout()  # (the name, and for the first "· best for your target" in the good colour after it)
        name = QLabel(c["name"])
        name.setObjectName("whichName")  # (semibold)
        name.setTextFormat(Qt.PlainText)
        head.addWidget(name)
        if i == 0:
            best = QLabel("· best for your target")
            theme.mark(best, role="good")
            head.addWidget(best)
        head.addStretch(1)
        main.addLayout(head)
        bits = [c["source"], (c["rig_name"] + ("" if c.get("sure") else " (usual for this source)")) if c.get("rig")
                else "rig not known", f"{c['n_files']} file{'s' if c['n_files'] > 1 else ''}"
                + (f" ({'+'.join(c['channels'])})" if c.get("channels") else "")]
        if c.get("variant"):
            bits.append(f"file “{c['variant']}”")
        if c.get("also"):
            bits.append("also " + ", ".join(c["also"]))
        src = QLabel(" · ".join(bits))
        src.setWordWrap(True)
        theme.mark(src, role="good" if self.data.get("target_rig") and c.get("rig") == self.data["target_rig"] else "muted")
        main.addWidget(src)
        if c.get("reasons"):  # (each a line with its bullet, + good and − not in their colours: find_windows)
            reasons = QGridLayout()
            reasons.setContentsMargins(4, 4, 0, 0)
            reasons.setHorizontalSpacing(8)
            reasons.setVerticalSpacing(2)
            reasons.setColumnStretch(1, 1)
            for k, (s, x) in enumerate(c["reasons"]):
                kind = {"+": "plus", "−": "minus"}.get(s, "")
                for col, text in ((0, "•"), (1, x)):
                    lab = QLabel(text)
                    lab.setTextFormat(Qt.PlainText)
                    lab.setWordWrap(col == 1)
                    if kind:
                        lab.setProperty("reason", kind)
                    reasons.addWidget(lab, k, col, Qt.AlignTop)
            main.addLayout(reasons)
        h.addLayout(main, 1)
        side = QVBoxLayout()
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(max(3, int(round(c["score"]))))
        bar.setTextVisible(False)
        bar.setFixedWidth(110)
        bar.setToolTip("Out of 100")
        side.addWidget(bar)
        score = QLabel(f"<b>{round(c['score'])}</b> / 100")
        score.setTextFormat(Qt.RichText)
        side.addWidget(score, 0, Qt.AlignHCenter)
        use = QPushButton("Use")
        if i == 0:
            theme.mark(use, primary=True)
        use.clicked.connect(lambda _=False, c=c, b=use: self.use(c, b))
        side.addWidget(use)
        side.addStretch(1)
        h.addLayout(side)
        return row

    def _averages(self):
        """Measurements on one known rig, to average into one (the target's rig first)."""
        d, out = self.data, []
        groups = {}
        for c in d["items"]:
            if c.get("rig"):
                groups.setdefault(c["rig"], []).append(c)
        order = sorted(groups.items(), key=lambda kv: (kv[0] != d.get("target_rig"), -len(kv[1])))
        for rig, lst in order:
            if len(lst) < 2:
                continue
            copy_of = {}  # (the same data published twice counts once: within 0.25 dB RMS of a higher-ranked one)
            for i, c in enumerate(lst):
                for p in lst[:i]:
                    if p["hash"] not in copy_of and np.sqrt(np.mean((np.asarray(c["vals"]) - np.asarray(p["vals"])) ** 2)) < 0.25:
                        copy_of[c["hash"]] = p
                        break
            if rig not in self.picked:
                self.picked[rig] = {c["hash"] for c in lst if (c.get("dev") is None or c["dev"] < 2) and c["hash"] not in copy_of}
            sel = self.picked[rig]
            box = _Row(lambda r=rig: self._avg_hover(r), lambda: self._avg_hover(None))
            box.setObjectName("whichAverage")  # (filled while the mouse is over it: theme_sheet's find_windows)
            theme.mark(box, card=True)
            bv = QVBoxLayout(box)
            head = QHBoxLayout()
            title = QLabel(f"Average the {len(lst)} measurements on the {lst[0]['rig_name']}")
            title.setObjectName("whichName")  # (semibold)
            title.setTextFormat(Qt.PlainText)
            title.setWordWrap(True)
            words = QVBoxLayout()
            words.addWidget(title)
            sub = QLabel("Same rig, so they differ only by unit and fit; averaging evens that out.")
            sub.setWordWrap(True)
            theme.mark(sub, role="muted")
            words.addWidget(sub)
            head.addLayout(words, 1)
            btn = QPushButton()
            theme.mark(btn, primary=True)
            head.addWidget(btn)
            bv.addLayout(head)
            note = QLabel()
            note.setWordWrap(True)
            names = {" ".join(re.sub(r"[^a-z0-9]+", " ", c["name"].lower()).split()) for c in lst}

            def update(lst=lst, sel=sel, btn=btn, note=note, names=names, copy_of=copy_of, rig=rig):
                n = sum(1 for c in lst if c["hash"] in sel)
                btn.setEnabled(n >= 2)
                btn.setText(f"Average {n} and use" if n >= 2 else "Tick at least 2")
                far = [c["source"] for c in lst if c.get("dev") is not None and c["dev"] >= 2]
                via = lambda c: c["source"] + (" via AutoEq" if str(c.get("site", "")).startswith("AutoEq") else "")
                dup = [f"{via(c)} (the same data as {via(copy_of[c['hash']])})" for c in lst if c["hash"] in copy_of]
                note.setText(("Not all are named the same (other tips or versions?): tick only one version. " if len(names) > 1 else "")
                             + (f"Left out so they don't count twice: {', '.join(dup)}. " if dup else "")
                             + (f"Left out by default: {', '.join(far)} (more than 2 dB from the others on this rig)." if far else ""))
                if self.avg_hot == rig:
                    self.draw()
            for c in lst:
                cb = QCheckBox(f"{c['name']} · {c['source']}" + (f" · {c['n_files']} files" if c["n_files"] > 1 else ""))
                cb.setChecked(c["hash"] in sel)
                cb.toggled.connect(lambda on, h=c["hash"], sel=sel, update=update: (sel.add(h) if on else sel.discard(h), update()))
                bv.addWidget(cb)
            bv.addWidget(note)
            btn.clicked.connect(lambda _=False, lst=lst, sel=sel, btn=btn: self.average(lst, sel, btn))
            update()
            out.append(box)
        return out

    def _hover(self, i):
        self.hot = i
        self.draw()

    def _avg_hover(self, rig):
        self.avg_hot = rig
        self.draw()

    def draw(self):
        """The chart in the graph's own colours (theme.graph_colours(): never the accent, Windows' own colour): the
        recommended one, or the one under the mouse, blue on top; the others grey (your target's rig) or dotted (other
        rigs); an average's box under the mouse: that average in green dashes. Drawn again when the theme changes."""
        ch = self.chart
        ch.clear()
        col, t = theme.graph_colours(), theme.tokens()
        ch.setBackground(col["bg"])
        for ax in ("left", "bottom"):
            ch.getAxis(ax).setPen(pg.mkPen(col["axis"]))
            ch.getAxis(ax).setTextPen(pg.mkPen(col["axis"]))
        ch.showGrid(x=True, y=True, alpha=0.2)
        d = self.data
        if not d or not d["items"]:
            return
        f = np.asarray(d["f"])
        top = self.hot if self.hot >= 0 else 0
        order = [i for i in range(len(d["items"])) if i != top] + [top]
        for i in order:
            c = d["items"][i]
            same = not d.get("target_rig") or c.get("rig") == d["target_rig"]
            colour = _colour(col["with_eq"] if i == top else col["target"] if same else col["axis"],
                             255 if i == top else 130 if same else 90)
            ch.plot(f, np.asarray(c["vals"], dtype=float),
                    pen=pg.mkPen(colour, width=2.5 if i == top else 1.2,
                                 style=Qt.SolidLine if same or i == top else Qt.DotLine))
        if self.avg_hot:
            lst = [c for c in d["items"] if c.get("rig") == self.avg_hot and c["hash"] in self.picked.get(self.avg_hot, set())]
            if len(lst) >= 2:
                avg = np.mean([np.asarray(c["vals"], dtype=float) for c in lst], axis=0)
                ch.plot(f, avg, pen=pg.mkPen(t["c4"], width=3, style=Qt.DashLine))  # (the graph's green)
        inside = (f >= 30) & (f <= 12000)
        vals = np.sort(np.concatenate([np.asarray(c["vals"], dtype=float)[inside] for c in d["items"]]))
        lo = np.floor((vals[int(len(vals) * 0.01)] - 3) / 5) * 5
        hi = np.ceil((vals[int(len(vals) * 0.99)] + 3) / 5) * 5
        ch.setYRange(lo, hi, padding=0)
        ch.setXRange(np.log10(20), np.log10(20000), padding=0)

    # ---------------------------------------------------------------- using
    def use(self, c, btn):
        btn.setEnabled(False)
        body = dict(c["body"], kind="measurement", settings=self.page.S)

        page = self.page

        def done(res, err):
            here = tasks.alive(self)  # (closed meanwhile: what was downloaded is still used)
            if err or (res or {}).get("error"):
                if here:
                    btn.setEnabled(True)
                    QMessageBox.warning(self, "Couldn't use it", str(err or res["error"]))
                return
            page.used(res)
            if here:
                self.accept()
        tasks.background(lambda: self.svc.call("/api/use", body), done)

    def average(self, lst, sel, btn):
        keys = [c["hash"] for c in lst if c["hash"] in sel]
        btn.setEnabled(False)
        btn.setText("Averaging…")  # (a second click would save the average twice)
        body = {"keys": keys, "name": self.data["query"], "settings": self.page.S}

        page = self.page

        def done(res, err):
            here = tasks.alive(self)
            if err or (res or {}).get("error"):
                if here:
                    QMessageBox.warning(self, "Couldn't average", str(err or res["error"]))
                    btn.setEnabled(True)
                    btn.setText(f"Average {len(keys)} and use")
                return
            page.used(dict(res, kind="measurement", names=[]))
            if here:
                self.accept()
        tasks.background(lambda: self.svc.call("/api/compare/average", body), done)


def _redraw_on_theme(window):
    """The window's chart drawn again when Windows' theme or accent changes (its colours are drawn, not styled), for
    as long as the window is there: held weakly, so a window closed and deleted never stays for it (theme.apply lets
    go of a listener that raises RuntimeError)."""
    ref = weakref.ref(window)

    def again():
        w = ref()
        if w is None or not tasks.alive(w):
            raise RuntimeError("Which measurement is closed")
        w.draw()
    theme.on_change(again)


def _colour(hex_, alpha):
    from PySide6.QtGui import QColor
    c = QColor(hex_)
    c.setAlpha(alpha)
    return c


def _esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;")
