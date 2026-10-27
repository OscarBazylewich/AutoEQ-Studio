"""Settings boxes, built from a list (AutoEQ Local's [data-path] boxes and limits.js, natively).

A Field shows and edits one setting (a dotted path in the EQ part's settings: "best_fit.filter_counts",
"scoring.band_hz.1"). Kinds: num, intlist ("4-10" or "4, 6, 8"), numlist, ranges ("-12..6, -10..20"), lines (one
per line), check, choice ([(value, label)]), text. A value is checked as it's typed against the EQ part's own limits
(eq.settings LIMITS and LIMIT_PAIRS: a "from" below its "to"): a wrong one turns the box red with the reason (and
isn't used); leaving a box with a value past a limit moves it to the limit and says so. Every box has its tooltip
(help_texts.HELP; a "to" box shares its "from" box's).

The automatic settings: a box they fill in has a tag beside it, "auto", or "yours ↺" once you've changed it (the tag
hands it back). A Form is a list of rows in sections; show(predicate) hides a row when it doesn't apply. Every
section's boxes start at the same place (one label column for the whole form). A Fold is a card that opens and
closes (Settings, Advanced, the tracer's Why these settings).
"""
import re

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QToolButton, QVBoxLayout, QWidget)

from ui import theme
from ui.help_texts import HELP
from ui.search_combo import SearchCombo


# ---------------------------------------------------------------- values as text, and back (settings.js)
def fmt_list(a, dash="-"):
    if not isinstance(a, list) or not a:
        return ""
    if all(isinstance(v, int) and not isinstance(v, bool) for v in a) and len(a) > 2 \
            and all(a[i] == a[i - 1] + 1 for i in range(1, len(a))):
        return f"{a[0]}{dash}{a[-1]}"
    return ", ".join(_num(v) for v in a)


def _num(v):
    """A number as a box shows it: 0.5, 16000, 0.00005 (never 5e-05)."""
    if not isinstance(v, float):
        return str(v)
    s = f"{v:g}"
    return f"{v:.10f}".rstrip("0").rstrip(".") if "e" in s else s


def parse_list(s, integers):
    out = []
    for part in [p for p in re.split(r"[,;\s]+", str(s)) if p]:
        m = re.fullmatch(r"(-?\d+)-(-?\d+)", part)
        if m and integers:
            a, b = int(m.group(1)), int(m.group(2))
            if b < a or b - a > 60:
                return None
            out += list(range(a, b + 1))
            continue
        try:
            v = float(part)
        except ValueError:
            return None
        if integers and v != int(v):
            return None
        out.append(int(v) if integers else v)
    return sorted(set(out)) if out else None


def parse_ranges(s):
    out = []
    for part in [p.strip() for p in re.split(r"[,;]+", str(s)) if p.strip()]:
        m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*(?:\.\.|to|/)\s*(-?\d+(?:\.\d+)?)", part)
        if not m or float(m.group(1)) > float(m.group(2)):
            return None
        out.append([_whole(float(m.group(1))), _whole(float(m.group(2)))])
    return out or None


def _whole(v):
    return int(v) if v == int(v) else v


