"""Make an EQ's shared names and small helpers: ui/eq_page.py and its parts use them, and FORMAT_NAMES, MODE_SHORT,
MODE_HINT, TICKS and file_base_name still import from ui/eq_page.py too.
- FORMAT_NAMES: the files Save filters can write, by key; MODE_SHORT: each method's short name; MODE_HINT: the line
  beside Method; TICKS: the graph's frequencies
- PASTE_HINT, skipped_words(name, items): Paste filters' gray words, and the message for the items an EQ can't have
- and_list(names): "A, B, and C" in a sentence; first_names(names, shown): "A and 2 more devices" (the on words),
  "A, B, C, and 9 more devices" (Update's message); on_words(names): where a profile is on, for a menu's keys'
  column; row_name(fm, name): a device's or a profile's name cut to a row's room; update_row_words(fm, name,
  names): an update row's two texts, cut to their room (the menu and the Guide);
  use_menu_order(sw, own): Use on device's device rows and Update rows, in one sequence (the menu and the Guide)
- count_words(n, engine): one result's count in a line, "6 filters", or "10 bands" for a graphic EQ's result
- label(text, role, wrap): a label, in one of the theme's text roles; set_note(lab, text): a note's words, the note
  hidden while it has none (so an empty one takes no room); hz(v): a frequency in Hz or kHz
- combo_width(combo, text): the width a drop-down needs for text; SameWidth: empty room as wide as another widget;
  WrapRow: a row of controls that takes more lines when its card has less room than the row needs on one;
  tab_order(*parts): the Tab sequence through parts of the page, one after the other (a part made later, or again)
- Elided: a one-line label that never makes its row wider than the window (the values under the pointer); NameCombo:
  a drop-down whose name, when longer than its room, ends in "…" as Windows 11's own do (Target, Measurement, Runs
  this session); PairTitle: "A  →  B" on one line, or B under A when the window is narrow (the graph's title)
- file_base_name(...): a saved EQ's name, "<IEM> to <target> - <layout or method> <n>f"
- Notices: a message from a worker thread, said on the window's thread; modal(dlg): a window over the page until it's
  closed; paste_dialog(...): a window to paste filters into, with a name (By hand, Listen's EQs to compare)
"""
from PySide6.QtCore import QObject, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import QLabel, QLayout, QStyle, QStyleOptionComboBox, QStylePainter, QWidget

from ui import own_items, theme
from ui.search_combo import SearchCombo


FORMAT_NAMES = {"apo": "Equalizer APO / squiglink (.txt)", "graphic": "GraphicEQ for Wavelet (.txt)",
                "poweramp": "Poweramp (.json)", "uapp": "USB Audio Player PRO (.xml)", "soundsource": "SoundSource (.txt)",
                "voicemeeter": "Voicemeeter (.xml)", "rockbox": "Rockbox (.cfg)", "convolution": "impulse response (.wav)",
                "report": "a report (.html)"}  # (AutoEQ Local's export.js)
MODE_SHORT = {"site_single": "Website AutoEQ", "site_sweep": "Website best settings", "best_fit": "Best fit",
              "manual": "Manually"}
MODE_HINT = {"best_fit": "Closest match to the target for your EQ app or device",
             "site_sweep": "Matches the squig.link or listener800 web AutoEQ",
             "site_single": "Uses a single fixed set of web AutoEQ parameters"}
TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
# (the gray words in the box of Paste filters, and the message for the items an EQ here can't have: one text for By
# hand and for Listen's EQs to compare, which read pasted text the same way)
PASTE_HINT = "Paste Equalizer APO lines, REW filters, or “frequency gain Q” (one per line)"


def skipped_words(name, items):
    """The message after an EQ was read with items that an EQ here can't have (a graphic EQ, other filter types)."""
    return (f"Skipped unsupported items in “{name}” (only peaking and shelf filters are supported): "
            f"{' · '.join(items)}")


def label(text="", role=None, wrap=True):
    lab = QLabel(text)
    lab.setWordWrap(wrap)
    if role:
        theme.mark(lab, role=role)
    return lab


