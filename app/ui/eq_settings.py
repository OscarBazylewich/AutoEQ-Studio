"""The Make an EQ screen's two folds of settings (AutoEQ Local's Settings fold and Settings › Advanced, natively): two
rows that open in the Make the EQ card, above Calculate and Start (the UI audit, 2026-11-08: Calculate was above the
settings that it uses, and the result 2,000 px below it).

Settings (the ones used most):
- Automatic settings: on or off; "Your values" (each one made automatic again with ↺, or all); About these settings
  (n), a row that opens (closed at the start, kept as you left it): each value and the fact about your files it
  comes from
- the method's own values: Website AutoEQ's six; the website sweep's summary; Best fit's filter counts and shelves
- Error and selection: the range the match is judged over, how a result is picked
- Target: the rig conversion
More settings, a tab for each section (less height; a method's tab only with its method): Best fit (its layout,
bands, shelves, limits, penalties, and your own filters to start from), Website best settings, Website, Saved files,
History, This PC.
The Target's Adjust… (AutoEQ Local's Adjust): a window with tilt, bass, half-tilt, ear gain, treble and air, each
with − and +, a small graph of the target, Clear the adjustments and Save as a target… (the UI audit: in the page,
the graph was out of view while you adjusted).

A value the automatic settings fill in becomes "yours" once you change it (kept through new files
until made automatic again); with them off nothing changes by itself. Settings that change the curves (target adjustments,
the scored range, the website's levelling, the rig conversion) draw the graph again.

EqSettings(page) keeps what the settings need; build_parts(slot, target_row, target_under) makes them in four parts,
one per step of the page's build (ui/eq_page_cards.py: each a few ms, so the window answers in between): Adjust… (its
button on the Target row, its window), the Settings fold, More settings' first half, its second half
(Form.add_sections). Each part goes into its place in the step that makes it.
"""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from ui import help_window, icons, theme
from ui.bubble import InfoMark
from ui.forms import Field, Fold, Form, Limits, fmt_list

ADJUST_GAINS = ("tilt", "bass_gain", "halftilt_gain", "ear_gain", "treble_gain", "air_gain")  # (eq.service's)
CURVE_KEYS = ("target_adjust.","site.", "scoring.band_hz", "files.", "rig_convert.")  # (settings.js)
LABELS = {  # (auto.js: what "Set by you" calls each one)
    "scoring.band_hz.1": "Error to", "site_single.rows": "Filter rows", "site_single.freq_high": "Frequency to",
    "site_single.gain_min": "Gain from", "site_single.gain_max": "Gain to", "site_single.q_max": "Q to",
    "site_sweep.filter_rows": "Filter rows to try", "site_sweep.freq_high": "Frequency “to” values",
    "site_sweep.gain_ranges": "Gain ranges", "site_sweep.q_max": "Q “to” values", "best_fit.filter_counts": "Filter counts",
    "best_fit.freq_range.1": "Filters up to", "best_fit.gain_min": "Minimum gain", "best_fit.gain_max": "Maximum gain values",
    "best_fit.q_max": "Maximum Q values", "best_fit.low_shelf": "Low shelf", "best_fit.high_shelf": "High shelf",
    "scoring.pick": "Best result", "scoring.ear_db": "Same sound below",
    "best_fit.fight_penalty": "Penalties for opposite filters"}
FORMATS = [("apo", "Equalizer APO / squiglink filters (.txt)"), ("graphic", "GraphicEQ for Wavelet (.txt)"),
           ("poweramp", "Poweramp / Poweramp Equalizer preset (.json)"),
           ("uapp", "USB Audio Player PRO parametric EQ preset (.xml)"),
           ("soundsource", "SoundSource headphone EQ, macOS (.txt)"), ("voicemeeter", "Voicemeeter bus EQ, Windows (.xml)"),
           ("rockbox", "Rockbox EQ preset, music devices (.cfg)"),
           # (Help's title for it; the apps that use it are in Help: with them, the words were cut at every width)
           ("convolution", "Convolution impulse response (.wav)"),
           ("report", "An HTML report")]


def _muted_label(text):
    lab = QLabel(text)
    theme.mark(lab, role="muted")
    return lab


def _opts(values, names=None):
    return [(v, (names or {}).get(v, f"{v:g}" if isinstance(v, float) else str(v))) for v in values]


class OwnFiltersWindow(QDialog):
    """Your own filters' window: never shorter than its words and the view shown need at its width. Qt works out a
    window's smallest height with a wrapped line of words counted as one line, so the note's second line came out of
    the filter editor under it: in the Sliders view its bottom, the sideways scroll bar, was under OK and Cancel and
    filters past the fifth couldn't be reached (2026-10-23). The smallest height is worked out again as the view
    changes (the editor's height follows it) and as the window is made wider or narrower (the note wraps again)."""

    def event(self, e):
        done = super().event(e)
        if e.type() in (QEvent.LayoutRequest, QEvent.Resize) and self.layout() is not None:
            need = self.layout().totalMinimumHeightForWidth(self.width())
            if need > 0 and need != self.minimumHeight():
                self.setMinimumHeight(need)  # (made taller at once when it's shorter than that)
        return done