class Limits:
    """The EQ part's limits (eq.settings), as limits.js checks them."""

    def __init__(self, limits, pairs):
        self.limits, self.pairs = limits, pairs

    def of(self, key):
        return self.limits.get(key)

    def text(self, key):
        lim = self.of(key)
        if not lim:
            return ""
        s = f"{_num(lim['min'])} to {_num(lim['max'])}{(' ' + lim['unit']) if lim.get('unit') else ''}"
        if lim.get("list"):
            s = "each value " + s
        if lim.get("empty"):
            s += f", or empty for {lim['empty']}"
        return s

    def check(self, key, v, get):
        """None when fine, else (kind "range" or "pair", message)."""
        lim = self.of(key)
        if not lim:
            return None
        flat = [x for x in (sum(v, []) if v and isinstance(v[0], list) else v) if x is not None] \
            if isinstance(v, list) else ([] if v is None else [v])
        if any(x < lim["min"] or x > lim["max"] for x in flat):
            return "range", "Allowed: " + self.text(key)
        if lim.get("int") and any(x != int(x) for x in flat):
            return "range", "Whole numbers only: " + self.text(key)
        lo_of = lambda x: min(sum(x, []) if x and isinstance(x[0], list) else x) if isinstance(x, list) else x
        hi_of = lambda x: max(sum(x, []) if x and isinstance(x[0], list) else x) if isinstance(x, list) else x
        for lo, hi, strict in self.pairs:
            if key not in (lo, hi):
                continue
            a = hi_of(v) if key == lo else get(lo)
            b = lo_of(v) if key == hi else lo_of(get(hi))
            if a is None or b is None or not (a > b or (strict and a == b)):
                continue
            unit = (" " + lim["unit"]) if lim.get("unit") else ""
            return "pair", (f"Must be {'below' if strict else 'at most'} the “to” value ({_num(b)}{unit})" if key == lo
                            else f"Must be {'above' if strict else 'at least'} the “from” value ({_num(a)}{unit})")
        return None

    def clamp(self, key, v):
        lim = self.of(key)
        if not lim or v is None:
            return v

        def c(x):
            y = min(max(x, lim["min"]), lim["max"])
            return int(round(y)) if lim.get("int") else y
        if not isinstance(v, list):
            return c(v)
        if v and isinstance(v[0], list):
            return [sorted(map(c, r)) for r in v]
        return sorted(set(map(c, v)))


CHOICE_MOST, LIST_MOST = 360, 240  # (px: a drop-down's width at most, a list of numbers' (UI-RULES 26))


def help_of(path):
    """A setting's tooltip line (a "to" box shares its "from" box's; a list's item, its list's: help_window.help_key)."""
    from ui.help_window import help_key
    h = HELP.get(help_key(path) or "")
    return (h[0] if isinstance(h, list) else h) if h else ""


