"""The Make an EQ screen's two folds of settings (AutoEQ Local's Settings fold and Settings › Advanced, natively): two
rows that open in the Make the EQ card, above Calculate and Start (the UI audit, 2026-11-08: Calculate was above the
settings that it uses, and the result 2,000 px below it).

Settings (the ones used most):
- Automatic settings: on or off; "Custom values" (each one made automatic again with "custom ↺", or all with Make all
  automatic); About these settings (n), a row that opens (closed at the start, kept as you left it): each value and
  the fact about your files it comes from
- the method's own values: Website AutoEQ's seven; the website sweep's filter rows and the summary of its ranges;
  Best fit's filter counts and shelves
- Error and selection: the range the match is judged over, how a result is picked
More settings, a tab for each section (less height; a method's tab only with its method): Best fit (its layout,
bands, shelves, limits, penalties, and your own filters to start from), Website best settings, Website, Saved files,
History. CPU cores is last in the tab of the method shown (Best fit's or Website best settings').
The Target's Adjust… (AutoEQ Local's Adjust): a window with tilt, bass, half-tilt, ear gain, treble and air, each
with − and +, a small graph of the target, Clear the adjustments and Save as a target… (the UI audit: in the page,
the graph was out of view while you adjusted). Rig change (the rig conversion) is a row of the Target and
Measurement card, under the Target's rows: it changes the target on the graph at once.

A value the automatic settings fill in becomes "yours" once you change it (kept through new files
until made automatic again); with them off nothing changes by itself. Settings that change the curves (target adjustments,
the scored range, the website's levelling, the rig conversion) draw the graph again.

EqSettings(page) keeps what the settings need; build_parts(slot, above, target_row, target_under, rig_slot) makes
them in four parts, one per step of the page's build (ui/eq_page_cards.py: each a few ms, so the window answers in
between): Adjust… (its button on the Target row) with Rig change, the Settings fold, More settings' first half, its second half
(Form.add_sections). Each part goes into its place in the step that makes it, on the page and in the Tab sequence
(tab_order: Qt puts a part made later at the sequence's end). Adjust…'s window is made at its first use (adjust()),
not in the build: with its graph it was most of the build's "adjust" step (34 ms, now under 1 ms, offscreen,
2026-11-10).
"""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

from ui import help_window, icons, placed, theme
from ui.bubble import InfoMark
from ui.eq_page_parts import tab_order
from ui.forms import Field, Fold, Form, Limits, fmt_list, help_of

ADJUST_GAINS = ("tilt", "bass_gain", "halftilt_gain", "ear_gain", "treble_gain", "air_gain")  # (eq.service's)
CURVE_KEYS = ("target_adjust.","site.", "scoring.band_hz", "files.", "rig_convert.")  # (settings.js)
FORMATS = [("apo", "Equalizer APO / squiglink filters (.txt)"), ("graphic", "GraphicEQ for Wavelet (.txt)"),
           ("poweramp", "Poweramp / Poweramp Equalizer preset (.json)"),
           ("uapp", "USB Audio Player PRO parametric EQ preset (.xml)"),
           ("soundsource", "SoundSource headphone EQ, macOS (.txt)"), ("voicemeeter", "Voicemeeter bus EQ, Windows (.xml)"),
           ("rockbox", "Rockbox EQ preset, music devices (.cfg)"),
           # (Help's title for it; the apps that use it are in Help: with them, the words were cut at every width)
           ("convolution", "Convolution impulse response (.wav)"),
           ("report", "An HTML report")]
HISTORY_KEEPS = [("saved", "EQs that you save or copy"), ("all", "All results, and the EQs that you save")]


def _muted_label(text):
    lab = QLabel(text)
    theme.mark(lab, role="muted")
    return lab


def _section_label(text):
    lab = QLabel(text)
    theme.mark(lab, role="section")
    return lab


def _opts(values, names=None):
    return [(v, (names or {}).get(v, f"{v:g}" if isinstance(v, float) else str(v))) for v in values]