def set_note(lab, text):
    """A note's words; the note hidden while it has none, so an empty one leaves no gap."""
    lab.setText(text)
    lab.setVisible(bool(text))


def hz(v):
    return f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"


def count_words(n, engine=None):
    """How many filters one result has, as a line says it: "1 filter", "6 filters"; for a result of a graphic EQ
    (engine "graphic": every band is a filter of the result) "1 band", "10 bands". One place for the word: the items
    of Number of filters, Compare's list, the Queue's "Done" line and History's lines. The names of settings, the
    column heads and Best result's choices say "filters" for every EQ."""
    word = "band" if engine == "graphic" else "filter"
    return f"{n} {word}{'' if n == 1 else 's'}"


def and_list(names):
    """Names in a sentence: "A", "A and B", "A, B, and C"."""
    names = list(names)
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + ", and " + names[-1]


NAMES_SHOWN = 1  # (the device names that a menu's on words give before "and N more devices": the menu stays narrow)
MESSAGE_NAMES = 3  # (the device names of each group in the message after Update before "and N more devices")


def first_names(names, shown=NAMES_SHOWN):
    """Devices in a few words (names: in Devices' order): all of them when there are shown or fewer ("A", "A and B",
    "A, B, and C", as and_list), else the first shown names and "1 more device" / "N more devices" for the others, in
    the same list ("A and 2 more devices", "A, B, C, and 9 more devices"), so many long Windows names make neither a
    menu wide nor a message long (Use on device's on words: NAMES_SHOWN; the message after Update: MESSAGE_NAMES)."""
    names = list(names)
    if len(names) <= shown:
        return and_list(names)
    more = len(names) - shown
    return and_list(names[:shown] + [f"{more} more device{'' if more == 1 else 's'}"])


ON_START = "active on "


def on_words(names):
    """Where a profile is switched on, for a menu's keys' column (names: its devices, in Devices' order): "off",
    "active on A", "active on A and 2 more devices" (first_names: one name only, so two long Windows names don't make
    the menu wide). ON_START: the words before the first name (update_row_words cuts that name only)."""
    return f"{ON_START}{first_names(names)}" if names else "off"


UPDATE_ROOM = 38  # (average characters for each of the two texts of an update row: about 600 px for the menu)


def row_name(fm, name, words="{}"):
    """A name in a row of Use on device's menu (a device, or a profile in words such as "Update “{}”"), cut in its
    middle with "…" to UPDATE_ROOM average characters of fm (the menu's QFontMetrics) for the row's first text, so
    a long name doesn't make the menu wide. Returns (the row's words, True when the name was cut)."""
    room = fm.averageCharWidth() * UPDATE_ROOM
    short = fm.elidedText(name, Qt.ElideMiddle, room - fm.horizontalAdvance(words.format("")))
    return words.format(short), short != name


def update_row_words(fm, name, names, quoted=True):
    """The two texts of a row that updates a profile (Use on device's menu, and the Guide's picture of it):
    Update “name” (quoted; the name only in the submenu) and on_words(names), each cut to UPDATE_ROOM average
    characters of fm (the menu's QFontMetrics) with "…", so a long name doesn't make the menu wide (an automatic name
    of 68 characters made it 958 px, a name of 80 wider than a 1366 px screen). The name is cut in the middle (the
    end, "… 10f", tells automatic names apart); in the on words only the first device's name is cut, at its end, so
    "and 1 more device" stays (cut at the end of the words, a usual Windows name such as "Speakers (Realtek(R) High
    Definition Audio)" took the count away). Returns (the row's first text, its on words, True when the name was cut)."""
    room = fm.averageCharWidth() * UPDATE_ROOM
    text, cut = row_name(fm, name, "Update “{}”" if quoted else "{}")
    on = on_words(names)
    if names and fm.horizontalAdvance(on) > room:
        start, more = ON_START, on[len(ON_START) + len(names[0]):]  # (more: " and N more devices", or "")
        first = fm.elidedText(names[0], Qt.ElideRight, max(0, room - fm.horizontalAdvance(start + more)))
        on = start + first + more
    return text, on, cut


