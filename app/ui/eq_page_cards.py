"""Make an EQ's cards (a part of EqPage, ui/eq_page.py): the page laid out once the EQ part has opened, top to
bottom: the graph (its title, Trace a graph image…, History…, View, Y range, Channels, Hide previews), Target, then
Measurement (Find…,
Add…), Make the EQ (your EQ app, the method, the search, Run), the settings' folds
(ui/eq_settings.py), Your result (its numbers, the filters, File name, Save filters, Use on device) and Listen
(ui/listen.py). This is the file to restyle Make an EQ in.
The look is Windows 11's (the restyle, 2026-10-23): Windows 11's symbols beside the main actions' words
(ui/icons.py), and every card as wide as the window and no wider (a long
title wraps, a long name ends in "…"; Target and Measurement one above the other, so their names fit). Its own
style rules are theme_sheet.py's eq_screen part (the properties eqtitle, and eqsub in ui/eq_settings.py).
EqCards is a plain class (no __init__, no signals); EqPage (ui/eq_page.py) joins it with the other parts. What it
makes is the page's (self.run_btn, self.plot …), and the other parts use it.

The page is made in steps (_build_steps, 2026-10-24: made in one go it froze the window for ~0.45 s), one per turn of
the window's event loop, so the window answers in between (each step a few ms; EqPage runs them): the page's frame
first (its scroll area and column, in the page, hidden), then the graph, Target and Measurement, Make
the EQ, the settings in four parts (ui/eq_settings.py), the result, Listen, the files in their lists, and last the
whole page shown at once ("Opening the EQ part…" until then: never seen half-made). The rule for every step: each part
goes into its final place in the step that makes it, never in a later one. Qt styles what it made between steps, and
a part moved once styled is styled again, all of it (the settings' folds moved a step later cost 42 ms; the whole page
moved into place at the end, as before, 149 ms).
"""
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLineEdit, QMenu, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from ui import help_window, icons, theme
from ui.eq_page_parts import TICKS, Elided, NameCombo, PairTitle, hz, label
from ui.forms import CHOICE_MOST
from ui.search_combo import SearchCombo


