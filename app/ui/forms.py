"""Settings boxes, built from a list (AutoEQ Local's [data-path] boxes and limits.js, natively).

A Field shows and edits one setting (a dotted path in the EQ part's settings: "best_fit.filter_counts",
"scoring.band_hz.1"). Kinds: num, intlist ("4-10" or "4, 6, 8"), numlist, ranges (RangeRows: a row of two boxes for
each range), lines (one per line), block (one text of many lines), check, choice ([(value, label)]), text. A value is
checked as it's typed against the EQ part's own limits (eq.settings LIMITS and LIMIT_PAIRS: a "from" below its "to"):
a wrong one turns the box red with the reason (and isn't used); leaving a box with a value past a limit moves it to
the limit and says so. A box's tooltip is its Help line and its limits (help_texts.HELP; a "to" box shares its "from"
box's). The rows of ranges take only valid values instead: no red box and no message (the owner, 2026-11-25).

The automatic settings: a box they fill in has a tag beside it, "automatic", or "custom ↺" once you've changed it
(the tag hands it back). A Form is a list of rows in sections; show(predicate) hides a row when it doesn't apply.

The layout (the UI audit, 2026-11-08, the user's selections): each setting is a cell with its label above its box
(+ its tag), and the cells go side by side in columns of one width (CELL), as many as the width holds (FlowLayout):
the label is directly above its box, and on a wide window the settings use less height. Two widths of box: a number
SHORT (110 px), every other box, list and "from … to" pair LONG (360 px; a "from" number and its list of "to" values
too: the number SHORT, the list the rest), so their tags are in one column (a list of
ranges: each row LONG wide with its ✕ in it, Add a range under the rows, the tag at the first row). A form
with tabs=True shows each section as a tab (More settings: less height; a section whose rows all hide has no tab).
A Fold is a part that opens and closes: a card (the tracer's About these settings), or a row in a card (sub=True:
Settings and More settings in Make the EQ, About these settings in Settings).
"""
import math
import re
import types

from PySide6.QtCore import QEvent, QRect, QSize, Qt, Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QLayout, QLineEdit,
                               QPlainTextEdit, QPushButton, QToolButton, QVBoxLayout, QWidget)

from ui import own_items, placed, theme
from ui.help_texts import HELP
from ui.search_combo import SearchCombo


# ---------------------------------------------------------------- values as text, and back (settings.js)
def fmt_list(a, dash="-"):
    if not isinstance(a, list) or not a:
        return ""
    if all(isinstance(v, int) and not isinstance(v, bool) for v in a) and len(a) > 2 \
            and all(a[i] == a[i - 1] + 1 for i in range(1, len(a))):
        return f"{a[0]}{dash}{a[-1]}"
    return ", ".join(number_text(v) for v in a)


def number_text(v):
    """A number as a box shows it: 0.5, 16000, 0.00005 (never 5e-05). Public: the filter table shows its numbers
    the same way."""
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
        s = f"{number_text(lim['min'])} to {number_text(lim['max'])}{(' ' + lim['unit']) if lim.get('unit') else ''}"
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
            return "range", "Integers only: " + self.text(key)
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
            return "pair", (f"Must be {'less than' if strict else 'at most'} {number_text(b)}{unit}" if key == lo
                            else f"Must be {'more than' if strict else 'at least'} {number_text(a)}{unit}")
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


SHORT, LONG = 110, 360  # (px: a number box; every other box, a drop-down, a list, a "from … to" pair: UI-RULES 26)
CHOICE_MOST = LONG       # (a drop-down's width outside a form: Your EQ app, Start from)
CELL = 470               # (px: a setting's cell, its box and its tag: the columns of a form)
PAIR_GAP, PAIR_TO = 8, 24  # (px: a "from … to" pair's gaps, and its "to")
PAIR_BOX = (LONG - PAIR_TO - 2 * PAIR_GAP) // 2  # (px: a pair's first box; the second has the rest of LONG)
LISTS = ("intlist", "numlist")  # (the kinds of a box of several values: a pair's "to" list)


RANGE_X = 30  # (px: a range row's ✕, as wide as a number box's − and +)
RANGE_BOX = (LONG - PAIR_TO - RANGE_X - 3 * PAIR_GAP) // 2  # (px: a range row's first box; the second has the rest)
# (what Add a range puts in its new row: the first of these that the list doesn't have, else a copy of the last row.
# The defaults of eq.settings, then the two widest usual ranges)
RANGE_STARTS = ([-12, 6], [-12, 9], [-12, 12], [-16, 16], [-20, 20])
_WHOLE = re.compile(r"-?\d+")


def help_of(path):
    """A setting's tooltip line (a "to" box shares its "from" box's; a list's item, its list's: help_window.help_key)."""
    from ui.help_window import help_key
    h = HELP.get(help_key(path) or "")
    return (h[0] if isinstance(h, list) else h) if h else ""