# ---------------------------------------------------------------- one box
class Field(QWidget):
    """One setting's box (and, when the automatic settings fill it, its tag)."""
    committed = Signal(str, object)   # (path, value): a valid value the user set
    handed_back = Signal(str)         # (path): "yours ↺" clicked

    def __init__(self, form, path, kind, options=None, placeholder=""):
        super().__init__()
        self.form, self.path, self.kind = form, path, kind
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        if kind == "check":
            self.box = QCheckBox()
            self.box.toggled.connect(lambda on: self._commit(on))
        elif kind == "choice":
            self.box = SearchCombo()
            for value, label in options or []:
                self.box.addItem(label, value)
            self.box.sort_items()
            self.box.activated.connect(lambda _i: self._commit(self.box.currentData()))
        elif kind in ("lines", "block"):  # (lines: a list, one per line; block: one text, e.g. EQ file lines)
            self.box = QPlainTextEdit()
            self.box.setFixedHeight(70 if kind == "lines" else 110)
            self.box.setPlaceholderText(placeholder)
            self.box.textChanged.connect(self._typed)
        else:
            self.box = QLineEdit()
            self.box.setPlaceholderText(placeholder or (form.limits.of(path) or {}).get("empty", ""))
            self.box.textEdited.connect(self._typed)
            self.box.editingFinished.connect(self._left)
            if kind == "num":
                self.box.setMaximumWidth(110)
        # (a drop-down or a list of numbers as wide as its choices, not the card: its tag right after it, where every
        # number box's is; they zig-zagged, UI-RULES 26)
        capped = {"choice": CHOICE_MOST}.get(kind, LIST_MOST if kind not in ("check", "num", "lines", "block") else None)
        if capped:
            self.box.setMaximumWidth(capped)
        lay.addWidget(self.box, 0 if kind == "check" else 1)
        self.step = (form.steps or {}).get(path) if kind == "num" else None
        if self.step:  # (− and +, and ↑ ↓ or the wheel in the box: a step down or up, as AutoEQ Local's number boxes)
            for sign, text, tip in ((-1, "−", "Lower (or ↓ in the box)"), (1, "+", "Higher (or ↑ in the box)")):
                b = QToolButton()
                b.setText(text)
                b.setToolTip(tip)
                b.setAutoRepeat(True)
                b.setFixedWidth(30)
                b.setFocusPolicy(Qt.NoFocus)  # (Tab goes box to box; ↑ ↓ in the box do the same)
                b.clicked.connect(lambda _=False, sign=sign: self.step_by(sign))
                lay.addWidget(b)
                setattr(self, "minus" if sign < 0 else "plus", b)
            self.box.installEventFilter(self)
        self.tag = QToolButton()
        theme.mark(self.tag, tag=True)
        self.tag.clicked.connect(lambda: self.handed_back.emit(self.path))
        self.tag.hide()
        lay.addWidget(self.tag)
        if kind == "check" or capped:  # (the tag right beside its box)
            lay.addStretch(1)
        tip = help_of(path)
        allowed = form.limits.text(path)
        from ui import help_window
        self.base_tip = tip + (f"\nAllowed: {allowed}." if allowed else "") + \
            ("\nF1: more in Help." if tip and help_window.entry_for(path) else "")
        self.box.setToolTip(self.base_tip)
        self.box.setProperty("help_key", path)  # (F1 on it: its entry in Help)

    # the value as the box shows it, and back
    def show_value(self, v):
        if self.box.hasFocus() and self.kind not in ("check", "choice"):
            return
        self.box.blockSignals(True)
        if self.kind == "check":
            self.box.setChecked(bool(v))
        elif self.kind == "choice":
            i = self.box.findData(v)
            if i < 0 and v is not None:  # (a value the list doesn't have: shown as it is, not as the first)
                self.box.addItem(str(v), v)
                i = self.box.count() - 1
            self.box.setCurrentIndex(max(0, i))
        elif self.kind == "lines":
            self.box.setPlainText("\n".join(v or []))
        elif self.kind == "block":
            self.box.setPlainText(v or "")
        elif self.kind in ("intlist", "numlist"):
            self.box.setText(fmt_list(v))
        elif self.kind == "ranges":
            self.box.setText(", ".join(f"{_num(r[0])}..{_num(r[1])}" for r in v or []))
        else:
            self.box.setText("" if v is None else _num(v))
        self.box.blockSignals(False)
        self._mark(None)

    def read(self):
        """The box's value, or the reason it isn't one ("bad", message)."""
        if self.kind == "lines":
            return [s.strip() for s in self.box.toPlainText().splitlines() if s.strip()]
        if self.kind == "block":
            return self.box.toPlainText()
        t = self.box.text().strip()
        if self.kind == "intlist":
            v = parse_list(t, True)
            return v if v is not None else ("bad", "Enter numbers, e.g. 4-10 or 4, 6, 8")
        if self.kind == "numlist":
            v = parse_list(t, False)
            return v if v is not None else ("bad", "Enter numbers, e.g. 4, 6, 8")
        if self.kind == "ranges":
            v = parse_ranges(t)
            return v if v is not None else ("bad", "Write ranges as min..max, e.g. -12..6")
        if self.kind == "num":
            if t == "" and (self.form.limits.of(self.path) or {}).get("empty"):
                return None
            try:
                return _whole(float(t.replace(",", ".")))
            except ValueError:
                return ("bad", "Enter a number")
        return t

    def _mark(self, msg):
        bad = bool(msg)
        if self.box.property("bad") != (True if bad else None):
            self.box.setProperty("bad", True if bad else None)
            self.box.style().unpolish(self.box)
            self.box.style().polish(self.box)
        self.box.setToolTip(msg if bad else self.base_tip)
        if bad and self.box.hasFocus():
            self.form.say(msg)

    def _checked(self, v):
        if isinstance(v, tuple):
            return v[1], None
        problem = self.form.limits.check(self.path, v, self.form.get)
        return (problem[1] if problem else None), problem

    def _typed(self, *_):
        v = self.read()
        msg, _ = self._checked(v)
        if msg:
            self._mark(msg)
            return
        self._mark(None)
        self._commit(v)

    def _left(self):
        """Leaving the box: a value past a limit moves to the limit (said); an emptied one shows the value in use."""
        v = self.read()
        msg, problem = self._checked(v)
        if problem and problem[0] == "range":
            c = self.form.limits.clamp(self.path, v)
            if not self.form.limits.check(self.path, c, self.form.get):
                self._commit(c)
                self.show_value(c)
                self.form.say(f"Changed to {fmt_list(c) if isinstance(c, list) else _num(c)}. "
                              f"Allowed: {self.form.limits.text(self.path)}.")
                return
        if isinstance(v, tuple) and self.box.text().strip() == "":
            self.show_value(self.form.get(self.path))

    def step_by(self, n):
        """The value n steps up (or down), kept within its limits (a value that isn't a number: from the one in use)."""
        v = self.read()
        if isinstance(v, tuple) or v is None:
            v = self.form.get(self.path) or 0
        c = self.form.limits.clamp(self.path, _whole(round(v + n * self.step, 6)))
        if c == v or self.form.limits.check(self.path, c, self.form.get):
            return
        self.box.setText(_num(c))
        self._mark(None)
        self._commit(c)

    def eventFilter(self, obj, ev):
        if obj is self.box and ev.type() == QEvent.KeyPress and ev.key() in (Qt.Key_Up, Qt.Key_Down):
            self.step_by(1 if ev.key() == Qt.Key_Up else -1)
            return True
        if obj is self.box and ev.type() == QEvent.Wheel and self.box.hasFocus():  # (not while the page scrolls by)
            d = ev.angleDelta().y()
            if d:
                self.step_by(1 if d > 0 else -1)
            return True
        return False

    def _commit(self, v):
        self.committed.emit(self.path, v)

    def set_tag(self, state):
        """None (no tag), "auto" or "yours"."""
        self.tag.setVisible(bool(state))
        if state:
            self.tag.setText("yours ↺" if state == "yours" else "auto")
            self.tag.setToolTip("You set this. Click to hand it back to the automatic settings." if state == "yours"
                                else "Set by the automatic settings. Change it to use your own value.")
            self.tag.setEnabled(state == "yours")