class OwnFiltersWindow(QDialog):
    """The Your filters window: never shorter than its words and the view shown need at its width. Qt works out a
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


def layout_words(layout):
    """A layout's row in the Layout list: its name. Only a graphic EQ whose name does not say so has its group first
    ("Graphic EQ: Your bands"). An EQ app's row is the app's name only (the user, 2026-11-10: "EQ apps (Your EQ app): "
    before each of 23 names was text to read past)."""
    name = layout["name"]
    if layout["group"] == "Graphic EQ" and "graphic" not in name.casefold():
        return f"Graphic EQ: {name}"
    return name


def _adjust_part(part):
    """One part of Adjust…'s window (make_adjust_window's namespace) by its old attribute name: the window is made at
    the first use of one (EqSettings.adjust)."""
    return property(lambda self: getattr(self.adjust(), part), doc=f"Adjust…'s window's {part} (made when first used)")


class EqSettings:
    # Adjust…'s window and its parts, made at their first use (EqSettings.adjust); adjust_panel is the Guide's name
    adjust_window = adjust_panel = _adjust_part("dlg")
    adjust_form, adjust_rows, adjust_footer = _adjust_part("form"), _adjust_part("rows"), _adjust_part("footer")
    adjust_plot, adjust_curve = _adjust_part("plot"), _adjust_part("curve")
    reset_adjust_btn, save_target_btn = _adjust_part("reset_btn"), _adjust_part("save_btn")

    def __init__(self, page):
        self.page = page
        self._adjust = None
        m = page.meta
        self.limits = Limits(m.get("limits", {}), m.get("limit_pairs", []))
        self.auto_paths = [p for ps in (m.get("auto_paths") or {}).values() for p in ps]
        from eq import settings as eq_settings
        self.eq_settings = eq_settings

    def build_parts(self, slot, above, target_row, target_under, rig_slot):
        """The settings made in four parts, each put in its place in the same step (yield: the step ends there):
        Adjust… on the Target row (target_row; its summary in target_under, its window) and Rig change's tick box
        under it (rig_slot: its row in the Target and Measurement card), the Settings fold into slot (the Make the EQ
        card's), More settings' first half into slot, its second half into More settings' form.
        above: the part of the card directly above slot (Tab goes from its last control to Settings)."""
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

        # ---------------------------------------------------------------- Adjust…, on the Target row: Tab reaches
        # it after the row's Find… and Add… (made after the cards under the row, it came after Queue… in the Tab
        # sequence: Tab on Queue… gave it the focus, and the page scrolled to its top, 2026-11-16)
        self._adjust_panel(C, get, changed, make_auto, say, target_row, target_under)
        # (Rig change in the Target and Measurement card, as it changes the target on the graph at once: it was
        # Settings › Target, the control audit, 2026-11-27. A form of its own: its box's tooltip, Help and value)
        self.rig_form = Form([("", [("", [("rig_convert.enabled", "check")])])], self.limits, get, changed, make_auto,
                             say)
        self._label_checks(self.rig_form)
        self.rig_box = self.rig_form.fields["rig_convert.enabled"].box
        rig_slot.addWidget(self.rig_form)
        if getattr(page, "rig_label", None) is not None:  # (the card's label: the setting's Help line, as a form's)
            page.rig_label.setToolTip(help_of("rig_convert.enabled"))
        tab_order(target_row.parentWidget(), self.rig_form)  # (after Adjust…, before the Measurement row)
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
            # (its main value here, as Best fit's Filter counts to try; its ranges in More settings: the control audit,
            # 2026-11-27)
            ("Website AutoEQ: find the best settings", [
                ("Filter rows to try", [("site_sweep.filter_rows", "intlist", None, "e.g. 4-10 or 4, 6, 8")],
                 mode("site_sweep")),
                (self.sweep_note, [], mode("site_sweep"))]),
            ("Best fit", [
                ("Filter counts to try", [("best_fit.filter_counts", "intlist", None, "e.g. 1-10")], free),
                ("Shelf", [("best_fit.low_shelf", "check")], shelves),
                (self.fixed_note, [], fixed)]),
            ("Error and selection", [
                ("Fit from (Hz)", [("scoring.band_hz.0", "num"), ("scoring.band_hz.1", "num")]),
                ("Best result", [("scoring.pick", "choice",
                                  [("audible", "Minimum number of filters for the same sound"),
                                   ("lowest", "Lowest error")])], multi),
                ("Same sound below (dB)", [("scoring.ear_db", "num")], audible),
]),
        ], self.limits, get, changed, make_auto, say)
        self.fold.add(self.form)
        self._label_checks()
        slot.addWidget(self.fold)
        tab_order(above, self.fold)  # (before Calculate, Queue… and Start, which are under it: it came after them)
        yield "settings"

        # ---------------------------------------------------------------- More settings (in two halves), a tab for
        # each section (the user's words, 2026-11-08: less height), a method's own only with that method
        self.adv = Fold("More settings", sub=True)
        layouts = [(l["key"], layout_words(l)) for l in m.get("layouts", [])]
        load_mine = QPushButton("Load an EQ file…")
        load_mine.clicked.connect(self.load_your_filters)
        self.mine_note = QLabel()
        theme.mark(self.mine_note, role="muted")
        mine_row = QWidget()
        mr = QHBoxLayout(mine_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.addWidget(load_mine)
        edit_mine = QPushButton("Edit as a table…")
        edit_mine.setToolTip("Edit filter type, frequency, gain, and Q in a table or with sliders")
        edit_mine.clicked.connect(self.edit_your_filters)
        mr.addWidget(edit_mine)
        mr.addWidget(self.mine_note, 1)
        sections = [
            ("Best fit", [
                ("Layout", [("best_fit.layout", "choice", layouts)], mode("best_fit")),
                ("Band frequencies (Hz)", [("best_fit.bands.freqs", "numlist", None, "e.g. 31, 62, 125, 250…")],
                 lambda: fixed() and S()["best_fit"]["layout"] == "bands"),
                ("Q of each band", [("best_fit.bands.q", "num")], lambda: fixed() and S()["best_fit"]["layout"] == "bands"),
                ("Sliders from (dB)", [("best_fit.bands.gain_min", "num"), ("best_fit.bands.gain_max", "num")], fixed),
                ("Slider step (dB)", [("best_fit.bands.step", "choice", _opts(C["best_fit.bands.step"]))], fixed),
                ("Low shelf (Hz)", [("best_fit.low_shelf_freq.0", "num"), ("best_fit.low_shelf_freq.1", "num")],
                 lambda: shelves() and S()["best_fit"]["low_shelf"]),
                ("Filters from (Hz)", [("best_fit.freq_range.0", "num"), ("best_fit.freq_range.1", "num")], free),
                # (a "from" and its list of "to" values in one cell, as every range: the control audit, 2026-11-27)
                ("Gain from (dB)", [("best_fit.gain_min", "num"), ("best_fit.gain_max", "numlist")], free),
                ("Q from", [("best_fit.q_min", "num"), ("best_fit.q_max", "numlist")], free),
                ("Penalties for opposite filters", [("best_fit.fight_penalty", "numlist")], free),
                # (your own filters to start from: here, not in Settings, as they are used less: the UI audit)
                ("Start from your filters", [("best_fit.start_filters", "block", None,
                                              "Equalizer APO lines e.g.\nFilter: ON PK Fc 1000 Hz Gain -3 dB Q 1")],
                 mode("best_fit")),
                (None, mine_row, mode("best_fit")),  # (under the box that it fills: UI-RULES 27)
                ("", [("best_fit.start_keep", "check")],
                 lambda: S()["mode"] == "best_fit" and S()["best_fit"]["start_filters"].strip()),
                # (only the two methods that run many fits use it, pipeline.py: one box, last in the tab of the method
                # shown; it had a tab of its own, This PC: the control audit, 2026-11-27)
                ("CPU cores (0 = all the cores minus 1)", [("performance.cores", "num")], multi,
                 {"follows": ("Best fit", "Website best settings")})]),
            ("Website best settings", [
                ("Frequency from", [("site_sweep.freq_low", "num"), ("site_sweep.freq_high", "numlist")],
                 mode("site_sweep")),
                ("Gain ranges", [("site_sweep.gain_ranges", "ranges")], mode("site_sweep")),  # (a row of two boxes each)
                ("Q from", [("site_sweep.q_min", "num"), ("site_sweep.q_max", "numlist")], mode("site_sweep"))]),
            ("Website", lambda: [  # (made in the second half's step, which places it: its gray line too)
                # (the two special choices pinned on top, then every graph website A to Z: UI-RULES 22; the list has
                # its search box, search_combo)
                ("Which website to copy", [("site.profile", "choice", [("auto", "The database of the measurement"),
                                                                        ("custom", "Other"),
                                                                        *[tuple(c) for c in m.get("site_choices", [])]],
                                            "", 2)]),
                (self.site_note, [], lambda: bool(self.site_note.text())),  # (where the values come from: in sight)
                ("Normalization", [("site.normalization", "choice", [("Hz~", "Hz~ (average across 4 octaves)"),
                                                                      ("Hz", "Hz (one frequency)"), ("dB", "dB (equal loudness, phon)")])]),
                # (by the levelling the curves have: the one shown, page.site_now)
                ("Around (Hz)", [("site.norm_hz", "num")], lambda: page.site_now()["normalization"] != "dB"),
                ("Loudness (phon)", [("site.norm_db", "num")], lambda: page.site_now()["normalization"] == "dB"),
                # (only the website's own AutoEQ reads it: engines.js_site_cfg, for the two Website methods)
                ("AutoEQ TrebleStartFrom (Hz)", [("site.treble_start_from", "num")], mode("site_single", "site_sweep")),
                ("Sample rate", [("site.sample_rate", "choice", _opts(C["site.sample_rate"]))]),
                ("Smoothing level", [("site.smooth_level", "num")]),
                ("Smoothing scale", [("site.scale_smoothing", "num")]),
                ("Loudness tables", [("site.phon_table", "choice", [("ISO 226:2023", "ISO 226:2023"),
                                                                   ("ISO 226:2003", "ISO 226:2003")])])]),
            # (the file types as a group of their own, under a heading, the other settings on the rows under them: the
            # control audit, 2026-11-27. Made in the second half's step, which places it)
            ("Saved files", lambda: [(_section_label("File types"), [])]
             + [("", [("export." + k, "check")], None, {"ends_row": k == FORMATS[-1][0]}) for k, name in FORMATS] + [
                ("Impulse response sample rate", [("export.convolution_rate", "choice", _opts(C["export.convolution_rate"]))],
                 lambda: S()["export"]["convolution"]),
                ("Pre-amp rounding", [("export.preamp_rounding", "choice", [("safe", "Safe (lower value)"), ("site", "Same as squiglink")])]),
                ("More headroom (dB)", [("export.extra_headroom", "num")]),
                ("Q decimals in saved files", [("export.q_decimals", "num")])]),
            # (History keeps is in the History window, where its effect shows: the control audit, 2026-11-27. This
            # tick box's effect is on this page, under Measurement)
            ("History", [("", [("history.eqd_before", "check")])]),
        ]
        self.adv_form = Form(sections[:2], self.limits, get, changed, make_auto, say, tabs=True)  # (Best fit, sweep)
        # (a tick box's words in the step that makes it: a screen reader's name is its words, and a box without words
        # when Qt first draws it is named by its tooltip, theme._Names)
        self._label_checks(self.adv_form)
        # (Tab leaves this box as it leaves the form's other boxes: Qt's Tab in a box of more than one line wrote a
        # tab character into the setting, and the focus stayed in the box, 2026-11-16)
        self.adv_form.fields["best_fit.start_filters"].box.setTabChangesFocus(True)
        self.adv.add(self.adv_form)
        slot.addWidget(self.adv)
        # (after Settings and what is in it; the tabs' buttons before the tabs' settings: the form makes each button
        # after its own tab's settings)
        tab_order(self.fold, self.adv.btn, *self.adv_form.tab_btns.values(), self.adv_form.pages)
        yield "advanced, first half"
        # (under Which website to copy: where the Website values come from, eq.site_values' words; a condition, so
        # in sight, not behind an ⓘ: UI-RULES 26. A screen reader reads its words: no tooltip of its own)
        self.site_note = QLabel()
        self.site_note.setWordWrap(True)
        theme.mark(self.site_note, role="muted")
        rest = [(t, rows() if callable(rows) else rows) for t, rows in sections[2:]]
        self.adv_form.add_sections(rest)  # (Website, Saved files, History)
        self._label_checks(self.adv_form)
        tab_order(self.adv.btn, *self.adv_form.tab_btns.values(), self.adv_form.pages)  # (the new tabs with the others)
        # (no refresh() here: the page's next step, the result card's, shows the settings (show_settings), which
        # refreshes all of them: the same work done twice, a few ms, 2026-11-10)
        yield "advanced, second half"

    # ---------------------------------------------------------------- the Target card's Adjust (AutoEQ Local's)
    def _adjust_panel(self, C, get, changed, make_auto, say, target_row, target_under):
        """Adjust… on the Target row (target_row) and its summary under it (target_under): a button after Add… that
        opens the window (the UI audit, 2026-11-08), the target's adjustments as listener800's Custom DF has them. The
        window is made at its first use (adjust(), make_adjust_window)."""
        self.adjust_btn = QPushButton("Adjust…")
        icons.put(self.adjust_btn, "eq")  # (every button in the row with its symbol, UI-RULES 9)
        self.adjust_btn.setToolTip("Fine-tune the target's tilt, bass, half-tilt, ear gain, treble, and air")
        help_window.tag(self.adjust_btn, "#target-adjust")
        self.adjust_btn.clicked.connect(self.open_adjust)
        target_row.addWidget(self.adjust_btn)
        self.adjust_summary = QLabel()
        theme.mark(self.adjust_summary, role="muted")
        self.adjust_summary.hide()
        target_under.addWidget(self.adjust_summary)
        self.adjust_row = self.adjust_btn  # (the Guide's name for what opens it)

    def adjust(self):
        """Adjust…'s window (make_adjust_window's parts), made the first time it is needed (a click on Adjust…, or
        code that uses one of its parts), with the values as they are then; the same window after that."""
        if self._adjust is None:
            self._adjust = self.make_adjust_window()
            self._show_adjust_values()
        return self._adjust

    def adjust_open(self):
        """Adjust…'s window shows (never made by the question)."""
        return self._adjust is not None and self._adjust.dlg.isVisible()

    def make_adjust_window(self):
        """Adjust…'s window, its parts in a namespace (dlg, form, rows, plot, curve, footer, reset_btn, save_btn): the
        page's own (adjust(): made at its first use), or one for the Guide's demo (shown in the Guide's frame, then
        thrown away)."""
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
        # (Value has no tooltip of its own: the ⓘ after it has the words about the values, the text survey 2026-11-23)
        for col, (text, tip) in enumerate((("Value", ""),
                                           ("Hz", "Shelf start frequency, or center frequency for half-tilt and ear gain"),
                                           ("Q", "Shelf slope, or ear gain width")), 1):
            h = QLabel(text)
            if tip:
                h.setToolTip(tip)
            theme.mark(h, role="muted")
            if col == 1:  # (the words about the values: behind the ⓘ after Value, the UI audit)
                head = QWidget()
                hh = QHBoxLayout(head)
                hh.setContentsMargins(0, 0, 0, 0)
                hh.setSpacing(4)
                hh.addWidget(h)
                hh.addWidget(InfoMark("Tilt: − adds bass, + adds treble. Use ↑/↓ or the scroll wheel in any field. Hz "
                                      "and Q apply only when value isn't 0.", "the values"))
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
        out.reset_btn.setToolTip("Reset all adjustments to 0")
        out.reset_btn.clicked.connect(self.clear_adjustments)
        out.save_btn = QPushButton("Save as a target…")
        out.save_btn.setToolTip("Save and select as a new target, resetting adjustments to 0")
        out.save_btn.clicked.connect(self.page.save_adjusted_target)
        help_window.tag(out.save_btn, "#target-save")
        b = placed(v, QHBoxLayout())
        b.addWidget(out.reset_btn)
        b.addWidget(out.save_btn)
        b.addStretch(1)
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
        """Adjust…: its window, in front (made at the first click, adjust())."""
        dlg = self.adjust_window
        if not dlg.isVisible():
            from ui.window_parts import fit_to_screen
            fit_to_screen(dlg, (560, 560), (460, None))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        self.redraw_adjust()

    def redraw_adjust(self):
        if self.adjust_open():
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
        if self.adjust_open():
            self.adjust_footer.say("Target adjustments reset to 0.", undo=undo)
        else:
            self.page.notify("Target adjustments reset to 0.", undo)

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
        shown = self.page.site_shown() if hasattr(self.page, "site_shown") else {}
        if shown.get(path, self.get(path)) == value:  # (a Website value: against the one its box shows)
            return
        self.eq_settings.set_path(S, path, value)
        # (a Website value typed is yours, "custom ↺", with every choice of Which website to copy; the choice itself
        # changes no value: the curves loaded again bring the website's, eq.site_values)
        if self.is_auto_path(path) and path not in self.your_values():
            self.your_values().append(path)
        if path == "best_fit.layout":  # (a graphic EQ app's layout chosen here: its sliders too)
            a = next((x for x in self.page.meta.get("eq_apps", []) if x["kind"] == "graphic" and x["layout"] == value), None)
            if a:
                self.page.apply_bands(a)
        self.page.changed(curves=any(path.startswith(k) for k in CURVE_KEYS))
        self.refresh()

    def make_auto(self, path):
        S = self.page.S
        back = [p for p in self.your_values() if p == path or not path]
        S["auto"]["manual"] = [p for p in self.your_values() if p != path] if path else []
        for p in back:  # (a Website value made automatic: the app's own in the settings, as at the start)
            if p.startswith("site."):
                self.eq_settings.set_path(S, p, self.eq_settings.get_path(self.page.meta["defaults"], p))
        # (a Website value made automatic: the curves again, with the website's value: the critique of feature 5)
        self.page.changed(curves=path is None or path.startswith("site."))
        self.page.refresh_auto()
        self.refresh()

    def auto_switched(self, on):
        self.page.S["auto"]["enabled"] = bool(on)
        # (the curves again: the Website values are filled in, or stay, only with the automatic settings on)
        self.page.changed(curves=True)
        self.refresh()  # (no message: the tick box and the Settings row's summary show the change, the text survey)

    def load_your_filters(self):
        f, _ = QFileDialog.getOpenFileName(self.fold, "Load an EQ file", "", "EQ files (*.txt *.cfg *.csv);;All files (*)")
        if not f:
            return
        import textfile
        r = self.page.svc.call("/api/filters/parse", {"text": textfile.read(f)})
        if r.get("error") or not r.get("filters"):
            self.page.status(r.get("error") or f"No filters found in “{f}”.", 8000)
            return
        lines = self._apo_lines(r["filters"])
        self.changed("best_fit.start_filters", "\n".join(lines))
        self.page.status(f"Loaded {len(lines)} starting filter{'' if len(lines) == 1 else 's'} for Best fit.", 5000)

    @staticmethod
    def _apo_lines(filters):
        """Filters as Equalizer APO lines (how "Start from your filters" keeps them); switched-off ones left out."""
        return [f"Filter {i}: ON {({'PK': 'PK', 'LSQ': 'LSC', 'HSQ': 'HSC'}).get(x.get('type', 'PK'), 'PK')} "
                f"Fc {x['freq']:g} Hz Gain {x['gain']:g} dB Q {x['q']:g}"
                for i, x in enumerate([x for x in filters if x.get("enabled", True) is not False], 1)]

    def edit_your_filters(self):
        """The Your filters window, with the filter editor (as AutoEQ Local's own-filters table and sliders): OK writes
        them back.
        It ends as every window does (.claude/notes/UI-RULES.md 1, 4, 6, 7): its own message line (what the editor
        changed: it was said in the main window's, behind it), OK (Enter's, in the accent; Enter in a box being typed in
        is the box's: it pressed OK and closed the window) and Cancel; it opens within the screen."""
        from ui.filter_editor import FilterEditor
        from ui.window_parts import Footer, enter_presses, fit_to_screen
        text = self.page.S["best_fit"].get("start_filters", "")
        r = self.page.svc.call("/api/filters/parse", {"text": text}) if text.strip() else {"filters": []}
        if r.get("error"):  # (an empty table, and OK then wiped your text: review 2)
            QMessageBox.warning(self.fold, "Your filters", f"{r['error']}\n\nFix the text and click Edit as a table… "
                                "again.")
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
        note = QLabel("Best fit starts from enabled filters and adds more, adjusting them unless “Keep them as they are” "
                      "is checked."
                      + (" OK clears non-filter lines, Preamp lines, and disabled filters from “Start from your filters”."
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
        row = placed(v, QHBoxLayout())
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
            # (8 px more between the two tabs: 14 px apart, as on the result card. At 6 px apart the focus frame,
            # which keeps clear of the next tab, was 1 px from their words: the user, 2026-11-17)
            if view == "sliders":
                row.addSpacing(8)
            row.addWidget(b)
        row.addSpacing(12)
        add = QPushButton("Add filter")
        icons.put(add, "add")
        add.clicked.connect(lambda: (filters.append({"enabled": True, "type": "PK", "freq": 1000, "gain": 0, "q": 1}),
                                     ed.rebuild()))
        ed.empty_focus = add  # (the last filter's ✕ pressed: the focus on Add filter, as on the result card)
        row.addWidget(add)
        sort = QPushButton("Sort")  # (the result card's commands: UI-RULES 19, the UI audit, 2026-11-08)
        icons.put(sort, "sort")
        sort.setToolTip("Sort filters by frequency")
        sort.clicked.connect(lambda: (filters.sort(key=lambda x: x["freq"]), ed.rebuild()))
        row.addWidget(sort)
        row.addStretch(1)
        v.addWidget(ed, 1)
        v.addWidget(footer)
        enter_presses(dlg, ok_btn)
        ok = dlg.exec()
        dlg.deleteLater()  # (each opening made a window of its own, kept hidden under the Settings fold)
        if ok:
            self.changed("best_fit.start_filters", "\n".join(self._apo_lines(filters)))
            n = sum(f.get('enabled', True) is not False for f in filters)
            if n:
                self.page.status(f"Best fit starts from {n} filter{'' if n == 1 else 's'}.", 5000)
            elif text.strip():  # (never "0 filters": the box had text and OK emptied it; an empty box that stays
                # empty has nothing to tell)
                self.page.status("Cleared starting filters for Best fit.", 5000)

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
            # ("custom" in the accent as text: 4.5:1 on the card, light or dark. A website's fixed value is used
            # over yours: its line as it is)
            if n.get("path") in mine and not n.get("lock"):
                # (a note that is a sentence, as the limits of an EQ app, loses its last period here: "(overridden)"
                # follows it as the last word of the line)
                text = text[:-1] if text.endswith(".") and not text.endswith("..") else text
                items.append(f"<li><span style='color:{t['accent_text']}'>custom</span> · Automatic: {text} "
                             "(overridden)</li>")
            else:
                items.append(f"<li>{text}</li>")
        self.why.setText("<ul style='margin-left:-20px'>" + "".join(items) + "</ul>" if items else
                         ("Select a target and measurement to enable automatic settings." if on
                          else "Automatic settings are off."))
        self.why_head.setText(f"About these settings ({len(notes)})" if notes else "About these settings")
        self.redraw_adjust()
        # (only the custom values whose boxes show now: one of another method, or AutoEQ TrebleStartFrom with Best
        # fit, was named with no box in sight to reset it)
        seen = [p for p in mine if any(f.applies(p) for f in self.forms())]
        self.mine_box.setVisible(on and bool(seen))
        # (eq.settings' names for these settings: the automatic notes that name a setting use them too)
        self.mine_text.setText("Custom values: " + ", ".join(self.eq_settings.AUTO_NAMES.get(p, p) for p in seen)
                               + " (click “custom ↺” to reset)")
        tags = {p: ("yours" if p in mine else "auto") for p in self.auto_paths} if on else {}
        if S["site"].get("profile") == "custom":  # (Other: the app fills none of the Website values)
            tags = {p: t for p, t in tags.items() if not p.startswith("site.")}
        elif getattr(self.page, "site_as_is", False):  # (an EQ from History's values, as they are: not automatic)
            tags = {p: t for p, t in tags.items() if not (p.startswith("site.") and t == "auto")}
        locks = self.site_locks()
        self._site_parts()
        # (the Website values the curves have, shown in their boxes; never saved: page.site_shown)
        shown = self.page.site_shown() if hasattr(self.page, "site_shown") else {}
        for form in self.forms():
            form.refresh(tags, locks, shown)
        if self._adjust is not None:  # (not made yet: adjust() shows the values as it makes it)
            self._show_adjust_values()
        adj = self.adjusted()
        self.adjust_summary.setText(("Adjusted: " + self._adjust_summary_text()) if adj else "")
        self.adjust_summary.setVisible(adj)
        # (what the sweep tries: a website's fixed values in place of the boxes')
        sw = dict(S["site_sweep"], **{p.split(".", 1)[1]: v for p, (v, _tip) in locks.items() if p.startswith("site_sweep.")})
        # (no filter rows: their box is above the line)
        self.sweep_note.setText("Testing: frequency to "
                                f"{', '.join(f'{v / 1000:g} kHz' for v in sw['freq_high'])} · gain "
                                f"{', '.join(f'{r[0]:g} to {r[1]:g}' for r in sw['gain_ranges'])} · Q to {fmt_list(sw['q_max'])}. "
                                "Edit in More settings › Website best settings.")
        lay = next((l for l in self.page.meta.get("layouts", []) if l["key"] == S["best_fit"]["layout"]), {})
        self.fixed_note.setText(f"{lay.get('name', '')}: Best fit adjusts band gains only. Edit range and step in "
                                "More settings › Best fit." if lay.get("fixed") else "")
        # (settings.js mineCount: the lines the run reads)
        n = len([s for s in (S["best_fit"].get("start_filters") or "").splitlines()
                 if s.strip() and not s.strip().lower().startswith(("#", ";", "//", "preamp")) and ": off" not in s.lower()])
        self.mine_note.setText(f"{n} starting filter{'s' if n != 1 else ''}" if n else "")
        hz = lambda v: f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"
        self.fold.summary.setText(f"{'automatic' if on else 'manual'} · error range "
                                  f"{hz(S['scoring']['band_hz'][0])}–{hz(S['scoring']['band_hz'][1])}")
        # (only what the method in use has in More settings: the layout and the limits are Best fit's, the search
        # ranges are Website AutoEQ: find the best settings', CPU cores both's; the first item with a capital letter)
        own = {"best_fit": "layout, limits, CPU, ", "site_sweep": "search ranges, CPU, "}.get(S["mode"], "")
        words = own + "website values, saved files, and history"
        self.adv.summary.setText(words[0].upper() + words[1:])

    def forms(self):
        """The forms of the settings' boxes made so far: Rig change's (in the Target and Measurement card), Settings'
        and More settings'."""
        return [f for f in (getattr(self, "rig_form", None), getattr(self, "form", None),
                            getattr(self, "adv_form", None)) if f is not None]

    def site_locks(self):
        """{path: (value, reason)}: the Website methods' boxes that the website of the curves fixes (no gain boxes or no
        Q boxes on its AutoEQ panel: eq.site_values), with a Website method; else {}."""
        S, info = self.page.S, getattr(self.page, "site_info", None) or {}
        if S["mode"] not in ("site_single", "site_sweep") or S["site"].get("profile") == "custom":
            return {}
        return {p: (x["value"], x["tip"]) for p, x in (info.get("locks") or {}).items()
                if isinstance(x, dict) and "value" in x and "tip" in x}

    def _site_parts(self):
        """Which website to copy has the choice in use (a website no list has any longer: by its name or address), and
        the gray line under it says where the values come from (the curves' answer, eq.site_values)."""
        info = getattr(self.page, "site_info", None) or {}
        self.site_note.setText(info.get("note") or "")
        f = self.adv_form.fields.get("site.profile")
        prof = self.page.S["site"].get("profile")
        if f is not None and isinstance(prof, str) and f.box.findData(prof) < 0:
            name = info.get("site") if info.get("site_url") and "site:" + info["site_url"] == prof else None
            f.box.addItem(name or prof[5:] or prof, prof)

    def _show_adjust_values(self):
        """Adjust…'s window (once made) with the values as they are: its boxes, a gain's Hz and Q greyed while it's 0
        (they do nothing then), Clear and Save usable once adjusted."""
        w, S = self._adjust, self.page.S
        w.form.refresh()
        for amount, deps in w.rows.items():
            for f in deps:
                f.box.setEnabled(bool(S["target_adjust"].get(amount)))
        adj = self.adjusted()
        w.reset_btn.setEnabled(adj)  # (always there, so nothing moves; usable once adjusted)
        w.save_btn.setEnabled(adj)
