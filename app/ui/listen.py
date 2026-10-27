"""Listen: hear the EQ through your own IEM or headphone (AutoEQ Local's Listen card and its EQs to compare, natively).

- Play / Stop; the sound (music, pink or white noise, a sweep, a tone, your own file); volume; level matching
- the versions: EQ off, the selected EQ (as edited) and this IEM's EQs to compare; click one or press 1-9; Blind
  test hides which is which until Reveal; Ears: both the same, or a different version in each ear (Swap)
- the tone's frequency slider (and its range); the sweep's and the tone's frequency shown on the graph
- your EQs to compare (eq.service /api/listen: one list per IEM, kept between sessions, 12 at most): The selected
  EQ, An EQ file…, Paste filters… (each with Windows 11's add symbol); each renamed in place, on the graph or not, ✕
  removed
- the device's own EQ (Devices) plays on top of what you hear here: said, with a button to switch it off

The look is Windows 11's (2026-10-23): Windows' symbols beside Play / Stop, Undo, Choose a file…, Swap and the three
that add an EQ to compare (its add symbol, as every other Add has, where they began with a typed "+"); each version
marked on its left in its curve's colour on the graph, and the same colour beside each EQ to compare (the property
listen_mark, matched in ui\\theme_sheet.py's listen part, so light, dark and Windows' accent change them live); the
versions in as many rows as the card needs; your EQs to compare in columns, each ✕ quiet (no fill until pointed at)
and each name box named for a screen reader; the device's own EQ said in Windows 11's warning card
(window_parts.warning_card: its symbol, the words, Switch it off at the right), as the banner.

The sound itself is ui/audio.py (sounddevice); nothing plays until Play.
"""
import math
import os

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLayout, QLineEdit, QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget)

import textfile
from ui import help_window, icons, tasks, theme, window_parts
from ui.search_combo import SearchCombo

SOUNDS = [("music", "Music (a short loop)"), ("pink", "Pink noise"), ("white", "White noise"), ("sweep", "Sweep 20 Hz-20 kHz"),
          ("tone", "Tone (choose a frequency)"), ("file", "Your own file…")]
COLOURS = ["c3", "c5", "c4", "c2"]  # (the EQs to compare on the graph, in turn)


class _PlayButton(QPushButton):
    """Play / Stop, the card's main action (the accent), with Windows 11's symbol beside its word: ▶ beside Play, ■
    beside Stop, whoever sets the word (the Guide's demo shows Stop on it too). A ▶ or ■ written before the word, as
    the words were before the symbols, is left out: the symbol shows it."""
    SYMBOLS = {"Play": "play", "Stop": "stop"}

    def __init__(self):
        super().__init__()
        self.symbol = None  # (the symbol's name shown, ui\\icons.py's GLYPHS)
        theme.mark(self, primary=True)
        self.setText("Play")
        self.ensurePolished()  # (the stylesheet's type size, for the width below)
        words = max(self.fontMetrics().horizontalAdvance(w) for w in ("Play", "Stop", "Preparing…"))
        self.setMinimumWidth(words + 22 + 2 * 11 + 12)  # (the same width whatever it says: the symbol, the padding)

    def setText(self, text):
        word = text.lstrip("▶■ ")
        super().setText(word)
        symbol = self.SYMBOLS.get(word, self.symbol or "play")  # ("Preparing…" keeps Play's)
        if symbol != self.symbol:
            self.symbol = symbol
            icons.put(self, symbol)