# ---------------------------------------------------------------- a form: sections of rows
class Form(QWidget):
    """Rows of settings in sections. Each row: (label, [Field spec…], show) where a spec is (path, kind, options);
    two specs in a row are a "from … to …" pair. changed(path, value) is called with each valid value set;
    hand_back(path) for "yours ↺"; steps {path: step} gives a number box − and + (and ↑ ↓). The labels are one column
    for every section, as wide as the widest of them (_line_up): each section's boxes start at the same place (a
    column per section made them zig-zag down Advanced). add_sections(sections) adds more sections under them later,
    exactly as if they'd been in the list (Make an EQ makes Advanced in two halves, one per step of its build)."""

    def __init__(self, sections, limits, get, changed, hand_back, say, steps=None):
        super().__init__()
        self.limits, self.get, self.say, self.steps = limits, get, say, steps
        self._changed, self._hand_back = changed, hand_back
        self.fields, self.rows = {}, []
        self._labels, self._grids = [], []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        self.add_sections(sections)

    def add_sections(self, sections):
        """More sections under those there are (their rows and boxes as the form's own), the label column lined up
        again over all of them."""
        lay, changed, hand_back = self.layout(), self._changed, self._hand_back
        for title, rows in sections:
            sec = QWidget()
            sl = QVBoxLayout(sec)
            sl.setContentsMargins(0, 0, 0, 0)
            sl.setSpacing(6)
            if title:
                h = QLabel(title)
                theme.mark(h, role="section")
                sl.addWidget(h)
            grid = QGridLayout()
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(6)
            grid.setColumnStretch(1, 1)
            self._grids.append(grid)
            for i, row in enumerate(rows):
                label, specs = row[0], row[1]
                show = row[2] if len(row) > 2 else None
                if isinstance(label, QWidget):  # (a note or a widget of its own, across the row)
                    grid.addWidget(label, i, 0, 1, 2)
                    self.rows.append(([label], show))
                    continue
                if label is None and isinstance(specs, QWidget):  # (a widget in the boxes' column: a button that fills
                    grid.addWidget(specs, i, 1)  # the box above it, under it: .claude/notes/UI-RULES.md 27)
                    self.rows.append(([specs], show))
                    continue
                lab = QLabel(label)
                self._labels.append(lab)
                lab.setToolTip(help_of(specs[0][0]) if specs else "")
                box = QWidget()
                bl = QHBoxLayout(box)
                bl.setContentsMargins(0, 0, 0, 0)
                bl.setSpacing(8)
                for j, spec in enumerate(specs):
                    if j:
                        bl.addWidget(QLabel("to"))
                    f = Field(self, spec[0], spec[1], spec[2] if len(spec) > 2 else None,
                              spec[3] if len(spec) > 3 else "")
                    f.committed.connect(changed)
                    f.handed_back.connect(hand_back)
                    f.box.setAccessibleName(label.strip() + (" (to)" if j else ""))  # (what a screen reader says)
                    if f.step:
                        f.minus.setAccessibleName(label.strip() + " lower")
                        f.plus.setAccessibleName(label.strip() + " higher")
                    self.fields[spec[0]] = f
                    bl.addWidget(f, 1 if spec[1] not in ("num",) else 0)
                bl.addStretch(1) if all(s[1] in ("num", "check") for s in specs) else None
                grid.addWidget(lab, i, 0, Qt.AlignTop if specs and specs[0][1] in ("lines", "block") else Qt.AlignVCenter)
                grid.addWidget(box, i, 1)
                self.rows.append(([lab, box], show))
            sl.addLayout(grid)
            lay.addWidget(sec)
            shows = [r[2] if len(r) > 2 else None for r in rows]
            if shows and all(shows):  # (a section whose rows all may hide: hidden with them, its heading too)
                self.rows.append(([sec], lambda shows=shows: any(s() for s in shows)))
        self._line_up()

    def _line_up(self):
        """The label column as wide as the form's widest label, in every section (hidden rows' labels too, so nothing
        moves when a row shows or hides)."""
        for lab in self._labels:
            lab.ensurePolished()  # (in the theme's text size)
        width = max((lab.sizeHint().width() for lab in self._labels), default=0)
        for grid in self._grids:
            grid.setColumnMinimumWidth(0, width)

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() in (QEvent.StyleChange, QEvent.FontChange):  # (the theme's text size may have come since)
            self._line_up()

    def refresh(self, tags=None):
        """Show the settings' values; hide what doesn't apply; the automatic settings' tags ({path: state})."""
        for path, f in self.fields.items():
            f.show_value(self.get(path))
            f.set_tag((tags or {}).get(path))
        for widgets, show in self.rows:
            if show is not None:
                on = bool(show())
                for w in widgets:
                    w.setVisible(on)


class Fold(QFrame):
    """A card that opens and closes: its title (and a short summary beside it) is the button, Windows 11's chevron
    before it (the theme's settings_boxes part: right when closed, down when open; filled when pointed at). Its
    chevron and its content start at a card's inset, as a card's title and content do (theme_sheet's CARD: the card's
    padding and these margins; the chevron's place starts where the button does)."""
    toggled = Signal(bool)

    def __init__(self, title, open_=False):
        super().__init__()
        theme.mark(self, card=True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 4)
        head = QHBoxLayout()
        self.btn = QToolButton()
        self.btn.setText(title)
        self.btn.setCheckable(True)
        self.btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        theme.mark(self.btn, fold=True)
        self.btn.toggled.connect(self._set)
        head.addWidget(self.btn)
        self.summary = QLabel("")
        theme.mark(self.summary, role="muted")
        head.addWidget(self.summary, 1)
        lay.addLayout(head)
        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 4, 0, 8)
        lay.addWidget(self.body)
        self.btn.setChecked(open_)
        self._set(open_)

    def _set(self, on):
        self.btn.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.body.setVisible(on)
        self.toggled.emit(on)

    def add(self, w):
        self.body_lay.addWidget(w)
        return w
