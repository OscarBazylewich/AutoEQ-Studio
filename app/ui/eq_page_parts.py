"""Make an EQ's shared names and small helpers: ui/eq_page.py and its parts use them, and FORMAT_NAMES, MODE_SHORT,
MODE_HINT, TICKS and file_base_name still import from ui/eq_page.py too.
- FORMAT_NAMES: the files Save filters can write, by key; MODE_SHORT: each method's short name; MODE_HINT: the line
  beside Method; TICKS: the graph's frequencies
- label(text, role, wrap): a label, in one of the theme's text roles; note(lab, text): a note's words, the note
  hidden while it has none (so an empty one takes no room); hz(v): a frequency in Hz or kHz
- Elided: a one-line label that never makes its row wider than the window (the values under the pointer); NameCombo:
  a drop-down whose name, when longer than its room, ends in "…" as Windows 11's own do (Target, Measurement, Runs
  this session); PairTitle: "A  →  B" on one line, or B under A when the window is narrow (the graph's title)
- file_base_name(...): a saved EQ's name, "<IEM> to <target> - <layout or method> <n>f"
- Notices: a message from a worker thread, said on the window's thread; modal(dlg): a window over the page until it's
  closed; paste_dialog(...): a window to paste filters into, with a name (By hand, Listen's EQs to compare)
"""
from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtWidgets import QLabel, QStyle, QStyleOptionComboBox, QStylePainter

from ui import theme
from ui.search_combo import SearchCombo


FORMAT_NAMES = {"apo": "Equalizer APO / squiglink (.txt)", "graphic": "GraphicEQ for Wavelet (.txt)",
                "poweramp": "Poweramp (.json)", "uapp": "USB Audio Player PRO (.xml)", "soundsource": "SoundSource (.txt)",
                "voicemeeter": "Voicemeeter (.xml)", "rockbox": "Rockbox (.cfg)", "convolution": "impulse response (.wav)",
                "report": "a report (.html)"}  # (AutoEQ Local's export.js)
MODE_SHORT = {"site_single": "Website AutoEQ", "site_sweep": "Website sweep", "best_fit": "Best fit", "manual": "By hand"}
MODE_HINT = {"best_fit": "For EQ apps and devices: the closest match", "site_sweep": "For the squiglink / listener800 website",
             "site_single": "Checks one set of website values"}
TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]


def label(text="", role=None, wrap=True):
    lab = QLabel(text)
    lab.setWordWrap(wrap)
    if role:
        theme.mark(lab, role=role)
    return lab


def note(lab, text):
    """A note's words; the note hidden while it has none, so an empty one leaves no gap."""
    lab.setText(text)
    lab.setVisible(bool(text))


def hz(v):
    return f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"


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


class NameCombo(SearchCombo):
    """A drop-down of names (a target, a measurement, a run): one too long for it ends in "…", as Windows 11's own
    drop-downs do, rather than being cut off; its list shows every name whole."""

    def shown_text(self):
        """The chosen name as drawn: whole, or as much as fits, then "…"."""
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        room = self.style().subControlRect(QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, self).width()
        return self.fontMetrics().elidedText(opt.currentText, Qt.ElideRight, max(0, room - 4))

    def paintEvent(self, e):
        p = QStylePainter(self)
        p.setPen(self.palette().color(self.foregroundRole()))
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        p.drawComplexControl(QStyle.CC_ComboBox, opt)
        opt.currentText = self.shown_text()
        p.drawControl(QStyle.CE_ComboBoxLabel, opt)


def file_base_name(device, target, layout_name, mode, n):
    """"<IEM> to <target> - <layout or method> <n>f" (AutoEQ Local's export.js fileBaseName)."""
    what = layout_name.replace(" / ", ", ") if layout_name else {"site_single": "site AutoEQ", "site_sweep": "site AutoEQ",
                                                                 "best_fit": "best fit", "manual": "by hand"}.get(mode, "EQ")
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
