"""The "Make an EQ" screen: AutoEQ Local's page, natively. One column, as there:
- the graph: your measurement, the target and the measurement with the EQ; under it the EQ itself (0 dB = no change)
- Target | Measurement: what's in the app (your Targets and Measurements folders), and Add… for files on this PC
- Make the EQ: your EQ app (its limits are kept, its file is what Save writes), the method, the search (what a run
  tries and how long it takes), Run, and the run's progress
- the result: its numbers, its filters (Fewer or more filters: the best result for each count), Save filters (the
  files your EQ app needs, under the File name), and Use on device: the EQ becomes a device's profile, switched on
- by the graph's title: Trace image (ui/trace_window.py: a picture of a graph becomes a measurement or target) and
  History; under the result, Listen (ui/listen.py)

Everything it does goes through eq.service (AutoEQ Local's page's requests, called directly); slow ones run off the
window's thread (ui.tasks). The EQ part is imported only when this screen is first opened (the tray stays light),
after AutoEQ Local's files are brought over (eq.bring_over: once, on the first opening).
Its Guide: ui\\guide.py (the top bar's Guide); F1 on a control: its entry in Help.
"""
import hashlib
import json
import os
import tempfile
import time

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

import textfile
from ui import help_window, tasks, theme
from ui.search_combo import SearchCombo

FORMAT_NAMES = {"apo": "Equalizer APO / squiglink (.txt)", "graphic": "GraphicEQ for Wavelet (.txt)",
                "poweramp": "Poweramp (.json)", "uapp": "USB Audio Player PRO (.xml)", "soundsource": "SoundSource (.txt)",
                "voicemeeter": "Voicemeeter (.xml)", "rockbox": "Rockbox (.cfg)", "convolution": "impulse response (.wav)",
                "report": "a report (.html)"}  # (AutoEQ Local's export.js)
MODE_SHORT = {"site_single": "Website AutoEQ", "site_sweep": "Website sweep", "best_fit": "Best fit"}
MODE_HINT = {"best_fit": "For EQ apps and devices: the closest match", "site_sweep": "For the squiglink / listener800 website",
             "site_single": "Checks one set of website values"}
TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]


def _label(text="", role=None, wrap=True):
    lab = QLabel(text)
    lab.setWordWrap(wrap)
    if role:
        theme.mark(lab, role=role)
    return lab


def _hz(v):
    return f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"


def file_base_name(device, target, layout_name, mode, n):
    """"<IEM> to <target> - <layout or method> <n>f" (AutoEQ Local's export.js fileBaseName)."""
    what = layout_name.replace(" / ", ", ") if layout_name else {"site_single": "site AutoEQ", "site_sweep": "site AutoEQ",
                                                                 "best_fit": "best fit"}.get(mode, "EQ")
    return f"{device} to {target} - {what} {n}f"


class _Notices(QObject):
    """A message from a worker thread, said on the window's thread (a queued signal)."""
    said = Signal(str)


def _modal(dlg):
    """A window over the page until it's closed, then let go (each kept all its rows for the rest of the session)."""
    dlg.exec()
    dlg.deleteLater()


