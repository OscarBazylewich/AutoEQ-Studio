"""The Make an EQ screen's two folds of settings (AutoEQ Local's Settings fold and Settings › Advanced, natively):

Settings (the ones used most):
- Automatic settings: on or off, "Why these values" (each value and the fact about your files it comes from; "yours"
  where you've set your own), "Set by you" (each one handed back with ↺, or all)
- the method's own values: Website AutoEQ's six; the website sweep's summary; Best fit's filter counts, shelves and
  your own filters to start from
- Scoring: the range the match is judged over, how a result is picked
- Target: the rig conversion
The Target card's Adjust (AutoEQ Local's, beside the target): tilt, bass, half-tilt, ear gain, treble, air, each
with − and +; Reset adjustments and Save as a target… once adjusted.
Advanced: Best fit's layout, bands, shelves, limits and penalties; the website sweep's lists; the website's level
matching and its code; saved files (the formats, pre-amp, Q decimals); History; CPU cores.

A value the automatic settings fill in becomes "yours" once you change it (kept through new files
until handed back); with them off nothing changes by itself. Settings that change the curves (target adjustments,
the scored range, the website's levelling, the rig conversion) draw the graph again.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton, QToolButton, QVBoxLayout,
                               QWidget)

from ui import help_window, theme
from ui.forms import Field, Fold, Form, Limits, fmt_list

ADJUST_GAINS = ("tilt", "bass_gain", "halftilt_gain", "ear_gain", "treble_gain", "air_gain")  # (eq.service's)
CURVE_KEYS = ("target_adjust.","site.", "scoring.band_hz", "files.", "rig_convert.")  # (settings.js)
LABELS = {  # (auto.js: what "Set by you" calls each one)
    "scoring.band_hz.1": "Scored up to", "site_single.rows": "Filter rows", "site_single.freq_high": "Frequency to",
    "site_single.gain_min": "Gain from", "site_single.gain_max": "Gain to", "site_single.q_max": "Q to",
    "site_sweep.filter_rows": "Filter rows to try", "site_sweep.freq_high": "Frequency “to” values",
    "site_sweep.gain_ranges": "Gain ranges", "site_sweep.q_max": "Q “to” values", "best_fit.filter_counts": "Filter counts",
    "best_fit.freq_range.1": "Filters up to", "best_fit.gain_min": "Max cut", "best_fit.gain_max": "Max boost values",
    "best_fit.q_max": "Q max values", "best_fit.low_shelf": "Low shelf", "best_fit.high_shelf": "High shelf",
    "scoring.pick": "Pick", "scoring.ear_db": "Audible limit", "best_fit.fight_penalty": "Fighting-filter penalties"}
FORMATS = [("apo", "Equalizer APO / squiglink filters (.txt)"), ("graphic", "GraphicEQ for Wavelet (.txt)"),
           ("poweramp", "Poweramp / Poweramp Equalizer preset (.json)"),
           ("uapp", "USB Audio Player PRO parametric EQ preset (.xml)"),
           ("soundsource", "SoundSource headphone EQ, macOS (.txt)"), ("voicemeeter", "Voicemeeter bus EQ, Windows (.xml)"),
           ("rockbox", "Rockbox EQ preset, music players (.cfg)"),
           ("convolution", "Convolution impulse response: Viper4Android, JamesDSP, EasyEffects, Roon… (.wav)"),
           ("report", "An HTML report")]


def _muted_label(text):
    lab = QLabel(text)
    theme.mark(lab, role="muted")
    return lab


def _opts(values, names=None):
    return [(v, (names or {}).get(v, f"{v:g}" if isinstance(v, float) else str(v))) for v in values]


class EqSettings:
    def __init__(self, page):
        self.page = page
        m = page.meta
        self.limits = Limits(m.get("limits", {}), m.get("limit_pairs", []))
        self.auto_paths = [p for ps in (m.get("auto_paths") or {}).values() for p in ps]
        from eq import settings as eq_settings
        self.eq_settings = eq_settings
        C = eq_settings.CHOICES
        S = lambda: page.S
        mode = lambda *ms: lambda: S()["mode"] in ms
        lay = lambda: next((l for l in m.get("layouts", []) if l["key"] == S()["best_fit"]["layout"]), {})
        fixed = lambda: S()["mode"] == "best_fit" and bool(lay().get("fixed"))
        free = lambda: S()["mode"] == "best_fit" and not lay().get("fixed")
        shelves = lambda: free() and lay().get("shelves", True)
        multi = mode("site_sweep", "best_fit")
        audible = lambda: multi() and S()["scoring"]["pick"] == "audible"
        get, changed, back, say = self.get, self.changed, self.hand_back, lambda t: page.status(t, 6000)

        # ---------------------------------------------------------------- Settings (the fold)
        self.fold = Fold("Settings")
        self.fold.add(self._auto_box())
        self.sweep_note = QLabel()
        self.sweep_note.setWordWrap(True)
        theme.mark(self.sweep_note, role="muted")
        self.fixed_note = QLabel()
        self.fixed_note.setWordWrap(True)
        theme.mark(self.fixed_note, role="muted")
        load_mine = QPushButton("Load an EQ file…")
        load_mine.clicked.connect(self.load_own_filters)
        self.mine_note = QLabel()
        theme.mark(self.mine_note, role="muted")
        mine_row = QWidget()
        mr = QHBoxLayout(mine_row)
        mr.setContentsMargins(0, 0, 0, 0)
        mr.addWidget(load_mine)
        edit_mine = QPushButton("Edit as a table…")
        edit_mine.setToolTip("Your own filters as a table or sliders (each one's type, frequency, gain and Q)")
        edit_mine.clicked.connect(self.edit_own_filters)
        mr.addWidget(edit_mine)
        mr.addWidget(self.mine_note, 1)
        self.method_title = QLabel()
        self.form = Form([
            ("Website AutoEQ: one run", [
                ("Filter rows", [("site_single.rows", "num")], mode("site_single")),
                ("Frequency from", [("site_single.freq_low", "num"), ("site_single.freq_high", "num")], mode("site_single")),
                ("Gain from (dB)", [("site_single.gain_min", "num"), ("site_single.gain_max", "num")], mode("site_single")),
                ("Q from", [("site_single.q_min", "num"), ("site_single.q_max", "num")], mode("site_single"))]),
            ("Website AutoEQ: find best settings", [(self.sweep_note, [], mode("site_sweep"))]),
            ("Best fit", [
                ("Filter counts to try", [("best_fit.filter_counts", "intlist", None, "e.g. 1-10")], free),
                ("Shelf", [("best_fit.low_shelf", "check")], shelves),
                (self.fixed_note, [], fixed),
                ("Start from your own filters", [("best_fit.start_filters", "block", None,
                                                  "Equalizer APO lines, e.g. Filter: ON PK Fc 1000 Hz Gain -3 dB Q 1")],
                 mode("best_fit")),
                ("", [("best_fit.start_keep", "check")], lambda: S()["mode"] == "best_fit" and S()["best_fit"]["start_filters"].strip()),
                (mine_row, [], mode("best_fit"))]),
            ("Scoring", [
                ("Score from (Hz)", [("scoring.band_hz.0", "num"), ("scoring.band_hz.1", "num")]),
                ("Pick", [("scoring.pick", "choice", [("audible", "Simplest that sounds the same as the target"),
                                                      ("lowest", "Lowest error")])], multi),
                ("Audible limit (dB)", [("scoring.ear_db", "num")], audible),
]),
            ("Target", [
                ("Rig conversion", [("rig_convert.enabled", "check")])]),
        ], self.limits, get, changed, back, say)
        self.fold.add(self.form)
        self._label_checks()
        self._adjust_panel(C, get, changed, back, say)

        # ---------------------------------------------------------------- Advanced
        self.adv = Fold("Advanced")
        layouts = [(l["key"], f"{l['group']}: {l['name']}" if l["group"] not in ("Any",) else l["name"])
                   for l in m.get("layouts", [])]
        self.adv_form = Form([
            ("Best fit", [
                ("Layout", [("best_fit.layout", "choice", layouts)], mode("best_fit")),
                ("Band frequencies (Hz)", [("best_fit.bands.freqs", "numlist", None, "e.g. 31, 62, 125, 250…")],
                 lambda: fixed() and S()["best_fit"]["layout"] == "bands"),
                ("Q of each band", [("best_fit.bands.q", "num")], lambda: fixed() and S()["best_fit"]["layout"] == "bands"),
                ("Sliders from (dB)", [("best_fit.bands.gain_min", "num"), ("best_fit.bands.gain_max", "num")], fixed),
                ("Slider step (dB)", [("best_fit.bands.step", "choice", _opts(C["best_fit.bands.step"]))], fixed),
                ("Low shelf Hz", [("best_fit.low_shelf_freq.0", "num"), ("best_fit.low_shelf_freq.1", "num")],
                 lambda: shelves() and S()["best_fit"]["low_shelf"]),
                ("Filters from (Hz)", [("best_fit.freq_range.0", "num"), ("best_fit.freq_range.1", "num")], free),
                ("Max cut (dB)", [("best_fit.gain_min", "num")], free),
                ("Max boost values (dB)", [("best_fit.gain_max", "numlist")], free),
                ("Q from", [("best_fit.q_min", "num")], free),
                ("Q max values", [("best_fit.q_max", "numlist")], free),
                ("Fighting-filter penalties", [("best_fit.fight_penalty", "numlist")], free)]),
            ("Website sweep", [
                ("Filter rows to try", [("site_sweep.filter_rows", "intlist", None, "e.g. 4-10 or 4, 6, 8")]),
                ("Frequency from", [("site_sweep.freq_low", "num")]),
                ("Frequency “to” values", [("site_sweep.freq_high", "numlist")]),
                ("Gain ranges", [("site_sweep.gain_ranges", "ranges", None, "min..max, …")]),
                ("Q from", [("site_sweep.q_min", "num")]),
                ("Q “to” values", [("site_sweep.q_max", "numlist")])]),
            ("Website", [
                ("Which website to copy", [("site.profile", "choice", [("listener800", "listener800 (5128 databases)"),
                                                                        ("squig.link lab", "squig.link"), ("custom", "Custom")])]),
                ("Level matching", [("site.normalization", "choice", [("Hz~", "Hz~ (average over 4 octaves)"),
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
                ("Pre-amp rounding", [("export.preamp_rounding", "choice", [("safe", "Safe (round down)"), ("site", "Like squiglink")])]),
                ("Extra headroom (dB)", [("export.extra_headroom", "num")]),
                ("Q decimals in saved files", [("export.q_decimals", "num")])]),
            ("History", [
                ("History keeps", [("history.keep", "choice", [("saved", "EQs you save or copy"),
                                                               ("all", "Every run's result, and the EQs you save")])]),
                ("", [("history.eqd_before", "check")])]),
            ("This PC", [("CPU cores (0 = all but one)", [("performance.cores", "num")])]),
        ], self.limits, get, changed, back, say)
        self.adv.add(self.adv_form)
        self._label_checks(self.adv_form)

    # ---------------------------------------------------------------- the Target card's Adjust (AutoEQ Local's)
    def _adjust_panel(self, C, get, changed, back, say):
        """Adjust, on the Target card: the target's tilt, bass, half-tilt, ear gain, treble and air (listener800's
        Custom DF) as a table: Amount with − and +, Hz and Q (greyed while the amount is 0); Reset adjustments and
        Save as a target… (usable once adjusted).
        adjust_btn (with adjust_summary) opens adjust_panel; eq_page puts both on the card."""
        self.adjust_btn = QToolButton()
        self.adjust_btn.setText("Adjust")
        self.adjust_btn.setCheckable(True)
        self.adjust_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        theme.mark(self.adjust_btn, fold=True)
        self.adjust_btn.setToolTip("Tilt, bass, half-tilt, ear gain, treble and air: the target made darker, brighter, bassier…")
        help_window.tag(self.adjust_btn, "#target-adjust")
        self.adjust_btn.toggled.connect(self._adjust_open)
        self.adjust_summary = QLabel()
        theme.mark(self.adjust_summary, role="muted")
        self.adjust_row = QWidget()
        r = QHBoxLayout(self.adjust_row)
        r.setContentsMargins(0, 0, 0, 0)
        r.addWidget(self.adjust_btn)
        r.addWidget(self.adjust_summary, 1)
        # a table: one row each, Amount (with − and +), Hz and Q always in their columns (greyed while the amount is 0),
        # so nothing appears or moves as you type (a row of Hz and Q under the amount, popping up, was hard to follow)
        self.adjust_form = form = Form([], self.limits, get, changed, back, say,
                                       steps={"target_adjust.tilt": 0.1,
                                              **{f"target_adjust.{k}": 0.5 for k in ADJUST_GAINS[1:]}})
        grid_w = QWidget()
        g = QGridLayout(grid_w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        for col, (text, tip) in enumerate((("Amount", "How much: + raises, − lowers (tilt: − darker, + brighter)"),
                                           ("Hz", "Where it acts: a shelf from there on, ear gain around it"),
                                           ("Q", "How steep (a shelf) or how wide (ear gain)")), 1):
            h = QLabel(text)
            h.setToolTip(tip)
            theme.mark(h, role="muted")
            g.addWidget(h, 0, col)

        def field(path, kind, options=None, width=64):
            f = Field(form, path, kind, options)
            f.committed.connect(changed)
            f.handed_back.connect(back)
            if kind == "num":
                f.box.setFixedWidth(width)
            form.fields[path] = f
            return f
        self.adjust_rows = {}
        rows = (("tilt", "Tilt", "dB/oct", None, None), ("bass", "Bass", "dB", "bass_freq", "bass_q"),
                ("halftilt", "Half-tilt", "dB", "halftilt_freq", None), ("ear", "Ear gain", "dB", "ear_freq", "ear_q"),
                ("treble", "Treble", "dB", "treble_freq", "treble_q"), ("air", "Air", "dB", "air_freq", "air_q"))
        for i, (k, name, unit, hz, q) in enumerate(rows, 1):
            amount = "tilt" if k == "tilt" else k + "_gain"
            lab = QLabel(name)
            g.addWidget(lab, i, 0)
            a = field("target_adjust." + amount, "num")
            a.layout().addWidget(_muted_label(unit))
            a.box.setAccessibleName(f"{name} amount ({unit})")
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
                g.addWidget(_muted_label("whole range"), i, 2, 1, 2)
            if q:
                f = field("target_adjust." + q, "choice", _opts(C["target_adjust." + q]))
                f.box.setAccessibleName(f"{name} Q")
                g.addWidget(f, i, 3)
                deps.append(f)
            self.adjust_rows[amount] = deps
        g.setColumnStretch(4, 1)
        hint = QLabel("+ raises, − lowers (tilt: − darker, + brighter); ↑ ↓ or the mouse wheel in a box work too. "
                      "Hz and Q apply once the amount isn't 0.")
        hint.setWordWrap(True)
        theme.mark(hint, role="muted")
        self.reset_adjust_btn = QPushButton("Reset adjustments")
        self.reset_adjust_btn.setToolTip("Every adjustment back to 0 (Undo puts them back)")
        self.reset_adjust_btn.clicked.connect(self.reset_adjustments)
        self.save_target_btn = QPushButton("Save as a target…")
        self.save_target_btn.setToolTip("Keep the target as adjusted here as a target of your own (the adjustments go "
                                        "back to 0)")
        self.save_target_btn.clicked.connect(self.page.save_adjusted_target)
        help_window.tag(self.save_target_btn, "#target-save")
        # (the page as its parent until the Target card takes it: opened before, with no parent, it was a window)
        self.adjust_panel = QWidget(self.page)
        v = QVBoxLayout(self.adjust_panel)
        v.setContentsMargins(0, 4, 0, 0)
        v.addWidget(grid_w)
        v.addWidget(hint)
        b = QHBoxLayout()
        b.addWidget(self.reset_adjust_btn)
        b.addWidget(self.save_target_btn)
        b.addStretch(1)
        v.addLayout(b)
        self.adjust_btn.setChecked(self.adjusted())  # (open when the target is adjusted already)
        self._adjust_open(self.adjust_btn.isChecked())

    def adjusted(self):
        return any(self.page.S["target_adjust"].get(k) for k in ADJUST_GAINS)

    def _adjust_open(self, on):
        self.adjust_btn.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.adjust_panel.setVisible(on)

    def reset_adjustments(self):
        """Reset adjustments: the target as it is (every adjustment's default); Undo puts them back."""
        before = dict(self.page.S["target_adjust"])
        self.page.S["target_adjust"] = dict(self.page.meta["defaults"]["target_adjust"])
        self.page.changed(curves=True)

        def undo():
            self.page.S["target_adjust"] = before
            self.page.changed(curves=True)
        self.page.notify("The target's adjustments are back to 0.", undo)

    def _adjust_summary_text(self):
        """Beside Adjust: what's adjusted (“tilt −1 dB/oct, bass +4 dB”), or nothing."""
        a = self.page.S["target_adjust"]
        n = lambda v: f"{v:+g}".replace("-", "−")
        parts = [f"tilt {n(a['tilt'])} dB/oct"] if a.get("tilt") else []
        parts += [f"{name} {n(a[k + '_gain'])} dB" for k, name in (("bass", "bass"), ("halftilt", "half-tilt"),
                                                                  ("ear", "ear gain"), ("treble", "treble"), ("air", "air"))
                  if a.get(k + "_gain")]
        return "· " + ", ".join(parts) if parts else ""

    def _label_checks(self, form=None):
        """A checkbox's words beside it (the form's rows have them as the label: moved into the box)."""
        names = {"best_fit.low_shelf": "Low shelf (a broad bass change)",
                 "best_fit.start_keep": "Keep them exactly as they are (the fit adds filters around them)",
                 "rig_convert.enabled": "Convert the target to the measurement's rig",
                 "history.eqd_before": "Say under Measurement when you've EQ'd it before"}
        names.update({"export." + k: n for k, n in FORMATS})
        for path, f in (form or self.form).fields.items():
            if f.kind == "check" and path in names:
                f.box.setText(names[path])

    # ---------------------------------------------------------------- the automatic settings' box
    def _auto_box(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        self.auto_on = QCheckBox("Automatic settings: fitted to your measurement and target")
        self.auto_on.toggled.connect(self.auto_switched)
        help_window.tag(self.auto_on, "#auto-on")
        v.addWidget(self.auto_on)
        self.why_head = QLabel("Why these values")
        theme.mark(self.why_head, role="section")
        v.addWidget(self.why_head)
        self.why = QLabel()
        self.why.setWordWrap(True)
        self.why.setTextFormat(Qt.RichText)  # (the list)
        v.addWidget(self.why)
        self.mine_box = QWidget()
        mb = QHBoxLayout(self.mine_box)
        mb.setContentsMargins(0, 0, 0, 0)
        self.mine_text = QLabel()
        self.mine_text.setWordWrap(True)
        mb.addWidget(self.mine_text, 1)
        all_back = QPushButton("Hand all back")
        all_back.clicked.connect(lambda: self.hand_back(None))
        mb.addWidget(all_back)
        v.addWidget(self.mine_box)
        return w

    # ---------------------------------------------------------------- reading and changing
    def get(self, path):
        return self.eq_settings.get_path(self.page.S, path)

    def controlled(self, path):
        return path in self.auto_paths

    def manual(self):
        return self.page.S["auto"].setdefault("manual", [])

    def changed(self, path, value):
        """A valid value set in a box: into the settings, yours (when the automatic settings fill it), its side
        effects (settings.js onSettingSideEffects), then saved, and the curves or the automatic settings again."""
        S = self.page.S
        if self.get(path) == value:
            return
        self.eq_settings.set_path(S, path, value)
        if self.controlled(path) and path not in self.manual():
            self.manual().append(path)
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

    def hand_back(self, path):
        S = self.page.S
        S["auto"]["manual"] = [p for p in self.manual() if p != path] if path else []
        self.page.changed()
        self.page.refresh_auto()
        self.refresh()

    def auto_switched(self, on):
        self.page.S["auto"]["enabled"] = bool(on)
        self.page.changed()
        self.page.status("Automatic settings on: fitted to the measurement and target." if on
                         else "Automatic settings off: every setting stays as it is.", 5000)
        self.refresh()

    def load_own_filters(self):
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
        self.page.status(f"Loaded {len(lines)} filters to start from.", 5000)

    @staticmethod
    def _apo_lines(filters):
        """Filters as Equalizer APO lines (how "Start from your own filters" keeps them); switched-off ones left out."""
        return [f"Filter {i}: ON {({'PK': 'PK', 'LSQ': 'LSC', 'HSQ': 'HSC'}).get(x.get('type', 'PK'), 'PK')} "
                f"Fc {x['freq']:g} Hz Gain {x['gain']:g} dB Q {x['q']:g}"
                for i, x in enumerate([x for x in filters if x.get("enabled", True) is not False], 1)]

    def edit_own_filters(self):
        """Your own filters in the filter editor (as AutoEQ Local's own-filters table and sliders): OK writes them back."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox
        from ui.filter_editor import FilterEditor
        text = self.page.S["best_fit"].get("start_filters", "")
        r = self.page.svc.call("/api/filters/parse", {"text": text}) if text.strip() else {"filters": []}
        if r.get("error"):  # (an empty table, and OK then wiped your text: review 2)
            QMessageBox.warning(self.fold, "Your own filters", f"{r['error']}\n\nFix that line in the box first, then "
                                "open the table again.")
            return
        filters = [{"enabled": True, "type": x.get("type", "PK"), "freq": x["freq"], "gain": x["gain"], "q": x["q"]}
                   for x in r.get("filters") or []]
        dlg = QDialog(self.fold)
        dlg.setWindowTitle("Your own filters")
        dlg.resize(820, 560)
        v = QVBoxLayout(dlg)
        others = len([ln for ln in text.splitlines() if ln.strip()]) > len(filters)
        note = QLabel("Best fit starts from these (switched-off ones are left out): it adds filters to them, or adjusts "
                      "them too unless “Keep them exactly as they are” is ticked."
                      + (" The box's other lines (a Preamp, comments, switched-off filters) go when you press OK."
                         if others else ""))
        note.setWordWrap(True)
        theme.mark(note, role="muted")
        v.addWidget(note)
        ed = FilterEditor(self.page.meta.get("limits", {}), lambda t: self.page.status(t, 5000))
        ed.set_filters(filters)
        ed.set_view("table")
        row = QHBoxLayout()
        for name, view in (("Table", "table"), ("Sliders", "sliders")):
            b = QPushButton(name)
            b.clicked.connect(lambda _=False, view=view: ed.set_view(view))
            row.addWidget(b)
        add = QPushButton("+ Add filter")
        add.clicked.connect(lambda: (filters.append({"enabled": True, "type": "PK", "freq": 1000, "gain": 0, "q": 1}),
                                     ed.rebuild()))
        row.addWidget(add)
        row.addStretch(1)
        v.addLayout(row)
        v.addWidget(ed, 1)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        v.addWidget(btns)
        if dlg.exec():
            self.changed("best_fit.start_filters", "\n".join(self._apo_lines(filters)))
            self.page.status(f"{sum(f.get('enabled', True) is not False for f in filters)} filters to start from.", 5000)

    # ---------------------------------------------------------------- showing
    def refresh(self):
        S, a = self.page.S, self.page.auto or {}
        on = bool(S["auto"]["enabled"])
        self.auto_on.blockSignals(True)
        self.auto_on.setChecked(on)
        self.auto_on.blockSignals(False)
        mine = [p for p in self.manual() if self.controlled(p)]
        notes = (a.get("notes") or []) if on else []
        t = theme.tokens()
        items = []
        for n in notes:
            text = n["text"].replace("&", "&amp;").replace("<", "&lt;")
            if n.get("path") in mine:
                items.append(f"<li><span style='color:{t['c1']}'>yours</span> · Automatic: {text} Your value is used.</li>")
            else:
                items.append(f"<li>{text}</li>")
        self.why.setText("<ul style='margin-left:-20px'>" + "".join(items) + "</ul>" if items else
                         ("Choose a target and a measurement to fit the settings to." if on else "Automatic settings are off."))
        self.why_head.setText(f"Why these values ({len(notes)})" if notes else "Why these values")
        self.mine_box.setVisible(on and bool(mine))
        self.mine_text.setText("Set by you (kept as they are): " + ", ".join(LABELS.get(p, p) for p in mine)
                               + ".  Click a “yours ↺” tag to hand one back.")
        tags = {p: ("yours" if p in mine else "auto") for p in self.auto_paths} if on else {}
        self.form.refresh(tags)
        self.adv_form.refresh(tags)
        self.adjust_form.refresh()
        for amount, deps in self.adjust_rows.items():  # (a gain's Hz and Q greyed while it's 0: they do nothing then)
            for f in deps:
                f.box.setEnabled(bool(S["target_adjust"].get(amount)))
        adj = self.adjusted()
        self.adjust_summary.setText(self._adjust_summary_text())
        self.reset_adjust_btn.setEnabled(adj)  # (always there, so nothing moves; usable once adjusted)
        self.save_target_btn.setEnabled(adj)
        sw = S["site_sweep"]
        self.sweep_note.setText(f"The website runs tried: rows {fmt_list(sw['filter_rows'])}; frequency to "
                                f"{', '.join(f'{v / 1000:g}k' for v in sw['freq_high'])}; gain "
                                f"{', '.join(f'{r[0]:g}..{r[1]:g}' for r in sw['gain_ranges'])}; Q to {fmt_list(sw['q_max'])}. "
                                "Change them in Advanced › Website sweep.")
        lay = next((l for l in self.page.meta.get("layouts", []) if l["key"] == S["best_fit"]["layout"]), {})
        self.fixed_note.setText(f"{lay.get('name', '')}: fixed bands, only their gains are fitted (their range and "
                                "steps are in Advanced)." if lay.get("fixed") else "")
        # (settings.js mineCount: the lines the run reads)
        n = len([s for s in (S["best_fit"].get("start_filters") or "").splitlines()
                 if s.strip() and not s.strip().lower().startswith(("#", ";", "//", "preamp")) and ": off" not in s.lower()])
        self.mine_note.setText(f"{n} filter{'s' if n != 1 else ''} to start from" if n else "")
        hz = lambda v: f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"
        self.fold.summary.setText(f"· {'automatic' if on else 'automatic off: your values as they are'} · scored "
                                  f"{hz(S['scoring']['band_hz'][0])}–{hz(S['scoring']['band_hz'][1])}")
        self.adv.summary.setText("· the layout, limits and search, the website's values, saved files")
