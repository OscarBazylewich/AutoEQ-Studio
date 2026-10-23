"""Editing filters: a table or sliders over the same list (AutoEQ Local's result card, natively).

Table: per filter on/off, type (Peak, Low shelf, High shelf), frequency, gain and Q (checked as typed against the EQ
part's limits for edits: edit.freq, edit.gain, edit.q; red and not used when wrong, moved to the limit on leaving),
and ✕ to delete it. Sliders: one per filter (Poweramp's look): its gain by dragging, arrow keys or the wheel
(0.1 dB steps), double-click for 0 dB; its frequency and Q under it; the pre-amp in its own column (set for you).
changed() is called after every edit (the caller works out the error, pre-amp and graph again); rebuilt() after a
filter is added or deleted. The editor is as tall as the view shown (a short table leaves no empty band under it).
Its look is the theme's (ui\\theme_sheet.py's eq_windows, by the object names eqw…): the table's boxes a little apart
without grid lines, Type's heading at the left over its drop-downs' words (the numbers' headings centred over them),
✕ as Windows 11's subtle buttons, the pre-amp's bar as a slider's empty track.
"""
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
                               QLabel, QLineEdit, QScrollArea, QSlider, QStackedWidget, QTableWidget, QToolButton,
                               QVBoxLayout, QWidget)

from ui import theme
from ui.forms import Limits, _num
from ui.search_combo import SearchCombo

TYPES = [("PK", "Peak"), ("LSQ", "Low shelf"), ("HSQ", "High shelf")]
SLIDERS_HEIGHT = 440  # (the Sliders view, with its scroll bar)


def _hz(v):
    return f"{v / 1000:g}k" if v >= 1000 else f"{v:g}"


