"""Make an EQ's shared names and small helpers: ui/eq_page.py and its parts use them, and FORMAT_NAMES, MODE_SHORT,
MODE_HINT, TICKS and file_base_name still import from ui/eq_page.py too.
- FORMAT_NAMES: the files Save filters can write, by key; MODE_SHORT: each method's short name; MODE_HINT: the line
  beside Method; TICKS: the graph's frequencies
- and_list(names): "A, B, and C" in a sentence; on_words(names): where a profile is on, for a menu's keys' column;
  update_row_words(fm, name, names): an update row's two texts, cut to their room (the menu and the Guide)
- label(text, role, wrap): a label, in one of the theme's text roles; set_note(lab, text): a note's words, the note
  hidden while it has none (so an empty one takes no room); hz(v): a frequency in Hz or kHz
- combo_width(combo, text): the width a drop-down needs for text; SameWidth: empty room as wide as another widget
- Elided: a one-line label that never makes its row wider than the window (the values under the pointer); NameCombo:
  a drop-down whose name, when longer than its room, ends in "…" as Windows 11's own do (Target, Measurement, Runs
  this session); PairTitle: "A  →  B" on one line, or B under A when the window is narrow (the graph's title)
- file_base_name(...): a saved EQ's name, "<IEM> to <target> - <layout or method> <n>f"
- Notices: a message from a worker thread, said on the window's thread; modal(dlg): a window over the page until it's
  closed; paste_dialog(...): a window to paste filters into, with a name (By hand, Listen's EQs to compare)
"""
from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtWidgets import QLabel, QStyle, QStyleOptionComboBox, QStylePainter, QWidget

from ui import theme
from ui.search_combo import SearchCombo


FORMAT_NAMES = {"apo": "Equalizer APO / squiglink (.txt)", "graphic": "GraphicEQ for Wavelet (.txt)",
                "poweramp": "Poweramp (.json)", "uapp": "USB Audio Player PRO (.xml)", "soundsource": "SoundSource (.txt)",
                "voicemeeter": "Voicemeeter (.xml)", "rockbox": "Rockbox (.cfg)", "convolution": "impulse response (.wav)",
                "report": "a report (.html)"}  # (AutoEQ Local's export.js)
MODE_SHORT = {"site_single": "Website AutoEQ", "site_sweep": "Website best settings", "best_fit": "Best fit",
              "manual": "Manually"}
MODE_HINT = {"best_fit": "For EQ apps and devices: the nearest EQ to the target",
             "site_sweep": "For the squiglink / listener800 website", "site_single": "Uses one set of website values"}
TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]


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


def and_list(names):
    """Names in a sentence: "A", "A and B", "A, B, and C"."""
    names = list(names)
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + ", and " + names[-1]


def on_words(names):
    """Where a profile is switched on, for a menu's keys' column (names: its devices, in Devices' order): "not on",
    "on for A", "on for A and 2 more devices" (one name only, so two long Windows names don't make the menu wide)."""
    if not names:
        return "not on"
    more = len(names) - 1
    return f"on for {names[0]}" + (f" and {more} more device{'' if more == 1 else 's'}" if more else "")


UPDATE_ROOM = 38  # (average characters for each of the two texts of an update row: about 600 px for the menu)


def update_row_words(fm, name, names, quoted=True):
    """The two texts of a row that updates a profile (Use on device's menu, and the Guide's picture of it):
    Update “name” (quoted; the name only in the submenu) and on_words(names), each cut to UPDATE_ROOM average
    characters of fm (the menu's QFontMetrics) with "…", so a long name doesn't make the menu wide (an automatic name
    of 68 characters made it 958 px, a name of 80 wider than a 1366 px screen). The name is cut in the middle (the
    end, "… 10f", tells automatic names apart), the on words at the end. Returns (the row's first text, its on
    words, True when the name was cut)."""
    room = fm.averageCharWidth() * UPDATE_ROOM
    words = "Update “{}”" if quoted else "{}"
    short = fm.elidedText(name, Qt.ElideMiddle, room - fm.horizontalAdvance(words.format("")))
    return words.format(short), fm.elidedText(on_words(names), Qt.ElideRight, room), short != name


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