class _WholeNumber(QValidator):
    """A whole number from lo to hi, or, while it's typed, an empty box or a lone "-". Qt refuses a key that would make
    anything else: the text stays as it was."""

    def __init__(self, lo, hi, parent):
        super().__init__(parent)
        self.lo, self.hi = lo, hi

    def validate(self, text, _pos):
        if text == "" or (text == "-" and self.lo < 0):
            return QValidator.Intermediate
        if not _WHOLE.fullmatch(text):
            return QValidator.Invalid
        return QValidator.Acceptable if self.lo <= int(text) <= self.hi else QValidator.Invalid


class _AtFirstRow(QWidget):
    """Room for a list's tag beside the list's first row (the list is taller than one row): as high as that row, the
    tag in its middle, as a one-box setting's tag is beside its box."""

    def __init__(self, tag, rows, parent):
        super().__init__(parent)
        self.rows = rows
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(tag)

    def sizeHint(self):
        s = self.layout().sizeHint()
        return QSize(s.width(), max(s.height(), self.rows.rows[0].widget.sizeHint().height()))

    def minimumSizeHint(self):
        return self.sizeHint()


class RangeRows(QWidget):
    """A list of ranges ([[from, to], …], e.g. Gain ranges) as rows: two boxes, "from" and "to", and a ✕ that removes
    the row (hidden with one row left, its room kept: UI-RULES 18); Add a range under the rows (UI-RULES 19). Each row
    is as wide as one LONG box.
    Only valid values go in, with no message (the owner, 2026-11-25): each box takes a whole number within the
    setting's limits (a key that would make anything else is refused). While you type, a row with an empty box, a
    lone "-", or its "from" above its "to" is not used: ranges() is None until every row is good, and the list in use
    stays. Leaving a box puts its row right: an empty box gets back the number the row had, and the box you left takes
    the other box's value when their order is wrong. Add a range and ✕ first put every row right, so the list after
    them is always good. changed is emitted after each of these. Rows no longer needed are hidden, not deleted, and
    shown again by a later Add a range: a row keeps its place in the Tab sequence."""
    changed = Signal()

    def __init__(self, form, path, parent=None):
        super().__init__(parent)
        self.form, self.path, self.name = form, path, path
        lim = form.limits.of(path) or {}
        self._limits = (math.ceil(lim.get("min", -999)), math.floor(lim.get("max", 999)))
        self._unit = lim.get("unit", "")
        self.rows, self._had, self._edited, self._n, self._tip = [], [], {}, 0, ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.rows_box = QWidget(self)
        self.rows_lay = QVBoxLayout(self.rows_box)
        self.rows_lay.setContentsMargins(0, 0, 0, 0)
        self.rows_lay.setSpacing(4)
        lay.addWidget(self.rows_box)
        # (the rows of the value in use made now, before Add a range: in the Tab sequence, in the build step that
        # makes the page's Tab sequence; a row made later is put into its place)
        for _ in range(max(1, len(form.get(path) or []))):
            self._make_row()
        self.add_btn = QPushButton("Add a range", self)
        from ui import icons
        icons.put(self.add_btn, "add")
        self.add_btn.setToolTip("Add another gain range to try")
        self.add_btn.setProperty("help_key", path)
        self.add_btn.clicked.connect(self.add)
        lay.addWidget(self.add_btn, 0, Qt.AlignLeft)
        self.setFixedWidth(LONG)
        self.setFocusProxy(self.rows[0].lo)
        self.set_ranges(form.get(path))

    # the rows
    def _make_row(self):
        r = types.SimpleNamespace(widget=QWidget(self.rows_box))
        rl = QHBoxLayout(r.widget)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(PAIR_GAP)
        r.lo, r.hi = QLineEdit(r.widget), QLineEdit(r.widget)
        to = QLabel("to", r.widget)
        to.setFixedWidth(PAIR_TO)
        to.setAlignment(Qt.AlignCenter)
        r.x = QToolButton(r.widget)
        theme.mark(r.x, quiet=True)  # (a row's ✕: every list's one look, UI-RULES 18)
        r.x.setText("✕")
        r.x.setToolTip("Remove this range")
        r.x.setFixedWidth(RANGE_X)
        sp = r.x.sizePolicy()
        sp.setRetainSizeWhenHidden(True)  # (one row left: its ✕ hidden, its room kept)
        r.x.setSizePolicy(sp)
        r.x.setProperty("help_key", self.path)
        r.x.clicked.connect(lambda _=False, x=r.x: self.remove(self._find(x)[0]))
        r.lo.setFixedWidth(RANGE_BOX)
        r.hi.setFixedWidth(LONG - RANGE_BOX - PAIR_TO - RANGE_X - 3 * PAIR_GAP)
        for box in (r.lo, r.hi):
            box.setValidator(_WholeNumber(*self._limits, box))
            box.setToolTip(self._tip)
            box.setProperty("help_key", self.path)  # (F1 on it: its entry in Help)
            box.textEdited.connect(lambda _t, box=box: self._typed(box))
            box.editingFinished.connect(lambda box=box: self._left(box))
            box.installEventFilter(self)
        for w in (r.lo, to, r.hi, r.x):
            rl.addWidget(w)
        self.rows_lay.addWidget(r.widget)
        if self.rows:  # (after the row above in the Tab sequence: Qt puts a new control at the end of its window's)
            for a, b in ((self.rows[-1].x, r.lo), (r.lo, r.hi), (r.hi, r.x)):
                QWidget.setTabOrder(a, b)
        self.rows.append(r)
        self._name(len(self.rows) - 1)
        return r

    def _name(self, i):
        r, unit = self.rows[i], f" ({self._unit})" if self._unit else ""
        r.lo.setAccessibleName(f"{self.name}, range {i + 1}, from{unit}")
        r.hi.setAccessibleName(f"{self.name}, range {i + 1}, to{unit}")
        one = self.name[:1].lower() + self.name[1:]  # ("Gain ranges": "Remove gain range 2")
        r.x.setAccessibleName(f"Remove {one[:-1] if one.endswith('s') else one} {i + 1}")

    def set_name(self, name):
        """The setting's name (its label), in the names a screen reader says: "Gain ranges, range 2, from (dB)"."""
        self.name = name
        for i in range(len(self.rows)):
            self._name(i)

    def set_tip(self, tip):
        self._tip = tip
        for r in self.rows:
            r.lo.setToolTip(tip)
            r.hi.setToolTip(tip)

    def _find(self, w):
        """(row, 0 for its "from" box, 1 for its "to" box, 2 for its ✕), or None."""
        for i, r in enumerate(self.rows):
            for k, c in enumerate((r.lo, r.hi, r.x)):
                if c is w:
                    return i, k
        return None

    def editing(self):
        """A box of a shown row has the focus."""
        hit = self._find(QApplication.focusWidget())
        return hit is not None and hit[0] < self._n and hit[1] < 2

    # values
    def set_ranges(self, v):
        """Shows the ranges v, a row each (the other rows hidden)."""
        v = [list(r) for r in v or []] or [[None, None]]
        while len(self.rows) < len(v):
            self._make_row()
        for r, (a, b) in zip(self.rows, v):
            self._put(r.lo, a)
            self._put(r.hi, b)
        self._had = [[0 if x is None else int(x) for x in r] for r in v]
        self._edited = {}
        self._show_rows(len(v))

    def ranges(self):
        """The list the rows show, or None while a row is not good (an empty box, a lone "-", from above to)."""
        out = []
        for r in self.rows[:self._n]:
            a, b = r.lo.text(), r.hi.text()
            if not (_WHOLE.fullmatch(a) and _WHOLE.fullmatch(b)) or int(a) > int(b):
                return None
            out.append([int(a), int(b)])
        return out

    def text(self):
        """The ranges as words: "-12 to 6, -12 to 9"."""
        return ", ".join(f"{r.lo.text()} to {r.hi.text()}" for r in self.rows[:self._n])

    @staticmethod
    def _put(box, v):
        t = "" if v is None else number_text(v)
        if box.text() != t:
            box.setText(t)

    def _show_rows(self, n):
        """Rows 1 to n shown, the others hidden; ✕ only with more than one row. A control with the focus that goes is
        first replaced by the one beside it (UI-RULES 30): hidden first, Qt gave the focus to the next control in the
        page's sequence and the page could scroll to it."""
        hit = self._find(QApplication.focusWidget())
        self._n = n  # (first: the box that the focus leaves now is in a hidden row, so _left leaves it alone)
        if hit is not None and (hit[0] >= n or (n == 1 and hit[1] == 2)):
            last = self.rows[n - 1]
            (last.x if hit[1] == 2 and n > 1 else last.hi if hit[1] == 2 else (last.lo, last.hi)[hit[1]]).setFocus(
                Qt.OtherFocusReason)
        for i, r in enumerate(self.rows):
            r.widget.setVisible(i < n)
            r.x.setVisible(n > 1)

    def _fix(self, i, box=None):
        """Row i put right: an empty box (or a lone "-") gets back its number, and when the order is wrong, the box
        just edited takes the other box's value."""
        r = self.rows[i]
        for k, b in enumerate((r.lo, r.hi)):
            self._put(b, int(b.text()) if _WHOLE.fullmatch(b.text()) else self._had[i][k])
        a, b = int(r.lo.text()), int(r.hi.text())
        if a > b:
            if (box or self._edited.get(i, r.hi)) is r.lo:
                self._put(r.lo, b)
            else:
                self._put(r.hi, a)
        self._had[i] = [int(r.lo.text()), int(r.hi.text())]

    def fix_all(self):
        for i in range(self._n):
            self._fix(i)

    def _typed(self, box):
        i = self._find(box)[0]
        self._edited[i] = box
        r = self.rows[i]
        a, b = r.lo.text(), r.hi.text()
        if _WHOLE.fullmatch(a) and _WHOLE.fullmatch(b) and int(a) <= int(b):  # (a good row: what an emptied box gets)
            self._had[i] = [int(a), int(b)]
        self.changed.emit()

    def _left(self, box):
        hit = self._find(box)
        if hit is None or hit[0] >= self._n:
            return
        self._fix(hit[0], box)
        self.changed.emit()

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.FocusOut and ev.reason() != Qt.PopupFocusReason:
            self._left(obj)  # (an empty box or a lone "-" is no number, so Qt's editingFinished doesn't come)
        return False

    def add(self):
        """A row more, with the first usual range that the list doesn't have; the caret in its first box, its text
        selected, so that what you type replaces it."""
        self.fix_all()
        have = self._had[:self._n]
        start = next((list(s) for s in RANGE_STARTS if list(s) not in have), list(have[-1]))
        if self._n == len(self.rows):
            self._make_row()
        r = self.rows[self._n]
        self._put(r.lo, start[0])
        self._put(r.hi, start[1])
        self._had = have + [start]
        self._show_rows(self._n + 1)
        self.changed.emit()
        r.lo.setFocus(Qt.OtherFocusReason)
        r.lo.selectAll()

    def remove(self, i):
        """Row i taken out; the rows under it move up. The focus moves only if its control goes (UI-RULES 30): a ✕
        clicked with the mouse takes no focus, and the caret stays where it is."""
        if self._n <= 1 or i >= self._n:
            return
        self.fix_all()
        values = self._had[:self._n]
        del values[i]
        for r, (a, b) in zip(self.rows, values):
            self._put(r.lo, a)
            self._put(r.hi, b)
        self._had, self._edited = values, {}
        self._show_rows(self._n - 1)
        self.changed.emit()


