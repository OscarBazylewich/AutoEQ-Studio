"""Editing filters: a table or sliders over the same list (AutoEQ Local's result card, natively).

Table: per filter on/off, type (Peak, Low shelf, High shelf), frequency, gain and Q (checked as typed against the EQ
part's limits for edits: edit.freq, edit.gain, edit.q; red and not used when wrong, moved to the limit on leaving),
and ✕ to delete it. Sliders: one per filter (Poweramp's look): its gain by dragging, arrow keys or the wheel
(0.1 dB steps), double-click for 0 dB; its frequency and Q under it; the pre-amp in its own column (set for you).
changed() is called after every edit (the caller works out the error, pre-amp and graph again); rebuilt() after a
filter is added or deleted; show_values() puts the values back in the boxes and sliders without making anything again
or saying it changed (a filter dragged on the EQ graph, ui/eq_page_handles.py). The editor is as tall as the view shown (a short table leaves no empty band under it).
Its look is the theme's (ui\\theme_sheet.py's eq_windows, by the object names eqw…): the table's boxes a little apart
without grid lines, Type's heading at the left over its drop-downs' words (the numbers' headings centred over them),
✕ as Windows 11's subtle buttons. The Sliders view is a graphic EQ's (2026-10-27): its sliders (_Slider), the
pre-amp's bar (_Meter), the dB scale (_Scale) and the lines across them (_SliderGrid) draw themselves in the theme's
colours, as the app's own sliders look; each filter's number as its handle on the EQ graph has it.
"""
from PySide6.QtCore import QPointF, QRectF, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QScrollArea, QSlider, QStackedWidget, QTableWidget, QToolButton, QVBoxLayout,
                               QWidget)

from ui import theme
from ui.forms import Limits, _num
from ui.search_combo import SearchCombo