class _Rows(QLayout):
    """Buttons side by side at their own widths, onto a new row when the next one doesn't fit: Listen's versions (up
    to 14, their names as long as you made them; in one row they made the card, and so all of Make an EQ, wider than
    the window)."""

    def __init__(self, parent, gap=6):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self._items, self._gap = [], gap

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._place(QRect(0, 0, width, 0), False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._place(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _place(self, rect, move):
        """Each one in its place (move), in rows from the left: the height they take."""
        x, y, row = rect.x(), rect.y(), 0
        for item in self._items:
            if item.isEmpty():  # (one hidden)
                continue
            hint = item.sizeHint()
            if x > rect.x() and x + hint.width() > rect.x() + rect.width():
                x, y, row = rect.x(), y + row + self._gap, 0
            if move:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._gap
            row = max(row, hint.height())
        return y + row - rect.y()


class Listen(QGroupBox):
    def __init__(self, page):
        super().__init__("Listen")
        self.page = page
        self.engine = None
        self.playing, self.blind_order, self.revealed = False, None, False
        self.file_data, self.file_name = None, ""
        self.pins, self.pins_for = [], None  # this IEM's EQs to compare, and which IEM they're for
        st = page.sw.s.get("listen") or {}
        v = QVBoxLayout(self)
        sub = QLabel("Hear the EQ through your own IEM or headphone. Start with the volume low.")
        theme.mark(sub, role="muted")
        v.addWidget(sub)
        row = QHBoxLayout()
        self.play_btn = _PlayButton()
        self.play_btn.clicked.connect(self.toggle)
        row.addWidget(self.play_btn)
        self.src = SearchCombo()
        for k, name in SOUNDS:
            self.src.addItem(name, k)
        self.src.sort_items()
        self.src.setCurrentIndex(max(0, self.src.findData(st.get("src", "music") if st.get("src") != "file" else "music")))
        self.src.activated.connect(lambda _i: self.source_changed())
        row.addWidget(self.src)
        row.addWidget(QLabel("Volume"))
        self.vol = QSlider(Qt.Horizontal)
        self.vol.setAccessibleName("Volume")
        self.vol.setRange(-60, 0)
        self.vol.setValue(int(st.get("vol", -24)))
        self.vol.setFixedWidth(150)
        self.vol.valueChanged.connect(self.volume_changed)
        row.addWidget(self.vol)
        self.vol_lab = QLabel()
        row.addWidget(self.vol_lab)
        self.lm = QCheckBox("Level-matched")
        self.lm.setToolTip("Every version at the same loudness, so you compare the EQ, not the volume")
        self.lm.setChecked(st.get("lm", True))
        self.lm.toggled.connect(self.lm_changed)
        row.addWidget(self.lm)
        for w, key in ((self.src, "#snd-src"), (self.vol, "#snd-vol"), (self.lm, "#snd-lm")):
            help_window.tag(w, key)
        row.addStretch(1)
        v.addLayout(row)
        # the tone and the file
        self.tone_row = QWidget()
        tr = QHBoxLayout(self.tone_row)
        tr.setContentsMargins(0, 0, 0, 0)
        tr.addWidget(QLabel("Tone"))
        self.tone = QSlider(Qt.Horizontal)
        self.tone.setAccessibleName("Tone frequency")
        self.tone.setRange(0, 10000)
        self.tone.setValue(int(st.get("tone", 0.5) * 10000))
        self.tone.valueChanged.connect(self.tone_changed)
        tr.addWidget(self.tone, 1)
        self.tone_lab = QLabel()
        self.tone_lab.setMinimumWidth(80)
        tr.addWidget(self.tone_lab)
        tr.addWidget(QLabel("from"))
        # (the range as you left it: kept with the slider's place, which is a fraction of it)
        saved = [st.get(k) for k in ("tone_from", "tone_to")]
        saved = [int(v) if isinstance(v, (int, float)) and math.isfinite(v) else d for v, d in zip(saved, (20, 20000))]
        self.tone_from = QLineEdit(str(saved[0]))
        self.tone_to = QLineEdit(str(saved[1]))
        for b in (self.tone_from, self.tone_to):
            b.setFixedWidth(70)
            b.editingFinished.connect(self.tone_range_done)
        tr.addWidget(self.tone_from)
        tr.addWidget(QLabel("to"))
        tr.addWidget(self.tone_to)
        tr.addWidget(QLabel("Hz"))
        for w in (self.tone_from, self.tone_to):
            help_window.tag(w, "#tone-from")
        v.addWidget(self.tone_row)
        self.file_row = QWidget()
        fr = QHBoxLayout(self.file_row)
        fr.setContentsMargins(0, 0, 0, 0)
        pick = QPushButton("Choose a file…")
        icons.put(pick, "open")
        pick.clicked.connect(self.choose_file)
        fr.addWidget(pick)
        self.file_lab = QLabel("mp3, flac, wav, ogg …")
        theme.mark(self.file_lab, role="muted")
        fr.addWidget(self.file_lab, 1)
        v.addWidget(self.file_row)
        # the versions
        ears = QHBoxLayout()
        self.ears = SearchCombo()
        self.ears.addItem("Both ears hear the same version", "both")
        self.ears.addItem("A different version in each ear", "split")
        self.ears.sort_items()
        self.ears.setCurrentIndex(max(0, self.ears.findData("split" if st.get("ears") == "split" else "both")))
        self.ears.activated.connect(lambda _i: self.ears_changed())
        ears.addWidget(self.ears)
        self.blind = QCheckBox("Blind test")
        self.blind.setToolTip("The versions as A, B, C … in a random order, until Reveal")
        self.blind.toggled.connect(self.blind_changed)
        ears.addWidget(self.blind)
        self.reveal_btn = QPushButton("Reveal")
        self.reveal_btn.clicked.connect(self.reveal)
        ears.addWidget(self.reveal_btn)
        ears.addStretch(1)
        v.addLayout(ears)
        self.ab_box = QWidget()
        self.ab = _Rows(self.ab_box)  # (in as many rows as the card needs)
        self.version_group = QButtonGroup(self)  # (one of them chosen; the same group however often they're redrawn)
        v.addWidget(self.ab_box)
        self.split_row = QWidget()
        sr = QHBoxLayout(self.split_row)
        sr.setContentsMargins(0, 0, 0, 0)
        sr.addWidget(QLabel("Left"))
        self.left = SearchCombo()
        self.left.activated.connect(lambda _i: self.sides_changed())
        sr.addWidget(self.left, 1)
        sr.addWidget(QLabel("Right"))
        self.right = SearchCombo()
        self.right.activated.connect(lambda _i: self.sides_changed())
        sr.addWidget(self.right, 1)
        swap = QPushButton("Swap")
        icons.put(swap, "swap")
        swap.clicked.connect(self.swap)
        sr.addWidget(swap)
        for w, key in ((self.ears, "#snd-ears"), (self.blind, "#snd-blind"), (self.left, "#snd-left"),
                       (self.right, "#snd-right")):
            help_window.tag(w, key)
        v.addWidget(self.split_row)
        self.note = QLabel()
        self.note.setWordWrap(True)
        theme.mark(self.note, role="muted")
        v.addWidget(self.note)
        self.apo_off = QPushButton("Switch it off")
        self.apo_off.clicked.connect(self.device_eq_off)
        # (Windows 11's warning card, as the banner's: the warning symbol, the words wrapping, the button at the right)
        self.apo_box, self.apo_text = window_parts.warning_card("", self.apo_off)
        v.addWidget(self.apo_box)
        # your EQs to compare
        head = QLabel("Your EQs to compare")
        theme.mark(head, role="section")
        v.addWidget(head)
        self.pins_box = QWidget()
        self.pins_lay = QVBoxLayout(self.pins_box)  # (holds their table, drawn again with each change: render_pins)
        self.pins_lay.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self.pins_box)
        self.undo_row = QWidget()
        ur = QHBoxLayout(self.undo_row)
        ur.setContentsMargins(0, 0, 0, 0)
        self.undo_text = QLabel()
        theme.mark(self.undo_text, role="muted")
        ur.addWidget(self.undo_text, 1)
        self.undo_btn = QPushButton("Undo")
        icons.put(self.undo_btn, "undo")
        ur.addWidget(self.undo_btn)
        self.undo_row.hide()
        v.addWidget(self.undo_row)
        self._undo_timer = QTimer(self, singleShot=True, interval=15000, timeout=self.undo_row.hide)
        help_window.tag(head, "snd_list")
        add = QHBoxLayout()
        # (Windows 11's add symbol before their words, as every other Add: they began with a typed "+"; a screen reader
        # reads what each does, the symbol being read as nothing)
        for text, name, fn in (("The selected EQ", "Add the selected EQ", self.add_selected),
                               ("An EQ file…", "Add an EQ file…", self.add_file),
                               ("Paste filters…", "Add filters you paste…", self.add_paste)):
            b = QPushButton(text)
            icons.put(b, "add")
            b.setAccessibleName(name)
            b.clicked.connect(fn)
            add.addWidget(b)
            if text == "The selected EQ":
                self.add_sel_btn = b
        add.addStretch(1)
        v.addLayout(add)
        self.active, self.picked = "sel", False
        self.left_key, self.right_key, self.sides_picked = "off", "sel", False
        self.marker_timer = QTimer(self, interval=100, timeout=self.page.draw_marker)
        self.source_changed(save=False)
        self.volume_changed()
        self.tone_lab.setText(self._tone_text(self.tone_hz()))  # (the tone's frequency shown from the start)
        self.refresh()

    # ---------------------------------------------------------------- settings kept (the switcher's, app-wide)
    def _keep(self, **kw):
        """Listen's choices into the app's settings, written half a second after the last change (a slider moves
        through many values) and without redrawing the other screens (nothing else shows them)."""
        sw = self.page.sw
        sw.s["listen"] = dict(sw.s.get("listen") or {}, **kw)
        if not hasattr(self, "_keep_timer"):
            from PySide6.QtWidgets import QApplication
            self._keep_timer = QTimer(self, singleShot=True, interval=500, timeout=sw.save)
            QApplication.instance().aboutToQuit.connect(sw.save)
        self._keep_timer.start()

    # ---------------------------------------------------------------- the versions
    def versions(self):
        """[(key, label, filters, colour)]: EQ off, the selected EQ, this IEM's EQs to compare. colour: the name of
        its curve's colour on the graph (theme.tokens()): EQ off the measurement's, the selected EQ "with the EQ"'s
        (never the accent: that's Windows' colour, not a curve's), each EQ to compare its own (COLOURS)."""
        out = [("off", "EQ off", [], "meas")]
        run, r = self.page.current()
        if r:
            what = "by hand" if run.get("mode") == "manual" else f"run {run.get('n', 1)}"
            out.append(("sel", f"Selected EQ ({what}{', edited' if self.page.edited() else ''})",
                        self.page.active(), "with_eq"))
        for i, p in enumerate(self.pins):
            out.append((p["key"], p["name"], [f for f in p["filters"] if f.get("enabled", True) is not False],
                        COLOURS[p.get("color", i) % len(COLOURS)]))
        return out

    def refresh(self):
        """After a new result, an edit, or another IEM: the versions and the buttons."""
        vs = self.versions()
        keys = [k for k, *_ in vs]
        if self.engine:
            self.engine.set_versions([(k, label, f) for k, label, f, _ in vs])
        has_sel = "sel" in keys
        if self.active not in keys or (not self.picked and has_sel):
            self.active = "sel" if has_sel else "off"
        first_eq = "sel" if has_sel else next((k for k in keys if k != "off"), "off")
        if not self.sides_picked:
            self.left_key, self.right_key = "off", first_eq
        self.left_key = self.left_key if self.left_key in keys else "off"
        self.right_key = self.right_key if self.right_key in keys else first_eq
        if self.blind_order and sorted(self.blind_order) != sorted(keys):
            self.new_blind()
        self._apply()
        self.render_ab()
        self.render_pins()
        self.render_apo()
        self.add_sel_btn.setEnabled(has_sel)

    def update_sound(self):
        """Only what's heard (a filter dragged on the EQ graph: many changes a second): each version's filters into the
        sound, the buttons left as they are (refresh draws them again)."""
        if self.engine:
            self.engine.set_versions([(k, label, f) for k, label, f, _ in self.versions()])

    def _apply(self):
        if self.engine:
            e = self.engine
            e.active, e.ears, e.left, e.right = self.active, self.ears.currentData(), self.left_key, self.right_key

    def choose(self, key):
        if any(k == key for k, *_ in self.versions()):
            self.active, self.picked = key, True
            self._apply()
            self.render_ab()

    def choose_number(self, n):
        """Keys 1-9: the nth version as the buttons show them (in a blind test, the nth letter)."""
        order = self._order()
        if 0 <= n < len(order):
            self.choose(order[n][0])

    def _order(self):
        vs = self.versions()
        if self.blind.isChecked() and self.blind_order:
            by = {v[0]: v for v in vs}
            return [by[k] for k in self.blind_order if k in by]
        return vs

    def render_ab(self):
        while self.ab.count():
            w = self.ab.takeAt(0).widget()
            if w:
                if isinstance(w, QPushButton):
                    self.version_group.removeButton(w)
                w.hide()
                w.setParent(None)
                w.deleteLater()
        split = self.ears.currentData() == "split"
        self.ab_box.setVisible(not split)
        self.split_row.setVisible(split)
        self.blind.setEnabled(not split)
        self.reveal_btn.setVisible(self.blind.isChecked() and not self.revealed and not split)
        blind = self.blind.isChecked()
        for i, (key, label, _f, colour) in enumerate(self._order()):
            name = chr(65 + i) + (f" = {label}" if self.revealed else "") if blind else label
            b = QPushButton(f"{i + 1}  {name}")
            b.setCheckable(True)
            b.setChecked(key == self.active)
            if not blind or self.revealed:  # (its curve's colour on its left: theme_sheet.py's listen part)
                theme.mark(b, listen_mark=colour)
            if self.engine and (not blind or self.revealed):
                s = next((s for s in self.engine.slots if s["key"] == key and not s.get("fading")), None)
                if s:
                    b.setToolTip(f"Level {s['gain_db']:.1f} dB")
            b.clicked.connect(lambda _=False, k=key: self.choose(k))
            self.version_group.addButton(b)
            self.ab.addWidget(b)
        for box, key in ((self.left, self.left_key), (self.right, self.right_key)):
            box.blockSignals(True)
            box.clear()
            for k, label, *_ in self.versions():
                box.addItem(label, k)
            box.sort_items()
            box.setCurrentIndex(max(0, box.findData(key)))
            box.blockSignals(False)
        note = ""
        if self.page.curves:
            note = f"Listen with the {self.page.curves['name']}. "
        if len(self.versions()) < 2:
            note += "Run the EQ or keep EQs to compare to switch between versions. "
        if split:
            note += "Swap sides too: your ears differ. "
        # (each ear chooses its own version there: the keys would only change one that isn't heard)
        self.note.setText(note + ("" if split else "Keys 1-9 switch versions. ") + "Start with the volume low.")

    def ears_changed(self):
        self._keep(ears=self.ears.currentData())
        if self.ears.currentData() == "split" and self.blind.isChecked():
            self.blind.setChecked(False)
        self._apply()
        self.render_ab()

    def sides_changed(self):
        self.left_key, self.right_key, self.sides_picked = self.left.currentData(), self.right.currentData(), True
        self._apply()

    def swap(self):
        self.left_key, self.right_key, self.sides_picked = self.right_key, self.left_key, True
        self._apply()
        self.render_ab()

    def new_blind(self):
        import random
        keys = [k for k, *_ in self.versions()]
        random.shuffle(keys)
        self.blind_order, self.revealed = keys, False

    def blind_changed(self, on):
        if on:
            self.new_blind()
            self.choose(self.blind_order[0])
        else:
            self.blind_order = None
        self.render_ab()

    def reveal(self):
        self.revealed = True
        self.render_ab()

    # ---------------------------------------------------------------- playing
    def ensure_engine(self):
        if self.engine is None:
            from ui import audio
            self.engine = audio.Engine(audio.card_rate())
            self.engine.volume_db = self.vol.value()
            self.engine.level_match = self.lm.isChecked()
            self.refresh()

    def toggle(self):
        self.stop() if self.playing else self.play()

    def play(self):
        self.ensure_engine()
        from ui import audio
        kind = self.src.currentData()
        sr = self.engine.sr
        if kind == "file":
            if self.file_data is None:  # (chosen first, then played once it's read)
                self.choose_file(play_after=True)
                return
            data = self.file_data
        elif kind == "tone":
            data = None
        else:
            if kind == "music" and not hasattr(self, "_music"):
                self.play_btn.setText("Preparing…")
                self.play_btn.repaint()
            cache = {"music": "_music", "pink": "_pink", "white": "_white", "sweep": "_sweep"}[kind]
            if not hasattr(self, cache):
                setattr(self, cache, audio.groove(sr) if kind == "music" else audio.sweep(sr) if kind == "sweep"
                        else audio.noise(sr, kind == "pink"))
            data = getattr(self, cache)
        self.engine.set_source(kind, data)
        self.tone_changed()
        try:
            self.engine.start()
        except Exception as e:  # noqa: BLE001 - no sound card, a driver refusing: said
            self.play_btn.setText("Play")
            QMessageBox.warning(self, "Listen", f"The sound card couldn't be opened: {e}")
            return
        self.playing = True
        self.play_btn.setText("Stop")
        if kind in ("tone", "sweep"):
            self.marker_timer.start()

    def stop(self):
        if self.engine:
            self.engine.stop()
        self.playing = False
        self.play_btn.setText("Play")
        self.marker_timer.stop()
        self.page.draw_marker()

    def marker_hz(self):
        """The frequency being played (the tone's, the sweep's), for the graph's marker; None otherwise."""
        if not self.playing or not self.engine:
            return None
        if self.engine.kind == "tone":
            return self.engine.tone_hz
        return self.engine.sweep_hz()

    def source_changed(self, save=True):
        kind = self.src.currentData()
        self.tone_row.setVisible(kind == "tone")
        self.file_row.setVisible(kind == "file")
        if save:
            self._keep(src=kind)
        if self.playing:
            self.play()

    def volume_changed(self, *_):
        self.vol_lab.setText(f"{self.vol.value()} dB")
        if self.engine:
            self.engine.volume_db = self.vol.value()
        self._keep(vol=self.vol.value())

    def lm_changed(self, on):
        if self.engine:
            self.engine.set_level_match(on)
        self._keep(lm=bool(on))
        self.render_ab()

    def tone_range(self):
        """The tone's From and To as used: numbers (not "nan"), within 20 Hz to 20 kHz and the sound card's top, To
        not below From."""
        def num(box, d):
            try:
                v = float(box.text())
            except ValueError:
                return d
            return v if math.isfinite(v) else d  # ("nan" or "inf" typed: Play stopped working for every sound)
        top = min(20000, (self.engine.sr if self.engine else 48000) / 2 - 1)
        lo = min(max(num(self.tone_from, 20), 20), top)
        return lo, min(max(num(self.tone_to, 20000), lo), top)

    def tone_hz(self):
        lo, hi = self.tone_range()
        return lo * (hi / lo) ** (self.tone.value() / 10000)

    def tone_range_done(self):
        """A From or To typed: the boxes show the values used (5 Hz shows as 20), kept for the next start."""
        lo, hi = self.tone_range()
        self.tone_from.setText(f"{round(lo)}")
        self.tone_to.setText(f"{round(hi)}")
        self._keep(tone_from=round(lo), tone_to=round(hi))
        self.tone_changed()

    @staticmethod
    def _tone_text(f):
        return f"{f / 1000:.2f} kHz" if f >= 1000 else f"{round(f)} Hz"

    def tone_changed(self, *_):
        f = self.tone_hz()
        self.tone_lab.setText(self._tone_text(f))
        if self.engine:
            self.engine.tone_hz = f
        self._keep(tone=self.tone.value() / 10000)
        self.page.draw_marker()

    def choose_file(self, play_after=False):
        """Your own file, read (and converted to the sound card's rate) off the window's thread. (m4a/AAC isn't
        offered: the sound library can't read it.)"""
        f, _ = QFileDialog.getOpenFileName(self, "Your own audio", os.path.expanduser("~"),
                                           "Audio (*.mp3 *.flac *.wav *.ogg *.opus *.aiff *.aif);;All files (*)")
        if not f:
            if play_after or (self.playing and self.file_data is None):  # (nothing to play: not the old sound)
                self.stop()
            return
        self.ensure_engine()
        from ui import audio
        name, sr = os.path.basename(f), self.engine.sr
        self.file_lab.setText(f"Loading {name}…")
        self._file_seq = seq = getattr(self, "_file_seq", 0) + 1

        def done(data, err):
            if seq != self._file_seq:  # (another file chosen while this one was read: that one, not this)
                return
            if err is not None:
                self.file_lab.setText(f"Couldn't read {name}: try mp3, wav, flac or ogg.")
                if play_after:
                    self.stop()
                return
            self.file_data, self.file_name = data, name
            self.file_lab.setText(f"{name} ({round(len(data) / sr)} s, loops)")
            self.src.setCurrentIndex(self.src.findData("file"))
            self.source_changed()
            if play_after and not self.playing:
                self.play()
        tasks.background(lambda: audio.read_file(f, sr), done, owner=self)

    # ---------------------------------------------------------------- the device's own EQ (Devices)
    def render_apo(self):
        sw = self.page.sw
        key, rec = sw.playing()
        name = sw.profile_name(rec["active"]) if rec else None
        if rec and sw.trial and sw.trial["key"] == key:  # (an EQ tried for a few minutes plays instead of its own)
            name = sw.trial["name"]
        on = bool(name) and sw.apo.set_up()
        self.apo_box.setVisible(on)
        if on:
            from switcher.core import shown
            self.apo_text.setText(f"{shown(rec)} has its own EQ on (“{name}”, Devices): it plays on top of what you "
                                  "hear here, so “EQ off” isn't off. Switch it off while you compare.")

    def device_eq_off(self):
        key, rec = self.page.sw.playing()
        if rec:
            self.page.sw.set_active(key, None)
            from switcher.core import shown
            self.page.status(f"{shown(rec)}'s own EQ is off (switch it on again in Devices or the tray).", 8000)
        self.render_apo()

    # ---------------------------------------------------------------- your EQs to compare (one list per IEM)
    def load_pins(self, device):
        if device == self.pins_for:
            return
        r = self.page.svc.call("/api/listen", {"device": device})
        self.pins = r.get("eqs") or [] if not r.get("error") else []
        self.max_pins = r.get("max", 12)
        self.pins_for = device
        self.refresh()

    def save_pins(self):
        """This IEM's list saved; refused, the list is read back as it's kept (the change undone). Returns whether
        it was saved."""
        if not self.pins_for:
            return False
        r = self.page.svc.call("/api/listen/save", {"device": self.pins_for, "eqs": self.pins})
        if r.get("error"):
            QMessageBox.warning(self, "EQs to compare", r["error"])
            device, self.pins_for = self.pins_for, None
            self.load_pins(device)
            self.page.draw()
            return False
        self.pins = r.get("eqs", self.pins)
        self.refresh()
        self.page.draw()
        return True

    def add(self, name, filters, note=""):
        """An EQ into this IEM's list (the same filters twice: refused). Returns whether it went in."""
        if not self.pins_for:
            QMessageBox.information(self, "EQs to compare", "Choose a measurement first: each IEM or headphone has its "
                                    "own list of EQs to compare.")
            return False
        filters = [dict(f) for f in filters if f.get("enabled", True) is not False and f.get("freq") and f.get("q")]
        if not filters:
            QMessageBox.information(self, "EQs to compare", "That EQ has no filters to compare.")
            return False
        sig = lambda fl: sorted((f.get("type", "PK"), float(f["freq"]), float(f["gain"]), float(f["q"])) for f in fl
                                if f.get("enabled", True) is not False)
        if any(sig(p["filters"]) == sig(filters) for p in self.pins):
            self.page.status("That EQ is in the list already.", 5000)
            return False
        if len(self.pins) >= getattr(self, "max_pins", 12):
            QMessageBox.information(self, "EQs to compare", "The list is full (12): remove one first.")
            return False
        import uuid
        used = {p.get("color", i) % len(COLOURS) for i, p in enumerate(self.pins)}  # (a colour not in use, as eqlist.js)
        colour = next((i for i in range(len(COLOURS)) if i not in used), len(self.pins))
        self.pins.append({"key": uuid.uuid4().hex[:8], "name": name[:80], "filters": filters, "note": note, "shown": True,
                          "color": colour})
        if not self.save_pins():
            return False
        self.page.status(f"“{name}” is in your EQs to compare for the {self.pins_for}: hear it in Listen.", 6000)
        return True

    def add_selected(self):
        run, r = self.page.current()
        if not r:
            return
        st = self.page.stats()
        from ui.eq_page import MODE_SHORT
        self.add(f"Run {run.get('n', 1)}: {MODE_SHORT.get(run['mode'], 'EQ')}, "
                 f"{st['n']} filters{' (edited)' if self.page.edited() else ''}", [dict(f) for f in self.page.active()],
                 f"error {st['rms']:.2f} dB" if st["rms"] is not None else "")

    def add_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "An EQ file", os.path.expanduser("~"), "EQ files (*.txt *.cfg *.csv);;All files (*)")
        if not f:
            return
        try:
            text = textfile.read(f)
        except OSError as e:  # (no rights, an offline OneDrive file, one another program holds)
            QMessageBox.warning(self, "EQs to compare", f"Couldn't read it: {e}")
            return
        self._add_text(text, os.path.splitext(os.path.basename(f))[0], f"from {os.path.basename(f)}")

    def add_paste(self):
        from ui.eq_page_parts import paste_dialog
        got = paste_dialog(self, "Paste filters", "Name (e.g. Crinacle's EQ)",
                           "Equalizer APO lines, or one filter per line as “frequency gain Q”:")
        if got:
            self._add_text(got[1], got[0] or "Pasted EQ", "pasted")

    def _add_text(self, text, name, note):
        r = self.page.svc.call("/api/filters/parse", {"text": text})
        if r.get("error") or not r.get("filters"):
            QMessageBox.warning(self, "EQs to compare", r.get("error") or "No filters found in it.")
            return
        self.add(name, [dict(f, enabled=True) for f in r["filters"]], note)

    def render_pins(self):
        """Your EQs to compare as a table, a row each, in columns: its colour (its curve's on the graph), its name
        (edit it to rename it), its filters and where it's from, Graph, ✕."""
        # (the table before: hidden now, deleted a moment later, as the control that changed the list is in it)
        while self.pins_lay.count():
            w = self.pins_lay.takeAt(0).widget()
            if w:
                w.hide()
                w.deleteLater()
        table = QWidget()
        grid = QGridLayout(table)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(1, 1)
        self.pins_lay.addWidget(table)
        if not self.pins:
            empty = QLabel("None yet: keep the result (Keep to compare) or add one below." if self.pins_for else
                           "Choose a measurement: each IEM has its own list.")
            theme.mark(empty, role="muted")
            grid.addWidget(empty, 0, 0, 1, 5)
        for i, p in enumerate(self.pins):
            sw = QLabel("■")
            theme.mark(sw, listen_mark=COLOURS[p.get("color", i) % len(COLOURS)])  # (theme_sheet.py's listen part)
            grid.addWidget(sw, i, 0)
            name = QLineEdit(p["name"])
            name.setAccessibleName(f"Name of {p.get('name') or 'this EQ'}")  # (a screen reader read it as nothing)
            name.editingFinished.connect(lambda p=p, name=name: self._rename(p, name.text()))
            grid.addWidget(name, i, 1)
            note = QLabel(f"{len(p['filters'])} filter{'' if len(p['filters']) == 1 else 's'}" +(f" · {p['note']}" if p.get("note") else ""))
            theme.mark(note, role="muted")
            grid.addWidget(note, i, 2)
            graph = QCheckBox("Graph")
            graph.setChecked(p.get("shown", True))
            graph.toggled.connect(lambda on, p=p: (p.__setitem__("shown", on), self.save_pins()))
            grid.addWidget(graph, i, 3)
            x = QPushButton("✕")
            theme.mark(x, quiet=True)  # (no fill until pointed at, as every ✕)
            x.setAccessibleName(f"Remove {p.get('name') or 'this EQ'} from the EQs to compare")
            graph.setAccessibleName(f"Show {p.get('name') or 'this EQ'} on the graph")
            x.setToolTip("Remove from the list")
            x.clicked.connect(lambda _=False, p=p: self._remove(p))
            grid.addWidget(x, i, 4)

    def _rename(self, p, text):
        text = text.strip()[:80]
        if text and text != p["name"]:
            p["name"] = text
            self.save_pins()

    def _remove(self, p):
        self.pins = [x for x in self.pins if x is not p]
        if self.save_pins():
            device = self.pins_for
            self.undo_text.setText(f"“{p['name']}” removed from your EQs to compare.")
            if getattr(self, "_undo_connected", False):  # (only what was connected: no warning)
                self.undo_btn.clicked.disconnect()
            self._undo_connected = True
            self.undo_btn.clicked.connect(lambda: self._put_back(device, p))
            self.undo_row.show()
            self._undo_timer.start()

    def _put_back(self, device, p):
        """Undo of ✕ (eqlist.js undoRemove): back in the list it came from, also after another IEM was chosen."""
        self.undo_row.hide()
        if device == self.pins_for:
            self.add(p["name"], p["filters"], p.get("note", ""))
            return
        r = self.page.svc.call("/api/listen", {"device": device})
        eqs = (r.get("eqs") or []) + [p]
        r = self.page.svc.call("/api/listen/save", {"device": device, "eqs": eqs})
        if r.get("error"):
            QMessageBox.warning(self, "EQs to compare", r["error"])
        else:
            self.page.status(f"“{p['name']}” is back in the EQs to compare for {device}.", 6000)