class EqSettings:
    def __init__(self, page):
        """What the settings need (their limits, the paths the automatic settings fill in); build_parts() makes them."""
        self.page = page
        m = page.meta
        self.limits = Limits(m.get("limits", {}), m.get("limit_pairs", []))
        self.auto_paths = [p for ps in (m.get("auto_paths") or {}).values() for p in ps]
        from eq import settings as eq_settings
        self.eq_settings = eq_settings

    def build_parts(self, slot, target_row, target_under):
        """The settings made in four parts, each put in its place in the same step (yield: the step ends there):
        Adjust… on the Target row (target_row; its summary in target_under, its window), the Settings fold into slot
        (the Make the EQ card's), More settings' first half into slot, its second half into More settings' form."""
        page, m = self.page, self.page.meta
        C = self.eq_settings.CHOICES
        S = lambda: page.S
        mode = lambda *ms: lambda: S()["mode"] in ms
        lay = lambda: next((l for l in m.get("layouts", []) if l["key"] == S()["best_fit"]["layout"]), {})
        fixed = lambda: S()["mode"] == "best_fit" and bool(lay().get("fixed"))
        free = lambda: S()["mode"] == "best_fit" and not lay().get("fixed")
        shelves = lambda: free() and lay().get("shelves", True)
        multi = mode("site_sweep", "best_fit")
        audible = lambda: multi() and S()["scoring"]["pick"] == "audible"
        get, changed, make_auto, say = self.get, self.changed, self.make_auto, lambda t: page.status(t, 6000)

        # ---------------------------------------------------------------- Adjust…, on the Target row (first: Tab
        # reaches it after Find… and Add…, as when the page was made in one go)
        self._adjust_panel(C, get, changed, make_auto, say, target_row, target_under)
        yield "adjust"

        # ---------------------------------------------------------------- Settings (a row that opens, in Make the EQ)
        self.fold = Fold("Settings", sub=True)
        self.fold.add(self._auto_box())
        self.sweep_note = QLabel()
        self.sweep_note.setWordWrap(True)
        theme.mark(self.sweep_note, role="muted")
        self.fixed_note = QLabel()
        self.fixed_note.setWordWrap(True)
        theme.mark(self.fixed_note, role="muted")
        self.method_title = QLabel()
        self.form = Form([
            ("Website AutoEQ: one set", [
                ("Filter rows", [("site_single.rows", "num")], mode("site_single")),
                ("Frequency from", [("site_single.freq_low", "num"), ("site_single.freq_high", "num")], mode("site_single")),
                ("Gain from (dB)", [("site_single.gain_min", "num"), ("site_single.gain_max", "num")], mode("site_single")),
                ("Q from", [("site_single.q_min", "num"), ("site_single.q_max", "num")], mode("site_single"))]),
            ("Website AutoEQ: find the best settings", [(self.sweep_note, [], mode("site_sweep"))]),
            ("Best fit", [
                ("Filter counts to try", [("best_fit.filter_counts", "intlist", None, "for example, 1-10")], free),
                ("Shelf", [("best_fit.low_shelf", "check")], shelves),
                (self.fixed_note, [], fixed)]),
            ("Error and selection", [
                ("Error from (Hz)", [("scoring.band_hz.0", "num"), ("scoring.band_hz.1", "num")]),
                ("Best result", [("scoring.pick", "choice",
                                  [("audible", "Minimum number of filters for the same sound"),
                                   ("lowest", "Lowest error")])], multi),
                ("Same sound below (dB)", [("scoring.ear_db", "num")], audible),
]),
            ("Target", [
                ("Rig change", [("rig_convert.enabled", "check")])]),
        ], self.limits, get, changed, make_auto, say)
        self.fold.add(self.form)
        self._label_checks()
        slot.addWidget(self.fold)
        yield "settings"

        # ---------------------------------------------------------------- More settings (in two halves), a tab for
        # each section (the user's words, 2026-11-08: less height), a method's own only with that method
        self.adv = Fold("More settings", sub=True)
        layouts = [(l["key"], f"{l['group']}: {l['name']}" if l["group"] not in ("Any",) else l["name"])
                   for l in m.get("layouts", [])]
        load_mine = QPushButton("Load an EQ file…")
        load_mine.clicked.connect(self.load_your_filters)
        self.mine_note = QLabel()
        theme.mark(self.mine_note, role="muted")
        mine_row = QWidget()
        mr = QHBoxLayout(mine_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.addWidget(load_mine)
        edit_mine = QPushButton("Edit as a table…")
        edit_mine.setToolTip("Your filters as a table or as sliders (the type, frequency, gain and Q of each filter)")
        edit_mine.clicked.connect(self.edit_your_filters)
        mr.addWidget(edit_mine)
        mr.addWidget(self.mine_note, 1)
        sections = [
            ("Best fit", [
                ("Layout", [("best_fit.layout", "choice", layouts)], mode("best_fit")),
                ("Band frequencies (Hz)", [("best_fit.bands.freqs", "numlist", None, "for example, 31, 62, 125, 250…")],
                 lambda: fixed() and S()["best_fit"]["layout"] == "bands"),
                ("Q of each band", [("best_fit.bands.q", "num")], lambda: fixed() and S()["best_fit"]["layout"] == "bands"),
                ("Sliders from (dB)", [("best_fit.bands.gain_min", "num"), ("best_fit.bands.gain_max", "num")], fixed),
                ("Slider step (dB)", [("best_fit.bands.step", "choice", _opts(C["best_fit.bands.step"]))], fixed),
                ("Low shelf (Hz)", [("best_fit.low_shelf_freq.0", "num"), ("best_fit.low_shelf_freq.1", "num")],
                 lambda: shelves() and S()["best_fit"]["low_shelf"]),
                ("Filters from (Hz)", [("best_fit.freq_range.0", "num"), ("best_fit.freq_range.1", "num")], free),
                ("Minimum gain (dB)", [("best_fit.gain_min", "num")], free),
                ("Maximum gain values (dB)", [("best_fit.gain_max", "numlist")], free),
                ("Q from", [("best_fit.q_min", "num")], free),
                ("Maximum Q values", [("best_fit.q_max", "numlist")], free),
                ("Penalties for opposite filters", [("best_fit.fight_penalty", "numlist")], free),
                # (your own filters to start from: here, not in Settings, as they are used less: the UI audit)
                ("Start from your filters", [("best_fit.start_filters", "block", None,
                                              "Equalizer APO lines, for example Filter: ON PK Fc 1000 Hz Gain -3 dB Q 1")],
                 mode("best_fit")),
                (None, mine_row, mode("best_fit")),  # (under the box that it fills: UI-RULES 27)
                ("", [("best_fit.start_keep", "check")],
                 lambda: S()["mode"] == "best_fit" and S()["best_fit"]["start_filters"].strip())]),
            ("Website best settings", [
                ("Filter rows to try", [("site_sweep.filter_rows", "intlist", None, "for example, 4-10 or 4, 6, 8")],
                 mode("site_sweep")),
                ("Frequency from", [("site_sweep.freq_low", "num")], mode("site_sweep")),
                ("Frequency “to” values", [("site_sweep.freq_high", "numlist")], mode("site_sweep")),
                ("Gain ranges", [("site_sweep.gain_ranges", "ranges", None, "low..high, …")], mode("site_sweep")),
                ("Q from", [("site_sweep.q_min", "num")], mode("site_sweep")),
                ("Q “to” values", [("site_sweep.q_max", "numlist")], mode("site_sweep"))]),
            ("Website", [
                ("Which website to copy", [("site.profile", "choice", [("listener800", "listener800 (5128 databases)"),
                                                                        ("squig.link lab", "squig.link"), ("custom", "Other")])]),
                ("Normalization", [("site.normalization", "choice", [("Hz~", "Hz~ (average across 4 octaves)"),
                                                                      ("Hz", "Hz (one frequency)"), ("dB", "dB (equal loudness, phon)")])]),
                ("Around (Hz)", [("site.norm_hz", "num")], lambda: S()["site"]["normalization"] != "dB"),
                ("Loudness (phon)", [("site.norm_db", "num")], lambda: S()["site"]["normalization"] == "dB"),
                ("AutoEQ TrebleStartFrom (Hz)", [("site.treble_start_from", "num")]),
                ("Sample rate", [("site.sample_rate", "choice", _opts(C["site.sample_rate"]))]),
                ("Smoothing level", [("site.smooth_level", "num")]),
                ("Smoothing scale", [("site.scale_smoothing", "num")]),
                ("Loudness tables", [("site.phon_table", "choice", [("ISO 226:2023", "ISO 226:2023 (listener800)"),
                                                                   ("ISO 226:2003", "ISO 226:2003 (squig.link)")])])]),
            ("Saved files", [("", [("export." + k, "check")]) for k, name in FORMATS] + [
                ("Impulse response sample rate", [("export.convolution_rate", "choice", _opts(C["export.convolution_rate"]))],
                 lambda: S()["export"]["convolution"]),
                ("Pre-amp rounding", [("export.preamp_rounding", "choice", [("safe", "Safe (lower value)"), ("site", "Same as squiglink")])]),
                ("More headroom (dB)", [("export.extra_headroom", "num")]),
                ("Q decimals in saved files", [("export.q_decimals", "num")])]),
            ("History", [
                ("History keeps", [("history.keep", "choice", [("saved", "EQs that you save or copy"),
                                                               ("all", "All results, and the EQs that you save")])]),
                ("", [("history.eqd_before", "check")])]),
            ("This PC", [("CPU cores (0 = all the cores minus 1)", [("performance.cores", "num")])]),
        ]
        self.adv_form = Form(sections[:2], self.limits, get, changed, make_auto, say, tabs=True)  # (Best fit, sweep)
        # (a tick box's words in the step that makes it: a screen reader's name is its words, and a box without words
        # when Qt first draws it is named by its tooltip, theme._Names)
        self._label_checks(self.adv_form)
        self.adv.add(self.adv_form)
        slot.addWidget(self.adv)
        yield "advanced, first half"
        self.adv_form.add_sections(sections[2:])  # (Website, Saved files, History, This PC)
        self._label_checks(self.adv_form)
        self.refresh()
        yield "advanced, second half"

    # ---------------------------------------------------------------- the Target card's Adjust (AutoEQ Local's)
    def _adjust_panel(self, C, get, changed, make_auto, say, target_row, target_under):
        """Adjust… (the UI audit, 2026-11-08: a button after Add… that opens a window): the target's tilt, bass,
        half-tilt, ear gain, treble and air (listener800's Custom DF) as a table: Value with − and +, Hz and Q (gray
        while the value is 0); a small graph of the target, which changes as you adjust it; Clear the adjustments and
        Save as a target… (usable once adjusted); its own message line and Close (UI-RULES 1). adjust_btn on the
        Target row (target_row), adjust_summary under it (target_under); the window is made here (hidden: its parent
        is the page, so it never shows as a window before it is opened)."""
        self.adjust_btn = QPushButton("Adjust…")
        icons.put(self.adjust_btn, "eq")  # (every button in the row with its symbol, UI-RULES 9)
        self.adjust_btn.setToolTip("Tilt, bass, half-tilt, ear gain, treble and air: give the target more or less bass "
                                   "or treble…")
        help_window.tag(self.adjust_btn, "#target-adjust")
        self.adjust_btn.clicked.connect(self.open_adjust)
        target_row.addWidget(self.adjust_btn)
        self.adjust_summary = QLabel()
        theme.mark(self.adjust_summary, role="muted")
        self.adjust_summary.hide()
        target_under.addWidget(self.adjust_summary)
        self.adjust_row = self.adjust_btn  # (the Guide's name for what opens it)
        w = self.make_adjust_window()
        self.adjust_window, self.adjust_form, self.adjust_rows = w.dlg, w.form, w.rows
        self.adjust_plot, self.adjust_curve, self.adjust_footer = w.plot, w.curve, w.footer
        self.reset_adjust_btn, self.save_target_btn = w.reset_btn, w.save_btn
        self.adjust_panel = w.dlg  # (the Guide's name for the controls)

    def make_adjust_window(self):
        """Adjust…'s window, its parts in a namespace (dlg, form, rows, plot, curve, footer, reset_btn, save_btn): the
        page's own (made at its build), or one for the Guide's demo (shown in the Guide's frame, then thrown away)."""
        import types
        from ui.window_parts import Footer, fit_to_screen
        C, get, changed, make_auto = self.eq_settings.CHOICES, self.get, self.changed, self.make_auto
        dlg = QDialog(self.page)
        out = types.SimpleNamespace(dlg=dlg)
        dlg.setWindowTitle("Adjust the target")
        dlg.setModal(False)
        fit_to_screen(dlg, (560, 560), (460, None))
        v = QVBoxLayout(dlg)
        v.setContentsMargins(16, 16, 16, 16)  # (a card's room around it, as Windows 11's own windows have)
        out.footer = Footer(dlg)
        say = out.footer.say  # (what its boxes say, in its own message line: UI-RULES 7)
        # a table: one row each, Value (with − and +), Hz and Q always in their columns (gray while the value is 0),
        # so nothing appears or moves as you type
        out.form = form = Form([], self.limits, get, changed, make_auto, say,
                               steps={"target_adjust.tilt": 0.1, **{f"target_adjust.{k}": 0.5 for k in ADJUST_GAINS[1:]}})
        grid_w = QWidget()
        g = QGridLayout(grid_w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        for col, (text, tip) in enumerate((("Value", "+ increases it, − decreases it (tilt: − more bass, + more treble)"),
                                           ("Hz", "The frequency: a shelf starts at it, ear gain is around it"),
                                           ("Q", "How quickly a shelf changes, or the width of ear gain")), 1):
            h = QLabel(text)
            h.setToolTip(tip)
            theme.mark(h, role="muted")
            if col == 1:  # (the words about the values: behind the ⓘ after Value, the UI audit)
                head = QWidget()
                hh = QHBoxLayout(head)
                hh.setContentsMargins(0, 0, 0, 0)
                hh.setSpacing(4)
                hh.addWidget(h)
                hh.addWidget(InfoMark("+ increases, − decreases (tilt: − more bass, + more treble). In a box, ↑ ↓ and "
                                      "the mouse wheel also change the value. Hz and Q change the target only when the "
                                      "value is not 0.", "the values"))
                hh.addStretch(1)
                g.addWidget(head, 0, col)
            else:
                g.addWidget(h, 0, col)

        def field(path, kind, options=None, width=64):
            f = Field(form, path, kind, options)
            f.committed.connect(changed)
            f.make_auto_clicked.connect(make_auto)
            if kind == "num":
                f.box.setFixedWidth(width)
            else:
                f.box.setFixedWidth(104)
            form.fields[path] = f
            return f
        out.rows = {}
        rows = (("tilt", "Tilt", "dB/oct", None, None), ("bass", "Bass", "dB", "bass_freq", "bass_q"),
                ("halftilt", "Half-tilt", "dB", "halftilt_freq", None), ("ear", "Ear gain", "dB", "ear_freq", "ear_q"),
                ("treble", "Treble", "dB", "treble_freq", "treble_q"), ("air", "Air", "dB", "air_freq", "air_q"))
        for i, (k, name, unit, hz, q) in enumerate(rows, 1):
            amount = "tilt" if k == "tilt" else k + "_gain"
            lab = QLabel(name)
            g.addWidget(lab, i, 0)
            a = field("target_adjust." + amount, "num")
            a.layout().addWidget(_muted_label(unit))
            a.box.setAccessibleName(f"{name} value ({unit})")
            a.minus.setAccessibleName(f"{name} lower")
            a.plus.setAccessibleName(f"{name} higher")
            lab.setToolTip(a.base_tip)
            g.addWidget(a, i, 1)
            deps = []
            if hz:
                f = field("target_adjust." + hz, "num", width=70)
                f.box.setAccessibleName(f"{name} frequency (Hz)")
                g.addWidget(f, i, 2)
                deps.append(f)
            else:
                g.addWidget(_muted_label("full range"), i, 2, 1, 2)
            if q:
                f = field("target_adjust." + q, "choice", _opts(C["target_adjust." + q]))
                f.box.setAccessibleName(f"{name} Q")
                g.addWidget(f, i, 3)
                deps.append(f)
            out.rows[amount] = deps
        g.setColumnStretch(4, 1)
        v.addWidget(grid_w)
        # the target, as it changes (the graph of the page can be under this window)
        import numpy as np
        import pyqtgraph as pg
        from ui.eq_page_parts import TICKS, hz as hz_text
        out.plot = plot = pg.PlotWidget()
        plot.setFixedHeight(170)
        plot.setLogMode(x=True, y=False)
        plot.setMenuEnabled(False)
        plot.setMouseEnabled(x=False, y=False)
        plot.hideButtons()
        plot.getAxis("bottom").setTicks([[(np.log10(t), hz_text(t).replace(" Hz", "").replace(" kHz", "k"))
                                          for t in TICKS]])
        plot.setXRange(np.log10(20), np.log10(20000), padding=0)
        plot.setAccessibleName("Graph of the adjusted target")
        out.curve = plot.plot([], [])
        v.addWidget(plot)
        out.reset_btn = QPushButton("Clear the adjustments")
        out.reset_btn.setToolTip("Set all adjustments to 0 (you can undo this)")
        out.reset_btn.clicked.connect(self.clear_adjustments)
        out.save_btn = QPushButton("Save as a target…")
        out.save_btn.setToolTip("Save the adjusted target as a new target (then all adjustments become 0)")
        out.save_btn.clicked.connect(self.page.save_adjusted_target)
        help_window.tag(out.save_btn, "#target-save")
        b = QHBoxLayout()
        b.addWidget(out.reset_btn)
        b.addWidget(out.save_btn)
        b.addStretch(1)
        v.addLayout(b)
        v.addStretch(1)
        v.addWidget(out.footer)
        return out

    def draw_adjust(self, w):
        """An Adjust window's graph (w: make_adjust_window's parts): the target as it is now, adjusted."""
        c = self.page.curves
        import numpy as np
        import pyqtgraph as pg
        col = theme.graph_colours()
        w.plot.setBackground(col["bg"])
        for ax in ("left", "bottom"):  # (the axes and grid as the page's graphs have them: pyqtgraph's own were gray)
            w.plot.getAxis(ax).setPen(pg.mkPen(col["axis"]))
            w.plot.getAxis(ax).setTextPen(pg.mkPen(col["axis"]))
        w.plot.showGrid(x=True, y=True, alpha=0.25)
        if not c:
            w.curve.setData([], [])
            return
        f, t = np.asarray(c["f"], dtype=float), np.asarray(c["target"], dtype=float)
        w.curve.setData(f, t, pen=pg.mkPen(col["target"], width=2))  # (the frequencies as they are: a log graph)

    def open_adjust(self):
        """Adjust…: its window, in front (made at the page's build)."""
        dlg = self.adjust_window
        if not dlg.isVisible():
            from ui.window_parts import fit_to_screen
            fit_to_screen(dlg, (560, 560), (460, None))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        self.redraw_adjust()

    def redraw_adjust(self):
        """The window's graph, while it shows."""
        if self.adjust_window.isVisible():
            import types
            self.draw_adjust(types.SimpleNamespace(plot=self.adjust_plot, curve=self.adjust_curve))

    def adjusted(self):
        return any(self.page.S["target_adjust"].get(k) for k in ADJUST_GAINS)

    def clear_adjustments(self):
        """Reset adjustments: the target as it is (every adjustment's default); Undo puts them back (in the window's
        own message line: UI-RULES 7)."""
        before = dict(self.page.S["target_adjust"])
        self.page.S["target_adjust"] = dict(self.page.meta["defaults"]["target_adjust"])
        self.page.changed(curves=True)

        def undo():
            self.page.S["target_adjust"] = before
            self.page.changed(curves=True)
        if self.adjust_window.isVisible():
            self.adjust_footer.say("All adjustments of the target are 0.", undo=undo)
        else:
            self.page.notify("All adjustments of the target are 0.", undo)

    def _adjust_summary_text(self):
        """Under the Target row: what's adjusted (“tilt −1 dB/oct, bass +4 dB”), or nothing."""
        a = self.page.S["target_adjust"]
        n = lambda v: f"{v:+g}".replace("-", "−")
        parts = [f"tilt {n(a['tilt'])} dB/oct"] if a.get("tilt") else []
        parts += [f"{name} {n(a[k + '_gain'])} dB" for k, name in (("bass", "bass"), ("halftilt", "half-tilt"),
                                                                  ("ear", "ear gain"), ("treble", "treble"), ("air", "air"))
                  if a.get(k + "_gain")]
        return ", ".join(parts) if parts else ""

    def _label_checks(self, form=None):
        """A checkbox's words beside it (the form's rows have them as the label: moved into the box)."""
        names = {"best_fit.low_shelf": "Low shelf (a wide bass change)",
                 "best_fit.start_keep": "Keep them as they are (Best fit adds filters around them)",
                 "rig_convert.enabled": "Change the target for the measurement's rig",
                 "history.eqd_before": "Show a message below Measurement if History has an EQ for it"}
        names.update({"export." + k: n for k, n in FORMATS})
        for path, f in (form or self.form).fields.items():
            if f.kind == "check" and path in names:
                f.box.setText(names[path])

    # ---------------------------------------------------------------- the automatic settings' box
    def _auto_box(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        self.auto_on = QCheckBox("Automatic settings: adjusted for your measurement and target")
        self.auto_on.toggled.connect(self.auto_switched)
        help_window.tag(self.auto_on, "#auto-on")
        v.addWidget(self.auto_on)
        self.mine_box = QWidget()
        mb = QHBoxLayout(self.mine_box)
        mb.setContentsMargins(0, 0, 0, 0)
        self.mine_text = QLabel()
        self.mine_text.setWordWrap(True)
        mb.addWidget(self.mine_text, 1)
        all_back = QPushButton("Make all automatic")
        all_back.clicked.connect(lambda: self.make_auto(None))
        mb.addWidget(all_back)
        v.addWidget(self.mine_box)
        # About these settings: a row that opens, closed at the start (the UI audit, 2026-11-08: its list was between
        # the tick box and the settings; as the tracer's, UI-RULES 12); kept open or closed for the next start
        sw = self.page.sw
        self.why_fold = Fold("About these settings", open_=bool(sw is not None and sw.s.get("about_settings_open")),
                             sub=True)
        self.why_head = self.why_fold.btn
        self.why = QLabel()
        self.why.setWordWrap(True)
        self.why.setTextFormat(Qt.RichText)  # (the list)
        self.why_fold.add(self.why)
        self.why_fold.toggled.connect(lambda on: sw is not None and sw.s.get("about_settings_open") != on
                                      and sw.set("about_settings_open", on, tell=False))
        v.addWidget(self.why_fold)
        return w

    # ---------------------------------------------------------------- reading and changing
    def get(self, path):
        return self.eq_settings.get_path(self.page.S, path)

    def is_auto_path(self, path):
        return path in self.auto_paths

    def your_values(self):
        return self.page.S["auto"].setdefault("manual", [])

    def changed(self, path, value):
        """A valid value set in a box: into the settings, yours (when the automatic settings fill it), its side
        effects (settings.js onSettingSideEffects), then saved, and the curves or the automatic settings again."""
        S = self.page.S
        if self.get(path) == value:
            return
        self.eq_settings.set_path(S, path, value)
        if self.is_auto_path(path) and path not in self.your_values():
            self.your_values().append(path)
        if path == "site.profile" and value in self.page.meta.get("profiles", {}):
            S["site"].update(self.page.meta["profiles"][value])
        elif path.startswith("site.") and path != "site.sample_rate":
            match = next((k for k, p in self.page.meta.get("profiles", {}).items()
                          if all(S["site"].get(a) == b for a, b in p.items())), None)
            S["site"]["profile"] = match or "custom"
        if path == "best_fit.layout":  # (a graphic EQ app's layout chosen here: its sliders too)
            a = next((x for x in self.page.meta.get("eq_apps", []) if x["kind"] == "graphic" and x["layout"] == value), None)
            if a:
                self.page.apply_bands(a)
        self.page.changed(curves=any(path.startswith(k) for k in CURVE_KEYS))
        self.refresh()

    def make_auto(self, path):
        S = self.page.S
        S["auto"]["manual"] = [p for p in self.your_values() if p != path] if path else []
        self.page.changed()
        self.page.refresh_auto()
        self.refresh()

    def auto_switched(self, on):
        self.page.S["auto"]["enabled"] = bool(on)
        self.page.changed()
        self.page.status("Automatic settings on: adjusted for the measurement and target." if on
                         else "Automatic settings off: all settings stay as they are.", 5000)
        self.refresh()

    def load_your_filters(self):
        f, _ = QFileDialog.getOpenFileName(self.fold, "Load an EQ file", "", "EQ files (*.txt *.cfg *.csv);;All files (*)")
        if not f:
            return
        import textfile
        r = self.page.svc.call("/api/filters/parse", {"text": textfile.read(f)})
        if r.get("error") or not r.get("filters"):
            self.page.status(r.get("error") or f"There are no filters in “{f}”.", 8000)
            return
        lines = self._apo_lines(r["filters"])
        self.changed("best_fit.start_filters", "\n".join(lines))
        self.page.status(f"Best fit starts from the {len(lines)} filter{'' if len(lines) == 1 else 's'} in the file.", 5000)

    @staticmethod
    def _apo_lines(filters):
        """Filters as Equalizer APO lines (how "Start from your own filters" keeps them); switched-off ones left out."""
        return [f"Filter {i}: ON {({'PK': 'PK', 'LSQ': 'LSC', 'HSQ': 'HSC'}).get(x.get('type', 'PK'), 'PK')} "
                f"Fc {x['freq']:g} Hz Gain {x['gain']:g} dB Q {x['q']:g}"
                for i, x in enumerate([x for x in filters if x.get("enabled", True) is not False], 1)]

    def edit_your_filters(self):
        """Your own filters in the filter editor (as AutoEQ Local's own-filters table and sliders): OK writes them back.
        It ends as every window does (.claude/notes/UI-RULES.md 1, 4, 6, 7): its own message line (what the editor
        changed: it was said in the main window's, behind it), OK (Enter's, in the accent; Enter in a box being typed in
        is the box's: it pressed OK and closed the window) and Cancel; it opens within the screen."""
        from ui.filter_editor import FilterEditor
        from ui.window_parts import Footer, enter_presses, fit_to_screen
        text = self.page.S["best_fit"].get("start_filters", "")
        r = self.page.svc.call("/api/filters/parse", {"text": text}) if text.strip() else {"filters": []}
        if r.get("error"):  # (an empty table, and OK then wiped your text: review 2)
            QMessageBox.warning(self.fold, "Your filters", f"{r['error']}\n\nCorrect that line in the box. Then open the "
                                "table again.")
            return
        filters = [{"enabled": True, "type": x.get("type", "PK"), "freq": x["freq"], "gain": x["gain"], "q": x["q"]}
                   for x in r.get("filters") or []]
        dlg = OwnFiltersWindow(self.fold)
        dlg.setWindowTitle("Your filters")
        # (at least 640 wide: it went down to 280, the table's boxes squeezed, one slider in sight)
        fit_to_screen(dlg, (820, 560), (640, None))
        v = QVBoxLayout(dlg)
        v.setContentsMargins(16, 16, 16, 16)  # (a card's room around it, as Windows 11's own windows have)
        others = len([ln for ln in text.splitlines() if ln.strip()]) > len(filters)
        note = QLabel("Best fit starts from these filters (not from the filters that are off). It adds filters to them. "
                      "If you do not select “Keep them as they are”, it also adjusts them."
                      + (" OK removes the other lines in the box (a Preamp line, other text, and filters that are off)."
                         if others else ""))
        note.setWordWrap(True)
        theme.mark(note, role="muted")
        v.addWidget(note)
        ok_btn, cancel = QPushButton("OK"), QPushButton("Cancel")
        theme.mark(ok_btn, primary=True)  # (the window's main action: the accent)
        ok_btn.clicked.connect(dlg.accept)
        cancel.clicked.connect(dlg.reject)
        footer = Footer(dlg, close=False, main=[ok_btn, cancel])
        ed = FilterEditor(self.page.meta.get("limits", {}), footer.say)
        ed.set_filters(filters)
        ed.set_view("table")
        row = QHBoxLayout()
        views = {}

        def show(view):  # (as the result card's Table and Sliders: tabs, the one shown marked)
            for k, b in views.items():
                b.setChecked(k == view)
            ed.set_view(view)
        for name, view in (("Table", "table"), ("Sliders", "sliders")):
            b = views[view] = QPushButton(name)
            b.setCheckable(True)
            b.setChecked(view == "table")
            theme.mark(b, nav=True, flush=True)
            b.clicked.connect(lambda _=False, view=view: show(view))
            row.addWidget(b)
        row.addSpacing(12)
        add = QPushButton("Add filter")
        icons.put(add, "add")
        add.clicked.connect(lambda: (filters.append({"enabled": True, "type": "PK", "freq": 1000, "gain": 0, "q": 1}),
                                     ed.rebuild()))
        row.addWidget(add)
        sort = QPushButton("Sort")  # (the result card's commands: UI-RULES 19, the UI audit, 2026-11-08)
        icons.put(sort, "sort")
        sort.setToolTip("Sort the filters by frequency")
        sort.clicked.connect(lambda: (filters.sort(key=lambda x: x["freq"]), ed.rebuild()))
        row.addWidget(sort)
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(ed, 1)
        v.addWidget(footer)
        enter_presses(dlg, ok_btn)
        ok = dlg.exec()
        dlg.deleteLater()  # (each opening made a window of its own, kept hidden under the Settings fold)
        if ok:
            self.changed("best_fit.start_filters", "\n".join(self._apo_lines(filters)))
            n = sum(f.get('enabled', True) is not False for f in filters)
            self.page.status(f"Best fit starts from {n} filter{'' if n == 1 else 's'}.", 5000)

    # ---------------------------------------------------------------- showing
    def refresh(self):
        S, a = self.page.S, self.page.auto or {}
        on = bool(S["auto"]["enabled"])
        self.auto_on.blockSignals(True)
        self.auto_on.setChecked(on)
        self.auto_on.blockSignals(False)
        mine = [p for p in self.your_values() if self.is_auto_path(p)]
        notes = (a.get("notes") or []) if on else []
        t = theme.tokens()
        items = []
        for n in notes:
            text = n["text"].replace("&", "&amp;").replace("<", "&lt;")
            if n.get("path") in mine:  # ("yours" in the accent as text: 4.5:1 on the card, light or dark)
                items.append(f"<li><span style='color:{t['accent_text']}'>your value</span> · Automatic: {text} The app "
                             "uses your value.</li>")
            else:
                items.append(f"<li>{text}</li>")
        self.why.setText("<ul style='margin-left:-20px'>" + "".join(items) + "</ul>" if items else
                         ("Select a target and a measurement for the automatic settings." if on
                          else "Automatic settings are off."))
        self.why_head.setText(f"About these settings ({len(notes)})" if notes else "About these settings")
        self.redraw_adjust()
        self.mine_box.setVisible(on and bool(mine))
        self.mine_text.setText("Your values (not changed): " + ", ".join(LABELS.get(p, p) for p in mine)
                               + ".  To make one automatic, click its “your value ↺” tag.")
        tags = {p: ("yours" if p in mine else "auto") for p in self.auto_paths} if on else {}
        self.form.refresh(tags)
        self.adv_form.refresh(tags)
        self.adjust_form.refresh()
        for amount, deps in self.adjust_rows.items():  # (a gain's Hz and Q greyed while it's 0: they do nothing then)
            for f in deps:
                f.box.setEnabled(bool(S["target_adjust"].get(amount)))
        adj = self.adjusted()
        self.adjust_summary.setText(("Adjusted: " + self._adjust_summary_text()) if adj else "")
        self.adjust_summary.setVisible(adj)
        self.reset_adjust_btn.setEnabled(adj)  # (always there, so nothing moves; usable once adjusted)
        self.save_target_btn.setEnabled(adj)
        sw = S["site_sweep"]
        self.sweep_note.setText(f"The settings that the app tries: rows {fmt_list(sw['filter_rows'])} · frequency to "
                                f"{', '.join(f'{v / 1000:g} kHz' for v in sw['freq_high'])} · gain "
                                f"{', '.join(f'{r[0]:g}..{r[1]:g}' for r in sw['gain_ranges'])} · Q to {fmt_list(sw['q_max'])}. "
                                "Change them in More settings › Website best settings.")
        lay = next((l for l in self.page.meta.get("layouts", []) if l["key"] == S["best_fit"]["layout"]), {})
        self.fixed_note.setText(f"{lay.get('name', '')}: a graphic EQ. Best fit adjusts only the gains of its bands "
                                "(their range and step are in More settings)." if lay.get("fixed") else "")
        # (settings.js mineCount: the lines the run reads)
        n = len([s for s in (S["best_fit"].get("start_filters") or "").splitlines()
                 if s.strip() and not s.strip().lower().startswith(("#", ";", "//", "preamp")) and ": off" not in s.lower()])
        self.mine_note.setText(f"{n} filter{'s' if n != 1 else ''} to start from" if n else "")
        hz = lambda v: f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"
        self.fold.summary.setText(f"{'automatic' if on else 'automatic off: your values'} · error range "
                                  f"{hz(S['scoring']['band_hz'][0])}–{hz(S['scoring']['band_hz'][1])}")
        self.adv.summary.setText("the layout, the limits and the settings to try, the website's values, saved files")