# ---------------------------------------------------------------- one box
class Field(QWidget):
    """One setting's box (and, when the automatic settings fill it, its tag)."""
    committed = Signal(str, object)   # (path, value): a valid value the user set
    make_auto_clicked = Signal(str)         # (path): "custom ↺" clicked

    def __init__(self, form, path, kind, options=None, placeholder="", pair=False, pinned=0):
        super().__init__()
        self.form, self.path, self.kind = form, path, kind
        self._focus_from_tag = False  # (the box got the focus of its tag, not typed in since: it shows each new value)
        self._state = None  # (the tag's: None, "auto" or "yours")
        self._lock = None  # (set_lock's: None, or (value, reason))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        if kind == "ranges":
            self.box = RangeRows(form, path, self)
            self.box.changed.connect(self._ranges_typed)
        elif kind == "check":
            self.box = QCheckBox()
            self.box.toggled.connect(lambda on: self._commit(on))
        elif kind == "choice":
            self.box = SearchCombo()
            for value, label in options or []:
                self.box.addItem(label, value)
            self.box.sort_items(pinned)  # (the first `pinned` choices stay on top: UI-RULES 22)
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
            self.box.editingFinished.connect(self._edit_finished)
        # (two widths: a number SHORT, every other box LONG, so the tags are in one column, UI-RULES 26; a pair's
        # boxes share LONG: the form sets them)
        if kind == "num":
            self.box.setFixedWidth(SHORT)
        elif kind != "check":
            self.box.setFixedWidth(LONG)
        lay.addWidget(self.box, 0)
        self.step = (form.steps or {}).get(path) if kind == "num" else None
        if self.step:  # (− and +, and ↑ ↓ or the wheel in the box: a step down or up, as AutoEQ Local's number boxes)
            for sign, text, tip in ((-1, "−", "Decrease (or press ↓)"), (1, "+", "Increase (or press ↑)")):
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
        self.tag.clicked.connect(lambda: self.make_auto_clicked.emit(self.path))
        self.tag.hide()
        if kind == "ranges":  # (the tag beside the first row, in the tags' column)
            lay.addWidget(_AtFirstRow(self.tag, self.box, self), 0, Qt.AlignTop)
            lay.addStretch(1)
        elif not pair:  # (the tag right beside its box; a pair's tags: after its second box, put there by the form)
            lay.addWidget(self.tag)
            lay.addStretch(1)
        tip = help_of(path)
        allowed = form.limits.text(path)
        # (the line of Help, then the limits. An empty line in HELP, help_texts.py, means the survey removed the
        # words: the tooltip is then only the limits, with no empty first line; with no limits either, no tooltip)
        self.base_tip = "\n".join(t for t in (tip, f"Allowed: {allowed}" if allowed else "") if t)
        if kind == "ranges":
            self.box.set_tip(self.base_tip)
        else:
            self.box.setToolTip(self.base_tip)
        # (no description for a screen reader is set: Qt gives the tooltip, with the limits and any message of a bad
        # value, the owner's rule of 2026-11-24, as help_window.tag)
        if kind != "ranges":  # (a list of ranges: each of its boxes and buttons has it)
            self.box.setProperty("help_key", path)  # (F1 on it: its entry in Help)

    # the value as the box shows it, and back
    def editing(self):
        """The caret is in the box (a list of ranges: in one of its boxes)."""
        return self.box.editing() if self.kind == "ranges" else self.box.hasFocus()

    def show_value(self, v, force=False):
        """v in the box; not while you type in it (force: all the same)."""
        if not self.editing():
            self._focus_from_tag = False
        elif self.kind not in ("check", "choice") and not self._focus_from_tag and not force:  # (not over what you type)
            return
        if self.kind == "ranges":
            self.box.set_ranges(v)
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
        else:
            self.box.setText("" if v is None else number_text(v))
        self.box.blockSignals(False)
        self._mark(None)

    def read(self):
        """The box's value, or the reason it isn't one ("bad", message)."""
        if self.kind == "lines":
            return [s.strip() for s in self.box.toPlainText().splitlines() if s.strip()]
        if self.kind == "block":
            return self.box.toPlainText()
        if self.kind == "ranges":  # (no message: its boxes take only valid values, and a row is put right on leaving)
            v = self.box.ranges()
            return v if v is not None else ("bad", "")
        t = self.box.text().strip()
        if self.kind == "intlist":
            v = parse_list(t, True)
            return v if v is not None else ("bad", "Enter integers, e.g. 4-10 or 4, 6, 8")
        if self.kind == "numlist":
            v = parse_list(t, False)
            return v if v is not None else ("bad", "Enter numbers, e.g. 4, 6, 8")
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
        self._focus_from_tag = False
        v = self.read()
        msg, _ = self._checked(v)
        if msg:
            self._mark(msg)
            return
        self._mark(None)
        self._commit(v)

    def _edit_finished(self):
        """Leaving the box: a value past a limit moves to the limit (said); an emptied one shows the value in use."""
        v = self.read()
        msg, problem = self._checked(v)
        if problem and problem[0] == "range":
            c = self.form.limits.clamp(self.path, v)
            if not self.form.limits.check(self.path, c, self.form.get):
                self._commit(c)
                self.show_value(c)
                self.form.say(f"Adjusted to {fmt_list(c) if isinstance(c, list) else number_text(c)} "
                              f"(allowed: {self.form.limits.text(self.path)})")
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
        self.box.setText(number_text(c))
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

    def _ranges_typed(self):
        """A list of ranges changed: used at once when every row is good (else the list in use stays)."""
        self._focus_from_tag = False
        v = self.box.ranges()
        if v is not None:
            self._commit(v)

    def _commit(self, v):
        self.committed.emit(self.path, v)

    def set_lock(self, lock):
        """None: the box as usual. (value, reason): a value that can't be changed here (a website's fixed gain or Q,
        eq.site_values): the box shows it and is off (gray, as Windows 11's), its tooltip the reason (a screen reader
        reads it too); the setting's own value stays in the settings. Form.refresh moves the focus off it first."""
        if lock is None and self._lock is None:
            return
        self._lock = lock
        if self.box.isEnabled() != (lock is None):
            self.box.setEnabled(lock is None)
        if lock is not None:
            self.show_value(lock[0], force=True)
        tip = lock[1] if lock is not None else self.base_tip
        if self.kind == "ranges":
            self.box.set_tip(tip)
        else:
            self.box.setToolTip(tip)

    def set_tag(self, state):
        """None (no tag), "auto" or "yours"."""
        was, self._state = self._state, state
        # (your value made automatic: the box shows the value in use, also with the caret in it. A click on the tag
        # with the mouse leaves the focus in the box (a tag takes none on a click), so the box kept your value under
        # "automatic", and your next key made the whole of it yours again: the critique of feature 4, 2026-11-24)
        if was == "yours" and state != "yours":
            if self.editing():
                self._focus_from_tag = True  # (it shows the automatic value that comes later too)
            self.show_value(self.form.get(self.path), force=True)
        # (the tag with the focus (Tab, then Space on "custom ↺") goes off or hides: the box beside it gets the
        # focus first. Qt gave it to the next setting in the page's order, and the page scrolled to it: 670 px to 791
        # px, 2026-11-15. The box still shows each new value until you type in it: the automatic value comes later)
        if state != "yours" and self.tag.window().focusWidget() is self.tag and self.box.isEnabled() \
                and self.box.isVisibleTo(self.tag.window()):
            self._focus_from_tag = True
            self.box.setFocus(Qt.OtherFocusReason)
        self.tag.setVisible(bool(state))
        if state:
            self.tag.setText("custom ↺" if state == "yours" else "automatic")
            self.tag.setToolTip("Custom value. Click to reset to automatic." if state == "yours"
                                else "Set automatically. Edit to override.")
            self.tag.setEnabled(state == "yours")