def use_menu_order(sw, own=None):
    """Use on device's rows in one sequence, for its menu (ui/eq_page_result.py) and the Guide's picture of it
    (ui/guide_eq.py): the keys of the devices that the Devices screen lists, in its sequence (sw.listed: connected ones
    first, then A to Z by the name shown, a nickname too; a device that Windows does not list only with profiles, as
    there: one that you removed is in neither), and the ids of the profiles that are on for them, in that sequence,
    each one time (own: the profile the EQ came from, left out: it has its own row at the top). Returns (keys, ids)."""
    keys = sw.listed()
    profiles, ids = sw.profiles(), []
    for key in keys:
        on = sw.record(key)["active"]
        if on and on != own and on in profiles and on not in ids:
            ids.append(on)
    return keys, ids


class Elided(QLabel):
    """A label on one line that never makes its row wider (a long line made the page wider than the window): when its
    words are longer than its room they end in "…". text() is still all of them."""

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    def shown_text(self):
        """The words as drawn: all of them, or as many as fit, then "…"."""
        return self.fontMetrics().elidedText(self.text(), Qt.ElideRight, max(0, self.contentsRect().width()))

    def paintEvent(self, e):
        p = QStylePainter(self)
        p.drawItemText(self.contentsRect(), int(self.alignment().value), self.palette(), self.isEnabled(),
                       self.shown_text(), self.foregroundRole())


class PairTitle(QLabel):
    """A title of two names, "A  →  B" (the graph's: your measurement → the target): on one line when it fits, else B
    on a line of its own under A, "→  B" (each wrapping further only if it must), so a narrow window never cuts it or
    makes the page wider than the window. text() is the title as shown; setText() takes a title as it is."""

    def __init__(self):
        super().__init__()
        self.setWordWrap(True)
        self._pair = None

    def set_pair(self, a, b):
        self._pair = (a, b)
        self._fit()

    def setText(self, text):
        self._pair = None
        super().setText(text)

    def _fit(self):
        if self._pair is None:
            return
        a, b = self._pair
        one = f"{a}  →  {b}"
        room = self.contentsRect().width()
        text = one if room <= 0 or self.fontMetrics().horizontalAdvance(one) <= room else f"{a}\n→  {b}"
        if text != self.text():
            super().setText(text)

    def resizeEvent(self, e):  # (its width is the row's room left by the buttons: never its words', so this settles)
        super().resizeEvent(e)
        self._fit()


def combo_width(combo, text):
    """The width a drop-down needs to show text whole (its frame and arrow too), in the theme's sizes."""
    combo.ensurePolished()
    opt = QStyleOptionComboBox()
    combo.initStyleOption(opt)
    fm = combo.fontMetrics()
    inner = QSize(fm.horizontalAdvance(text) + 4, fm.height())
    return combo.style().sizeFromContents(QStyle.CT_ComboBox, opt, inner, combo).width()


def tab_order(*parts):
    """Puts these parts of one window one after the other in its Tab sequence: from the last control of a part, Tab
    goes to the first control of the next part. A part is a control, or a widget with controls in it (they keep the
    sequence in which they went into it). The first control keeps its place in the window's sequence, and the others
    come directly after it.
    Qt puts each new control at the end of its window's Tab sequence, wherever it is on the page. Make an EQ makes
    its page in steps and makes some rows again later: a part made after the parts under it is put into its place
    with this, in the step that makes it (2026-11-16: Tab on Queue… went to Adjust…, at the page's top, and the page
    scrolled there).
    The controls come from findChildren, not from a walk of Qt's sequence: a Python call of nextInFocusChain makes
    PySide6 6.11.2 keep the control that it returns as a child of the control asked, and mark it as deleted when Qt
    deletes that one (measured, 2026-11-16)."""
    stops = []
    for part in parts:
        window = part.window()
        # (not a control's own text field or view, which gives its focus to the control: Qt moves it with the
        # control; not a control's own pop-up list or menu, which is a window of its own)
        stops += [w for w in (part, *part.findChildren(QWidget))
                  if w.focusPolicy() != Qt.NoFocus and w.focusProxy() is None and w.window() is window]
    for before, after in zip(stops, stops[1:]):
        QWidget.setTabOrder(before, after)