TYPES = [("PK", "Peak"), ("LSQ", "Low shelf"), ("HSQ", "High shelf")]
SLIDERS_HEIGHT = 460  # (the Sliders view, with its sideways scroll bar: never one up and down)


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
            theme.mark(x, quiet=True)  # (a row's ✕: every list's one look, UI-RULES 18)
            x.setText("✕")
            x.setToolTip("Remove this filter")
            x.setAccessibleName(f"Remove filter {i + 1}")
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
        """The Sliders view, as a graphic EQ (the user's ask, 2026-10-27: more polished): the dB at the left and a line
        across at each, every filter a column (its number as on the EQ graph, its gain, its slider filled from 0 dB,
        its frequency, Q, type, on and ✕), the pre-amp's column first (set for you)."""
        holder = _SliderGrid()
        g = QGridLayout(holder)
        g.setContentsMargins(4, 6, 12, 6)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)
        lim = self.limits.of("edit.gain") or {"min": -36, "max": 35}
        top = max(12.0, *(abs(f["gain"]) * 1.2 for f in self.filters)) if self.filters else 12.0
        top = float(min(top, max(abs(lim["min"]), lim["max"])))
        top = max(6.0, (int(top + 5.999) // 6) * 6)  # (a whole number of the scale's steps: its lines at the ends)
        # rows: 0 the numbers, 1 the gain, 2 the sliders (the scale at their left), 3 frequency, 4 Q, 5 type, 6 on and ✕
        for row, name in ((1, "Gain (dB)"), (3, "Frequency (Hz)"), (4, "Q"), (5, "Type"), (6, "On")):
            lab = QLabel(name)
            theme.mark(lab, role="muted")
            g.addWidget(lab, row, 0, Qt.AlignRight | Qt.AlignVCenter)
        holder.scale = _Scale(top)
        g.addWidget(holder.scale, 2, 0, Qt.AlignRight)
        # the pre-amp's own column ("set for you": it follows the filters)
        cap = QLabel("Pre-amp")
        theme.mark(cap, role="muted")
        g.addWidget(cap, 0, 1, Qt.AlignHCenter)
        self.pre_label = pre = QLabel(self.preamp_text)
        pre.setAlignment(Qt.AlignCenter)
        theme.mark(pre, role="muted")
        g.addWidget(pre, 1, 1)
        self.pre_meter = _Meter(top)
        self.pre_meter.set_value(self._read_db(self.preamp_text))
        g.addWidget(self.pre_meter, 2, 1, Qt.AlignHCenter)
        note = QLabel("set for\nyou")
        theme.mark(note, role="muted")
        note.setAlignment(Qt.AlignCenter)
        g.addWidget(note, 3, 1, 2, 1)
        self.slider_vals = []
        self._slider_rows = []  # (per filter: its gain's words, its slider, its frequency and Q boxes: show_values)
        eq = theme.graph_colours()["eq"]
        for i, f in enumerate(self.filters):
            col = i + 2
            on = f.get("enabled", True) is not False
            # (its number as the EQ graph's handle has it: the EQ's dot, hollow when switched off, and the number)
            num = QLabel(f"<span style='color:{eq if on else theme.tokens()['muted']}'>{'●' if on else '○'}</span>"
                         f"&nbsp;{i + 1}")
            num.setTextFormat(Qt.RichText)
            theme.mark(num, role="muted")
            num.setAccessibleName(f"Filter {i + 1}")
            g.addWidget(num, 0, col, Qt.AlignHCenter)
            val = QLabel(f"{f['gain']:+.1f}")
            val.setObjectName("eqwGainValue")  # (semibold: theme_sheet's eq_windows)
            val.setAlignment(Qt.AlignCenter)
            if not on:
                theme.mark(val, role="muted")
            g.addWidget(val, 1, col)
            s = _Slider()
            s.setObjectName("eqwGain")
            s.setAccessibleName(f"Filter {i + 1} gain (dB)")
            s.setRange(int(round(-top * 10)), int(round(top * 10)))
            s.setValue(int(round(f["gain"] * 10)))
            s.setSingleStep(1)
            s.setPageStep(10)
            s.setEnabled(on)
            s.setToolTip(f"Filter {i + 1}: drag, or arrow keys (0.1 dB); double-click for 0 dB")
            s.valueChanged.connect(lambda v, f=f, val=val: (f.__setitem__("gain", round(v / 10, 1)),
                                                             val.setText(f"{v / 10:+.1f}"), self._edited()))
            g.addWidget(s, 2, col, Qt.AlignHCenter)
            holder.last = s
            # (frequency, Q and type typed or chosen as in the table, with the same limits)
            boxes = {}
            for row, key in ((3, "freq"), (4, "q")):
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
                boxes[key] = box
            self._slider_rows.append((val, s, boxes["freq"], boxes["q"]))
            typ = SearchCombo()
            for k, name in TYPES:
                typ.addItem(name.replace("Low shelf", "Low sh.").replace("High shelf", "High sh."), k)
            typ.sort_items(pinned=1)  # ("Peak" on top)
            typ.setCurrentIndex(max(0, typ.findData(f.get("type", "PK"))))
            typ.setToolTip(f"Filter {i + 1}'s type")
            typ.setAccessibleName(f"Filter {i + 1} type")
            typ.activated.connect(lambda _x, f=f, typ=typ: (f.__setitem__("type", typ.currentData()), self._edited()))
            typ.setEnabled(on)
            g.addWidget(typ, 5, col, Qt.AlignHCenter)
            foot = QWidget()
            fl = QHBoxLayout(foot)
            fl.setContentsMargins(0, 0, 0, 0)
            fl.setSpacing(2)
            tick = QCheckBox()
            tick.setChecked(on)
            tick.setToolTip(f"Filter {i + 1} on or off")
            tick.setAccessibleName(f"Filter {i + 1} on")
            tick.toggled.connect(lambda v, f=f: (f.__setitem__("enabled", v), self._edited(),
                                                 QTimer.singleShot(0, self.rebuild)))  # (not inside its own signal)
            fl.addWidget(tick)
            x = QToolButton()
            theme.mark(x, quiet=True)
            x.setText("✕")
            x.setToolTip(f"Remove filter {i + 1}")
            x.setAccessibleName(f"Remove filter {i + 1}")
            x.clicked.connect(lambda _=False, i=i: self.delete(i))
            fl.addWidget(x)
            g.addWidget(foot, 6, col, Qt.AlignHCenter)
            g.setColumnStretch(col, 1)  # (the columns share the width when they fit, as a graphic EQ's across the card)
        g.setRowStretch(7, 1)  # (room over goes under the rows, never between them)
        self.sliders_scroll.setWidget(holder)
        self.stack.setFixedHeight(SLIDERS_HEIGHT)

    @staticmethod
    def _read_db(text):
        """A pre-amp's words ("-6.6") as dB; 0 when they aren't a number."""
        try:
            return float(str(text).replace("−", "-").replace(",", "."))
        except ValueError:
            return 0.0

    def show_values(self):
        """Every filter's values shown again where they are (a filter dragged on the EQ graph): nothing made again and
        no edit said (a box being typed in is left as it is)."""
        from PySide6.QtCore import QSignalBlocker
        if self.view() == "sliders":
            for f, (val, s, fbox, qbox) in zip(self.filters, getattr(self, "_slider_rows", [])):
                with QSignalBlocker(s):
                    if s.minimum() <= round(f["gain"] * 10) <= s.maximum():
                        s.setValue(int(round(f["gain"] * 10)))
                val.setText(f"{f['gain']:+.1f}")
                for box, key in ((fbox, "freq"), (qbox, "q")):
                    if box is not None and not box.hasFocus():
                        box.setText(_num(f[key]))
            return
        t = self.table
        for i, f in enumerate(self.filters[:t.rowCount()]):
            for c, key in ((3, "freq"), (4, "gain"), (5, "q")):
                box = t.cellWidget(i, c)
                if box is not None and not box.hasFocus():
                    box.setText(_num(f[key]))

    def set_preamp_text(self, text):
        self.preamp_text = text
        if getattr(self, "pre_label", None) is not None and self.view() == "sliders":
            self.pre_label.setText(text)
            self.pre_meter.set_value(self._read_db(text))


# ---------------------------------------------------------------- the sliders' own parts, drawn in the theme's colours
THUMB_R = 9              # (the thumb's radius: 18 px across, as every slider's in the app, theme_sheet's sliders)
TRACK_PAD = THUMB_R + 3  # (room at the track's ends for the thumb)
SLIDER_H = 210           # (a gain slider's height, its scale's and the pre-amp's alike: their dB at one height)
COLUMN_W = 2 * THUMB_R + 14


def _track(h):
    """(top, bottom): where a slider's track runs in a part h px tall."""
    return TRACK_PAD, max(TRACK_PAD + 1, h - TRACK_PAD)


def _y_of(v, lo, hi, h):
    """Where a value v (lo to hi) is on a track h px tall: hi at the top."""
    top, bot = _track(h)
    return top + (hi - min(hi, max(lo, v))) / ((hi - lo) or 1) * (bot - top)


def ticks(top):
    """The dB marked on the scale and across the sliders (±top): every 6 dB (every 12 past ±24), 0 among them."""
    step = 6 if top <= 24 else 12
    n = int(top // step)
    return [k * step for k in range(-n, n + 1)]


def _bar(p, cx, y0, y1, colour):
    """A track's or a fill's 4 px bar from y0 to y1 (rounded ends)."""
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(colour))
    p.drawRoundedRect(QRectF(cx - 2, min(y0, y1), 4, max(abs(y1 - y0), 0.01)), 2, 2)


class _Slider(QSlider):
    """A filter's gain slider, as Windows 11's (the app's sliders: a 4 px track, a round thumb with the accent inside,
    bigger while pointed at), filled from 0 dB to its value, so a boost and a cut read at a glance; switched off, grey.
    A click on its track moves the thumb there (on the thumb, it keeps its place under the pointer); double-click puts
    it at 0 dB; the arrow keys and the wheel as any slider's (0.1 dB a step). Its keyboard focus: a ring round the
    thumb."""

    def __init__(self):
        super().__init__(Qt.Vertical)
        self.setAttribute(Qt.WA_Hover)
        self.setFixedSize(COLUMN_W, SLIDER_H)
        self._grab = None
        self._keys = False

    def _y(self, v):
        return _y_of(v, self.minimum(), self.maximum(), self.height())

    def _value_at(self, y):
        top, bot = _track(self.height())
        frac = min(1.0, max(0.0, (y - top) / ((bot - top) or 1)))
        return int(round(self.maximum() - frac * (self.maximum() - self.minimum())))

    def paintEvent(self, _e):
        t = theme.tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = self.width() / 2
        top, bot = _track(self.height())
        on = self.isEnabled()
        _bar(p, cx, top, bot, t["strong"] if on else t["track"])
        y0, yv = self._y(0), self._y(self.value())
        if on and abs(yv - y0) >= 1:
            _bar(p, cx, y0, yv, t["accent"])
        p.setPen(QPen(QColor(t["stroke"]), 1))
        p.setBrush(QColor(t["thumb"]))
        p.drawEllipse(QPointF(cx, yv), THUMB_R, THUMB_R)
        inner = 4 if self.isSliderDown() else 6 if on and self.underMouse() else 5  # (Windows 11's: as pointed, pressed)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t["accent"] if on else t["disabled"]))
        p.drawEllipse(QPointF(cx, yv), inner, inner)
        if self.hasFocus() and self._keys:
            p.setPen(QPen(QColor(t["ink"]), 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, yv), THUMB_R + 3, THUMB_R + 3)
        p.end()

    def focusInEvent(self, e):
        self._keys = e.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason)
        super().focusInEvent(e)

    def keyPressEvent(self, e):
        self._keys = True  # (the arrow keys: its focus shown from now on)
        super().keyPressEvent(e)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or not self.isEnabled():
            super().mousePressEvent(e)
            return
        y, yv = e.position().y(), self._y(self.value())
        self._grab = y - yv if abs(y - yv) <= THUMB_R + 2 else 0.0
        self._keys = False
        self.setFocus(Qt.MouseFocusReason)
        self.setSliderDown(True)
        self.setValue(self._value_at(y - self._grab))
        self.update()
        e.accept()

    def mouseMoveEvent(self, e):
        if self._grab is None:
            super().mouseMoveEvent(e)
            return
        self.setValue(self._value_at(e.position().y() - self._grab))
        e.accept()

    def mouseReleaseEvent(self, e):
        if self._grab is None:
            super().mouseReleaseEvent(e)
            return
        self._grab = None
        self.setSliderDown(False)
        self.update()
        e.accept()

    def mouseDoubleClickEvent(self, e):
        self.setValue(0)


class _Meter(QWidget):
    """The pre-amp's column: a slider's empty track, filled from 0 dB down to the pre-amp (set for you: no thumb)."""

    def __init__(self, top):
        super().__init__()
        self.top, self.value = top, 0.0
        self.setFixedSize(COLUMN_W, SLIDER_H)
        self.setAccessibleName("Pre-amp")

    def set_value(self, db):
        self.value = db
        self.update()

    def paintEvent(self, _e):
        t = theme.tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx = self.width() / 2
        top, bot = _track(self.height())
        _bar(p, cx, top, bot, t["track"])
        y0, yv = (_y_of(v, -self.top, self.top, self.height()) for v in (0, self.value))
        if abs(yv - y0) >= 1:
            _bar(p, cx, y0, yv, t["muted"])
        p.end()


class _Scale(QWidget):
    """The sliders' dB at their left: every mark the lines across them have (ticks), 0 among them."""

    def __init__(self, top):
        super().__init__()
        self.top = top
        self.setFixedHeight(SLIDER_H)

    def sizeHint(self):
        # (measured when it's laid out, in the font it's drawn in: measured as it was made, "+12" was cut at its left)
        return QSize(QFontMetrics(self.font()).horizontalAdvance("−24") + 8, SLIDER_H)

    def minimumSizeHint(self):
        return self.sizeHint()

    def y_of(self, db):
        return _y_of(db, -self.top, self.top, self.height())

    def paintEvent(self, _e):
        t = theme.tokens()
        p = QPainter(self)
        p.setPen(QColor(t["muted"]))
        fm = p.fontMetrics()
        for db in ticks(self.top):
            words = f"{db:+d}" if db else "0"
            y = self.y_of(db)
            p.drawText(QRectF(0, y - fm.height() / 2, self.width() - 4, fm.height()), Qt.AlignRight | Qt.AlignVCenter,
                       words.replace("-", "−"))
        p.end()


class _SliderGrid(QWidget):
    """The Sliders view's page: under its parts, a line across at each dB the scale marks (0 dB a little stronger),
    from the scale to the last slider, so the gains can be read and compared as on a graphic EQ."""

    def __init__(self):
        super().__init__()
        self.scale = self.last = None

    def paintEvent(self, _e):
        if self.scale is None:
            return
        t = theme.tokens()
        p = QPainter(self)
        sc = self.scale.geometry()
        x0 = sc.right() + 6
        x1 = self.width() - self.layout().contentsMargins().right() if self.layout() is not None else self.width()
        for db in ticks(self.scale.top):
            y = round(sc.top() + self.scale.y_of(db)) + 0.5
            p.setPen(QPen(QColor(t["stroke"] if db == 0 else t["line"]), 1))
            p.drawLine(QPointF(x0, y), QPointF(x1, y))
        p.end()