class FilterEditor(QWidget):
    changed = Signal()

    def __init__(self, limits_map, say=lambda t: None):
        super().__init__()
        self.limits = Limits(limits_map, [])
        self.say = say
        self.filters = []          # [{"enabled", "type", "freq", "gain", "q"}] (edited in place)
        self.preamp_text = "0.0"
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.table = QTableWidget(0, 7)
        self.table.setObjectName("eqwFilters")  # (its look: ui\theme_sheet.py's eq_windows)
        self.table.setShowGrid(False)  # (each row's boxes stand a little apart instead, as Windows 11's rows)
        self.table.setAccessibleName("Filters")
        self.table.setHorizontalHeaderLabels(["On", "#", "Type", "Frequency (Hz)", "Gain (dB)", "Q", ""])
        # (Type's heading at the left, over its drop-downs' words, as Windows 11's tables have them: centred, it sat in
        # the middle of its column, 2026-10-23; the number columns' headings stay centred, as their values are)
        self.table.horizontalHeaderItem(2).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.verticalHeader().hide()
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        for c in (0, 1, 6):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.stack.addWidget(self.table)
        self.sliders_scroll = QScrollArea()
        self.sliders_scroll.setWidgetResizable(True)
        self.sliders_scroll.setFixedHeight(SLIDERS_HEIGHT)
        self.stack.addWidget(self.sliders_scroll)
        lay.addWidget(self.stack, 0, Qt.AlignTop)  # (in a taller window, Your own filters: at the top)

    # ---------------------------------------------------------------- the list
    def set_filters(self, filters, preamp_text="0.0"):
        self.filters = filters
        self.preamp_text = preamp_text
        self.rebuild()

    def set_view(self, view):
        self.stack.setCurrentIndex(1 if view == "sliders" else 0)
        self.rebuild()

    def view(self):
        return "sliders" if self.stack.currentIndex() == 1 else "table"

    def rebuild(self):
        if self.view() == "sliders":
            self._build_sliders()
        else:
            self._build_table()

    def _edited(self):
        self.changed.emit()

    def delete(self, i):
        del self.filters[i]
        self.rebuild()
        self._edited()

    # ---------------------------------------------------------------- the table
    def _build_table(self):
        t = self.table
        t.setRowCount(0)
        for i, f in enumerate(self.filters):
            t.insertRow(i)
            on = QCheckBox()
            on.setAccessibleName(f"Filter {i + 1} on")
            on.setChecked(f.get("enabled", True) is not False)
            on.toggled.connect(lambda v, f=f, i=i: (f.__setitem__("enabled", v), self._dim(i), self._edited()))
            cell = QWidget()
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(11, 0, 0, 0)  # (under its heading, “On”: the headings' room at the sides, 11 px)
            cl.addWidget(on)
            t.setCellWidget(i, 0, cell)
            num = QLabel(str(i + 1))
            num.setAlignment(Qt.AlignCenter)
            t.setCellWidget(i, 1, num)
            typ = SearchCombo()
            for k, name in TYPES:
                typ.addItem(name, k)
            typ.sort_items(pinned=1)  # ("Peak" on top, the user's ask: TYPES starts with it)
            typ.setCurrentIndex(max(0, typ.findData(f.get("type", "PK"))))
            typ.setAccessibleName(f"Filter {i + 1} type")
            typ.activated.connect(lambda _x, f=f, typ=typ: (f.__setitem__("type", typ.currentData()), self._edited()))
            t.setCellWidget(i, 2, typ)
            for c, key in ((3, "freq"), (4, "gain"), (5, "q")):
                box = QLineEdit(_num(f[key]))
                box.setAccessibleName(f"Filter {i + 1} " + {"freq": "frequency (Hz)", "gain": "gain (dB)", "q": "Q"}[key])
                box.setAlignment(Qt.AlignCenter)
                lim = self.limits.text("edit." + key)
                box.setToolTip(f"Allowed: {lim}." if lim else "")
                box.textEdited.connect(lambda text, f=f, key=key, box=box: self._typed(f, key, box))
                box.editingFinished.connect(lambda f=f, key=key, box=box: self._left(f, key, box))
                t.setCellWidget(i, c, box)
            x = QToolButton()
            x.setObjectName("eqwDelete")  # (a subtle button: ui\theme_sheet.py's eq_windows)
            x.setText("✕")
            x.setToolTip("Delete this filter")
            x.setAccessibleName(f"Delete filter {i + 1}")
            x.clicked.connect(lambda _=False, i=i: self.delete(i))
            t.setCellWidget(i, 6, x)
            self._dim(i)
        t.resizeRowsToContents()
        rows = sum(t.rowHeight(i) for i in range(t.rowCount()))
        height = min(560, t.horizontalHeader().height() + rows + 2 * t.frameWidth() + 2)
        t.setFixedHeight(height)
        self.stack.setFixedHeight(height)  # (as tall as the table: the Sliders view's height left no empty band)

    def _dim(self, i):
        """A switched-off filter's row shows paler."""
        off = self.filters[i].get("enabled", True) is False
        for c in range(1, 6):
            w = self.table.cellWidget(i, c)
            if w:
                w.setEnabled(not off)

    @staticmethod
    def _read(box):
        try:
            return float(box.text().replace(",", "."))
        except ValueError:
            return None

    def _mark(self, box, msg):
        box.setProperty("bad", True if msg else None)
        box.style().unpolish(box)
        box.style().polish(box)
        if msg:
            box.setToolTip(msg)

    def _typed(self, f, key, box):
        v = self._read(box)
        problem = ("range", "Enter a number") if v is None else self.limits.check("edit." + key, v, lambda p: None)
        if problem:
            self._mark(box, problem[1])
            return
        self._mark(box, None)
        f[key] = int(v) if key == "freq" and v == int(v) else v
        self._edited()

    def _left(self, f, key, box):
        v = self._read(box)
        if v is not None and self.limits.check("edit." + key, v, lambda p: None):
            c = self.limits.clamp("edit." + key, v)
            f[key] = c
            self.say(f"Changed to {_num(c)}. Allowed: {self.limits.text('edit.' + key)}.")
            self._edited()
        box.setText(_num(f[key]))
        self._mark(box, None)

    # ---------------------------------------------------------------- the sliders
    def _build_sliders(self):
        holder = QWidget()
        g = QGridLayout(holder)
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(4)
        lim = self.limits.of("edit.gain") or {"min": -36, "max": 35}
        top = max(12.0, *(abs(f["gain"]) * 1.2 for f in self.filters)) if self.filters else 12.0
        top = min(top, max(abs(lim["min"]), lim["max"]))
        for row, name in enumerate(("Gain", "", "Frequency", "Q", "Type", "On")):
            lab = QLabel(name)
            theme.mark(lab, role="muted")
            g.addWidget(lab, row, 0, Qt.AlignRight | Qt.AlignVCenter)
        # the pre-amp's own column ("set for you": it follows the filters)
        self.pre_label = pre = QLabel(self.preamp_text)
        pre.setAlignment(Qt.AlignCenter)
        g.addWidget(pre, 0, 1)
        bar = QFrame()
        bar.setObjectName("eqwPreamp")  # (a slider's empty track, in the theme's colour: ui\theme_sheet.py)
        bar.setFixedWidth(4)
        g.addWidget(bar, 1, 1, Qt.AlignHCenter)
        note = QLabel("Pre-amp\nset for you")
        theme.mark(note, role="muted")
        note.setAlignment(Qt.AlignCenter)
        g.addWidget(note, 2, 1, 2, 1)
        self.slider_vals = []
        for i, f in enumerate(self.filters):
            col = i + 2
            val = QLabel(f"{f['gain']:+.1f}")
            val.setAlignment(Qt.AlignCenter)
            g.addWidget(val, 0, col)
            s = _Slider(Qt.Vertical)
            s.setObjectName("eqwGain")  # (switched off: its thumb's ring with a grey dot, ui\theme_sheet.py)
            s.setAccessibleName(f"Filter {i + 1} gain (dB)")
            s.setRange(int(round(-top * 10)), int(round(top * 10)))
            s.setValue(int(round(f["gain"] * 10)))
            s.setSingleStep(1)
            s.setPageStep(10)
            s.setMinimumHeight(170)
            s.setEnabled(f.get("enabled", True) is not False)
            s.setToolTip(f"Filter {i + 1}: drag, or arrow keys (0.1 dB); double-click for 0 dB")
            s.valueChanged.connect(lambda v, f=f, val=val: (f.__setitem__("gain", round(v / 10, 1)),
                                                             val.setText(f"{v / 10:+.1f}"), self._edited()))
            g.addWidget(s, 1, col, Qt.AlignHCenter)
            # (frequency, Q and type typed or chosen as in the table, with the same limits)
            for row, key in ((2, "freq"), (3, "q")):
                box = QLineEdit(_num(f[key]))
                box.setAccessibleName(f"Filter {i + 1} " + ("frequency (Hz)" if key == "freq" else "Q"))
                box.setAlignment(Qt.AlignCenter)
                box.setFixedWidth(64)
                lim_text = self.limits.text("edit." + key)
                box.setToolTip(f"Filter {i + 1}'s {'frequency (Hz)' if key == 'freq' else 'Q'}"
                               + (f". Allowed: {lim_text}." if lim_text else ""))
                box.textEdited.connect(lambda text, f=f, key=key, box=box: self._typed(f, key, box))
                box.editingFinished.connect(lambda f=f, key=key, box=box: self._left(f, key, box))
                box.setEnabled(f.get("enabled", True) is not False)
                g.addWidget(box, row, col, Qt.AlignHCenter)
            typ = SearchCombo()
            for k, name in TYPES:
                typ.addItem(name.replace("Low shelf", "Low sh.").replace("High shelf", "High sh."), k)
            typ.sort_items(pinned=1)  # ("Peak" on top)
            typ.setCurrentIndex(max(0, typ.findData(f.get("type", "PK"))))
            typ.setToolTip(f"Filter {i + 1}'s type")
            typ.setAccessibleName(f"Filter {i + 1} type")
            typ.activated.connect(lambda _x, f=f, typ=typ: (f.__setitem__("type", typ.currentData()), self._edited()))
            typ.setEnabled(f.get("enabled", True) is not False)
            g.addWidget(typ, 4, col, Qt.AlignHCenter)
            foot = QWidget()
            fl = QHBoxLayout(foot)
            fl.setContentsMargins(0, 0, 0, 0)
            fl.setSpacing(2)
            on = QCheckBox()
            on.setChecked(f.get("enabled", True) is not False)
            on.setToolTip(f"Filter {i + 1} on or off")
            on.setAccessibleName(f"Filter {i + 1} on")
            on.toggled.connect(lambda v, f=f: (f.__setitem__("enabled", v), self._edited(),
                                               QTimer.singleShot(0, self.rebuild)))  # (not inside its own signal)
            fl.addWidget(on)
            x = QToolButton()
            x.setObjectName("eqwDelete")
            x.setText("✕")
            x.setToolTip(f"Delete filter {i + 1}")
            x.setAccessibleName(f"Delete filter {i + 1}")
            x.clicked.connect(lambda _=False, i=i: self.delete(i))
            fl.addWidget(x)
            g.addWidget(foot, 5, col, Qt.AlignHCenter)
            num = QLabel(f"#{i + 1}")
            theme.mark(num, role="muted")
            num.setAlignment(Qt.AlignCenter)
            g.addWidget(num, 6, col)
        g.setColumnStretch(len(self.filters) + 2, 1)
        self.sliders_scroll.setWidget(holder)
        self.stack.setFixedHeight(SLIDERS_HEIGHT)

    def set_preamp_text(self, text):
        self.preamp_text = text
        if getattr(self, "pre_label", None) is not None and self.view() == "sliders":
            self.pre_label.setText(text)


class _Slider(QSlider):
    """A filter's gain slider: double-click puts it at 0 dB."""

    def mouseDoubleClickEvent(self, e):
        self.setValue(0)