class SameWidth(QWidget):
    """Empty room as wide as another widget (follow(widget)), none while that one is hidden: a row's end lined up
    with the row above, whose last button this row does not have (the Measurement row, under the Target's
    Adjust…)."""

    def __init__(self):
        super().__init__()
        from PySide6.QtWidgets import QSizePolicy
        self.partner = None
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def follow(self, widget):
        self.partner = widget
        self.updateGeometry()

    def sizeHint(self):
        p = self.partner
        if p is None or p.isHidden():
            return QSize(0, 0)
        return QSize(p.sizeHint().width(), 0)

    def minimumSizeHint(self):
        return self.sizeHint()


class WrapRow(QLayout):
    """A row of controls, placed as a QHBoxLayout places them while they fit on one line: each as wide as it asks
    for, from the left, and those added after to_the_end() at the row's right end. With less room, the row takes
    more lines: a group of controls (group() starts one) that does not fit after the group before it starts the next
    line with all of its controls, and a control that does not fit on its group's line starts one too. So the
    controls keep their sequence and the row never makes its card wider than the window. It says how high it is at a
    width (height for width).
    The result card's tools were the widest row of Make an EQ: 869 px on one line, with 779 px of room in the smallest
    window (841 px), so the page scrolled sideways by 90 px (measured, 2026-11-16)."""

    def __init__(self):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self._items, self._space, self._end, self._group = own_items(self), 0, False, 0

    def space(self, px):
        """px more room before the next control (a QHBoxLayout's addSpacing). A line never starts with it."""
        self._space += px

    def to_the_end(self):
        """The controls added from now on go to the right end of their line (a QHBoxLayout's addStretch)."""
        self._end = True

    def group(self):
        """The controls added from now on are a group of their own: they go to the next line together when they do
        not all fit after the controls before them. (Without groups the row's last control went there alone, and one
        button on a line did not look good: the user, 2026-11-16.)"""
        self._group += 1

    # ---------------------------------------------------------------- Qt's own: what's in it
    def addItem(self, item):
        self._items.append((item, self._space, self._end, self._group))
        self._space = 0

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i][0] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i)[0] if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation.Horizontal

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        lines = self._lines(width)
        return sum(self._high(line) for line in lines) + self.spacing() * max(0, len(lines) - 1)

    def sizeHint(self):
        """On one line."""
        wide = 0
        for item, space, _end, _group in self._shown():
            wide += (self.spacing() + space if wide else 0) + item.sizeHint().width()
        return QSize(wide, self.heightForWidth(wide))

    def minimumSize(self):
        """Its narrowest: as wide as its widest control (each on a line of its own), and one line high (as a label
        whose words wrap: how high it is at a width comes from heightForWidth)."""
        shown = [part[0] for part in self._shown()]
        return QSize(max((item.sizeHint().width() for item in shown), default=0),
                     max((item.minimumSize().height() for item in shown), default=0))

    def setGeometry(self, rect):
        super().setGeometry(rect)
        y = rect.y()
        for line in self._lines(rect.width()):
            high = self._high(line)
            for item, x, wide in line:
                # (the line's height for each, as in a QHBoxLayout: Qt puts a lower control, a tick box, in its middle)
                item.setGeometry(QRect(rect.x() + x, y, wide, high))
            y += high + self.spacing()

    # ---------------------------------------------------------------- the lines
    def _shown(self):
        return [part for part in self._items if not part[0].isEmpty()]  # (a hidden control takes no room)

    @staticmethod
    def _high(line):
        return max(item.sizeHint().height() for item, _x, _wide in line)

    def _lines(self, width):
        """The controls in lines of width px: [[(item, its x from the line's start, its width)]]."""
        gap, lines, ends, shown = self.spacing(), [], [], self._shown()
        for i, (item, space, end, group) in enumerate(shown):
            wide = need = item.sizeHint().width()
            x = lines[-1][-1][1] + lines[-1][-1][2] + gap + space if lines else 0
            if i == 0 or shown[i - 1][3] != group:  # (a group's first control needs room for all of its group)
                for other, more, _end, its in shown[i + 1:]:
                    if its != group:
                        break
                    need += gap + more + other.sizeHint().width()
            if not lines or x + need > width:
                lines.append([])
                ends.append(0)
                x = 0
            lines[-1].append((item, x, wide))
            ends[-1] = ends[-1] + 1 if end else 0  # (how many controls at this line's end are for its right end)
        for line, n in zip(lines, ends):
            move = max(0, width - line[-1][1] - line[-1][2])
            line[len(line) - n:] = [(item, x + move, wide) for item, x, wide in line[len(line) - n:]]
        return lines