class EqPage(QWidget):
    def __init__(self, sw, status):
        super().__init__()
        self.sw, self.status = sw, status  # (the per-device part, for Use on device; status(text): the window's line)
        self.svc = None
        self.S = self.meta = self.curves = self.analysis = self.auto = self.run_result = None
        self.sel = None  # the result shown (its id)
        self.session_runs = []  # this session's runs (and EQs shown from History), newest last: chosen again on the card
        self.history, self.session, self.runs = [], format(int(time.time()), "x"), 0
        self.previews = []  # [(key, name, values)]: curves shown from the search, not in use
        self.preview_bodies = {}  # key: what /api/preview was asked (to work them out again with new settings)
        self.started = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.loading = _label("Opening the EQ part…", "muted")
        self.loading.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.loading)
        self._save_timer = QTimer(self, singleShot=True, interval=400, timeout=self._save_settings)
        self.save_settings_soon = self._save_timer.start  # (for other windows: Sources)
        self._auto_timer = QTimer(self, singleShot=True, interval=150, timeout=self.refresh_auto)
        self._poll = QTimer(self, interval=400, timeout=self._poll_job)
        self.setAcceptDrops(True)
        # (in a text box, "/" and Ctrl+V type and paste as usual: they take their keys first)
        QShortcut(QKeySequence("/"), self, lambda: self.svc and self.find("measurement"),
                  context=Qt.WidgetWithChildrenShortcut)
        QShortcut(QKeySequence.Paste, self, self.paste_picture, context=Qt.WidgetWithChildrenShortcut)
        theme.on_change(self._recolour)

    # ---------------------------------------------------------------- opening (once)
    def start(self):
        """The first time the screen is shown: bring AutoEQ Local's files over (once), load the EQ part, its state."""
        if self.started:
            return
        self.started = True
        # your files still where an older copy kept them: a move offered before the EQ part takes its folders; then a
        # new copy's (or a new folder's) samples and database lists put in place
        import paths
        from ui import your_files
        try:
            your_files.offer_move(self, self.sw.set)
            paths.first_start()
        except OSError:  # (said in the log; the EQ part opens with what's there)
            import traceback
            traceback.print_exc()

        def load():
            from eq import bring_over
            brought = bring_over.bring_over() if bring_over.needed() else []
            from eq import databases, library, settings as eq_settings
            cfg = eq_settings.load()
            # (as AutoEQ Local did at launch: the saved lists, which also say which rig a target was made for; online
            # new ones every few days. Offline nothing is fetched: net.check in databases)
            library.start_scan(cfg)
            databases.start_refresh(cfg)
            from eq import service
            return brought, service, service.call("/api/state"), service.call("/api/history").get("entries", [])

        def loaded(res, err):
            if err:
                self.loading.setText(f"The EQ part couldn't open: {err}\nThe details are in data\\app.log.")
                return
            brought, self.svc, st, self.history = res
            from eq import service
            self._notices = _Notices()
            self._notices.said.connect(lambda t: QMessageBox.warning(self, "AutoEQ Studio", t))
            service.SET_ASIDE.append(self._notices.said.emit)
            if st.get("set_aside"):
                self._notices.said.emit(st["set_aside"])
            if "error" in st:
                self.loading.setText(f"The EQ part couldn't open: {st['error']}")
                return
            self.meta, self.S = st, st["settings"]
            self._build()
            if brought:
                self.status(f"Brought over {len(brought)} files from AutoEQ Local (your settings, History, targets, "
                            "measurements and saved EQs); AutoEQ Local keeps its own.", 12000)
            self.show_inputs(st["inputs"])
            self.load_curves()
            self._lists_timer = QTimer(self, interval=500, timeout=self._lists_loaded)
            self._lists_timer.start()
        tasks.background(load, loaded)

    def _lists_loaded(self):
        """Once the database lists are in: the rig tags and the curves again (a target's rig may only be known from
        them, and with it the rig conversion)."""
        from eq import databases
        if databases.status()["loading"]:
            return
        self._lists_timer.stop()
        st = self.svc.call("/api/state")
        if "inputs" in st:
            self.show_inputs(st["inputs"])
        self.load_curves()

    # ---------------------------------------------------------------- building
    def _build(self):
        self.loading.hide()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setSpacing(12)
        col.setContentsMargins(14, 14, 14, 14)
        col.addWidget(self._graph_card())
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self._file_card("target"))
        row.addWidget(self._file_card("measurement"))
        col.addLayout(row)
        col.addWidget(self._notice_row())
        col.addWidget(self._eq_card())
        from ui.eq_settings import EqSettings
        self.settings = EqSettings(self)
        self.target_box.layout().addWidget(self.settings.adjust_row)  # (Adjust, under the target: AutoEQ Local's)
        self.target_box.layout().addWidget(self.settings.adjust_panel)
        col.addWidget(self.settings.fold)
        col.addWidget(self.settings.adv)
        col.addWidget(self._result_card())
        from ui.listen import Listen
        self.listen = Listen(self)
        self.listen.hide()  # (once there are curves)
        col.addWidget(self.listen)
        col.addStretch(1)
        scroll.setWidget(body)
        self.layout().addWidget(scroll)

    def _graph_card(self):
        card = QFrame()
        theme.mark(card, card=True)
        v = QVBoxLayout(card)
        head = QHBoxLayout()
        self.graph_title = _label("", wrap=False)
        theme.mark(self.graph_title, role="brand")
        head.addWidget(self.graph_title, 1)
        self.chip_noeq = _label("", "chip", wrap=False)
        head.addWidget(self.chip_noeq)
        trace = QPushButton("✎ Trace image")
        trace.setToolTip("Make a frequency response from a picture of a graph")
        trace.clicked.connect(self.open_trace)
        head.addWidget(trace)
        self.clear_prev_btn = QPushButton("Hide shown curves")
        self.clear_prev_btn.setToolTip("Take the curves shown from Find… (dotted) off the graph")
        self.clear_prev_btn.clicked.connect(self.clear_previews)
        self.clear_prev_btn.hide()
        head.addWidget(self.clear_prev_btn)
        hist = QPushButton("History")
        hist.setToolTip("Your past EQs, kept between sessions")
        hist.clicked.connect(lambda: self.open_history(False))
        head.addWidget(hist)
        v.addLayout(head)
        opts = QHBoxLayout()  # (the graph's views, as AutoEQ Local's: kept between sessions)
        g = self.sw.s.get("graph") or {}
        opts.addWidget(_label("View", wrap=False))
        self.view_combo = SearchCombo()
        self.view_combo.addItem("Absolute", "abs")
        self.view_combo.addItem("Relative to target", "rel")
        self.view_combo.sort_items()
        self.view_combo.setCurrentIndex(max(0, self.view_combo.findData(g.get("view", "abs"))))
        self.view_combo.activated.connect(lambda _i: self.graph_option(view=self.view_combo.currentData()))
        help_window.tag(self.view_combo, "#opt-view")
        opts.addWidget(self.view_combo)
        opts.addWidget(_label("Y range", wrap=False))
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
        opts.addStretch(1)
        self.hover_lab = _label("", "muted", wrap=False)
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
            p.getAxis("bottom").setTicks([[(np.log10(t), _hz(t).replace(" Hz", "").replace(" kHz", "k")) for t in TICKS]])
            p.setXRange(np.log10(20), np.log10(20000), padding=0)
        self.legend = self.plot.addLegend(offset=(10, 10))
        self.plot.getAxis("left").setLabel("dB")
        self.eqplot.getAxis("left").setLabel("EQ dB")
        v.addWidget(self.plot)
        v.addWidget(self.eqplot)
        self.graph_note = _label("", "muted")
        v.addWidget(self.graph_note)
        self._recolour(draw=False)
        return card

    def _notice_row(self):
        """What was just done to the files (Use, an average, a move), with Undo (AutoEQ Local's toasts)."""
        self.notice = QFrame()
        theme.mark(self.notice, card=True)
        h = QHBoxLayout(self.notice)
        h.setContentsMargins(12, 6, 8, 6)
        self.notice_text = _label("")
        h.addWidget(self.notice_text, 1)
        self.notice_undo = QPushButton("Undo")
        h.addWidget(self.notice_undo)
        x = QPushButton("✕")
        x.setAccessibleName("Close the notice")
        x.setToolTip("Close")
        x.clicked.connect(self.notice.hide)
        h.addWidget(x)
        self.notice.hide()
        self._notice_timer = QTimer(self, singleShot=True, interval=20000, timeout=self.notice.hide)
        return self.notice

    def notify(self, text, undo=None):
        self.notice_text.setText(text)
        if getattr(self, "_undo_connected", False):  # (only what was connected: no warning)
            self.notice_undo.clicked.disconnect()
        self._undo_connected = bool(undo)
        if undo:
            self.notice_undo.clicked.connect(lambda: (self.notice.hide(), undo()))
        self.notice_undo.setVisible(bool(undo))
        self.notice.show()
        self._notice_timer.start()

    def _file_card(self, kind):
        box = QGroupBox("Target" if kind == "target" else "Measurement")
        v = QVBoxLayout(box)
        combo = SearchCombo()
        combo.setMinimumContentsLength(20)
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.activated.connect(lambda _i, k=kind: self._file_chosen(k))
        help_window.tag(combo, "slot:" + kind)
        row = QHBoxLayout()
        row.addWidget(combo, 1)
        find = QPushButton("Find…")
        find.setToolTip("Search your files, this PC and the online databases")
        find.clicked.connect(lambda _=False, k=kind: self.find(k))
        row.addWidget(find)
        add = QPushButton("Add…")
        add.setToolTip("Add target files from this PC" if kind == "target" else
                       "Add measurement files from this PC (a set: L/R, seatings)")
        add.clicked.connect(lambda _=False, k=kind: self.add_files(k))
        row.addWidget(add)
        v.addLayout(row)
        note = _label("", "muted")
        v.addWidget(note)
        if kind == "measurement":
            other = QPushButton("Other measurements of this model…")
            other.setToolTip("Find every measurement of this model and see which suits your target best")
            other.clicked.connect(self.compare)
            v.addWidget(other, 0, Qt.AlignLeft)
            row2 = QHBoxLayout()
            self.eqd_before = _label("", wrap=False)
            row2.addWidget(self.eqd_before)
            self.eqd_show = QPushButton("Show")
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
        self.eq_box = box = QGroupBox("Make the EQ")
        g = QGridLayout(box)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        g.addWidget(_label("Your EQ app", wrap=False), 0, 0)
        self.app_combo = SearchCombo()
        self.app_combo.addItem("Choose your EQ app (its limits are kept)", "")
        self.app_combo.addItem("Not listed, or not sure: any filters, an Equalizer APO file", "other")
        for a in sorted(self.meta.get("eq_apps", []), key=lambda a: a["name"].lower()):
            self.app_combo.addItem(f"{a['name']}  ·  {', '.join(a['platforms'])}", a["key"])
        self.app_combo.sort_items(pinned=1)  # ("Choose your EQ app" on top)
        self.app_combo.activated.connect(lambda _i: self.choose_app(self.app_combo.currentData()))
        help_window.tag(self.app_combo, "eq_app")
        g.addWidget(self.app_combo, 0, 1, 1, 3)
        self.app_note = _label("", "muted")
        self.app_note.setTextFormat(Qt.RichText)
        self.app_note.linkActivated.connect(self.open_link)
        g.addWidget(self.app_note, 1, 1, 1, 3)
        g.addWidget(_label("Method", wrap=False), 2, 0)
        self.mode_combo = SearchCombo()
        for k, name in self.meta["modes"].items():
            self.mode_combo.addItem(name, k)
        self.mode_combo.sort_items()
        self.mode_combo.activated.connect(lambda _i: self.set_mode(self.mode_combo.currentData()))
        help_window.tag(self.mode_combo, "slot:method")
        g.addWidget(self.mode_combo, 2, 1)
        self.mode_hint = _label("", "muted")
        g.addWidget(self.mode_hint, 2, 2, 1, 2)
        g.addWidget(_label("Search", wrap=False), 3, 0)
        # what a run tries and how long it takes (one search since 1.0.8, the user's ask 2026-10-13: with the EQ grown
        # one filter at a time Quick, Standard and Thorough all took seconds, and one search trying every limit they
        # tried found the fewest filters for every IEM tested: the benchmarks in BENCHMARKS.md)
        self.sa = QWidget()
        sa = QVBoxLayout(self.sa)
        sa.setContentsMargins(0, 0, 0, 0)
        sa.setSpacing(2)
        self.estimate = _label("", wrap=False)
        sa.addWidget(self.estimate)
        self.sa_what = _label("", "muted")
        sa.addWidget(self.sa_what)
        self.sa.setAccessibleName("Search")
        help_window.tag(self.sa, "sa")
        g.addWidget(self.sa, 3, 1, 1, 3)
        run_row = QHBoxLayout()
        run_row.setSpacing(10)
        self.run_btn = QPushButton("Run")
        theme.mark(self.run_btn, primary=True)
        self.run_btn.setMinimumWidth(120)
        self.run_btn.clicked.connect(lambda: self.run())  # (not self.run: Qt hands it the click's checked=False as retry)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(lambda: self.svc.call("/api/cancel"))
        self.cancel_btn.hide()
        self.queue_btn = QPushButton("Run several…")
        self.queue_btn.setToolTip("EQs for several IEMs or targets in one go, each saved and kept in History")
        self.queue_btn.clicked.connect(self.open_queue)
        help_window.tag(self.queue_btn, "#queue")
        run_row.addWidget(self.run_btn)
        run_row.addWidget(self.cancel_btn)
        run_row.addWidget(self.queue_btn)
        run_row.addStretch(1)
        g.addLayout(run_row, 6, 1, 1, 3)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.hide()
        g.addWidget(self.progress, 7, 1, 1, 3)
        self.progress_text = _label("", "muted")
        g.addWidget(self.progress_text, 8, 1, 1, 3)
        g.setColumnStretch(2, 1)
        self.show_settings()
        return box

    def _result_card(self):
        self.result_box = box = QGroupBox("Your result")
        v = QVBoxLayout(box)
        self.res_title = _label("")
        theme.mark(self.res_title, role="brand")
        v.addWidget(self.res_title)
        self.res_sub = _label("", "muted")
        v.addWidget(self.res_sub)
        chips = QHBoxLayout()
        self.chips = {k: _label("", "chip", wrap=False) for k in ("filters", "error", "preamp", "boost", "maxq")}
        for k, c in self.chips.items():
            chips.addWidget(c)
            if k != "filters":  # (F1 on a chip: its entry in Help)
                help_window.tag(c, {"error": "res.error", "preamp": "res.preamp", "boost": "res.boost",
                                    "maxq": "res.maxq"}[k])
        chips.addStretch(1)
        v.addLayout(chips)
        self.pick_lab = _label("", "muted")  # (the audible pick: the target reached inaudibly, or as close as it gets)
        self.pick_lab.hide()
        v.addWidget(self.pick_lab)
        self.site_row = QWidget()  # (the website methods: what to type into squiglink's AutoEQ panel)
        sr = QHBoxLayout(self.site_row)
        sr.setContentsMargins(0, 0, 0, 0)
        self.site_text = _label("")
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
        rr.addWidget(_label("Runs this session", wrap=False))
        self.runs_combo = SearchCombo()
        self.runs_combo.setAccessibleName("Runs this session")
        self.runs_combo.setToolTip("Every run of this session (and EQs shown from History): choose one to see it again")
        self.runs_combo.activated.connect(lambda _i: self.choose_run(self.runs_combo.currentData()))
        rr.addWidget(self.runs_combo, 1)
        drop = QPushButton("Remove")
        drop.setToolTip("Take the run shown off this list (History keeps what you saved)")
        drop.clicked.connect(self.remove_run)
        rr.addWidget(drop)
        self.runs_row.hide()
        v.addWidget(self.runs_row)
        pick = QHBoxLayout()
        pick.addWidget(_label("Fewer or more filters", wrap=False))
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
        for text, fn, tip in (("+ Add filter", self.add_filter, "A new filter at 1 kHz, 0 dB"),
                              ("Sort", self.sort_filters, "Put the filters in order of frequency"),
                              ("Revert", self.revert, "Back to the filters as the run made them")):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            tools.addWidget(b)
            if text == "Revert":
                self.revert_btn = b
        tools.addStretch(1)
        self.retry_btn = QPushButton("Retry from these filters")
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
        name_row.addWidget(_label("File name", wrap=False))
        self.name_edit = QLineEdit()
        help_window.tag(self.name_edit, "x_name")
        self.name_edit.setPlaceholderText("named for you")
        self.name_edit.textEdited.connect(lambda _t: self.name_edit.setProperty("auto", False))  # (yours from now)
        name_row.addWidget(self.name_edit, 1)
        v.addLayout(name_row)
        self.formats_line = _label("", "muted")
        v.addWidget(self.formats_line)
        btns = QHBoxLayout()
        save = QPushButton("Save filters")
        theme.mark(save, primary=True)
        save.clicked.connect(self.save)
        self.use_btn = QPushButton("Use on device")
        self.use_menu = QMenu(self.use_btn)
        self.use_menu.aboutToShow.connect(self._fill_use_menu)
        self.use_btn.setMenu(self.use_menu)
        help_window.tag(self.use_btn, "#use-try")
        report = QPushButton("Report")
        report.setToolTip("An HTML page with the graph and the filters, opened in your browser (saved in your Saved EQs folder)")
        report.clicked.connect(lambda: self.report(open_it=True))
        folder = QPushButton("Open the Saved EQs folder")
        folder.clicked.connect(lambda: self.svc.call("/api/open", {"what": "output"}))
        keep = QPushButton("📌 Keep to compare")
        keep.setToolTip("Add this EQ to your EQs to compare for this IEM: on the graph, and in Listen to hear it")
        keep.clicked.connect(lambda: self.listen.add_selected())
        copy = QPushButton("Copy")
        copy.setToolTip("Copy the filters as Equalizer APO / squiglink text")
        copy.clicked.connect(lambda: self.copy_filters(self.active(), self.stats()["preamp_raw"]))
        for b in (save, copy, self.use_btn, keep, report, folder):
            btns.addWidget(b)
        btns.addStretch(1)
        v.addLayout(btns)
        box.hide()
        return box

    # ---------------------------------------------------------------- settings
    def _save_settings(self):
        def done(res, err):
            if err or (res or {}).get("error"):
                self.status(f"Couldn't save the settings: {err or res['error']}", 8000)
        s = self.S
        tasks.background(lambda: self.svc.call("/api/settings", {"settings": s}), done)

    def changed(self, curves=False):
        """A setting changed: save it soon, show it, ask the automatic settings again (and reload the curves)."""
        self._save_timer.start()
        self.show_settings()
        if curves:
            self.load_curves()
        else:
            self._auto_timer.start()
        if self.current()[1]:
            self.live_update()  # (e.g. the pre-amp's rounding and headroom: the result's numbers follow at once)
        elif self.curves and not curves:
            self.draw()  # (e.g. your own filters, drawn as “With your filters”)

    def show_settings(self):
        S = self.S
        i = self.app_combo.findData(S.get("eq_app") or "")
        self.app_combo.setCurrentIndex(max(0, i))
        self.app_note.setText(self.app_note_text(S.get("eq_app") or ""))
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(S["mode"])))
        self.mode_hint.setText(MODE_HINT.get(S["mode"], ""))
        on = [FORMAT_NAMES[k] for k in list(FORMAT_NAMES) if S["export"].get(k)]
        if hasattr(self, "formats_line"):
            self.formats_line.setText("Save filters writes: " + ", ".join(on) + "." if on else
                                      "Save filters writes nothing yet: choose your EQ app, or tick a file in "
                                      "Advanced › Saved files.")
        if hasattr(self, "settings"):
            self.settings.refresh()

    def app_note_text(self, key):
        """The line under Your EQ app for an app (its limits, how to load its file, its source), as rich text."""
        a = self.eq_app(key) if key not in ("", "other") else None
        if a:
            import html
            own = self.S["best_fit"].get("layout") == a.get("layout") or a.get("kind") == "site"                 or key != (self.S.get("eq_app") or "")  # (another app, as the Guide shows it: its own limits)
            text = html.escape(f"{a.get('note') or a.get('summary')}"
                               + (" Its band shapes aren't stated, so the app's result can differ a little." if a.get("approx") else "")
                               + f" {a.get('how', '')}"
                               + ("" if own else " (You've changed Best fit's layout since, so its limits aren't the app's "
                                  "any more.)")).strip()
            return text + (f' <a href="{html.escape(a["source"])}">Source</a>' if a.get("source") else "")
        return ("Any filters, as many as needed, saved as an Equalizer APO file, which many apps can read."
                if key == "other" else
                "Which app or device will play the EQ? Its limits (bands, gain, Q) are kept, and Save writes its file.")

    def open_link(self, url):
        """A website link (online only: offline the app never connects, net.py)."""
        import net
        if net.offline():
            self.status("Offline: switch to Online (top right) to open websites.", 6000)
            return
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(url))

    def eq_app(self, key=None):
        key = self.S.get("eq_app") if key is None else key
        return next((a for a in self.meta.get("eq_apps", []) if a["key"] == key), None)

    def choose_app(self, key):
        """Your EQ app: its limits and its file (AutoEQ Local's settings.js applyEqApp): the method that makes its
        EQ, its layout, a graphic EQ's slider range and steps, and Save writing exactly its file."""
        S, a = self.S, self.eq_app(key)
        S["eq_app"] = key
        S["mode"] = "site_sweep" if a and a["kind"] == "site" else "best_fit"
        S["best_fit"]["layout"] = a["layout"] if a else "any"
        if a and a["kind"] == "graphic":
            self.apply_bands(a)
        file = a["file"] if a else "apo"
        from eq import exports
        for f in exports.FORMATS:
            S["export"][f] = f == file
        self.changed()

    def apply_bands(self, a):
        """A graphic EQ app's sliders: its range and steps, or the defaults when it states none (settings.js)."""
        S, lim = self.S, self.meta.get("limits", {})
        d = self.meta["defaults"]["best_fit"]["bands"]
        g = a.get("bands_gain") or [d["gain_min"], d["gain_max"]]
        S["best_fit"]["bands"]["gain_min"] = max(g[0], lim.get("best_fit.bands.gain_min", {}).get("min", -1e9))
        S["best_fit"]["bands"]["gain_max"] = min(g[1], lim.get("best_fit.bands.gain_max", {}).get("max", 1e9))
        S["best_fit"]["bands"]["step"] = a.get("bands_step") or d["step"]

    def set_mode(self, mode):
        self.S["mode"] = mode
        self.changed()

    # ---------------------------------------------------------------- the files
    def show_inputs(self, inputs):
        self.inputs = inputs
        t = self.target_combo
        t.clear()
        from ui.search_combo import natural_key
        for n in sorted(inputs["targets"], key=lambda n: natural_key(os.path.splitext(n)[0])):  # (A to Z)
            t.addItem(os.path.splitext(n)[0], n)
        t.setCurrentIndex(max(0, t.findData(inputs["active_target"])))
        self.target_note.setText("" if inputs["targets"] else "No targets yet: Add… one from this PC.")
        from eq import inputs as eq_inputs
        groups = {}
        for m in sorted(inputs["measurements"], key=lambda m: natural_key(m["name"])):
            groups.setdefault(eq_inputs.device_name([m["name"]]), []).append(m)
        self.groups = groups = dict(sorted(groups.items(), key=lambda kv: natural_key(kv[0])))  # (A to Z)
        mc = self.measurement_combo
        mc.clear()
        current = None
        for dev, files in groups.items():
            mc.addItem(f"{dev}  ({len(files)} file{'s' if len(files) > 1 else ''})", dev)
            if any(f["included"] for f in files):
                current = current or dev
        mc.setCurrentIndex(max(0, mc.findData(current)))
        if not groups:
            self.measurement_note.setText("No measurements yet: Add… one from this PC (L and R, or several seatings).")
        else:
            on = [f["name"] for f in groups.get(current, []) if f["included"]]
            rigs = {inputs.get("rigs", {}).get(n) for n in on} - {None, ""}
            self.measurement_note.setText(f"{len(on)} file{'s' if len(on) != 1 else ''} used"
                                          + (f" · measured on {', '.join(sorted(rigs))}" if rigs else ""))

    def _file_chosen(self, kind):
        S = self.S
        if kind == "target":
            S["files"]["active_target"] = self.target_combo.currentData()
        else:
            dev = self.measurement_combo.currentData()
            mine = {f["name"] for f in self.groups.get(dev, [])}
            S["files"]["excluded"] = [m["name"] for m in self.inputs["measurements"] if m["name"] not in mine]
        self._save_files()

    def _save_files(self, after=None):
        def done(res, err):
            if err or (res or {}).get("error"):
                self.status(f"Couldn't use that file: {err or res['error']}", 8000)
                return
            if res.get("inputs"):
                self.show_inputs(res["inputs"])
            self.load_curves()
            if after:
                after()
        s = self.S
        tasks.background(lambda: self.svc.call("/api/settings", {"settings": s}), done)

    def add_files(self, kind):
        start = os.path.expanduser("~")
        files, _ = QFileDialog.getOpenFileNames(self, "Add target files" if kind == "target" else "Add measurement files",
                                                start, "Frequency response (*.txt *.csv *.frd *.tsv);;All files (*)")
        if not files:
            return
        said, read = [], []
        for f in files:
            try:
                read.append({"name": os.path.basename(f), "content": textfile.read(f)})
            except OSError as e:
                said.append(f"{os.path.basename(f)}: {e}")
        # (a measurement's files as one set: one number for all when names are taken, so they stay one device;
        # targets each on their own)
        for batch in ([read] if kind == "measurement" else [[x] for x in read]) if read else []:
            r = self.svc.call("/api/files/add", {"kind": kind, "files": batch, "settings": self.S})
            if r.get("error"):
                said.append(f"{', '.join(x['name'] for x in batch)}: {r['error']}")
            elif r.get("settings"):
                self.S = r["settings"]
        if said:
            QMessageBox.warning(self, "Not added", "\n\n".join(said))
        st = self.svc.call("/api/state")
        if "inputs" in st:
            self.S = st["settings"]
            self.show_inputs(st["inputs"])
            self.show_settings()
            self.load_curves()

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
        tasks.background(lambda: self.svc.call("/api/curves", {"settings": s}), done)

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
        tasks.background(lambda: self.svc.call("/api/analysis", {"settings": s}), done)

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

    # ---------------------------------------------------------------- running
    def run(self, retry=None):
        """Run with the settings; retry: {"filters", "add"} (Best fit from the filters shown, this run only)."""
        if not self.curves:
            QMessageBox.information(self, "Run", "Add a target and at least one measurement first.")
            return
        if retry is not None and not retry["filters"]:
            QMessageBox.information(self, "Retry", "There are no filters to start from: add one, or switch one on.")
            return
        if self.S["auto"]["enabled"]:
            self.refresh_auto()  # (the values for exactly these settings)
        body = {"settings": self.S, "mode": "best_fit" if retry else self.S["mode"], "analysis": self.analysis}
        if retry:
            body["retry"] = retry
        r = self.svc.call("/api/run", body)
        if r.get("error"):
            QMessageBox.warning(self, "Run", r["error"])
            return
        self.run_btn.setEnabled(False)
        self.queue_btn.setEnabled(False)  # (a queue started now failed every pair: one run at a time)
        self.retry_btn.setEnabled(False)
        self.cancel_btn.show()
        self.progress.setValue(0)
        self.progress.show()
        self.progress_text.setText("Starting…")
        self._poll.start()

    def _poll_job(self):
        j = self.svc.call("/api/job")
        total = j.get("total") or 0
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(j.get("done") or 0)
        self.progress_text.setText(f"{j.get('message') or ''}" + (f" · {round(j['elapsed'])} s" if j.get("elapsed") else ""))
        if j.get("status") == "running":
            return
        self._poll.stop()
        self.svc.call("/api/job", {"ack": True})
        self.run_btn.setEnabled(True)
        self.queue_btn.setEnabled(True)
        self.retry_btn.setEnabled(True)
        self.cancel_btn.hide()
        self.progress.hide()
        if j.get("status") == "done":
            self.runs += 1
            self.run_result = dict(j["result"], n=self.runs)
            self.keep_run(self.run_result)
            self.progress_text.setText(f"Done in {j['result'].get('seconds')} s.")
            self.name_edit.clear()
            self.show_result(j["result"]["pick"])
            self.record(False)
        elif j.get("status") == "error":
            self.progress_text.setText("")
            QMessageBox.warning(self, "Run failed", j.get("message") or "The run failed.")
        elif j.get("status") == "cancelled":
            self.progress_text.setText("Cancelled.")

    # ---------------------------------------------------------------- the result
    def show_result(self, rid):
        run = self.run_result
        if not run:
            return
        self.sel = run["_sel"] = rid
        r = next(x for x in run["results"] if x["id"] == rid)
        self.ORIG = [{"enabled": True, "type": f.get("type") or "PK", "freq": f["freq"], "gain": f["gain"], "q": f["q"]}
                     for f in r["filters"]]
        self.EDIT = [dict(f) for f in self.ORIG]
        self.res_sub.setText((f"From History ({run['when']})" if run.get("history") else f"Run {run.get('n', 1)}")
                             + f" · {self.run_label(run, r)} · made for {run.get('device')} → {run.get('target_name')}")
        note = self.pick_note(run, r)
        self.pick_lab.setText(note)
        self.pick_lab.setVisible(bool(note))
        self.chips["error"].setToolTip("How far the EQ'd measurement stays from the target, on average, in the scored "
                                       "range (lower is closer)")
        self.chips["preamp"].setToolTip("How much the whole EQ is turned down so its boosts never clip: the filters' "
                                        "boosts added up where they overlap")
        # the best result for each filter count (the pick for its own count), as AutoEQ Local's chips
        by_n = {}
        for x in run["results"]:
            had = by_n.get(x["n_filters"])
            if not had or x["id"] == run["pick"] or (had["id"] != run["pick"] and x["rms"] < had["rms"]):
                by_n[x["n_filters"]] = x
        shown = next((x for x in run["results"] if x["id"] == rid), None)
        if shown:  # (one chosen in All results… or Compare: its own count's entry, so the list says what's shown)
            by_n[shown["n_filters"]] = shown
        self.count_combo.clear()
        for n, x in sorted(by_n.items()):
            self.count_combo.addItem(f"{n} filters  ·  {x['rms']:.2f} dB" + ("  ✓ picked for you" if x["id"] == run["pick"] else ""),
                                     x["id"])
        self.count_combo.setCurrentIndex(max(0, self.count_combo.findData(rid)))
        self.count_combo.sort_items()
        self.count_combo.setEnabled(len(by_n) > 1)
        self.all_btn.setText(f"All {len(run['results'])} results…")
        self.all_btn.setVisible(len(run["results"]) > 1)
        self.result_box.show()
        self.render_runs()
        self.set_view(self.sw.s.get("filters_view", "table"), remember=False)
        self.live_update()

    @staticmethod
    def pick_note(run, r):
        """Under the result's numbers: how it sounds next to the target (the audible pick, engines.pick)."""
        case, lim = run.get("pick_case"), run.get("ear_db") or 0.25
        hz = lambda v: (f"{v / 1000:.1f} kHz" if v >= 1000 else f"{v:.0f} Hz") if v else ""
        if r.get("ear") is None or not case:
            return ""
        if r["id"] != run.get("pick"):
            return f"Sounds within {r['ear']:.2f} dB of the target everywhere (as the ear hears it)" + (
                f"; most off around {hz(r['ear_at'])}." if r.get("ear_at") and r["ear"] > lim else ".")
        if case == "target":
            return (f"Sounds the same as the target: within {r['ear']:.2f} dB everywhere, as the ear hears it (the "
                    f"limit: {lim:g} dB), with the fewest filters that do.")
        best = min((x for x in run["results"] if x.get("ear") is not None), key=lambda x: x["ear"], default=r)
        return (f"The target is out of reach here (your EQ app's limits, or detail filters can't follow): even the "
                f"closest EQ is {best['ear']:.2f} dB off around {hz(best.get('ear_at'))}. "
                + ("This is that closest one." if best["id"] == r["id"] else
                   "This one sounds the same as that closest one, with fewer filters."))

    # ---------------------------------------------------------------- runs this session (results.js RUNS)
    def use_in_single_run(self):
        """A sweep's chosen values into Website AutoEQ: one run (results.js "Use in single run")."""
        run, r = self.current()
        if not r:
            return
        self.S["site_single"].update({k: r[k] for k in ("rows", "freq_low", "freq_high", "gain_min", "gain_max", "q_min",
                                                        "q_max") if r.get(k) is not None})
        manual = self.S["auto"].setdefault("manual", [])
        for k in ("rows", "freq_high", "gain_min", "gain_max", "q_max"):  # (these exact values: yours)
            if "site_single." + k not in manual:
                manual.append("site_single." + k)
        self.S["mode"] = "site_single"
        self.changed()
        self.settings.refresh()
        self.status("Copied into Website AutoEQ: one run.", 6000)

    def open_all_results(self):
        """Every result of the run shown, and the error grid (ui/all_results.py)."""
        from ui.all_results import AllResults
        if self.current()[1]:
            _modal(AllResults(self))

    def open_queue(self):
        """Several EQs in one go (ui/queue_window.py)."""
        from ui.queue_window import QueueWindow
        if not self.groups or not self.inputs.get("targets"):
            QMessageBox.information(self, "Run several", "Add a target and at least one measurement first.")
            return
        _modal(QueueWindow(self))

    def open_compare(self):
        """Two EQs side by side (ui/compare_results.py)."""
        from ui.compare_results import CompareResults, options
        if len(options(self)) < 2:
            self.status("Nothing else to compare with yet: another run, another filter count or History.", 6000)
            return
        _modal(CompareResults(self))

    def keep_run(self, run):
        self.session_runs = [x for x in self.session_runs if x is not run][-19:] + [run]  # (the last 20)

    def render_runs(self):
        c = self.runs_combo
        c.clear()
        for run in reversed(self.session_runs):
            best = min((x["rms"] for x in run["results"] if x.get("rms") is not None), default=None)
            c.addItem((f"From History ({run['when']})" if run.get("history") else f"Run {run.get('n', 1)}")
                      + f"  ·  {MODE_SHORT.get(run['mode'], run['mode'])}"
                      + (f"  ·  {best:.2f} dB" if best is not None else "")
                      + f"  ·  {run.get('device')} → {run.get('target_name')}", id(run))
        c.setCurrentIndex(max(0, c.findData(id(self.run_result))))
        c.sort_items()
        self.runs_row.setVisible(len(self.session_runs) > 1)

    def choose_run(self, key):
        run = next((x for x in self.session_runs if id(x) == key), None)
        if run is None or run is self.run_result:
            return
        self.run_result = run
        self.name_edit.clear()
        self.show_result(run["_sel"] if run.get("_sel") is not None else run["pick"])  # (result 0 is a result)

    def remove_run(self):
        self.session_runs = [x for x in self.session_runs if x is not self.run_result]
        if self.session_runs:
            last = self.session_runs[-1]
            self.run_result = last
            self.name_edit.clear()
            self.show_result(last["_sel"] if last.get("_sel") is not None else last["pick"])
        else:
            self.run_result, self.sel = None, None
            self.result_box.hide()

    # ---------------------------------------------------------------- the filters being edited
    def active(self):
        """The filters switched on, as the run, Save and Use take them."""
        return [{"type": f.get("type", "PK"), "freq": f["freq"], "gain": f["gain"], "q": f["q"]}
                for f in self.EDIT if f.get("enabled", True) is not False]

    def edited(self):
        key = lambda fl: sorted((f.get("enabled", True) is not False, f.get("type", "PK"), float(f["freq"]),
                                 float(f["gain"]), float(f["q"])) for f in fl)
        return key(self.EDIT) != key(self.ORIG)  # (the same filters in another order, e.g. after Sort, aren't)

    def stats(self):
        """The filters' numbers as AutoEQ Local's plot.js worked them out: the error in the scored range, the pre-amp
        (the EQ's highest point, turned down), the biggest Q and boost."""
        from eq import engines
        act, c = self.active(), self.curves
        f = np.asarray(c["f"]) if c else np.geomspace(20, 20000, 480)
        g = engines.eq_gain(f, act, self.S["site"]["sample_rate"])
        rms = ear = None
        if c:
            band = self.S["scoring"]["band_hz"]
            inside = (f >= band[0]) & (f <= band[1])
            full = np.asarray(c["meas"]) + g - np.asarray(c["target"])
            d = full[inside]
            rms = float(np.sqrt(np.mean(d * d))) if d.size else None
            ear = engines.ear_error(f, full, band)[0] if d.size else None  # (how it sounds: the pick's line)
        return {"rms": rms, "ear": ear, "preamp_raw": -float(np.max(g)) if act else 0.0, "n": len(act),
                "max_q": max([0] + [x["q"] for x in act]), "max_boost": max([0] + [x["gain"] for x in act])}

    def preamp_text(self, raw):
        """The pre-amp as saved: less the extra headroom, rounded (safe: down; site: as squiglink)."""
        e = self.S["export"]
        p = raw - float(e.get("extra_headroom") or 0)
        v = round(p * 10) / 10 if e.get("preamp_rounding") == "site" else np.floor(p * 10 + 1e-9) / 10
        return f"{(0.0 if v == 0 else v):.1f}"

    def live_update(self):
        """After an edit (or a new result): the numbers, the title, the file name, the graph."""
        run, r = self.current()
        if not r:
            return
        st, ed = self.stats(), self.edited()
        tag = "recommended" if r["id"] == run["pick"] else "lowest error" if r["id"] == run["best"] else ""
        self.res_title.setText(MODE_SHORT.get(run["mode"], run["mode"]) + (f"  ·  {tag}" if tag else "")
                               + ("  ·  edited" if ed else ""))
        if ed:  # (the run's line was about the filters before the edit)
            note = (f"As edited: sounds within {st['ear']:.2f} dB of the target everywhere, as the ear hears it (the "
                    f"limit: {run.get('ear_db') or 0.25:g} dB)." if run.get("pick_case") and st["ear"] is not None else "")
        else:
            note = self.pick_note(run, r)
        self.pick_lab.setText(note)
        self.pick_lab.setVisible(bool(note))
        self.chips["filters"].setText(f"Filters  {st['n']}")
        self.chips["error"].setText(f"Error  {st['rms']:.2f} dB" if st["rms"] is not None else "Error  –")
        self.chips["preamp"].setText(f"Pre-amp  {self.preamp_text(st['preamp_raw'])} dB")
        self.chips["boost"].setText(f"Max boost  +{st['max_boost']:.1f} dB")
        self.chips["maxq"].setText(f"Max Q  {st['max_q']:g}" if st["max_q"] else "Max Q  –")
        site = run["mode"].startswith("site") and r.get("rows") is not None
        self.site_row.setVisible(site)
        if site:
            self.site_text.setText(
                "Type into squiglink's AutoEQ panel: Filter rows <b>{rows}</b> · Frequency Range <b>{freq_low}</b> to "
                "<b>{freq_high}</b> · Gain Range <b>{gain_min}</b> to <b>{gain_max}</b> · Q Range <b>{q_min}</b> to "
                "<b>{q_max}</b> → the site shows Pre-amp <b>{pre:.1f} dB</b>".format(
                    pre=float(r.get("preamp") or 0), **{k: r.get(k, "–") for k in ("rows", "freq_low", "freq_high",
                                                                                      "gain_min", "gain_max", "q_min", "q_max")})
                + (" <i>(you edited the filters, so the site won't produce these exact values)</i>" if ed else ""))
            self.site_use.setVisible(run["mode"] == "site_sweep")
        self.revert_btn.setVisible(ed)
        self.editor.set_preamp_text(self.preamp_text(st["preamp_raw"]))
        if hasattr(self, "listen"):
            self.listen.refresh()
        if not self.name_edit.text().strip() or self.name_edit.property("auto") is not False:
            self.name_edit.setText(self.auto_name())
            self.name_edit.setProperty("auto", True)
        self.draw()

    def set_view(self, view, remember=True):
        for k, b in self.view_btns.items():
            b.setChecked(k == view)
        self.editor.set_filters(self.EDIT, self.preamp_text(self.stats()["preamp_raw"]) if self.current()[1] else "0.0")
        self.editor.set_view(view)
        if remember and self.sw.s.get("filters_view") != view:
            self.sw.set("filters_view", view)

    def add_filter(self):
        self.EDIT.append({"enabled": True, "type": "PK", "freq": 1000, "gain": 0.0, "q": 1.0})
        self.editor.rebuild()
        self.live_update()

    def sort_filters(self):
        self.EDIT.sort(key=lambda f: f["freq"])
        self.editor.rebuild()
        self.live_update()

    def revert(self):
        self.EDIT[:] = [dict(f) for f in self.ORIG]
        self.editor.rebuild()
        self.live_update()

    def auto_name(self):
        run, r = self.current()
        lay = next((l for l in self.meta.get("layouts", []) if l["key"] == r.get("layout") and l["key"] != "any"), None)
        return file_base_name(run.get("device") or "EQ", run.get("target_name") or "target", lay["name"] if lay else "",
                              run["mode"], len(self.active()) if self.EDIT else r["n_filters"]) + \
            (" edited" if self.EDIT and self.edited() else "")

    def save(self):
        run, r = self.current()
        if not r:
            return
        if not self.active():
            QMessageBox.information(self, "Save filters", "There are no filters switched on to save.")
            return
        from eq import exports
        files = any(self.S["export"].get(k) for k in exports.FORMATS)
        if not files and not self.S["export"].get("report"):
            QMessageBox.information(self, "Save filters", "No file is ticked to save: choose your EQ app, or tick the "
                                    "files under Advanced › Saved files.")
            return
        name = self.name_edit.text().strip() or self.auto_name()
        written, notes, kept = [], "", False
        if files:
            # (switched-off filters go too: an Equalizer APO file keeps them as OFF lines, as AutoEQ Local's did)
            body = {"settings": self.S, "filters": [dict(f) for f in self.EDIT if f.get("freq") and f.get("q")],
                    "preamp": self.stats()["preamp_raw"], "name": name}
            res = self.svc.call("/api/export", body)
            if res.get("exists"):
                if not self._replace_ok(res["exists"]):
                    return
                res = self.svc.call("/api/export", {**body, "replace": True})
            if res.get("error"):
                QMessageBox.warning(self, "Save filters", res["error"])
                return
            written = [os.path.basename(p) for p in (res.get("written") or {}).values()]
            notes = " ".join(res.get("notes") or [])
        if self.S["export"].get("report"):
            path = self.report(open_it=False)
            if path:
                written.append(os.path.basename(path))
            else:
                kept = True
        if not written:
            return
        self.record(True)
        self.status(f"Saved {', '.join(written)} in your Saved EQs folder." + (f" {notes}" if notes else "")
                    + (" The report of that name was kept: change the File name to save another beside it." if kept else ""),
                    10000)

    def _replace_ok(self, names):
        return QMessageBox.question(self, "Replace?", "Already in your Saved EQs folder:\n\n" + "\n".join(names)
                                    + "\n\nReplace? (No keeps them: change the File name to save beside them.)") == QMessageBox.Yes

    def report(self, open_it=True):
        """The HTML report of the result shown (and of up to two of your EQs to compare on the graph), as AutoEQ
        Local's export.js reportBody: its path, or None when one of that name was kept or it failed."""
        run, r = self.current()
        if not r:
            return None
        title = MODE_SHORT.get(run["mode"], "EQ") + (" (edited)" if self.edited() else "")
        fields = [["Filter rows", r.get("rows")], ["Frequency Range", f"{r.get('freq_low')} to {r.get('freq_high')}"],
                  ["Gain Range", f"{r.get('gain_min')} to {r.get('gain_max')}"],
                  ["Q Range", f"{r.get('q_min')} to {r.get('q_max')}"]] if run["mode"].startswith("site") else []
        # (the report is drawn on the files the EQ was made for, while they're in the app; else on the measurement
        # chosen now, and it says so)
        mf, tf = run.get("meas_files"), run.get("target_file")
        names = {m["name"] for m in self.inputs["measurements"]}
        own_files = bool(mf) and all(n in names for n in mf) and tf in self.inputs["targets"]
        made_for, here = run.get("device"), (self.curves or {}).get("name")
        other = (f" Made for the {made_for}: shown here on the {here}." if not own_files and made_for and here
                 and made_for != here else "")
        cards = [{"title": title, "badge": "recommended" if r["id"] == run.get("pick") else "", "fields": fields,
                  "text": self.run_label(run, r) + "." + other, "filters": self.active()}]
        for p in [p for p in self.listen.pins if p.get("shown", True)][:2]:
            cards.append({"title": p["name"], "text": "", "filters": [f for f in p["filters"] if f.get("enabled", True) is not False]})
        own = self.name_edit.text().strip() if self.name_edit.property("auto") is False else ""
        body = {"settings": self.S, "cards": cards, "open": open_it, "name": own,
                **({"meas_files": mf, "target_file": tf} if own_files else {})}
        if run["mode"] in ("site_sweep", "best_fit") and len(run["results"]) > 1:
            body.update(grid_mode=run["mode"], grid_results=[{k: x.get(k) for k in ("rows", "q_max", "rms", "freq_high",
                                                                                     "n_filters", "max_boost", "ear")}
                                                             for x in run["results"]])
        res = self.svc.call("/api/report", body)
        if res.get("exists"):
            if not self._replace_ok(res["exists"]):
                return None
            res = self.svc.call("/api/report", {**body, "replace": True})
        if res.get("error"):
            QMessageBox.warning(self, "Report", res["error"])
            return None
        if open_it:
            self.status(f"Report: {os.path.basename(res['path'])} (in your Saved EQs folder).", 8000)
        return res.get("path")

    # ---------------------------------------------------------------- Use on device
    def _fill_use_menu(self):
        m = self.use_menu
        m.clear()
        _, r = self.current()
        if not r:
            m.addAction("Run first").setEnabled(False)
            return
        if not self.sw.apo.found:
            m.addAction("Equalizer APO isn't installed (see Devices)").setEnabled(False)
            return
        from switcher.core import shown
        keys = [d.key for d in self.sw.devices] + [k for k in self.sw.s["devices"] if not self.sw.device(k)]
        for key in keys:
            rec, d = self.sw.record(key), self.sw.device(key)
            where = "playing now" if key == self.sw.playing_key else "connected" if d and d.connected else "not connected"
            a = m.addAction(f"{shown(rec)}  ·  {where}")
            a.triggered.connect(lambda _=False, k=key: self.use_on(k))
        if not keys:
            m.addAction("No playback devices found").setEnabled(False)
        live = [d.key for d in self.sw.devices if d.connected]
        if live:  # (hear it in every app for a few minutes before keeping it)
            m.addSeparator()
            t = m.addMenu("Try for 5 minutes on")
            t.setToolTipsVisible(True)
            for key in live:
                a = t.addAction(shown(self.sw.record(key)) + ("  ·  playing now" if key == self.sw.playing_key else ""))
                a.setToolTip("Plays in every app for 5 minutes; then Keep it, or the device's own EQ comes back")
                a.triggered.connect(lambda _=False, k=key: self.try_on(k))

    def _apo_text(self, title):
        """The EQ shown, as Equalizer APO text (as edited, with its pre-amp), or None (said)."""
        res = self.svc.call("/api/text", {"settings": self.S, "filters": self.active(),
                                          "preamp": self.stats()["preamp_raw"]})
        if res.get("error"):
            QMessageBox.warning(self, title, res["error"])
            return None
        return res["apo"]

    def try_on(self, key, minutes=5):
        """The EQ shown plays on a device for a few minutes, in every app (Devices' trial: switcher/core.py)."""
        from switcher.core import shown
        text = self._apo_text("Try on device")
        if text is None:
            return
        name = (self.name_edit.text().strip() or self.auto_name())[:80]
        try:
            self.sw.try_eq(key, text, name, minutes)
        except OSError as e:
            QMessageBox.warning(self, "Try on device", str(e))
            return
        extra = "" if self.sw.apo.set_up() else " (Equalizer APO isn't using AutoEQ Studio yet: Set up… on Devices.)"
        self.window().render_all() if hasattr(self.window(), "render_trial") else None
        self.status(f"Trying “{name}” on {shown(self.sw.record(key))} for {minutes} minutes: Keep it or Stop now in "
                    f"the bar at the top, or the tray icon's menu.{extra}", 10000)

    def use_on(self, key):
        """The EQ shown becomes a profile of this device, switched on (APO applies it while the device plays)."""
        from switcher.core import shown
        run, r = self.current()
        text = self._apo_text("Use on device")
        if text is None:
            return
        name = (self.name_edit.text().strip() or self.auto_name())[:80]
        path = os.path.join(tempfile.mkdtemp(prefix="autoeq-studio-"), textfile.safe_name(name, "EQ", 80) + ".txt")
        try:
            textfile.write_atomic(path, text)
            pid = self.sw.import_profile(path, name)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Use on device", str(e))
            return
        finally:
            try:
                os.remove(path)
                os.rmdir(os.path.dirname(path))
            except OSError:
                pass
        self.sw.add_to_device(key, pid, switch_on=True)
        rec, d = self.sw.record(key), self.sw.device(key)
        extra = ""
        if not self.sw.apo.set_up():
            extra = " Equalizer APO isn't using AutoEQ Studio yet: Set up… on the Devices screen."
        elif d and not d.apo:
            extra = " Equalizer APO isn't installed on this device yet (see Devices)."
        self.status(f"“{self.sw.profile_name(pid)}” is now on for {shown(rec)}.{extra}", 10000)

    # ---------------------------------------------------------------- History (history.js)
    def run_label(self, run, r):
        """What a result is, in a line (results.js runLabel)."""
        lay = next((l for l in self.meta.get("layouts", []) if l["key"] == r.get("layout")), None)
        if r.get("engine") == "graphic":
            return (f"{lay['name'] if lay else 'Fixed bands'}: {r['n_filters']} bands, {r.get('gain_min')} to "
                    f"+{r.get('gain_max')} dB in {r.get('step')} dB steps")
        if run["mode"] == "best_fit":
            yours, added = r.get("yours") or 0, max(0, r["n_filters"] - (r.get("yours") or 0))
            mine = ""
            if yours:
                mine = (f"your {yours} + {added} added" if r.get("rows") else f"your {yours} alone" if r.get("keep")
                        else f"your {yours}, fine-tuned") + ("" if r.get("keep") or not r.get("rows") else " (adjusted)") + " · "
            return (mine + (f"{lay['name']} · " if lay and lay["key"] != "any" else "")
                    + f"{r['n_filters']} filters, Q ≤ {r.get('q_max')}, boost ≤ +{r.get('gain_max')}")
        return (f"{r.get('rows')} rows · {r.get('freq_low')}–{r.get('freq_high')} · {r.get('gain_min')} to "
                f"{r.get('gain_max')} · Q {r.get('q_min')}–{r.get('q_max')}")

    @staticmethod
    def _print(filters):
        """A short fingerprint of filters: the same result saved as it is and edited are two entries (in another
        order, e.g. sorted, one)."""
        rows = sorted(json.dumps([f.get("type", "PK"), float(f["freq"]), float(f["gain"]), float(f["q"]),
                                  f.get("enabled", True) is not False]) for f in filters)
        return hashlib.sha1(json.dumps(rows).encode()).hexdigest()[:8]

    def entry_now(self, saved):
        run, r = self.current()
        st, c = self.stats(), self.curves or {}
        filters = [dict(f) for f in self.EDIT if f["freq"] and f["q"]]
        base = run.get("history") or f"{self.session}-{run.get('n', 1)}-{r['id']}"
        result = {k: v for k, v in r.items() if k != "filters"}
        S = self.S
        return {"key": f"{base}-{self._print(filters)}", "base": base, "saved": saved,
                "device": run.get("device") or c.get("name"), "target": run.get("target_name") or c.get("target_name"),
                "target_file": run.get("target_file") or self.inputs.get("active_target"),
                "meas_files": run.get("meas_files") or [m["name"] for m in self.inputs["measurements"] if m["included"]],
                "adjust": S["target_adjust"], "mode": run["mode"],
                "label": self.run_label(run, r) + (" (edited)" if self.edited() else ""), "result": result,
                "filters": filters, "rms": st["rms"], "preamp": st["preamp_raw"], "n_filters": st["n"],
                "site": S["site"], "rig_convert": S["rig_convert"]["enabled"], "band": S["scoring"]["band_hz"]}

    def record(self, saved):
        """Into History: after a run (saved False: only when Advanced › History keeps every run), or saved/copied."""
        run, r = self.current()
        if not r or not self.curves or (not saved and (self.S["history"]["keep"] != "all" or run.get("history"))):
            return
        res = self.svc.call("/api/history/add", {"entry": self.entry_now(saved)})
        if res.get("error"):
            self.status(f"Couldn't add this EQ to the history: {res['error']}", 8000)
            return
        by_key = {e["key"]: e for e in self.history}
        by_key[res["entry"]["key"]] = res["entry"]
        self.history = [by_key[k] for k in res.get("keys", []) if k in by_key]
        self.history_note()

    def history_note(self):
        """Under Measurement: when you've EQ'd it before (Advanced › History can turn it off)."""
        mine = [e for e in self.history if self.curves and e.get("device") == self.curves["name"]]
        on = bool(self.S["history"].get("eqd_before")) and bool(mine)
        self.eqd_before.setVisible(on)
        self.eqd_show.setVisible(on)
        if on:
            from ui.history_window import day_of
            last = max(mine, key=lambda e: e["when"])
            self.eqd_before.setText(f"You've EQ'd this {'once' if len(mine) == 1 else f'{len(mine)} times'} before · "
                                    f"last {day_of(last['when']).lower()}")

    def open_history(self, this_iem):
        from ui.history_window import HistoryWindow
        r = self.svc.call("/api/history")
        if "entries" in r:
            self.history = r["entries"]
        _modal(HistoryWindow(self, this_iem))

    def paste_picture(self):
        """Ctrl+V with a picture (or a picture file) on the clipboard: the tracer opens with it (as AutoEQ Local's
        paste anywhere)."""
        from PySide6.QtWidgets import QApplication
        md = QApplication.clipboard().mimeData()
        self._picture_in(md)

    def _picture_in(self, md):
        """A picture in dragged or pasted data: into the tracer. Returns whether there was one."""
        if self.svc is None or md is None:
            return False
        from ui.trace_window import IMAGE_SUFFIXES
        for u in md.urls() if md.hasUrls() else []:
            if u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_SUFFIXES:
                self.open_trace()
                self.tracer.open_file(u.toLocalFile())
                return True
        if md.hasImage():
            from PySide6.QtGui import QImage
            self.open_trace()
            self.tracer.load_image(QImage(md.imageData()))
            return True
        return False

    def dragEnterEvent(self, e):
        from ui.trace_window import IMAGE_SUFFIXES
        md = e.mimeData()
        if md.hasImage() or any(u.isLocalFile() and os.path.splitext(u.toLocalFile())[1].lower() in IMAGE_SUFFIXES
                                for u in md.urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        if self._picture_in(e.mimeData()):
            e.acceptProposedAction()

    def open_trace(self):
        """The tracer (one window, kept while the screen is open: what's traced stays when it's closed)."""
        from ui.trace_window import TraceWindow
        if getattr(self, "tracer", None) is None:
            self.tracer = TraceWindow(self)
        self.tracer.fill_comp()
        self.tracer.show()
        self.tracer.raise_()
        self.tracer.activateWindow()

    def copy_filters(self, filters, preamp_raw, record=True):
        """The filters as Equalizer APO text on the clipboard (kept in History when they're the result's)."""
        from PySide6.QtGui import QGuiApplication
        on = [f for f in filters if f.get("enabled", True) is not False]
        res = self.svc.call("/api/text", {"settings": self.S, "filters": on, "preamp": preamp_raw})
        if res.get("error"):
            QMessageBox.warning(self, "Copy", res["error"])
            return
        QGuiApplication.clipboard().setText(res["apo"])
        self.status("Copied the filters (Equalizer APO / squiglink format).", 5000)
        if record:
            self.record(True)

    def bring_back(self, e):
        """Show: its files, target adjustments and curve settings back when they're still in the app, then the EQ as
        a run of its own on the result card."""
        from ui.history_window import day_of, time_of
        names = {m["name"] for m in self.inputs["measurements"]}
        have_m = bool(e.get("meas_files")) and all(n in names for n in e["meas_files"])
        have_t = e.get("target_file") in self.inputs["targets"]
        S = self.S
        if have_m and have_t:
            S["files"]["active_target"] = e["target_file"]
            S["files"]["excluded"] = [n for n in names if n not in e["meas_files"]]
            for k in self.meta["defaults"]["target_adjust"]:
                if e.get("adjust") and k in e["adjust"]:
                    S["target_adjust"][k] = e["adjust"][k]
            for k in self.meta["defaults"]["site"]:
                if e.get("site") and k in e["site"]:
                    S["site"][k] = e["site"][k]
            if isinstance(e.get("rig_convert"), bool):
                S["rig_convert"]["enabled"] = e["rig_convert"]
            res = self.svc.call("/api/settings", {"settings": S})
            if res.get("inputs"):
                self.show_inputs(res["inputs"])
            self._curves_seq = getattr(self, "_curves_seq", 0) + 1  # (any load still on its way is dropped)
            self.curves_loaded(self.svc.call("/api/curves", {"settings": S}))
            self.show_settings()
        elif self.curves:
            self.status(f"{'Its target isn’t' if have_m else 'Its measurement files aren’t'} in the app any more, so its "
                        "filters are shown on the graph you have now.", 10000)
        if not self.curves:  # (nothing to show its filters on: said, not "shown on the graph")
            self.status(f"{'Its target isn’t' if have_m else 'Its measurement files aren’t'} in the app any more: "
                        "choose a measurement and a target first, then Show it again.", 10000)
            return
        band = e.get("band")
        if band and list(band) != list(S["scoring"]["band_hz"]):
            self.status(f"It was scored over {band[0]}–{band[1]} Hz and is now over {S['scoring']['band_hz'][0]}–"
                        f"{S['scoring']['band_hz'][1]} Hz, so its error here differs from the one in History.", 10000)
        res = dict(e.get("result") or {}, id=1, filters=[dict(f) for f in e["filters"]])
        res.setdefault("n_filters", e.get("n_filters", len(e["filters"])))
        res.setdefault("rms", e.get("rms") or 0)
        res.setdefault("max_boost", 0)
        self.runs += 1
        self.run_result = {"mode": e.get("mode", "best_fit"), "results": [res], "pick": 1, "best": 1, "n": self.runs,
                           "settings": {}, "seconds": 0,
                           "when": f"{day_of(e['when'])} {time_of(e['when'])}", "history": e.get("base"),
                           "device": e.get("device"), "target_name": e.get("target"), "target_file": e.get("target_file"),
                           "meas_files": e.get("meas_files")}
        self.keep_run(self.run_result)
        self.name_edit.clear()
        self.show_result(1)
        self.history_note()
        self.status(f"From the history: {e.get('device')} → {e.get('target')}, {day_of(e['when']).lower()} "
                    f"{time_of(e['when'])}.", 8000)

    # ---------------------------------------------------------------- finding files (ui/picker.py)
    def find(self, kind):
        from ui.picker import Picker
        _modal(Picker(self, kind))

    def save_files(self, after=None):
        self._save_files(after)

    def save_adjusted_target(self):
        """Target › Adjust › Save as a target…: the target as adjusted becomes a target of your own, in
        use, the adjustments back to 0 (eq.service /api/target/save); Undo puts it all back."""
        from PySide6.QtWidgets import QInputDialog
        base = os.path.splitext(self.S["files"].get("active_target") or "Target")[0]
        name, ok = QInputDialog.getText(self, "Save as a target", "Name of your target:", text=f"{base} (mine)")
        if not ok or not name.strip():
            return
        res = self.svc.call("/api/target/save", {"settings": self.S, "name": name.strip()})
        if res.get("error"):
            QMessageBox.warning(self, "Save as a target", res["error"])
            return
        before = res["before"]
        self.S = res["settings"]
        self.show_inputs(res["inputs"])
        self.show_settings()
        self.load_curves()

        def undo():
            self.S["files"]["active_target"] = before["files"]["active_target"]
            self.S["target_adjust"] = before["target_adjust"]
            r = self.svc.call("/api/files/remove", {"kind": "target", "names": [res["name"]], "settings": self.S})
            if r.get("inputs"):
                self.show_inputs(r["inputs"])
            self.show_settings()
            self._save_files()
        self.notify(f"Saved “{os.path.splitext(res['name'])[0]}” as a target, now in use (the adjustments are in it, "
                    "so they're back to 0).", undo)

    # ---------------------------------------------------------------- presets (AutoEQ Local's Presets ▾)
    def preset_names(self):
        from eq import settings as eq_settings
        try:
            return eq_settings.list_presets()
        except OSError:
            return []

    def fill_presets(self, menu):
        """The top bar's Presets menu: each preset (click: load it), Save current settings as…, Delete a preset, and
        Reset all settings…. A preset keeps every setting, not your files."""
        menu.clear()
        names = self.preset_names()
        if not names:
            a = menu.addAction("No presets yet: a preset keeps all your settings (not your files)")
            a.setEnabled(False)
        for n in names:
            menu.addAction(n, lambda n=n: self.load_preset(n))
        menu.addSeparator()
        menu.addAction("Save current settings as…", self.save_preset)
        if names:
            d = menu.addMenu("Delete a preset")
            for n in names:
                d.addAction(n, lambda n=n: self.delete_preset(n))
        menu.addSeparator()
        menu.addAction("Reset all settings…", self.reset_settings)

    def _use_settings(self, s, said):
        """Settings from a preset (or the defaults) in use, your files as they are; Undo in the notice puts the ones
        before back."""
        before = json.loads(json.dumps(self.S))
        s["files"] = before["files"]
        self.S = s
        self._save_settings()
        self.show_settings()
        self.load_curves()

        def undo():
            self.S = before
            self._save_settings()
            self.show_settings()
            self.load_curves()
        self.notify(said, undo)

    def load_preset(self, name):
        res = self.svc.call("/api/presets/load", {"name": name})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self._use_settings(res["settings"], f"Loaded the preset “{name}”: all its settings (your files stay as they are).")

    def save_preset(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save a preset", "Save the current settings as the preset:",
                                        text="My settings")
        name = name.strip()
        if not ok or not name:
            return
        if name in self.preset_names() and QMessageBox.question(
                self, "Save a preset", f"There's a preset called “{name}” already. Replace it?") != QMessageBox.Yes:
            return
        res = self.svc.call("/api/presets/save", {"name": name, "settings": self.S})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self.notify(f"Saved the preset “{name}”: every setting, not your files. Presets ▾ loads it again.")

    def delete_preset(self, name):
        if QMessageBox.question(self, "Presets", f"Delete the preset “{name}”?") != QMessageBox.Yes:
            return
        res = self.svc.call("/api/presets/delete", {"name": name})
        if res.get("error"):
            QMessageBox.warning(self, "Presets", res["error"])
            return
        self.notify(f"Deleted the preset “{name}”.")

    def reset_settings(self):
        if QMessageBox.question(self, "Reset all settings", "Every setting back to its default? Your files and your "
                                "presets are kept, and Undo brings your settings back.") != QMessageBox.Yes:
            return
        res = self.svc.call("/api/reset")
        if res.get("error"):
            QMessageBox.warning(self, "Reset all settings", res["error"])
            return
        self._use_settings(res["settings"], "Every setting is back to its default (your files stay as they are).")

    def use_target(self, name):
        self.S["files"]["active_target"] = name
        self._save_files()

    def use_device(self, device):
        """A measurement in the app (a set of files) in use: its files ticked, the others not."""
        mine = {f["name"] for f in self.groups.get(device, [])}
        self.S["files"]["excluded"] = [m["name"] for m in self.inputs["measurements"] if m["name"] not in mine]
        self._save_files()

    def used(self, res):
        """A file from this PC or the online databases (or an average) is in the app and in use (eq.service /api/use's
        answer), said with Undo."""
        if res.get("settings"):
            self.S = res["settings"]
        if res.get("inputs"):
            self.show_inputs(res["inputs"])
        self.show_settings()
        self.load_curves()
        n = len(res.get("names") or [])
        self.notify(f"“{res.get('name')}” is now the target." if res.get("kind") == "target" else
                    f"Now measuring “{res.get('name')}”" + (f" ({n} file{'s' if n != 1 else ''})." if n else "."),
                    self._undo_use(res) if res.get("before") and res.get("settings") else None)

    def _undo_use(self, res):
        """Undo of a Use or an average (files.js undoUse): the files it made go, and what it chose goes back while
        it's as it left it (a file chosen since stays)."""
        back = "active_target" if res.get("kind") == "target" else "excluded"
        made = json.dumps(res["settings"]["files"][back])
        before = json.loads(json.dumps(res["before"][back]))  # (as it was, whatever changes the settings later)

        def undo():
            if json.dumps(self.S["files"][back]) == made:  # (the choice back first: never none ticked meanwhile)
                self.S["files"][back] = before
            if res.get("created"):
                r = self.svc.call("/api/files/remove", {"kind": res["kind"], "names": res["created"], "settings": self.S})
                if r.get("error"):
                    QMessageBox.warning(self, "Undo", r["error"])
            self._save_files()
        return undo

    def moved(self, kind, name, before):
        """A file moved between Target and Measurement (Find…), said with Undo (it goes back, the choice too)."""
        def undo():
            r = self.svc.call("/api/files/move", {"kind": "measurement" if kind == "target" else "target", "name": name,
                                                  "settings": self.S})
            if r.get("error"):
                QMessageBox.warning(self, "Undo", r["error"])
                return
            self.S["files"] = before
            self._save_files()
        self.notify(f"Moved “{name}” to {'Measurement' if kind == 'target' else 'Target'}.", undo)

    def reload_state(self):
        st = self.svc.call("/api/state")
        if "inputs" in st:
            self.S = st["settings"]
            self.show_inputs(st["inputs"])
            self.show_settings()
            self.load_curves()

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
            tasks.background(lambda req=req: self.svc.call("/api/preview", req), done)

    def compare(self):
        """Which measurement to use? (ui/compare_window.py)"""
        from ui.compare_window import CompareWindow
        _modal(CompareWindow(self))

    # ---------------------------------------------------------------- Listen (ui/listen.py)
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

    def keyPressEvent(self, e):
        """1-9: Listen's versions (not while typing in a box)."""
        from PySide6.QtWidgets import QLineEdit, QPlainTextEdit
        if hasattr(self, "listen") and Qt.Key_1 <= e.key() <= Qt.Key_9 and not e.modifiers() \
                and not isinstance(self.focusWidget(), (QLineEdit, QPlainTextEdit)):
            self.listen.choose_number(e.key() - Qt.Key_1)
            return
        super().keyPressEvent(e)

    def stop_sound(self):
        if hasattr(self, "listen") and self.listen.playing:
            self.listen.stop()