class EqCards:
    """Make an EQ's cards, made once, in this order, by _build_steps."""

    # ---------------------------------------------------------------- building
    def _build_steps(self):
        """The page, a step at a time (each yield ends one: EqPage runs the next in the next turn of the event loop).
        Each part goes into its final place in the step that makes it (see the module's words); the page is shown in
        the last step (after the last yield), whole."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setSpacing(12)
        col.setContentsMargins(14, 14, 14, 14)
        scroll.setWidget(body)
        scroll.hide()  # ("Opening the EQ part…" until the page is whole)
        self.layout().addWidget(scroll)  # (in its place first: the cards then go straight into it, never moved)
        yield "the page's frame"
        col.addWidget(self._graph_card())
        yield "the graph"
        # (one above the other, each the page's width: side by side, with Windows 11's sizes, a measurement's name was
        # cut off in its drop-down at the window's own size, 2026-10-23)
        col.addWidget(self._file_card("target"))
        col.addWidget(self._file_card("measurement"))
        yield "Target, Measurement"
        col.addWidget(self._eq_card())
        yield "Make the EQ"
        from ui.eq_settings import EqSettings
        settings = EqSettings(self)
        # (Adjust onto the Target card, under the target: AutoEQ Local's; the Settings fold; Advanced in two halves)
        yield from settings.parts(col, self.target_box.layout())
        self.settings = settings
        col.addWidget(self._result_card())
        # (the settings shown again now the result card is there: its line under File name, "Save filters writes: …",
        # was made after Make the EQ first showed them, and stayed empty until a setting changed, 2026-10-23)
        self.show_settings()
        yield "the result"
        from ui.listen import Listen
        self.listen = Listen(self)
        self.listen.hide()  # (once there are curves)
        col.addWidget(self.listen)
        col.addStretch(1)
        yield "Listen"
        self.show_inputs(self.meta["inputs"])  # (the files in their lists before the page shows: never empty there)
        yield "the files"
        self.loading.hide()
        scroll.show()

    def _graph_card(self):
        card = QFrame()
        theme.mark(card, card=True)
        v = QVBoxLayout(card)
        # (a card frame's padding leaves 4 px for this: its title then starts where the cards' titles below it do;
        # Qt's own 9 px put it 5 px further in, 2026-10-23)
        v.setContentsMargins(4, 4, 4, 4)
        head = QHBoxLayout()
        self.graph_title = PairTitle()  # (the target under the measurement on a narrow window: on one line it made
        theme.mark(self.graph_title, eqtitle=True)  # the page wider than the window)
        head.addWidget(self.graph_title, 1)
        self.chip_noeq = label("", "chip", wrap=False)
        head.addWidget(self.chip_noeq, 0, Qt.AlignVCenter)  # (its own height: a value, not a button)
        # (each opens a window: "…", and the tracer's own words, as Find…'s, UI-RULES 11 and 16)
        self.trace_btn = QPushButton("Trace a graph image…")
        icons.put(self.trace_btn, "trace")
        self.trace_btn.setToolTip("Make a frequency response from a picture of a graph")
        self.trace_btn.clicked.connect(self.open_trace)
        head.addWidget(self.trace_btn)
        self.hist_btn = QPushButton("History…")
        icons.put(self.hist_btn, "history")
        self.hist_btn.setToolTip("Your past EQs, kept between sessions")
        self.hist_btn.clicked.connect(lambda: self.open_history(False))
        head.addWidget(self.hist_btn)
        v.addLayout(head)
        opts = QHBoxLayout()  # (the graph's views, as AutoEQ Local's: kept between sessions)
        g = self.sw.s.get("graph") or {}
        opts.addWidget(label("View", wrap=False))
        self.view_combo = SearchCombo()
        self.view_combo.addItem("Absolute", "abs")
        self.view_combo.addItem("Relative to target", "rel")
        self.view_combo.sort_items()
        self.view_combo.setCurrentIndex(max(0, self.view_combo.findData(g.get("view", "abs"))))
        self.view_combo.activated.connect(lambda _i: self.graph_option(view=self.view_combo.currentData()))
        help_window.tag(self.view_combo, "#opt-view")
        opts.addWidget(self.view_combo)
        opts.addWidget(label("Y range", wrap=False))
        self.yrange_combo = SearchCombo()
        for k, name in (("auto", "Auto"), ("30", "30 dB"), ("40", "40 dB"), ("50", "50 dB"), ("60", "60 dB")):
            self.yrange_combo.addItem(name, k)
        self.yrange_combo.sort_items(pinned=1)  # ("Auto" on top, the user's ask)
        self.yrange_combo.setCurrentIndex(max(0, self.yrange_combo.findData(g.get("y", "auto"))))
        self.yrange_combo.activated.connect(lambda _i: self.graph_option(y=self.yrange_combo.currentData()))
        help_window.tag(self.yrange_combo, "#opt-y")
        opts.addWidget(self.yrange_combo)
        self.channels_chk = QCheckBox("Channels")
        self.channels_chk.setChecked(bool(g.get("channels")))
        self.channels_chk.toggled.connect(lambda on: self.graph_option(channels=on))
        help_window.tag(self.channels_chk, "#opt-ch")
        opts.addWidget(self.channels_chk)
        # (a view of the graph, with the others: it popped into the header between Trace and History, moving them)
        self.clear_prev_btn = QPushButton("Hide previews")  # (Find…'s Preview and Hide, and the legend's words)
        icons.put(self.clear_prev_btn, "hide")
        self.clear_prev_btn.setToolTip("Take the previews from Find… (dotted) off the graph")
        self.clear_prev_btn.clicked.connect(self.clear_previews)
        self.clear_prev_btn.hide()
        opts.addWidget(self.clear_prev_btn)
        opts.addStretch(1)
        self.hover_lab = Elided("")  # (never wider than its room: "…" at its end on a narrow window)
        theme.mark(self.hover_lab, role="muted")
        opts.addWidget(self.hover_lab)
        v.addLayout(opts)
        self.plot = pg.PlotWidget()
        self.plot.setMinimumHeight(300)
        self.plot.scene().sigMouseMoved.connect(self._hover)
        self.eqplot = pg.PlotWidget()
        self.eqplot.setFixedHeight(130)
        self.eqplot.setXLink(self.plot)
        for p in (self.plot, self.eqplot):
            p.setLogMode(x=True, y=False)
            p.setMenuEnabled(False)
            p.setMouseEnabled(x=False, y=False)
            p.hideButtons()
            p.getAxis("bottom").setTicks([[(np.log10(t), hz(t).replace(" Hz", "").replace(" kHz", "k")) for t in TICKS]])
            p.setXRange(np.log10(20), np.log10(20000), padding=0)
        self.legend = self.plot.addLegend(offset=(10, 10))
        self.plot.getAxis("left").setLabel("dB")
        self.eqplot.getAxis("left").setLabel("EQ dB")
        # (the EQ graph is where the filters are dragged: ui/eq_page_handles.py; a double-click adds one)
        self.eqplot.scene().sigMouseClicked.connect(self.eq_graph_clicked)
        self.eqplot.setAccessibleName("EQ graph")
        self.eqplot.setToolTip("Drag a filter's handle: frequency and gain; the mouse wheel over it: its Q; right-click "
                               "it: its type, on or off, Remove. Double-click where there's none: a new filter there")
        help_window.tag(self.eqplot, "#eq-graph")
        # (both graphs' value axes one width, room for three characters ("-12", "100") in the font pyqtgraph draws
        # them in: left to themselves, each took the width of the first numbers it drew, so a page made ahead, first
        # drawn with its curves, had a narrower one than the EQ graph under it (their edges 4 px apart), and each
        # jumped wider once its curves came, 2026-10-24)
        room = QFontMetrics(QApplication.font()).horizontalAdvance("-188") + 1
        for p in (self.plot, self.eqplot):
            p.getAxis("left").setStyle(autoExpandTextSpace=False, tickTextWidth=room)
        v.addWidget(self.plot)
        v.addWidget(self.eqplot)
        self.graph_note = label("", "muted")
        self.graph_note.hide()  # (shown when it has words: a rig's note, or why there are no curves)
        v.addWidget(self.graph_note)
        self._recolour(draw=False)
        return card

    def notify(self, text, undo=None):
        """What was just done to your files or settings (Use, an average, a move, a preset) in the window's message
        line, with Undo beside it when it can be undone (window_parts.MessageLine: every message in one place; the
        notice card that was here, between the cards, made the page jump as it came and went)."""
        self.status(text, undo=undo)

    def _file_card(self, kind):
        box = QGroupBox("Target" if kind == "target" else "Measurement")
        v = QVBoxLayout(box)
        combo = NameCombo()  # (a name longer than its room ends in "…": never cut off)
        combo.setMinimumContentsLength(20)
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.activated.connect(lambda _i, k=kind: self._file_chosen(k))
        help_window.tag(combo, "slot:" + kind)
        row = QHBoxLayout()
        row.addWidget(combo, 1)
        find = QPushButton("Find…")
        icons.put(find, "find")
        find.setToolTip("Search your files, this PC and the online databases")
        find.clicked.connect(lambda _=False, k=kind: self.find(k))
        row.addWidget(find)
        add = QPushButton("Add…")
        icons.put(add, "add")
        add.setToolTip("Add target files from this PC" if kind == "target" else
                       "Add measurement files from this PC (a set: L/R, seatings)")
        add.clicked.connect(lambda _=False, k=kind: self.add_files(k))
        row.addWidget(add)
        v.addLayout(row)
        note = label("", "muted")
        note.hide()  # (shown when it has words: eq_page_files.show_inputs)
        v.addWidget(note)
        if kind == "measurement":
            other = QPushButton("Other measurements of this model…")
            other.setToolTip("Find every measurement of this model and see which suits your target best")
            other.clicked.connect(self.compare)
            v.addWidget(other, 0, Qt.AlignLeft)
            row2 = QHBoxLayout()
            self.eqd_before = label("", wrap=False)
            row2.addWidget(self.eqd_before)
            self.eqd_show = QPushButton("Show in History…")  # (it opens History, this IEM's: UI-RULES 11, 16)
            self.eqd_show.setToolTip("History's window, showing the EQs made for this IEM")
            self.eqd_show.clicked.connect(lambda: self.open_history(True))
            row2.addWidget(self.eqd_show)
            row2.addStretch(1)
            v.addLayout(row2)
            self.eqd_before.hide()
            self.eqd_show.hide()
        setattr(self, f"{kind}_combo", combo)
        setattr(self, f"{kind}_note", note)
        setattr(self, f"{kind}_box", box)
        return box

    def _eq_card(self):
        """Make the EQ: first the way to make it (the user's ask, 2026-10-27: By hand was a small menu at the end of
        the Run row, after three settings only a run uses), as tabs in the look of the app's other tabs (Table /
        Sliders, Find…'s sources: .claude/notes/UI-RULES.md 8): Automatically (a run: AutoEQ fits the filters) or By
        hand (an EQ of your own). Under them Your EQ app, which both use (its limits, the file Save writes), then only
        the chosen way's steps: Method, Search and Run (with Run several…), or Start from and Start. Its three grids
        keep one label column (_line_up_ways)."""
        self.eq_box = box = QGroupBox("Make the EQ")
        v = QVBoxLayout(box)
        v.setSpacing(8)
        tabs = QHBoxLayout()
        tabs.setSpacing(4)
        self.way_btns = {}
        for key, words, tip in (("auto", "Automatically", "AutoEQ fits the filters to the target for your EQ app: "
                                 "choose the method, then Run"),
                                ("hand", "By hand", "You set the filters: start empty or from an EQ you have, then "
                                 "change them on the EQ graph")):
            b = QPushButton(words)
            b.setCheckable(True)
            theme.mark(b, nav=True)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, key=key: self.set_way(key))
            help_window.tag(b, "#make-way" if key == "auto" else "#by-hand")  # (F1: the entry named as it reads)
            tabs.addWidget(b)
            self.way_btns[key] = b
        tabs.addStretch(1)
        v.addLayout(tabs)

        def grid(parent=None):
            g = QGridLayout(parent) if parent is not None else QGridLayout()
            g.setContentsMargins(0, 0, 0, 0)
            g.setHorizontalSpacing(12)
            g.setVerticalSpacing(8)
            g.setColumnStretch(2, 1)
            self._way_grids.append(g)
            return g

        def name(words):
            lab = label(words, wrap=False)
            self._way_labels.append(lab)
            return lab
        self._way_labels, self._way_grids = [], []
        g = grid()
        g.addWidget(name("Your EQ app"), 0, 0)
        self.app_combo = SearchCombo()
        self.app_combo.addItem("Choose your EQ app (its limits are kept)", "")
        self.app_combo.addItem("Not listed, or not sure: any filters, an Equalizer APO file", "other")
        for a in sorted(self.meta.get("eq_apps", []), key=lambda a: a["name"].lower()):
            self.app_combo.addItem(f"{a['name']}  ·  {', '.join(a['platforms'])}", a["key"])
        self.app_combo.sort_items(pinned=2)  # ("Choose your EQ app" and "Not listed" on top: it was among the apps)
        self.app_combo.activated.connect(lambda _i: self.choose_app(self.app_combo.currentData()))
        help_window.tag(self.app_combo, "eq_app")
        # (as wide as its choices, capped as every drop-down of a form, and Method's under it: it took the card's
        # whole width, UI-RULES 26)
        self.app_combo.setMaximumWidth(CHOICE_MOST)
        g.addWidget(self.app_combo, 0, 1, 1, 3, Qt.AlignLeft)
        self.app_note = label("", "muted")
        self.app_note.setTextFormat(Qt.RichText)
        self.app_note.linkActivated.connect(self.open_link)
        g.addWidget(self.app_note, 1, 1, 1, 3)
        v.addLayout(g)

        # Automatically: the method, the search, Run (its rows in a part of their own, shown with its tab: what a run
        # shows of itself, its progress and Cancel, keeps its own state meanwhile)
        self.auto_w = QWidget()
        g = grid(self.auto_w)
        g.addWidget(name("Method"), 0, 0)
        self.mode_combo = SearchCombo()
        for k, mode in self.meta["modes"].items():
            self.mode_combo.addItem(mode, k)
        self.mode_combo.sort_items()
        self.mode_combo.activated.connect(lambda _i: self.set_mode(self.mode_combo.currentData()))
        help_window.tag(self.mode_combo, "slot:method")
        g.addWidget(self.mode_combo, 0, 1)
        self.mode_hint = label("", "muted")  # (under its box, as Your EQ app's note: UI-RULES 26)
        g.addWidget(self.mode_hint, 1, 1, 1, 3)
        g.addWidget(name("Search"), 2, 0, Qt.AlignTop)  # (level with the first of its lines)
        # what a run tries and how long it takes (one search since 1.0.8, the user's ask 2026-10-13: with the EQ grown
        # one filter at a time Quick, Standard and Thorough all took seconds, and one search trying every limit they
        # tried found the fewest filters for every IEM tested: the benchmarks in BENCHMARKS.md)
        self.sa = QWidget()
        sa = QVBoxLayout(self.sa)
        sa.setContentsMargins(0, 0, 0, 0)
        sa.setSpacing(2)
        self.estimate = label("", wrap=False)
        sa.addWidget(self.estimate)
        self.sa_what = label("", "muted")
        sa.addWidget(self.sa_what)
        self.sa.setAccessibleName("Search")
        help_window.tag(self.sa, "sa")
        g.addWidget(self.sa, 2, 1, 1, 3)
        run_row = QHBoxLayout()
        run_row.setSpacing(10)
        self.run_btn = QPushButton("Run")
        theme.mark(self.run_btn, primary=True)
        icons.put(self.run_btn, "run")
        self.run_btn.setMinimumWidth(120)
        self.run_btn.clicked.connect(lambda: self.run())  # (not self.run: Qt hands it the click's checked=False as retry)
        # (Cancel at the row's end while a run goes on: beside Run it pushed Run several… along, and in Run's place a
        # double-click on Run cancelled the run it started, UI-RULES 13)
        self.cancel_btn = QPushButton("Cancel")
        icons.put(self.cancel_btn, "cancel")
        self.cancel_btn.clicked.connect(lambda: self.svc.call("/api/cancel"))
        self.cancel_btn.hide()
        self.queue_btn = QPushButton("Run several…")
        icons.put(self.queue_btn, "list")  # (every button in the row with its symbol, UI-RULES 9)
        self.queue_btn.setToolTip("EQs for several IEMs or targets in one go, each saved and kept in History")
        self.queue_btn.clicked.connect(self.open_queue)
        help_window.tag(self.queue_btn, "#queue")
        run_row.addWidget(self.run_btn)
        run_row.addWidget(self.queue_btn)
        run_row.addWidget(self.cancel_btn)
        run_row.addStretch(1)
        g.addLayout(run_row, 3, 1, 1, 3)
        self.progress = QProgressBar()  # (Windows 11's thin line: its height is the theme's)
        self.progress.setTextVisible(False)
        self.progress.hide()
        g.addWidget(self.progress, 4, 1, 1, 3)
        self.progress_text = label("", "muted")
        self.progress_text.hide()  # (shown with words only: an empty band under Run before any run, say_progress)
        g.addWidget(self.progress_text, 5, 1, 1, 3)
        v.addWidget(self.auto_w)

        # By hand: an EQ of your own, from where it starts (an EQ's sources in their order, then each device's
        # profile: fill_hand_sources), then Start, as Run (its words with "…" when it asks first: a file, pasted lines)
        self.hand_w = QWidget()
        g = grid(self.hand_w)
        g.addWidget(name("Start from"), 0, 0)
        self.hand_source = SearchCombo()
        self.hand_source.setAccessibleName("Start from")
        self.hand_source.setMaximumWidth(CHOICE_MOST)  # (as Your EQ app's: UI-RULES 26)
        self.hand_source.currentIndexChanged.connect(lambda _i: self.hand_source_changed())
        help_window.tag(self.hand_source, "#by-hand")
        g.addWidget(self.hand_source, 0, 1, 1, 3, Qt.AlignLeft)
        self.hand_src_note = label("", "muted")
        g.addWidget(self.hand_src_note, 1, 1, 1, 3)
        start_row = QHBoxLayout()
        start_row.setSpacing(10)
        self.hand_start = QPushButton("Start")
        theme.mark(self.hand_start, primary=True)  # (By hand's main action, as Run is Automatically's)
        icons.put(self.hand_start, "edit")
        self.hand_start.setMinimumWidth(120)
        self.hand_start.clicked.connect(self.start_from_source)
        help_window.tag(self.hand_start, "#hand-start")
        start_row.addWidget(self.hand_start)
        start_row.addStretch(1)
        g.addLayout(start_row, 2, 1, 1, 3)
        g.addWidget(label("Then change its filters on the EQ graph (drag a handle) or in the table under your result.",
                          "muted"), 3, 1, 1, 3)
        v.addWidget(self.hand_w)
        self.show_settings()
        self.fill_hand_sources()
        self.set_way((self.sw.s.get("make_way") if self.sw is not None else None) or "auto", remember=False)
        self._line_up_ways()
        return box

    def _line_up_ways(self):
        """Your EQ app's grid and each way's: one label column, as wide as the widest label of the three (as
        forms.line_up_together does for forms)."""
        for lab in self._way_labels:
            lab.ensurePolished()  # (in the theme's text size)
        width = max(lab.sizeHint().width() for lab in self._way_labels)
        for g in self._way_grids:
            g.setColumnMinimumWidth(0, width)

    def _result_card(self):
        self.result_box = box = QGroupBox("Your result")
        v = QVBoxLayout(box)
        self.res_title = label("")
        theme.mark(self.res_title, eqtitle=True)
        head = QHBoxLayout()
        head.addWidget(self.res_title, 1)
        # (an EQ by hand's Close, on the card's title line, as a card closed from its top: under Runs this session's
        # Remove, at the same edge, the two read as one, UI-RULES 14)
        self.hand_close = QPushButton("Close")
        icons.put(self.hand_close, "close")
        self.hand_close.setToolTip("Back to what was shown before this EQ by hand (changed, it stays in Runs this "
                                   "session)")
        help_window.tag(self.hand_close, "#hand-close")  # (a screen reader's name too: "Close (an EQ by hand)")
        self.hand_close.clicked.connect(self.close_by_hand)
        self.hand_close.hide()
        head.addWidget(self.hand_close, 0, Qt.AlignTop)
        v.addLayout(head)
        self.res_sub = label("", "muted")
        v.addWidget(self.res_sub)
        chips = QHBoxLayout()
        self.chips = {k: label("", "chip", wrap=False) for k in ("filters", "error", "preamp", "boost", "maxq")}
        for k, c in self.chips.items():
            chips.addWidget(c)
            if k != "filters":  # (F1 on a chip: its entry in Help)
                help_window.tag(c, {"error": "res.error", "preamp": "res.preamp", "boost": "res.boost",
                                    "maxq": "res.maxq"}[k])
        chips.addStretch(1)
        v.addLayout(chips)
        self.pick_lab = label("", "muted")  # (the audible pick: the target reached inaudibly, or as close as it gets)
        self.pick_lab.hide()
        v.addWidget(self.pick_lab)
        self.site_row = QWidget()  # (the website methods: what to type into squiglink's AutoEQ panel)
        sr = QHBoxLayout(self.site_row)
        sr.setContentsMargins(0, 0, 0, 0)
        self.site_text = label("")
        self.site_text.setTextFormat(Qt.RichText)
        sr.addWidget(self.site_text, 1)
        self.site_use = QPushButton("Use in single run")
        self.site_use.setToolTip("Copy these values into Website AutoEQ: one run (they become yours)")
        self.site_use.clicked.connect(self.use_in_single_run)
        sr.addWidget(self.site_use)
        self.site_row.hide()
        v.addWidget(self.site_row)
        self.runs_row = QWidget()
        rr = QHBoxLayout(self.runs_row)
        rr.setContentsMargins(0, 0, 0, 0)
        self.runs_lab = label("Runs this session", wrap=False)
        rr.addWidget(self.runs_lab)
        self.runs_combo = NameCombo()  # (as wide as its room, a long run's line ending in "…": it made the page wider)
        self.runs_combo.setMinimumContentsLength(20)
        self.runs_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.runs_combo.setAccessibleName("Runs this session")
        self.runs_combo.setToolTip("Every run of this session (and EQs shown from History): choose one to see it again")
        self.runs_combo.activated.connect(lambda _i: self.choose_run(self.runs_combo.currentData()))
        rr.addWidget(self.runs_combo, 1)
        drop = QPushButton("Remove")
        icons.put(drop, "remove")
        drop.setToolTip("Take the run shown off this list (Undo puts it back; History keeps what you saved)")
        drop.clicked.connect(self.remove_run)
        rr.addWidget(drop)
        self.runs_row.hide()
        v.addWidget(self.runs_row)
        pick = QHBoxLayout()
        self.count_lab = label("Fewer or more filters", wrap=False)  # (hidden with its list for an EQ made by hand)
        pick.addWidget(self.count_lab)
        self.count_combo = SearchCombo()
        help_window.tag(self.count_combo, "fcounts")
        self.count_combo.activated.connect(lambda _i: self.show_result(self.count_combo.currentData()))
        pick.addWidget(self.count_combo, 1)
        self.all_btn = QPushButton("All results…")
        self.all_btn.setToolTip("Every result the run tried, and the error by filter count and max Q")
        self.all_btn.clicked.connect(self.open_all_results)
        pick.addWidget(self.all_btn)
        self.cmp_btn = QPushButton("Compare…")
        self.cmp_btn.setToolTip("Two EQs side by side: this one, other filter counts or runs, or History's")
        self.cmp_btn.clicked.connect(self.open_compare)
        help_window.tag(self.cmp_btn, "#compare-results")
        # (an EQ by hand, its filter counts' list hidden: Compare… at its own width and still at the row's right end,
        # where a run's card has it; it sat alone at the left)
        pick.addStretch(0)
        pick.addWidget(self.cmp_btn)
        v.addLayout(pick)
        tools = QHBoxLayout()
        self.view_btns = {}
        for key, name in (("table", "Table"), ("sliders", "Sliders")):
            b = QPushButton(name)
            b.setCheckable(True)
            theme.mark(b, nav=True)
            b.clicked.connect(lambda _=False, k=key: self.set_view(k))
            tools.addWidget(b)
            self.view_btns[key] = b
        tools.addSpacing(12)
        for text, symbol, fn, tip in (("Add filter", "add", self.add_filter, "A new filter at 1 kHz, 0 dB"),
                                      ("Sort", "sort", self.sort_filters, "Put the filters in order of frequency"),
                                      ("Revert", "undo", self.revert, "Back to the filters as the run made them")):
            b = QPushButton(text)
            icons.put(b, symbol)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            tools.addWidget(b)
            if text == "Revert":
                self.revert_btn = b
        tools.addStretch(1)
        self.retry_btn = QPushButton("Retry from these filters")
        icons.put(self.retry_btn, "refresh")  # (every button in the row with its symbol, UI-RULES 9)
        help_window.tag(self.retry_btn, "f_retry")
        self.retry_btn.setToolTip("Best fit again, starting from these filters (this run only: your settings stay)")
        retry_menu = QMenu(self.retry_btn)
        retry_menu.addAction("Fine-tune them", lambda: self.run(retry={"filters": self.active(), "add": False}))
        retry_menu.addAction("Keep them, add filters", lambda: self.run(retry={"filters": self.active(), "add": True}))
        self.retry_btn.setMenu(retry_menu)
        tools.addWidget(self.retry_btn)
        v.addLayout(tools)
        from ui.filter_editor import FilterEditor
        self.editor = FilterEditor(self.meta.get("limits", {}), lambda t: self.status(t, 6000))
        self.editor.changed.connect(self.live_update)
        v.addWidget(self.editor)
        self.EDIT, self.ORIG = [], []
        name_row = QHBoxLayout()
        self.name_lab = label("File name", wrap=False)
        name_row.addWidget(self.name_lab)
        self.name_edit = QLineEdit()
        help_window.tag(self.name_edit, "x_name")
        self.name_edit.setPlaceholderText("named for you")
        self.name_edit.textEdited.connect(lambda _t: self.name_edit.setProperty("auto", False))  # (yours from now)
        name_row.addWidget(self.name_edit, 1)
        v.addLayout(name_row)
        # (the card's labelled rows in one column, as a form's: each box started at its own label's end, UI-RULES 26)
        labs = (self.runs_lab, self.count_lab, self.name_lab)
        for lab in labs:
            lab.ensurePolished()  # (the theme's text size: its width in it)
        wide = max(lab.sizeHint().width() for lab in labs)
        for lab in labs:
            lab.setMinimumWidth(wide)
        self.formats_line = label("", "muted")
        v.addWidget(self.formats_line)
        btns = QHBoxLayout()
        save = QPushButton("Save filters")
        theme.mark(save, primary=True)
        icons.put(save, "save")
        save.clicked.connect(self.save)
        self.use_btn = QPushButton("Use on device")
        icons.put(self.use_btn, "devices")  # (the Devices screen's own symbol)
        self.use_menu = QMenu(self.use_btn)
        self.use_menu.aboutToShow.connect(self._fill_use_menu)
        self.use_btn.setMenu(self.use_menu)
        help_window.tag(self.use_btn, "#use-try")
        report = QPushButton("Report")
        icons.put(report, "report")  # (every button in the row with its symbol, UI-RULES 9)
        report.setToolTip("An HTML page with the graph and the filters, opened in your browser (saved in your Saved EQs folder)")
        report.clicked.connect(lambda: self.report(open_it=True))
        folder = QPushButton("Open the Saved EQs folder")
        icons.put(folder, "folder")  # (Windows' folder symbol, as every button that opens a folder has)
        folder.clicked.connect(lambda: self.svc.call("/api/open", {"what": "output"}))
        keep = QPushButton("Keep to compare")
        icons.put(keep, "pin")  # (Windows 11's pin, where the words had 📌)
        keep.setToolTip("Add this EQ to your EQs to compare for this IEM: on the graph, and in Listen to hear it")
        keep.clicked.connect(lambda: self.listen.add_selected())
        copy = QPushButton("Copy")
        icons.put(copy, "copy")
        copy.setToolTip("Copy the filters as Equalizer APO / squiglink text")
        copy.clicked.connect(lambda: self.copy_filters(self.active(), self.stats()["preamp_raw"]))
        for b in (save, copy, self.use_btn, keep, report, folder):
            btns.addWidget(b)
        btns.addStretch(1)
        v.addLayout(btns)
        box.hide()
        return box