class FlowLayout(QLayout):
    """Cells side by side, as many as the width holds, then the next row (Qt's flow layout): each cell CELL px wide,
    so they make columns; a widget with the property full_row takes a row of its own. Hidden cells take no room."""

    def __init__(self, parent=None, cell=CELL, hspace=16, vspace=12):
        super().__init__(parent)
        self._items, self.cell, self.hspace, self.vspace = own_items(self), cell, hspace, vspace
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._place(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._place(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        w = h = 0
        for it in self._items:
            if not it.isEmpty():
                m = it.minimumSize()
                w, h = max(w, min(self.cell, m.width()) if not _full(it) else m.width()), max(h, m.height())
        return QSize(w, h)

    def _place(self, rect, test):
        x, y, line, first = rect.x(), rect.y(), 0, True
        for it in self._items:
            if it.isEmpty():
                continue
            full = _full(it)
            # (a cell that needs more than CELL, as long words or two tags, gets it: else they were cut or went on a box)
            w = rect.width() if full else min(max(self.cell, it.minimumSize().width()), rect.width())
            h = it.heightForWidth(w) if it.hasHeightForWidth() else it.sizeHint().height()
            if not first and (full or x + w > rect.right() + 1):
                x, y, line = rect.x(), y + line + self.vspace, 0
            if not test:
                it.setGeometry(QRect(x, y, w, h))
            x += w + self.hspace
            line = max(line, h)
            first = False
            if full:  # (the next cell starts a new row)
                x = rect.right() + 2
        return y + line - rect.y()


def _full(item):
    w = item.widget()
    return w is not None and bool(w.property("full_row"))


class TabPages(QWidget):
    """A form's tab pages, one shown at a time, as high as the page shown. Qt's QStackedWidget is as high as its
    highest page: its layout asks every page for its height at a width, whatever their size policy, so More settings'
    short tabs (History, This PC) had up to 330 px of empty room under them (the review, 2026-11-10). Here the pages
    are in a column and only the page shown is not hidden: a layout leaves out hidden widgets, so the column is as
    high as that page. The names are QStackedWidget's (addWidget, count, widget, currentIndex, setCurrentIndex,
    currentWidget, currentChanged)."""
    currentChanged = Signal(int)

    def __init__(self):
        super().__init__()
        self._pages, self._current = [], -1
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

    def addWidget(self, page):
        if self._pages:  # (hidden before it goes in: never shown, so never styled, until its tab is clicked)
            page.hide()
        self._pages.append(page)
        self.layout().addWidget(page)
        if self._current < 0:
            self._current = 0
            self.currentChanged.emit(0)
        return len(self._pages) - 1

    def count(self):
        return len(self._pages)

    def widget(self, i):
        return self._pages[i] if 0 <= i < len(self._pages) else None

    def currentIndex(self):
        return self._current

    def currentWidget(self):
        return self.widget(self._current)

    def setCurrentIndex(self, i):
        if not 0 <= i < len(self._pages) or i == self._current:
            return
        old, self._current = self.currentWidget(), i
        self._pages[i].show()
        if old is not None:
            old.hide()
        self.currentChanged.emit(i)


# ---------------------------------------------------------------- a form: sections of rows
class Form(QWidget):
    """Rows of settings in sections. Each row: (label, [Field spec…], show) where a spec is (path, kind, options);
    two specs in a row are a "from … to …" pair. changed(path, value) is called with each valid value set;
    make_auto(path) for "custom ↺"; steps {path: step} gives a number box − and + (and ↑ ↓). Each row is a cell,
    its label above its box, the cells in columns (FlowLayout); a widget as the label is a note across the form; a
    (None, widget) row goes under the box above it (a button that fills it: UI-RULES 27). tabs: a tab for each
    section (More settings), else a title above each section. add_sections(sections) adds more sections under them
    later, exactly as if they'd been in the list (Make an EQ makes More settings in two halves, one per step of its
    build)."""

    def __init__(self, sections, limits, get, changed, make_auto, say, steps=None, tabs=False):
        super().__init__()
        self.limits, self.get, self.say, self.steps = limits, get, say, steps
        self._changed, self._make_auto = changed, make_auto
        self.fields, self.rows, self._show_of = {}, [], {}
        self.tabs, self.tab_btns, self._sections = tabs, {}, []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        if tabs:  # (the tabs in the app's look: Table / Sliders, Find…'s sources; the page as high as its own cells)
            self.tab_row = placed(lay, QHBoxLayout())
            self.tab_row.setSpacing(20)
            self.tab_row.addStretch(1)
            self.pages = TabPages()
            lay.addWidget(self.pages)
        self.add_sections(sections)

    def add_sections(self, sections):
        """More sections under those there are (their rows and boxes as the form's own)."""
        lay, changed, make_auto = self.layout(), self._changed, self._make_auto
        for title, rows in sections:
            sec = QWidget()
            sl = QVBoxLayout(sec)
            sl.setContentsMargins(0, 0, 0, 0)
            sl.setSpacing(6)
            if title and not self.tabs:
                h = QLabel(title)
                theme.mark(h, role="section")
                sl.addWidget(h)
            flow = placed(sl, FlowLayout())
            last = None
            for row in rows:
                label, specs = row[0], row[1]
                show = row[2] if len(row) > 2 else None
                if isinstance(label, QWidget):  # (a note or a widget of its own, across the form)
                    label.setProperty("full_row", True)
                    flow.addWidget(label)
                    self.rows.append(([label], show))
                    continue
                if label is None and isinstance(specs, QWidget):  # (under the box above it, in its cell)
                    if last is not None:
                        last.layout().addWidget(specs)
                    else:
                        flow.addWidget(specs)
                    self.rows.append(([specs], show))
                    continue
                cell = QWidget()
                cl = QVBoxLayout(cell)
                cl.setContentsMargins(0, 0, 0, 0)
                cl.setSpacing(4)
                checks = all(sp[1] == "check" for sp in specs)
                if not checks or label:  # (a tick box's words are beside it: no label above it, unless given one)
                    lab = QLabel(label)
                    lab.setToolTip(help_of(specs[0][0]) if specs else "")
                    cl.addWidget(lab)
                pair = len(specs) == 2
                kinds = [sp[1] for sp in specs]
                box = QWidget()  # (the boxes' row: a pair's boxes and "to", then their tags)
                bl = QHBoxLayout(box)
                bl.setContentsMargins(0, 0, 0, 0)
                bl.setSpacing(PAIR_GAP)
                for j, spec in enumerate(specs):
                    if j:
                        to = QLabel("to")
                        to.setFixedWidth(PAIR_TO)
                        to.setAlignment(Qt.AlignCenter)
                        bl.addWidget(to)
                    f = Field(self, spec[0], spec[1], spec[2] if len(spec) > 2 else None,
                              spec[3] if len(spec) > 3 else "", pair=pair, pinned=spec[4] if len(spec) > 4 else 0)
                    f.committed.connect(changed)
                    f.make_auto_clicked.connect(make_auto)
                    name = (label or "").strip() or spec[0]
                    if spec[1] != "check":  # (what a screen reader says; a tick box: its own words, Qt's default)
                        f.box.setAccessibleName(name + (" (to)" if j else ""))
                    if spec[1] == "ranges":  # (its boxes and ✕ by the label: "Gain ranges, range 1, from (dB)")
                        f.box.set_name(name)
                    if f.step:
                        f.minus.setAccessibleName(name + " lower")
                        f.plus.setAccessibleName(name + " higher")
                    self.fields[spec[0]] = f
                    self._show_of[spec[0]] = show
                    # (its two boxes and "to" exactly as wide as one LONG box: UI-RULES 26. A "from" number and a list
                    # of "to" values: the number SHORT, the list the rest)
                    if pair and spec[1] == "num" and kinds[1] == "num":
                        f.box.setFixedWidth(PAIR_BOX if not j else LONG - PAIR_BOX - PAIR_TO - 2 * PAIR_GAP)
                    elif pair and kinds[1] in LISTS:
                        f.box.setFixedWidth(SHORT if not j else LONG - SHORT - PAIR_TO - 2 * PAIR_GAP)
                    bl.addWidget(f)
                if pair:  # (both tags after the second box, so they are in the tags' column and never on a box)
                    first, second = (self.fields[sp[0]] for sp in specs)
                    second.layout().addWidget(first.tag)
                    second.layout().addWidget(second.tag)
                    second.layout().addStretch(1)
                bl.addStretch(1)
                cl.addWidget(box)
                flow.addWidget(cell)
                last = cell
                self.rows.append(([cell], show))
            shows = [r[2] if len(r) > 2 else None for r in rows]
            whole = (lambda shows=shows: any(s() for s in shows)) if shows and all(shows) else None
            if self.tabs:
                self._add_tab(title, sec, whole)
            else:
                lay.addWidget(sec)
                if whole is not None:  # (a section whose rows all may hide: hidden with them, its heading too)
                    self.rows.append(([sec], whole))

    def applies(self, path):
        """The form has a box for this setting, and its row shows now (its show predicate)."""
        show = self._show_of.get(path)
        return path in self.fields and (show is None or bool(show()))

    def _focus_off_locked(self, locks):
        """A box with the focus that becomes fixed now (locks) first gives the focus to the nearest setting that stays
        on, the one before it, else the one after it (UI-RULES 30, as RangeRows.remove does): disabled with the focus,
        Qt gave the focus to the next control in the page's order, and the page could scroll to it (the review of
        feature 5)."""
        w = QApplication.focusWidget()
        if w is None:
            return
        order = list(self.fields.items())
        at = next((i for i, (path, f) in enumerate(order) if path in locks and f.box.isEnabled()
                   and (w is f.box or f.box.isAncestorOf(w))), None)
        if at is None:
            return
        near = [order[i] for i in range(at - 1, -1, -1)] + order[at + 1:]
        for path, f in near:
            if path not in locks and f.box.isEnabled() and f.isVisible() and f.box.focusPolicy() != Qt.NoFocus:
                f.box.setFocus(Qt.OtherFocusReason)
                return

    def _add_tab(self, title, page, show):
        b = QPushButton(title)
        b.setCheckable(True)
        theme.mark(b, nav=True, flush=True)
        i = self.pages.addWidget(page)
        b.clicked.connect(lambda _=False, i=i: self.show_tab(i))
        self.tab_row.insertWidget(self.tab_row.count() - 1, b)
        self.tab_btns[i] = b
        self._sections.append((i, show))
        b.setChecked(i == self.pages.currentIndex())

    def show_tab(self, i):
        self.pages.setCurrentIndex(i)
        for k, b in self.tab_btns.items():
            b.setChecked(k == i)

    def refresh(self, tags=None, locks=None, shown=None):
        """Show the settings' values (shown: {path: value} shown in place of the setting's own, which stays as it is);
        hide what doesn't apply; the automatic settings' tags ({path: state}); the boxes whose values can't be changed
        now ({path: (value, reason)}: Field.set_lock, no tag); the tabs of the sections that apply."""
        self._focus_off_locked(locks or {})
        for path, f in self.fields.items():
            lock = (locks or {}).get(path)
            if lock is not None:
                f.set_tag(None)
                f.set_lock(lock)
                continue
            f.set_lock(None)
            f.show_value((shown or {}).get(path, self.get(path)))
            f.set_tag((tags or {}).get(path))
        for widgets, show in self.rows:
            if show is not None:
                on = bool(show())
                for w in widgets:
                    w.setVisible(on)
        if self.tabs:
            for i, show in self._sections:
                self.tab_btns[i].setVisible(show is None or bool(show()))
            # (the tab shown has no settings that apply now: the first that has. Not only while the form shows: More
            # settings is closed at the start, and with a saved method other than Best fit it opened on Best fit's
            # empty page with no tab selected, 2026-11-10. A tab button is the form's own child, so its own hidden
            # state is all that counts)
            if self.tab_btns[self.pages.currentIndex()].isHidden():
                first = next((i for i, b in self.tab_btns.items() if not b.isHidden()), None)
                if first is not None:
                    self.show_tab(first)


class Fold(QFrame):
    """A part that opens and closes: its title (and a short summary after it, with no "·" before it) is the button,
    Windows 11's chevron at its left (the theme's settings_boxes part: right when closed, down when open; filled when
    pointed at). A card (its chevron and its content start at a card's inset, as a card's title and content do), or
    with sub=True a row in a card (its title 14 px bold, a title in a card: Settings and More settings in Make the EQ,
    About these settings)."""
    toggled = Signal(bool)

    def __init__(self, title, open_=False, sub=False):
        super().__init__()
        if not sub:
            theme.mark(self, card=True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*((0, 0, 0, 0) if sub else (4, 2, 4, 4)))
        head = placed(lay, QHBoxLayout())
        self.btn = QToolButton()
        self.btn.setText(title)
        self.btn.setCheckable(True)
        self.btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        theme.mark(self.btn, fold=True, **({"sub": True} if sub else {}))
        self.btn.toggled.connect(self._set_open)
        head.addWidget(self.btn)
        self.summary = QLabel("")
        theme.mark(self.summary, role="muted")
        head.addWidget(self.summary, 1)
        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 4, 0, 8)
        lay.addWidget(self.body)
        self.btn.setChecked(open_)
        self._set_open(open_)

    def _set_open(self, on):
        self.btn.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.body.setVisible(on)
        self.toggled.emit(on)

    def add(self, w):
        self.body_lay.addWidget(w)
        return w