class NameCombo(SearchCombo):
    """A drop-down of names (a target, a measurement, a run). A name too long for it ends in "…": every SearchCombo
    does that now (2026-11-10), so this is only its name for those lists."""


def file_base_name(device, target, layout_name, mode, n):
    """"<IEM> to <target> - <layout or method> <n>f" (AutoEQ Local's export.js fileBaseName)."""
    what = layout_name.replace(" / ", ", ") if layout_name else {"site_single": "website AutoEQ",
                                                                 "site_sweep": "website AutoEQ", "best_fit": "best fit",
                                                                 "manual": "manual"}.get(mode, "EQ")
    return f"{device} to {target} - {what} {n}f"


class Notices(QObject):
    """A message from a worker thread, said on the window's thread (a queued signal)."""
    said = Signal(str)


def modal(dlg):
    """A window over the page until it's closed, then let go (each kept all its rows for the rest of the session)."""
    dlg.exec()
    dlg.deleteLater()


def paste_dialog(parent, title, name_hint, words, verb="OK"):
    """A window to paste filters into, with a name: (name, text), or None when it's cancelled. Windows 11's dialog, as
    Set up's (.claude/notes/UI-RULES.md 2): the words on the card's colour, its buttons on a band below
    (window_parts.dialog_band): `verb` (what it does: Add, Start…) first, in the accent, then Cancel."""
    from PySide6.QtWidgets import QDialog, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget
    from ui.window_parts import dialog_band
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    theme.mark(dlg, dialog=True)  # (the card's colour: theme_sheet's window_screens)
    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    body = QWidget()
    v = QVBoxLayout(body)
    v.setContentsMargins(24, 24, 24, 20)  # (Windows 11's dialog padding)
    v.addWidget(QLabel("Name"))  # (its label, as Save as a preset's: the gray example goes as you type, the UI audit)
    name = QLineEdit()
    name.setPlaceholderText(name_hint)
    name.setAccessibleName("Name")
    v.addWidget(name)
    v.addWidget(QLabel(words))  # (over its box)
    text = QPlainTextEdit()
    text.setAccessibleName("Filters")
    v.addWidget(text)
    outer.addWidget(body, 1)
    band, _main = dialog_band(dlg, verb, dlg.accept)
    outer.addWidget(band)
    ok = dlg.exec()
    out = (name.text().strip(), text.toPlainText())
    dlg.deleteLater()  # (asked once: not kept, hidden, for as long as the page is there)
    return out if ok else None


