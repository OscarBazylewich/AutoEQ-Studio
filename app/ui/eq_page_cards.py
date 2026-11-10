"""Make an EQ's cards (a part of EqPage, ui/eq_page.py): the page laid out once the EQ part has opened, top to
bottom (the UI audit, 2026-11-08): Target and Measurement in one card (a row each, Find…, Add…, the Target's
Adjust…), the graph (its title, Trace a graph image…, History…, View, Y range, Channels, Hide previews), Make the EQ
(Your EQ app, then the tabs Automatically and Manually: Method and Settings to try, or Start from; then the rows that
open, Settings and More settings (ui/eq_settings.py); then Calculate or Start), Your result (its numbers, the
filters, File name, Save filters, Use on device) and Listen (ui/listen.py). This is the file to restyle Make an EQ in.
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QMenu, QProgressBar, QPushButton, QScrollArea, QStackedWidget,
                               QVBoxLayout, QWidget)

from ui import help_window, icons, theme
from ui.bubble import InfoMark
from ui.eq_page_parts import TICKS, CurveNames, Elided, NameCombo, PairTitle, SameWidth, combo_width, hz, label
from ui.forms import CHOICE_MOST
from ui.search_combo import SearchCombo


# Number of filters' longest line (eq_page_result.show_result: a count, its error, the pick's words), for its width
COUNT_LONGEST = "00 filters  ·  00.00 dB  ✓ selected for you"


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
        from ui.window_parts import scroll_bar_in_margin
        scroll_bar_in_margin(scroll, col)  # (the cards' right edge where the other screens' is: the bar in the space)
        self.page_area = scroll  # (the page's own scroll area: what floats over the page goes on its view, eq_page_live)
        scroll.hide()  # ("Opening the EQ part…" until the page is whole)
        self.layout().addWidget(scroll)  # (in its place first: the cards then go straight into it, never moved)
        yield "the page's frame"
        # (Target and Measurement first, above the graph: the first screen has the lists, and the graph is directly
        # under them as you select; the UI audit, 2026-11-08)
        col.addWidget(self._select_card())
        yield "Target, Measurement"
        col.addWidget(self._graph_card())
        yield "the graph"
        col.addWidget(self._eq_card())
        yield "Make the EQ"
        from ui.eq_settings import EqSettings
        settings = EqSettings(self)
        # (Adjust… onto the Target row; Settings and More settings, rows that open in Make the EQ, in their place)
        yield from settings.build_parts(self.settings_slot, self.target_row, self.target_under)
        self.settings = settings
        self.measurement_pad.follow(settings.adjust_btn)  # (the two drop-downs end at one x: Adjust… is the Target's)
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
        self.hist_btn.setToolTip("Your EQs in History (the app keeps them when you close it)")
        self.hist_btn.clicked.connect(lambda: self.open_history(False))
        head.addWidget(self.hist_btn)
        v.addLayout(head)
        opts = QHBoxLayout()  # (the graph's views, as AutoEQ Local's: kept between sessions)
        g = self.sw.s.get("graph") or {}
        opts.addWidget(label("View", wrap=False))
        self.view_combo = SearchCombo()
        self.view_combo.addItem("Frequency response", "abs")
        self.view_combo.addItem("Difference from target", "rel")
        self.view_combo.sort_items()
        self.view_combo.setCurrentIndex(max(0, self.view_combo.findData(g.get("view", "abs"))))
        self.view_combo.activated.connect(lambda _i: self.set_graph_option(view=self.view_combo.currentData()))
        help_window.tag(self.view_combo, "#opt-view")
        opts.addWidget(self.view_combo)
        opts.addWidget(label("Y range", wrap=False))
        self.yrange_combo = SearchCombo()
        for k, name in (("auto", "Automatic"), ("30", "30 dB"), ("40", "40 dB"), ("50", "50 dB"), ("60", "60 dB")):
            self.yrange_combo.addItem(name, k)
        self.yrange_combo.sort_items(pinned=1)  # ("Auto" on top, the user's ask)
        self.yrange_combo.setCurrentIndex(max(0, self.yrange_combo.findData(g.get("y", "auto"))))
        self.yrange_combo.activated.connect(lambda _i: self.set_graph_option(y=self.yrange_combo.currentData()))
        help_window.tag(self.yrange_combo, "#opt-y")
        opts.addWidget(self.yrange_combo)
        self.channels_chk = QCheckBox("Channels")
        self.channels_chk.setChecked(bool(g.get("channels")))
        self.channels_chk.toggled.connect(lambda on: self.set_graph_option(channels=on))
        help_window.tag(self.channels_chk, "#opt-ch")
        opts.addWidget(self.channels_chk)
        # (a view of the graph, with the others: it popped into the header between Trace and History, moving them)
        self.clear_prev_btn = QPushButton("Hide previews")  # (Find…'s Preview and Hide, and the legend's words)
        icons.put(self.clear_prev_btn, "hide")
        self.clear_prev_btn.setToolTip("Remove the previews (dotted lines from Find…) from the graph")
        self.clear_prev_btn.clicked.connect(self.clear_previews)
        self.clear_prev_btn.hide()
        opts.addWidget(self.clear_prev_btn)
        opts.addStretch(1)
        self.hover_lab = Elided("")  # (never wider than its room: "…" at its end on a narrow window)
        theme.mark(self.hover_lab, role="muted")
        opts.addWidget(self.hover_lab)
        v.addLayout(opts)
        # (the curves' names in a line between the views and the graph, not on the curves: the UI audit, 2026-11-08;
        # pyqtgraph's legend still gathers them, hidden)
        self.curve_names = CurveNames()
        v.addWidget(self.curve_names)
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
        self.legend.setVisible(False)
        self.plot.getAxis("left").setLabel("dB")
        self.eqplot.getAxis("left").setLabel("EQ dB")
        # (the EQ graph is where the filters are dragged: ui/eq_page_handles.py; a double-click adds one)
        self.eqplot.scene().sigMouseClicked.connect(self.eq_graph_clicked)
        self.eqplot.setAccessibleName("EQ graph")
        # (with no EQ: words in its middle that tell what a double-click there does; the UI audit, 2026-11-08)
        self.eq_empty = QLabel("Double-click here to add a filter and start a manual EQ.", self.eqplot)
        self.eq_empty.setAlignment(Qt.AlignCenter)
        self.eq_empty.setWordWrap(True)  # (on a narrow graph: two lines, never cut)
        self.eq_empty.setAttribute(Qt.WA_TransparentForMouseEvents)
        theme.mark(self.eq_empty, role="muted")
        self.eqplot.installEventFilter(self)  # (the words follow its size: eventFilter, eq_page)
        self.eqplot.setToolTip("Drag a handle: frequency and gain. Mouse wheel on a handle: Q. Right-click a handle: type, "
                               "Remove. Double-click an empty area: a new filter.")
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

    def _select_card(self):
        """Target and Measurement, the 2 inputs of the EQ, in one card (the UI audit, 2026-11-08: two cards used
        approximately 90 px more): a row each, their labels in a column at the left, as Make the EQ's. Under a row, its
        information (a note; the Target's adjustments; Other measurements of this model… and History's line)."""
        card = QFrame()
        theme.mark(card, card=True)
        g = QGridLayout(card)
        g.setContentsMargins(4, 4, 4, 4)  # (a card frame's padding and these: a card's inset)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(4)
        g.setColumnStretch(1, 1)
        for i, kind in enumerate(("target", "measurement")):
            g.addWidget(label("Target" if kind == "target" else "Measurement", wrap=False), 2 * i, 0)
            g.addWidget(self._file_row(kind), 2 * i, 1)
            under = QWidget()
            u = QVBoxLayout(under)
            u.setContentsMargins(0, 0, 0, 6 if kind == "target" else 0)
            u.setSpacing(4)
            g.addWidget(under, 2 * i + 1, 1)
            note = label("", "muted")
            note.hide()  # (shown when it has words: eq_page_files.show_inputs)
            u.addWidget(note)
            setattr(self, f"{kind}_note", note)
            setattr(self, f"{kind}_under", u)
            if kind == "measurement":
                other = QPushButton("Other measurements of this model…")
                other.setToolTip("Find all the measurements of this model and the best one for your target")
                other.clicked.connect(self.open_other_measurements)
                u.addWidget(other, 0, Qt.AlignLeft)
                row2 = QHBoxLayout()
                self.eqd_before = label("", wrap=False)
                row2.addWidget(self.eqd_before)
                self.eqd_show = QPushButton("Show in History…")  # (it opens History, this IEM's: UI-RULES 11, 16)
                self.eqd_show.setToolTip("History, with the EQs that you made for this IEM")
                self.eqd_show.clicked.connect(lambda: self.open_history(True))
                row2.addWidget(self.eqd_show)
                row2.addStretch(1)
                u.addLayout(row2)
                self.eqd_before.hide()
                self.eqd_show.hide()
        self.select_box = card
        return card

    def _file_row(self, kind):
        """A row of the Target and Measurement card: the list (a long name ends in "…"), Find… and Add… (the
        Target's Adjust… comes after them: eq_settings). It is target_box or measurement_box."""
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        combo = NameCombo()  # (a name longer than its room ends in "…": never cut off)
        combo.setMinimumContentsLength(20)
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.setAccessibleName("Target" if kind == "target" else "Measurement")
        combo.activated.connect(lambda _i, k=kind: self._file_chosen(k))
        help_window.tag(combo, "slot:" + kind)
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
        if kind == "measurement":
            # (room as wide as the Target's Adjust… after Add…, so that the two drop-downs end at one x at every
            # width: the Measurement's went on 105 px further; a code review, 2026-11-10)
            self.measurement_pad = SameWidth()
            row.addWidget(self.measurement_pad)
        setattr(self, f"{kind}_combo", combo)
        setattr(self, f"{kind}_box", box)
        if kind == "target":
            self.target_row = row
        return box

    def _eq_card(self):
        """Make the EQ (the UI audit, 2026-11-08): Your EQ app first, as it is for the 2 ways; then the tabs
        Automatically and Manually (their words lined up with the labels; the card as high with either tab: nothing
        under it moves); then only that way's steps (Method and Settings to try, or Start from); then the rows that
        open, Settings and More settings (eq_settings: for the 2 ways, above the button that uses them); then the way's
        main button (Calculate with Queue…, or Start), so the result card comes directly after it. The gray notes are
        behind an ⓘ after their labels (bubble.InfoMark). Its grids keep one label column (_line_up_ways)."""
        self.eq_box = box = QGroupBox("Make the EQ")
        v = QVBoxLayout(box)
        v.setSpacing(8)

        def grid(parent=None):
            g = QGridLayout(parent) if parent is not None else QGridLayout()
            g.setContentsMargins(0, 0, 0, 0)
            g.setHorizontalSpacing(12)
            g.setVerticalSpacing(8)
            g.setColumnStretch(2, 1)
            self._way_grids.append(g)
            return g

        def name(words, info=None):
            """A label of the column, with its ⓘ after it when it has one."""
            if info is None:
                lab = label(words, wrap=False)
                self._way_labels.append(lab)
                return lab
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            h.addWidget(label(words, wrap=False))
            h.addWidget(info)
            h.addStretch(1)
            self._way_labels.append(w)
            return w
        self._way_labels, self._way_grids = [], []
        g = grid()
        self.app_note = InfoMark("", "Your EQ app", links=self.open_link)
        g.addWidget(name("Your EQ app", self.app_note), 0, 0)
        self.app_combo = SearchCombo()
        self.app_combo.addItem("Select your EQ app", "")
        self.app_combo.addItem("Not in the list, or not sure: no limits, an Equalizer APO file", "other")
        for a in sorted(self.meta.get("eq_apps", []), key=lambda a: a["name"].lower()):
            self.app_combo.addItem(f"{a['name']}  ·  {', '.join(a['platforms'])}", a["key"])
        self.app_combo.sort_items(pinned=2)  # ("Select your EQ app" and "Not in the list" on top: it was among the apps)
        self.app_combo.activated.connect(lambda _i: self.choose_app(self.app_combo.currentData()))
        help_window.tag(self.app_combo, "eq_app")
        self.app_combo.setFixedWidth(CHOICE_MOST)  # (one width for the drop-downs: their edges on one line, UI-RULES 26)
        g.addWidget(self.app_combo, 0, 1, 1, 3, Qt.AlignLeft)
        v.addLayout(g)
        tabs = QHBoxLayout()
        tabs.setSpacing(20)
        self.way_btns = {}
        for key, words, tip in (("auto", "Automatically", "AutoEQ adjusts the filters for the target and your EQ "
                                 "app: you select the method, then click Calculate"),
                                ("hand", "Manually", "You make the filters: start from an empty EQ or from an EQ "
                                 "that you have. Then change them on the EQ graph.")):
            b = QPushButton(words)
            b.setCheckable(True)
            theme.mark(b, nav=True, flush=True)  # (its words start at the labels' left edge: the UI audit)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, key=key: self.set_way(key))
            help_window.tag(b, "#make-way" if key == "auto" else "#by-hand")  # (F1: the entry named as it reads)
            tabs.addWidget(b)
            self.way_btns[key] = b
        tabs.addStretch(1)
        v.addLayout(tabs)

        # the way's own steps: a stack, as high as the higher one (the card keeps one height with either tab)
        self.way_stack = QStackedWidget()
        self.auto_w = QWidget()
        g = grid(self.auto_w)
        self.mode_hint = InfoMark("", "Method")
        g.addWidget(name("Method", self.mode_hint), 0, 0)
        self.mode_combo = SearchCombo()
        for k, mode in self.meta["modes"].items():
            self.mode_combo.addItem(mode, k)
        self.mode_combo.sort_items()
        self.mode_combo.activated.connect(lambda _i: self.set_mode(self.mode_combo.currentData()))
        help_window.tag(self.mode_combo, "slot:method")
        self.mode_combo.setFixedWidth(CHOICE_MOST)
        g.addWidget(self.mode_combo, 0, 1, 1, 3, Qt.AlignLeft)
        g.addWidget(name("Settings to try"), 1, 0)
        # what a run tries and how long it takes, in one short line ("36 EQs, 1 to 32 filters · approximately 20 s");
        # the whole text in its tooltip and in Help (the UI audit, 2026-11-08: 2 lines, 5 numbers, 3 settings)
        self.sa = QWidget()
        sa = QVBoxLayout(self.sa)
        sa.setContentsMargins(0, 0, 0, 0)
        self.estimate = label("", wrap=False)
        theme.mark(self.estimate, role="section")
        sa.addWidget(self.estimate)
        self.sa_what = self.estimate  # (the Guide's name for it)
        self.sa.setAccessibleName("Settings to try")
        help_window.tag(self.sa, "sa")
        g.addWidget(self.sa, 1, 1, 1, 3)
        self.way_stack.addWidget(self.auto_w)
        self.hand_w = QWidget()
        g = grid(self.hand_w)
        self.hand_src_note = InfoMark("", "Start from")
        g.addWidget(name("Start from", self.hand_src_note), 0, 0)
        self.hand_source = SearchCombo()
        self.hand_source.setAccessibleName("Start from")
        self.hand_source.setFixedWidth(CHOICE_MOST)  # (as Your EQ app's: UI-RULES 26)
        self.hand_source.currentIndexChanged.connect(lambda _i: self.manual_source_changed())
        help_window.tag(self.hand_source, "#by-hand")
        g.addWidget(self.hand_source, 0, 1, 1, 3, Qt.AlignLeft)
        g.setRowStretch(1, 1)
        self.way_stack.addWidget(self.hand_w)
        v.addWidget(self.way_stack)

        # Settings and More settings: rows that open, for the 2 ways (eq_settings puts them here in its own steps)
        self.settings_slot = QVBoxLayout()
        self.settings_slot.setSpacing(2)
        v.addLayout(self.settings_slot)

        # the way's main button: Calculate (with Queue…, and Cancel while it runs) or Start
        self.go_stack = QStackedWidget()
        go_auto = QWidget()
        ga = QVBoxLayout(go_auto)
        ga.setContentsMargins(0, 4, 0, 0)
        ga.setSpacing(6)
        run_row = QHBoxLayout()
        run_row.setSpacing(10)
        self.run_btn = QPushButton("Calculate")
        theme.mark(self.run_btn, primary=True)
        icons.put(self.run_btn, "run")
        self.run_btn.setMinimumWidth(120)
        self.run_btn.clicked.connect(lambda: self.run())  # (not self.run: Qt hands it the click's checked=False as retry)
        # (Cancel at the row's end while a run goes on: beside Calculate it pushed Queue… along, and in Calculate's
        # place a double-click on Calculate cancelled the run it started, UI-RULES 13)
        self.cancel_btn = QPushButton("Cancel")
        icons.put(self.cancel_btn, "cancel")
        self.cancel_btn.clicked.connect(lambda: self.svc.call("/api/cancel"))
        self.cancel_btn.hide()
        self.queue_btn = QPushButton("Queue…")
        icons.put(self.queue_btn, "list")  # (every button in the row with its symbol, UI-RULES 9)
        self.queue_btn.setToolTip("EQs for more than one IEM or target, one after the other: each one saved and kept in "
                                  "History")
        self.queue_btn.clicked.connect(self.open_queue)
        help_window.tag(self.queue_btn, "#queue")
        run_row.addWidget(self.run_btn)
        run_row.addWidget(self.queue_btn)
        run_row.addWidget(self.cancel_btn)
        run_row.addStretch(1)
        ga.addLayout(run_row)
        self.progress = QProgressBar()  # (Windows 11's thin line: its height is the theme's)
        self.progress.setTextVisible(False)
        self.progress.hide()
        ga.addWidget(self.progress)
        self.progress_text = label("", "muted")
        self.progress_text.hide()  # (shown with words only: an empty band under Run before any run, say_progress)
        ga.addWidget(self.progress_text)
        ga.addStretch(1)
        self.go_stack.addWidget(go_auto)
        go_hand = QWidget()
        gh = QHBoxLayout(go_hand)
        gh.setContentsMargins(0, 4, 0, 0)
        gh.setSpacing(10)
        self.hand_start = QPushButton("Start")
        theme.mark(self.hand_start, primary=True)  # (Manually's main action, as Calculate is Automatically's)
        icons.put(self.hand_start, "edit")
        self.hand_start.setMinimumWidth(120)
        self.hand_start.clicked.connect(self.start_from_source)
        help_window.tag(self.hand_start, "#hand-start")
        gh.addWidget(self.hand_start, 0, Qt.AlignTop)
        gh.addStretch(1)
        self.go_stack.addWidget(go_hand)
        v.addWidget(self.go_stack)
        self.show_settings()
        self.fill_manual_sources()
        self.set_way((self.sw.s.get("make_way") if self.sw is not None else None) or "auto", remember=False)
        self._line_up_ways()
        return box

    def _line_up_ways(self):
        """Your EQ app's grid and each way's (3 grids): one label column, as wide as the widest of their labels (Your
        EQ app, Method, Settings to try, Start from), so that their boxes start at one x."""
        for lab in self._way_labels:
            lab.ensurePolished()  # (in the theme's text size)
        width = max(lab.sizeHint().width() for lab in self._way_labels)
        for g in self._way_grids:
            g.setColumnMinimumWidth(0, width)

    def _result_card(self):
        self.result_box = box = QGroupBox("Your result")
        v = QVBoxLayout(box)
        self.res_title = label("")
        theme.mark(self.res_title, eqname=True)  # (a title in a card: 14 px bold)
        head = QHBoxLayout()
        head.addWidget(self.res_title, 1)
        # (an EQ by hand's Close, on the card's title line, as a card closed from its top: under Runs this session's
        # Remove, at the same edge, the two read as one, UI-RULES 14)
        self.hand_close = QPushButton("Close")
        icons.put(self.hand_close, "close")
        self.hand_close.setToolTip("Show the EQ from before this manual EQ again (a changed EQ stays in EQs that you "
                                   "made)")
        help_window.tag(self.hand_close, "#hand-close")  # (a screen reader's name too: "Close (an EQ by hand)")
        self.hand_close.clicked.connect(self.close_manual)
        self.hand_close.hide()
        head.addWidget(self.hand_close, 0, Qt.AlignTop)
        v.addLayout(head)
        self.res_sub = label("", "muted")
        v.addWidget(self.res_sub)
        # (the error first, as a large number, the error without EQ under it, then the other numbers as tags; no
        # Filters tag: the number of filters is in the line above and in Number of filters. The UI audit, 2026-11-08)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        err = QWidget()
        ev = QVBoxLayout(err)
        ev.setContentsMargins(0, 0, 12, 0)
        ev.setSpacing(0)
        big = label("", wrap=False)
        theme.mark(big, errbig=True)
        ev.addWidget(big)
        self.err_noeq = label("", "muted", wrap=False)
        ev.addWidget(self.err_noeq)
        chips.addWidget(err)
        self.chips = {"error": big}
        self.chips.update({k: label("", "chip", wrap=False) for k in ("preamp", "boost", "maxq")})
        for k, c in self.chips.items():
            if k != "error":
                chips.addWidget(c, 0, Qt.AlignVCenter)
            help_window.tag(c, {"error": "res.error", "preamp": "res.preamp", "boost": "res.boost",
                                "maxq": "res.maxq"}[k])  # (F1 on a number: its entry in Help)
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
        self.site_use = QPushButton("Use these settings")
        self.site_use.setToolTip("Copy these values into Website AutoEQ: one set (they become your values)")
        self.site_use.clicked.connect(self.use_these_settings)
        sr.addWidget(self.site_use)
        self.site_row.hide()
        v.addWidget(self.site_row)
        self.runs_row = QWidget()
        rr = QHBoxLayout(self.runs_row)
        rr.setContentsMargins(0, 0, 0, 0)
        self.runs_lab = label("EQs that you made", wrap=False)
        rr.addWidget(self.runs_lab)
        self.runs_combo = NameCombo()  # (as wide as its room, a long run's line ending in "…": it made the page wider)
        self.runs_combo.setMinimumContentsLength(20)
        self.runs_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.runs_combo.setAccessibleName("EQs that you made")
        self.runs_combo.setToolTip("The EQs that you made since you started the app, and EQs from History: select one to "
                                   "show it again")
        self.runs_combo.activated.connect(lambda _i: self.choose_run(self.runs_combo.currentData()))
        rr.addWidget(self.runs_combo, 1)
        drop = QPushButton("Remove")
        icons.put(drop, "remove")
        drop.setToolTip("Remove the shown EQ from this list. Undo adds it again, and History keeps the EQs that you saved.")
        drop.clicked.connect(self.remove_run)
        rr.addWidget(drop)
        self.runs_row.hide()
        v.addWidget(self.runs_row)
        pick = QHBoxLayout()
        self.count_lab = label("Number of filters", wrap=False)  # (hidden with its list for an EQ made by hand)
        pick.addWidget(self.count_lab)
        self.count_combo = SearchCombo()
        help_window.tag(self.count_combo, "fcounts")
        self.count_combo.activated.connect(lambda _i: self.show_result(self.count_combo.currentData()))
        # (one width, as wide as its longest line can be: All results… and Compare… directly after it, UI-RULES 33.
        # As wide as the lines of each result, it changed width from one result to the next and moved them; a code
        # review, 2026-11-10)
        self.count_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.count_combo.setFixedWidth(min(CHOICE_MOST, combo_width(self.count_combo, COUNT_LONGEST)))
        pick.addWidget(self.count_combo)
        self.all_btn = QPushButton("All results…")
        self.all_btn.setToolTip("All the results that the app tried, and the error for each filter count and maximum Q")
        self.all_btn.clicked.connect(self.open_all_results)
        pick.addWidget(self.all_btn)
        self.cmp_btn = QPushButton("Compare…")
        self.cmp_btn.setToolTip("Two EQs at the same time: this one, other filter counts, other EQs that you made, or EQs "
                                "from History")
        self.cmp_btn.clicked.connect(self.open_compare)
        help_window.tag(self.cmp_btn, "#compare-results")
        pick.addWidget(self.cmp_btn)
        pick.addStretch(1)
        v.addLayout(pick)
        tools = QHBoxLayout()
        self.view_btns = {}
        for key, name in (("table", "Table"), ("sliders", "Sliders")):
            b = QPushButton(name)
            b.setCheckable(True)
            theme.mark(b, nav=True, flush=True)  # (its words at the card's left edge, as every tab's: the UI audit)
            b.clicked.connect(lambda _=False, k=key: self.set_view(k))
            tools.addWidget(b)
            tools.addSpacing(8)
            self.view_btns[key] = b
        tools.addSpacing(12)
        for text, symbol, fn, tip in (("Add filter", "add", self.add_filter, "A new filter at 1 kHz, 0 dB"),
                                      ("Sort", "sort", self.sort_filters, "Sort the filters by frequency"),
                                      ("Undo all", "undo", self.undo_all, "Use the initial filters again (as the app made them)")):
            b = QPushButton(text)
            icons.put(b, symbol)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            tools.addWidget(b)
            if text == "Undo all":
                self.revert_btn = b
        tools.addSpacing(12)
        # (the graph floating over the page as you edit, while it's out of sight: on to start with, kept: eq_page_live)
        self.live_check = QCheckBox("Show the graph while you edit")
        self.live_check.setChecked(self.live_graph_on())
        self.live_check.setToolTip("If the graph is not in view, the app shows a copy of it on top of the page while you "
                                   "change the filters")
        self.live_check.toggled.connect(self.set_live_graph_on)
        help_window.tag(self.live_check, "#live-graph")
        tools.addWidget(self.live_check)
        tools.addStretch(1)
        self.retry_btn = QPushButton("Calculate from these filters")
        icons.put(self.retry_btn, "refresh")  # (every button in the row with its symbol, UI-RULES 9)
        help_window.tag(self.retry_btn, "f_retry")
        self.retry_btn.setToolTip("Best fit again, from these filters (only for this EQ: your settings do not change)")
        retry_menu = QMenu(self.retry_btn)
        retry_menu.addAction("Adjust them", lambda: self.run(retry={"filters": self.enabled_filters(), "add": False}))
        retry_menu.addAction("Keep them and add filters", lambda: self.run(retry={"filters": self.enabled_filters(), "add": True}))
        self.retry_btn.setMenu(retry_menu)
        tools.addWidget(self.retry_btn)
        v.addLayout(tools)
        from ui.filter_editor import FilterEditor
        self.editor = FilterEditor(self.meta.get("limits", {}), lambda t: self.status(t, 6000))
        self.editor.changed.connect(self.live_update)
        self.editor.changed.connect(self.request_live_graph)  # (after the page has drawn the change: its curves current)
        v.addWidget(self.editor)
        self.EDIT, self.ORIG = [], []
        name_row = QHBoxLayout()
        self.name_lab = label("File name", wrap=False)
        name_row.addWidget(self.name_lab)
        self.name_edit = QLineEdit()
        help_window.tag(self.name_edit, "x_name")
        self.name_edit.setPlaceholderText("automatic name")
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
        self.save_btn = save = QPushButton("Save filters")
        theme.mark(save, primary=True)
        icons.put(save, "save")
        save.clicked.connect(self.save_filters)
        self.use_btn = QPushButton("Use on device")
        icons.put(self.use_btn, "devices")  # (the Devices screen's own symbol)
        self.use_menu = QMenu(self.use_btn)
        self.use_menu.aboutToShow.connect(self._fill_use_menu)
        self.use_btn.setMenu(self.use_menu)
        help_window.tag(self.use_btn, "#use-try")
        self.report_btn = report = QPushButton("Report")
        icons.put(report, "report")  # (every button in the row with its symbol, UI-RULES 9)
        report.setToolTip("An HTML page with the graph and the filters, in your browser (also in your Saved EQs folder)")
        report.clicked.connect(lambda: self.report(open_it=True))
        folder = QPushButton("Open the Saved EQs folder")
        icons.put(folder, "folder")  # (Windows' folder symbol, as every button that opens a folder has)
        folder.clicked.connect(lambda: self.svc.call("/api/open", {"what": "output"}))
        keep = QPushButton("Keep to compare")
        icons.put(keep, "pin")  # (Windows 11's pin, where the words had 📌)
        keep.setToolTip("Add this EQ to Your EQs to compare for this IEM: on the graph, and in Listen, where you can hear "
                         "it")
        keep.clicked.connect(lambda: self.listen.add_selected())
        copy = QPushButton("Copy")
        icons.put(copy, "copy")
        copy.setToolTip("Copy the filters as Equalizer APO / squiglink text")
        copy.clicked.connect(lambda: self.copy_filters(self.enabled_filters(), self.stats()["preamp_raw"]))
        # (two rows by function, the user's answer, 2026-11-08: they were 6 buttons in one row for different jobs. Row
        # 1, under File name: the files (Save filters, the accent; Copy; Open the Saved EQs folder). Row 2: this EQ on a
        # device, in Listen, in a report)
        for b in (save, copy, folder):
            btns.addWidget(b)
        btns.addStretch(1)
        v.addLayout(btns)
        use_row = QHBoxLayout()
        for b in (self.use_btn, keep, report):
            use_row.addWidget(b)
        use_row.addStretch(1)
        v.addSpacing(6)
        v.addLayout(use_row)
        box.hide()
        return box