class CurveNames(QWidget):
    """The names of a graph's curves in a line next to it, each after a short line in its colour and style (the UI
    audit, 2026-11-08: pyqtgraph's names were in the graph, on the curves at its top left); more lines when they
    need them. set_items([(name, pen)]); from_legend(legend): the names a pyqtgraph legend has (kept hidden). A name
    longer than the whole line ends in "…" (it went past the graph's edge, cut off: a code review, 2026-11-10), its
    whole name in its tooltip (full_name_at)."""
    SAMPLE, GAP, SPACE = 20, 6, 18  # (px: the line, from it to the name, between two names)

    def __init__(self):
        super().__init__()
        self.items = []
        from PySide6.QtWidgets import QSizePolicy
        sp = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sp.setHeightForWidth(True)
        self.setSizePolicy(sp)

    def set_items(self, items):
        self.items = [(str(n), p) for n, p in items if n]
        self.setAccessibleName("Curves: " + ", ".join(n for n, _p in self.items))
        self.setVisible(bool(self.items)) if self.parentWidget() is not None else None
        self.updateGeometry()
        self.update()

    def from_legend(self, legend):
        import pyqtgraph as pg
        items = []
        for sample, lab in getattr(legend, "items", []):
            item = getattr(sample, "item", None)
            pen = getattr(item, "opts", {}).get("pen") if item is not None else None
            items.append((getattr(lab, "text", ""), pg.mkPen(pen) if pen is not None else pg.mkPen("#888888")))
        self.set_items(items)

    def _places(self, width):
        """Each name's place: (x, y, width, the name as drawn, pen, its whole name), and the height of them all. A
        name that fits on no line ends in "…" at the line's end."""
        from PySide6.QtGui import QFontMetrics
        fm = QFontMetrics(self.font())
        x, y, out, h = 0, 0, [], fm.height() + 4
        room = max(0, width - self.SAMPLE - self.GAP)  # (for the words of a name alone on its line)
        for name, pen in self.items:
            shown = name if fm.horizontalAdvance(name) <= room else fm.elidedText(name, Qt.ElideRight, room)
            w = self.SAMPLE + self.GAP + fm.horizontalAdvance(shown)
            if x and x + w > width:
                x, y = 0, y + h
            out.append((x, y, w, shown, pen, name))
            x += w + self.SPACE
        return out, (y + h if out else 0)

    def shown_names(self):
        """The names as drawn at the present width (a long one ends in "…")."""
        return [shown for _x, _y, _w, shown, _p, _n in self._places(self.width())[0]]

    def full_name_at(self, pos):
        """The whole name of a name cut to "…" at pos (a point in the widget), or "" (a name shown whole needs no
        tooltip)."""
        from PySide6.QtGui import QFontMetrics
        h = QFontMetrics(self.font()).height() + 4
        for x, y, w, shown, _p, name in self._places(self.width())[0]:
            if shown != name and x <= pos.x() <= x + w and y <= pos.y() < y + h:
                return name
        return ""

    def event(self, e):
        from PySide6.QtCore import QEvent
        if e.type() == QEvent.ToolTip:  # (only on a name that ends in "…": its whole name)
            from PySide6.QtWidgets import QToolTip
            whole = self.full_name_at(e.pos())
            if whole:
                QToolTip.showText(e.globalPos(), whole, self)
            else:
                QToolTip.hideText()
                e.ignore()
            return True
        return super().event(e)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._places(width)[1]

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(300, self.heightForWidth(max(300, self.width())))

    def minimumSizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(0, self.heightForWidth(max(1, self.width())))

    @staticmethod
    def sample_pen(pen):
        """The pen of a name's short line: the curve's own colour, style and width (at least 1 px). A floor of 2 px
        made a 1.2 px curve's line look thicker than the curve (2026-11-10)."""
        from PySide6.QtGui import QPen
        line = QPen(pen)
        line.setWidthF(max(1.0, pen.widthF()))
        line.setCosmetic(True)
        return line

    def paintEvent(self, e):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QColor, QPainter
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        fm = p.fontMetrics()
        for x, y, _w, name, pen, _whole in self._places(self.width())[0]:
            mid = y + (fm.height() + 4) / 2
            p.setPen(self.sample_pen(pen))
            p.drawLine(QPointF(x, mid), QPointF(x + self.SAMPLE, mid))
            p.setPen(QColor(theme.tokens()["ink2"]))
            p.drawText(int(x + self.SAMPLE + self.GAP), int(y + 2 + fm.ascent()), name)
